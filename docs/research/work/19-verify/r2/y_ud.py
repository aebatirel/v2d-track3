# Round-2 verifier (C2, C3): independent union-depth estimate for the 21 public GT contact states.
# Differences from round-1 v_uniondepth2.py:
#  * A's collider surface = A hull-union BOUNDARY only (samples strictly inside another A hull by > 0.05 mm dropped),
#    1 sample/mm^2 + boundary hull vertices, own seeds; reported as 'bnd'. 'all' = every A hull-surface sample
#    (round-1 choice, includes interior faces between A's own hulls).
#  * Depth inside B's hull union from a voxel EDT (0.2 mm voxels, occupancy = exact half-space test of every B hull;
#    depth = trilinear EDT - h/2), not from nearest boundary samples. A coarse sample-based upper bound only ranks the
#    candidate points; every reported maximum is an EDT value (branch and bound: stop when no unevaluated point can
#    exceed the best EDT depth).
#  * Floors recomputed with W2 vertices + 300k W2 surface samples (own seed), igl signed distance to the other W2.
# usage: y_ud.py floors | y_ud.py LABEL=dir[,dir2] ...
import sys, os, time, numpy as np, pandas as pd, trimesh
from scipy.spatial import ConvexHull, cKDTree
from scipy.spatial.transform import Rotation as R
from scipy.ndimage import distance_transform_edt, map_coordinates
P = '/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public/data/chunk-000/episode_%06d.parquet'
W2D = '/Users/aebatirel/Documents/Code/v2d-research/work/19/b/W2/'
H, EPS = 2.0e-4, 5e-5
CASES = [(0,0,'white_pot_lid','white_pot'),(2,0,'white_pot_lid','white_pot'),(0,-1,'white_pot_lid','white_pot'),
 (31,0,'mini_sweeper','plastic_dish_rack'),(31,160,'mini_sweeper','plastic_dish_rack'),(26,4,'white_pot','plastic_dish_rack'),
 (27,216,'white_pot','plastic_dish_rack'),(12,160,'blue_cup','plastic_dish_rack'),(12,-1,'blue_cup','plastic_dish_rack'),
 (13,176,'blue_cup','plastic_dish_rack'),(13,-1,'blue_cup','plastic_dish_rack'),(11,96,'beige_cup','blue_cup'),(11,-1,'beige_cup','blue_cup'),
 (0,28,'white_pot_lid','white_pot'),(2,314,'white_pot_lid','white_pot'),(11,124,'beige_cup','blue_cup'),(12,168,'blue_cup','plastic_dish_rack'),
 (13,130,'blue_cup','plastic_dish_rack'),(26,12,'white_pot','plastic_dish_rack'),(27,218,'white_pot','plastic_dish_rack'),(31,238,'mini_sweeper','plastic_dish_rack')]
def T(pose):
    x, y, z, qw, qx, qy, qz = pose; M = np.eye(4); M[:3, :3] = R.from_quat([qx, qy, qz, qw]).as_matrix(); M[:3, 3] = [x, y, z]; return M
def tr(M, p): return p @ M[:3, :3].T + M[:3, 3]
class Obj:
    def __init__(s, path):
        d = np.load(path); s.hv = [d[f'v{i}'] for i in range(int(d['n']))]
        s.E = []; s.lo = []; s.hi = []; s.tri = []
        for v in s.hv:
            h = ConvexHull(v); s.E.append(h.equations); s.lo.append(v.min(0)); s.hi.append(v.max(0)); s.tri.append(h)
        s.lo = np.array(s.lo); s.hi = np.array(s.hi); s._b = None; s._s = None
    def inside_any(s, pts, skip=-1, tol=0.0):   # max plane distance < -tol (tol<0: also points within |tol| outside)
        ins = np.zeros(len(pts), bool)
        for j in range(len(s.hv)):
            if j == skip: continue
            mg = max(0.0, -tol)   # AABB prefilter must include the tolerance band (CoACD cut faces lie on AABB extremes)
            k = np.where(~ins & np.all((pts >= s.lo[j] - mg) & (pts <= s.hi[j] + mg), 1))[0]
            if len(k): ins[k[(pts[k] @ s.E[j][:, :3].T + s.E[j][:, 3]).max(1) < -tol]] = True
        return ins
    def surf(s, dens, seed):   # (all hull-surface samples, boundary mask)
        out, own = [], []
        for i, (v, h) in enumerate(zip(s.hv, s.tri)):
            m = trimesh.Trimesh(v, h.simplices, process=False); np.random.seed(seed + i)
            p = np.vstack([v[h.vertices], m.sample(max(30, int(m.area * dens)))]); out.append(p); own.append(np.full(len(p), i))
        P_ = np.vstack(out); own = np.concatenate(own); bnd = np.ones(len(P_), bool)
        for i in range(len(s.hv)):
            k = np.where(own == i)[0]; bnd[k] = ~s.inside_any(P_[k], skip=i, tol=-EPS)   # exclude points inside or within EPS of another hull (shared cut faces)
        return P_, bnd
    def perhull(s, q):
        ph = np.full(len(q), -np.inf)
        for j in range(len(s.hv)):
            k = np.where(np.all((q >= s.lo[j]) & (q <= s.hi[j]), 1))[0]
            if len(k): ph[k] = np.maximum(ph[k], -(q[k] @ s.E[j][:, :3].T + s.E[j][:, 3]).max(1))
        return ph
    def ub_tree(s):
        if s._b is None:
            P_, bnd = s.surf(2e6, 5000); s._b = cKDTree(P_[bnd])
        return s._b
    def occ(s, g):   # g: (n,3) voxel centres -> inside union (exact half-space test)
        ins = np.zeros(len(g), bool); glo, ghi = g.min(0), g.max(0)
        for j in np.where(np.all((s.hi >= glo) & (s.lo <= ghi), 1))[0]:
            k = np.where(~ins & np.all((g >= s.lo[j]) & (g <= s.hi[j]), 1))[0]
            if len(k): ins[k[(g[k] @ s.E[j][:, :3].T + s.E[j][:, 3]).max(1) <= 0]] = True
        return ins
    def maxdepth(s, q):
        """max union depth (mm) over points q (B frame) by EDT branch and bound; returns (depth, n_tiles, per-hull max)."""
        ph = s.perhull(q); inside = ph > 0
        if not inside.any(): return 0.0, 0, 0.0
        qi = q[inside]; ub = s.ub_tree().query(qi)[0] + 1e-4   # sample-distance upper bound (+0.1 mm slack)
        best = ph[inside].max(); done = np.zeros(len(qi), bool); tiles = 0
        while True:
            cand = np.where(~done & (ub > best))[0]
            if len(cand) == 0 or tiles >= 60: break
            c = cand[np.argmax(ub[cand])]; Rr = ub[c] + 2.5e-3
            lo = qi[c] - Rr; n = int(np.ceil(2 * Rr / H)) + 1
            ax = [lo[d] + H * np.arange(n) for d in range(3)]
            G = np.stack(np.meshgrid(*ax, indexing='ij'), -1).reshape(-1, 3)
            m = s.occ(G).reshape(n, n, n)
            if m.all(): raise RuntimeError('tile without outside voxels')
            D = distance_transform_edt(m) * H
            # evaluate every not-done candidate whose ball of radius ub fits in the tile
            mg = ub[:, None] + 5e-4; inn = np.where(~done & np.all(qi - mg >= lo, 1) & np.all(qi + mg <= lo + H * (n - 1), 1))[0]
            inn = np.union1d(inn, [c])
            idx = ((qi[inn] - lo) / H).T
            d = map_coordinates(D, idx, order=1, mode='nearest') - H / 2
            best = max(best, d.max()); done[inn] = True; tiles += 1
        return best * 1e3, tiles, ph[inside].max() * 1e3
_o = {}
def obj(d, n):
    for dd in d.split(','):
        p = f'{dd}/{n}.npz'
        if os.path.exists(p):
            if p not in _o: _o[p] = Obj(p)
            return _o[p]
_ss = {}
def samples(o, key):
    if key not in _ss: _ss[key] = o.surf(1e6, 9000)
    return _ss[key]
def pose(ep, f, a, b):
    df = pd.read_parquet(P % ep); fi = f if f >= 0 else len(df) - 1
    po = {x['name']: x['pose'] for x in df['observation.objects'].iloc[fi]}; return fi, T(po[a]), T(po[b])
if sys.argv[1] == 'floors':
    import igl
    for ep, f, a, b in CASES:
        fi, Ma, Mb = pose(ep, f, a, b); out = []
        for x, y, Mx, My in ((a, b, Ma, Mb), (b, a, Mb, Ma)):
            dx, dy = np.load(W2D + x + '.npz'), np.load(W2D + y + '.npz')
            mx = trimesh.Trimesh(dx['v'], dx['f'], process=False); np.random.seed(77)
            px = np.vstack([dx['v'], trimesh.sample.sample_surface(mx, 300000)[0]])
            q = tr(np.linalg.inv(My) @ Mx, px); sd = igl.signed_distance(q, dy['v'], dy['f'].astype(np.int64))[0]
            out.append(-sd.min() * 1e3)
        print(f'FLOOR2 ep{ep:<2d} f{fi:<4d} {a:13s} vs {b:17s}: A-in-B {out[0]:5.2f} | B-in-A {out[1]:5.2f}', flush=True)
    sys.exit()
SEL = [int(x) for x in os.environ.get('SEL', '').split(',') if x]
for arg in sys.argv[1:]:
    lab, d = arg.split('=', 1)
    for ci, (ep, f, a, b) in enumerate(CASES):
        if SEL and ci not in SEL: continue
        t0 = time.time(); fi, Ma, Mb = pose(ep, f, a, b); A, B = obj(d, a), obj(d, b)
        res = []
        for X, Y, Mx, My in ((A, B, Ma, Mb), (B, A, Mb, Ma)):
            Px, bnd = samples(X, id(X)); q = tr(np.linalg.inv(My) @ Mx, Px)
            db, nt, phb = Y.maxdepth(q[bnd]); da, _, pha = Y.maxdepth(q)
            res.append((db, da, phb, nt))
        print(f'{lab:7s} ep{ep:<2d} f{fi:<4d} {a:13s} vs {b:17s}: A-in-B bnd {res[0][0]:5.2f} all {res[0][1]:5.2f} ph {res[0][2]:4.1f} | '
              f'B-in-A bnd {res[1][0]:5.2f} all {res[1][1]:5.2f} ph {res[1][2]:4.1f} | tiles {res[0][3]},{res[1][3]} {time.time()-t0:.0f}s', flush=True)
