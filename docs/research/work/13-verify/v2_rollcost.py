"""Verifier run 2 (C2): independent re-derivation of the per-episode cost of a 180 deg body-z (roll) frame error, using the KIT's
own warp/metric functions (imported, unmodified) on public GT motions. Slot-0 case: the slot-0 object of each public episode whose
slot-0 rotates > 30 deg from frame 0, scored ALONE (as eval 35-37). Slot-1 case: every 2+-object public episode, flip applied to
slot 1, scored with its slot-0 host (as eval 3,5,6,15,16,32,33). Perfect tracking otherwise. Reports MPPE (cm) and SP-SR per episode."""
import glob, json, importlib.util, numpy as np, pandas as pd
K = "/Users/aebatirel/Documents/Code/v2d-research/kit/v2d_submission_kit/metric_code/track_3/"
def load(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), K + name + ".py"); m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m); return m
MP = load("MPPE"); SP = load("SP-SR")
D = "/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public/data/chunk-000/"
QM = np.array([0.0, 0.0, 1.0, 0.0])  # xyzw, 180 deg about body z
def ang(a, b): return np.degrees(MP._quaternion_geodesic_angle(a, b))
res = {"slot0": [], "slot1": []}
for f in sorted(glob.glob(D + "episode_*.parquet")):
    ep = int(f[-14:-8]); df = pd.read_parquet(f, columns=["observation.objects"])
    objs = df["observation.objects"].tolist(); nb = len(objs[0])
    P = np.array([[o["pose"] for o in fr] for fr in objs], dtype=float)  # T, B, 7 (x y z qw qx qy qz)
    X = np.concatenate([P[..., :3], P[..., 4:7], P[..., 3:4]], -1)        # xyzw
    X[..., 3:] /= np.linalg.norm(X[..., 3:], axis=-1, keepdims=True)
    ref = X[:, None]                                                      # T, W=1, B, 7
    def score(ach, r):
        a = MP._warp_to_reference_start(ach, r)
        return MP._mean_per_point_error_cm(a, r), float(np.mean(SP._spider_success(a, r)))
    # slot 0 alone
    rot0 = ang(X[:, 0, 3:], np.repeat(X[:1, 0, 3:], len(X), 0)).max()
    if rot0 > 30:
        r = ref[:, :, :1]; a = r.copy(); a[..., 3:] = MP._quaternion_multiply(a[..., 3:], QM)
        res["slot0"].append((ep, round(rot0, 1)) + score(a, r) + score(r.copy(), r))
    if nb >= 2:
        r = ref[:, :, :2]; a = r.copy(); a[:, :, 1, 3:] = MP._quaternion_multiply(a[:, :, 1, 3:], QM)
        res["slot1"].append((ep, nb) + score(a, r) + score(r.copy(), r))
for k, v in res.items():
    print(k, "N", len(v))
    for row in v: print("  ", row)
    m = np.array([row[2:] for row in v], dtype=float)
    print(f"  mean flip MPPE {m[:,0].mean():.2f} cm, SP {m[:,1].mean():.3f}; perfect MPPE {m[:,2].mean():.2f}, SP {m[:,3].mean():.3f}")
