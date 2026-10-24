"""Shared helpers for the start-instability audit (ep21, ep2, ep26). No ground truth here."""
import os, glob, xml.etree.ElementTree as ET
import numpy as np, pyarrow.parquet as pq, trimesh
from scipy.spatial.transform import Rotation as R

W = '/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/grasp_work/audit-starts'
S = '/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad'
FC = f'{S}/src/video_to_data/robotic_grounding/flash_chord/src/flash_chord/assets'
LIB = '/home/user/v2d-track3/meshes/library_v3'
KIT = f'{S}/kit/v2d_submission_kit'
RUNS = {21: '20261024-e2-e49e83d', 2: '20261024-e3-e49e83d', 26: '20261024-w1-37cc551'}


def run_dir(ep):
    return f'{W}/data/store/runs/{RUNS[ep]}'


def ref_path(ep, kind='ref_gl_ilc'):
    if os.environ.get('REFDIR'):                       # a locally built grasp-lock tree (CPU rebuilds)
        return glob.glob(f"{os.environ['REFDIR']}/processed/*/*/{kind}.parquet")[0]
    return glob.glob(f'{run_dir(ep)}/refs/glock/ep{ep}/processed/*/*/{kind}.parquet')[0]


def gl_json(ep, kind='ref_gl'):
    if os.environ.get('REFDIR'):
        return glob.glob(f"{os.environ['REFDIR']}/processed/*/*/{kind}_grasp_lock.json")[0]
    return glob.glob(f'{run_dir(ep)}/refs/glock/ep{ep}/processed/*/*/{kind}_grasp_lock.json')[0]


def col(t, c):
    return t.column(c)[0].as_py()


def load_ref(path):
    t = pq.read_table(path)
    names = col(t, 'object_body_names'); B = len(names)
    T = len(np.array(col(t, 'robot_left_wrist_position'), float).reshape(-1, 3))
    d = dict(names=names, T=T)
    d['OP'] = np.array(col(t, 'object_body_position'), float).reshape(T, B, 3)
    d['OQ'] = np.array(col(t, 'object_body_wxyz'), float).reshape(T, B, 4)[..., [1, 2, 3, 0]]  # xyzw
    for s in ('left', 'right'):
        d[f'wpos_{s}'] = np.array(col(t, f'robot_{s}_wrist_position'), float).reshape(T, 3)
        d[f'J_{s}'] = np.array(col(t, f'mano_{s}_joints'), float).reshape(T, 21, 3)
        try:
            d[f'frames_{s}'] = np.array(col(t, f'robot_{s}_frames'), float).reshape(T, -1, 7)
            d[f'fnames_{s}'] = col(t, f'{s}_robot_frame_names')
        except Exception:
            pass
    return d


def load_trace(path):
    z = np.load(path)
    return z['q'].astype(float), [str(x) for x in z['labels']], z['frame']


def obj_index(labels, o):
    return labels.index(f'track3_{o}/object')


def rot_deg(qa, qb):
    return np.degrees((R.from_quat(qa) * R.from_quat(qb).inv()).magnitude())


# ---------------- hand collision geometry (Sharpa Wave URDF; fixed children folded onto the parent body) -------------
def _T(xyz, rpy):
    M = np.eye(4); M[:3, :3] = R.from_euler('xyz', rpy).as_matrix(); M[:3, 3] = xyz; return M


def hand_points(side, n_per=150, seed=0):
    """{body label: (N,3) collision-surface samples in the body frame}."""
    urdf = f'{FC}/urdfs/sharpawave/{side}_sharpawave.urdf'
    root = ET.parse(urdf).getroot(); base = os.path.dirname(urdf)
    def f3(e, k, dflt='0 0 0'):
        return np.array([float(x) for x in (e.get(k) if e is not None and e.get(k) else dflt).split()])
    coll = {}
    for L in root.findall('link'):
        lst = []
        for c in L.findall('collision'):
            o = c.find('origin'); m = c.find('geometry/mesh')
            if m is None:
                continue
            lst.append((_T(f3(o, 'xyz'), f3(o, 'rpy')), os.path.normpath(os.path.join(base, m.get('filename')))))
        coll[L.get('name')] = lst
    fixed = {}
    for j in root.findall('joint'):
        if j.get('type') == 'fixed':
            o = j.find('origin'); fixed[j.find('child').get('link')] = (j.find('parent').get('link'), _T(f3(o, 'xyz'), f3(o, 'rpy')))
    rng = np.random.default_rng(seed); out = {}
    for link, lst in coll.items():
        body, M = link, np.eye(4)
        while body in fixed:
            par, Tj = fixed[body]; M = Tj @ M; body = par
        for Tc, fn in lst:
            mesh = trimesh.load(fn, force='mesh')
            p, _ = trimesh.sample.sample_surface(mesh, n_per, seed=int(rng.integers(1e9)))
            p = np.c_[p, np.ones(len(p))] @ (M @ Tc).T
            out.setdefault(body, []).append(p[:, :3])
    return {k: np.concatenate(v) for k, v in out.items()}


# ---------------- object collision geometry: FlashCHORD's own CoACD hulls ---------------------------------------
class Hulls:
    def __init__(self, npz):
        z = np.load(npz); n = int(z['n'])
        self.H = [trimesh.Trimesh(z[f'v{i}'], z[f'f{i}']).convex_hull for i in range(n)]
        self.eq = [np.c_[h.face_normals, -np.einsum('ij,ij->i', h.face_normals, h.triangles[:, 0])] for h in self.H]
        self.n = n

    def depth(self, P):
        """per point: penetration depth into the union of hulls (>0 inside: distance to the nearest face of the
        deepest containing hull), and a lower bound of the outside distance (max plane distance, min over hulls)."""
        P = np.asarray(P); dep = np.zeros(len(P)); out = np.full(len(P), np.inf)
        for e in self.eq:
            s = P @ e[:, :3].T + e[:, 3]  # >0 outside each face
            m = s.max(1)
            inside = m <= 0
            dep[inside] = np.maximum(dep[inside], -m[inside])
            out = np.minimum(out, np.where(inside, 0.0, m))
        return dep, out


def hull_path(o):
    return f'{W}/data/hulls/{o}_0.npz'


def world_to_local(P, pos, q):
    return R.from_quat(q).inv().apply(P - pos)


def local_to_world(P, pos, q):
    return R.from_quat(q).apply(P) + pos
