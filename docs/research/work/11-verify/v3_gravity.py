"""Verifier for dig-11 C2 (gravity/table alignment of the mocap world): for every public episode and object resting on
the table at the first / last frame, the convex-hull support face (hull facets within 4 deg of facing down, area-
weighted normal) is compared with mocap -z. Tilt of that face = table tilt in the mocap frame + scan/pose error.
Public GT only (analysis)."""
import json, os, numpy as np, pyarrow.parquet as pq, trimesh
from scipy.spatial.transform import Rotation as Rot
ROOT = "/Users/aebatirel/Documents/Code/v2d-research"; PUB = f"{ROOT}/data/track_3/public"
EPS = [0, 2, 11, 12, 13, 18, 21, 22, 23, 24, 26, 27, 31, 39, 40, 41, 42, 43, 44, 45]
H = {}
def hull(n):
    if n not in H:
        f = f"{PUB}/mesh/{n}/{n}.glb"; f = f if os.path.exists(f) else f.replace(".glb", "_visual.glb")
        m = trimesh.util.concatenate(list(trimesh.load(f, force="scene").dump())); H[n] = m.convex_hull
    return H[n]
rows = []
for ep in EPS:
    t = pq.read_table(f"{PUB}/data/chunk-000/episode_{ep:06d}.parquet"); df = t.to_pandas().sort_values("frame_index")
    names = json.loads(t.schema.metadata[b"objects"])
    for fi in (0, len(df) - 1):
        for o in df["observation.objects"].iloc[fi]:
            p = np.asarray(o["pose"], float); R = Rot.from_quat([p[4], p[5], p[6], p[3]]).as_matrix()
            h = hull(o["name"]); v = h.vertices @ R.T + p[:3]
            if v[:, 2].min() > 0.612: continue  # not resting on the table top (~0.601)
            nrm = h.face_normals @ R.T; a = h.area_faces; sel = nrm[:, 2] < -np.cos(np.radians(4))
            if a[sel].sum() < 1e-4: continue
            n = (nrm[sel] * a[sel, None]).sum(0); n /= np.linalg.norm(n)
            tilt = np.degrees(np.arccos(-n[2])); az = np.degrees(np.arctan2(-n[1], -n[0]))
            rows.append((ep, fi, o["name"], round(v[:, 2].min(), 4), round(a[sel].sum() * 1e4, 1), tilt, az))
for r in rows:
    print(f"ep {r[0]:2d} f{r[1]:3d} {r[2]:18s} zmin {r[3]:.4f} face {r[4]:6.1f} cm2 tilt {r[5]:.2f} az {r[6]:7.1f}")
T = np.array([r[5] for r in rows]); AZ = np.radians([r[6] for r in rows])
vec = np.c_[np.radians(T) * np.cos(AZ), np.radians(T) * np.sin(AZ)]
print(f"n {len(T)} tilt median {np.median(T):.2f} p90 {np.percentile(T, 90):.2f} max {T.max():.2f}; "
      f"mean tilt vector {np.degrees(np.linalg.norm(vec.mean(0))):.2f} deg toward az {np.degrees(np.arctan2(*vec.mean(0)[::-1])):.1f}")
