# Round-2 verifier (C1): do welded, closed convex pieces come back from the exact FlashCHORD CoACD call unchanged?
# Inputs: synthetic convex pieces + real CoACD hulls re-fed as pieces (scipy ConvexHull triangulation, outward-oriented,
# float32-rounded vertices as newton stores them). Output: hull count, max distance of output vertices outside the input
# hull, max distance of input hull vertices outside the output union (both mm), manifold-check log line.
import sys, numpy as np, io, os, contextlib
sys.path.insert(0, '/Users/aebatirel/Documents/Code/v2d-research/work/15-verify/pylib11')
import coacd
from scipy.spatial import ConvexHull
sys.path.insert(0, '/Users/aebatirel/Documents/Code/v2d-research/work/19/b'); from common import load_hulls
coacd.set_log_level('info')
def piece(v):
    v = np.asarray(v, np.float32).astype(np.float64); h = ConvexHull(v); idx = h.vertices
    remap = -np.ones(len(v), int); remap[idx] = np.arange(len(idx)); f = remap[h.simplices]; w = v[idx]; c = w.mean(0)
    for k in range(len(f)):
        a, b, cc = w[f[k]]
        if np.dot(np.cross(b - a, cc - a), a - c) < 0: f[k] = f[k][[0, 2, 1]]
    return w, f
def outside(p, eq): return (p @ eq[:, :3].T + eq[:, 3]).max(1)
def test(name, v):
    w, f = piece(v); E = ConvexHull(w).equations
    parts = coacd.run_coacd(coacd.Mesh(w, f), threshold=0.05, max_convex_hull=-1, preprocess_mode='auto')
    ov = np.vstack([p[0] for p in parts]); o1 = outside(ov, E).max() * 1e3
    o2 = max(min(outside(w, ConvexHull(p[0]).equations)[i] for p in parts) for i in range(len(w))) * 1e3
    print(f'{name:34s} in v {len(w):4d} f {len(f):4d} -> hulls {len(parts):2d} out-v {sum(len(p[0]) for p in parts):4d} | '
          f'out outside in {o1:+.4f} mm | in outside out {o2:+.4f} mm', flush=True)
rng = np.random.default_rng(7)
test('box 120x30x200', np.array([[x, y, z] for x in (0, .12) for y in (0, .03) for z in (0, .2)]))
test('plate 300x200x3', np.array([[x, y, z] for x in (0, .3) for y in (0, .2) for z in (0, .003)]))
test('cube 5 mm', np.array([[x, y, z] for x in (0, .005) for y in (0, .005) for z in (0, .005)]))
s = rng.normal(size=(64, 3)); s /= np.linalg.norm(s, axis=1)[:, None]; test('sphere-ish 64 pts r 20 mm', 0.02 * s)
s = rng.normal(size=(400, 3)); s /= np.linalg.norm(s, axis=1)[:, None]; test('sphere-ish 400 pts r 20 mm', 0.02 * s)
t = np.linspace(0, 2 * np.pi, 12, endpoint=False); cap = np.c_[0.004 * np.cos(t), 0.004 * np.sin(t)]
test('thin rod 8 mm x 150 mm (12-gon)', np.vstack([np.c_[cap, np.zeros(12)], np.c_[cap, np.full(12, .15)]]))
W = '/Users/aebatirel/Documents/Code/v2d-research/work/19/b/'
for f, n in ((W + 'V1/white_pot_lid.npz', 6), (W + 'V4_120/plastic_dish_rack.npz', 8), (W + 'V4_120/white_pot.npz', 6)):
    hv = load_hulls(f); ids = rng.choice(len(hv), n, replace=False)
    for i in ids:
        if ConvexHull(hv[i]).volume < 1e-12: continue
        test(f'{f.split("/")[-2]}/{f.split("/")[-1][:-4]} hull {i}', hv[i])
