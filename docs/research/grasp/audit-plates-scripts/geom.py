"""Object geometry from our library_v3 meshes (and the simulator copies): extents, PCA axes, cross-section
thickness profiles, candidate handle, wall thickness. Our meshes only (no ground truth)."""
import sys, json
import numpy as np, trimesh
from scipy.spatial.transform import Rotation as R

def load(p):
    m = trimesh.load(p, force='mesh'); return m

out = {}
for name, p, psim in [('mini_sweeper', sys.argv[1] + '/mini_sweeper.glb', sys.argv[2] + '/mini_sweeper/mini_sweeper.glb'),
                      ('mini_dust_pan', sys.argv[1] + '/mini_dust_pan.glb', sys.argv[2] + '/mini_dust_pan/mini_dust_pan.glb')]:
    m = load(p); ms = load(psim)
    same = (len(m.vertices) == len(ms.vertices)) and np.allclose(np.sort(m.vertices, 0), np.sort(ms.vertices, 0), atol=1e-6)
    V = m.vertices; c = V.mean(0)
    U, S, Wt = np.linalg.svd(V - c, full_matrices=False)
    ax = Wt  # rows = principal axes
    P = (V - c) @ ax.T
    ext = P.max(0) - P.min(0)
    info = dict(watertight=bool(m.is_watertight), volume_cm3=round(float(m.volume) * 1e6, 1) if m.is_watertight else None,
                area_cm2=round(float(m.area) * 1e4, 1), bbox_cm=[round(100 * x, 1) for x in (m.bounds[1] - m.bounds[0])],
                pca_extents_cm=[round(100 * x, 1) for x in ext], pca_axes=[[round(float(x), 3) for x in a] for a in ax],
                centroid_obj_cm=[round(100 * x, 2) for x in c], sim_copy_same_vertices=bool(same),
                pca_ratio=round(float(S[0] / S[1]), 2), pca_ratio_13=round(float(S[0] / S[2]), 2))
    # cross-sections along the longest axis: width (axis 2) and thickness (axis 3) per 1 cm slab
    prof = []
    pts, _ = trimesh.sample.sample_surface_even(m, 40000, seed=0)
    Pp = (pts - c) @ ax.T
    lo, hi = Pp[:, 0].min(), Pp[:, 0].max()
    for s0 in np.arange(lo, hi, 0.01):
        k = (Pp[:, 0] >= s0) & (Pp[:, 0] < s0 + 0.01)
        if k.sum() < 20:
            continue
        w = Pp[k, 1].max() - Pp[k, 1].min(); th = Pp[k, 2].max() - Pp[k, 2].min()
        prof.append((round(100 * (s0 + 0.005), 1), round(100 * w, 1), round(100 * th, 1), int(k.sum())))
    info['profile_axis1_cm'] = prof
    # same along axis 2
    prof2 = []
    lo, hi = Pp[:, 1].min(), Pp[:, 1].max()
    for s0 in np.arange(lo, hi, 0.01):
        k = (Pp[:, 1] >= s0) & (Pp[:, 1] < s0 + 0.01)
        if k.sum() < 20:
            continue
        prof2.append((round(100 * (s0 + 0.005), 1), round(100 * (Pp[k, 0].max() - Pp[k, 0].min()), 1), round(100 * (Pp[k, 2].max() - Pp[k, 2].min()), 1)))
    info['profile_axis2_cm'] = prof2
    # local wall thickness: ray from each sample inward along -normal, distance to the next hit
    try:
        sp, fi = trimesh.sample.sample_surface_even(m, 3000, seed=1)
        nrm = m.face_normals[fi]
        locs, ir, _ = m.ray.intersects_location(sp - nrm * 1e-4, -nrm, multiple_hits=False)
        d = np.full(len(sp), np.nan); d[ir] = np.linalg.norm(locs - sp[ir], axis=1)
        info['wall_thickness_mm_p10_p50_p90'] = [round(1000 * float(np.nanpercentile(d, q)), 1) for q in (10, 25, 50, 75, 90)]
        info['wall_thin_share_lt8mm'] = round(float(np.nanmean(d < 0.008)), 3)
        info['wall_thin_share_lt15mm'] = round(float(np.nanmean(d < 0.015)), 3)
    except Exception as e:
        info['wall_err'] = str(e)
    out[name] = info
json.dump(out, open(sys.argv[3], 'w'), indent=1)
for k, v in out.items():
    print(k, {kk: vv for kk, vv in v.items() if not kk.startswith('profile')})
    print(' axis1 profile (pos, width, thick, n):', v['profile_axis1_cm'])
    print(' axis2 profile (pos, len1, thick):', v['profile_axis2_cm'])
