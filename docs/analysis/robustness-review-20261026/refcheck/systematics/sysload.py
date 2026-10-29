"""Shared loaders for refcheck/systematics (26 Oct 2026; CPU; diagnostics on PUBLIC episodes, mocap read AFTER inference).

Paths come from the canonical reference list (refcheck/resolve/canonical_refs.json). Everything here only reads files.
Conventions:
  ours  = our object path: the final reference parquet (table frame, our mesh's body frame) or a perception
          poses_world_vo.npz (rectified-left camera-0 frame, the tracking mesh's body frame);
  gt    = mocap from the public episode parquet (scan body frame, mocap world, z up);
  pose arrays are 4x4 per frame per object.
"""
import glob, json, os, sys
import numpy as np
import pyarrow.parquet as pq
import trimesh
from scipy.spatial.transform import Rotation as Rot

RC = '/tmp/claude-0/-home-user-v2d-track3/12630086-0942-582d-80bb-a9806af3e32b/scratchpad/refcheck'
STORE = f'{RC}/store'
T3 = f'{RC}/t3'
KIT = f'{RC}/kit/v2d_submission_kit'
REPO = '/home/user/v2d-track3'
CANON = f'{REPO}/docs/analysis/robustness-review-20261026/refcheck/resolve/canonical_refs.json'
if KIT not in sys.path:
    sys.path.insert(0, KIT)

# Mesh library each source used (from canonical_refs.json: tracking_mesh_library; reference assets for ep18 = v3).
REF_LIB = {2: 'library_v3', 11: 'library_v3x', 12: 'library_v2', 18: 'library_v3', 21: 'library_v3', 24: 'library_v2',
           26: 'library_v4', 27: 'library_v2', 31: 'library_v3', 39: 'library_v3'}
PERC_LIB = dict(REF_LIB); PERC_LIB[18] = 'library_v2'
for e in (0, 13, 22, 23, 40, 41, 42, 43, 44, 45):
    PERC_LIB[e] = 'library_v2'
SYM = {'beige_cup': 'axis', 'blue_cup': 'axis', 'white_pot_lid': 'half'}


def canon():
    return {e['ep']: e for e in json.load(open(CANON))['episodes']}


def mats(pos, q_xyzw):
    M = np.tile(np.eye(4), (len(pos), 1, 1))
    M[:, :3, :3] = Rot.from_quat(q_xyzw).as_matrix(); M[:, :3, 3] = pos
    return M


def load_ref_parquet(path):
    t = pq.read_table(path, columns=['object_body_names', 'object_body_position', 'object_body_wxyz'])
    names = t.column('object_body_names')[0].as_py()
    pos = np.array(t.column('object_body_position')[0].as_py(), float)
    q = np.array(t.column('object_body_wxyz')[0].as_py(), float)
    return {n: mats(pos[:, i], q[:, i][:, [1, 2, 3, 0]]) for i, n in enumerate(names)}


def load_npz(path):
    P = np.load(path)
    return {n: np.asarray(P[n], float) for n in P.files}


def load_gt(ep):
    tab = pq.read_table(f'{T3}/ep{ep}.parquet', columns=['observation.objects']).to_pandas()
    names = [str(o['name']) for o in tab['observation.objects'].iloc[0]]
    out = {}
    for n in names:
        rows = [np.array([o for o in r if o['name'] == n][0]['pose'], float) for r in tab['observation.objects']]
        A = np.stack(rows)                                                     # x y z qw qx qy qz
        out[n] = mats(A[:, :3], A[:, [4, 5, 6, 3]])
    return names, out


def mesh_vf(path):
    m = trimesh.load(path, force='mesh')
    return np.asarray(m.vertices, float), np.asarray(m.faces, np.int64)


def scan_path(n):
    q = f'{T3}/mesh/{n}/{n}.glb'
    return q if os.path.exists(q) else f'{T3}/mesh/{n}/{n}_visual.glb'


def our_mesh_path(lib, n):
    return f'{REPO}/meshes/{lib}/{n}.glb'


def ref_files(e):
    """(final reference parquet, pre-contact-retarget parquet or None, table_frame.npz or None) under the store."""
    if not e.get('ref_path'):
        return None, None, None
    d = f"{STORE}/{e['ref_path']}"
    fin = f"{STORE}/{e['ref_parquet']}" if e.get('ref_parquet') else sorted(glob.glob(f'{d}/processed/*/*/*.parquet'))[0]
    pre = f'{d}/e2s_reference.parquet'
    tf = f'{d}/table_frame.npz'
    return fin, (pre if os.path.exists(pre) else None), (tf if os.path.exists(tf) else None)


def centre_path(M, c):
    """World position of the body-frame point c over frames."""
    return M[:, :3, :3] @ c + M[:, :3, 3]
