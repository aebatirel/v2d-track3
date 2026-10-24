"""CoACD with Newton's settings (threshold 0.05, auto preprocess) on a mesh -> npz of hull vertex arrays."""
import sys, time, trimesh, coacd, numpy as np
coacd.set_log_level('error')
src, out = sys.argv[1], sys.argv[2]
m = trimesh.load(src, force='mesh'); m = trimesh.Trimesh(np.asarray(m.vertices), np.asarray(m.faces), process=True)
t0 = time.time()
parts = coacd.run_coacd(coacd.Mesh(np.asarray(m.vertices), np.asarray(m.faces)), threshold=0.05, max_convex_hull=-1, preprocess_mode='auto')
np.savez(out, **{f'h{i}': np.asarray(p[0]) for i, p in enumerate(parts)})
print(f'{src.split("/")[-1]}: {len(parts)} hulls, {time.time() - t0:.0f} s', flush=True)
