"""Classic-error probes on the public rollouts (diagnostic; mocap read only here, after inference).
1. Off-by-one: R of every distinct reference with the mocap shifted by -2..+2 frames (peak should be at 0 unless the
   reference has a genuine lag).
2. Quaternion order: R with the mocap quaternion read as x,y,z,w instead of w,x,y,z (should collapse).
3. H-rest, direct: for the ep11 / ep12 / ep31 objects the mapping check names, the per-frame displacement of truth,
   reference and simulation from frame 0, and the registered errors sim-vs-truth / ref-vs-truth.
Writes check_frames.json."""
import collections, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import myscore as M

rows = [json.loads(l) for l in open(f'{M.SP}/work/verify_mapping/all.jsonl')]
rows = [r for r in rows if 'error' not in r and r['lib'] != 'scan']
ref1 = {}
for r in rows:
    ref1.setdefault((r['ep'], r['ref_digest'], r['lib']), r)
out = dict(shift={}, quat={}, rest={})
for (ep, rd, lib), r in sorted(ref1.items()):
    names = M.gt(ep)[0]
    fr, sim, ref, _, _ = M.read_rollout(f"{M.SP}/store/{r['path']}", names)
    out['shift'][f'ep{ep} {rd[:6]} {lib}'] = {s: M.registered(ep, lib, ref, fr, gt_shift=s)[0] for s in (-2, -1, 0, 1, 2)}
    print(ep, rd[:6], lib, out['shift'][f'ep{ep} {rd[:6]} {lib}'], flush=True)
# quaternion order probe on one reference per episode
done = set()
for (ep, rd, lib), r in sorted(ref1.items()):
    if ep in done:
        continue
    done.add(ep); names, fidx, G = M.gt(ep)
    fr, sim, ref, _, _ = M.read_rollout(f"{M.SP}/store/{r['path']}", names)
    good = M.registered(ep, lib, ref, fr)[0]
    G2 = G.copy(); G2[..., 3:] = G[..., [6, 3, 4, 5]]          # wrong: treat stored w,x,y,z as x,y,z,w
    M._GT[ep] = (names, fidx, G2)
    bad = M.registered(ep, lib, ref, fr)[0]
    M._GT[ep] = (names, fidx, G)
    out['quat'][ep] = dict(R_w_first=good, R_if_read_xyzw=bad)
    print('quat', ep, good, bad, flush=True)
# H-rest direct check: one high-S own-mesh rollout per named episode
for ep, obj in ((11, 'blue_cup'), (12, 'plastic_dish_rack'), (31, 'plastic_dish_rack'), (26, 'plastic_dish_rack'), (21, 'water_pitcher')):
    cand = sorted([r for r in rows if r['ep'] == ep], key=lambda r: -r['S'])[:1]
    if not cand:
        continue
    r = cand[0]; names, fidx, G = M.gt(ep); b = names.index(obj)
    fr, sim, ref, _, _ = M.read_rollout(f"{M.SP}/store/{r['path']}", names)
    et = M.registered(ep, r['lib'], sim, fr, return_err=True)[:, b]
    er = M.registered(ep, r['lib'], ref, fr, return_err=True)[:, b]
    gt = G[np.searchsorted(fidx, fr)]
    disp = lambda X: np.linalg.norm(X[:, b, :3] - X[:1, b, :3], axis=-1) * 100
    ang = lambda X: np.degrees(2 * np.arccos(np.clip(np.abs(np.sum(X[:, b, 3:] * X[:1, b, 3:], -1)), 0, 1)))
    out['rest'][f'ep{ep} {obj}'] = dict(path=r['path'], S=r['S'], T=r['T'], T_obj=r['T_obj'][obj], R_obj=r['R_obj'][obj],
                                        S_obj=r['S_obj'][obj],
                                        truth_disp_cm_max=round(float(disp(gt).max()), 2), truth_rot_deg_max=round(float(ang(gt).max()), 1),
                                        ref_disp_cm_max=round(float(disp(ref).max()), 2), ref_rot_deg_max=round(float(ang(ref).max()), 1),
                                        sim_disp_cm_max=round(float(disp(sim).max()), 2), sim_rot_deg_max=round(float(ang(sim).max()), 1),
                                        e_sim_truth_cm=[round(float(np.mean(et)) * 100, 2), round(float(np.max(et)) * 100, 2)],
                                        e_ref_truth_cm=[round(float(np.mean(er)) * 100, 2), round(float(np.max(er)) * 100, 2)])
    print('rest', ep, obj, out['rest'][f'ep{ep} {obj}'], flush=True)
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'check_frames.json'), 'w'), indent=1)
