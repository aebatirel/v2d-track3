# Run pipeline/recon_mesh.py UNCHANGED (independent per-object fusion) and save its fused grid (tsdf, weight) so a
# joint post-pass can use the per-voxel evidence. Inference-legal inputs only (our poses, depth, hands, our meshes).
# Usage: fuse_save.py OUT_NPZ recon_mesh args...
import sys, numpy as np
sys.path.insert(0, '/home/user/v2d-track3/pipeline')
import recon_mesh as rm
_svd = np.linalg.svd        # table_plane line 89: full N x N SVD (2-45 GB); thin SVD gives the same Vt (this process only)
np.linalg.svd = lambda A, full_matrices=False, **k: _svd(A, full_matrices=False, **k)
out = sys.argv[1]
cap = {}
_int = rm.integrate
def integrate(a, K, X, tsdf, wgt, *r):
    cap.update(a=a, tsdf=tsdf, wgt=wgt); return _int(a, K, X, tsdf, wgt, *r)
rm.integrate = integrate
sys.argv = ['recon_mesh.py'] + sys.argv[2:]
rm.main()
a = cap['a']
np.savez_compressed(out, tsdf=cap['tsdf'], wgt=cap['wgt'], voxel=a.voxel, half=a.half, trunc=a.trunc, min_obs=a.min_obs,
                    close=a.close, auto_thr=a.auto_thr, near_vox=a.near_vox, merge_vox=a.merge_vox, obj=a.obj, mesh=a.out)
print('saved', out)
