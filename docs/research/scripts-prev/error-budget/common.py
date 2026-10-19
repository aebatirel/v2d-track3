"""Shared loaders for the Track 3 error-budget analysis (research only)."""
import glob, json, os, importlib.util
import numpy as np
import pyarrow.parquet as pq

S = "/private/tmp/claude-501/-Users-aebatirel-Documents-Code-SlamDunk/ad61ecbd-403d-49a3-817f-1f8b688b5549/scratchpad"
PUB = f"{S}/t3/public"
KIT = f"{S}/kit_v2/v2d_submission_kit/metric_code/track_3"
FPS = json.load(open(f"{PUB}/meta/info.json"))["fps"]
TASKS = {json.loads(l)["episode_index"]: json.loads(l)["task"] for l in open(f"{PUB}/meta/episodes_metadata.jsonl")}


def load_metric(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), f"{KIT}/{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_episode(path):
    """Return dict(ep, names, t, pose[T,N,7] as xyz+qxyzw, vis[T,N])."""
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
    return dict(ep=int(df["episode_index"].iloc[0]), names=names, frame=df["frame_index"].to_numpy(),
                ts=df["timestamp"].to_numpy(), pose=pose, vis=vis)


def all_episodes():
    return [load_episode(p) for p in sorted(glob.glob(f"{PUB}/data/chunk-000/*.parquet"))]


# ---- quaternion helpers (xyzw) ----
def qmul(a, b):
    ax, ay, az, aw = np.moveaxis(a, -1, 0); bx, by, bz, bw = np.moveaxis(b, -1, 0)
    return np.stack([aw*bx+ax*bw+ay*bz-az*by, aw*by-ax*bz+ay*bw+az*bx,
                     aw*bz+ax*by-ay*bx+az*bw, aw*bw-ax*bx-ay*by-az*bz], -1)


def qconj(q):
    return q * np.array([-1, -1, -1, 1.0])


def qaxang(axis, ang):
    axis = np.asarray(axis, float); axis = axis / np.linalg.norm(axis, axis=-1, keepdims=True)
    ang = np.asarray(ang, float)[..., None]
    return np.concatenate([axis*np.sin(ang/2), np.cos(ang/2)], -1)


def qrot(q, v):
    qv = np.concatenate([v, np.zeros(v.shape[:-1] + (1,))], -1)
    return qmul(qmul(q, qv), qconj(q))[..., :3]


def qangle(a, b):
    d = np.clip(np.abs(np.sum(a*b, -1)), 0, 1)
    return 2*np.arctan2(np.sqrt(np.maximum(0, 1-d*d)), d)


def slerp(q0, q1, w):
    d = np.sum(q0*q1, -1, keepdims=True)
    q1 = np.where(d < 0, -q1, q1); d = np.abs(d)
    th = np.arccos(np.clip(d, -1, 1)); s = np.sin(th)
    w = np.asarray(w)[..., None] if np.ndim(w) else w
    out = np.where(s < 1e-6, (1-w)*q0 + w*q1, (np.sin((1-w)*th)*q0 + np.sin(w*th)*q1)/np.where(s < 1e-6, 1, s))
    return out / np.linalg.norm(out, axis=-1, keepdims=True)


def fill_gaps(pose, vis):
    """Interpolate invisible frames (linear pos, slerp rot); hold at ends."""
    out = pose.copy(); T, N, _ = pose.shape
    idx = np.arange(T)
    for j in range(N):
        v = np.where(vis[:, j])[0]
        if len(v) == 0:
            continue
        for k in range(3):
            out[:, j, k] = np.interp(idx, v, pose[v, j, k])
        q = pose[v, j, 3:].copy()
        for i in range(1, len(q)):  # sign continuity
            if np.dot(q[i], q[i-1]) < 0:
                q[i] = -q[i]
        hi = np.searchsorted(v, idx).clip(1, len(v)-1); lo = hi-1
        w = np.clip((idx - v[lo]) / np.maximum(v[hi]-v[lo], 1), 0, 1)
        if len(v) == 1:
            out[:, j, 3:] = q[0]
        else:
            out[:, j, 3:] = slerp(q[lo], q[hi], w)
    return out
