# Verifier: per-hull depth (b_eval/pen2 metric) vs union depth, both directions, all 21 GT contact states.
# Union depth = distance from a penetrating point to the nearest union-boundary sample (hull-surface samples not inside
# any other hull of the same object by > EPS), computed on the hulls near the penetrating points (lazy, cached).
# usage: v_uniondepth2.py LABEL=dir[,dir2] ...   (first dir holding <obj>.npz wins)
import sys, os, numpy as np, pandas as pd, trimesh
from scipy.spatial import ConvexHull, cKDTree
from scipy.spatial.transform import Rotation as R
P = '/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public/data/chunk-000/episode_%06d.parquet'
EPS, DB, DQ, PAD = 5e-5, 4e6, 0.25e6, 0.015
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
        s.ch = [ConvexHull(v) for v in s.hv]
        s.H = [(v.min(0), v.max(0), h.equations) for v, h in zip(s.hv, s.ch)]
        s.lo = np.array([h[0] for h in s.H]); s.hi = np.array([h[1] for h in s.H]); s.bcache = {}
        out = []
        for i, (v, h) in enumerate(zip(s.hv, s.ch)):
            m = trimesh.Trimesh(v, h.simplices, process=False); np.random.seed(100 + i)
            out.append(np.vstack([v[h.vertices], m.sample(max(50, int(m.area * DQ)))]))
        s.S = np.vstack(out)
    def inside_any(s, pts, skip=-1, eps=0.0):
        ins = np.zeros(len(pts), bool)
        for j, (lo, hi, e) in enumerate(s.H):
            if j == skip: continue
            k = np.where(~ins & np.all((pts >= lo - eps) & (pts <= hi + eps), 1))[0]
            if len(k): ins[k[(pts[k] @ e[:, :3].T + e[:, 3]).max(1) <= eps]] = True
        return ins
    def boundary(s, i):
        if i not in s.bcache:
            v, h = s.hv[i], s.ch[i]; m = trimesh.Trimesh(v, h.simplices, process=False); np.random.seed(i)
            pts = np.vstack([v[h.vertices], m.sample(max(60, int(m.area * DB)))])
            s.bcache[i] = pts[~s.inside_any(pts, skip=i, eps=EPS)]
        return s.bcache[i]
    def depth(s, q):
        ph = np.full(len(q), -np.inf)
        for lo, hi, e in s.H:
            k = np.where(np.all((q >= lo) & (q <= hi), 1))[0]
            if len(k): ph[k] = np.maximum(ph[k], -(q[k] @ e[:, :3].T + e[:, 3]).max(1))
        inside = ph > 0; ud = np.zeros(len(q))
        if inside.any():
            lo, hi = q[inside].min(0) - PAD, q[inside].max(0) + PAD
            sel = np.where(np.all((s.hi >= lo) & (s.lo <= hi), 1))[0]
            B = np.vstack([s.boundary(i) for i in sel]); ud[inside] = cKDTree(B).query(q[inside])[0]
        return np.maximum(ph, 0) * 1e3, ud * 1e3
_o = {}
def obj(d, n):
    for dd in d.split(','):
        p = f'{dd}/{n}.npz'
        if os.path.exists(p):
            if p not in _o: _o[p] = Obj(p)
            return _o[p]
for arg in sys.argv[1:]:
    lab, d = arg.split('=', 1)
    for ep, f, a, b in CASES:
        A, Bo = obj(d, a), obj(d, b)
        df = pd.read_parquet(P % ep); fi = f if f >= 0 else len(df) - 1
        pose = {x['name']: x['pose'] for x in df['observation.objects'].iloc[fi]}; Ma, Mb = T(pose[a]), T(pose[b])
        ab_ph, ab_ud = Bo.depth(tr(np.linalg.inv(Mb) @ Ma, A.S)); ba_ph, ba_ud = A.depth(tr(np.linalg.inv(Ma) @ Mb, Bo.S))
        print(f'{lab:6s} ep{ep:<2d} f{fi:<4d} {a:13s} vs {b:17s}: A-in-B per-hull {ab_ph.max():4.1f} union {ab_ud.max():4.1f} | '
              f'B-in-A per-hull {ba_ph.max():4.1f} union {ba_ud.max():4.1f}', flush=True)
