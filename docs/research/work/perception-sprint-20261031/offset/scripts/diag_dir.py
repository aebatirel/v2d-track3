"""ORACLE diagnostic (public): direction of the trk constant body offset at frame 0, in the camera frame (along the
viewing ray vs lateral) and rotation. Reads xstar_trk_Po.json (mocap-fitted) + our P_o tracks. Not inference."""
import json, sys, numpy as np, trimesh
from scipy.spatial.transform import Rotation as Rot
REPO='/home/user/v2d-track3'; S='/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad'
arm=sys.argv[1]  # Po
J=json.load(open(f'{REPO}/docs/research/work/leak-decomp-20261030/phase1/scores/xstar_trk_{arm}.json'))
XG=json.load(open(f'{REPO}/docs/research/work/leak-decomp-20261030/tierA/xstar_geom.json'))['objects']
for ep,r in J['episodes'].items():
    root=f'{S}/leak/p1/oracle_roots/{arm}/ep{ep}'
    P=np.load(f'{root}/poses.npz'); V=np.load(f'{root}/poses_world_vo.npz'); W0=P['world_T_cam'][0].astype(float)
    row=[]
    for n,o in r['objects'].items():
        Xt=np.array(o['X_scan_T_lib']); Xg=np.array(XG[n]['X_scan_T_lib'])
        C=np.linalg.inv(Xt)@Xg
        m=trimesh.load(f'{REPO}/meshes/library_v3/{n}.glb',force='mesh'); a=m.vertices.mean(0)
        Tc=np.linalg.inv(W0)@V[n][0].astype(float)
        pc=Tc[:3,:3]@a+Tc[:3,3]; ray=pc/np.linalg.norm(pc)
        d=Tc[:3,:3]@(C[:3,:3]@a+C[:3,3]-a)
        along=d@ray; lat=np.linalg.norm(d-along*ray)
        rv=Tc[:3,:3]@Rot.from_matrix(C[:3,:3]).as_rotvec()   # rotation axis in camera frame
        ang=np.degrees(np.linalg.norm(rv)); about_ray=np.degrees(abs(rv@ray))
        row.append(f'{n}(s{o["slot"]}) along {along*100:+.2f} lat {lat*100:.2f} cm | rot {ang:.1f} (about ray {about_ray:.1f}) | z {pc[2]:.2f} m')
    print(ep, r['scores']['lib']['AUC'], r['scores']['trk']['AUC'], ' || '.join(row))
