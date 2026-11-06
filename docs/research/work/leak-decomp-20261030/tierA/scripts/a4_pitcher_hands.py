"""ORACLE (public): A4 side check. Per hand side, during the pitcher's true motion (ep21, ep22): measured fraction and
the nearest fingertip-to-true-surface gap (cm)."""
import sys, json, numpy as np
sys.path.insert(0, '/home/user/v2d-track3/tools'); sys.path.insert(0, '/home/user/v2d-track3/pipeline')
import leak_tierA as LT, xstar_fit as XF
from scipy.spatial import cKDTree
S = sys.argv[1]; T3 = f'{S}/map/scoring/t3'; XT = '/home/user/v2d-track3/docs/research/work/leak-decomp-20261030/tierA/xstar_trk.json'
XF.kit(f'{S}/map/scoring/kit/v2d_submission_kit')
for ep in (21, 22):
    V = np.load(f'{S}/refine/in/ep{ep}/poses_world_vo.npz'); N = len(V[V.files[0]])
    names, gt = XF.mocap(T3, ep, N); Gi = np.linalg.inv(np.asarray(json.load(open(XT))['episodes'][str(ep)]['fit']['G_mocap_T_perc']))
    _, J, _ = LT.hands(f'{S}/refine/in/ep{ep}')
    for s, n in enumerate(names):
        H = XF.host_geometry(T3, n, s); mv, runs = LT.true_motion(gt[n], H['anchor']); m = np.zeros(N, bool)
        for a, b in runs: m[a:b] = True
        tree = LT.surface_tree(*H['mesh']); Pw = np.einsum('ij,tjk->tik', Gi, gt[n]); row = {}
        for sd, (jt, meas) in J.items():
            g = LT.tip_gap_cm({sd: (jt, meas)}, Pw, tree)
            mm = m & meas
            row[sd] = dict(measured_in_motion=f'{int(mm.sum())}/{int(m.sum())}', gap_median_cm=(round(float(np.median(g[mm])), 2) if mm.any() else None))
        print(f'ep{ep} {n}: {row}', flush=True)
