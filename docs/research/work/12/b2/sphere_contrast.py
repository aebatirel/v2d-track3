"""Stage B gap 3: automatic sphere-vs-surround contrast at GT-projected marker centres, public ep 11 f0 cam a.
Inner disc 0.6 R vs annulus 1.25-1.7 R (Lab, delta E76) and mean radial gradient on the R circle."""
import cv2, numpy as np, json
J = json.load(open('b2/beige_id_ep11_f0.json'))
im = cv2.imread('b/fr/p11_a_0000.png'); lab = cv2.cvtColor(im, cv2.COLOR_BGR2LAB).astype(np.float32)
lab[..., 0] *= 100 / 255; lab[..., 1:] -= 128
g = cv2.GaussianBlur(cv2.cvtColor(im, cv2.COLOR_BGR2GRAY).astype(np.float32), (0, 0), 1.0)
gx = cv2.Sobel(g, cv2.CV_32F, 1, 0); gy = cv2.Sobel(g, cv2.CV_32F, 0, 1)
yy, xx = np.mgrid[:im.shape[0], :im.shape[1]]
out = {}
for k, r in J.items():
    if k == 'cam_err_px': continue
    (u, v), R = r['uv'], r['pred_diam_px'] / 2
    d = np.hypot(xx - u, yy - v)
    inner = lab[d < 0.6 * R].mean(0); ann = lab[(d > 1.25 * R) & (d < 1.7 * R)]
    dE = np.linalg.norm(ann - inner, axis=1)
    t = np.linspace(0, 2 * np.pi, 72, endpoint=False); px = (u + R * np.cos(t)).astype(int); py = (v + R * np.sin(t)).astype(int)
    rad = np.abs(gx[py, px] * np.cos(t) + gy[py, px] * np.sin(t))
    out[k] = dict(theta=r['theta'], R_px=round(R, 1), dE_median=round(float(np.median(dE)), 1), dE_p25=round(float(np.percentile(dE, 25)), 1),
                  inner_L=round(float(inner[0]), 1), edge_grad_median=round(float(np.median(rad)), 1),
                  edge_frac_weak=round(float((rad < 20).mean()), 2))
    print(k, out[k])
json.dump(out, open('b2/sphere_contrast_ep11_f0.json', 'w'), indent=1)
