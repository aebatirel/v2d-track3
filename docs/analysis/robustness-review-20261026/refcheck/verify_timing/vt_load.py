"""verify_timing: independent loaders (27 Oct 2026). Written from scratch; does NOT import refcheck/timing or
refcheck/systematics. Public episodes only; mocap is read only here, for diagnostics after inference.

Conventions (checked in vt_checks.py):
  mocap parquet pose = [x, y, z, qw, qx, qy, qz] (w FIRST), world_T_object in the public scan's body frame.
  reference parquet object_body_wxyz = w first; object_body_position [T, B, 3].
  perception poses_world_vo.npz = 4x4 per object, our tracking mesh's body frame, camera-0 world.
Rotation matrices are built with my own quaternion formula (not scipy) to avoid hidden order assumptions.
"""
import glob, json, os
import numpy as np
import pyarrow.parquet as pq
import trimesh

RC = '/tmp/claude-0/-home-user-v2d-track3/12630086-0942-582d-80bb-a9806af3e32b/scratchpad/refcheck'
STORE = f'{RC}/store'
T3 = f'{RC}/t3'
REPO = '/home/user/v2d-track3'
CANON = f'{REPO}/docs/analysis/robustness-review-20261026/refcheck/resolve/canonical_refs.json'
WORK = f'{RC}/work/verify_timing'
PUBLIC = [0, 2, 11, 12, 13, 18, 21, 22, 23, 24, 26, 27, 31, 39, 40, 41, 42, 43, 44, 45]


def lib_of(e, stage):
    """Mesh library from the canonical_refs.json free-text label (my own parse, not sysload's table)."""
    s = e['tracking_mesh_library']
    if e['ep'] == 18:                      # 'tracking library_v2 (rounded sweeper); reference/simulation library_v3'
        return 'library_v2' if stage == 'perc' else 'library_v3'
    for lib in ('library_v3x', 'library_v4', 'library_v3', 'library_v2'):
        if s.startswith(lib):
            return lib
    raise ValueError(s)


def canon():
    return {e['ep']: e for e in json.load(open(CANON))['episodes']}


def quat_wxyz_to_R(q):
    q = np.asarray(q, float)
    q = q / np.linalg.norm(q, axis=-1, keepdims=True)
    w, x, y, z = q[..., 0], q[..., 1], q[..., 2], q[..., 3]
    R = np.empty(q.shape[:-1] + (3, 3))
    R[..., 0, 0] = 1 - 2 * (y * y + z * z); R[..., 0, 1] = 2 * (x * y - w * z); R[..., 0, 2] = 2 * (x * z + w * y)
    R[..., 1, 0] = 2 * (x * y + w * z); R[..., 1, 1] = 1 - 2 * (x * x + z * z); R[..., 1, 2] = 2 * (y * z - w * x)
    R[..., 2, 0] = 2 * (x * z - w * y); R[..., 2, 1] = 2 * (y * z + w * x); R[..., 2, 2] = 1 - 2 * (x * x + y * y)
    return R


def to44(pos, R):
    M = np.tile(np.eye(4), (len(pos), 1, 1)); M[:, :3, :3] = R; M[:, :3, 3] = pos
    return M


def load_mocap(ep):
    tab = pq.read_table(f'{T3}/ep{ep}.parquet', columns=['observation.objects', 'frame_index']).to_pandas()
    assert (tab.frame_index.values == np.arange(len(tab))).all()
    names = [str(o['name']) for o in tab['observation.objects'].iloc[0]]
    out = {}
    for n in names:
        A = np.stack([np.asarray([o for o in r if str(o['name']) == n][0]['pose'], float)
                      for r in tab['observation.objects']])
        out[n] = to44(A[:, :3], quat_wxyz_to_R(A[:, 3:7]))
    return names, out


def load_npz(path):
    P = np.load(path)
    return {k: np.asarray(P[k], float) for k in P.files}


def load_refpq(path):
    t = pq.read_table(path, columns=['object_body_names', 'object_body_position', 'object_body_wxyz'])
    names = [str(x) for x in t.column('object_body_names')[0].as_py()]
    pos = np.asarray(t.column('object_body_position')[0].as_py(), float)
    q = np.asarray(t.column('object_body_wxyz')[0].as_py(), float)
    return {n: to44(pos[:, i], quat_wxyz_to_R(q[:, i])) for i, n in enumerate(names)}


def surf_centroid(path):
    m = trimesh.load(path, force='mesh')
    v, f = np.asarray(m.vertices, float), np.asarray(m.faces)
    tri = v[f]
    a = 0.5 * np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1)
    return (tri.mean(1) * a[:, None]).sum(0) / a.sum()


def scan_mesh(n):
    p = f'{T3}/mesh/{n}/{n}.glb'
    return p if os.path.exists(p) else f'{T3}/mesh/{n}/{n}_visual.glb'


def our_mesh(lib, n):
    return f'{REPO}/meshes/{lib}/{n}.glb'


def ref_paths(e):
    if not e.get('ref_parquet'):
        return None, None
    fin = f"{STORE}/{e['ref_parquet']}"
    pre = f"{STORE}/{e['ref_path']}/e2s_reference.parquet"
    return fin, (pre if os.path.exists(pre) else None)


def point_path(M, c):
    return np.einsum('tij,j->ti', M[:, :3, :3], c) + M[:, :3, 3]
