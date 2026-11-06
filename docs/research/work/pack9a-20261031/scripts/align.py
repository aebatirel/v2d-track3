"""C0a: each C0 mesh rigidly moved onto its library_v3 mesh with the kit scorer's own _align_rigid (no scale change).
usage: align.py KIT_AUC_PY C0_DIR V3_DIR OUT_DIR objects..."""
import importlib.util, json, sys
import numpy as np, trimesh
auc_py, c0d, v3d, out = sys.argv[1:5]; objs = sys.argv[5:]
spec = importlib.util.spec_from_file_location('kitauc', auc_py); K = importlib.util.module_from_spec(spec); spec.loader.exec_module(K)
rep = {}
for o in objs:
    c = trimesh.load(f'{c0d}/{o}.glb', force='mesh'); v = trimesh.load(f'{v3d}/{o}.glb', force='mesh')
    cv, cf = np.asarray(c.vertices, float), np.asarray(c.faces); vv, vf = np.asarray(v.vertices, float), np.asarray(v.faces)
    rp = K._sample_mesh_surface(vv, vf, 6000, 7); cp = K._sample_mesh_surface(cv, cf, 6000, 7)
    R, t = K._align_rigid(rp, cp)                       # cp @ R.T + t ~ rp
    nv = cv @ R.T + t
    ang = float(np.degrees(np.arccos(np.clip((np.trace(R) - 1) / 2, -1, 1))))
    disp = np.linalg.norm(nv - cv, axis=1) * 1000
    m = trimesh.Trimesh(nv, cf, process=False); m.export(f'{out}/{o}.glb')
    # checks: reload; re-align onto v3 must be ~identity; chamfer before/after (mm, symmetric mean, kit sampler)
    a = trimesh.load(f'{out}/{o}.glb', force='mesh'); av = np.asarray(a.vertices, float)
    ap = K._sample_mesh_surface(av, np.asarray(a.faces), 6000, 7); R2, t2 = K._align_rigid(rp, ap)
    ang2 = float(np.degrees(np.arccos(np.clip((np.trace(R2) - 1) / 2, -1, 1))))
    rep[o] = dict(rot_deg=round(ang, 3), trans_mm=round(float(np.linalg.norm(t) * 1000), 2), vertex_move_mm_median=round(float(np.median(disp)), 2),
                  vertex_move_mm_max=round(float(disp.max()), 2), realign_rot_deg=round(ang2, 3), realign_trans_mm=round(float(np.linalg.norm(t2) * 1000), 2),
                  chamfer_to_v3_mm_before=round(10 * K._symmetric_mean_distance(rp, cp), 2), chamfer_to_v3_mm_after=round(10 * K._symmetric_mean_distance(rp, ap), 2),
                  same_faces=bool(np.array_equal(np.asarray(a.faces), cf)), n_vertices=len(av), extents_mm=[round(x * 1000, 1) for x in a.extents])
    print(o, rep[o], flush=True)
json.dump(rep, open(f'{out}/align_report.json', 'w'), indent=1)
