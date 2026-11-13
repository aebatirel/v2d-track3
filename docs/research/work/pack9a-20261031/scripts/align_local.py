"""C0a v2: local rigid ICP of each C0 mesh onto its library_v3 mesh, started at identity (no global search: the kit's
25-start search flips the round lid by 174 deg), no scale, no reflection. Reports symmetric chamfer (mm) before/after.
usage: align_local.py KIT_AUC_PY C0_DIR V3_DIR OUT_DIR objects..."""
import importlib.util, json, sys
import numpy as np, trimesh
auc_py, c0d, v3d, out = sys.argv[1:5]; objs = sys.argv[5:]
spec = importlib.util.spec_from_file_location('kitauc', auc_py); K = importlib.util.module_from_spec(spec); spec.loader.exec_module(K)
def ch(a, b):  # symmetric mean nearest distance, mm
    return 1000 * K._symmetric_mean_distance(a, b)
rep = {}
for o in objs:
    c = trimesh.load(f'{c0d}/{o}.glb', force='mesh'); v = trimesh.load(f'{v3d}/{o}.glb', force='mesh')
    cv, cf = np.asarray(c.vertices, float), np.asarray(c.faces)
    rp = K._sample_mesh_surface(np.asarray(v.vertices, float), np.asarray(v.faces), 20000, 7)
    cp = K._sample_mesh_surface(cv, cf, 20000, 7)
    M, _, cost = trimesh.registration.icp(cp, rp, initial=np.eye(4), threshold=1e-7, max_iterations=200,
                                         reflection=False, translation=True, scale=False)
    R, t = M[:3, :3], M[:3, 3]
    nv = cv @ R.T + t
    ang = float(np.degrees(np.arccos(np.clip((np.trace(R) - 1) / 2, -1, 1))))
    disp = np.linalg.norm(nv - cv, axis=1) * 1000
    trimesh.Trimesh(nv, cf, process=False).export(f'{out}/{o}.glb')
    a = trimesh.load(f'{out}/{o}.glb', force='mesh'); ap = K._sample_mesh_surface(np.asarray(a.vertices, float), np.asarray(a.faces), 20000, 7)
    # how well-determined is the alignment: chamfer as a function of rotating back part of the way
    rep[o] = dict(rot_deg=round(ang, 3), trans_mm=round(float(np.linalg.norm(t) * 1000), 2),
                  vertex_move_mm_median=round(float(np.median(disp)), 2), vertex_move_mm_max=round(float(disp.max()), 2),
                  chamfer_mm_before=round(ch(rp, cp), 3), chamfer_mm_after=round(ch(rp, ap), 3),
                  same_faces=bool(np.array_equal(np.asarray(a.faces), cf)), n_vertices=len(a.vertices))
    print(o, rep[o], flush=True)
json.dump(rep, open(f'{out}/align_report.json', 'w'), indent=1)
