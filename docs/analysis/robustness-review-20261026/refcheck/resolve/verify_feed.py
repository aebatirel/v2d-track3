"""Which perception fed a reference? (refcheck/resolve, 26 Oct 2026; CPU, no ground truth read.)

mkref maps each object's perceived world pose W_t (perception poses_world_vo.npz = world_T_cam @ cam_T_obj) into the
table frame with one rigid transform per episode (plus a constant per-object z snap), so for the perception that fed a
reference R_t = A @ W_t @ B with constant A (table frame) for every frame t before any contact-retarget rest settling.
We estimate the constant from frame 0 and report the residual over all frames (position mm, rotation deg). The
pre-retarget mkref output (e2s_reference.parquet) is used when present, because contact_retarget --rest_settle moves
resting objects. Usage: python -I verify_feed.py STORE_ROOT OUT.json
"""
import glob, json, os, sys
import numpy as np
import pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as Rot


def ref_poses(path):
    t = pq.read_table(path, columns=['object_body_names', 'object_body_position', 'object_body_wxyz'])
    names = t.column('object_body_names')[0].as_py()
    pos = np.array(t.column('object_body_position')[0].as_py(), float)
    q = np.array(t.column('object_body_wxyz')[0].as_py(), float)
    out = {}
    for i, n in enumerate(names):
        M = np.tile(np.eye(4), (len(pos), 1, 1))
        M[:, :3, :3] = Rot.from_quat(q[:, i][:, [1, 2, 3, 0]]).as_matrix(); M[:, :3, 3] = pos[:, i]
        out[n] = M
    return out


def residual(R, W):
    """R_t = A W_t (A constant, world -> table, any per-object z snap absorbed): A_t = R_t W_t^-1 should be constant."""
    T = min(len(R), len(W))
    A = R[:T] @ np.linalg.inv(W[:T])
    A0 = np.median(A[:, :3, 3], 0)
    dpos = np.linalg.norm(A[:, :3, 3] - A0, axis=1) * 1000
    r0 = Rot.from_matrix(A[0, :3, :3])
    drot = np.degrees((Rot.from_matrix(A[:, :3, :3]) * r0.inv()).magnitude())
    return dict(frames=[len(R), len(W)], pos_resid_max_mm=round(float(dpos.max()), 3), pos_resid_med_mm=round(float(np.median(dpos)), 3),
                rot_resid_max_deg=round(float(drot.max()), 4))


CASES = [  # (episode, reference dir, perception dir)
    (2, 'runs/20261024-e3-e49e83d/refs/perc2mck/ep2', 'runs/20261024-e3-e49e83d/perc2/ep2'),
    (39, 'runs/20261024-e3-e49e83d/refs/perc2mck/ep39', 'runs/20261024-e3-e49e83d/perc2/ep39'),
    (11, 'runs/20261025-twin11v3x-0e8aebb/refs/perc2mck/ep11', 'runs/20261025-twin11v3x-0e8aebb/perc2/ep11'),
    (11, 'runs/20261025-twin11v3-0e8aebb/refs/perc2mck/ep11', 'runs/20261025-twin11v3-0e8aebb/perc2/ep11'),
    (11, 'runs/20261025-twin11v3x-0e8aebb/refs/perc2mck/ep11', 'runs/20261025-twin11v3-0e8aebb/perc2/ep11'),   # cross check
    (12, 'runs/20261023-fdr43-715c9f7/refs/perc2mckd/ep12', 'runs/20261021-auto18-966eb96/perc2m/ep12'),
    (12, 'runs/20261023-fdr43-715c9f7/refs/perc2mckd/ep12', 'runs/20261025-sweep-a894083/results/sweep/base/ep12'),   # cross check
    (18, 'runs/20261022-r4kfi-a30ac72/refs/perc2mckfi/ep18', 'runs/20261021-auto18-966eb96/perc2m/ep18'),
    (18, 'runs/20261021-auto18-966eb96/refs/perc2mc/ep18', 'runs/20261021-auto18-966eb96/perc2m/ep18'),
    (21, 'runs/20261025-twin21arc-ee7ba8e/refs/perc2mck/ep21', 'runs/20261025-twin21arc-ee7ba8e/perc2/ep21'),
    (21, 'runs/20261025-twin21base-ee7ba8e/refs/perc2mck/ep21', 'runs/20261025-twin21base-ee7ba8e/perc2/ep21'),
    (21, 'runs/20261025-twin21arc-ee7ba8e/refs/perc2mck/ep21', 'runs/20261025-twin21base-ee7ba8e/perc2/ep21'),   # cross check
    (24, 'runs/20261022-r5ks-72ecb2f/refs/perc2mcsks/ep24', 'runs/20261021-auto24-966eb96/perc2m/ep24'),
    (24, 'runs/20261022-r5ks-72ecb2f/refs/perc2mcsks/ep24', 'runs/20261021-autohard-3c11668/perc2m/ep24'),   # cross check
    (24, 'runs/20261024-w1-37cc551/refs/perc2mck/ep24', 'runs/20261024-w1-37cc551/perc2/ep24'),
    (26, 'runs/20261024-w1-37cc551/refs/perc2mck/ep26', 'runs/20261024-w1-37cc551/perc2/ep26'),
    (27, 'runs/20261022-r3kie-342d72c/refs/perc2mcki/ep27', 'runs/20261021-auto18-966eb96/perc2m/ep27'),
    (31, 'runs/20261024-ev30rp-07eef1a/refs/perc2mck/ep31', 'runs/20261024-ev30rp-07eef1a/perc2/ep31'),
] + [(e, f'runs/20261020-refsweep-ea14fdf/refs/perc2/ep{e}', f'runs/20261020-refsweep-ea14fdf/perc2/ep{e}') for e in (0, 13, 22, 23, 40, 41, 42, 43, 44, 45)]

if __name__ == '__main__':
    root, out = sys.argv[1], sys.argv[2]
    res = []
    for ep, rd, pd in CASES:
        e2s = f'{root}/{rd}/e2s_reference.parquet'
        src = e2s if os.path.exists(e2s) else sorted(glob.glob(f'{root}/{rd}/processed/*/*/*.parquet'))[0]
        R = ref_poses(src); Wz = np.load(f'{root}/{pd}/poses_world_vo.npz')
        row = dict(ep=ep, ref=rd, ref_file=src[len(root) + 1:], perception=pd, objects={})
        for n in R:
            row['objects'][n] = residual(R[n], Wz[n]) if n in Wz.files else 'missing in perception'
        res.append(row)
        print(ep, rd.split('runs/')[1], '<-', pd.split('runs/')[1], {n: (o['pos_resid_max_mm'], o['rot_resid_max_deg']) if isinstance(o, dict) else o for n, o in row['objects'].items()})
    json.dump(res, open(out, 'w'), indent=1)
