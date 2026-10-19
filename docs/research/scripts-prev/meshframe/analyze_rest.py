"""Relate public GT rest poses to the mesh frame axes.

For each public episode/object: take the first visible frames (rest), compute
which body axis is vertical and its sign, the lowest mesh point height (table
contact check), and how much the object moves over the episode.
"""
import glob, json, os
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import trimesh
from scipy.spatial.transform import Rotation as Rot

HERE = os.path.dirname(__file__)
ROOT = os.path.join(HERE, "..", "t3", "public")


def mesh_path(name):
    for c in [f"{name}/{name}.glb", f"{name}/{name}_visual.glb"]:
        p = os.path.join(ROOT, "mesh", c)
        if os.path.exists(p):
            return p


_cache = {}


def verts(name):
    if name not in _cache:
        m = trimesh.load(mesh_path(name), force="mesh", process=False)
        V = np.asarray(m.vertices)
        idx = np.random.default_rng(0).choice(len(V), min(len(V), 60000), replace=False)
        _cache[name] = V[idx]
    return _cache[name]


def load(f):
    t = pq.read_table(f).to_pandas()
    rows = []
    for _, r in t.iterrows():
        for slot, o in enumerate(r["observation.objects"]):
            p = np.asarray(o["pose"], float)
            rows.append(dict(frame=int(r["frame_index"]), slot=slot, name=o["name"], visible=bool(o["visible"]),
                             x=p[0], y=p[1], z=p[2], qw=p[3], qx=p[4], qy=p[5], qz=p[6]))
    return pd.DataFrame(rows)


def main():
    out = []
    stats = json.load(open(os.path.join(HERE, "mesh_stats.json")))
    skew = {s["name"].replace("_visual", ""): s["surface_skewness_xyz"] for s in stats if not s["name"].endswith("_collision")}
    for f in sorted(glob.glob(os.path.join(ROOT, "data", "chunk-000", "*.parquet"))):
        ep = int(os.path.basename(f)[8:14])
        df = load(f)
        for (slot, name), g in df.groupby(["slot", "name"]):
            g = g[g.visible].sort_values("frame")
            if len(g) == 0:
                continue
            R = Rot.from_quat(g[["qx", "qy", "qz", "qw"]].to_numpy()).as_matrix()
            P = g[["x", "y", "z"]].to_numpy()
            V = verts(name)
            # rest: first 5 visible frames
            r0 = R[:5].mean(0)
            u, _, vt = np.linalg.svd(r0); r0 = u @ vt
            up_body = r0.T @ np.array([0, 0, 1.0])  # world up in body coords
            k = int(np.argmax(np.abs(up_body)))
            low0 = (V @ r0.T + P[0])[:, 2].min()
            # last frame rest
            r1 = R[-1]
            up1 = r1.T @ np.array([0, 0, 1.0]); k1 = int(np.argmax(np.abs(up1)))
            low1 = (V @ r1.T + P[-1])[:, 2].min()
            # motion
            ang = np.degrees(np.linalg.norm(Rot.from_matrix(R[0].T @ R).as_rotvec(), axis=1))
            disp = np.linalg.norm(P - P[0], axis=1)
            rec = dict(ep=ep, slot=slot, name=name, n_vis=len(g), n_frames=int(df.frame.max() + 1),
                       up_axis_start="+-"[int(up_body[k] < 0)] + "xyz"[k], up_cos_start=float(abs(up_body[k])),
                       up_axis_end="+-"[int(up1[k1] < 0)] + "xyz"[k1], up_cos_end=float(abs(up1[k1])),
                       origin_z_start=float(P[0, 2]), lowest_pt_z_start=float(low0), lowest_pt_z_end=float(low1),
                       max_rot_deg=float(ang.max()), max_disp_m=float(disp.max()),
                       skew=np.round(skew[name], 3).tolist())
            out.append(rec)
    df = pd.DataFrame(out)
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    print(df.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    df.to_csv(os.path.join(HERE, "rest_poses.csv"), index=False)


if __name__ == "__main__":
    main()
