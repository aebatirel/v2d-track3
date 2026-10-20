# Verifier: is the per-hull depth metric (max over hulls of inward plane distance; b_eval/pen2) a fair proxy for depth
# inside the hull UNION when objects are finely split? Union depth = distance from a penetrating point to the nearest
# union-boundary sample (hull-surface samples not inside any other hull by > EPS). Lid/pot GT states only.
# usage: v_uniondepth.py LABEL=lid_npz,pot_npz ...
import sys, numpy as np, pandas as pd, trimesh
from scipy.spatial import ConvexHull, cKDTree
from scipy.spatial.transform import Rotation as R
P = '/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public/data/chunk-000/episode_%06d.parquet'
EPS = 5e-5; DB = 4e6; DQ = 0.25e6
def load(p):
    d = np.load(p); return [d[f'v{i}'] for i in range(int(d['n']))]
def T(pose):
    x, y, z, qw, qx, qy, qz = pose; M = np.eye(4); M[:3, :3] = R.from_quat([qx, qy, qz, qw]).as_matrix(); M[:3, 3] = [x, y, z]; return M
def tr(M, p): return p @ M[:3, :3].T + M[:3, 3]
class U:
    def __init__(s, hv):
        s.H = [(v.min(0), v.max(0), ConvexHull(v).equations) for v in hv]; s.hv = hv
        bs = []
        for i, v in enumerate(hv):
            h = ConvexHull(v); m = trimesh.Trimesh(v, h.simplices, process=False); np.random.seed(i)
            pts = np.vstack([v[h.vertices], m.sample(max(60, int(m.area * DB)))])
            keep = np.ones(len(pts), bool)
            for j, (lo, hi, e) in enumerate(s.H):
                if j == i: continue
                k = np.where(keep & np.all((pts >= lo - EPS) & (pts <= hi + EPS), 1))[0]
                if len(k) == 0: continue
                keep[k[(pts[k] @ e[:, :3].T + e[:, 3]).max(1) <= EPS]] = False
            bs.append(pts[keep])
        s.B = np.vstack(bs); s.kd = cKDTree(s.B)
    def query(s, q):
        ph = np.full(len(q), -np.inf)
        for lo, hi, e in s.H:
            k = np.where(np.all((q >= lo) & (q <= hi), 1))[0]
            if len(k) == 0: continue
            ph[k] = np.maximum(ph[k], -(q[k] @ e[:, :3].T + e[:, 3]).max(1))
        inside = ph > 0
        ud = np.zeros(len(q)); ud[inside] = s.kd.query(q[inside])[0]
        return np.maximum(ph, 0), ud
    def samples(s):
        out = []
        for i, v in enumerate(s.hv):
            h = ConvexHull(v); m = trimesh.Trimesh(v, h.simplices, process=False); np.random.seed(100 + i)
            out.append(np.vstack([v[h.vertices], m.sample(max(50, int(m.area * DQ)))]))
        return np.vstack(out)
CASES = [(0, 0), (2, 0), (0, -1), (0, 28), (2, 314)]
for arg in sys.argv[1:]:
    lab, paths = arg.split('='); pl, pp = paths.split(',')
    L, Pt = U(load(pl)), U(load(pp)); sl, sp = L.samples(), Pt.samples()
    for ep, f in CASES:
        df = pd.read_parquet(P % ep); fi = f if f >= 0 else len(df) - 1
        pose = {x['name']: x['pose'] for x in df['observation.objects'].iloc[fi]}
        Ml, Mp = T(pose['white_pot_lid']), T(pose['white_pot'])
        a_ph, a_ud = Pt.query(tr(np.linalg.inv(Mp) @ Ml, sl))   # lid hull samples in pot union
        b_ph, b_ud = L.query(tr(np.linalg.inv(Ml) @ Mp, sp))    # pot hull samples in lid union
        print(f'{lab:6s} ep{ep} f{fi:<4d} lid-in-pot per-hull max {a_ph.max()*1e3:4.1f} union max {a_ud.max()*1e3:4.1f} | '
              f'pot-in-lid per-hull {b_ph.max()*1e3:4.1f} union {b_ud.max()*1e3:4.1f} | nbound {len(Pt.B)}/{len(L.B)}', flush=True)
