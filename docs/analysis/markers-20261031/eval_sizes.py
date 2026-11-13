"""GT-free size of what the (FAILED, not adopted) marker layer would change on the eval spoon tracks.
Per spoon episode: fix coverage, correction size (median, frame 0), roll about the handle axis at frame 0 (body z),
static-segment vote decisions; eval 16 frames >= 120 also: the correction's component along the table normal (our own
mkref table frame; negative = moves the spoon down). Inputs: our tracks, census fix files, table frames. No GT.
Usage: python eval_sizes.py EPS(comma) OUT_JSON
"""
import json, os, sys
import numpy as np
from scipy.spatial.transform import Rotation as Rot
sys.path.insert(0, os.path.dirname(__file__))
import mlib, correct

ANCHOR = {32, 33, 35, 36, 37}


def table(e):
    for v in ('perc2mck', 'perc2mcks'):
        p = f'{mlib.S}/eg/dl/runs/{mlib.PERC_EVAL[e]}/refs/{v}/ep{e}/table_frame.npz'
        if os.path.exists(p):
            t = np.load(p); return t['plane_n'].astype(float), float(t['plane_d'])


out = {}
for e in [int(x) for x in sys.argv[1].split(',')]:
    F = np.load(f'{mlib.S}/mk/scan/fix_eval{e}_wooden_spoon.npz')
    P = np.load(mlib.poses_path('eval', e)); T = P['cam_T_wooden_spoon'].astype(float)[:len(F['n'])]
    W = P['world_T_cam'].astype(float)[:len(F['n'])]
    Tc, C, info = correct.correct(T, F['n'], F['fix'], F['rest'])
    tw = np.array([correct.twist_deg(c[:3, :3], np.array([0, 0, 1.0])) for c in C])
    dpos = (W @ Tc)[:, :3, 3] - (W @ T)[:, :3, 3]                                  # world-frame shift of the origin
    r = dict(anchor=e in ANCHOR, N=len(T), fix2_share=round(float((F['n'] >= 2).mean()), 3),
             fix3_share=round(float((F['n'] >= 3).mean()), 3), accepted=info['accepted'],
             corr_mm_med=round(float(np.median(np.linalg.norm(C[:, :3, 3], axis=1)) * 1000), 1),
             corr_deg_med=round(float(np.median(np.degrees(Rot.from_matrix(C[:, :3, :3]).magnitude()))), 2),
             f0_mm=round(float(np.linalg.norm(C[0, :3, 3]) * 1000), 1),
             f0_deg=round(float(np.degrees(Rot.from_matrix(C[0, :3, :3]).magnitude())), 2), f0_roll_deg=round(float(tw[0]), 2),
             votes=[(s['a'], s['b'], s['decision'], s.get('corr_deg')) for s in info['segs']])
    if e == 16:
        n, d = table(e); m = np.arange(len(T)) >= 120
        dz = dpos[m] @ n
        r['f120_fix2_share'] = round(float((F['n'][m] >= 2).mean()), 3)
        r['f120_corr_mm_med'] = round(float(np.median(np.linalg.norm(C[m, :3, 3], axis=1)) * 1000), 1)
        r['f120_dz_mm'] = dict(median=round(float(np.median(dz) * 1000), 1), p10=round(float(np.percentile(dz, 10) * 1000), 1),
                               p90=round(float(np.percentile(dz, 90) * 1000), 1))
        V = np.asarray(__import__('trimesh').load('/home/user/v2d-track3/meshes/library_v3/wooden_spoon.glb', force='mesh').vertices)
        low = lambda TT: np.array([((V @ (W[t] @ TT[t])[:3, :3].T + (W[t] @ TT[t])[:3, 3]) @ n + d).min() for t in np.nonzero(m)[0]])
        r['f120_lowest_point_above_table_mm'] = dict(track=round(float(np.median(low(T)) * 1000), 1),
                                                     corrected=round(float(np.median(low(Tc)) * 1000), 1))
    out[str(e)] = r
    print(e, json.dumps(r))
json.dump(out, open(sys.argv[2], 'w'), indent=1)
