"""D7 (DIAGNOSTIC, reads mocap): twist about the cup's symmetry axis relative to frame 0, ours vs truth.
Ours: body-frame relative rotation R0^T R(t), twist about our mesh's axis (swing-twist). Truth: same with mocap and the
scan's distinct principal axis. Error per frame = |wrap(tw_ours - tw_true)| in deg. Usage: d7_twist.py SCRATCH TRACKS_A TRACKS_B"""
import sys, json, numpy as np, pyarrow.parquet as pq, trimesh
from scipy.spatial.transform import Rotation as Rot
S, TA, TB = sys.argv[1:4]
sys.path.insert(0, '/home/user/v2d-track3/docs/analysis/physperc-20261101/scripts')
from twist_canon_grasp_41383b4 import mesh_axis
import physlib as PL
def twist(Rrel, a):
    q = Rot.from_matrix(Rrel).as_quat()                      # x y z w
    return np.degrees(2 * np.arctan2(q[:, :3] @ a, q[:, 3]))
wrap = lambda x: (x + 180) % 360 - 180
for e in (11, 12, 13, 21, 22):
    tab = pq.read_table(f'{S}/t3/ep{e}.parquet').to_pandas()
    for n in ('blue_cup', 'beige_cup'):
        if n not in [o['name'] for o in tab['observation.objects'].iloc[0]]:
            continue
        G = np.array([Rot.from_quat([q[4], q[5], q[6], q[3]]).as_matrix() for q in
                      [[o for o in tab['observation.objects'].iloc[t] if o['name'] == n][0]['pose'] for t in range(len(tab))]])
        sa, _, _ = mesh_axis(PL.scan_path(S, n))
        tt = twist(np.einsum('ji,tjk->tik', G[0], G), sa)
        row = [f'{e} {n:9s}']
        for TR in (TA, TB):
            R = np.load(f'{TR}/ep{e}/poses_world_vo.npz')[n][:, :3, :3]
            a, _, _ = mesh_axis(f'{S}/mesh9a/{n}.glb')
            to = twist(np.einsum('ji,tjk->tik', R[0], R), a)
            # sign convention of the two axes may differ: take the better of +/-
            er = min(np.mean(np.abs(wrap(to - tt))), np.mean(np.abs(wrap(-to - tt))))
            row.append(f'mean|err| {er:6.1f} deg (true twist range {np.ptp(tt):5.1f}, ours {np.ptp(to):5.1f})')
        print(' | '.join(row), flush=True)
