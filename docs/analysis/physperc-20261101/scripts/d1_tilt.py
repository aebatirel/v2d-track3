"""D1 (DIAGNOSTIC, reads public mocap after inference; feeds no transform): is the physics prior right?
Per object at frame 0, in the kit's scan body convention (kit registration of our mesh, as score_registered.py):
  e_now   = angle(our down axis vs OUR table plane,  true down axis)        [our current tilt error]
  e_prior = angle(nearest stable-pose down axis of our mesh, true down axis) [error left after a tilt-to-plane fix]
true down axis = R_gt^T (-z_mocap) (mocap table horizontal, top 598-602 mm in all 20 episodes [refcheck]).
Also GT-free labels used by later rules: gap of our mesh's lowest point above our table, stable-pose match angle,
stable-pose probability, hand distance at f0.
Usage: python -I d1_tilt.py SCRATCH MESHDIR OUT_JSON [EPS...]"""
import json, sys, os, numpy as np, trimesh, pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as Rot
S, MD, OUT = sys.argv[1:4]
EPS = [int(x) for x in sys.argv[4:]] or [0, 2, 11, 12, 13, 18, 21, 22, 23, 24, 26, 27, 31, 39, 40, 41, 42, 43, 44, 45]
sys.path.insert(0, f'{S}/kit/v2d_submission_kit')
from v2dlb import track3_pose as T3
from v2dlb.mesh_budget import budget_mesh
from v2dlb.object_mesh import _surface_moments
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import physlib as PL

ang = lambda a, b: float(np.degrees(np.arccos(np.clip(np.dot(a, b) / np.linalg.norm(a) / np.linalg.norm(b), -1, 1))))
res = {}
for e in EPS:
    tab = pq.read_table(f'{S}/t3/ep{e}.parquet').to_pandas()
    names = [str(o['name']) for o in tab['observation.objects'].iloc[0]]
    P = np.load(f'{S}/tracks/ep{e}/poses_world_vo.npz')
    up, d = PL.table_up(S, e, P, MD)
    J = PL.hand_joints(S, e)
    res[e] = {}
    for s, n in enumerate(names):
        o0 = [o for o in tab['observation.objects'].iloc[0] if o['name'] == n][0]['pose']
        Rgt = Rot.from_quat([o0[4], o0[5], o0[6], o0[3]]).as_matrix()
        sv, sf = PL.load_vf(PL.scan_path(S, n))
        c, _ = _surface_moments(sv, sf)
        cand = budget_mesh(f'{MD}/{n}.glb', 4096, 4096)
        ca, B = T3._register_object_body(cand, (sv, sf), c, 1_000_003 * e + 101 * s)
        R0 = P[n][0][:3, :3]
        g_true = Rgt.T @ np.array([0, 0, -1.0])                 # scan body frame
        g_ours = B @ (R0.T @ -up)                                # our down axis, scan body frame
        sp = PL.stable_poses(f'{MD}/{n}.glb')
        k, match = PL.nearest_stable(sp, R0.T @ -up)
        g_prior = B @ sp['down'][k]
        gap = PL.lowest_gap(f'{MD}/{n}.glb', P[n][0], up, d)
        res[e][n] = dict(slot=s, e_now=round(ang(g_ours, g_true), 2), e_prior=round(ang(g_prior, g_true), 2),
                         match_deg=round(match, 2), prob=round(float(sp['prob'][k]), 3), gap_mm=round(gap * 1000, 1),
                         hand_mm=round(PL.hand_dist(J, 0, f'{MD}/{n}.glb', P[n][0]) * 1000, 1),
                         reg_deg=round(float(np.degrees(Rot.from_matrix(B).magnitude())), 2))
        print(e, n, res[e][n], flush=True)
json.dump(res, open(OUT, 'w'), indent=1)
