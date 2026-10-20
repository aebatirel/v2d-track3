"""Verifier (C5): kit CD-O (_object_chamfer_cm, no decimation) and origin shift for the bowl-underside-missing spoon."""
import sys, importlib.util, json, numpy as np
args = sys.argv[1:]; sys.argv = sys.argv[:1] + ["0", "0"]
import v_spoon_asym as M
spec = importlib.util.spec_from_file_location("cdo", "/Users/aebatirel/Documents/Code/v2d-research/kit/v2d_submission_kit/metric_code/track_3/CD-O.py")
cdo = importlib.util.module_from_spec(spec); spec.loader.exec_module(cdo)
M.rng = np.random.default_rng(int(args[1]))
def centroid(V, F):
    T = V[F]; a = 0.5 * np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1); return (a[:, None] * T.mean(1)).sum(0) / a.sum()
for i in range(int(args[0])):
    p = M.draw(); V, F = M.build(p); Lb = p["body"]["Lb"]
    T = V[F]; n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-30; cen = T.mean(1)
    body = (cen[:, 2] > Lb + 0.03) & (cen[:, 2] < p["body"]["L"] - 0.02) & (np.abs(cen[:, 1]) < 0.015)
    n *= np.sign(np.mean(np.sum(n[body][:, :2] * (cen[body][:, :2] - np.median(cen[body][:, :2], 0)), 1)))
    Fp = F[~((n[:, 0] > 0.3) & (cen[:, 2] < Lb))]
    fl = cdo._object_chamfer_cm((V, F), (V, F), seed=1000 + i)   # same mesh, different alignment/metric samples? (same seed) -> sampling floor proxy
    fl2 = cdo._object_chamfer_cm((V, F), (V.copy(), F.copy()), seed=2000 + i)
    cp = cdo._object_chamfer_cm((V, F), (V, Fp), seed=3000 + i)
    dc = 1000 * np.linalg.norm(centroid(V, Fp) - centroid(V, F))
    print(json.dumps(dict(i=i, floor_same=round(fl, 4), floor2=round(fl2, 4), cdo_partial=round(cp, 4), origin_shift_mm=round(dc, 1))), flush=True)
