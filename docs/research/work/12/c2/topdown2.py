"""Add two simple cues to topdown.py at the same points: dark (black mount) fraction and fine-texture energy inside
r0 (the grey floor is speckled, a sphere is smooth). Same background sample."""
import numpy as np, cv2, json
W = '/Users/aebatirel/Documents/Code/v2d-research/work/12'
im = cv2.imread(W + '/b/fr/p11_a_0000.png'); hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV).astype(np.float32)
V = hsv[..., 2] / 255; g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY).astype(np.float32)
hp = np.abs(g - cv2.GaussianBlur(g, (0, 0), 1.5))
r0 = 18.5; yy, xx = np.mgrid[-19:20, -19:20]; disk = xx ** 2 + yy ** 2 <= r0 ** 2
def cues(x, y):
    sl = (slice(int(y) - 19, int(y) + 20), slice(int(x) - 19, int(x) + 20))
    return float((V[sl][disk] < 0.2).mean()), float(np.percentile(hp[sl][disk], 25))
pred = {'true (0 deg)': (1277, 888), '-131 branch': (1325, 871), '+120 branch': (1267, 888), 'by-eye true': (1273, 888),
        '@35 control': (1261, 1058), '@171 control': (1479, 982)}
rng = np.random.default_rng(1); bg = np.array([cues(rng.uniform(1150, 1600), rng.uniform(820, 1350)) for _ in range(150)])
out = {}
for k, (x, y) in pred.items():
    d, t = cues(x, y); out[k] = dict(dark=d, tex25=t, dark_pct=float((bg[:, 0] < d).mean()), tex_pct_smoother=float((bg[:, 1] > t).mean()))
    print('%-14s dark %.3f (bg pct %.2f)  fine-texture p25 %.2f (share of bg rougher %.2f)' % (k, d, out[k]['dark_pct'], t, out[k]['tex_pct_smoother']))
print('bg dark p50/p90 %.3f/%.3f, tex p50 %.2f' % (np.percentile(bg[:, 0], 50), np.percentile(bg[:, 0], 90), np.percentile(bg[:, 1], 50)))
json.dump(out, open(W + '/c2/topdown2_ep11_f0.json', 'w'), indent=1)
