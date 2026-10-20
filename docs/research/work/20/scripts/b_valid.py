# Validation of the marker pipeline on public episodes with GT: detected sphere centres (rect-c frame) vs scan-catalogue
# marker centres placed by GT (mocap world, z up). Heights above the table: measured vs GT (z - min z of the resting mesh).
# Analysis only (public GT). Usage: b_valid.py p23 [k]
import sys, json, itertools, numpy as np, pandas as pd, trimesh
from scipy.spatial.transform import Rotation as Rot
sys.path.insert(0, '.'); from b_lib import *
tag = sys.argv[1]; ep = int(tag[1:]); kk = int(sys.argv[2]) if len(sys.argv) > 2 else 0
cat = json.load(open('/Users/aebatirel/Documents/Code/v2d-research/work/17/out/marker_catalogue.json'))
d = pd.read_parquet(f'{D}/public/data/chunk-000/episode_{ep:06d}.parquet'); objs = d['observation.objects'].iloc[kk]
G, Gh, Gn = [], [], []
for o in objs:
    p = np.array(o['pose'], float); Rw = Rot.from_quat([p[4], p[5], p[6], p[3]]).as_matrix()
    import glob; m = trimesh.load([f for f in sorted(glob.glob(f"{D}/public/mesh/{o['name']}/*.glb")) if "collision" not in f][0], force="mesh"); zt = (m.vertices @ Rw.T + p[:3])[:, 2].min()
    for i, mk in enumerate(cat.get(o['name'], [])):
        X = Rw @ np.array(mk['c']) + p[:3]; G.append(X); Gh.append((X[2] - zt) * 1e3); Gn.append(f"{o['name']}#{i}")
    print(o['name'], 'table z (min mesh z) %.4f' % zt)
G = np.array(G); Gh = np.array(Gh)
rec = [r for r in json.load(open(f'{OUT}/meas_{tag}.json')) if r['k'] == kk][0]
C = [c for c in rec['cands'] if c['ncc'] > 0.8 and not c['edge']]; P = np.array([c['X_r'] for c in C])
def kabsch(A, B):
    ca, cb = A.mean(0), B.mean(0); U, S, Vt = np.linalg.svd((A - ca).T @ (B - cb)); Dm = np.diag([1, 1, np.sign(np.linalg.det(Vt.T @ U.T))])
    Rm = Vt.T @ Dm @ U.T; return Rm, cb - Rm @ ca
best = None
for ci in itertools.combinations(range(len(P)), 3):
    dc = [np.linalg.norm(P[a] - P[b]) for a, b in itertools.combinations(ci, 2)]
    for gi in itertools.permutations(range(len(G)), 3):
        dg = [np.linalg.norm(G[a] - G[b]) for a, b in itertools.combinations(gi, 2)]
        if max(abs(x - y) for x, y in zip(dc, dg)) > 0.008: continue
        Rm, t = kabsch(P[list(ci)], G[list(gi)]); Q = P @ Rm.T + t
        dd = np.linalg.norm(Q[:, None] - G[None], axis=2); j = dd.argmin(1); inl = dd[np.arange(len(P)), j] < 0.010
        if best is None or inl.sum() > best[0] or (inl.sum() == best[0] and dd[np.arange(len(P)), j][inl].mean() < best[1]):
            best = (inl.sum(), dd[np.arange(len(P)), j][inl].mean(), ci, gi)
_, _, ci, gi = best
# refit on all inliers
Rm, t = kabsch(P[list(ci)], G[list(gi)])
for _ in range(3):
    Q = P @ Rm.T + t; dd = np.linalg.norm(Q[:, None] - G[None], axis=2); j = dd.argmin(1); inl = dd[np.arange(len(P)), j] < 0.010
    Rm, t = kabsch(P[inl], G[j[inl]])
Q = P @ Rm.T + t; res = np.linalg.norm(Q - G[j], axis=1)
nw = Rm @ np.array(rec['plane_g_n']); print(f'{tag} k{kk}: matched {inl.sum()}/{len(P)} | table normal in world {nw.round(4)} (tilt {np.degrees(np.arccos(abs(nw[2]))):.2f} deg)')
for i in np.nonzero(inl)[0]:
    c = C[i]; print(f'  {Gn[j[i]]:18s} uv ({c["uv"][0]:.0f},{c["uv"][1]:.0f}) r {c["r"]:.1f} ncc {c["ncc"]:.2f} | 3D res {res[i]*1e3:.1f} mm '
                    f'(world dz {(Q[i]-G[j[i]])[2]*1e3:+.1f}) | h meas {c["hg_mm"]:.1f} gt {Gh[j[i]]:.1f} diff {c["hg_mm"]-Gh[j[i]]:+.1f}')
print('  rms 3D', np.sqrt(np.mean(res[inl] ** 2)) * 1e3, 'mean h diff', np.mean([C[i]['hg_mm'] - Gh[j[i]] for i in np.nonzero(inl)[0]]))
# --- SGBM surface check: plank top surfaces vs GT (selection by the Kabsch map; heights from the measured table plane)
import glob
Dm = np.load(f'{OUT}/disp_{tag}_k{kk}.npy'); pc_, pn_ = np.array(rec['plane_g_c']), np.array(rec['plane_g_n'])
yy, xx = np.mgrid[0:RSZ[1], 0:RSZ[0]]; ok = Dm > 32
X = tri_rect(xx[ok].astype(float), yy[ok].astype(float), xx[ok] - Dm[ok], yy[ok].astype(float)); hm = (X - pc_) @ pn_ * 1e3
W = X @ Rm.T + t
for o in objs:
    p = np.array(o['pose'], float); Rw = Rot.from_quat([p[4], p[5], p[6], p[3]]).as_matrix()
    m = trimesh.load([f for f in sorted(glob.glob(f"{D}/public/mesh/{o['name']}/*.glb")) if "collision" not in f][0], force="mesh")
    Vw = m.vertices @ Rw.T + p[:3]; zt = Vw[:, 2].min()
    # object frame coords of the measured points; inside the footprint shrunk by 12 mm, away from markers
    Lo = (W - p[:3]) @ Rw; lo, hi = m.vertices.min(0) + 0.012, m.vertices.max(0) - 0.012
    up = np.argmax(np.abs(Rw[2]))   # object axis closest to world z
    ins = np.ones(len(Lo), bool)
    for a in range(3):
        if a != up: ins &= (Lo[:, a] > lo[a]) & (Lo[:, a] < hi[a])
    mk = np.array([Rw @ np.array(c['c']) + p[:3] for c in cat[o['name']]])
    ins &= np.min(np.linalg.norm(W[:, None, :2] - mk[None, :, :2], axis=2), axis=1) > 0.02
    # GT top surface height: ray-cast down at the selected xy
    sel = np.nonzero(ins)[0][::5]
    if len(sel) == 0: continue
    from scipy.spatial import cKDTree
    tr_ = cKDTree(Vw[:, :2]); nb = tr_.query_ball_point(W[sel, :2], 0.003)
    ri = np.array([i for i, n in enumerate(nb) if len(n) > 0]); gt_top = np.array([Vw[nb[i], 2].max() - zt for i in ri])
    print(f'  {o["name"]}: plank top surface, n {len(ri)} | measured h median {np.median(hm[sel][ri]):.1f} mm (IQR {np.percentile(hm[sel][ri],25):.1f}-{np.percentile(hm[sel][ri],75):.1f}) '
          f'| GT {np.median(gt_top*1e3):.1f} mm | diff {np.median(hm[sel][ri] - gt_top*1e3):+.1f}')
