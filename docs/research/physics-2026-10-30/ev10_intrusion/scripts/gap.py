"""ev10 GT-free nest geometry check (DIAGNOSTIC): per frame of OUR reference, in the blue cup's file frame (world up
~ -z, within ~4 deg):
  floor_gap_mm  height of the beige cup's lowest point minus the blue cup's inner-floor height (median top-surface
                height within 1.5 cm of the cavity axis); < 0 = the beige bottom is below the inner floor.
  vclear_mm     min over beige points within 40 mm of the cavity axis (inside the opening) of (point height - blue top-surface height at
                that x,y), the top surface = first hit of a ray from above; < 0 = beige penetrates the blue cup from
                above by that much along the vertical (the blue cup would need to drop / beige rise by -vclear).
and, for the plain library_v3 meshes, an exact mesh intrusion (2 mm lattice of each partner's solid by winding-number
SDF; depth = distance to the target mesh surface). Usage: gap.py REF OUT_PREFIX
"""
import sys, glob, json, csv, importlib.util
import numpy as np, trimesh
sys.path.insert(0, '/home/user/v2d-track3/pipeline')
from collision_decomp import SignedDistance
spec = importlib.util.spec_from_file_location('intrusion', '/home/user/v2d-track3/tools/intrusion.py')
I = importlib.util.module_from_spec(spec); spec.loader.exec_module(I)
ref, outp = sys.argv[1], sys.argv[2]
names, O, P, Q, fps = I.load_ref(ref); T = len(O); ib, ig = names.index('blue_cup'), names.index('beige_cup')
Oi = I.inv_pose(O)
REL = np.einsum('tij,tjk->tik', Oi[:, ib], O[:, ig])          # beige file -> blue file
LIB = '/home/user/v2d-track3/meshes/library_v3'; CARVE = '/home/user/v2d-track3/meshes/carve/ev10'

def pieces_mesh(d):
    return trimesh.util.concatenate([trimesh.load(f, force='mesh', process=False) for f in sorted(glob.glob(f'{d}/piece_*.obj'))])

def heightmap(inside, lo, hi, h=0.0015, dz=0.0005):
    """Top-surface height (-z, up) per (x, y) column: the first sample from above (step dz) that is inside."""
    xs = np.arange(lo[0], hi[0] + h, h); ys = np.arange(lo[1], hi[1] + h, h); zs = np.arange(lo[2] - dz, hi[2] + dz, dz)
    gx, gy = (g.ravel() for g in np.meshgrid(xs, ys, indexing='ij')); H = np.full(len(gx), np.nan)
    for z in zs[::-1][::-1]:                               # from file z min (= top in the world) downward
        todo = np.isnan(H)
        if not todo.any():
            break
        X = np.c_[gx[todo], gy[todo], np.full(todo.sum(), z)]
        ins = inside(X); idx = np.nonzero(todo)[0][ins]; H[idx] = -z
    return xs, ys, H.reshape(len(xs), len(ys))

def analyse(inside, lo, hi, beige_pts, tag):
    xs, ys, H = heightmap(inside, lo, hi); h = xs[1] - xs[0]
    rim = np.nanmax(H)
    cav = H < rim - 0.01                                   # cells whose top surface is > 1 cm below the rim: the cavity
    gx, gy = np.meshgrid(xs, ys, indexing='ij'); cx, cy = gx[cav].mean(), gy[cav].mean()
    rr = np.hypot(gx - cx, gy - cy)
    floor = float(np.nanmedian(H[cav & (rr < 0.015)])); cav_r = float(rr[cav].max())
    print(tag, f'blue rim height {rim*1e3:.1f} mm, inner floor {floor*1e3:.1f} mm (file z {-floor*1e3:.1f}), cavity radius <= {cav_r*1e3:.1f} mm, axis ({cx*1e3:.1f}, {cy*1e3:.1f}) mm')
    res = []
    for f in range(T):
        X = beige_pts @ REL[f, :3, :3].T + REL[f, :3, 3]; hz = -X[:, 2]
        k = np.argmin(hz); low = float(hz[k])
        i = np.clip(np.round((X[:, 0] - xs[0]) / h).astype(int), 0, len(xs) - 1); j = np.clip(np.round((X[:, 1] - ys[0]) / h).astype(int), 0, len(ys) - 1)
        Hp = H[i, j]; inb = (X[:, 0] >= xs[0]) & (X[:, 0] <= xs[-1]) & (X[:, 1] >= ys[0]) & (X[:, 1] <= ys[-1]) & np.isfinite(Hp) & (np.hypot(X[:, 0] - cx, X[:, 1] - cy) < 0.040)     # inside the opening (inner rim ~42 mm)
        vc = (hz - Hp)[inb]
        res.append(dict(frame=f, beige_low_h_mm=low * 1e3, floor_gap_mm=(low - floor) * 1e3, over_floor=bool(np.hypot(X[k, 0] - cx, X[k, 1] - cy) < 0.04),
                        low_r_mm=float(np.hypot(X[k, 0] - cx, X[k, 1] - cy) * 1e3),
                        vclear_mm=float(vc.min() * 1e3) if len(vc) else np.nan,
                        n_below_top=int((vc < 0).sum()), n_pts_in_footprint=int(inb.sum())))
    return dict(rim_mm=rim * 1e3, floor_mm=floor * 1e3, cavity_r_mm=cav_r * 1e3, axis_mm=[cx * 1e3, cy * 1e3]), res

def surf(m, n=40000):
    return np.vstack([trimesh.sample.sample_surface(m, n, seed=0)[0], m.vertices])

out = {}
# A: carved collision pieces (beige points = piece surface samples)
UA = I.Union(sorted(glob.glob(f'{CARVE}/blue_cup/piece_*.obj'))); gA = pieces_mesh(f'{CARVE}/beige_cup')
out['A_carve_ev10'] = analyse(lambda X: UA.depth_lb(X) > 0, UA.alo, UA.ahi, surf(gA), 'A')
# B: plain library_v3 meshes
bB = trimesh.load(f'{LIB}/blue_cup.glb', force='mesh', process=False); gB = trimesh.load(f'{LIB}/beige_cup.glb', force='mesh', process=False)
bB = trimesh.Trimesh(bB.vertices, bB.faces, process=True); gB = trimesh.Trimesh(gB.vertices, gB.faces, process=True)

# exact mesh intrusion for the library_v3 meshes
pitch = 0.002
def lattice(m, sd):
    lo, hi = m.bounds; ax = [(np.arange(np.floor(a / pitch - .5), np.ceil(b / pitch - .5) + 1) + .5) * pitch for a, b in zip(lo, hi)]
    G = np.stack(np.meshgrid(*ax, indexing='ij'), -1).reshape(-1, 3); return G[sd(G, 1.0) < -1e-6]
sdB, sdG = SignedDistance(bB), SignedDistance(gB)
out['B_libv3_mesh'] = analyse(lambda X: sdB(X, 0.05) < 0, bB.bounds[0], bB.bounds[1], surf(gB), 'B')
LB, LG = lattice(bB, sdB), lattice(gB, sdG)
print('lattice', len(LB), len(LG), 'solid cm3', len(LB) * pitch**3 * 1e6, len(LG) * pitch**3 * 1e6)
exact = []
for f in range(T):
    r = {}
    Xg = LG @ REL[f, :3, :3].T + REL[f, :3, 3]; d = sdB(Xg, 0.2); k = d < -1e-6                 # beige samples inside blue
    Ri = np.linalg.inv(REL[f]); Xb = LB @ Ri[:3, :3].T + Ri[:3, 3]; e = sdG(Xb, 0.2); q = e < -1e-6  # blue samples inside beige
    exact.append(dict(frame=f, beige_in_blue_n=int(k.sum()), beige_in_blue_vol_cm3=float(k.sum() * pitch**3 * 1e6),
                      beige_in_blue_depth_max_mm=float(-d[k].min() * 1e3) if k.any() else 0.0,
                      beige_in_blue_depth_med_mm=float(np.median(-d[k]) * 1e3) if k.any() else 0.0,
                      blue_in_beige_n=int(q.sum()), blue_in_beige_vol_cm3=float(q.sum() * pitch**3 * 1e6),
                      blue_in_beige_depth_max_mm=float(-e[q].min() * 1e3) if q.any() else 0.0,
                      blue_in_beige_depth_med_mm=float(np.median(-e[q]) * 1e3) if q.any() else 0.0))
out['B_libv3_mesh_exact_intrusion'] = dict(pitch_m=pitch, lattice_n=dict(blue_cup=len(LB), beige_cup=len(LG)), rows=exact)
out['DIAGNOSTIC'] = 'GT-free consistency check of our eval-10 reference (ev10_intrusion/scripts/gap.py); not contract output; no score'
json.dump(out, open(outp + '.json', 'w'), indent=1, default=float)
with open(outp + '_per_frame.csv', 'w', newline='') as fh:
    w = csv.writer(fh)
    w.writerow(['frame', 'A_floor_gap_mm', 'A_vclear_mm', 'A_low_r_mm', 'B_floor_gap_mm', 'B_vclear_mm', 'B_low_r_mm',
                'Bmesh_beige_in_blue_vol_cm3', 'Bmesh_beige_in_blue_depth_max_mm', 'Bmesh_blue_in_beige_vol_cm3', 'Bmesh_blue_in_beige_depth_max_mm'])
    for f in range(T):
        a, b, x = out['A_carve_ev10'][1][f], out['B_libv3_mesh'][1][f], exact[f]
        w.writerow([f] + [round(v, 2) for v in (a['floor_gap_mm'], a['vclear_mm'], a['low_r_mm'], b['floor_gap_mm'], b['vclear_mm'], b['low_r_mm'],
                    x['beige_in_blue_vol_cm3'], x['beige_in_blue_depth_max_mm'], x['blue_in_beige_vol_cm3'], x['blue_in_beige_depth_max_mm'])])
print('wrote', outp)
