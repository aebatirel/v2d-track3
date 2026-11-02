"""C4 addendum 3: board-2 round-2 variants from graft_v1 (GT-free; our meshes only).
v3 = graft_v1 + library_v3 cluster 1 (face +1 feature); v4 = graft_v1 with the occupancy slab re-extruded to
library_v3's slab thickness; v5 = v4 + cluster 1.
Usage: board_graft2.py OCC.glb LIBV3.glb GRAFT_V1.glb OUT_DIR
"""
import hashlib, json, os, sys
import numpy as np, trimesh
from scipy.cluster.hierarchy import fcluster, linkage

occ_p, lib_p, v1_p, out = sys.argv[1:5]
os.makedirs(out, exist_ok=True)
occ = trimesh.load(occ_p, force='mesh'); lib = trimesh.load(lib_p, force='mesh'); v1 = trimesh.load(v1_p, force='mesh')


def frame(m):
    x = trimesh.sample.sample_surface(m, 40000, seed=0)[0]
    c = x.mean(0); w, V = np.linalg.eigh(np.cov((x - c).T)); n = V[:, 0]
    h = (x - c) @ n; lo, hi = np.percentile(h, [10, 90])
    return c, n, 0.5 * (lo + hi), hi - lo


c, n, mid, t_occ = frame(occ)
cl, nl, midl, t_lib = frame(lib)
if n @ nl < 0:
    nl = -nl
# --- cluster 1 of board_graft.py: library faces beyond the occ slab, on face +1, the small feature (not the sheet)
fc = lib.triangles_center
hf = (fc - c) @ n
idx = np.where(np.abs(hf - mid) > t_occ / 2 + 1e-3)[0]
lab = fcluster(linkage(fc[idx], 'single'), 0.010, 'distance')
best = None
for k in np.unique(lab):
    f = idx[lab == k]
    side = np.sign(((fc[f] - c) @ n).mean() - mid)
    if side > 0 and 20 <= len(f) <= 500:          # the small +1 feature (cluster 1 had 69 faces); the sheet had 2335
        cen = (fc[f].mean(0) - c) * 1e3
        if best is None or len(f) > len(best[0]):
            best = (f, cen)
feat = lib.submesh([best[0]], append=True) if best is not None else None
# --- v4: re-extrude graft_v1's occupancy part to library_v3's slab thickness
n_occ_faces = len(occ.faces)
v = v1.vertices.copy()
occ_vid = np.unique(v1.faces[:n_occ_faces])          # graft_v1 = concatenate([occ, library balls]): occ faces first
hv = (v[occ_vid] - c) @ n - mid
inside = np.abs(hv) <= t_occ / 2 + 5e-4
scale = t_lib / t_occ
newh = np.where(inside, hv * scale, hv + np.sign(hv) * (t_lib - t_occ) / 2)
v[occ_vid] = v[occ_vid] + np.outer(newh - hv, n)
v4 = trimesh.Trimesh(v, v1.faces.copy(), process=False)
info = dict(t_occ_mm=round(t_occ * 1e3, 2), t_lib_mm=round(t_lib * 1e3, 2), scale=round(scale, 4),
            feature_faces=int(len(best[0])) if best is not None else 0,
            feature_centre_mm=np.round(best[1], 1).tolist() if best is not None else None)
for name, m in (('v3', trimesh.util.concatenate([v1, feat]) if feat is not None else v1), ('v4', v4),
                ('v5', trimesh.util.concatenate([v4, feat]) if feat is not None else v4)):
    p = os.path.join(out, f'wooden_piece_2_graft_{name}.glb')
    m.export(p)
    info[name] = dict(path=p, faces=int(len(m.faces)), md5=hashlib.md5(open(p, 'rb').read()).hexdigest(),
                      extents_mm=np.round(m.extents * 1e3, 1).tolist())
json.dump(info, open(os.path.join(out, 'graft2.json'), 'w'), indent=1)
print(json.dumps(info, indent=1))
