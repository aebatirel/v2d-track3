"""Sphere contrast in cam b (E-raw extrinsic) vs cam a at the same markers, public ep 11 f0. Grey-level contrast only
(cam b is mono): |mean annulus - mean inner disc| median over annulus pixels, and weak-edge share (radial grad < 20)."""
import cv2, numpy as np, json
def meas(img, uv, R):
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32); gb = cv2.GaussianBlur(g, (0, 0), 1.0)
    gx = cv2.Sobel(gb, cv2.CV_32F, 1, 0); gy = cv2.Sobel(gb, cv2.CV_32F, 0, 1)
    yy, xx = np.mgrid[:g.shape[0], :g.shape[1]]; u, v = uv; d = np.hypot(xx - u, yy - v)
    inner = g[d < 0.6 * R].mean(); ann = np.abs(g[(d > 1.25 * R) & (d < 1.7 * R)] - inner)
    t = np.linspace(0, 2 * np.pi, 72, endpoint=False); px = (u + R * np.cos(t)).astype(int); py = (v + R * np.sin(t)).astype(int)
    rad = np.abs(gx[py, px] * np.cos(t) + gy[py, px] * np.sin(t))
    return dict(R=round(float(R), 1), dI_med=round(float(np.median(ann)), 1), dI_p25=round(float(np.percentile(ann, 25)), 1),
                weak=round(float((rad < 20).mean()), 2))
A = json.load(open('b2/beige_id_ep11_f0.json')); B = json.load(open('b2/camb_proj_cands.json'))['E-raw']
ia = cv2.imread('b/fr/p11_a_0000.png'); ib = cv2.imread('b/fr/p11_b_0000.png')
keys = ['blue_cup#0', 'blue_cup#1', 'blue_cup#2', 'blue_cup#3', 'beige_cup#0', 'beige_cup#1', 'beige_cup#2']
out = {}
for i, k in enumerate(keys):
    a = meas(ia, A[k]['uv'], A[k]['pred_diam_px'] / 2); b = meas(ib, B['uv'][i], 567.26 * 0.0073 / B['Z'][i])
    out[k] = dict(theta=A[k]['theta'], a=a, b=b); print(k, A[k]['theta'], 'a', a, '| b', b)
json.dump(out, open('b2/camb_contrast_ep11_f0.json', 'w'), indent=1)
