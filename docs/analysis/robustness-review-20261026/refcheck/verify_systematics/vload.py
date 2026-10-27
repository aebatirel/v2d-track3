"""verify_systematics: my own loaders (independent of refcheck/systematics/sysload.py). Diagnostics on PUBLIC episodes;
mocap is read only after inference, here, to check another agent's measurements. Nothing here feeds inference."""
import glob, json, os
import numpy as np
import pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as R

RC = '/tmp/claude-0/-home-user-v2d-track3/12630086-0942-582d-80bb-a9806af3e32b/scratchpad/refcheck'
ST = f'{RC}/store'
T3D = f'{RC}/t3'
KIT = f'{RC}/kit/v2d_submission_kit'
REPO = '/home/user/v2d-track3'
WORK = f'{RC}/work/verify_systematics'
CANON = json.load(open(f'{REPO}/docs/analysis/robustness-review-20261026/refcheck/resolve/canonical_refs.json'))
CE = {e['ep']: e for e in CANON['episodes']}


def T44(p, quat_xyzw):
    M = np.zeros((len(p), 4, 4)); M[:, 3, 3] = 1
    M[:, :3, :3] = R.from_quat(quat_xyzw).as_matrix(); M[:, :3, 3] = p
    return M


def mocap(ep):
    """names (slot order) and {name: T x 4 x 4} world_T_scanbody. Parquet pose = x y z qw qx qy qz."""
    df = pq.read_table(f'{T3D}/ep{ep}.parquet', columns=['observation.objects', 'frame_index']).to_pandas()
    rows = df['observation.objects'].tolist()
    names = [str(o['name']) for o in rows[0]]
    out = {}
    for n in names:
        A = np.array([[o['pose'] for o in r if str(o['name']) == n][0] for r in rows], float)
        out[n] = T44(A[:, :3], np.c_[A[:, 4], A[:, 5], A[:, 6], A[:, 3]])
    return names, out, df['frame_index'].values


def refparq(path):
    t = pq.read_table(path, columns=['object_body_names', 'object_body_position', 'object_body_wxyz'])
    names = t.column('object_body_names')[0].as_py()
    P = np.array(t.column('object_body_position')[0].as_py(), float)
    Q = np.array(t.column('object_body_wxyz')[0].as_py(), float)          # w x y z
    return {n: T44(P[:, i], Q[:, i][:, [1, 2, 3, 0]]) for i, n in enumerate(names)}


def ref_dir(ep):
    e = CE[ep]
    if not e.get('ref_path'):
        return None
    return f"{ST}/{e['ref_path']}"


def ref_final(ep):
    e = CE[ep]
    return f"{ST}/{e['ref_parquet']}" if e.get('ref_parquet') else None


def perc(ep):
    z = np.load(f"{ST}/{CE[ep]['perception_path']}")
    return {k: np.asarray(z[k], float) for k in z.files}
