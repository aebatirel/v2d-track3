"""G3 trim copy (C4 PREREG s12 step 3), generalised from C4-audit/scripts/rack_trim.py (addendum 6), GT-free.
Deletes every face of MESH whose centroid is > THR from BOTH:
  (a) our observed points of the object (union of the given obs_points.py npz files: the episodes used for the object's
      G3 crops / view sets; object frame), and
  (b) the surface of REF (the object's 13h mesh, ours; 200000 surface samples, seed 0, as rack_trim.py).
No hole filling. For speed the observed-point union is reduced to one point per 1 mm voxel (the point nearest the voxel's
mean is not needed: any member is within 0.87 mm, negligible against THR = 15 mm).
Reads only our meshes and our observed points (no scan, mocap, parquet pose or *_align).
Usage: trim.py MESH.glb REF.glb OUT.glb THR_MM OBS.npz [OBS.npz ...]
"""
import hashlib, json, sys
import numpy as np, trimesh
from scipy.spatial import cKDTree

mesh_p, ref_p, out, thr_mm = sys.argv[1:5]
obs_ps = sys.argv[5:]
thr = float(thr_mm) / 1000
m0 = trimesh.load(mesh_p, force='mesh'); ref = trimesh.load(ref_p, force='mesh')
P = np.concatenate([np.load(p)['pts'].astype(float) for p in obs_ps])
n_obs = len(P)
_, i = np.unique(np.floor(P / 0.001).astype(np.int64), axis=0, return_index=True)
P = P[np.sort(i)]
fc = m0.triangles_center
d_obs = cKDTree(P).query(fc)[0]
d_ref = cKDTree(trimesh.sample.sample_surface(ref, 200000, seed=0)[0]).query(fc)[0]
keep = ~((d_obs > thr) & (d_ref > thr))
m = m0.submesh([np.where(keep)[0]], append=True)
m.export(out)
info = dict(mesh=mesh_p, ref=ref_p, obs=obs_ps, obs_points=int(n_obs), obs_points_1mm=int(len(P)),
            faces_in=int(len(m0.faces)), faces_removed=int((~keep).sum()), faces_out=int(len(m.faces)),
            area_removed_frac=round(float(m0.area_faces[~keep].sum() / m0.area), 5),
            removed_centroid_mm=np.round(fc[~keep].mean(0) * 1e3, 1).tolist() if (~keep).any() else None,
            extents_in_mm=np.round(m0.extents * 1e3, 1).tolist(), extents_out_mm=np.round(m.extents * 1e3, 1).tolist(),
            md5=hashlib.md5(open(out, 'rb').read()).hexdigest(), thr_mm=thr * 1e3)
json.dump(info, open(out + '.json', 'w'), indent=1)
print(json.dumps({k: v for k, v in info.items() if k not in ('obs',)}))
