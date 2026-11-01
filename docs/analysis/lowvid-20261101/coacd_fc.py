"""FlashCHORD's default collision decomposition, as in fc_mesh.py (coacd 1.0.11, threshold 0.05, max_convex_hull -1,
preprocess auto). Usage: coacd_fc.py OUT.npz MESH"""
import sys, numpy as np, trimesh, coacd
coacd.set_log_level('error')
m = trimesh.load(sys.argv[2], force='mesh')
parts = coacd.run_coacd(coacd.Mesh(np.ascontiguousarray(m.vertices, np.float64), np.ascontiguousarray(m.faces, np.int64)),
                        threshold=0.05, max_convex_hull=-1, preprocess_mode='auto')
np.savez(sys.argv[1], **{f'v{i}': np.asarray(v) for i, (v, f) in enumerate(parts)}, **{f'f{i}': np.asarray(f) for i, (v, f) in enumerate(parts)}, n=len(parts))
print(sys.argv[2], len(parts), 'hulls')
