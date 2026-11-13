"""ORACLE DIAGNOSTIC zoom overlays (public ep24, cam a): silhouette outlines of board 2 (static and untouched in mocap
until ~f105) at full resolution. red = P_o track; green = mocap through our VO camera (one fit on f0-7);
cyan = mocap through the GT-free anchor-corrected camera. Usage: python -I overlay24_zoom.py OUT_DIR
"""
import os, sys
import numpy as np, cv2, trimesh
sys.argv = [sys.argv[0], sys.argv[1]]
OUT = sys.argv[1]
os.environ.setdefault('SEL', '0')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import overlay24 as O  # noqa: E402  (builds G, C, frames)
dense = {n: trimesh.sample.sample_surface(trimesh.load(O.XF.scan_path(O.V.T3D, n), force='mesh'), 30000, seed=2)[0] for n in O.names}


def outline(img, Tw, n, cam, col):
    O.pts[n], keep = dense[n], O.pts[n]
    uv = O.proj(Tw, n, cam).astype(int); O.pts[n] = keep
    m = np.zeros(img.shape[:2], np.uint8)
    ok = (uv[:, 0] >= 0) & (uv[:, 0] < img.shape[1]) & (uv[:, 1] >= 0) & (uv[:, 1] < img.shape[0])
    for u, v in uv[ok]:
        cv2.circle(m, (u, v), 3, 255, -1)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    cv2.drawContours(img, cs, -1, col, 2)
    return uv[ok].mean(0) if ok.any() else None


tiles = []
n = O.names[1]
for i in (0, 30, 45, 60, 80, 100):
    img = O.frames[i + O.aoff].copy()
    c = None
    for Tw, cam, col in ((O.T[n][i], O.W_C[i], (0, 0, 255)), (O.G @ O.gt[n][i], O.W_C[i], (0, 200, 0)),
                         (O.G @ O.gt[n][i], O.C[i] @ O.W_C[i], (255, 255, 0))):
        cc = outline(img, Tw, n, cam, col); c = cc if c is None else c
    c = c.astype(int)
    x0, y0 = int(np.clip(c[0] - 260, 0, img.shape[1] - 520)), int(np.clip(c[1] - 200, 0, img.shape[0] - 400))
    crop = img[y0:y0 + 400, x0:x0 + 520].copy()
    r = O.D[i]
    cv2.rectangle(crop, (0, 0), (520, 24), (0, 0, 0), -1)
    cv2.putText(crop, f"f{i} board 2 (static)  kit ADD {r[n]['Po']['add']:.1f} cm  VO corr {np.linalg.norm(O.C[i, :3, 3]) * 100:.1f} cm",
                (6, 17), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
    tiles.append(crop)
rows = [np.hstack(tiles[k:k + 3]) for k in (0, 3)]
img = np.vstack(rows)
cv2.rectangle(img, (0, img.shape[0] - 26), (img.shape[1], img.shape[0]), (0, 0, 0), -1)
cv2.putText(img, 'red = P_o track | green = mocap via our VO camera (fit f0-7) | cyan = mocap via GT-free anchor-corrected camera | ORACLE DIAGNOSTIC',
            (6, img.shape[0] - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
cv2.imwrite(f'{OUT}/ep24_board2_static_zoom.png', img)
print('wrote', f'{OUT}/ep24_board2_static_zoom.png')
