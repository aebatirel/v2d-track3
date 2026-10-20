"""Coarse cameras for eps without a marker registration: note-11 s24 frame-0 cam_a pose (~5-15 deg, ~5-15 cm off) carried by
the stereo VO (cam a with the sync delta). Writes out/reg2s24_<ep>.json with the reg2 keys (cams, cams_b, cams_c, delta).
For a geometric (self-occlusion) census only [E]. usage: mkcams_s24.py ep"""
import sys, json, numpy as np
from scipy.spatial.transform import Rotation as Rot, Slerp
import lib17 as L
ep = int(sys.argv[1]); VO = np.load(f'out/vo_public_{ep}.npy'); T = len(VO)
sy = json.load(open(f'out/sync_{ep}.json')); DELTA = sy['delta']
Tba = L.ext('a').copy(); Tba[:3, :3] = Rot.from_rotvec(sy['drot']).as_matrix() @ Tba[:3, :3]; Tbc = L.ext('c')
sl = Slerp(np.arange(T), Rot.from_matrix(VO[:, :3, :3]))
def vo_at(tau):
    tau = float(np.clip(tau, 0, T - 1)); i = min(int(np.floor(tau)), T - 2); f = tau - i
    M = np.eye(4); M[:3, :3] = sl([tau]).as_matrix()[0]; M[:3, 3] = (1 - f) * VO[i, :3, 3] + f * VO[i + 1, :3, 3]; return M
R0, C0 = L.s25_cam(ep); Twa0 = np.eye(4); Twa0[:3, :3] = R0; Twa0[:3, 3] = C0
Treg = Twa0 @ np.linalg.inv(Tba) @ np.linalg.inv(vo_at(0 - DELTA))
pa = [Treg @ vo_at(t - DELTA) @ Tba for t in range(T)]; pb = [Treg @ VO[t] for t in range(T)]; pc = [P @ Tbc for P in pb]
f = lambda P: dict(Rwc=P[:3, :3].tolist(), C=P[:3, 3].tolist())
json.dump(dict(ep=ep, delta=DELTA, Treg=Treg.tolist(), cams=[f(P) for P in pa], cams_b=[f(P) for P in pb], cams_c=[f(P) for P in pc], src='s24+VO'),
          open(f'out/reg2s24_{ep}.json', 'w'))
print('ok', ep, T)
