"""Stage B gap 1: does the scan identity cue of the beige @171 marker (lower, almost no mount) show in video?
PUBLIC ep 11 frame 0, cam a. Analysis-only GT use: camera = stored 6-point PnP on GT-placed scan markers (pnp_check)."""
import numpy as np, json, sys, cv2
W = '/Users/aebatirel/Documents/Code/v2d-research/work/12'; sys.path.insert(0, W)
from pnp_check import variant, world_markers, solve, T_of
from selfsim import good_markers
from meshlib import load
import pandas as pd
VID = '/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public/videos/chunk-000/observation.images.ego_cam_a/episode_000011.mp4'
cap = cv2.VideoCapture(VID); ok, im = cap.read()
K, D = variant(False)
uv = np.array([[795, 988], [1044, 1022], [950, 1290], [1260, 1059], [1479, 984], [1273, 888]], float)
X, lab, objs = world_markers(11, 0, ['blue_cup', 'beige_cup'])
err, (perm, rv, tv, e) = solve(uv, X, K, D)
AX = json.load(open(W + '/out/axes2.json')); MK = json.load(open(W + '/out/markers2.json'))
out = {'cam_err_px': err}
crops = []
for name in ['beige_cup', 'blue_cup']:
    p = np.array(AX[name]['p']); a = np.array(AX[name]['a']); a /= np.linalg.norm(a)
    g, _ = load(name); V = np.asarray(g.vertices)
    hv = (V - p) @ a; h_rim = np.percentile(hv, 99.9)
    T = T_of(objs[name]['pose']); Rc = cv2.Rodrigues(rv)[0]
    for i, m in enumerate(good_markers(name)):
        d = m - p; h = d @ a; rad = d - h * a; rn = np.linalg.norm(rad); rd = rad / rn
        rim = p + h_rim * a + rd * 0.044          # outer rim top above the marker
        Pw = np.array([T[:3, :3] @ q + T[:3, 3] for q in (m, rim)])
        pr = cv2.projectPoints(Pw, rv, tv, K, D)[0].reshape(-1, 2)
        Zc = (Rc @ Pw[0] + tv.ravel())[2]
        diam = K[0, 0] * 0.0146 / Zc
        th = MK[name]['theta'][i]
        rec = dict(theta=round(th), h_mm=round(h * 1e3, 1), rim_minus_h_mm=round((h_rim - h) * 1e3, 1),
                   uv=pr[0].round(1).tolist(), rim_uv=pr[1].round(1).tolist(), gap_px=round(float(np.linalg.norm(pr[1] - pr[0])), 1),
                   Z_m=round(float(Zc), 3), pred_diam_px=round(float(diam), 1))
        out[f'{name}#{i}'] = rec; print(name, i, rec)
        if name == 'beige_cup':
            x, y = pr[0].astype(int); r = 60
            c = im[max(0, y - r):y + r, max(0, x - r):x + r].copy()
            c = cv2.resize(c, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
            cc = ((pr[0] - [max(0, x - r), max(0, y - r)]) * 3).astype(int); rr = ((pr[1] - [max(0, x - r), max(0, y - r)]) * 3).astype(int)
            cv2.circle(c, tuple(cc), int(diam * 1.5), (0, 0, 255), 1); cv2.drawMarker(c, tuple(rr), (0, 255, 0), cv2.MARKER_CROSS, 20, 1)
            cv2.putText(c, f'@{th:.0f} gap {rec["rim_minus_h_mm"]}mm', (5, 25), 0, 0.8, (0, 0, 255), 2)
            crops.append(cv2.resize(c, (360, 360)))
cv2.imwrite(W + '/b2/beige_id_ep11_f0.png', np.hstack(crops))
json.dump(out, open(W + '/b2/beige_id_ep11_f0.json', 'w'), indent=1)
