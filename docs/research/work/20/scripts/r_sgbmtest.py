"""SGBM density test on white/textureless objects (debug). usage: r_sgbmtest.py <ep>"""
import sys, os, numpy as np, cv2
sys.path.insert(0, os.path.dirname(__file__))
import b_lib as B
ep = int(sys.argv[1]); split = sys.argv[2] if len(sys.argv) > 2 else 'public'
gc = cv2.cvtColor(B.read_frames(split, ep, 'c', [0])[0], cv2.COLOR_BGR2GRAY)
gb = cv2.cvtColor(B.read_frames(split, ep, 'b', [0])[0], cv2.COLOR_BGR2GRAY)
rc, rbw, f, info = B.rect_pair(gc, gb)
tiles = []
for name, sc, bs, ur, sw in (('full7', 1, 7, 8, 100), ('full11u3', 1, 11, 3, 200), ('half7u5', 2, 7, 5, 50), ('half11u2', 2, 11, 2, 50)):
    a, b = (rc, rbw) if sc == 1 else (cv2.resize(rc, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA), cv2.resize(rbw, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA))
    md = 24 // sc; nd = 160 // sc; nd = (nd + 15) // 16 * 16
    sg = cv2.StereoSGBM_create(minDisparity=md, numDisparities=nd, blockSize=bs, P1=8 * bs * bs, P2=32 * bs * bs, disp12MaxDiff=1,
                               uniquenessRatio=ur, speckleWindowSize=sw, speckleRange=2, mode=cv2.STEREO_SGBM_MODE_SGBM_3WAY)
    d = sg.compute(a, b).astype(np.float32) / 16.0 * sc
    if sc == 2: d = cv2.resize(d, (rc.shape[1], rc.shape[0]), interpolation=cv2.INTER_NEAREST)
    v = np.clip((d - 40) / 120 * 255, 0, 255).astype(np.uint8); v = cv2.applyColorMap(v, cv2.COLORMAP_JET); v[d < 24.5] = 0
    v = cv2.resize(v, (640, 400)); cv2.putText(v, f'{name} valid {(d > 24.5).mean():.2f}', (5, 20), 0, 0.6, (255, 255, 255), 2); tiles.append(v)
g = cv2.cvtColor(cv2.resize(rc, (640, 400)), cv2.COLOR_GRAY2BGR)
cv2.imwrite(f'/Users/aebatirel/Documents/Code/v2d-research/work/20/out/c2/dbg/sgbm_{split[0]}{ep}.jpg', np.vstack([np.hstack([g, tiles[0], tiles[1]]), np.hstack([g * 0, tiles[2], tiles[3]])]))
