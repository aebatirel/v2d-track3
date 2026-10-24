"""Zero-action hold audit (no ground truth): per hold phase of the grasp-lock reference, does the hand acquire and
hold the object? Lift (sim vs ref), fraction of hold frames within 3 cm / 2 cm of the reference, object pose in the
holding hand's palm frame (slip from the closing frame), hand-object hull contact count, first frame lost (> 5 cm).
Usage: hold_audit.py EP TRACE REFKIND"""
import sys, os, json, glob, numpy as np
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from common import *

ep, trn, kind = int(sys.argv[1]), sys.argv[2], sys.argv[3]
d = load_ref(ref_path(ep, kind)); names = d['names']
glk = kind.replace('_ilc', '') + '_grasp_lock.json'
gl = json.load(open(gl_json(ep, kind.replace('_ilc', ''))))
Q, L, F = load_trace(trn if trn.endswith('.npz') else f'{run_dir(ep)}/results/glock_public/ep{ep}/{trn}.npz'); n = min(len(Q), d['T'])
HP = {s: hand_points(s, 40) for s in ('left', 'right')}
HB = {s: {b: L.index(f'{s}_sharpa_wave/{b}') for b in HP[s] if f'{s}_sharpa_wave/{b}' in L} for s in HP}
Hh = {o: Hulls(hull_path(o)) for o in names}
out = []
for ph in gl['phases']:
    o, s = ph['object'], ph['hand']; j = names.index(o); oi = obj_index(L, o); pi = L.index(f'{s}_sharpa_wave/{s}_hand_C_MC')
    a, b = ph['hold_from'], min(ph['end'], n - 1); close = ph['grasp_frame'] + 10 if ph.get('grasp_frame') else a + 10
    P, Qo = Q[:n, oi, :3], Q[:n, oi, 3:7]
    e = 100 * np.linalg.norm(P - d['OP'][:n, j], axis=1); er = rot_deg(Qo, d['OQ'][:n, j])
    lift = 100 * (P[:, 2] - P[0, 2]); rlift = 100 * (d['OP'][:n, j, 2] - d['OP'][0, j, 2])
    # object in palm frame
    Pp, Qp = Q[:n, pi, :3], Q[:n, pi, 3:7]
    rel = R.from_quat(Qp).inv().apply(P - Pp); relq = (R.from_quat(Qp).inv() * R.from_quat(Qo))
    c = min(close, b)
    slip = 100 * np.linalg.norm(rel[a:b + 1] - rel[c], axis=1); slipr = np.degrees((relq[a:b + 1] * relq[c].inv()).magnitude())
    # contacts: number of hand sample points within 3 mm of / inside the hulls over the hold
    ncont = []
    for t in range(a, b + 1, 5):
        Pw = np.concatenate([local_to_world(HP[s][bb], Q[t, i, :3], Q[t, i, 3:7]) for bb, i in HB[s].items()])
        dep, outd = Hh[o].depth(world_to_local(Pw, P[t], Qo[t]))
        ncont.append(int(((dep > 0) | (outd < 0.003)).sum()))
    lost = next((t for t in range(a, b + 1) if e[t] > 5), None)
    r = dict(object=o, hand=s, hold=[a, b], close=c, err_at_hold_start_cm=round(float(e[a]), 1), deg_at_hold_start=round(float(er[a]), 1),
             sim_lift_max=round(float(lift[a:b + 1].max()), 1), ref_lift_max=round(float(rlift[a:b + 1].max()), 1),
             in3=round(float((e[a:b + 1] < 3).mean()), 2), in2=round(float((e[a:b + 1] < 2).mean()), 2), mean_err_cm=round(float(e[a:b + 1].mean()), 1),
             mean_err_deg=round(float(er[a:b + 1].mean()), 1), slip_cm_max=round(float(slip.max()), 1), slip_deg_max=round(float(slipr.max()), 1),
             slip_cm_p50=round(float(np.median(slip)), 1), contact_pts_median=int(np.median(ncont)), lost_at=lost,
             replan=ph.get('replan'), wrap=ph.get('wrap'), fingers_on=ph.get('fingers_on'), grasp_gap_mm=ph.get('grasp_gap_mm'),
             joints_at_limit=ph.get('joints_at_limit_after_squeeze'), human_hold_axis_cm=ph.get('human_hold_axis_cm'))
    out.append(r); print(json.dumps(r))
json.dump(out, open(f"{W}/out/hold_audit_ep{ep}_{os.path.basename(trn).replace('.npz', '')}.json", 'w'), indent=1)
