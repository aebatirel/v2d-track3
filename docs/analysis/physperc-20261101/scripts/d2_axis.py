"""D2 (DIAGNOSTIC, reads public mocap): physics prior = revolution axis of our mesh is vertical at rest.
Per object at f0 with a revolution fit (rms <= 4 mm): tilt error of the fused down axis vs the truth for W in WS,
and the same for the T1 stable-facet prior. Gate as T1 (hand > 50 mm, lowest point in [-20, +10] mm, match <= 6 deg).
Usage: python -I d2_axis.py SCRATCH OUT_JSON"""
import sys, json, numpy as np
S, OUT = sys.argv[1:3]; sys.path.insert(0, f'{S}/kit/v2d_submission_kit')
sys.path.insert(0, '/home/user/v2d-track3/docs/analysis/physperc-20261101/scripts')
from v2dlb import track3_pose as T3; from v2dlb.mesh_budget import budget_mesh; from v2dlb.object_mesh import _surface_moments
import physlib as PL
SYM = {'beige_cup', 'blue_cup', 'white_pot_lid'}
ang = lambda a, b: float(np.degrees(np.arccos(np.clip(np.dot(a, b) / np.linalg.norm(a) / np.linalg.norm(b), -1, 1))))
def sl(a, b, w):
    a = a / np.linalg.norm(a); b = b / np.linalg.norm(b); th = np.arccos(np.clip(a @ b, -1, 1))
    return a if th < 1e-9 else (np.sin((1 - w) * th) * a + np.sin(w * th) * b) / np.sin(th)
WS = [0, 0.25, 0.5, 0.6, 0.75, 0.9, 1.0]
D1 = json.load(open('/home/user/v2d-track3/docs/analysis/physperc-20261101/diag/d1_tilt_9a.json'))
out = {}
for e, objs in D1.items():
    names = sorted(objs, key=lambda k: objs[k]['slot']); anc = next((k for k in names if k not in SYM), names[0])
    for n, D in objs.items():
        mp = f'{S}/mesh9a/{n}.glb'
        a, rms, _ = PL.revolution_axis(mp)
        if rms > 0.004:
            continue
        sv, sf = PL.load_vf(PL.scan_path(S, n)); c, _ = _surface_moments(sv, sf)
        ca, B = T3._register_object_body(budget_mesh(mp, 4096, 4096), (sv, sf), c, 1_000_003 * int(e) + 101 * D['slot'])
        gt = np.array(D['g_true']); go = np.array(D['g_ours'])
        gb = B.T @ go                                   # tracker down in our body frame
        ab = a if a @ gb > 0 else -a
        match = ang(gb, ab)
        ok = D['hand_mm'] > 50 and -20 <= D['gap_mm'] <= 10 and match <= 6
        out[f'{e}:{n}'] = dict(anchor=n == anc, gate=ok, match=round(match, 2), rms_mm=round(rms * 1000, 2),
                               e_axis=[round(ang(B @ sl(gb, ab, w), gt), 3) for w in WS],
                               e_facet=[round(ang(sl(go, np.array(D['g_prior']), w), gt), 3) for w in WS])
        print(e, n, out[f'{e}:{n}'], flush=True)
for sel in ('anchor', 'all'):
    X = [v for v in out.values() if v['gate'] and (sel == 'all' or v['anchor'])]
    A = np.array([v['e_axis'] for v in X]); F = np.array([v['e_facet'] for v in X])
    print(sel, len(X), 'W', WS, '\n  axis  mean', np.round(A.mean(0), 2), '\n  facet mean', np.round(F.mean(0), 2))
json.dump(dict(WS=WS, objects=out), open(OUT, 'w'), indent=1)
