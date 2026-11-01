"""O1 ORACLE (DIAGNOSTIC ONLY: the correction is computed FROM MOCAP; never an inference candidate).
Where is the anchor's frame-0 orientation loss? For the scorer's anchor, a constant body-frame correction makes its
frame-0 down axis relative to OUR table equal the truth (an exact physics tilt prior = the ceiling of T1 / T2). Same pivot / application as pp_tilt.
Usage: python -I o1_oracle.py SCRATCH MESHDIR TRACKS_IN OUT_ROOT tilt"""
import json, os, sys, numpy as np, pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as Rot
S, MD, TIN, OUT, MODE = sys.argv[1:6]
sys.path.insert(0, f'{S}/kit/v2d_submission_kit'); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v2dlb import track3_pose as T3; from v2dlb.mesh_budget import budget_mesh; from v2dlb.object_mesh import _surface_moments
import physlib as PL
SYM = {'beige_cup', 'blue_cup', 'white_pot_lid'}
EPS = [0, 2, 11, 12, 13, 18, 21, 22, 23, 24, 26, 27, 31, 39, 40, 41, 42, 43, 44, 45]
for e in EPS:
    tab = pq.read_table(f'{S}/t3/ep{e}.parquet').to_pandas()
    names = [str(o['name']) for o in tab['observation.objects'].iloc[0]]
    P = dict(np.load(f'{TIN}/ep{e}/poses_world_vo.npz'))
    s = next((i for i, n in enumerate(names) if n not in SYM), 0); n = names[s]
    up, d = PL.table_up(S, e, P, MD)
    o0 = [o for o in tab['observation.objects'].iloc[0] if o['name'] == n][0]['pose']
    Rgt = Rot.from_quat([o0[4], o0[5], o0[6], o0[3]]).as_matrix()
    sv, sf = PL.load_vf(PL.scan_path(S, n)); c, _ = _surface_moments(sv, sf)
    ca, B = T3._register_object_body(budget_mesh(f'{MD}/{n}.glb', 4096, 4096), (sv, sf), c, 1_000_003 * e + 101 * s)
    R0 = P[n][0][:3, :3]
    zt = np.array([0, 0, 1.0])
    Wm = PL.swing(up, zt)                          # our world -> a z-up world (mocap z up; table horizontal)
    Rconv = Wm @ R0 @ B.T                          # our anchor in that world, scan body convention
    g_true = Rgt.T @ -zt; g_ours = Rconv.T @ -zt   # down axes in the scan body frame
    Cs = PL.swing(g_ours, g_true)                  # body-frame swing that makes the anchor's down axis exact
    assert MODE == 'tilt'
    Cb = B.T @ Cs @ B                              # to our body convention
    Rn = np.einsum('tij,kj->tik', P[n][:, :3, :3], Cb)
    cc = PL.shell_com(f'{MD}/{n}.glb')
    Q = P[n].copy(); Q[:, :3, :3] = Rn
    Q[:, :3, 3] = P[n][:, :3, 3] + np.einsum('tij,j->ti', P[n][:, :3, :3], cc) - np.einsum('tij,j->ti', Rn, cc)
    P[n] = Q
    os.makedirs(f'{OUT}/ep{e}', exist_ok=True)
    np.savez(f'{OUT}/ep{e}/poses_world_vo.npz', **P)
    print(e, n, 'tilt fixed %.2f deg' % np.degrees(np.arccos(np.clip((np.trace(Cs) - 1) / 2, -1, 1))), flush=True)
