"""GT-free audit of packed Track 3 rollouts (31 Oct 2026): the kit's RPE / MPPE / AUC of the simulated object
trajectory against OUR OWN reference (the one the policy was trained to track), and a failure flag per rollout.

No ground truth is read anywhere in this script: no mocap, no `observation.objects` pose field, no public scans, no
public episode parquets. Inputs are only
  - the evaluator output parquets (episode_XXXXXX.parquet: achieved = simulated object, reference = our reference, both
    tracking-mesh body-frame poses in the table frame) and their episode JSONs;
  - our library meshes (anchor = surface centroid, 1000 surface samples seed 7+slot, symmetry axis/order from the mesh:
    cups axis/360, lid thinnest axis/2), identity registration; this is roll.py's "policy" path of
    docs/analysis/rpe-decomp-20261031 (rdlib.py chain, kit metric file RPE.py == MPPE.py == AUC.py apart from _METRIC);
  - object names and slot order: the kit's data/track_3_evaluation_objects.json (eval) or the names stored in
    roll_rollouts.json (public check), cross-checked against the parquet's object_id -> object_body_name.

Usage (python -I):
  audit.py check RDLIB_DIR KIT_DIR ROLL_JSON OUT_JSON CELL_DIR:ARM/epN [...]   public draws, compared with roll_rollouts.json
  audit.py eval  RDLIB_DIR KIT_DIR DL_DIR SUMMARY7 SUMMARY8 OUT_JSON           the 20 eval episodes of packs 7 and 8
"""
import glob, json, os, sys, time
import numpy as np, pyarrow.parquet as pq

REPO = '/home/user/v2d-track3'
LIB = f'{REPO}/meshes/library_v3'
EP_LIB = {8: f'{REPO}/meshes/library_v3x'}           # pack 6's EP_LIB (ops/jobs/h5_reeval.sh): eval 8 tracked v3x
P6 = 'runs/20261026-pack6-5203d42/results/submission'
SRC = {'p7': {33: 'runs/20261030-c33B-0202139/results/submission'},
       'p8': {33: 'runs/20261030-c33B-0202139/results/submission', 1: 'runs/20261030-e1conf2-d41382e/results/submission'}}
# learner per eval episode: pack READMEs results/submissions/20261025-track3c, 20261026-track3d, 20261030-track3{g,h}
LEARNER = {1: 'standard (std0116)', 3: 'grasp lock (seed43)', 5: 'grasp lock (seed43)', 6: 'grasp lock (pack1)',
           8: 'grasp lock (eval_both)', 10: 'grasp lock, carved cups (gl10A2)', 14: 'grasp lock (eval_both)',
           15: 'grasp lock (seed43)', 16: 'grasp lock (seed43)', 19: 'standard (std1928)',
           20: 'grasp lock (eval_both)', 25: 'standard, carve s42 (c25s42)', 28: 'standard (std1928)',
           30: 'standard (std30)', 32: 'grasp lock frozen s46', 33: 'grasp lock arm B (rcB)',
           35: 'grasp lock (pack1)', 36: 'grasp lock (pack1)', 37: 'grasp lock (pack1)', 38: 'grasp lock (pack1)'}
LEARNER_P8 = {1: 'standard, carve s43 (c01s43)'}

# failure rule (fixed before any eval rollout was scored; thresholds checked on the public P-arm draws only)
KP_CM = 5.0          # per-frame keypoint error (kit MPPE keypoints) above which an object is "off" the reference
FAIL_FRAC = 0.20     # object fails if it is off in >= 20 % of frames; pair fails if per-frame RPE > 5 cm in >= 20 %
LEFT_MOVE = 5.0      # left behind: reference travel >= 5 cm and simulated travel < 30 % of it
LEFT_RATIO = 0.30
FLUNG_CM = 15.0      # flung: the simulated anchor goes >= 15 cm away from every point of the reference path


def lib_host(L, lib, n, slot):  # roll.py's lib_host with the library as an argument
    v, f = L.load_vf(f'{lib}/{n}.glb'); c, r = L.M._surface_moments(v, f)
    pts = L.M._sample_mesh_surface(v, f, 1000, 7 + slot) - c
    axis, order = np.zeros(3), 0
    if n in L.SYM:
        w, U = np.linalg.eigh(np.cov(pts.T))
        if L.SYM[n] == 'half':
            axis, order = U[:, 0], 2
        else:
            k = int(np.argmax([abs(w[i] - np.mean(np.delete(w, i))) for i in range(3)])); axis, order = U[:, k], 360
    return dict(name=n, mesh=(v, f), anchor=c, radius=r, points=pts, axis=axis, order=order)


def load(f, names):  # roll.py's load, plus a slot-order check (object_id k must be names[k])
    t = pq.read_table(f).to_pandas()
    t = t[t.environment_id == t.environment_id.min()]
    pairs = {(int(i), str(n)) for i, n in zip(t.object_id, t.object_body_name)}
    assert pairs == {(k, n) for k, n in enumerate(names)}, (f, pairs, names)
    fr = np.sort(t.reference_frame.unique()); B = len(names)
    A = np.full((len(fr), B, 7), np.nan); F = np.full((len(fr), B, 7), np.nan)
    idx = {n: i for i, n in enumerate(names)}
    for row in t.itertuples():
        i = np.searchsorted(fr, row.reference_frame); s = idx[row.object_body_name]
        A[i, s] = [row.achieved_position_x, row.achieved_position_y, row.achieved_position_z, row.achieved_quaternion_x,
                   row.achieved_quaternion_y, row.achieved_quaternion_z, row.achieved_quaternion_w]
        F[i, s] = [row.reference_position_x, row.reference_position_y, row.reference_position_z, row.reference_quaternion_x,
                   row.reference_quaternion_y, row.reference_quaternion_z, row.reference_quaternion_w]
    assert np.isfinite(A).all() and np.isfinite(F).all() and (fr == np.arange(len(fr))).all(), f
    return A, F


def audit(L, parquet, names, lib):
    A, F = load(parquet, names)
    H = [lib_host(L, lib, n, s) for s, n in enumerate(names)]
    REG = [(h['anchor'], np.eye(3)) for h in H]
    C, R = L.convert(A, REG), L.ref_anchor(F, H)
    Al = L.align(C, R, H)                                            # the kit's frame-0 scene alignment
    m = L.metrics(Al, R, H, per_frame=True)
    pf_rpe = m['pf_rpe_cm']
    if len(names) > 1:
        assert abs(pf_rpe.mean() - m['RPE']) < 1e-6 * max(1, m['RPE']), (pf_rpe.mean(), m['RPE'])
    T = len(A); objs = []
    for s, n in enumerate(names):
        pa, pr = Al[:, s, :3] * 100, R[:, s, :3] * 100
        err = np.linalg.norm(pa - pr, axis=1); kp = m['pf_mppe_cm'][:, s]
        ref_tr = float(np.linalg.norm(pr - pr[0], axis=1).max()); sim_tr = float(np.linalg.norm(pa - pa[0], axis=1).max())
        path_dev = float(np.min(np.linalg.norm(pa[:, None] - pr[None], axis=2), axis=1).max())
        off = kp > KP_CM
        first_off = int(np.argmax(off)) if off.any() else None
        o = dict(name=n, AUC=round(m['obj_AUC'][s], 4), MPPE=round(m['obj_MPPE'][s], 3),
                 frac_kp_over_5cm=round(float(off.mean()), 3), max_kp_cm=round(float(kp.max()), 2),
                 end_kp_cm=round(float(kp[-1]), 2), end_pos_err_cm=round(float(err[-1]), 2),
                 max_pos_err_cm=round(float(err.max()), 2), ref_travel_cm=round(ref_tr, 2), sim_travel_cm=round(sim_tr, 2),
                 path_dev_cm=round(path_dev, 2), first_off_frac=None if first_off is None else round(first_off / T, 3),
                 min_dz_cm=round(float((pa[:, 2] - pr[:, 2]).min()), 2))
        o['fail'] = o['frac_kp_over_5cm'] >= FAIL_FRAC
        if o['fail']:
            if ref_tr >= LEFT_MOVE and sim_tr < LEFT_RATIO * ref_tr:
                o['reason'] = f'left behind (sim travel {sim_tr:.1f} of ref {ref_tr:.1f} cm)'
            elif path_dev >= FLUNG_CM:
                o['reason'] = f'flung ({path_dev:.0f} cm off the reference path)'
            elif np.median(err[off]) < 3.0:
                o['reason'] = f'orientation off (pos err median {np.median(err[off]):.1f} cm in off frames)'
            else:
                o['reason'] = (f'dropped/lost (off from {100 * first_off / T:.0f} % of the episode, '
                               f'ends {err[-1]:.1f} cm off, {path_dev:.1f} cm off the path)')
        objs.append(o)
    rpe5 = float((pf_rpe > 5).mean()) if len(names) > 1 else 0.0
    fail_obj = [o for o in objs if o['fail']]
    fail = bool(fail_obj) or rpe5 >= FAIL_FRAC
    reason = '; '.join(f"{o['name']}: {o['reason']}" for o in fail_obj)
    if fail and not fail_obj:
        reason = f'pair relation off in {100 * rpe5:.0f} % of frames (each object < 20 %)'
    marginal = (not fail) and (any(o['frac_kp_over_5cm'] >= 0.05 or o['end_kp_cm'] > KP_CM for o in objs) or rpe5 >= 0.05)
    return dict(names=names, frames=T, AUC=round(m['AUC'], 4), MPPE=round(m['MPPE'], 4), RPE=round(m['RPE'], 4),
                rpe_max_frame_cm=round(float(pf_rpe.max()), 2), rpe_frac_frames_over_5cm=round(rpe5, 3),
                fail=fail, reason=reason, marginal=bool(marginal), objects=objs)


def kit(rdlib, kitdir):
    sys.path.insert(0, rdlib)
    import rdlib as L
    L.load_kit(kitdir)
    return L


def check(rdlib, kitdir, roll_json, out, specs):
    """public draws: compare our numbers with roll_rollouts.json's GT-free 'policy' numbers (and show 'total')."""
    L = kit(rdlib, kitdir); ref = json.load(open(roll_json))['cells']; res = {}
    for spec in specs:
        root, cell = spec.split(':'); c = ref[cell]; names = c['names']; rows = []
        for d in c['draws']:
            f = f"{root}/{cell}/{d['draw']}/episode_{c['ep']:06d}.parquet"
            t0 = time.time(); a = audit(L, f, names, LIB)
            rows.append(dict(draw=d['draw'], ours={k: a[k] for k in ('AUC', 'MPPE', 'RPE')}, roll_policy=d['policy'],
                             roll_total=d['total'], qa_sim_vs_ref=d['sim_vs_ref_qa'], fail=a['fail'], reason=a['reason'],
                             marginal=a['marginal'], rpe_max_frame_cm=a['rpe_max_frame_cm'],
                             rpe_frac_frames_over_5cm=a['rpe_frac_frames_over_5cm'], objects=a['objects']))
            r = rows[-1]
            print(f"{cell} {d['draw']}: ours RPE {a['RPE']:.4f} MPPE {a['MPPE']:.4f} AUC {a['AUC']:.4f} | roll policy "
                  f"RPE {d['policy']['RPE']:.4f} MPPE {d['policy']['MPPE']:.4f} AUC {d['policy']['AUC']:.4f} | total RPE "
                  f"{d['total']['RPE']:.2f} | fail {a['fail']} {a['reason']} ({time.time() - t0:.0f} s)", flush=True)
        dif = max(abs(r['ours'][k] - r['roll_policy'][k]) for r in rows for k in ('AUC', 'MPPE', 'RPE'))
        res[cell] = dict(ep=c['ep'], names=names, max_abs_diff_vs_roll_policy=round(dif, 4), draws=rows)
        print(f'{cell}: max |ours - roll policy| = {dif:.4g}', flush=True)
    json.dump(dict(kind='evalaudit public check', note='GT-free path only; roll_total copied from roll_rollouts.json',
                   cells=res), open(out, 'w'), indent=1)


def summary(path):
    txt = open(path).read(); return {int(k): v for k, v in json.loads(txt[:txt.index('}') + 1]).items()}


def eval_audit(rdlib, kitdir, dl, sum7, sum8, out):
    L = kit(rdlib, kitdir)
    roster = {int(k): v for k, v in json.load(open(f'{kitdir}/data/track_3_evaluation_objects.json'))['episodes'].items()}
    packed = {'p7': summary(sum7), 'p8': summary(sum8)}
    res = {}
    for pk in ('p7', 'p8'):
        rows = {}
        for ep in sorted(roster):
            if pk == 'p8' and ep != 1:
                continue                                              # pack 8 = pack 7 apart from eval 1
            base = f"{dl}/{SRC[pk].get(ep, P6)}"
            pqf, js = f'{base}/results/episode_{ep:06d}.parquet', f'{base}/results/episode_{ep:06d}.json'
            qa = json.load(open(f'{base}/qa/ep{ep}/qa_policy.json'))
            j = json.load(open(js)); mt = j['metrics']
            t0 = time.time(); a = audit(L, pqf, roster[ep], EP_LIB.get(ep, LIB))
            a.update(ep=ep, learner=(LEARNER_P8 if pk == 'p8' else {}).get(ep, LEARNER[ep]), source=f"{SRC[pk].get(ep, P6)}",
                     reference_parquet=j['parquet'], checkpoint_sha256=j['checkpoint_sha256'],
                     packed_sim_vs_ref=packed[pk][ep], qa_sim_vs_ref=qa['sim_vs_ref'],
                     evaluator=dict(add_auc=round(mt['add_auc'], 4), relative_position_error_cm=round(mt['relative_position_error_cm'], 3),
                                    mppe_cm=round(mt['mppe_cm'], 3), success_rate=j['reference_tracking']['success_rate'],
                                    termination_cause_fraction=mt['termination_cause_fraction']),
                     mesh_library=os.path.basename(EP_LIB.get(ep, LIB)))
            rows[ep] = a
            print(f"{pk} eval {ep:2d} {'+'.join(roster[ep]):32s} sim_vs_ref {packed[pk][ep]:.4f} | RPE {a['RPE']:6.2f} MPPE "
                  f"{a['MPPE']:6.2f} AUC {a['AUC']:.4f} | maxRPE {a['rpe_max_frame_cm']:6.1f} >5cm {a['rpe_frac_frames_over_5cm']:.2f} | "
                  f"fail {a['fail']} {a['reason']} ({time.time() - t0:.0f} s)", flush=True)
        res[pk] = rows
    json.dump(dict(kind='evalaudit', note='GT-free: sim vs our own reference, kit chain (rdlib), library meshes as host',
                   rule=dict(KP_CM=KP_CM, FAIL_FRAC=FAIL_FRAC, LEFT_MOVE=LEFT_MOVE, LEFT_RATIO=LEFT_RATIO, FLUNG_CM=FLUNG_CM),
                   packs={k: {str(e): v for e, v in r.items()} for k, r in res.items()}), open(out, 'w'), indent=1)
    print('wrote', out)


if __name__ == '__main__':
    if sys.argv[1] == 'check':
        check(*sys.argv[2:6], sys.argv[6:])
    elif sys.argv[1] == 'eval':
        eval_audit(*sys.argv[2:8])
    else:
        sys.exit(__doc__)
