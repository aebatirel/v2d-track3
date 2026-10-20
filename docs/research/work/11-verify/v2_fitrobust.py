"""Verifier for dig-11 C1/C2: robustness of the s25 GT-silhouette heading fits to initialisation and point sampling.
Re-runs the s25 pipeline (GrabCut seeded by the rendering, 2 rounds of free 6-DoF Nelder-Mead) from a start whose
heading is offset by DPSI (other 5 DoF re-fit at that heading first), with point-sample seed SEED; then a dense heading
profile (psi fixed on a grid, 5 DoF re-fit from 2 starts) on the final mask. Public GT only (analysis).
usage: python v2_fitrobust.py <native|flipped> <ep> <dpsi> <seed>"""
import sys, os, json, numpy as np, cv2, trimesh
VAR, EP, DPSI, SEED = sys.argv[1], sys.argv[2], float(sys.argv[3]), int(sys.argv[4])
W11 = "/Users/aebatirel/Documents/Code/v2d-research/work/11"; sys.path.insert(0, W11)
sys.argv = [sys.argv[0], VAR]
import s24_campose as S, c11, s25_refine as R
from s23_mask import masks
fits = json.load(open(f"{W11}/s25_refine_{VAR}.json")); f = fits[EP]
e = c11.load_episode(int(EP)); img0 = cv2.imread(f"{W11}/cfr/pub{EP}_f0.png")
P = np.vstack([trimesh.sample.sample_surface(c11.glb_mesh(n), 15000, seed=SEED)[0] @ c11.R_of(e["pose"][0, j, 3:]).T
               + e["pose"][0, j, :3] for j, n in enumerate(e["names"])])
img, fg0, dc = masks(img0, R.SC)
x = np.array([f["psi"], f["th"], f["ph"]] + f["C"])
if DPSI != 0:  # wrong-heading start: re-fit the other 5 DoF at the offset heading on the colour mask
    x, _ = R.nm(P, x, fg0, fix_psi=x[0] + DPSI)
x_start = x.copy()
for rnd in range(2):
    fg = R.gc_fg(img, S.render(P, x, R.SC, fg0.shape), fg0)
    cands = [R.nm(P, x + d, fg) for d in (np.zeros(6), np.r_[3, 0, 0, 0, 0.0, 0], np.r_[-3, 0, 0, 0, 0.0, 0])]
    x, sc = max(cands, key=lambda t: t[1])
prof = {}
for d in np.arange(-6, 6.1, 1.0):
    prof[float(round(x[0] + d, 2))] = float(max(R.nm(P, x + s, fg, fix_psi=x[0] + d, step=0.5)[1]
                                           for s in (np.zeros(6), np.r_[0, 0, 0, 0, 0.02 * np.sign(d), 0]) ))
best_psi = max(prof, key=prof.get)
out = dict(var=VAR, ep=int(EP), dpsi=DPSI, seed=SEED, psi_start=float(x_start[0]), psi_fit=float(x[0]), iou_fit=float(sc),
           s25_psi=f["psi"], profile=prof, profile_argmax=best_psi, profile_max=prof[best_psi])
os.makedirs("v2_out", exist_ok=True)
json.dump(out, open(f"v2_out/{VAR}_{EP}_{DPSI:+.0f}_{SEED}.json", "w"), indent=1)
print(VAR, EP, DPSI, SEED, "fit psi", round(x[0], 2), "iou", round(sc, 4), "s25", round(f["psi"], 2),
      "profile argmax", best_psi, round(prof[best_psi], 4), flush=True)
