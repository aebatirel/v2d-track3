"""ORACLE DISPLAY (public ep31, cam a): sweeper and rack at mocap (green), P_s (magenta) and P_o (red; scan meshes at
X*_geom) on f0 / f20 / f100 / f260 crops. Mocap is mapped into the perception world by a rigid fit of the P_s RACK track
to the mocap rack over all frames (median residual 0.29 cm). Display only. Usage: python -I overlay31.py SCRIPTS OUT_PNG"""
import sys, json, numpy as np, cv2, trimesh
sys.path.insert(0, sys.argv[1]); import diag31 as D
XF = D.XF
names, gt, N, tr = D.load_tracks()
H = [XF.host_geometry(D.T3D, n, s) for s, n in enumerate(names)]
rk = names.index('plastic_dish_rack')
pts = H[rk]['points'][::10] + H[rk]['anchor']
P = np.concatenate([pts @ tr['Ps'][names[rk]][i][:3, :3].T + tr['Ps'][names[rk]][i][:3, 3] for i in range(N)])
Q = np.concatenate([pts @ gt[names[rk]][i][:3, :3].T + gt[names[rk]][i][:3, 3] for i in range(N)])
mp, mq = P.mean(0), Q.mean(0); U, _, Vt = np.linalg.svd((P - mp).T @ (Q - mq))
Rm = Vt.T @ np.diag([1, 1, np.sign(np.linalg.det(Vt.T @ U.T))]) @ U.T; tm = mq - Rm @ mp
G = np.eye(4); G[:3, :3] = Rm.T; G[:3, 3] = -Rm.T @ tm
hz = np.load(f'{D.REF}/hands_refined.npz', allow_pickle=True)
Ka, Da, Tra, aoff = hz['Ka'], hz['Da'], hz['T_rect_a'], int(hz['a_offset'])
W = np.load(f'{D.RUN}/perc2/poses.npz')['world_T_cam'].astype(float)
sp = {n: trimesh.sample.sample_surface(trimesh.load(XF.scan_path(D.T3D, n), force='mesh'), 2500 if n == names[rk] else 1500, seed=2)[0] for n in names}
VID = f'{D.S}/hfds/track_3/public/videos/chunk-000/observation.images.ego_cam_a/episode_000031.mp4'
cap = cv2.VideoCapture(VID); fr = []
while True:
    ok, f = cap.read()
    if not ok: break
    fr.append(f)
dj = json.load(open(f'{D.S}/leak/diag_31/diag31.json'))
def proj(Tw, n, i):
    X = sp[n] @ Tw[:3, :3].T + Tw[:3, 3]; A = np.linalg.inv(W[i] @ Tra); Xa = X @ A[:3, :3].T + A[:3, 3]
    uv, _ = cv2.projectPoints(Xa.reshape(-1, 1, 3), np.zeros(3), np.zeros(3), Ka, Da); return uv.reshape(-1, 2).astype(int)
tiles = []
for i in (0, 20, 100, 260):
    img = fr[i + aoff].copy()
    for Tw_of, col in ((lambda n: G @ gt[n][i], (0, 220, 0)), (lambda n: tr['Ps'][n][i], (255, 0, 255)), (lambda n: tr['Po'][n][i], (0, 0, 255))):
        for n in names:
            for u, v in proj(Tw_of(n), n, i):
                if 0 <= u < img.shape[1] and 0 <= v < img.shape[0]:
                    cv2.circle(img, (u, v), 2 if n != names[rk] else 1, col, -1)
    c = proj(G @ gt['mini_sweeper'][i], 'mini_sweeper', i).mean(0).astype(int)
    x0, y0 = max(0, c[0] - 330), max(0, c[1] - 230); crop = cv2.resize(img[y0:y0 + 460, x0:x0 + 660], (660, 460))
    row = dj['frames'][i]
    t = (f"f{i}  sweeper kit-ADD Po {row['mini_sweeper']['Po_kit']['add']:.1f} Ps {row['mini_sweeper']['Ps_kit']['add']:.1f} | "
         f"rack Po {row['plastic_dish_rack']['Po_kit']['add']:.1f} Ps {row['plastic_dish_rack']['Ps_kit']['add']:.1f} cm")
    cv2.rectangle(crop, (0, 0), (660, 24), (0, 0, 0), -1); cv2.putText(crop, t, (5, 17), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
    tiles.append(crop)
g = np.vstack([np.hstack(tiles[:2]), np.hstack(tiles[2:])])
cv2.rectangle(g, (0, g.shape[0] - 26), (g.shape[1], g.shape[0]), (0, 0, 0), -1)
cv2.putText(g, 'ep31 cam a, public, ORACLE DIAGNOSTIC: green = mocap (via P_s rack fit), magenta = P_s, red = P_o', (5, g.shape[0] - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
cv2.imwrite(sys.argv[2], g); print('wrote', sys.argv[2], len(fr), 'frames')
