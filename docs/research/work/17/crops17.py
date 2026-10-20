"""Crop sheet of z-visible markers for visual inspection. usage: crops17.py ep cam seg(rest|held|carried|any) n [seed] [gtshift]
Crops: 5 x rpx half-size around the projected centre, 80x80, circle = projected sphere. Label: t obj k rpx speed.
gtshift (frames, b/c clock; cam a adds -delta): GT pose interpolated at t + shift for the projection."""
import sys, json, numpy as np, cv2
import lib17 as L, seg17
from scipy.spatial.transform import Rotation as Rot, Slerp
ep, c, sg, n = int(sys.argv[1]), sys.argv[2], sys.argv[3], int(sys.argv[4]); seed = int(sys.argv[5]) if len(sys.argv) > 5 else 0
TS = int(__import__("os").environ.get("TS", 128))
NC = 8
shift = float(sys.argv[6]) if len(sys.argv) > 6 else 0.0
z = np.load(f'out/census_{ep}.npz'); gt = L.load_gt(ep); seg = seg17.segments(gt)[0]; ci = 'abc'.index(c)
RG = json.load(open(f'out/reg2_{ep}.json')); cams = RG['cams' if c == 'a' else f'cams_{c}']
sh = shift - (RG['delta'] if c == 'a' else 0.0)
def gt_pose(j, tau):
    T = len(gt['t']); tau = float(np.clip(tau, 0, T - 1)); i = min(int(tau), T - 2); f = tau - i
    R = Slerp([0, 1], Rot.from_matrix(gt['R'][i:i + 2, j]))([f]).as_matrix()[0]; return R, (1 - f) * gt['t'][i, j] + f * gt['t'][i + 1, j]
cand = []
T, N, KM = z['VIS'].shape[0], z['VIS'].shape[2], z['VIS'].shape[3]
for t in range(T):
    for j in range(N):
        if sg != 'any' and ['rest', 'held', 'carried'][seg[t, j]] not in ({'moving': ('held', 'carried')}.get(sg, (sg,))): continue
        for k in range(KM):
            if z['VIS'][t, ci, j, k]: cand.append((t, j, k))
rng = np.random.default_rng(seed); sel = sorted([cand[i] for i in rng.choice(len(cand), min(n, len(cand)), replace=False)])
vid = L.Video(ep, c); tiles = []
for t, j, k in sel:
    im = vid.get(t); R, C = np.array(cams[t]['Rwc']), np.array(cams[t]['C'])
    Rj, tj = gt_pose(j, t + sh); X = np.array(L.CAT[gt['names'][j]][k]['c']) @ Rj.T + tj
    uv, zz = L.project(X[None], R, C, c, own=True); u, v = uv[0]; r = L.cam(c)[0][0, 0] * L.CAT[gt['names'][j]][k]['r'] / zz[0]
    h = max(int(5 * r), 12); pad = cv2.copyMakeBorder(im, h, h, h, h, cv2.BORDER_CONSTANT)
    cr = pad[int(v):int(v) + 2 * h, int(u):int(u) + 2 * h]; s = TS / (2 * h); cr = cv2.resize(cr, (TS, TS))
    cv2.circle(cr, (TS // 2, TS // 2), max(int(r * s), 1), (0, 0, 255), 1)
    cv2.putText(cr, f'#{len(tiles)} {t} {gt["names"][j][:5]}{gt["names"][j][-3:]}{k}', (1, 9), cv2.FONT_HERSHEY_PLAIN, 0.7, (0, 255, 255), 1)
    cv2.putText(cr, f'r{r:.0f} s{z["SPD"][t, ci, j, k]:.0f}', (1, TS - 3), cv2.FONT_HERSHEY_PLAIN, 0.7, (0, 255, 255), 1)
    tiles.append(cr)
while len(tiles) % NC: tiles.append(np.zeros((TS, TS, 3), np.uint8))
sheet = np.vstack([np.hstack(tiles[i:i + NC]) for i in range(0, len(tiles), NC)])
out = f'out/crops_{ep}_{c}_{sg}_{seed}.jpg'; cv2.imwrite(out, sheet); print(out, len(cand), 'candidates')
