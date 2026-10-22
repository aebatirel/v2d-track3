# Run pipeline/recon_mesh.py UNCHANGED (imported, not edited) and save its fused TSDF grid so a post-pass can work on
# it. Scratch prototype for the 'minimal-carve' design (2026-10-22). Only inference-legal inputs are passed in.
# Usage: fuse_grid.py GRID_OUT.npz -- <recon_mesh.py arguments>
import sys, json, numpy as np
sys.path.insert(0, '/home/user/v2d-track3/pipeline')
import recon_mesh as rm
# recon_mesh.table_plane line 89: np.linalg.svd(Q - q0) allocates N x N U (2 GB on real data). Thin SVD in this
# process only; identical Vt.
_svd = np.linalg.svd
np.linalg.svd = lambda A, full_matrices=False, **k: _svd(A, full_matrices=False, **k)
out = sys.argv[1]; assert sys.argv[2] == '--'
cap = {}
_int = rm.integrate
_tp = rm.table_plane
def table_plane(*a, **k):
    r = _tp(*a, **k); cap.setdefault('planes', []).append((np.asarray(r[0]), float(r[1]))); return r
rm.table_plane = table_plane
def integrate(a, K, X, tsdf, wgt, *r):
    cap.update(a=a, tsdf=tsdf, wgt=wgt); return _int(a, K, X, tsdf, wgt, *r)
rm.integrate = integrate
sys.argv = ['recon_mesh.py'] + sys.argv[3:]
rm.main()
a = cap['a']; n = int(round(2 * a.half / a.voxel))
np.savez_compressed(out, tsdf=cap['tsdf'].reshape(n, n, n).astype(np.float16), wgt=np.minimum(cap['wgt'], 65000).reshape(n, n, n).astype(np.uint16),
                    voxel=a.voxel, half=a.half, trunc=a.trunc, min_obs=a.min_obs, obj=a.obj,
                    plane_n=np.array([p[0] for p in cap.get('planes', [])]), plane_c=np.array([p[1] for p in cap.get('planes', [])]),
                    args=json.dumps(vars(a)))
print('saved grid', out)
