"""Per packed D eval: DR vs no-DR sampled resets (same worlds, same upstream frames), box patch set, zero action.
Object position difference DR - noDR per world (max over objects) right after the reset (r1), at the end of the 20-step
VOC-1 hold (h20) and 20 steps later (h40, VOC 0 in this env). Also the no-DR run's own object motion during the hold
(h20 - r1), the baseline settling. Our references only; no ground truth."""
import json, os, sys
import numpy as np
O = sys.argv[1]; P = json.load(open(sys.argv[2])); res = {}
def pos(q, oq):
    return np.stack([q[:, i:i + 3] for i in oq], 1)                  # [W, B, 3]
for ep in sys.argv[3].split(',') if len(sys.argv) > 3 else ('14', '16', '33', '25', '30'):
    try:
        f = ep.replace('p', 'p') ; a, b = np.load(f'{O}/ep{f}_nodr.npz'), np.load(f'{O}/ep{f}_dr.npz')
    except FileNotFoundError:
        res[ep] = 'missing'; continue
    oq = [int(i) for i in a['obj_q']]
    same = bool(np.array_equal(a['frame1'], b['frame1']) and np.array_equal(a['finger1'], b['finger1']))
    d = {k: np.linalg.norm(pos(b[k], oq) - pos(a[k], oq), axis=2).max(1) * 100 for k in ('r1', 'h20', 'h40')}   # cm per world
    base = np.linalg.norm(pos(a['h20'], oq) - pos(a['r1'], oq), axis=2).max(1) * 100
    fin = bool(np.isfinite(a['h40']).all() and np.isfinite(b['h40']).all())
    W = len(d['h20'])
    res[ep] = dict(worlds=W, same_upstream_frames=same, finite=fin, frames=sorted(set(int(x) for x in a['frame1']))[:6],
                   reset_offset_cm_max=round(float(d['r1'].max()), 3),
                   hold_end_diff_cm=dict(median=round(float(np.median(d['h20'])), 3), p90=round(float(np.percentile(d['h20'], 90)), 3),
                                         max=round(float(d['h20'].max()), 2), share_gt_1cm=round(float((d['h20'] > 1).mean()), 3)),
                   after_hold_diff_cm=dict(median=round(float(np.median(d['h40'])), 3), max=round(float(d['h40'].max()), 2),
                                           share_gt_1cm=round(float((d['h40'] > 1).mean()), 3)),
                   nodr_hold_motion_cm=dict(median=round(float(np.median(base)), 3), max=round(float(base.max()), 2),
                                            share_gt_1cm=round(float((base > 1).mean()), 3)),
                   worst_worlds=[dict(world=int(w), frame=int(a['frame1'][w]), hold_end_diff_cm=round(float(d['h20'][w]), 2),
                                      nodr_hold_motion_cm=round(float(base[w]), 2)) for w in np.argsort(-d['h20'])[:3]],
                   ref_md5=P[ep]['md5'], objects=P[ep]['urdfs'] and [os.path.basename(u).replace('_rigid.urdf', '') for u in P[ep]['urdfs']],
                   embodiment=P[ep]['emb'])
print(json.dumps(res, indent=1))
