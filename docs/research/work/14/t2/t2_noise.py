"""Track 2: measure tier-2 injected noise vs tier-1 clean, and score a 'perfect tracker of noisy input'.
Uses the kit's Track 2 metric definitions (no frame-0 alignment for Track 2). AUC needs mesh vertices
(not downloaded) -> only SP-SR, MP-SR, MPPE are exact here; AUC proxy computed with MPPE keypoints."""
import glob, json, os, numpy as np, pandas as pd, pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as R
D = os.path.dirname(os.path.abspath(__file__))
dirs = np.array([[1,0,0],[-1,0,0],[0,1,0],[0,-1,0],[0,0,1],[0,0,-1]], float) * 0.05
rows = []
for f1 in sorted(glob.glob(f"{D}/tier1/episode_*.parquet")):
    ep = int(f1[-14:-8]); f2 = f"{D}/tier2/episode_{ep:06d}.parquet"
    a = pq.read_table(f1, columns=["observation.object.pose", "observation.object.visible", "observation.human.translation"]).to_pandas()
    b = pq.read_table(f2, columns=["observation.object.pose", "observation.object.visible", "observation.human.translation"]).to_pandas()
    meta = pq.read_schema(f1).metadata or {}
    obj = meta.get(b"objects", b"?").decode()[:40]
    P1 = np.stack(a["observation.object.pose"].values).astype(float); P2 = np.stack(b["observation.object.pose"].values).astype(float)
    v = a["observation.object.visible"].values.astype(bool) & b["observation.object.visible"].values.astype(bool)
    P1, P2 = P1[v], P2[v]
    q1 = R.from_quat(P1[:, [4,5,6,3]]); q2 = R.from_quat(P2[:, [4,5,6,3]])
    dp = np.linalg.norm(P2[:, :3] - P1[:, :3], axis=1)
    dr = (q1.inv() * q2).magnitude()
    k1 = P1[:, None, :3] + np.einsum("tij,kj->tki", q1.as_matrix(), dirs)
    k2 = P2[:, None, :3] + np.einsum("tij,kj->tki", q2.as_matrix(), dirs)
    kp = np.linalg.norm(k2 - k1, axis=-1).mean(-1)
    auc_proxy = np.trapezoid([np.mean(kp < t) for t in np.arange(0.01, 0.10, 0.01)], x=np.linspace(0, 1, 9))
    H1 = np.stack(a["observation.human.translation"].values).astype(float); H2 = np.stack(b["observation.human.translation"].values).astype(float)
    dh = np.linalg.norm(H2 - H1, axis=1)
    # noise character: lag-1 autocorrelation of position noise (random walk -> ~1, white -> ~0)
    e = P2[:, :3] - P1[:, :3]; e0 = e - e.mean(0)
    ac = float((e0[1:] * e0[:-1]).sum() / max((e0 * e0).sum(), 1e-12))
    rows.append(dict(ep=ep, obj=obj, n=int(v.sum()), nT=len(a), pos_mean_cm=dp.mean()*100, pos_p95_cm=np.percentile(dp, 95)*100,
                     pos_max_cm=dp.max()*100, rot_mean_deg=np.degrees(dr.mean()), rot_p95_deg=np.degrees(np.percentile(dr, 95)),
                     bias_cm=np.linalg.norm(e.mean(0))*100, ac1=ac, hum_mean_cm=dh.mean()*100,
                     sp_sr=float(dp.mean() <= 0.10 and dr.mean() <= 0.5), mp_sr=float(dp.mean() < 0.03 and np.degrees(dr.mean()) < 30),
                     mppe_cm=kp.mean()*100, auc_kp_proxy=auc_proxy))
df = pd.DataFrame(rows)
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
print(df.round(3).to_string(index=False))
print("MEAN", df.drop(columns=["obj"]).mean().round(4).to_dict())
print("MEDIAN", df.drop(columns=["obj"]).median().round(4).to_dict())
df.to_csv(f"{D}/t2_noise.csv", index=False)
