"""DIG 20 stage C helpers: frames (D18 undistorted pinhole), frame-0 cameras (D18 map registration), GT slot-0
perturbation reference, mesh silhouettes. GT is used only by the validation harness (masks at frame 0, scoring)."""
import sys, json, numpy as np, cv2, trimesh
from scipy.spatial.transform import Rotation as Rot
ROOT = '/Users/aebatirel/Documents/Code/v2d-research'
D3 = f'{ROOT}/data/track_3'
OUT = f'{ROOT}/work/20/out/c'
sys.path.insert(0, f'{ROOT}/work/11'); sys.path.insert(0, f'{ROOT}/work/18')
import c11
from a1_extract import NEW, newK, maps as d18maps
PUB = [0, 2, 11, 12, 13, 18, 21, 22, 23, 24, 26, 27, 31, 39, 40, 41, 42, 43, 44]
EV = [1, 3, 5, 6, 8, 10, 14, 15, 16, 19, 20, 25, 28, 30, 32, 33, 35, 36, 37, 38]
_REG = None; _A10 = None; _MAPS = {}


def clip(split, ep, c):
    return f'{D3}/{split}/videos/chunk-000/observation.images.ego_cam_{c}/episode_{ep:06d}.mp4'


def frames(split, ep, c, n_max=10 ** 9, gray=False):
    """undistorted pinhole frames (cam a colour 1014x760 f=500; b/c gray 1280x800 f=420)."""
    if c not in _MAPS: _MAPS[c] = d18maps(c)
    (m1, m2), (w0, h0) = _MAPS[c]
    cap = cv2.VideoCapture(clip(split, ep, c)); out = []
    while len(out) < n_max:
        ok, fr = cap.read()
        if not ok: break
        g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY) if (c != 'a' or gray) else fr
        out.append(cv2.remap(g, m1, m2, cv2.INTER_AREA if c == 'a' else cv2.INTER_LINEAR))
    return out


def cam0(ep, c='a'):
    """frame-0 camera of public ep in the mocap world: (Rwc [cols x right, y down, z fwd], C). D18 a8 + a10."""
    global _REG, _A10
    if _REG is None:
        _REG = json.load(open(f'{ROOT}/work/18/a8_registration.json'))['poses']
        _A10 = json.load(open(f'{ROOT}/work/18/a10_yaw_per_episode.json'))['episodes']
    ks = sorted(k for k in _REG if k.startswith(f'a/p{ep:02d}_'))
    Cbar = np.mean([np.array(_REG[k]['C']) for k in ks], 0)
    o = np.array(_A10[str(ep)]['o']); Rz = Rot.from_euler('z', o[3], degrees=True).as_matrix()
    k0 = f'{c}/p{ep:02d}_0000.jpg'
    R = np.array(_REG[k0]['R_wc']); C = np.array(_REG[k0]['C'])
    return Rz @ R, Rz @ (C - Cbar) + Cbar + o[:3]


_MESH = {}


def mesh(name):
    if name not in _MESH:
        m = c11.glb_mesh(name)
        _MESH[name] = (np.asarray(m.vertices), np.asarray(m.faces))
    return _MESH[name]


def silhouette(name, pose7, Rwc, C, c='a'):
    """filled silhouette (uint8 0/255) + median depth. pose7 = [x y z qx qy qz qw] (c11 order)."""
    w, h, f = NEW[c]; K = newK(c)
    V, F = mesh(name)
    Xw = V @ c11.R_of(pose7[3:]).T + pose7[:3]
    Xc = (Xw - C) @ Rwc
    m = np.zeros((h, w), np.uint8)
    ok = Xc[:, 2] > 0.05
    uv = Xc[:, :2] / np.maximum(Xc[:, 2:3], 1e-3) * f + K[:2, 2]
    good = ok[F].all(1)
    tri = np.round(uv[F[good]] * 4).astype(np.int32)
    cv2.fillPoly(m, list(tri), 255, lineType=cv2.LINE_8, shift=2)
    return m, float(np.median(Xc[ok, 2])) if ok.any() else np.nan


def gt_ref(ep, j=None):
    """slot 0 (parquet row order, as preonset.py) unless column j given: first >1mm|1deg row, 1 cm onset row,
    per-row displacement (mm) and rotation (deg) from row 0."""
    e = c11.load_episode(ep)
    if j is None: j = e['names'].index(slot0_name(ep))
    P = e['pose'][:, j]
    d = np.linalg.norm(P[:, :3] - P[0, :3], axis=1) * 1000
    q = Rot.from_quat(P[:, 3:]); a = np.degrees((q[0].inv() * q).magnitude())
    pert = int(np.argmax((d > 1) | (a > 1))) if ((d > 1) | (a > 1)).any() else len(d)
    on = int(np.argmax(d > 10)) if (d > 10).any() else len(d)
    # robust reference: >1.5 mm or >1.5 deg sustained for 3 consecutive rows (rejects 1-row spikes and the
    # ~1 deg marker-fit steps seen in p2/p18)
    x = (d > 1.5) | (a > 1.5); run = np.convolve(x.astype(int), np.ones(3, int), 'valid') == 3
    pert_r = int(np.argmax(run)) if run.any() else len(d)
    return dict(e=e, j=j, name=e['names'][j], pert_r=pert_r, pert=pert, on=on, d=d, a=a, n=len(d))


def slot0_name(ep):
    """slot 0 as the parquet's first object in row 0 (as in work/15/c2/preonset.py)."""
    import pandas as pd
    df = pd.read_parquet(f'{D3}/public/data/chunk-000/episode_{ep:06d}.parquet', columns=['observation.objects'])
    return df['observation.objects'].iloc[0][0]['name']
