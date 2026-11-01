"""Step 1+2 (GT-free): marker layout discovery in our body frame and the per-frame visibility census.

Reads scan.py detections, our perc2 tracks (poses.npz) and, for the hand/rest split, our refined hands (eval only).
Layout: mklayout.discover on rest frames pooled over the episodes, then the stereo-only shape by generalised
Procrustes, placed in the body frame by Kabsch onto the cluster medians. Per frame, the labelled marker set is the
largest set of detections whose pairwise 3-D distances match the layout (tol TOL) and whose rigid fit lies within
GATE of our track (prior). No ground truth, no scan, no scan-derived constant.
Usage: python census.py OBJ SPLIT EPS(comma) OUT_JSON [--seed-template]
"""
import itertools, json, os, sys
import numpy as np
from scipy.spatial.transform import Rotation as Rot
sys.path.insert(0, os.path.dirname(__file__))
import mlib, mklayout as L

S = mlib.S
TOL = 0.007                  # m, pairwise-distance tolerance of a layout-consistent set
GATE_T, GATE_R = 0.05, 30.0  # prior gate for accepting a set (m, deg)
HAND_CM = 4.0


def hands_path(e):
    run = mlib.PERC_EVAL[e]
    for v in ('perc2mck', 'perc2mcks'):
        p = f'{S}/eg/dl/runs/{run}/refs/{v}/ep{e}/hands_refined.npz'
        if os.path.exists(p):
            return p
    return None


def load(obj, split, e):
    P = np.load(mlib.poses_path(split, e)); T = P[f'cam_T_{obj}'].astype(np.float64); W = P['world_T_cam'].astype(np.float64)
    J = json.load(open(f'{S}/mk/scan/{split}{e}_{obj}{os.environ.get("MK_SUFFIX", "")}.json'))
    N = min(J['N'], len(T)); T, W = T[:N], W[:N]
    return dict(e=e, T=T, W=W, Tw=W @ T, dets=J['dets'][:N], dv0=J['dv0'], N=N)


def hand_state(d, obj, split):
    """True where a perceived hand joint is within HAND_CM of our tracked mesh (world frame). None if no hands."""
    if split != 'eval':
        return None
    p = hands_path(d['e'])
    if p is None:
        return None
    import trimesh
    V = np.asarray(trimesh.load(f'/home/user/v2d-track3/meshes/library_v3/{obj}.glb', force='mesh').vertices)[::8]
    H = np.load(p); out = np.zeros(d['N'], bool)
    for t in range(min(d['N'], len(H['joints_left']))):
        X = V @ d['Tw'][t][:3, :3].T + d['Tw'][t][:3, 3]; m = 99.0
        for s in ('left', 'right'):
            if H[f'valid_{s}'][t]:
                m = min(m, np.linalg.norm(H[f'joints_{s}'][t].astype(float)[:, None] - X[None], axis=2).min() * 100)
        out[t] = m < HAND_CM
    return out


def best_set(X, Lb, Tprior, tol=TOL):
    """largest layout-consistent labelled subset of detections X (n,3 camera) -> (labels dict marker->det, pose 4x4,
    rms m), by backtracking over prior-gated candidates (a detection is a candidate for marker j when it lies within
    GATE_T + sin(GATE_R) * lever_j of j's prior prediction). Ties: closer to the prior pose."""
    k, n = len(Lb), len(X)
    if n == 0:
        return {}, None, None
    Dl = np.linalg.norm(Lb[:, None] - Lb[None], axis=2); Dx = np.linalg.norm(X[:, None] - X[None], axis=2)
    pred = Lb @ Tprior[:3, :3].T + Tprior[:3, 3]
    lever = np.linalg.norm(Lb - Lb.mean(0), axis=1)
    cand = [[i for i in range(n) if np.linalg.norm(X[i] - pred[j]) < GATE_T + np.sin(np.radians(GATE_R)) * lever[j]]
            for j in range(k)]
    best = [0, -1e9, {}, None, None]

    def leaf(lab):
        m = len(lab)
        if m == 0 or m < best[0]:
            return
        pose, rms = fit_pose(lab, X, Lb, Tprior)
        dt = np.linalg.norm(pose[:3, 3] - Tprior[:3, 3])
        dr = np.degrees(Rot.from_matrix(pose[:3, :3] @ Tprior[:3, :3].T).magnitude())
        if dt > GATE_T or dr > GATE_R:
            return
        sc = -dt / GATE_T - dr / GATE_R - rms / tol
        if m > best[0] or sc > best[1]:
            best[:] = [m, sc, dict(lab), pose, rms]

    def rec(j, lab, used):
        if len(lab) + (k - j) < best[0]:
            return
        if j == k:
            leaf(lab); return
        for i in cand[j]:
            if i in used or any(abs(Dx[i, lab[q]] - Dl[j, q]) > tol for q in lab):
                continue
            lab[j] = i; used.add(i); rec(j + 1, lab, used); used.discard(i); del lab[j]
        rec(j + 1, lab, used)

    rec(0, {}, set())
    return best[2], best[3], best[4]


def fit_pose(lab, X, Lb, Tprior):
    """rigid pose (body->camera) from labelled markers. >=3: Kabsch. 2: rotate the prior minimally so the body
    marker axis maps onto the observed axis, translate to match the midpoint. 1: prior rotation, translate."""
    ks = sorted(lab); A = Lb[ks]; B = X[[lab[j] for j in ks]]
    R0, t0 = Tprior[:3, :3], Tprior[:3, 3]; P = np.eye(4)
    if len(ks) >= 3:
        R, t = L.kabsch(A, B)
    elif len(ks) == 2:
        a = R0 @ (A[1] - A[0]); b = B[1] - B[0]; a /= np.linalg.norm(a); b /= np.linalg.norm(b)
        v = np.cross(a, b); s = np.linalg.norm(v); c = float(a @ b)
        Rm = np.eye(3) if s < 1e-9 else Rot.from_rotvec(v / s * np.arctan2(s, c)).as_matrix()
        R = Rm @ R0; t = B.mean(0) - R @ A.mean(0)
    else:
        R = R0; t = B[0] - R @ A[0]
    P[:3, :3], P[:3, 3] = R, t
    rms = float(np.sqrt(np.mean(np.sum((A @ R.T + t - B) ** 2, 1)))) if len(ks) >= 2 else 0.0
    return P, rms


def refine_layout(D, L0, rest_only=True):
    """stereo-only shape from labelled sets (pairwise-distance medians for 3 markers, GPA for more), placed in the
    body frame by Kabsch onto the medians of the labelled body-frame points (our track's mean pose)."""
    k = len(L0); sets, Bpts = [], [[] for _ in range(k)]
    for d in D:
        for t in range(d['N']):
            lab = d['labs'][t]
            if len(lab) < 2 or (rest_only and not d['rest'][t]):
                continue
            X = np.array([q['X'] for q in d['dets'][t]]); B, _ = d['B'][t]
            sets.append({int(j): X[i] for j, i in lab.items()})
            for j, i in lab.items():
                Bpts[int(j)].append(B[i])
    pd = {}
    for a_, b_ in itertools.combinations(range(k), 2):
        v = [np.linalg.norm(s_[a_] - s_[b_]) for s_ in sets if a_ in s_ and b_ in s_]
        pd[(a_, b_)] = (float(np.median(v)), len(v), float(np.percentile(np.abs(np.array(v) - np.median(v)), 90)) if v else None)
    if k == 3 and all(pd[p][1] >= 5 for p in pd):
        d01, d02, d12 = pd[(0, 1)][0], pd[(0, 2)][0], pd[(1, 2)][0]
        x = (d01 ** 2 + d02 ** 2 - d12 ** 2) / (2 * d01); y = np.sqrt(max(d02 ** 2 - x ** 2, 0))
        Sh = np.array([[0, 0, 0], [d01, 0, 0], [x, y, 0.0]])
        # orientation (reflection) from the seed: the planar triangle is reflection-ambiguous only by a 180 deg flip
        res = None
    else:
        Sh, res = L.gpa(sets, k)
        if Sh is None:
            return L0, dict(note='too few sets; seed kept', n_sets=len(sets))
    # placement: body-frame medians of the labelled markers, from complete sets when there are >= 10 of them (a
    # 2-marker label is constrained only by one distance, so its marker can be a look-alike)
    full_pts = [[] for _ in range(k)]
    for d in D:
        for t in range(d['N']):
            lab = d['labs'][t]
            if len(lab) == k and (not rest_only or d['rest'][t]):
                B, _ = d['B'][t]
                for j, i in lab.items():
                    full_pts[int(j)].append(B[i])
    if len(full_pts[0]) >= 10:
        Bpts = full_pts
    Bm = np.array([np.median(b, 0) if len(b) else L0[j] for j, b in enumerate(Bpts)])
    nB = [len(b) for b in Bpts]
    R, t = L.kabsch(Sh, Bm, w=np.maximum(np.array(nB, float), 1.0))
    Lb = Sh @ R.T + t
    info = dict(n_sets=len(sets), n_full=int(sum(len(s_) == k for s_ in sets)), body_pts=nB,
                dists_mm={f'{a_}-{b_}': [round(v[0] * 1000, 1), v[1], None if v[2] is None else round(v[2] * 1000, 1)]
                          for (a_, b_), v in pd.items()},
                place_resid_mm=(np.linalg.norm(Lb - Bm, axis=1) * 1000).round(1).tolist(),
                shift_from_seed_mm=(np.linalg.norm(Lb - L0, axis=1) * 1000).round(1).tolist())
    res = []
    for s_ in sets:
        if len(s_) >= 3:
            ks = sorted(s_); A = np.array([s_[j] for j in ks]); R_, t_ = L.kabsch(A, Sh[ks])
            res.append(np.linalg.norm(A @ R_.T + t_ - Sh[ks], axis=1).mean())
    if res:
        info['shape_fit_mm'] = dict(n=len(res), median=round(float(np.median(res) * 1000), 2),
                                    p90=round(float(np.percentile(res, 90) * 1000), 2))
    return Lb, info


def discover_seed(D, r3_min=0.0046, min_sep=0.025, max_k=6):
    """GT-free layout seed from our own video: body-frame clusters of rest detections (mklayout.discover), kept when
    their median 3-D radius is marker-like (>= r3_min), they are seen in >= 2 episodes (share >= 0.05; one episode
    suffices if the object has one), and they are >= min_sep apart (strongest first)."""
    C, share, cnt = L.discover([d['B'] for d in D], [d['rest'] for d in D], min_share=0.15)
    rows = []
    for c, sh in zip(C, share):
        per_ep, r3 = [], []
        for d in D:
            hit = 0
            for t, (B, X) in enumerate(d['B']):
                if d['rest'][t] and len(B):
                    dd = np.linalg.norm(B - c, axis=1); i = int(np.argmin(dd))
                    if dd[i] < 0.012:
                        hit += 1; r3.append(d['dets'][t][i]['r3'])
            per_ep.append(hit / max(1, int(d['rest'].sum())))
        rows.append(dict(c=c, share=sh, per_ep=per_ep, r3=float(np.median(r3)) if r3 else 0.0))
    need = 2 if len(D) >= 2 else 1
    keep = []
    for r in sorted(rows, key=lambda r: -r['share']):
        ok = r['r3'] >= r3_min and sum(p >= 0.05 for p in r['per_ep']) >= need
        ok = ok and all(np.linalg.norm(r['c'] - q['c']) >= min_sep for q in keep)
        r['kept'] = bool(ok)
        if ok and len(keep) < max_k:
            keep.append(r)
    info = [dict(c_mm=(r['c'] * 1000).round(1).tolist(), share=r['share'], per_ep=[round(p, 2) for p in r['per_ep']],
                 r3_mm=round(r['r3'] * 1000, 2), kept=r['kept']) for r in rows]
    return np.array([r['c'] for r in keep]), info


def label_all(D, Lb):
    for d in D:
        n = np.zeros(d['N'], int); poses = [None] * d['N']; labs = [None] * d['N']; rms_ = np.full(d['N'], np.nan)
        for t in range(d['N']):
            X = np.array([q['X'] for q in d['dets'][t]]) if d['dets'][t] else np.zeros((0, 3))
            lab, pose, rms = best_set(X, Lb, d['T'][t])
            n[t] = len(lab); poses[t] = pose; labs[t] = {int(k): int(v) for k, v in lab.items()}
            if rms is not None:
                rms_[t] = rms
        d['n'], d['labs'], d['fix'], d['rms'] = n, labs, poses, rms_


def main():
    obj, split, eps, out = sys.argv[1], sys.argv[2], [int(x) for x in sys.argv[3].split(',')], sys.argv[4]
    D = [load(obj, split, e) for e in eps]
    for d in D:
        d['rest'] = L.rest_mask(d['Tw'])
        d['B'] = L.body_points(d['dets'], d['T'])
        d['hand'] = hand_state(d, obj, split)
    rep = dict(obj=obj, split=split, eps=eps)
    if '--seed-template' in sys.argv:      # our own video-measured template layout (note 20 / spoon/params.json)
        L0 = np.array(json.load(open('/home/user/v2d-track3/spoon/params.json'))['markers_canonical_m'])
        rep['seed'] = 'spoon template (note 20 stereo measurements of our own video)'
    elif '--consensus' in sys.argv:
        Cj = json.load(open(sys.argv[sys.argv.index('--consensus') + 1]))
        L0 = np.array(Cj['layout_body_m']); rep['seed'] = 'consensus ' + sys.argv[sys.argv.index('--consensus') + 1]
        keep = []
        for d in D:
            o = Cj['offsets'].get(str(d['e'])); A = np.eye(4)
            if o is None:      # not registered: the episode's own track frame (within-episode corrections only)
                print('episode', d['e'], 'not registered to the consensus: offset = identity')
                rep.setdefault('unregistered', []).append(d['e'])
            else:
                A[:3, :3] = np.array(o['R']); A[:3, 3] = o['t']
            d['A'] = A
            d['T_obj'] = d['T']; d['T'] = d['T'] @ A          # prior in the consensus (mesh) frame
            keep.append(d)
        D = keep
        rep['layout_body_m'] = L0.tolist(); label_all(D, L0); _census_out(D, L0, rep, obj, split, out); return
    elif '--discover' in sys.argv:
        L0, info = discover_seed(D); rep['seed'] = 'discovery'; rep['discovery'] = info
        print('discovery:', len(L0), 'markers'); [print('  ', r) for r in info]
        if len(L0) < 2:
            json.dump(rep, open(out, 'w'), indent=1); print('fewer than 2 markers discovered'); return
    else:
        L0 = np.array(json.load(open(sys.argv[sys.argv.index('--seed') + 1]))['layout_body_m'])
        rep['seed'] = sys.argv[sys.argv.index('--seed') + 1]
    rep['seed_body_mm'] = (L0 * 1000).round(1).tolist()
    label_all(D, L0)
    Lb, info = refine_layout(D, L0, rest_only=True)
    if info.get('n_sets', 0) < 20:
        Lb, info = refine_layout(D, L0, rest_only=False); info['rest_only'] = False
    rep['layout_refine'] = info; rep['layout_body_m'] = Lb.tolist()
    print('layout refine:', json.dumps(info))
    label_all(D, Lb)
    _census_out(D, Lb, rep, obj, split, out)


def _census_out(D, Lb, rep, obj, split, out):
    rep['census'] = {}
    for d in D:
        n = d['n']
        grp = dict(all=np.ones(d['N'], bool), rest=d['rest'])
        if d['hand'] is not None:
            grp['hand'] = d['hand']; grp['nohand'] = ~d['hand']
        rep['census'][str(d['e'])] = {g: dict(frames=int(m.sum()), ge1=round(float((n[m] >= 1).mean()), 3) if m.any() else None,
                                              ge2=round(float((n[m] >= 2).mean()), 3) if m.any() else None,
                                              ge3=round(float((n[m] >= 3).mean()), 3) if m.any() else None)
                                      for g, m in grp.items()}
        rep['census'][str(d['e'])]['fit_rms_mm_med'] = round(float(np.nanmedian(d['rms'][n >= 3]) * 1000), 2) if (n >= 3).any() else None
        per_marker = [int(sum(1 for lab in d['labs'] if j in lab and len(lab) >= 2)) for j in range(len(Lb))]
        rep['census'][str(d['e'])]['per_marker_in_sets'] = per_marker
        print(d['e'], json.dumps(rep['census'][str(d['e'])]))
        np.savez_compressed(f'{S}/mk/scan/fix_{split}{d["e"]}_{obj}.npz', n=n, rest=d['rest'],
                            hand=d['hand'] if d['hand'] is not None else np.zeros(0),
                            fix=np.array([p if p is not None else np.full((4, 4), np.nan) for p in d['fix']]),
                            labs=json.dumps(d['labs']), layout=Lb, A=d.get('A', np.eye(4)))
    json.dump(rep, open(out, 'w'), indent=1)


if __name__ == '__main__':
    main()
