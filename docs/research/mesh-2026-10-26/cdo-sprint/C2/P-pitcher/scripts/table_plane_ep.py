"""C2/P GT-free: the frame-0 support plane of one public episode in our track's world frame, exactly as
obs_points.py computes it (recon_mesh.table_plane on our FoundationStereo depth of frame 0, rectified-left K, under the
pitcher's frame-0 origin). Saved so the rest check can run after the 1.2 GB depth file is deleted.
Usage: table_plane_ep.py POSES.npz DEPTH.npy CALIB.json OBJ OUT.json
"""
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..', '..', '..', 'pipeline')))
from recon_mesh import rectified_K, table_plane  # noqa: E402

poses, depth, calib, obj, out = sys.argv[1:6]
P = np.load(poses)
W_C = P['world_T_cam'].astype(np.float64); T_co = P[f'cam_T_{obj}'].astype(np.float64)
D = np.load(depth, mmap_mode='r')
K = rectified_K(calib)
o0 = (W_C[0] @ T_co[0])[:3, 3]
nw, cw, frac = table_plane(np.array(D[0], np.float32), K, o0)
r = dict(poses=poses, depth=depth, obj=obj, n_world=[float(x) for x in nw], c_world=float(cw), inlier_frac=float(frac),
         world_T_cam0_is_identity=bool(np.allclose(W_C[0], np.eye(4), atol=1e-6)),
         obj_origin_height_f0_mm=round(float(nw @ o0 + cw) * 1e3, 2))
json.dump(r, open(out, 'w'), indent=1)
print(json.dumps(r))
