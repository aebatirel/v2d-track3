"""debug (analysis only): compare tracker-associated observations with GT-projected markers (VO cams + Treg^-1 GT)."""
import sys, json, numpy as np
sys.path.insert(0, '/Users/aebatirel/Documents/Code/v2d-research/work/17')
import lib17 as L, det17lib as D
from scipy.spatial.transform import Rotation as Rot, Slerp
fn, oi = sys.argv[1], int(sys.argv[2]); ep = int(fn.split('trk_')[1].split('_')[0]); z = np.load(fn)
n = str(z['objs'][oi]); gt = L.load_gt(ep); j = gt['names'].index(n); Ti = np.linalg.inv(np.array(json.load(open(f'out/reg2_{ep}.json'))['Treg']))
VO = np.load(f'out/vo_public_{ep}.npy'); T = len(VO); sy = json.load(open(f'out/sync_{ep}.json')); DELTA = sy['delta']; KA = int(round(DELTA))
Tba = L.ext('a').copy(); Tba[:3, :3] = Rot.from_rotvec(sy['drot']).as_matrix() @ Tba[:3, :3]; Tbc = L.ext('c'); sl = Slerp(np.arange(T), Rot.from_matrix(VO[:, :3, :3]))
def vo_at(tau):
    tau = float(np.clip(tau, 0, T - 1)); i = min(int(np.floor(tau)), T - 2); f = tau - i
    M = np.eye(4); M[:3, :3] = sl([tau]).as_matrix()[0]; M[:3, 3] = (1 - f) * VO[i, :3, 3] + f * VO[i + 1, :3, 3]; return M
def cam_pose(t, c):
    P = vo_at(t + KA - DELTA) @ Tba if c == 'a' else (VO[t] if c == 'b' else VO[t] @ Tbc); return P[:3, :3], P[:3, 3]
M = np.array([q['c'] for q in L.CAT[n]]); O = z['obslog']; O = O[O[:, 1] == oi]
ts = [int(x) for x in sys.argv[3].split(',')] if len(sys.argv) > 3 else sorted(set(O[:, 0].astype(int)))[:6]
for t in ts:
    for c in 'abc':
        tau = t - 0.5 - ((KA - DELTA) * -1 if c == 'a' else 0)
        tau = t - 0.5 + (KA - DELTA if c == 'a' else 0)
        Rm, tm = D.gt_interp(gt, j, tau); X = (M @ Rm.T + tm) @ Ti[:3, :3].T + Ti[:3, 3]
        uvg, _ = L.project(X, *cam_pose(t, c), c, own=True)
        Re, te = z[f'R_{oi}'][t], z[f't_{oi}'][t]; uve, _ = L.project(M @ Re.T + te, *cam_pose(t, c), c, own=True)
        oo = O[(O[:, 0] == t) & (O[:, 2] == 'abc'.index(c))]
        s = ' '.join(f'k{int(o[3])}:obs({o[4]:.0f},{o[5]:.0f}) gt({uvg[int(o[3]),0]:.0f},{uvg[int(o[3]),1]:.0f}) d{np.hypot(o[4]-uvg[int(o[3]),0], o[5]-uvg[int(o[3]),1]):.1f}' for o in oo)
        print(t, c, s, '| est-gt px per marker', np.round(np.hypot(*(uve - uvg).T), 1))
