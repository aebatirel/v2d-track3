"""Shared loaders for agent 11 (placement priors). Research only."""
import glob, json, importlib.util, struct
import numpy as np
import pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as Rot

ROOT = "/Users/aebatirel/Documents/Code/v2d-research"
PUB = f"{ROOT}/data/track_3/public"
KIT = f"{ROOT}/kit/v2d_submission_kit/metric_code/track_3"
TASKS = {json.loads(l)["episode_index"]: json.loads(l)["task"] for l in open(f"{PUB}/meta/episodes_metadata.jsonl")}
NOTES = {json.loads(l)["episode_index"]: json.loads(l)["notes"] for l in open(f"{PUB}/meta/episodes_metadata.jsonl")}
EVAL = json.load(open(f"{ROOT}/kit/v2d_submission_kit/data/track_3_evaluation_objects.json"))["episodes"]
EVAL = {int(k): v for k, v in EVAL.items()}


def load_metric(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), f"{KIT}/{name}.py")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod


def load_episode(ep):
    t = pq.read_table(f"{PUB}/data/chunk-000/episode_{ep:06d}.parquet")
    names = json.loads(t.schema.metadata[b"objects"])
    df = t.to_pandas().sort_values("frame_index")
    T, N = len(df), len(names)
    pose = np.full((T, N, 7), np.nan); vis = np.zeros((T, N), bool)
    for i, objs in enumerate(df["observation.objects"]):
        for o in objs:
            j = names.index(o["name"]); p = np.asarray(o["pose"], np.float64)
            pose[i, j, :3] = p[:3]; pose[i, j, 3:] = [p[4], p[5], p[6], p[3]]  # -> xyzw
            vis[i, j] = bool(o["visible"])
    return dict(ep=ep, task=TASKS[ep], names=names, frame=df["frame_index"].to_numpy(), ts=df["timestamp"].to_numpy(),
                index=df["index"].to_numpy(), task_index=int(df["task_index"].iloc[0]), pose=pose, vis=vis)


PUBLIC = sorted(TASKS)


def R_of(q_xyzw):
    return Rot.from_quat(q_xyzw).as_matrix()

# body "up at rest" axis per object (from note 07 table), and a horizontal body reference axis for yaw
UP = {"beige_cup": [0, 0, -1], "blue_cup": [0, 0, -1], "mini_dust_pan": [1, 0, 0], "mini_sweeper": [0, 0, 1],
      "plastic_dish_rack": [1, 0, 0], "water_pitcher": [0, 0, 1], "white_pot": [1, 0, 0], "white_pot_lid": [1, 0, 0],
      "wooden_piece_1": [1, 0, 0], "wooden_piece_2": [-1, 0, 0]}
HREF = {"beige_cup": [1, 0, 0], "blue_cup": [1, 0, 0], "mini_dust_pan": [0, 0, 1], "mini_sweeper": [0, 1, 0],
        "plastic_dish_rack": [0, 0, 1], "water_pitcher": [0, 1, 0], "white_pot": [0, 0, 1], "white_pot_lid": [0, 0, 1],
        "wooden_piece_1": [0, 0, 1], "wooden_piece_2": [0, 0, 1]}


def yaw_tilt(q, name):
    """yaw (deg) of body HREF axis projected on world xy; tilt (deg) of body UP axis from world +z."""
    R = R_of(q)
    u = R @ np.array(UP[name], float); h = R @ np.array(HREF[name], float)
    tilt = np.degrees(np.arccos(np.clip(u[..., 2] if u.ndim == 1 else u[:, 2], -1, 1)))
    yaw = np.degrees(np.arctan2(h[..., 1], h[..., 0]))
    return yaw, tilt


def wrap(a):
    return (np.asarray(a) + 180) % 360 - 180


def glb_mesh(name):
    import trimesh
    import os
    p = f"{PUB}/mesh/{name}/{name}.glb"
    if not os.path.exists(p):
        p = f"{PUB}/mesh/{name}/{name}_visual.glb"
    s = trimesh.load(p, force="scene")
    return trimesh.util.concatenate([g for g in s.dump()])


def surface_points(name, n=500, seed=0):
    m = glb_mesh(name)
    rng = np.random.default_rng(seed)
    pts, _ = trimesh_sample(m, n, rng)
    return pts


def trimesh_sample(m, n, rng):
    a = m.area_faces; ch = rng.choice(len(a), size=n, p=a / a.sum())
    tri = m.triangles[ch]; r1, r2 = rng.random(n), rng.random(n); s = np.sqrt(r1)[:, None]
    return (1 - s) * tri[:, 0] + s * (1 - r2[:, None]) * tri[:, 1] + s * r2[:, None] * tri[:, 2], ch
