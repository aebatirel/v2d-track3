"""Stage B retry [H test]: is the published roll tied to how each object rests (world up in body coords at frame 0 and
last frame), across the 20 public GT episodes? Analysis only (public GT)."""
import glob, numpy as np, pandas as pd
from scipy.spatial.transform import Rotation as Rot
P = "/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public/data/chunk-000"
rows = {}
for f in sorted(glob.glob(f"{P}/episode_*.parquet")):
    ep = int(f[-14:-8]); df = pd.read_parquet(f, columns=["observation.objects"])
    for fi in (0, len(df) - 1):
        for o in df["observation.objects"].iloc[fi]:
            q = o["pose"][3:7]; R = Rot.from_quat([q[1], q[2], q[3], q[0]]).as_matrix()
            up = R.T @ np.array([0, 0, 1.0])
            rows.setdefault(o["name"], []).append((ep, fi, np.round(up, 2), round(o["pose"][2], 3)))
for n, v in sorted(rows.items()):
    U = np.array([r[2] for r in v])
    dom = [("xyz"[int(np.argmax(np.abs(u)))] + ("+" if u[np.argmax(np.abs(u))] > 0 else "-")) for u in U]
    print(f"{n:20s} n={len(v):2d} up-axis counts {dict(zip(*np.unique(dom, return_counts=True)))}  mean up(body) {np.round(U.mean(0),2)}")
