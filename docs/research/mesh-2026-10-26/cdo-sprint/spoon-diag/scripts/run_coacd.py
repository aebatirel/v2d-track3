"""CoACD pieces exactly as FlashCHORD calls it: run_coacd(Mesh(v_f64, f_i64), threshold=0.05, max_convex_hull=-1,
preprocess_mode='auto'), mesh loaded by trimesh.load(force='mesh') (default process = weld, as newton's loader).
Note: FlashCHORD pins coacd 1.0.11; this venv has the installed version (printed)."""
import sys, time, json, hashlib, numpy as np, trimesh, coacd
out = sys.argv[1]
coacd.set_log_level('error')
rep = {'coacd_version': getattr(coacd, '__version__', 'unknown')}
for spec in sys.argv[2:]:
    name, path = spec.split('=', 1)
    m = trimesh.load(path, force='mesh')
    v = np.ascontiguousarray(m.vertices, np.float64); f = np.ascontiguousarray(m.faces, np.int64).reshape(-1, 3)
    t = time.time()
    parts = coacd.run_coacd(coacd.Mesh(v, f), threshold=0.05, max_convex_hull=-1, preprocess_mode='auto')
    dt = time.time() - t
    arrs = {'n': np.int64(len(parts))}
    vol = 0.0
    for i, (pv, pf) in enumerate(parts):
        arrs[f'v{i}'] = np.asarray(pv, np.float32); arrs[f'f{i}'] = np.asarray(pf, np.int32).reshape(-1, 3)
        vol += trimesh.convex.convex_hull(np.asarray(pv)).volume
    np.savez(f'{out}/{name}_coacd.npz', **arrs)
    rep[name] = dict(path=path, md5=hashlib.md5(open(path, 'rb').read()).hexdigest(), V=len(v), F=len(f),
                     pieces=len(parts), hull_vol_sum_cm3=round(vol * 1e6, 1), mesh_vol_cm3=round(abs(m.volume) * 1e6, 1), sec=round(dt, 1))
    print(name, rep[name], flush=True)
json.dump(rep, open(f'{out}/coacd_report.json', 'w'), indent=1)
