# Round-2 verifier (C2): voxel term on identical geometry: hull-vs-W2 outward distance p50/p99 for V2 (forced prep
# res 50) vs V1 (no prep), in units of the voxel L/100 (L = longest W2 extent).
import numpy as np, trimesh, igl
from scipy.spatial import ConvexHull
B = '/Users/aebatirel/Documents/Code/v2d-research/work/19/b/'
def lh(p): d = np.load(p); return [d[f'v{i}'] for i in range(int(d['n']))]
def hs(hv, dens=1e6):
    out = []
    for i, v in enumerate(hv):
        h = ConvexHull(v); m = trimesh.Trimesh(v, h.simplices, process=False); np.random.seed(i)
        out.append(np.vstack([v[h.vertices], m.sample(max(20, int(m.area * dens)))]))
    return np.vstack(out)
for o in ['white_pot_lid', 'white_pot', 'mini_sweeper', 'plastic_dish_rack', 'blue_cup', 'beige_cup']:
    d = np.load(B + f'W2/{o}.npz'); V, F = d['v'], d['f'].astype(np.int64); vox = np.ptp(V, 0).max() / 100
    r = {}
    for L in ('V1', 'V2'):
        s = igl.signed_distance(hs(lh(B + f'{L}/{o}.npz')), V, F)[0]; r[L] = (np.percentile(s, 50), np.percentile(s, 99), s.max())
    print(f'{o:18s} voxel {vox*1e3:4.2f} mm | V1 p50/p99/max {r["V1"][0]*1e3:5.2f}/{r["V1"][1]*1e3:5.2f}/{r["V1"][2]*1e3:5.2f} | V2 {r["V2"][0]*1e3:5.2f}/{r["V2"][1]*1e3:5.2f}/{r["V2"][2]*1e3:5.2f} | '
          f'V2-V1 p50 {(r["V2"][0]-r["V1"][0])/vox:4.2f} vox, p99 {(r["V2"][1]-r["V1"][1])/vox:4.2f} vox', flush=True)
