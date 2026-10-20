# Round-2 verifier (C2): concavity-tolerance law. For each mesh handed to CoACD (exact call, no preprocessing), max
# outward distance of its hulls (vertices + 1/mm^2 surface samples) from that mesh (igl signed distance) / (0.025 L),
# L = longest bbox extent of the mesh. Meshes: 6 whole W2 objects (V1) + pot S120 parts + lid S60 parts + rack S120 parts.
import sys, glob, os, numpy as np, trimesh, igl
from scipy.spatial import ConvexHull
B = '/Users/aebatirel/Documents/Code/v2d-research/work/19/b/'
def hs(hv, dens=1e6):
    out = []
    for i, v in enumerate(hv):
        h = ConvexHull(v); m = trimesh.Trimesh(v, h.simplices, process=False); np.random.seed(i)
        out.append(np.vstack([v[h.vertices], m.sample(max(20, int(m.area * dens)))]))
    return np.vstack(out)
def law(name, V, F, hv):
    L = np.ptp(V, 0).max(); s = igl.signed_distance(hs(hv), V, F.astype(np.int64))[0]
    r = s.max() / (0.025 * L); print(f'{name:40s} L {L*1e3:6.1f} mm hulls {len(hv):4d} max out {s.max()*1e3:6.2f} mm p99 {np.percentile(s,99)*1e3:5.2f} -> max/(0.025L) {r:4.2f}', flush=True); return r
def lh(p): d = np.load(p); return [d[f'v{i}'] for i in range(int(d['n']))]
R = []
for o in ['white_pot_lid', 'white_pot', 'mini_sweeper', 'plastic_dish_rack', 'blue_cup', 'beige_cup']:
    d = np.load(B + f'W2/{o}.npz'); R.append(law('V1 ' + o, d['v'], d['f'], lh(B + f'V1/{o}.npz')))
for sub, o, k in (('S120', 'white_pot', 99), ('S60', 'white_pot_lid', 6), ('S120', 'plastic_dish_rack', 5)):
    parts = sorted(glob.glob(B + f'{sub}/{o}/{o}_p*.npz'))[:k]
    for p in parts:
        hp = B + f'{sub}/{o}/hulls/' + os.path.basename(p)
        if not os.path.exists(hp): continue
        d = np.load(p); R.append(law(f'{sub} {os.path.basename(p)[:-4]}', d['v'], d['f'], lh(hp)))
R = np.array(R); print(f'n {len(R)} ratio median {np.median(R):.2f} min {R.min():.2f} max {R.max():.2f}')
