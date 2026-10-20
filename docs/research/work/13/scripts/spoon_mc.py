"""Monte Carlo over spoon shape / marker uncertainty -> distribution of exact skews and rule predictions."""
import sys, json; sys.path.insert(0, "/Users/aebatirel/Documents/Code/v2d-research/work/13/scripts")
import numpy as np
from spoon_model import spoon_with_markers, frame_and_skews
rng = np.random.default_rng(int(sys.argv[2]) if len(sys.argv) > 2 else 0)
N = int(sys.argv[1]) if len(sys.argv) > 1 else 200
rows = []
for i in range(N):
    Lb = rng.uniform(0.08, 0.105)
    body = dict(L=rng.uniform(0.29, 0.37), Lb=Lb, wb=rng.uniform(0.026, 0.035), wn=rng.uniform(0.007, 0.010),
                we=rng.uniform(0.010, 0.014), tb=rng.uniform(0.0035, 0.006), th=rng.uniform(0.007, 0.013),
                Db=rng.uniform(0.004, 0.012), asym_y=rng.uniform(-0.03, 0.03), handle_off_x=rng.uniform(-0.004, 0.004),
                ns=360, nphi=56)
    m1 = Lb + rng.uniform(-0.005, 0.02)
    p = dict(body=body, m1_z=m1, m2_z=m1 + rng.uniform(0.03, 0.07), marker_x=rng.uniform(-0.004, 0.004),
             m1_dx=rng.uniform(-0.002, 0.002), m2_dx=rng.uniform(-0.002, 0.002),
             m1_extra=rng.uniform(-0.002, 0.002), m2_extra=rng.uniform(-0.002, 0.002),
             keep_frac=rng.uniform(0.35, 0.95), bases=bool(rng.random() < 0.8), base_h=rng.uniform(0.002, 0.006),
             r_marker=rng.uniform(0.0065, 0.0076), m3=bool(rng.random() < 0.95))
    V, F = spoon_with_markers(p)
    c, w, E, sk, A = frame_and_skews(V, F)
    rows.append(dict(sx=sk[0], sy=sk[1], sz=sk[2], area=A, lam_yx=w[1]/w[0], lam_zy=w[2]/w[1],
                     dz=p["m2_z"] - p["m1_z"], ex=p["m1_extra"] - p["m2_extra"], th=body["th"], Db=body["Db"], mx=p["marker_x"],
                     asym=body["asym_y"]))
json.dump(rows, open(f"/Users/aebatirel/Documents/Code/v2d-research/work/13/out/spoon_mc_{sys.argv[2] if len(sys.argv)>2 else 0}.json", "w"))
sx = np.array([r["sx"] for r in rows]); sy = np.array([r["sy"] for r in rows]); sz = np.array([r["sz"] for r in rows])
print(f"N={N}  skew_z>0: {np.mean(sz>0):.3f} (min {sz.min():.3f})   skew_y(+toward M1) mean {sy.mean():+.4f} sd {sy.std():.4f}  P(sy<0)={np.mean(sy<0):.3f}  P(sy<-0.02)={np.mean(sy<-0.02):.3f}")
print(f"skew_x(+toward convex) mean {sx.mean():+.4f} sd {sx.std():.4f} P(sx>0)={np.mean(sx>0):.3f}")
