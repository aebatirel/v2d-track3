"""Helpers for the ep18 'what grasp did RL discover' analysis (2026-10-24). Diagnostics only, after inference.
Built on docs/research/grasp/audit-plates-scripts/audit_lib.py (same hand geometry and object collision proxy):
- hand collision samples from the Sharpa Wave URDF convex collision meshes (fixed pads composed into the distal link);
- object collision = CoACD pieces of our mesh (Newton settings), signed distance: exact inside (max plane), and
  refined to the exact Euclidean distance (closest point on the piece triangles) for near-surface samples outside;
- plate PCA frame: axis1 = long axis with the ring handle at negative axis1, axis3 = plate normal;
- joint angles recovered from link poses with the URDF joint origins and axes.
Quaternions are xyzw everywhere."""
import os
import xml.etree.ElementTree as ET

import numpy as np
import pyarrow.parquet as pq
import trimesh
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation as R

SP = '/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad'
ASSETS = f'{SP}/src/video_to_data/robotic_grounding/flash_chord/src/flash_chord/assets'
TABLE_Z = 0.600   # top of the support cylinder (t3_ep018_support.usda: centre z 0.59, height 0.02)


def _rpy(s):
    return R.from_euler('xyz', [float(x) for x in s.split()]) if s else R.identity()


def _xyz(s):
    return np.array([float(x) for x in s.split()]) if s else np.zeros(3)


def hull_samples(V, n, seed=0):
    h = ConvexHull(V); P = V[h.vertices]; tri = V[h.simplices]
    area = 0.5 * np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1)
    rng = np.random.default_rng(seed); k = rng.choice(len(tri), size=n, p=area / area.sum())
    u, v = rng.random(n), rng.random(n); fl = u + v > 1; u[fl], v[fl] = 1 - u[fl], 1 - v[fl]
    S = tri[k, 0] + u[:, None] * (tri[k, 1] - tri[k, 0]) + v[:, None] * (tri[k, 2] - tri[k, 0])
    return np.vstack([P, S])


def urdf_path(side):
    return f'{ASSETS}/urdfs/sharpawave/{side}_sharpawave.urdf'


def hand_points(side, n=200):
    """{body link: (N, 3) local collision-surface samples}; fixed children composed into the parent body."""
    path = urdf_path(side); root = ET.parse(path).getroot(); base = os.path.dirname(path)
    fixed = {}
    for j in root.findall('joint'):
        if j.get('type') == 'fixed':
            o = j.find('origin')
            fixed[j.find('child').get('link')] = (j.find('parent').get('link'), _xyz(o.get('xyz') if o is not None else ''),
                                                  _rpy(o.get('rpy') if o is not None else ''))
    out = {}
    for link in root.findall('link'):
        name = link.get('name'); pts = []
        for c in link.findall('collision'):
            mesh = c.find('geometry').find('mesh')
            if mesh is None:
                continue
            o = c.find('origin'); m = trimesh.load(os.path.normpath(os.path.join(base, mesh.get('filename'))), force='mesh')
            sc = _xyz(mesh.get('scale')) if mesh.get('scale') else np.ones(3)
            V = hull_samples(np.asarray(m.vertices) * sc, n)
            pts.append(_rpy(o.get('rpy') if o is not None else '').apply(V) + _xyz(o.get('xyz') if o is not None else ''))
        if not pts:
            continue
        P = np.vstack(pts); body = name
        while body in fixed:
            parent, t, r = fixed[body]; P = r.apply(P) + t; body = parent
        out.setdefault(body, []).append(P)
    return {k: np.vstack(v) for k, v in out.items()}


def fingertip_offsets(side):
    """{DP body: pad-centre point in the DP frame} (the URDF '<finger>_fingertip' frame, through the fixed joints)."""
    root = ET.parse(urdf_path(side)).getroot(); fixed = {}
    for j in root.findall('joint'):
        if j.get('type') == 'fixed':
            o = j.find('origin'); fixed[j.find('child').get('link')] = (j.find('parent').get('link'), _xyz(o.get('xyz')), _rpy(o.get('rpy')))
    out = {}
    for child in fixed:
        if child.endswith('_fingertip'):
            p = np.zeros(3); body = child
            while body in fixed:
                parent, t, r = fixed[body]; p = r.apply(p) + t; body = parent
            out[body] = p
    return out


def revolute_joints(side):
    """[(name, parent, child, R_origin, axis, lower, upper)] for the revolute joints."""
    root = ET.parse(urdf_path(side)).getroot(); js = []
    for j in root.findall('joint'):
        if j.get('type') != 'revolute':
            continue
        o = j.find('origin'); l = j.find('limit')
        js.append((j.get('name'), j.find('parent').get('link'), j.find('child').get('link'), _rpy(o.get('rpy')), _xyz(j.find('axis').get('xyz')),
                   float(l.get('lower')), float(l.get('upper'))))
    return js


def joint_angles(links_pose, joints):
    """{joint: (angle about its axis, off-axis residual angle)} from parent/child link poses (xyzw) at one frame."""
    out = {}
    for name, par, ch, Ro, ax, lo, hi in joints:
        if par not in links_pose or ch not in links_pose:
            continue
        Rp = R.from_quat(links_pose[par][3:7]); Rc = R.from_quat(links_pose[ch][3:7])
        rv = (Ro.inv() * Rp.inv() * Rc).as_rotvec(); a = float(rv @ ax)
        out[name] = (a, float(np.linalg.norm(rv - a * ax)))
    return out


class ObjGeom:
    """Object collision proxy (CoACD pieces) + the render mesh for face normals + the plate PCA frame."""

    def __init__(self, hull_npz, glb):
        d = np.load(hull_npz); self.pieces = []
        for k in d.files:
            V = d[k]; h = ConvexHull(V)
            self.pieces.append(dict(E=h.equations, tm=trimesh.Trimesh(V, h.simplices, process=True), V=V[h.vertices]))
        self.hullV = np.vstack([p['V'] for p in self.pieces])
        self.m = trimesh.load(glb, force='mesh'); self.pq = trimesh.proximity.ProximityQuery(self.m)
        V = self.m.vertices; c = V.mean(0); W = np.linalg.svd(V - c, full_matrices=False)[2]; P = (V - c) @ W.T
        lo = P[P[:, 0] < np.percentile(P[:, 0], 15)]; hi = P[P[:, 0] > np.percentile(P[:, 0], 85)]
        if np.ptp(lo[:, 1]) > np.ptp(hi[:, 1]):
            W[0] *= -1; W[1] *= -1
        if np.linalg.det(W) < 0:
            W[2] *= -1
        self.c, self.W = c, W
        self.radius = float(np.linalg.norm(self.hullV - self.hullV.mean(0), axis=1).max()); self.ctr = self.hullV.mean(0)

    def lb(self, X):
        """Lower-bound signed distance (exact inside) and the arg piece."""
        best = np.full(len(X), np.inf); arg = np.zeros(len(X), int)
        for i, p in enumerate(self.pieces):
            d = (X @ p['E'][:, :3].T + p['E'][:, 3]).max(1); k = d < best; best[k] = d[k]; arg[k] = i
        return best, arg

    def exact(self, X):
        """Exact signed distance + closest surface point (object frame), vectorised per piece."""
        X = np.atleast_2d(X); d0, arg = self.lb(X); D = np.full(len(X), np.inf); CP = np.zeros_like(X)
        inside = d0 <= 0
        for i, p in enumerate(self.pieces):
            k = np.where(~inside | (arg == i))[0]
            if inside.any():
                k = np.where((~inside) | (inside & (arg == i)))[0]
            if len(k) == 0:
                continue
            cp, dist, _ = trimesh.proximity.closest_point(p['tm'], X[k])
            for j, kk in enumerate(k):
                if inside[kk]:
                    D[kk] = d0[kk]; CP[kk] = cp[j]
                elif dist[j] < D[kk]:
                    D[kk] = dist[j]; CP[kk] = cp[j]
        return D, CP

    def pca(self, Xo):
        return (np.atleast_2d(Xo) - self.c) @ self.W.T

    def face(self, Xo):
        """Render-mesh normal at the nearest surface point (object frame) and its PCA axis-3 component."""
        cp, _, tri = self.pq.on_surface(np.atleast_2d(Xo)); n = self.m.face_normals[tri]
        return n, n @ self.W[2]


def link_world(pose, P):
    return R.from_quat(pose[3:7]).apply(P) + pose[:3]


def to_obj(pose, X):
    return R.from_quat(pose[3:7]).inv().apply(X - pose[:3])


def rot_deg(q1, q2):
    return float(np.degrees((R.from_quat(q1) * R.from_quat(q2).inv()).magnitude()))


def load_trace(path):
    d = np.load(path); L = [str(x) for x in d['labels']]; q = d['q'].astype(float)
    objs = {l[len('track3_'):-len('/object')]: q[:, i] for i, l in enumerate(L) if l.startswith('track3_') and l.endswith('/object')}
    links = {l.split('/')[-1]: q[:, i] for i, l in enumerate(L) if '_sharpa_wave/' in l}
    return dict(T=len(q), obj=objs, links=links, frame=d['frame'], labels=L, q=q)


def load_ref(path):
    t = pq.read_table(path); names = t.column('object_body_names')[0].as_py()
    T = len(np.array(t.column('robot_left_wrist_position')[0].as_py(), float).reshape(-1, 3))
    OP = np.array(t.column('object_body_position')[0].as_py(), float).reshape(T, len(names), 3)
    OQ = np.array(t.column('object_body_wxyz')[0].as_py(), float).reshape(T, len(names), 4)[..., [1, 2, 3, 0]]
    links = {}
    for s in ('left', 'right'):
        fn = t.column(f'{s}_robot_frame_names')[0].as_py(); F = np.array(t.column(f'robot_{s}_frames')[0].as_py(), float).reshape(T, -1, 7)
        for k, n in enumerate(fn):
            links[n] = np.c_[F[:, k, :3], F[:, k, [4, 5, 6, 3]]]
    obj = {n: np.concatenate([OP[:, j], OQ[:, j]], 1) for j, n in enumerate(names)}
    return dict(T=T, names=names, obj=obj, links=links)
