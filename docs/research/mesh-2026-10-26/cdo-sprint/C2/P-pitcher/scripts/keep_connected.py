"""C2/P PREREG amendment A2 (GT-free): the object is one connected rigid body, so a candidate keeps only the mesh
components linked to its largest-area component. Two components are linked when the nearest distance between their
vertices is <= LINK = 8 mm (2 vote voxels of obs_points, C0b AUDIT id 142); links are followed transitively.
Components not in that set (static clutter or co-object residue that the 0.30 m cube admitted and lathe_obs splatted
as an 'appendage') are dropped. A mesh with one component is copied unchanged (byte for byte); the .lathe.json is
copied alongside. Writes OUT.glb and OUT.keep.json (kept / dropped components: faces, area, centroid, extents).
Usage: keep_connected.py IN.glb OUT.glb
"""
import json, os, shutil, sys
import numpy as np
import trimesh
from scipy.spatial import cKDTree

LINK = 0.008
src, dst = sys.argv[1], sys.argv[2]
m = trimesh.load(src, force='mesh')
parts = m.split(only_watertight=False)
info = lambda p: dict(faces=int(len(p.faces)), area_cm2=round(float(p.area) * 1e4, 1),          # noqa: E731
                      centroid_mm=[round(float(x) * 1e3, 1) for x in p.centroid],
                      extents_mm=[round(float(x) * 1e3, 1) for x in p.extents], watertight=bool(p.is_watertight))
if len(parts) <= 1:
    shutil.copyfile(src, dst)
    keep, drop = parts, []
else:
    trees = [cKDTree(p.vertices) for p in parts]
    seed = int(np.argmax([p.area for p in parts]))
    kept, frontier = {seed}, [seed]
    while frontier:
        i = frontier.pop()
        for j in range(len(parts)):
            if j in kept:
                continue
            d = trees[i].query(parts[j].vertices, k=1, distance_upper_bound=LINK)[0]
            if np.isfinite(d).any():
                kept.add(j); frontier.append(j)
    keep = [parts[i] for i in sorted(kept)]
    drop = [parts[i] for i in range(len(parts)) if i not in kept]
    if drop:
        trimesh.util.concatenate(keep).export(dst)
    else:
        shutil.copyfile(src, dst)
lj = src.rsplit('.', 1)[0] + '.lathe.json'
if os.path.exists(lj):
    shutil.copyfile(lj, dst.rsplit('.', 1)[0] + '.lathe.json')
rep = dict(src=src, dst=dst, link_m=LINK, components=len(parts), kept=[info(p) for p in keep], dropped=[info(p) for p in drop],
           unchanged=not drop)
json.dump(rep, open(dst.rsplit('.', 1)[0] + '.keep.json', 'w'), indent=1)
print(os.path.basename(src), 'components', len(parts), 'kept', len(keep), 'dropped', [(d['faces'], d['area_cm2'], d['centroid_mm']) for d in rep['dropped']])
