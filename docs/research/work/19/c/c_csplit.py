# Stage C: contact-zone split (budgeted). Split the W2 solid into (a) the contact-zone box subdivided into a
# grid of cells, each cell its own closed part, and (b) ONE remainder part = everything outside the zone box.
# Parts are closed with flat caps like b/b_split.py (marching cubes on max(field, box sdf), same nudge), so each is a
# watertight mesh = one <collision> element; neighbouring parts overlap by 2 x 0.3 mm at the cuts.
# usage: c_csplit.py name x0 x1 y0 y1 z0 z1 (mm, object frame) nx ny nz outdir
import sys, os, numpy as np, trimesh
from skimage.measure import marching_cubes
sys.path.insert(0, '/Users/aebatirel/Documents/Code/v2d-research/work/19/b'); from b_field import *
n = sys.argv[1]; Z = np.array([float(x) for x in sys.argv[2:8]]).reshape(3, 2) * 1e-3
G = [int(x) for x in sys.argv[8:11]]; od = sys.argv[11]; os.makedirs(od, exist_ok=True)
h, dl, t = 1e-3, 0.3e-3, 3e-3
f, lo = w2_field(n, h, t); N = np.array(f.shape)
X = [lo[i] + h * np.arange(N[i]) for i in range(3)]
g = np.stack(np.meshgrid(*X, indexing='ij'), -1)
def boxsdf(bmin, bmax): return np.max(np.maximum(bmin - g, g - bmax), -1)
def part(fp, tag):
    fp = nudge(fp, dl, h); fp = np.pad(fp, 1, constant_values=1.0)
    if not (fp < dl).any(): return None
    v, fc, _, _ = marching_cubes(fp, level=dl, spacing=(h, h, h), allow_degenerate=False)
    v = v - h + lo
    w = trimesh.Trimesh(v, fc, process=True); w.merge_vertices()
    keep = [c for c in w.split(only_watertight=False) if abs(c.volume) > 0.05e-6]
    if not keep: return None
    w = trimesh.util.concatenate(keep)
    if w.volume < 0: w.invert()
    return w
out = []
zb = boxsdf(Z[:, 0], Z[:, 1])
edges = [np.linspace(Z[i, 0], Z[i, 1], G[i] + 1) for i in range(3)]
for a in range(G[0]):
    for b in range(G[1]):
        for c in range(G[2]):
            bmin = np.array([edges[0][a], edges[1][b], edges[2][c]]); bmax = np.array([edges[0][a + 1], edges[1][b + 1], edges[2][c + 1]])
            w = part(np.maximum(f, boxsdf(bmin, bmax)), f'z{a}{b}{c}')
            if w is not None: out.append(w)
nz = len(out)
w = part(np.maximum(f, -zb), 'rest')
if w is not None: out.append(w)
for i, w in enumerate(out):
    np.savez(f'{od}/{n}_p{i:03d}.npz', v=np.asarray(w.vertices), f=np.asarray(w.faces, np.int64))
    print(f'part {i:2d} ({"zone" if i < nz else "rest"}): F {len(w.faces)} L {np.ptp(w.vertices,0).max()*1e3:.1f} mm '
          f'watertight {w.is_watertight} vol {w.volume*1e6:.1f} cm3', flush=True)
print(f'{n}: {nz} zone parts + {len(out)-nz} remainder part(s)', flush=True)
