"""PUBOWN frame and kit check (GT-free; no scoring). For every PUBOWN pick (selection.json of the box results) against
the repo's meshes/library_v3/<object>.glb, both in the object frame of the library_v3-seeded track:
  identity: area-weighted centroid offset, PCA axis angles, dense-sample median symmetric surface distance;
  rigid ICP (trimmed 90 % point-to-point, from identity, 12 k new -> 150 k library points): rotation, translation,
    centroid motion, symmetry-axis tilt (lid: minor PCA axis; cups: major axis), median residual before -> after;
  kit path: v2dlb budget_mesh(path, 4096, 4096) -> _encode_archive -> _decode_object_mesh, faces, vertices,
    watertight, bodies, volume, mesh_quality_flags, raw <-> budget deviation.
Reads only our mesh files (box results + library_v3) and the submission kit code. Adapted from the E0 verifier's
v1_frame_kit.py (identity + ICP + kit blocks; no 48-hypothesis flip test).
Usage: python -I pubown_frame_kit.py REPO KIT RESULTS OUT.json [pair,pair,...]
"""
import hashlib, json, os, sys

import numpy as np
import trimesh
from scipy.spatial import cKDTree

REPO, KIT, RES, OUT = sys.argv[1:5]
ONLY = sys.argv[5].split(',') if len(sys.argv) > 5 else None
sys.path.insert(0, KIT)
from v2dlb.mesh_budget import budget_mesh  # noqa: E402
from v2dlb.track3_pose import _encode_archive, _decode_object_mesh  # noqa: E402
from v2dlb.mesh_quality import mesh_quality_flags  # noqa: E402

SEED_N, SEED_L = 1234, 4321
SYM = {'white_pot': None, 'white_pot_lid': 2, 'plastic_dish_rack': None, 'blue_cup': 0, 'beige_cup': 0}


def h(path, algo='sha256'):
    return hashlib.new(algo, open(path, 'rb').read()).hexdigest()


def load(p):
    return trimesh.load(p, force='mesh', process=False)


def surf(m, n, seed):
    return trimesh.sample.sample_surface(m, n, seed=seed)[0]


def area_centroid(m):
    w = m.area_faces
    return (m.triangles_center * w[:, None]).sum(0) / w.sum()


def pca(m, seed):
    p = surf(m, 200000, seed)
    X = p - p.mean(0)
    ev, evec = np.linalg.eigh(X.T @ X / len(X))
    o = np.argsort(ev)[::-1]
    return ev[o], evec[:, o]


def rot_angle(R):
    return float(np.degrees(np.arccos(np.clip((np.trace(R) - 1) / 2, -1, 1))))


def kabsch(a, b):
    ca, cb = a.mean(0), b.mean(0)
    U, _, Vt = np.linalg.svd((a - ca).T @ (b - cb))
    D = np.eye(3)
    D[2, 2] = np.sign(np.linalg.det(Vt.T @ U.T))
    R = Vt.T @ D @ U.T
    return R, cb - R @ ca


def icp(src, tree, tgt, iters=80, keep=0.9):
    R, t = np.eye(3), np.zeros(3)
    prev = np.inf
    for _ in range(iters):
        x = src @ R.T + t
        d, i = tree.query(x)
        k = d <= np.quantile(d, keep)
        dR, dt = kabsch(x[k], tgt[i[k]])
        R, t = dR @ R, dR @ t + dt
        m = float(np.mean(d[k]))
        if abs(prev - m) < 1e-9:
            break
        prev = m
    d, _ = tree.query(src @ R.T + t)
    return R, t, d


def frame(new_p, lib_p, sym):
    a, b = load(new_p), load(lib_p)
    ca, cb = area_centroid(a), area_centroid(b)
    eva, va = pca(a, SEED_N)
    evb, vb = pca(b, SEED_L)
    ang = [float(np.degrees(np.arccos(min(1.0, abs(float(va[:, i] @ vb[:, i])))))) for i in range(3)]
    pa, pb = surf(a, 12000, SEED_N), surf(b, 150000, SEED_L)
    pb_s, pa_d = surf(b, 12000, SEED_L + 1), surf(a, 150000, SEED_N + 1)
    tb, ta = cKDTree(pb), cKDTree(pa_d)
    dab, _ = tb.query(pa)
    dba, _ = ta.query(pb_s)
    R, t, d_after = icp(pa, tb, pb)
    cen = pa.mean(0)
    out = dict(
        extent_mm_new=[round(float(x), 2) for x in a.extents * 1000], extent_mm_lib=[round(float(x), 2) for x in b.extents * 1000],
        centroid_offset_mm=float(np.linalg.norm(ca - cb) * 1000), centroid_delta_mm=((ca - cb) * 1000).round(3).tolist(),
        axis_angle_deg=[round(x, 3) for x in ang],
        surf_sym_median_mm=float(np.median(np.concatenate([dab, dba])) * 1000),
        icp_rot_deg=rot_angle(R), icp_trans_mm=float(np.linalg.norm(t) * 1000),
        icp_centroid_motion_mm=float(np.linalg.norm((R @ cen + t) - cen) * 1000),
        icp_trans_vec_mm=(t * 1000).round(3).tolist(),
        icp_med_before_mm=float(np.median(dab) * 1000), icp_med_after_mm=float(np.median(d_after) * 1000))
    if sym is not None:
        ax = vb[:, sym]
        out['icp_symaxis_tilt_deg'] = float(np.degrees(np.arccos(min(1.0, abs(float((R @ ax) @ ax))))))
        out['symaxis_angle_identity_deg'] = ang[sym]
    w = trimesh.Trimesh(a.vertices, a.faces, process=True)
    out['raw_new'] = dict(faces=int(len(a.faces)), vertices=int(len(a.vertices)), watertight=bool(w.is_watertight),
                          winding_consistent=bool(w.is_winding_consistent), volume_cm3=float(w.volume * 1e6),
                          bodies=int(len(w.split(only_watertight=False))))
    return out


def kit(path):
    v, f = budget_mesh(path, 4096, 4096)
    payload = _encode_archive(vertices=v, faces=f)
    dv, df = _decode_object_mesh(payload)
    keep = ~((f[:, 0] == f[:, 1]) | (f[:, 1] == f[:, 2]) | (f[:, 0] == f[:, 2]))
    m = trimesh.Trimesh(v, f[keep], process=True)
    m.remove_unreferenced_vertices()
    raw = load(path)
    d1, _ = cKDTree(surf(m, 150000, 9)).query(surf(raw, 10000, 7))
    d2, _ = cKDTree(surf(raw, 150000, 10)).query(surf(m, 10000, 8))
    return dict(payload_chars=len(payload), decoded_shape=[list(dv.shape), list(df.shape)],
                decoded_equal=bool(np.array_equal(np.asarray(dv), np.asarray(v)) and np.array_equal(np.asarray(df), np.asarray(f))),
                nonpad_faces=int(keep.sum()), vertices_used=int(len(m.vertices)), watertight=bool(m.is_watertight),
                volume_cm3=float(m.volume * 1e6), bodies=int(len(m.split(only_watertight=False))),
                finite=bool(np.isfinite(v).all()), quality_flags=mesh_quality_flags(v, f),
                raw_to_budget_p50_max_mm=[float(np.median(d1) * 1000), float(d1.max() * 1000)],
                budget_to_raw_p50_max_mm=[float(np.median(d2) * 1000), float(d2.max() * 1000)])


sel = json.load(open(os.path.join(RES, 'selection.json')))['selection']
res = dict(script=os.path.relpath(os.path.abspath(__file__), REPO), library='meshes/library_v3', pairs={}, library_kit={})
if os.path.exists(OUT):
    res = json.load(open(OUT))
for pair, s in sorted(sel.items()):
    if ONLY and pair not in ONLY:
        continue
    if not s.get('pick') or pair in res['pairs']:
        continue
    o = pair.split('/', 1)[1]
    new = os.path.join(RES, s['mesh'])
    lib = os.path.join(REPO, 'meshes/library_v3', o + '.glb')
    r = dict(mesh=s['mesh'], sha256=h(new), sha256_selection=s['sha256'], lib_sha256=h(lib))
    r['frame'] = frame(new, lib, SYM[o])
    r['kit'] = kit(new)
    if o not in res['library_kit']:
        res['library_kit'][o] = kit(lib)
    res['pairs'][pair] = r
    f = r['frame']
    print(pair, json.dumps(dict(cen=round(f['centroid_offset_mm'], 2), ang=f['axis_angle_deg'], med=round(f['surf_sym_median_mm'], 2),
                                icp_rot=round(f['icp_rot_deg'], 2), icp_cen=round(f['icp_centroid_motion_mm'], 2),
                                tilt=round(f.get('icp_symaxis_tilt_deg', -1), 2), kit=(r['kit']['nonpad_faces'], r['kit']['vertices_used'],
                                r['kit']['watertight'], r['kit']['quality_flags']))), flush=True)
    json.dump(res, open(OUT, 'w'), indent=1, default=str)
json.dump(res, open(OUT, 'w'), indent=1, default=str)
print('WROTE', OUT, len(res['pairs']), 'pairs')
