"""Which end of the spoon is inside the container? Interaction-consistency check of spoon tracks (GT-free).
Approach-1 study, 2026-10-25.

Our spoon mesh (template) has its bowl at the -z end (z in [-14.4, -4.8] cm, 4.6-5.2 cm wide) and the handle toward +z
(about 2 cm wide). People stir and scoop with the bowl, so in frames where exactly one end of the spoon is inside the
container's convex hull (pot or cup: cavity included), the bowl end should be the one inside. A track whose handle end
is inside in most such frames is end-flipped [H]. Rack episodes are reported but not judged (a utensil holder can take
a spoon handle-first). Inputs: the reference parquet and its simulator meshes only.
Usage: python spoon_end_check.py ROOT OUT.json"""
import glob, json, os, sys

import numpy as np
import trimesh
from scipy.spatial import Delaunay

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pair_overlap as po  # noqa: E402

BOWL = np.array([0.0, 0.0, -0.096]); HANDLE = np.array([0.0, 0.0, 0.16])   # spoon frame, metres
root, out = sys.argv[1:3]
res = {}
for ref in sorted(glob.glob(f'{root}/**/ref_sf.parquet', recursive=True)):
    import pyarrow.parquet as pq
    names = list(pq.read_table(ref, columns=['object_body_names']).to_pylist()[0]['object_body_names'])
    if 'wooden_spoon' not in names or len(names) != 2:
        continue
    cont = [n for n in names if n != 'wooden_spoon'][0]
    ep = ref.split('/refs/sf/')[1].split('/')[0]
    base = ref.split('/processed/')[0]
    cm = trimesh.load(f'{base}/assets/mesh/{cont}/{cont}.glb', force='mesh')
    hull = Delaunay(np.asarray(cm.convex_hull.vertices))
    TS, TC = po.load_poses(ref, 'wooden_spoon', cont)
    n_b = n_h = n_both = 0
    for t in range(len(TS)):
        T = np.linalg.inv(TC[t]) @ TS[t]                         # spoon -> container frame
        pb, ph = T[:3, :3] @ BOWL + T[:3, 3], T[:3, :3] @ HANDLE + T[:3, 3]
        ib, ih = hull.find_simplex(pb) >= 0, hull.find_simplex(ph) >= 0
        n_b += ib and not ih; n_h += ih and not ib; n_both += ib and ih
    judged = cont != 'plastic_dish_rack'
    verdict = ('bowl in (consistent)' if n_b > 3 * max(n_h, 1) else 'HANDLE IN (end-flip suspected)' if n_h > 3 * max(n_b, 1) else 'mixed') if judged and (n_b + n_h) >= 10 else 'not judged'
    res[ep] = dict(container=cont, frames=len(TS), bowl_only_inside=int(n_b), handle_only_inside=int(n_h), both_inside=int(n_both), verdict=verdict)
    print(ep, res[ep], flush=True)
json.dump(res, open(out, 'w'), indent=1)
