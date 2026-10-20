"""DIG 18 B14: GT-free summary of relocalisation runs: coverage, inliers, time, blur-vs-inliers, head motion range
(cam_a in mocap via a13; pitch below horizon, heading excursion, path length). Reads no GT.
usage: python b14_reloc_summary.py <reloc json> [align json|-] ..."""
import sys, json, numpy as np
from scipy.stats import spearmanr
HERE = "/Users/aebatirel/Documents/Code/v2d-research/work/18"
REG = json.load(open(f"{HERE}/a13_registration_refined.json")); Rm = np.array(REG["R_mocap_from_map"])
args = sys.argv[1:]
for i in range(0, len(args), 2):
    RL = json.load(open(args[i])); AL = json.load(open(args[i + 1])) if args[i + 1] != "-" else None
    Ra = np.array(AL["Ra"]) if AL else np.eye(3); ta = np.array(AL["ta"]) if AL else np.zeros(3)
    F = RL["frames"]; n = len(F)
    ib = np.array([r.get("inl_bc", 0) for r in F]); ia = np.array([r.get("inl_a", 0) for r in F])
    tm = np.array([sum(v for v in r["time"].values()) for r in F]); bl = np.array([r.get("blur_c", np.nan) for r in F]); bla = np.array([r.get("blur_a", np.nan) for r in F])
    P, H, C = [], [], []
    for r in F:
        if r.get("inl_a", 0) < 30: continue
        T = np.array(r["a_from_world"]); R = T[:, :3] @ Ra.T; Cm = Ra @ (-T[:, :3].T @ T[:, 3]) + ta
        f = Rm @ R.T[:, 2]; P.append(np.degrees(np.arcsin(-f[2]))); H.append(np.degrees(np.arctan2(f[1], f[0]))); C.append(Rm @ Cm)
    P, H, C = np.array(P), np.unwrap(np.radians(H)), np.array(C); H = np.degrees(H - H[0])
    path = np.sum(np.linalg.norm(np.diff(C, axis=0), axis=1)) * 100
    print(f"{RL['tag']}: frames {n}; coverage rig {np.mean(ib >= 30):.3f} a {np.mean(ia >= 30):.3f}; rig inliers min/p5/med {ib.min()}/{int(np.percentile(ib, 5))}/{int(np.median(ib))};"
          f" a {ia.min()}/{int(np.percentile(ia, 5))}/{int(np.median(ia))}; time/frame med {np.median(tm):.2f} p90 {np.percentile(tm, 90):.2f} s;"
          f" spearman(blur_c, rig inl) {spearmanr(bl, ib)[0]:+.2f}, (blur_a, a inl) {spearmanr(bla, ia)[0]:+.2f};"
          f" pitch {P.min():.1f}-{P.max():.1f} deg; heading excursion {H.min():+.1f}..{H.max():+.1f} deg; cam_a path {path:.1f} cm, extent {np.ptp(C, 0).max() * 100:.1f} cm")
