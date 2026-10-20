"""DIG 18 A12: cross-check of the A11 yaw correction with note 11's own IoU/GrabCut silhouette machinery on the
reference frame-0s (raw cam_a frame, K as given). Pitch/roll are fixed to the map's gravity-correct values (A8);
heading = A8 heading + d (d on a grid); camera centre re-fitted (3-DoF Nelder-Mead) to maximise IoU against a
GrabCut mask seeded by the s25 fit rendering (as in s25). usage: python a12_iou_check.py <eps csv>"""
import sys, os, json, numpy as np, cv2, trimesh
W11 = "/Users/aebatirel/Documents/Code/v2d-research/work/11"; HERE = os.path.dirname(os.path.abspath(__file__))
EPS = sys.argv[1].split(","); sys.argv = [sys.argv[0], "native"]; sys.path.insert(0, W11); os.chdir(W11)
import s24_campose as S, c11
from s23_mask import masks
from scipy.optimize import minimize
SC = 0.5
REG = json.load(open(f"{HERE}/a8_registration.json")); FITS = json.load(open(f"{W11}/s25_refine_native.json"))


def gc_fg(img, r, fg0):
    m = np.full(r.shape, cv2.GC_BGD, np.uint8); m[cv2.dilate(r, np.ones((41, 41), np.uint8)) > 0] = cv2.GC_PR_BGD
    m[r > 0] = cv2.GC_PR_FGD; m[(cv2.erode(r, np.ones((15, 15), np.uint8)) > 0) & fg0] = cv2.GC_FGD
    bg, fgm = np.zeros((1, 65)), np.zeros((1, 65)); cv2.grabCut(img, m, None, bg, fgm, 4, cv2.GC_INIT_WITH_MASK)
    return (m == cv2.GC_FGD) | (m == cv2.GC_PR_FGD)


def iou(P, x, fg):
    r = S.render(P, x, SC, fg.shape)
    if r.sum() < 20: return 0.0
    fo = S.OUTFRAC["f"]; extra = r.sum() * fo / max(1 - fo, 1e-3); rr = r > 0
    return (rr & fg).sum() / max((rr | fg).sum() + extra, 1)


out = {}
for ep in EPS:
    e = c11.load_episode(int(ep)); img0 = cv2.imread(f"{W11}/cfr/pub{ep}_f0.png")
    P = np.vstack([trimesh.sample.sample_surface(c11.glb_mesh(n), 15000, seed=0)[0] @ c11.R_of(e["pose"][0, j, 3:]).T + e["pose"][0, j, :3]
                   for j, n in enumerate(e["names"])])
    img, fg0, dc = masks(img0, SC); fz = FITS[ep]; xs25 = np.array([fz["psi"], fz["th"], fz["ph"]] + fz["C"])
    fg = gc_fg(img, S.render(P, xs25, SC, fg0.shape), fg0)
    mp = REG["poses"][f"a/p{int(ep):02d}_0000.jpg"]
    prof = []
    for d in np.arange(-2.0, 5.01, 1.0):
        ang = np.array([mp["psi"] + d, mp["th"], mp["ph"]]); C0 = np.array(fz["C"])
        best = None
        for dc_ in (np.zeros(3), np.r_[0, 0.01, 0], np.r_[0, -0.01, 0]):
            c0 = C0 + dc_
            r_ = minimize(lambda c: -iou(P, np.r_[ang, c], fg), c0, method="Nelder-Mead",
                          options=dict(initial_simplex=np.vstack([c0] + [c0 + np.eye(3)[k] * 0.01 for k in range(3)]), xatol=2e-4, fatol=1e-6, maxiter=400))
            if best is None or r_.fun < best.fun: best = r_
        prof.append((float(d), float(-best.fun)))
    c = np.array([p[1] for p in prof]); k = int(np.argmax(c)); lo, hi = max(0, k - 2), min(len(c), k + 3)
    pf = np.polyfit([p[0] for p in prof][lo:hi], c[lo:hi], 2); yb = float(-pf[1] / (2 * pf[0])) if pf[0] < 0 else prof[k][0]
    out[ep] = dict(profile=prof, best=yb, s25_iou=float(fz["iou"]), map_psi=mp["psi"], fit_psi=fz["psi"])
    print(f"ep {ep:>2}: s25 IoU {fz['iou']:.3f} (psi {fz['psi']:.2f}); map-gravity profile IoU vs d(psi): "
          + " ".join(f"{p[0]:+.0f}:{p[1]:.4f}" for p in prof) + f" | best d {yb:+.2f} (abs psi {mp['psi'] + yb:.2f})", flush=True)
json.dump(out, open(f"{HERE}/a12_iou_check.json", "w"), indent=1)
