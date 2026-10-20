"""Shared helpers for agent 17: calibration, projection (a/b/c), GT poses, marker world points, frames, visibility."""
import json, os, numpy as np, cv2, pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as Rot
ROOT = '/Users/aebatirel/Documents/Code/v2d-research'
PUB = f'{ROOT}/data/track_3/public'
CAL = json.load(open(f'{PUB}/meta/camera_calibration.json'))['cameras']
CAT = {k: v for k, v in json.load(open(f'{ROOT}/work/17/out/marker_catalogue.json')).items() if isinstance(v, list)}
def cam(c):
    q = CAL[f'ego_cam_{c}']
    K = np.array(q['intrinsic_matrix'], float); d = np.array(q['distortion_coefficients'], float)
    return K, d, tuple(q['resolution'])
def ext(c):
    """T (4x4) mapping X_c -> X_b (b = mono right, the 'stereo_left' reference)."""
    if c == 'b': return np.eye(4)
    E = np.array(CAL[f'ego_cam_{c}']['extrinsics_to_stereo_left'], float); return E
def T_a_to(c):
    """X_c = R X_a + t for target camera c."""
    Tba = ext('a')
    if c == 'a': return np.eye(4)
    if c == 'b': return Tba
    Tbc = ext('c'); return np.linalg.inv(Tbc) @ Tba
def to_cam(Xw, Rwc, C, c='a', own=False):
    """Rwc: columns = cam_a axes in world (x right, y down, z forward); C: cam_a centre in world.
    own=True: (Rwc, C) is the pose of camera c itself."""
    Xa = (np.asarray(Xw) - C) @ Rwc
    if own: return Xa
    T = T_a_to(c); return Xa @ T[:3, :3].T + T[:3, 3]
def project(Xw, Rwc, C, c='a', own=False):
    Xc = to_cam(Xw, Rwc, C, c, own); K, d, _ = cam(c)
    uv, _ = cv2.projectPoints(Xc.reshape(-1, 1, 3), np.zeros(3), np.zeros(3), K, d)
    return uv.reshape(-1, 2), Xc[:, 2]
def Rwc_from(psi, th, ph):
    p, t = np.radians(psi), np.radians(th)
    f = np.array([np.cos(t) * np.cos(p), np.cos(t) * np.sin(p), -np.sin(t)])
    r = np.cross(f, [0, 0, 1.0]); r /= np.linalg.norm(r); d = np.cross(f, r)
    Rr = Rot.from_rotvec(f * np.radians(ph)).as_matrix()
    return np.column_stack([Rr @ r, Rr @ d, f])
def s25_cam(ep):
    s = json.load(open(f'{ROOT}/work/11/s25_refine_native.json'))[str(ep)]
    return Rwc_from(s['psi'], s['th'], s['ph']), np.array(s['C'])
def load_gt(ep):
    t = pq.read_table(f'{PUB}/data/chunk-000/episode_{ep:06d}.parquet')
    names = json.loads(t.schema.metadata[b'objects']); df = t.to_pandas().sort_values('frame_index')
    T, N = len(df), len(names); R = np.zeros((T, N, 3, 3)); tr = np.zeros((T, N, 3))
    for i, objs in enumerate(df['observation.objects']):
        for o in objs:
            j = names.index(o['name']); p = np.asarray(o['pose'], float)
            tr[i, j] = p[:3]; R[i, j] = Rot.from_quat([p[4], p[5], p[6], p[3]]).as_matrix()
    return dict(names=names, R=R, t=tr, frame=df['frame_index'].to_numpy(), cap=df['capture_time'].to_numpy(), ts=df['timestamp'].to_numpy())
def markers_world(gt, i, j):
    n = gt['names'][j]; M = np.array([q['c'] for q in CAT[n]])
    return M @ gt['R'][i, j].T + gt['t'][i, j]
def marker_meta(n):
    return [(q['r'], q['size'], q['src']) for q in CAT[n]]
class Video:
    def __init__(self, ep, c, split='public'):
        self.p = f'{ROOT}/data/track_3/{split}/videos/chunk-000/observation.images.ego_cam_{c}/episode_{ep:06d}.mp4'
        self.cap = cv2.VideoCapture(self.p); self.i = -1
    def get(self, k):
        if k <= self.i: self.cap.set(cv2.CAP_PROP_POS_FRAMES, k); self.i = k - 1
        while self.i < k:
            ok, im = self.cap.read(); self.i += 1
            if not ok: return None
        return im
# --- scan surface points (for z-buffer visibility) ---
_SP = {}
def surf(n, npts=150000):
    if n in _SP: return _SP[n]
    import trimesh
    p = f'{PUB}/mesh/{n}/{n}.glb'
    if not os.path.exists(p): p = f'{PUB}/mesh/{n}/{n}_visual.glb'
    g = list(trimesh.load(p).geometry.values())[0]
    rng = np.random.default_rng(0); a = g.area_faces; fi = rng.choice(len(a), npts, p=a / a.sum())
    r1, r2 = rng.random(npts), rng.random(npts); s1 = np.sqrt(r1); b = np.stack([1 - s1, s1 * (1 - r2), s1 * r2], 1)
    P = (b[:, :, None] * g.vertices[g.faces[fi]]).sum(1)
    # drop samples on the marker spheres themselves (+1 mm) so a marker does not occlude itself
    M = np.array([q['c'] for q in CAT[n]]); rr = np.array([q['r'] for q in CAT[n]])
    keep = np.all(np.linalg.norm(P[:, None] - M[None], axis=2) > rr[None] + 0.0015, axis=1)
    _SP[n] = P[keep]; return _SP[n]
def visibility(gt, i, Rwc, C, c='a', step=2, tol=0.004, own=False):
    """For each object j and marker k: (uv, depth, visible) using a splat z-buffer of all GT-posed objects.
    A marker is visible if its nearest-surface point (centre - r * view dir) is not behind the z-buffer by > tol."""
    K, d, (W, H) = cam(c); w, h = W // step, H // step
    zb = np.full((h, w), np.inf)
    for j, n in enumerate(gt['names']):
        if n not in CAT: continue
        Xw = surf(n) @ gt['R'][i, j].T + gt['t'][i, j]
        uv, z = project(Xw, Rwc, C, c, own); ok = z > 0.05
        u = (uv[ok, 0] / step).astype(int); v = (uv[ok, 1] / step).astype(int); z = z[ok]
        k = (u >= 0) & (u < w) & (v >= 0) & (v < h)
        np.minimum.at(zb, (v[k], u[k]), z[k])
    zb = cv2.erode(np.where(np.isfinite(zb), zb, 1e3).astype(np.float32), np.ones((3, 3), np.uint8))  # fill splat holes (min filter)
    out = []
    for j, n in enumerate(gt['names']):
        if n not in CAT: out.append(None); continue
        Mw = markers_world(gt, i, j); rr = np.array([q['r'] for q in CAT[n]])
        uv, z = project(Mw, Rwc, C, c, own)
        zf = z - rr  # approx front surface depth
        vis = np.zeros(len(Mw), bool); rpx = K[0, 0] * rr / np.maximum(z, 1e-3); frac = np.zeros(len(Mw))
        ang = np.linspace(0, 2 * np.pi, 8, endpoint=False)
        for k in range(len(Mw)):
            if not (z[k] > 0.05): continue
            pts = [(uv[k][0], uv[k][1])] + [(uv[k][0] + 0.7 * rpx[k] * np.cos(a), uv[k][1] + 0.7 * rpx[k] * np.sin(a)) for a in ang]
            ok = []
            for (u, v) in pts:
                u, v = u / step, v / step
                if not (0 <= u < w and 0 <= v < h): continue
                ok.append(zf[k] <= zb[int(v), int(u)] + tol)
            frac[k] = np.mean(ok) if ok else 0.0
            vis[k] = frac[k] >= 0.34
        out.append(dict(uv=uv, z=z, rpx=rpx, vis=vis, frac=frac))
    return out
