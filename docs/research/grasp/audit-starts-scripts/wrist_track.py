"""Hand tracking in the zero-action trace vs the DESIGNED grasp-lock hand (ref_gl, before ILC): wrist position error
(cm) and rotation error (deg) per hold window, and the object's pose in the designed hand frame vs in the simulated
hand frame (is the object where the design put it relative to the palm?). No ground truth.
Usage: wrist_track.py EP TRACE GLKIND(ref_gl|ref_gl_r1)"""
import sys, json, glob, numpy as np
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from common import *
ep, trn, kind = int(sys.argv[1]), sys.argv[2], sys.argv[3]
dg = load_ref(ref_path(ep, kind)); names = dg['names']
import pyarrow.parquet as pq
t = pq.read_table(ref_path(ep, kind)); T = dg['T']
WQ = {s: np.array(t.column(f'robot_{s}_wrist_wxyz')[0].as_py(), float).reshape(T, 4)[:, [1, 2, 3, 0]] for s in ('left', 'right')}
gl = json.load(open(glob.glob(f'{run_dir(ep)}/refs/glock/ep{ep}/processed/*/*/{kind}_grasp_lock.json')[0]))
Q, L, F = load_trace(f'{run_dir(ep)}/results/glock_public/ep{ep}/{trn}.npz'); n = min(len(Q), T)
for ph in gl['phases']:
    s, o = ph['hand'], ph['object']; ci = L.index(f'{s}_sharpa_wave/{s}_hand_C_MC'); oi = obj_index(L, o); j = names.index(o)
    a, b = ph['hold_from'], min(ph['end'], n - 1); c = min(ph['grasp_frame'] + 10, b)
    ep_ = 100 * np.linalg.norm(Q[:n, ci, :3] - dg[f'wpos_{s}'][:n], axis=1); er = rot_deg(Q[:n, ci, 3:7], WQ[s][:n])
    # object in hand frame: designed (ref object in ref wrist frame) vs simulated
    rel_d = R.from_quat(WQ[s][:n]).inv().apply(dg['OP'][:n, j] - dg[f'wpos_{s}'][:n])
    rel_s = R.from_quat(Q[:n, ci, 3:7]).inv().apply(Q[:n, oi, :3] - Q[:n, ci, :3])
    dr = 100 * np.linalg.norm(rel_s - rel_d, axis=1)
    rq_d = R.from_quat(WQ[s][:n]).inv() * R.from_quat(dg['OQ'][:n, j]); rq_s = R.from_quat(Q[:n, ci, 3:7]).inv() * R.from_quat(Q[:n, oi, 3:7])
    drr = np.degrees((rq_s * rq_d.inv()).magnitude())
    w = lambda x, aa, bb: round(float(np.mean(x[aa:bb + 1])), 1)
    print(json.dumps(dict(hand=s, obj=o, hold=[a, b], close=c, wrist_err_cm_approach=w(ep_, max(0, a - 15), a), wrist_err_cm_hold=w(ep_, c, b), wrist_err_deg_hold=w(er, c, b),
                          obj_in_hand_err_at_close_cm=round(float(dr[c]), 1), obj_in_hand_err_at_close_deg=round(float(drr[c]), 1),
                          obj_in_hand_err_hold_cm=w(dr, c, b), obj_in_hand_err_hold_deg=w(drr, c, b), obj_in_hand_err_end_cm=round(float(dr[b]), 1))))
