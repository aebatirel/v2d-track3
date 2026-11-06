"""GT-free: geometry of OUR cup meshes (library_v3): symmetry axis, extents along it, radius profile, ray hits along
the axis (is the interior open?). No mocap, no scans."""
import sys, json
import numpy as np, trimesh
sys.path.insert(0, '/home/user/v2d-track3/pipeline')
import refine, offsetfix
for n in ['blue_cup', 'beige_cup']:
    o = refine.Obj(n, f'/home/user/v2d-track3/meshes/library_v3/{n}.glb')
    ax = offsetfix.body_axis(o)
    P = offsetfix.mesh_model(o)[0]
    c = P.mean(0)
    h = (P - c) @ ax
    if np.abs(h.min()) > np.abs(h.max()):   # orient: base is where the radius profile is ... decide later
        pass
    rad = np.linalg.norm((P - c) - h[:, None] * ax, axis=1)
    bins = np.linspace(h.min(), h.max(), 18)
    prof = []
    for i in range(len(bins) - 1):
        m = (h >= bins[i]) & (h < bins[i + 1])
        prof.append([round(float((bins[i] + bins[i + 1]) / 2 * 100), 1), int(m.sum()), round(float(np.percentile(rad[m], 10) * 100), 2) if m.sum() else None,
                     round(float(np.percentile(rad[m], 90) * 100), 2) if m.sum() else None])
    w, U = np.linalg.eigh(np.cov((P - c).T))
    # ray along axis from both ends
    mesh = o.mesh
    hits = {}
    for sgn in (+1, -1):
        org = c + sgn * ax * 0.2
        loc, _, _ = mesh.ray.intersects_location([org], [-sgn * ax], multiple_hits=True)
        hits['from +' if sgn > 0 else 'from -'] = sorted(round(float((x - c) @ ax * 100), 2) for x in loc)
    # also rays parallel to axis at radius 1.5 cm
    off = np.cross(ax, [1, 0, 0]); off /= np.linalg.norm(off)
    loc, _, _ = mesh.ray.intersects_location([c + ax * 0.2 + off * 0.015], [-ax], multiple_hits=True)
    hits['r1.5 from +'] = sorted(round(float((x - c) @ ax * 100), 2) for x in loc)
    print(n, json.dumps(dict(axis=np.round(ax, 4).tolist(), eig=np.round(w * 1e4, 3).tolist(), V_centroid=np.round(o.V.mean(0), 4).tolist(),
                             sample_centroid=np.round(c, 4).tolist(), h_range_cm=[round(float(h.min() * 100), 2), round(float(h.max() * 100), 2)],
                             watertight=bool(mesh.is_watertight), volume_cm3=round(float(abs(mesh.volume)) * 1e6, 1) if mesh.is_watertight else None,
                             hull_volume_cm3=round(float(mesh.convex_hull.volume) * 1e6, 1), hits=hits)))
    for r in prof:
        print('   h %6.1f n %6d r10 %s r90 %s' % tuple(r))
