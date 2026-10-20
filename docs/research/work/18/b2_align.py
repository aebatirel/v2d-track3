"""DIG 18 B2a: align a held-out map (run2) to run1 (which carries the mocap registration a13) using the images both
models share (all non-test images). Camera centres span only a few cm (one seat), so rotation is the chordal mean of
per-image R1^T R2 and translation is the mean of C1 - Ra C2; scale is checked by Sim3 on centres + per-point
distances (both maps are metric through the fixed b/c rig).
X_run1 = Ra X_run2 + ta.   usage: python b2_align.py run2/sparse/0 out.json"""
import sys, json, numpy as np
import pycolmap

r1 = pycolmap.Reconstruction("run1/sparse/0"); r2 = pycolmap.Reconstruction(sys.argv[1])


def poses(r):
    P = {}
    for im in r.images.values():
        T = im.cam_from_world(); R = T.rotation.matrix(); t = np.asarray(T.translation); P[im.name] = (R, -R.T @ t)
    return P


P1, P2 = poses(r1), poses(r2); common = sorted(set(P1) & set(P2))
M = sum(P1[n][0].T @ P2[n][0] for n in common); U, S, Vt = np.linalg.svd(M); Ra = U @ np.diag([1, 1, np.linalg.det(U @ Vt)]) @ Vt
C1 = np.array([P1[n][1] for n in common]); C2 = np.array([P2[n][1] for n in common])
ta = np.mean(C1 - C2 @ Ra.T, 0)
res = C1 - (C2 @ Ra.T + ta); rot = [np.degrees(np.arccos(np.clip((np.trace(P1[n][0].T @ P2[n][0] @ Ra.T) - 1) / 2, -1, 1))) for n in common]
# scale check: spread of centres about their mean
s = np.sqrt(((C1 - C1.mean(0)) ** 2).sum(1)).mean() / np.sqrt(((C2 - C2.mean(0)) ** 2).sum(1)).mean()
out = dict(Ra=Ra.tolist(), ta=ta.tolist(), n_common=len(common), n_run2=len(P2), centre_res_mm_median=float(np.median(np.linalg.norm(res, axis=1)) * 1000),
           centre_res_mm_p90=float(np.percentile(np.linalg.norm(res, axis=1), 90) * 1000), rot_res_deg_median=float(np.median(rot)),
           rot_res_deg_p90=float(np.percentile(rot, 90)), centre_spread_ratio=float(s), run2_summary=r2.summary())
json.dump(out, open(sys.argv[2], "w"), indent=1)
print({k: v for k, v in out.items() if k not in ("Ra", "ta")})
