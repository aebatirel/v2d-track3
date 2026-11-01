"""ORACLE DIAGNOSTIC, POST HOC (public only): where the thin-object tracker errors are, relative to S10's holds and to
hand measurement. Per frame (* convention, Po S2 track): ADD vs mocap; in an S10 hold or not; nearest hand measured.
Usage: python -I hp_where.py"""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hp_score as HS  # noqa: E402
XF = HS.XF
res = {}
for ep in (18, 31, 39, 40):
    XF.kit(HS.KIT)
    names, gt = XF.mocap(HS.T3D, ep, None)
    H = [XF.host_geometry(HS.T3D, n, s) for s, n in enumerate(names)]
    REG = [XF.reg_of_X(np.asarray(HS.XG[n]['X_scan_T_lib']), H[s]['anchor']) for s, n in enumerate(names)]
    V = np.load(f'{HS.W}/runs/Po/S2/ep{ep}/poses_world_vo.npz')
    T = {n: V[n].astype(np.float64) for n in names}
    N = len(T[names[0]])
    e = HS.per_frame(names, T, {n: gt[n][:N] for n in names}, H, REG)
    aux = np.load(f'{HS.W}/runs/Po/S10g/ep{ep}/pose_opt_aux.npz')
    Hd = np.load(f'{HS.ARMS["Po"]}/ep{ep}/hands_refined.npz')
    anyh = Hd['measured_left'] | Hd['measured_right']
    for s, n in enumerate(names):
        if n not in ('mini_sweeper', 'mini_dust_pan'):
            continue
        ec = e[s] * 100
        hold = aux[f'S10_{n}_side'] >= 0
        bad = ec > 3.0
        r = dict(frames=N, err_med_cm=round(float(np.median(ec)), 2), frames_err_gt3cm=int(bad.sum()),
                 of_which_in_hold=int((bad & hold).sum()), of_which_no_hand_measured=int((bad & ~anyh).sum()),
                 err_med_in_hold=round(float(np.median(ec[hold])), 2) if hold.any() else None,
                 err_med_out_hold=round(float(np.median(ec[~hold])), 2),
                 worst_10f_blocks=[(int(i), round(float(ec[i:i + 10].max()), 1)) for i in range(0, N, 10) if ec[i:i + 10].max() > 3])
        res[f'ep{ep} {n}'] = r
        print(f'ep{ep} {n}', json.dumps(r))
json.dump(res, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'results', 'hp_where.json'), 'w'), indent=1)
