"""Shared loaders for note 14 (policy tracking error). Research only.

Public GT is read for analysis; nothing here is used for inference.
"""
import glob, json, importlib.util
import numpy as np
import pyarrow.parquet as pq

ROOT = "/Users/aebatirel/Documents/Code/v2d-research"
PUB = f"{ROOT}/data/track_3/public"
KIT = f"{ROOT}/kit/v2d_submission_kit/metric_code/track_3"
FPS = 20.0  # true capture rate (note 06)


def load_metric(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), f"{KIT}/{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_episode(path):
    """Return dict(ep, names, pose[T,N,7] xyz+qxyzw, vis[T,N])."""
    t = pq.read_table(path)
    names = json.loads(t.schema.metadata[b"objects"])
    df = t.to_pandas().sort_values("frame_index")
    T, N = len(df), len(names)
    pose = np.full((T, N, 7), np.nan)
    vis = np.zeros((T, N), bool)
    for i, objs in enumerate(df["observation.objects"]):
        for o in objs:
            j = names.index(o["name"])
            p = np.asarray(o["pose"], np.float64)
            pose[i, j, :3] = p[:3]
            pose[i, j, 3:] = [p[4], p[5], p[6], p[3]]  # wxyz -> xyzw
            vis[i, j] = bool(o["visible"])
    return dict(ep=int(df["episode_index"].iloc[0]), names=names, pose=pose, vis=vis)


def all_episodes():
    return [load_episode(p) for p in sorted(glob.glob(f"{PUB}/data/chunk-000/*.parquet"))]


def qmul(a, b):
    ax, ay, az, aw = np.moveaxis(a, -1, 0); bx, by, bz, bw = np.moveaxis(b, -1, 0)
    return np.stack([aw*bx+ax*bw+ay*bz-az*by, aw*by-ax*bz+ay*bw+az*bx,
                     aw*bz+ax*by-ay*bx+az*bw, aw*bw-ax*bx-ay*by-az*bz], -1)


def qconj(q):
    return q * np.array([-1, -1, -1, 1.0])


def qangle(a, b):
    d = np.clip(np.abs(np.sum(a*b, -1)), 0, 1)
    return 2*np.arctan2(np.sqrt(np.maximum(0, 1-d*d)), d)


def qaxang(axis, ang):
    axis = np.asarray(axis, float); axis = axis / np.linalg.norm(axis, axis=-1, keepdims=True)
    ang = np.asarray(ang, float)[..., None]
    return np.concatenate([axis*np.sin(ang/2), np.cos(ang/2)], -1)


def slerp(q0, q1, w):
    d = np.sum(q0*q1, -1, keepdims=True)
    q1 = np.where(d < 0, -q1, q1); d = np.abs(d)
    th = np.arccos(np.clip(d, -1, 1)); s = np.sin(th)
    w = np.asarray(w, float)
    if w.ndim:
        w = w[..., None]
    out = np.where(s < 1e-6, (1-w)*q0 + w*q1, (np.sin((1-w)*th)*q0 + np.sin(w*th)*q1)/np.where(s < 1e-6, 1, s))
    return out / np.linalg.norm(out, axis=-1, keepdims=True)


def fill_gaps(pose, vis):
    """Interpolate invisible frames (linear pos, slerp rot); hold at ends."""
    out = pose.copy(); T, N, _ = pose.shape
    idx = np.arange(T)
    for j in range(N):
        v = np.where(vis[:, j] & np.isfinite(pose[:, j, 0]))[0]
        if len(v) == 0:
            continue
        for k in range(3):
            out[:, j, k] = np.interp(idx, v, pose[v, j, k])
        q = pose[v, j, 3:].copy()
        for i in range(1, len(q)):
            if np.dot(q[i], q[i-1]) < 0:
                q[i] = -q[i]
        if len(v) == 1:
            out[:, j, 3:] = q[0]
            continue
        hi = np.searchsorted(v, idx).clip(1, len(v)-1); lo = hi-1
        w = np.clip((idx - v[lo]) / np.maximum(v[hi]-v[lo], 1), 0, 1)
        out[:, j, 3:] = slerp(q[lo], q[hi], w)
    return out


_VCACHE = {}


def mesh_points(name, n=500, seed=0):
    """Area-weighted surface samples of the public scan, in the scan (object) frame."""
    if name in _VCACHE:
        return _VCACHE[name]
    import trimesh
    import os
    path = f"{PUB}/mesh/{name}/{name}.glb"
    if not os.path.exists(path):
        path = f"{PUB}/mesh/{name}/{name}_visual.glb"
    m = trimesh.load(path, force="mesh")
    rng = np.random.default_rng(seed)
    a = m.area_faces
    f = rng.choice(len(a), size=n, p=a / a.sum())
    tri = m.triangles[f]
    r1, r2 = rng.random(n), rng.random(n)
    s = np.sqrt(r1)[:, None]
    pts = (1 - s) * tri[:, 0] + s * (1 - r2[:, None]) * tri[:, 1] + s * r2[:, None] * tri[:, 2]
    _VCACHE[name] = pts
    return pts


MODS = None


def metrics(ach, ref, names):
    """ach/ref: [T,N,7] xyz+qxyzw. Mirrors the official score(): normalise, warp to slot-0 frame-0, metric.
    Returns per-episode values (SP-SR/MP-SR as 0/1)."""
    global MODS
    if MODS is None:
        MODS = {m: load_metric(m) for m in ["AUC", "SP-SR", "MP-SR", "RPE", "MPPE"]}
    A = MODS["AUC"]
    a = A._normalise_quaternions(ach[:, None], "submission", ValueError)
    r = A._normalise_quaternions(ref[:, None], "solution", ValueError)
    a = A._warp_to_reference_start(a, r)
    ids = np.arange(ach.shape[1])
    v = np.stack([mesh_points(n) for n in names])
    return dict(AUC=A._add_auc(A._object_add(a, r, v)),
                SPSR=float(np.mean(MODS["SP-SR"]._spider_success(a, r))),
                MPSR=float(np.mean(MODS["MP-SR"]._maniptrans_success(a, r, ids))),
                RPE=MODS["RPE"]._relative_position_error_cm(a, r),
                MPPE=MODS["MPPE"]._mean_per_point_error_cm(a, r))
