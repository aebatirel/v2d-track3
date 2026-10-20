"""Stage C: for discrepant fits, compare silhouette IoU with the heading FIXED at the room-transfer prediction vs the
free s25 fit (same GrabCut mask as s25 round 2). usage: python s28_fixedpsi.py <variant> ep:psi_pred [ep:psi_pred ...]"""
import sys, json, numpy as np, cv2, trimesh
VAR = sys.argv[1]; ARGS = sys.argv[2:]; sys.argv = [sys.argv[0], VAR]
import s24_campose as S, c11, s25_refine as R
from s23_mask import masks
fits = json.load(open(f"s25_refine_{VAR}.json")); out = {}
for a in ARGS:
    ep, pp = a.split(":"); pp = float(pp); f = fits[ep]
    e = c11.load_episode(int(ep)); img0 = cv2.imread(f"cfr/pub{ep}_f0.png")
    P = np.vstack([trimesh.sample.sample_surface(c11.glb_mesh(n), 15000, seed=0)[0] @ c11.R_of(e["pose"][0, j, 3:]).T
                   + e["pose"][0, j, :3] for j, n in enumerate(e["names"])])
    img, fg0, dc = masks(img0, R.SC); x = np.array([f["psi"], f["th"], f["ph"]] + f["C"])
    fg = R.gc_fg(img, S.render(P, x, R.SC, fg0.shape), fg0)
    free = R.iou(P, x, fg)
    fixed = max((R.nm(P, x + d, fg, fix_psi=pp) for d in (np.zeros(6), np.r_[0, 2, 0, 0, 0.02, 0], np.r_[0, -2, 0, 0, -0.02, 0])), key=lambda t: t[1])
    free2 = R.nm(P, fixed[0], fg)  # free re-fit started from the room-heading solution
    out[ep] = dict(psi_fit=f["psi"], iou_fit=float(free), psi_room=pp, iou_room_fixed=float(fixed[1]), psi_free_from_room=float(free2[0][0]), iou_free_from_room=float(free2[1]))
    print(ep, {k: round(v, 4) for k, v in out[ep].items()}, flush=True)
json.dump(out, open(f"s28_fixedpsi_{VAR}.json", "w"), indent=1)
