"""Shared helpers for the ep18 / ep39 plate audit (2026-10-24). Diagnostics only.
- Hand collision geometry from the Sharpa Wave URDFs (convex hull samples per link, as MuJoCo collides mesh geoms;
  fixed children such as the elastomer pads are composed into their parent link, as FlashCHORD collapses them).
- Object collision geometry = CoACD convex pieces of our library_v3 mesh (Newton settings, scratchpad/audit/hulls),
  signed distance = min over pieces of max over face planes (exact inside, lower bound outside; exact when the
  closest feature is a face).
- Reference (our ref_gl*.parquet) and trace (tools/trace_rollout.py npz) loaders, quaternions xyzw everywhere.
"""
import os
import xml.etree.ElementTree as ET

import numpy as np
import pyarrow.parquet as pq
import trimesh
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation as R

SP = '/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad'
ASSETS = f'{SP}/src/video_to_data/robotic_grounding/flash_chord/src/flash_chord/assets'
HULLS = f'{SP}/audit/hulls'
FINGERS = ('thumb', 'index', 'middle', 'ring', 'pinky')


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


def hand_points(side, n=150):
    """{body link name: (N, 3) local collision-surface samples}; fixed-joint children composed into the parent."""
    path = f'{ASSETS}/urdfs/sharpawave/{side}_sharpawave.urdf'; root = ET.parse(path).getroot(); base = os.path.dirname(path)
    fixed = {}
    for j in root.findall('joint'):
        if j.get('type') == 'fixed':
            o = j.find('origin'); fixed[j.find('child').get('link')] = (j.find('parent').get('link'),
                                                                       _xyz(o.get('xyz') if o is not None else ''),
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
        while body in fixed:                                       # compose into the collapsed parent body
            parent, t, r = fixed[body]; P = r.apply(P) + t; body = parent
        out.setdefault(body, []).append(P)
    return {k: np.vstack(v) for k, v in out.items()}


class HullSDF:
    def __init__(self, obj):
        d = np.load(f'{HULLS}/{obj}.npz'); self.eqs = []
        for k in d.files:
            h = ConvexHull(d[k]); self.eqs.append(h.equations)          # n . x + off <= 0 inside, |n| = 1
        self.n_hulls = len(self.eqs)

    def __call__(self, X):
        X = np.atleast_2d(X); best = np.full(len(X), np.inf)
        for E in self.eqs:
            d = (X @ E[:, :3].T + E[:, 3]).max(1); best = np.minimum(best, d)
        return best


class MeshSDF:
    def __init__(self, glb):
        self.m = trimesh.load(glb, force='mesh'); self.q = trimesh.proximity.ProximityQuery(self.m)

    def __call__(self, X):
        return -self.q.signed_distance(np.atleast_2d(X))        # trimesh: + inside -> flip to + outside


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
    return dict(t=t, T=T, names=names, obj=np.concatenate([OP, OQ], 2), links=links)


def load_trace(path):
    d = np.load(path); L = [str(x) for x in d['labels']]; q = d['q'].astype(float)
    objs = {l[len('track3_'):-len('/object')]: q[:, i] for i, l in enumerate(L) if l.startswith('track3_') and l.endswith('/object')}
    links = {l.split('/')[-1]: q[:, i] for i, l in enumerate(L) if '_sharpa_wave/' in l}
    return dict(T=len(q), obj=objs, links=links, frame=d['frame'])


def link_world(pose, P):
    return R.from_quat(pose[3:7]).apply(P) + pose[:3]


def to_obj(pose, X):
    return R.from_quat(pose[3:7]).inv().apply(X - pose[:3])


def rot_deg(q1, q2):
    return float(np.degrees((R.from_quat(q1) * R.from_quat(q2).inv()).magnitude()))


def link_dists(links_pose, hp, objpose, sdf, side=None):
    """{link: min signed distance (m) of its collision samples to the object} at one frame."""
    out = {}
    for ln, P in hp.items():
        if side and not ln.startswith(side):
            continue
        if ln not in links_pose:
            continue
        X = to_obj(objpose, link_world(links_pose[ln], P)); out[ln] = float(sdf(X).min())
    return out
