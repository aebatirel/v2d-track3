"""GT-free scoring of eval-10 rollouts against BOTH our references (2026-10-31; eval-10 V4p retrain, ops/jobs/ev10_v4p.sh;
docs/research/work/perception-sprint-20261031/ev10retrain/PREREG.md section 3.5). No ground truth exists for an eval
episode and none is read: inputs are the official evaluator's rollout parquets (achieved = simulated object poses,
reference columns = the reference the policy was trained on, at each reference_frame), our reference parquets (V = the
V4p trained reference, P = the packed gl10A2 reference), the kit's metric code and our library meshes.

For each rollout and each reference X:
  - the reference columns are replaced by X's object poses (object_body_position / object_body_wxyz) at the same
    reference_frame; for X = the rollout's OWN training reference (--set NAME:OWN:...) the replaced values must equal
    the stored columns (max |dpos| <= 1e-6 m, max |dq| <= 1e-6 up to sign), else own_ref_ok = false (INVALID upstream);
  - sim_vs_ref: exactly pipeline/qa.py policy's metric (the kit's read_trajectory, world 0, 500 points on a 5 cm sphere
    (rng seed 0), _warp_to_reference_start, _object_add, _add_auc);
  - RPE / MPPE / AUC and per-object AUC / MPPE / fraction of frames with keypoint error > 5 cm: the score-status session's
    GT-free audit (docs/analysis/evalaudit-20261031/audit.py on origin/claude/standings-20261031, its rdlib chain): our
    library mesh as host (anchor = surface centroid, 1000 surface samples seed 7+slot, cups: distinct principal axis,
    order 360), identity registration, the kit's _convert_object_body, _align_registered_scene (frame 0), kit metrics;
    audit_fail = audit.py's flag (an object off by > 5 cm keypoint error in >= 20 % of frames), reported only;
  - fail = RPE > 5 cm (the agreed pack-10 rule's failure).
Only the GT-free functions of rdlib are re-implemented here (no mocap, scan or episode-parquet reader is present).
A rollout whose any score is non-finite gets scored = false.
Usage: e10v_score.py --kit KIT --lib meshes/library_v3 --ref V=REF.parquet --ref P=REF.parquet --out OUT.json
                     --set NAME:OWN:GLOB [--set ...] [--jobs N]   (OWN = V | P | -; GLOB matches rollout parquets, e.g.
                     results/ev10_v4p/conf/r*/ep10/episode_000010.parquet; draws sorted by the r<i> number in the path;
                     N worker processes, default env E10V_SCORE_JOBS or min(8, cpu count): ~10 s per rollout and reference)
"""
import argparse, glob, hashlib, importlib.util, json, math, os, re, sys
import numpy as np, pyarrow.parquet as pq

NAMES = ['blue_cup', 'beige_cup']                  # the kit roster of eval 10 (slot order)
SYM = {'beige_cup': 'axis', 'blue_cup': 'axis', 'white_pot_lid': 'half'}
KP_CM, FAIL_FRAC, RPE_FAIL_CM = 5.0, 0.20, 5.0
TOL = 1e-6
EP = 10


def load_mod(path, name):
    spec = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def ref_poses(path):
    """(T, B, 7) xyzw object poses of a reference parquet, in the roster's slot order."""
    t = pq.read_table(path, columns=['object_body_names', 'object_body_position', 'object_body_wxyz'])
    names = [str(x) for x in t.column('object_body_names')[0].as_py()]
    if names != NAMES:
        raise SystemExit(f'{path}: object names {names} != roster {NAMES}')
    P = np.array(t.column('object_body_position')[0].as_py(), float); B = len(names); T = P.size // (3 * B)
    P = P.reshape(T, B, 3); Q = np.array(t.column('object_body_wxyz')[0].as_py(), float).reshape(T, B, 4)[..., [1, 2, 3, 0]]
    return np.concatenate([P, Q], 2)


def load_rollout(path):
    """audit.py's load(): world 0, slot order check, achieved A and reference F (frames, B, 7) xyzw."""
    t = pq.read_table(path).to_pandas()
    t = t[t.environment_id == t.environment_id.min()]
    pairs = {(int(i), str(n)) for i, n in zip(t.object_id, t.object_body_name)}
    if pairs != {(k, n) for k, n in enumerate(NAMES)}:
        raise ValueError(f'{path}: slots {sorted(pairs)} != roster {NAMES}')
    fr = np.sort(t.reference_frame.unique()); B = len(NAMES)
    A = np.full((len(fr), B, 7), np.nan); F = np.full((len(fr), B, 7), np.nan); idx = {n: i for i, n in enumerate(NAMES)}
    for row in t.itertuples():
        i = np.searchsorted(fr, row.reference_frame); s = idx[row.object_body_name]
        A[i, s] = [row.achieved_position_x, row.achieved_position_y, row.achieved_position_z, row.achieved_quaternion_x,
                   row.achieved_quaternion_y, row.achieved_quaternion_z, row.achieved_quaternion_w]
        F[i, s] = [row.reference_position_x, row.reference_position_y, row.reference_position_z, row.reference_quaternion_x,
                   row.reference_quaternion_y, row.reference_quaternion_z, row.reference_quaternion_w]
    if not (np.isfinite(A).all() and np.isfinite(F).all() and (fr == np.arange(len(fr))).all()):
        raise ValueError(f'{path}: non-finite poses or non-contiguous reference frames')
    return A, F, fr


class Scorer:
    def __init__(self, kit, lib):
        self.M = load_mod(f'{kit}/metric_code/track_3/RPE.py', 'kit_track3_rpe')     # rdlib.load_kit
        self.A = load_mod(f'{kit}/metric_code/track_3/AUC.py', 'kit_track3_auc')     # qa.py's import AUC
        sys.path.insert(0, kit)
        from v2dlb.submission_parquet import read_trajectory                          # qa.py's reader
        self.read_trajectory = read_trajectory
        import trimesh
        self.H = []
        for s, n in enumerate(NAMES):                                                 # audit.py lib_host
            m = trimesh.load(f'{lib}/{n}.glb', force='mesh'); v, f = np.asarray(m.vertices, np.float64), np.asarray(m.faces, np.int64)
            c, r = self.M._surface_moments(v, f); pts = self.M._sample_mesh_surface(v, f, 1000, 7 + s) - c
            axis, order = np.zeros(3), 0
            if n in SYM:
                w, U = np.linalg.eigh(np.cov(pts.T))
                if SYM[n] == 'half':
                    axis, order = U[:, 0], 2
                else:
                    k = int(np.argmax([abs(w[i] - np.mean(np.delete(w, i))) for i in range(3)])); axis, order = U[:, k], 360
            self.H.append(dict(name=n, anchor=c, radius=r, points=pts, axis=axis, order=order))
        rng = np.random.default_rng(0); p = rng.normal(size=(500, 3)); p = 0.05 * p / np.linalg.norm(p, axis=1, keepdims=True)
        self.V500 = np.repeat(p[None], len(NAMES), 0)                                 # qa.py's points

    # ---- qa.py policy
    def qa_grid(self, path):
        tr = self.read_trajectory(path); w0 = tr.world_index == tr.world_index.min()
        frames = np.unique(tr.frame_index[w0]); B = int(tr.object_slot.max()) + 1
        def grid(P):
            G = np.full((len(frames), B, 7), np.nan)
            for f, s, p in zip(tr.frame_index[w0], tr.object_slot[w0], P[w0]):
                G[np.searchsorted(frames, f), s] = p
            return G
        return frames, grid(tr.pose_xyzw), grid(tr.reference_xyzw)

    def sim_vs_ref(self, sim, ref):
        a, r = sim[:, None], ref[:, None]
        a = self.A._warp_to_reference_start(a, r)
        return float(self.A._add_auc(self.A._object_add(a, r, self.V500)))

    # ---- audit.py (rdlib chain, GT-free functions only)
    def audit(self, A7, F7):
        M, H = self.M, self.H
        C = A7.copy()
        for s, h in enumerate(H):                                                     # convert (identity registration)
            C[:, s] = M._convert_object_body(A7[:, s], h['anchor'], np.eye(3))
        R = F7.copy()
        for s, h in enumerate(H):                                                     # ref_anchor
            R[:, s, :3] += np.einsum('...ij,j->...i', M._rotation_matrix(F7[:, s, 3:]), h['anchor'])
        Al = M._align_registered_scene(C[:, None].copy(), R[:, None].copy(), [h['axis'] for h in H])[:, 0]
        a, r = Al[:, None], R[:, None]
        axes = [h['axis'] for h in H]; orders = [h['order'] for h in H]; pts = [h['points'] for h in H]
        adds = [M._symmetry_point_errors(a[:, :, s], r[:, :, s], pts[s], axes[s], orders[s]) for s in range(len(H))]
        kp = M._MPPE_KEYPOINT_DIRECTIONS * M._MPPE_KEYPOINT_RADIUS_M
        mp = [M._symmetry_point_errors(a[:, :, s], r[:, :, s], kp, axes[s], orders[s]) for s in range(len(H))]
        out = dict(AUC=float(M._add_auc(np.stack(adds, axis=-1))), MPPE=float(np.mean(mp) * 100),
                   RPE=float(M._registered_pose_metric('rpe_cm', a, r, pts, axes, orders)))
        pf_kp = np.stack([x[:, 0] for x in mp], 1) * 100
        objs = {}
        for s, h in enumerate(H):
            off = pf_kp[:, s] > KP_CM
            objs[h['name']] = dict(AUC=round(float(M._add_auc(adds[s][..., None])), 4), MPPE=round(float(mp[s].mean() * 100), 3),
                                   frac_kp_over_5cm=round(float(off.mean()), 3), end_kp_cm=round(float(pf_kp[-1, s]), 2),
                                   ref_travel_cm=round(float(np.linalg.norm(R[:, s, :3] - R[0, s, :3], axis=1).max() * 100), 2),
                                   sim_travel_cm=round(float(np.linalg.norm(Al[:, s, :3] - Al[0, s, :3], axis=1).max() * 100), 2))
        out['objects'] = objs
        out['audit_fail'] = any(o['frac_kp_over_5cm'] >= FAIL_FRAC for o in objs.values())
        return out

    def score(self, path, refs, own):
        A7, F7, fr = load_rollout(path)
        frames, sim_q, ref_q = self.qa_grid(path)
        if not (np.array_equal(frames, fr) and np.allclose(sim_q, A7, atol=0, rtol=0, equal_nan=False)):
            raise ValueError(f'{path}: the kit reader and the audit reader disagree')
        md = pq.read_schema(path).metadata or {}
        row = dict(path=path, frames=int(len(fr)), checkpoint_sha256=md.get(b'flash_chord.checkpoint_sha256', b'').decode() or None,
                   reference_parquet=md.get(b'flash_chord.reference_parquet', b'').decode() or None, own=own, vs={})
        row['sim_vs_ref_stored'] = round(self.sim_vs_ref(sim_q, ref_q), 4)              # qa.py on the file as it is
        for X, Rx in refs.items():
            if len(Rx) < len(fr):
                raise ValueError(f'{path}: reference {X} has {len(Rx)} frames, the rollout {len(fr)}')
            Fx = Rx[fr]
            if X == own:
                dp = float(np.abs(Fx[..., :3] - F7[..., :3]).max())
                dq = float(np.minimum(np.abs(Fx[..., 3:] - F7[..., 3:]), np.abs(Fx[..., 3:] + F7[..., 3:])).max())
                row['own_ref_check'] = dict(ref=X, max_dpos_m=dp, max_dq=dq, ok=bool(dp <= TOL and dq <= TOL))
            v = dict(sim_vs_ref=round(self.sim_vs_ref(A7, Fx), 4))
            au = self.audit(A7, Fx)
            v.update(RPE=round(au['RPE'], 4), MPPE=round(au['MPPE'], 4), AUC=round(au['AUC'], 4), audit_fail=au['audit_fail'],
                     objects=au['objects'])
            v['fail'] = bool(v['RPE'] > RPE_FAIL_CM) if math.isfinite(v['RPE']) else None
            row['vs'][X] = v
        if own in refs and 'own_ref_check' not in row:
            row['own_ref_check'] = dict(ref=own, ok=False, why='own reference not given')
        vals = [row['vs'][X][k] for X in row['vs'] for k in ('sim_vs_ref', 'RPE', 'MPPE', 'AUC')]
        row['scored'] = all(isinstance(x, float) and math.isfinite(x) for x in vals)
        return row


_W = {}


def _init(kit, lib, refs):
    _W['S'] = Scorer(kit, lib); _W['refs'] = refs


def _one(w):
    f, own = w
    try:
        r = _W['S'].score(f, _W['refs'], own); r['draw'] = draw_no(f)
    except Exception as e:
        r = dict(path=f, draw=draw_no(f), scored=False, error=f'{type(e).__name__}: {str(e)[:300]}')
    return r


def draw_no(path):
    m = re.findall(r'/r(\d+)/', path)
    return int(m[-1]) if m else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--kit', required=True); ap.add_argument('--lib', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--ref', action='append', required=True, help='X=path (X in V, P)')
    ap.add_argument('--set', action='append', required=True, help='NAME:OWN:GLOB')
    ap.add_argument('--jobs', type=int, default=0)
    a = ap.parse_args()
    md5 = lambda f: hashlib.md5(open(f, 'rb').read()).hexdigest()
    refs = {}; ref_info = {}
    for x in a.ref:
        k, p = x.split('=', 1); refs[k] = ref_poses(p); ref_info[k] = dict(path=p, md5=md5(p), frames=int(len(refs[k])))
    out = dict(refs=ref_info, rule='docs/research/work/perception-sprint-20261031/ev10retrain/PREREG.md 3.5', rpe_fail_cm=RPE_FAIL_CM, sets={})
    jobs = a.jobs or int(os.environ.get('E10V_SCORE_JOBS') or min(8, os.cpu_count() or 1))
    specs = [(spec.split(':', 2)) for spec in a.set]
    work = [(f, own) for name, own, g in specs for f in sorted(glob.glob(g), key=lambda p: (draw_no(p), p))]
    if jobs > 1 and len(work) > 1:
        from concurrent.futures import ProcessPoolExecutor
        with ProcessPoolExecutor(jobs, initializer=_init, initargs=(a.kit, a.lib, refs)) as ex:
            done = dict(zip(work, ex.map(_one, work)))
    else:
        _init(a.kit, a.lib, refs); done = {w: _one(w) for w in work}
    for name, own, g in specs:
        files = sorted(glob.glob(g), key=lambda p: (draw_no(p), p)); rows = [done[(f, own)] for f in files]
        out['sets'][name] = dict(own=own, glob=g, n_files=len(files), n_scored=sum(1 for r in rows if r.get('scored')), rollouts=rows)
        print(f'{name} (own {own}): {len(files)} rollouts, {out["sets"][name]["n_scored"]} scored; ' + '; '.join(
            f"r{r['draw']} " + ' '.join(f"{X} s_v_r {r['vs'][X]['sim_vs_ref']:.4f} RPE {r['vs'][X]['RPE']:.2f}" for X in r.get('vs', {}))
            + ('' if r.get('own_ref_check', {}).get('ok', own == '-') else ' OWN-REF-CHECK FAILED') + (f" ERROR {r['error']}" if 'error' in r else '')
            for r in rows), flush=True)
    json.dump(out, open(a.out, 'w'), indent=1)


if __name__ == '__main__':
    main()
