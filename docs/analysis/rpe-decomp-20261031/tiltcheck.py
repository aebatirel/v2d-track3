"""ORACLE DIAGNOSTIC (public only): split the W* vs kit-alignment rotation into tilt and yaw (mocap z up).
Usage: python -I tiltcheck.py RDLIB_DIR SCRATCH  (reads RDLIB_DIR/decomp_Po.json)"""
# ORACLE diagnostic: is the kit-vs-best-world rotation (anchor frame-0 bias) mostly tilt or yaw (mocap z)?
import sys, json, numpy as np
sys.path.insert(0, sys.argv[1]); import rdlib as L
from scipy.spatial.transform import Rotation as Rot
S = sys.argv[2]; L.load_kit(f'{S}/dl/kit/v2d_submission_kit'); t3 = f'{S}/t3'
R = json.load(open(f'{sys.argv[1]}/decomp_Po.json'))['episodes']
BOX = {13:'a',2:'a',26:'a',44:'a',45:'a',41:'a',0:'a',11:'b',21:'b',31:'b',39:'b',22:'b',42:'b',23:'b',12:'c',27:'c',24:'c',18:'c',40:'c',43:'c'}
for ep in [0,2,11,12,13,18,21,22,24,26,27,31,39,40,41,42,43,44,45]:
    names = L.names_of(t3, ep)
    P = L.track7(f'{S}/store/runs/20261030-orcP1{BOX[ep]}-87fc869/results/leak_p1/ep{ep}/perc2/poses_world_vo.npz', names)
    H = [L.host_geometry(t3, n, s) for s, n in enumerate(names)]
    G = L.ref_anchor(L.mocap7(t3, ep, names, len(P)), H)
    REG = [L.kit_reg('/home/user/v2d-track3/meshes/library_v3', n, H[s], ep, s) for s, n in enumerate(names)]
    C = L.convert(P, REG); A = L.align(C, G, H); C4, A4 = L.to4(C), L.to4(A)
    Wk = A4[0, 0] @ np.linalg.inv(C4[0, 0]); W = np.asarray(R[str(ep)]['W_star'])
    dR = (W @ np.linalg.inv(Wk))[:3, :3]; rv = Rot.from_matrix(dR).as_rotvec(); ang = np.degrees(np.linalg.norm(rv))
    z = np.array([0, 0, 1.0]); yaw = np.degrees(abs(rv @ z)); tilt = np.degrees(np.linalg.norm(rv - (rv @ z) * z))
    # table check: z spread of slot anchors in still frames
    still = L.rest_mask(G); zs = [float(np.std(G[still[:, s], s, 2]) * 100) if still[:, s].any() else None for s in range(len(names))]
    print(f'ep{ep} {names}: W* vs kit {ang:.2f} deg = tilt {tilt:.2f} + yaw {yaw:.2f}; still-z sd cm {zs}', flush=True)
