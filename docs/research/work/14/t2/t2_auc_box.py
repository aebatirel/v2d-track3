"""AUC proxy for 'perfect tracker of tier-2 noisy input': ADD over 500 points on each mesh's bbox surface."""
import glob, json, os, numpy as np, pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as R
D = os.path.dirname(os.path.abspath(__file__)); bb = json.load(open(f"{D}/glb_bbox.json")); rng = np.random.default_rng(0)
def box_pts(lo, hi, n=500):
    lo, hi = np.array(lo), np.array(hi); p = rng.uniform(lo, hi, (n, 3)); ax = rng.integers(0, 3, n); s = rng.integers(0, 2, n)
    p[np.arange(n), ax] = np.where(s == 1, hi[ax], lo[ax]); return p
res = []
for f1 in sorted(glob.glob(f"{D}/tier1/episode_*.parquet")):
    ep = int(f1[-14:-8]); name = json.loads(pq.read_schema(f1).metadata[b"objects"])[0]
    a = np.stack(pq.read_table(f1, columns=["observation.object.pose"]).column(0).to_pylist()).astype(float)
    b = np.stack(pq.read_table(f"{D}/tier2/episode_{ep:06d}.parquet", columns=["observation.object.pose"]).column(0).to_pylist()).astype(float)
    v = (np.linalg.norm(a[:, 3:], axis=1) > 0.5) & (np.linalg.norm(b[:, 3:], axis=1) > 0.5); a, b = a[v], b[v]
    lo, hi = np.array(bb[name]["min"]), np.array(bb[name]["max"])
    if os.environ.get("SHAPE") == "ellipsoid":
        u = rng.normal(size=(500, 3)); u /= np.linalg.norm(u, axis=1, keepdims=True); V = (lo + hi) / 2 + u * (hi - lo) / 2
    else:
        V = box_pts(lo, hi)
    Ra = R.from_quat(a[:, [4,5,6,3]]).as_matrix(); Rb = R.from_quat(b[:, [4,5,6,3]]).as_matrix()
    add = np.linalg.norm(np.einsum("tij,vj->tvi", Rb - Ra, V) + (b[:, None, :3] - a[:, None, :3]), axis=-1).mean(-1)
    auc = np.trapezoid([np.mean(add < t) for t in np.arange(0.01, 0.10, 0.01)], x=np.linspace(0, 1, 9))
    res.append((ep, name, float(np.linalg.norm(np.array(bb[name]["max"]) - bb[name]["min"]) / 2), add.mean() * 100, auc))
    print(ep, name, f"half-diag {res[-1][2]:.2f} m  ADD mean {res[-1][3]:.1f} cm  AUC {auc:.3f}")
print("MEAN AUC (box proxy)", round(float(np.mean([r[4] for r in res])), 4), " mean ADD cm", round(float(np.mean([r[3] for r in res])), 2))
