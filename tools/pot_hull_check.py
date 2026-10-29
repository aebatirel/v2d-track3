import os, sys, numpy as np, warp as wp, pyarrow.parquet as pq, trimesh
sys.path.insert(0, '/home/user/v2d-track3/pipeline'); import contact_retarget as cr
from scipy.spatial.transform import Rotation as Rot
pqp = sys.argv[1]; S = sys.argv[2]
with wp.ScopedDevice('cpu'):
    st, env = cr.build_scene(pqp, os.environ['FC']); m = st.scene.model
    labels = list(getattr(m, 'body_label', None) or getattr(m, 'body_key', []))
    t = pq.read_table(pqp); names = t.column('object_body_names')[0].as_py(); T = len(np.array(t.column('robot_left_wrist_position')[0].as_py(), float).reshape(-1, 3))
    OP = np.array(t.column('object_body_position')[0].as_py(), float).reshape(T, len(names), 3)
    OQ = np.array(t.column('object_body_wxyz')[0].as_py(), float).reshape(T, len(names), 4)[..., [1, 2, 3, 0]]
    ip, isp = names.index('white_pot'), names.index('wooden_spoon')
    hull = cr.HullSDF(m, next(i for i, l in enumerate(labels) if l.startswith('track3_white_pot/')))
    print('pot collision pieces:', len(hull.pieces))
    pot_vis = trimesh.load(f'{S}/gap/mesh/white_pot/white_pot.glb', force='mesh'); pq_vis = trimesh.proximity.ProximityQuery(pot_vis)
    sp = trimesh.load(f'{S}/gap/mesh/wooden_spoon/wooden_spoon.glb', force='mesh'); V = np.asarray(sp.vertices)[::4]
    print('frame | spoon pts inside pot COLLISION hulls (deepest cm) | inside pot VISUAL mesh (deepest cm)')
    for f in range(60, 241, 10):
        Xw = Rot.from_quat(OQ[f, isp]).apply(V) + OP[f, isp]; Xp = Rot.from_quat(OQ[f, ip]).inv().apply(Xw - OP[f, ip])
        d = hull(Xp); sv = pq_vis.signed_distance(Xp)  # trimesh: positive inside
        print(f'{f:4d} | {int((d < 0).sum()):4d} ({-100 * min(0, d.min()):4.1f}) | {int((sv > 0).sum()):4d} ({100 * max(0, sv.max()):4.1f})')
