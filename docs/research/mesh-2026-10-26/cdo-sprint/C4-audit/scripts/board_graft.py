"""C4 addendum 1: graft library_v3's board-2 protrusions onto the shipped occupancy plate (GT-free).
Reads only our meshes and our observed points. Writes OUT_DIR/wooden_piece_2_graft_v1.glb, _v2.glb and graft.json.
Usage: board_graft.py OCC.glb LIBV3.glb OBS.npz OUT_DIR
"""
import json, os, sys
import numpy as np, trimesh
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial import cKDTree

occ_p, lib_p, obs_p, out = sys.argv[1:5]
os.makedirs(out, exist_ok=True)
occ = trimesh.load(occ_p, force='mesh'); lib = trimesh.load(lib_p, force='mesh')
xs = occ.sample(40000, return_index=False) if False else trimesh.sample.sample_surface(occ, 40000, seed=0)[0]
c = xs.mean(0); w, V = np.linalg.eigh(np.cov((xs - c).T)); n, e1, e2 = V[:, 0], V[:, 2], V[:, 1]
h = (xs - c) @ n
lo, hi = np.percentile(h, [10, 90]); mid = 0.5 * (lo + hi); t = hi - lo
# occupancy-plate protrusions (its own balls): beyond the slab by > 1 mm
occ_out = xs[np.abs(h - mid) > t / 2 + 1e-3]
# outline footprint of the occ plate in-plane (2D hull), expanded 10 mm
uv = np.c_[(xs - c) @ e1, (xs - c) @ e2]
from scipy.spatial import Delaunay
hull = Delaunay(uv[np.random.default_rng(0).choice(len(uv), 4000, replace=False)])
fc = lib.triangles_center
hf = (fc - c) @ n
uvf = np.c_[(fc - c) @ e1, (fc - c) @ e2]
inside = hull.find_simplex(uvf) >= 0
if (~inside).any():                      # within 10 mm of the footprint counts as inside
    tree_uv = cKDTree(uv)
    d, _ = tree_uv.query(uvf[~inside])
    inside[np.where(~inside)[0][d <= 0.010]] = True
prot = (np.abs(hf - mid) > t / 2 + 1e-3) & inside
idx = np.where(prot)[0]
info = dict(occ=occ_p, lib=lib_p, obs=obs_p, t_mm=round(t * 1e3, 2), n_prot_faces=int(len(idx)), clusters=[])
keep_v1, keep_v2 = [], []
if len(idx):
    lab = fcluster(linkage(fc[idx], 'single'), 0.010, 'distance') if len(idx) > 1 else np.array([1])
    obs = np.load(obs_p)['pts'].astype(float)
    tree_obs = cKDTree(obs)
    tree_occ = cKDTree(occ_out) if len(occ_out) else None
    for k in np.unique(lab):
        f = idx[lab == k]
        cen = fc[f].mean(0)
        rec = dict(cluster=int(k), faces=int(len(f)), centre_mm=np.round((cen - c) * 1e3, 1).tolist(),
                   side=int(np.sign(((fc[f] - c) @ n).mean() - mid)))
        if len(f) < 20:
            rec['drop'] = '< 20 faces'; info['clusters'].append(rec); continue
        if tree_occ is not None and tree_occ.query(fc[f])[0].min() < 0.012:
            rec['drop'] = 'within 12 mm of an occupancy-plate protrusion'; info['clusters'].append(rec); continue
        sub = lib.submesh([f], append=True)
        samp = trimesh.sample.sample_surface(sub, 500, seed=1)[0]
        near = tree_obs.query_ball_point(samp, 0.003)
        sup = len(set(i for l in near for i in l))
        rec['obs_support_pts'] = int(sup); rec['supported'] = bool(sup >= 30)
        keep_v2.append(f)
        if sup >= 30:
            keep_v1.append(f)
        info['clusters'].append(rec)
for name, keep in (('v1', keep_v1), ('v2', keep_v2)):
    parts = [occ] + ([lib.submesh([np.concatenate(keep)], append=True)] if keep else [])
    m = trimesh.util.concatenate(parts)
    p = os.path.join(out, f'wooden_piece_2_graft_{name}.glb')
    m.export(p)
    info[name] = dict(path=p, faces=int(len(m.faces)), n_clusters=len(keep),
                      md5=__import__('hashlib').md5(open(p, 'rb').read()).hexdigest())
json.dump(info, open(os.path.join(out, 'graft.json'), 'w'), indent=1)
print(json.dumps(info, indent=1))
