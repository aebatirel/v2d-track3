"""Verifier: map cam_a own-PnP track vs note 17 marker-registered cam_a cameras, one rigid transform per clip (own fit:
rotation = chordal mean of R17 Rmap^T, translation = mean centre difference). Also by thirds."""
import json, numpy as np
from scipy.spatial.transform import Rotation as Rot
W = "/Users/aebatirel/Documents/Code/v2d-research/work"
for ep, src in ((26, "run2"), (31, "run2"), (0, "run1lso"), (12, "run1lso"), (21, "run1lso")):
    N = json.load(open(f"{W}/17/out/reg2_{ep}.json")); cams = N["cams"]
    F = {f["frame"]: f for f in json.load(open(f"{W}/18/b1/{src}_p{ep}.json"))["frames"] if f.get("inl_a", 0) >= 30}
    fr = [t for t in range(len(cams)) if t in F]
    Rm = np.array([np.array(F[t]["a_from_world"])[:, :3].T for t in fr]); Cm = np.array([-np.array(F[t]["a_from_world"])[:, :3].T @ np.array(F[t]["a_from_world"])[:, 3] for t in fr])
    R7 = np.array([cams[t]["Rwc"] for t in fr]); C7 = np.array([cams[t]["C"] for t in fr])
    Rf = Rot.from_matrix(np.einsum("tij,tkj->tik", R7, Rm)).mean().as_matrix()
    tf = np.mean(C7 - Cm @ Rf.T, 0)
    dp = 1000 * np.linalg.norm(C7 - (Cm @ Rf.T + tf), axis=1)
    dr = np.degrees(Rot.from_matrix(np.einsum("tij,tkj->tik", R7, np.einsum("ij,tjk->tik", Rf, Rm))).magnitude())
    th = np.array_split(dp, 3)
    print(f"p{ep} ({src}) n={len(fr)}: pos median {np.median(dp):.2f} p90 {np.percentile(dp,90):.2f} max {dp.max():.1f} mm | rot median {np.median(dr):.3f} p90 {np.percentile(dr,90):.3f} deg | thirds {[round(float(np.median(x)),1) for x in th]}")
