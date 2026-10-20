"""Stage C re-run: top-down (hypothesis-driven) verification of the beige spin branch on public ep 11 f0 cam a.
Each branch predicts where its undetected third marker should be (verifier v_c3_branch.py refit, 6-pt camera).
Instead of needing bottom-up recall, score 'is there a sphere of the expected size here?' within 6 px of each
prediction, and compare with the same score at random cup/floor points (background). Scores: circular-edge
completeness at the expected radius, and scale-normalised DoG blob response."""
import numpy as np, cv2, json
W = '/Users/aebatirel/Documents/Code/v2d-research/work/12'
im = cv2.imread(W + '/b/fr/p11_a_0000.png'); g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY).astype(np.float32)
gs = cv2.GaussianBlur(g, (0, 0), 1.5); gx = cv2.Sobel(gs, cv2.CV_32F, 1, 0); gy = cv2.Sobel(gs, cv2.CV_32F, 0, 1)
gm = np.hypot(gx, gy)
r0 = 18.5    # expected sphere radius px at Z ~0.44 m (stage B re-run: 35-40 px diameter)
s1 = r0 / np.sqrt(2); dog = cv2.GaussianBlur(g, (0, 0), s1) - cv2.GaussianBlur(g, (0, 0), 1.6 * s1)
ang = np.linspace(0, 2 * np.pi, 72, endpoint=False)
def samp(img, x, y): return cv2.remap(img, x.astype(np.float32), y.astype(np.float32), cv2.INTER_LINEAR)
def circ(cx, cy):
    best = 0
    for r in r0 * np.array([0.85, 0.92, 1.0, 1.08, 1.15]):
        x = (cx + r * np.cos(ang))[None]; y = (cy + r * np.sin(ang))[None]
        rad = np.abs(samp(gx, x, y) * np.cos(ang) + samp(gy, x, y) * np.sin(ang)).ravel()
        loc = gm[int(cy - 2.5 * r):int(cy + 2.5 * r), int(cx - 2.5 * r):int(cx + 2.5 * r)].mean() + 1e-6
        best = max(best, float((rad > 0.5 * loc).mean() * rad.mean() / loc))
    return best
def score(cx, cy, rho=6, step=2):
    c, d = 0, 0
    for dx in range(-rho, rho + 1, step):
        for dy in range(-rho, rho + 1, step):
            if dx * dx + dy * dy > rho * rho: continue
            c = max(c, circ(cx + dx, cy + dy)); d = max(d, abs(float(dog[int(cy + dy), int(cx + dx)])))
    return c, d
pred = {'true (0 deg)': (1277, 888), '-131 branch': (1325, 871), '+120 branch (poor 2-blob fit)': (1267, 888),
        'by-eye true sphere': (1273, 888), 'detected @35 (control)': (1261, 1058), 'detected @171 (control)': (1479, 982)}
rng = np.random.default_rng(1); bg = []
for _ in range(150):
    x, y = rng.uniform(1150, 1600), rng.uniform(820, 1350); bg.append(score(x, y))
bg = np.array(bg); out = {}
for k, (x, y) in pred.items():
    c, d = score(x, y); out[k] = dict(xy=[x, y], circ=c, dog=d, circ_pct=float((bg[:, 0] < c).mean()), dog_pct=float((bg[:, 1] < d).mean()))
    print('%-32s circ %.3f (bg pct %.2f)  dog %.1f (bg pct %.2f)' % (k, c, out[k]['circ_pct'], d, out[k]['dog_pct']))
print('background circ p50/p90/p99 %.3f/%.3f/%.3f, dog %.1f/%.1f/%.1f' % (*np.percentile(bg[:, 0], [50, 90, 99]), *np.percentile(bg[:, 1], [50, 90, 99])))
json.dump(dict(pred=out, bg_pct=dict(circ=np.percentile(bg[:, 0], [50, 90, 99]).tolist(), dog=np.percentile(bg[:, 1], [50, 90, 99]).tolist())),
          open(W + '/c2/topdown_ep11_f0.json', 'w'), indent=1)
crops = [cv2.resize(im[y - 40:y + 40, x - 40:x + 40], (240, 240), interpolation=cv2.INTER_NEAREST) for (x, y) in [pred['true (0 deg)'], pred['-131 branch']]]
for c in crops: cv2.circle(c, (120, 120), int(3 * r0), (0, 255, 0), 1)
cv2.imwrite(W + '/c2/topdown_ep11_f0.png', np.hstack(crops))
