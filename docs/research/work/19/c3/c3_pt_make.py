# Stage C3: write the 26 Y4 pass-through pieces (same generator, same rng sequence as 19-verify/r2/y_passthru.py)
# plus two spoon-like thin pieces, as npz (v float64 from float32, f int64) for the Linux exact-call run.
import sys, numpy as np, json
from scipy.spatial import ConvexHull
sys.path.insert(0, '/Users/aebatirel/Documents/Code/v2d-research/work/19/b'); from common import load_hulls
OUT = '/Users/aebatirel/Documents/Code/v2d-research/work/19/c3/pt/'
def piece(v):
    v = np.asarray(v, np.float32).astype(np.float64); h = ConvexHull(v); idx = h.vertices
    remap = -np.ones(len(v), int); remap[idx] = np.arange(len(idx)); f = remap[h.simplices]; w = v[idx]; c = w.mean(0)
    for k in range(len(f)):
        a, b, cc = w[f[k]]
        if np.dot(np.cross(b - a, cc - a), a - c) < 0: f[k] = f[k][[0, 2, 1]]
    return w, f
names = []
def save(name, v):
    w, f = piece(v); k = len(names); np.savez(OUT + f'p{k:02d}.npz', v=w, f=f.astype(np.int64)); names.append(name)
rng = np.random.default_rng(7)
save('box 120x30x200', np.array([[x, y, z] for x in (0, .12) for y in (0, .03) for z in (0, .2)]))
save('plate 300x200x3', np.array([[x, y, z] for x in (0, .3) for y in (0, .2) for z in (0, .003)]))
save('cube 5 mm', np.array([[x, y, z] for x in (0, .005) for y in (0, .005) for z in (0, .005)]))
s = rng.normal(size=(64, 3)); s /= np.linalg.norm(s, axis=1)[:, None]; save('sphere-ish 64 pts r 20 mm', 0.02 * s)
s = rng.normal(size=(400, 3)); s /= np.linalg.norm(s, axis=1)[:, None]; save('sphere-ish 400 pts r 20 mm', 0.02 * s)
t = np.linspace(0, 2 * np.pi, 12, endpoint=False); cap = np.c_[0.004 * np.cos(t), 0.004 * np.sin(t)]
save('thin rod 8 mm x 150 mm (12-gon)', np.vstack([np.c_[cap, np.zeros(12)], np.c_[cap, np.full(12, .15)]]))
W = '/Users/aebatirel/Documents/Code/v2d-research/work/19/b/'
for f, n in ((W + 'V1/white_pot_lid.npz', 6), (W + 'V4_120/plastic_dish_rack.npz', 8), (W + 'V4_120/white_pot.npz', 6)):
    hv = load_hulls(f); ids = rng.choice(len(hv), n, replace=False)
    for i in ids:
        if ConvexHull(hv[i]).volume < 1e-12: continue
        save(f'{f.split("/")[-2]}/{f.split("/")[-1][:-4]} hull {i}', hv[i])
save('spoon-like plate 40x25x1 mm', np.array([[x, y, z] for x in (0, .04) for y in (0, .025) for z in (0, .001)]))
u = np.linspace(-0.6, 0.6, 6); g = np.array([[a, b] for a in u for b in u])
cap1 = np.c_[0.02 * g, 0.02 * (1 - np.sqrt(np.clip(1 - (g ** 2).sum(1), 0, 1)))]   # shallow spherical patch r 20 mm
save('spoon-bowl slab 1.5 mm (72 pts)', np.vstack([cap1, cap1 + [0, 0, 0.0015]]))
json.dump(names, open(OUT + 'names.json', 'w'), indent=0); print(len(names), 'pieces')
