"""H-rest mechanism, per object named by the mapping check (diagnostic; mocap read only here).
For the 3 highest-S own-mesh rollouts of each episode: registered error of sim and of reference vs truth at frame 0,
mean and max; their drift from frame 0 (cm); the share of frames where the sim is closer to the truth than the
reference; and the per-object T, S, R, S*R. Distinguishes 'reference drifts, sim stays at the truth' (H-rest as
stated) from 'static shared offset, errors do not compound' (sub-additive AUC)."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import myscore as M

rows = [json.loads(l) for l in open(f'{M.SP}/work/verify_mapping/all.jsonl')]
rows = [r for r in rows if 'error' not in r and r['lib'] != 'scan']
out = {}
for ep, obj in ((11, 'blue_cup'), (12, 'plastic_dish_rack'), (31, 'plastic_dish_rack'), (24, 'wooden_piece_2'),
                (26, 'white_pot'), (27, 'white_pot')):
    names, fidx, G = M.gt(ep); b = names.index(obj); L = []
    for r in sorted([r for r in rows if r['ep'] == ep], key=lambda r: -r['S'])[:3]:
        fr, sim, ref, _, _ = M.read_rollout(f"{M.SP}/store/{r['path']}", names)
        et = M.registered(ep, r['lib'], sim, fr, return_err=True)[:, b] * 100
        er = M.registered(ep, r['lib'], ref, fr, return_err=True)[:, b] * 100
        gt = G[np.searchsorted(fidx, fr)]
        rest = (np.linalg.norm(gt[:, b, :3] - gt[:1, b, :3], axis=-1) < 0.015) & \
               (np.degrees(2 * np.arccos(np.clip(np.abs(np.sum(gt[:, b, 3:] * gt[:1, b, 3:], -1)), 0, 1))) < 5)
        drift = lambda X: float(np.linalg.norm(X[:, b, :3] - X[:1, b, :3], axis=-1).max() * 100)
        L.append(dict(S=r['S'], T_obj=r['T_obj'][obj], S_obj=r['S_obj'][obj], R_obj=r['R_obj'][obj],
                      SxR=round(r['S_obj'][obj] * r['R_obj'][obj], 4), rest_share=round(float(rest.mean()), 3),
                      e_sim_f0=round(float(et[0]), 2), e_ref_f0=round(float(er[0]), 2),
                      e_sim_mean=round(float(et.mean()), 2), e_ref_mean=round(float(er.mean()), 2),
                      e_ref_minus_f0_max=round(float(np.max(np.abs(er - er[0]))), 2),
                      drift_ref_cm=round(drift(ref), 2), drift_sim_cm=round(drift(sim), 2), drift_truth_cm=round(drift(gt), 2),
                      sim_closer_share=round(float(np.mean(et < er)), 3)))
    out[f'ep{ep} {obj}'] = L
    for x in L:
        print(ep, obj, x, flush=True)
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rest_detail.json'), 'w'), indent=1)
