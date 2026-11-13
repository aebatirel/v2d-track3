"""FlashCHORD's packed decomposition (fc_mesh.py:62-90: coacd.run_coacd(Mesh(V f64, F i64), threshold 0.05,
max_convex_hull -1, preprocess_mode auto), mesh loaded by trimesh.load(force='mesh')) with coacd 1.0.11 from a separate
pip target. Usage: packed_coacd.py COACD_TARGET OUT_DIR name=mesh.glb ..."""
import sys, os, json, time, hashlib
sys.path.insert(0, sys.argv[1])
import numpy as np, trimesh, coacd, importlib.metadata as md
out = sys.argv[2]; os.makedirs(out, exist_ok=True)
coacd.set_log_level('error')
rep = {}
for arg in sys.argv[3:]:
    name, p = arg.split('=', 1)
    m = trimesh.load(p, force='mesh')
    V = np.ascontiguousarray(m.vertices, np.float64); F = np.ascontiguousarray(m.faces, np.int64)
    h = hashlib.sha1(V.tobytes() + F.tobytes()).hexdigest()[:12]
    t0 = time.time()
    parts = coacd.run_coacd(coacd.Mesh(V, F), threshold=0.05, max_convex_hull=-1, preprocess_mode='auto')
    dt = time.time() - t0
    np.savez(os.path.join(out, f'{name}.npz'), **{f'v{i}': np.asarray(v, np.float64) for i, (v, f) in enumerate(parts)},
             n=np.int64(len(parts)))
    vol = sum(trimesh.convex.convex_hull(np.asarray(v)).volume for v, f in parts)
    rep[name] = dict(mesh=p, geom_sha1_12=h, n=len(parts), hull_vol_cm3=round(vol * 1e6, 2),
                     mesh_vol_cm3=round(float(m.volume) * 1e6, 2), secs=round(dt, 1), coacd=md.version('coacd'),
                     coacd_file=coacd.__file__)
    print(json.dumps({name: rep[name]}), flush=True)
    json.dump(rep, open(os.path.join(out, 'report.json'), 'w'), indent=1)
