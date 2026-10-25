"""Shared loaders for the approach-3 analyses (our own references only; ground truth is read only by gt_events.py).

Reference = a FlashCHORD ManoSharpa parquet written by pipeline/mkref.py (perceived objects + MediaPipe hands + E2S IK).
Columns used: object_body_names, object_body_position (T,B,3), object_body_wxyz (T,B,4 wxyz), mano_<s>_joints (T,21,3,
MediaPipe order, the perceived human hand), robot_<s>_frames (T,67,7) + <s>_robot_frame_names, and the 16 contact slots
mano_<s>_object_contact_part_ids/positions/normals. Slot order (pipeline/mkref.py PROBE_SITES + palm): 0-4 tip sites
(thumb, index, middle, ring, pinky), 5-9 DP sites, 10 thumb_MCP_VL, 11-14 index..pinky MP sites, 15 palm (mean of 5
palm frames). Meshes: our library (body frame = the reference's object frame).
"""
import os
import numpy as np
import pyarrow.parquet as pq
import trimesh
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation as Rot

SLOTS = ['thumb_tip', 'index_tip', 'middle_tip', 'ring_tip', 'pinky_tip', 'thumb_DP', 'index_DP', 'middle_DP',
         'ring_DP', 'pinky_DP', 'thumb_MCP', 'index_MP', 'middle_MP', 'ring_MP', 'pinky_MP', 'palm']
PROBE_SITES = ['thumb_tip_site', 'index_tip_site', 'middle_tip_site', 'ring_tip_site', 'pinky_tip_site',
               'thumb_DP_site', 'index_DP_site', 'middle_DP_site', 'ring_DP_site', 'pinky_DP_site',
               'thumb_MCP_VL_site', 'index_MP_site', 'middle_MP_site', 'ring_MP_site', 'pinky_MP_site']
PALM_FRAMES = ['hand_C_MC', 'index_MCP_VL_site', 'middle_MCP_VL_site', 'ring_MCP_VL_site', 'pinky_MC_site']
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
LIB = os.path.join(REPO, 'meshes', 'library_v3')


def col(t, c):
    return t.column(c)[0].as_py()


def load_ref(path):
    t = pq.read_table(path)
    names = col(t, 'object_body_names')
    T = len(col(t, 'robot_left_wrist_position'))
    B = len(names)
    OP = np.array(col(t, 'object_body_position'), float).reshape(T, B, 3)
    OQ = np.array(col(t, 'object_body_wxyz'), float).reshape(T, B, 4)[..., [1, 2, 3, 0]]
    d = dict(t=t, names=names, T=T, OP=OP, OR=[Rot.from_quat(OQ[:, j]) for j in range(B)], OQ=OQ)
    for s in ('left', 'right'):
        d[f'J_{s}'] = np.array(col(t, f'mano_{s}_joints'), float).reshape(T, 21, 3)
        fn = col(t, f'{s}_robot_frame_names'); F = np.array(col(t, f'robot_{s}_frames'), float).reshape(T, len(fn), -1)
        d[f'F_{s}'] = {n[len(s) + 1:]: F[:, i, :3] for i, n in enumerate(fn) if n.startswith(s + '_')}
        d[f'pid_{s}'] = np.array(col(t, f'mano_{s}_object_contact_part_ids'), int).reshape(T, -1)
    return d


class Surface:
    """Surface samples + normals of one library mesh (body frame) with a KD-tree: distance and outward normal."""
    def __init__(self, name, n=12000, lib=LIB):
        m = trimesh.load(os.path.join(lib, f'{name}.glb'), force='mesh')
        P, fi = trimesh.sample.sample_surface(m, n, seed=0)
        self.P, self.N, self.mesh = np.asarray(P), np.asarray(m.face_normals[fi]), m
        self.kd = cKDTree(self.P)
        self.V = np.asarray(m.vertices)

    def query(self, X):
        d, i = self.kd.query(X)
        return d, self.P[i], self.N[i]


def to_obj(d, j, f, X):
    return d['OR'][j][f].inv().apply(np.asarray(X) - d['OP'][f, j])


def hold_list(path):
    import sys
    sys.path.insert(0, os.path.join(REPO, 'pipeline'))
    from hold_phases import hold_phases
    return hold_phases(path)[0]['phases']
