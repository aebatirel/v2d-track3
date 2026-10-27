"""verify_scorer test 1: re-derive the e2e AUC / SP / MP of stored public rollouts with my own scorer (vs_core),
plus the frame-0 = reference diagnostic, plus a frame-offset (lag) check, plus a quaternion-order sanity check.
Usage: python -I t1_rollouts.py EP RUN_SUBPATH LIB OUT.json [--f0]"""
import json, sys, time
sys.path.insert(0, '/home/user/v2d-track3/docs/analysis/robustness-review-20261026/refcheck/verify_scorer')
import numpy as np
from vs_core import *

ep, sub, lib, out = int(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
names, G = load_gt(ep)
rn, ach, ref, steps, rframe, md = load_rollout(f'{STORE}/{sub}/episode_{ep:06d}.parquet')
assert rn == names, (rn, names)
res = dict(ep=ep, rollout=sub, lib=lib, names=names, T_rollout=len(steps), T_gt=len(G),
           steps_first_last=[int(steps[0]), int(steps[-1])],
           reference_frame_equals_step=bool(np.all(rframe == steps[:, None])), md_fps=md.get('flash_chord.control_fps'))
assert len(steps) == len(G)
t0 = time.time()
Hs = [host(n, s) for s, n in enumerate(names)]
regs = [register(budget(f'{LIB}/{lib}/{n}.glb'), Hs[s], 1_000_003 * ep + 101 * s) for s, n in enumerate(names)]
res['reg_deg'] = {n: round(reg_angle(regs[s][1]), 3) for s, n in enumerate(names)}
r = my_score(ach, G, Hs, regs)
res['sim'] = dict(AUC=round(r['AUC'], 6), per_obj=[round(x, 4) for x in r['per_obj']], SP=r['SP'], MP=r['MP'])
a2 = ach.copy(); a2[0] = ref[0]
r2 = my_score(a2, G, Hs, regs)
res['sim_f0ref'] = dict(AUC=round(r2['AUC'], 6), SP=r2['SP'], MP=r2['MP'], dAUC=round(r2['AUC'] - r['AUC'], 4))
# frame-offset check: distance of sim[k] to our reference[k+d] (no GT), mean over objects and frames
lag = {}
for d in (-2, -1, 0, 1, 2):
    k = np.arange(max(0, -d), len(steps) - max(0, d))
    lag[d] = round(float(np.linalg.norm(ach[k, :, :3] - ref[k + d, :, :3], axis=-1).mean() * 1000), 3)
res['sim_vs_ref_pos_mm_by_lag'] = lag
# frame-0 gap sim vs reference
res['frame0_gap'] = {n: dict(pos_mm=round(float(np.linalg.norm(ach[0, s, :3] - ref[0, s, :3]) * 1000), 3),
                             rot_deg=round(float(np.degrees((Rot.from_quat(ach[0, s, 3:]) * Rot.from_quat(ref[0, s, 3:]).inv()).magnitude())), 3))
                     for s, n in enumerate(names)}
# reference vs GT, frame lag (does our reference sit on the GT time base?)
lagg = {}
for d in (-1, 0, 1):
    k = np.arange(max(0, -d), len(steps) - max(0, d))
    lagg[d] = round(float(np.linalg.norm(ref[k, :, :3] - G[k + d, :, :3], axis=-1).mean() * 1000), 3)
res['ref_vs_gt_pos_mm_by_lag_unaligned'] = lagg
res['seconds'] = round(time.time() - t0, 1)
json.dump(res, open(out, 'w'), indent=1)
print(json.dumps(res, indent=1))
