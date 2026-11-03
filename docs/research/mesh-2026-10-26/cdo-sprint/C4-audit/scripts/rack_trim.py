"""C4 addendum 6: GT-free trim of the G2 rack. Deletes faces whose centroid is > THR from both our observed points and
the dev1 primitive rack surface. Usage: rack_trim.py G2_RACK.glb DEV1_RACK.glb OBS.npz OUT.glb [THR_MM=15]"""
import hashlib, json, sys
import numpy as np, trimesh
from scipy.spatial import cKDTree

g2_p, dev_p, obs_p, out = sys.argv[1:5]
thr = float(sys.argv[5]) / 1000 if len(sys.argv) > 5 else 0.015
g2 = trimesh.load(g2_p, force='mesh'); dev = trimesh.load(dev_p, force='mesh')
obs = np.load(obs_p)['pts'].astype(float)
fc = g2.triangles_center
d_obs = cKDTree(obs).query(fc)[0]
d_dev = cKDTree(trimesh.sample.sample_surface(dev, 200000, seed=0)[0]).query(fc)[0]
keep = ~((d_obs > thr) & (d_dev > thr))
m = g2.submesh([np.where(keep)[0]], append=True)
m.export(out)
info = dict(faces_in=int(len(g2.faces)), faces_removed=int((~keep).sum()), faces_out=int(len(m.faces)),
            removed_centroid_mm=np.round(fc[~keep].mean(0) * 1e3, 1).tolist() if (~keep).any() else None,
            extents_in_mm=np.round(g2.extents * 1e3, 1).tolist(), extents_out_mm=np.round(m.extents * 1e3, 1).tolist(),
            md5=hashlib.md5(open(out, 'rb').read()).hexdigest(), thr_mm=thr * 1e3)
json.dump(info, open(out + '.json', 'w'), indent=1)
print(json.dumps(info))
