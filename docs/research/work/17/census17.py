"""Stage B census: z-buffer visibility of GT-posed marker spheres per frame / object / camera, with segment type.
Cameras: stage-A out/reg2_<ep>.json (cams a, b, c in the mocap world). Visibility: lib17.visibility (splat z-buffer of all
GT-posed scans; hands / table / room are NOT modelled -> this is an upper bound), plus centre inside the image by >= 1 radius.
Segments from GT kinematics per object: speed v and angular rate w over +-2 frames; 'static' = v < 5 mm/s & w < 0.5 deg/s;
rest = static run >= 10 frames (0.5 s); in-hand = not rest; carried = in-hand & v >= 0.05 m/s; held = in-hand & v < 0.05 m/s.
usage: census17.py ep    -> out/census_<ep>.npz"""
import sys, os, json, numpy as np, time
from scipy.spatial.transform import Rotation as Rot
import lib17 as L
ep = int(sys.argv[1]); t0 = time.time()
gt = L.load_gt(ep); SRC = os.environ.get('CAMSRC', 'reg2'); RG = json.load(open(f'out/{SRC}_{ep}.json')); N = len(gt['names'])
cams = {'a': RG['cams'], 'b': RG['cams_b'], 'c': RG['cams_c']}; T = len(cams['a'])
KM = max(len(L.CAT.get(n, [])) for n in gt['names'])
# --- segments ---
v = np.zeros((T, N)); w = np.zeros((T, N))
for j in range(N):
    for t in range(T):
        a, b = max(t - 2, 0), min(t + 2, T - 1); dt = max(b - a, 1) / 20.0
        v[t, j] = np.linalg.norm(gt['t'][b, j] - gt['t'][a, j]) / dt
        w[t, j] = np.degrees(np.linalg.norm(Rot.from_matrix(gt['R'][b, j] @ gt['R'][a, j].T).as_rotvec())) / dt
st = (v < 0.005) & (w < 0.5); seg = np.ones((T, N), int)
for j in range(N):
    t = 0
    while t < T:
        if st[t, j]:
            e = t
            while e < T and st[e, j]: e += 1
            if e - t >= 10: seg[t:e, j] = 0
            t = e
        else: t += 1
seg[(seg == 1) & (v >= 0.05)] = 2
# --- visibility ---
shp = (T, 3, N, KM)
VIS = np.zeros(shp, bool); ZV = np.zeros(shp, bool); INI = np.zeros(shp, bool); UV = np.full(shp + (2,), np.nan)
Z = np.full(shp, np.nan); RPX = np.full(shp, np.nan); FR = np.zeros(shp); SPD = np.full(shp, np.nan)
for t in range(T):
    for ci, c in enumerate('abc'):
        R, C = np.array(cams[c][t]['Rwc']), np.array(cams[c][t]['C']); W, H = L.cam(c)[2]
        vis = L.visibility(gt, t, R, C, c, own=True)
        for j in range(N):
            if vis[j] is None: continue
            q = vis[j]; nk = len(q['vis'])
            ini = (q['z'] > 0.05) & (q['uv'][:, 0] >= q['rpx']) & (q['uv'][:, 0] < W - q['rpx']) & (q['uv'][:, 1] >= q['rpx']) & (q['uv'][:, 1] < H - q['rpx'])
            ZV[t, ci, j, :nk] = q['vis']; INI[t, ci, j, :nk] = ini; VIS[t, ci, j, :nk] = q['vis'] & ini
            UV[t, ci, j, :nk] = q['uv']; Z[t, ci, j, :nk] = q['z']; RPX[t, ci, j, :nk] = q['rpx']; FR[t, ci, j, :nk] = q['frac']
            # image speed (own px / frame) from GT motion + camera motion, central difference
            if 0 < t < T - 1:
                pp = []
                for tt in (t - 1, t + 1):
                    R2, C2 = np.array(cams[c][tt]['Rwc']), np.array(cams[c][tt]['C'])
                    pp.append(L.project(L.markers_world(gt, tt, j), R2, C2, c, own=True)[0])
                SPD[t, ci, j, :nk] = np.linalg.norm(pp[1] - pp[0], axis=1) / 2
    if t % 50 == 0: print(f'ep {ep} t {t}/{T} {time.time()-t0:.0f}s', flush=True)
np.savez_compressed(f'out/census_{ep}.npz' if SRC == 'reg2' else f'out/census_{SRC}_{ep}.npz', VIS=VIS, ZV=ZV, INI=INI, UV=UV, Z=Z, RPX=RPX, FR=FR, SPD=SPD, seg=seg, v=v, w=w,
                    names=np.array(gt['names']), nk=np.array([len(L.CAT.get(n, [])) for n in gt['names']]),
                    small=np.array([[q['r'] < 0.005 for q in L.CAT[n]] + [False] * (KM - len(L.CAT[n])) for n in gt['names']]))
print('done', time.time() - t0)
