"""GT-free: geometry of the eval-10 collision pieces (meshes/carve/ev10) in our mesh frame: axis, extent along it,
inner floor (lowest point of the cavity along the axis)."""
import glob, sys, json
import numpy as np, trimesh
sys.path.insert(0, '/home/user/v2d-track3/pipeline')
import refine, offsetfix
for n in ['blue_cup', 'beige_cup']:
    o = refine.Obj(n, f'/home/user/v2d-track3/meshes/library_v3/{n}.glb')
    ax_m = offsetfix.body_axis(o)
    pcs = [trimesh.load(f, force='mesh') for f in sorted(glob.glob(f'/home/user/v2d-track3/meshes/carve/ev10/{n}/piece_*.obj'))]
    V = np.concatenate([p.vertices for p in pcs])
    c = V.mean(0)
    w, U = np.linalg.eigh(np.cov((V - c).T)); k = int(np.argmax([abs(w[i] - np.mean(np.delete(w, i))) for i in range(3)])); ax = U[:, k]
    if ax @ ax_m < 0: ax = -ax
    h = (V - c) @ ax
    comb = trimesh.util.concatenate(pcs)
    hits = {}
    for r in (0.0, 0.01, 0.02):
        off = np.cross(ax, [1, 0, 0]); off /= np.linalg.norm(off)
        res = []
        for sgn in (1, -1):
            loc, _, _ = comb.ray.intersects_location([c + sgn * ax * 0.2 + off * r], [-sgn * ax], multiple_hits=True)
            res.append(sorted(round(float((x - c) @ ax * 100), 2) for x in loc))
        hits[r] = res
    print(n, 'pieces', len(pcs), 'axis', np.round(ax, 4).tolist(), 'angle to mesh PCA axis', round(float(np.degrees(np.arccos(min(1, abs(ax @ ax_m))))), 1),
          'centroid(pieces verts)', np.round(c, 4).tolist(), 'mesh V centroid', np.round(o.V.mean(0), 4).tolist(), 'h range', round(h.min() * 100, 2), round(h.max() * 100, 2))
    print('   ray hits along axis at radius 0/1/2 cm (from + end, from - end):', json.dumps(hits))
    hm = (o.V - c) @ ax
    print('   our mesh along the pieces axis:', round(hm.min() * 100, 2), round(hm.max() * 100, 2))
