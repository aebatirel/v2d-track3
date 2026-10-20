"""Stage C: refine s24 camera fits (camera pose of public frame 0 in the mocap world) with a GrabCut object mask
seeded by the GT-silhouette rendering, 2 rounds; then a heading profile (psi fixed at offsets, other 5 dof re-fit).
Analysis only (public GT). usage: python s25_refine.py <native|flipped> ep [ep ...]"""
import sys, json, os, numpy as np, cv2, trimesh
VAR = sys.argv[1]; EPS = sys.argv[2:]; sys.argv = [sys.argv[0], VAR]
import s24_campose as S, c11
from s23_mask import masks
from scipy.optimize import minimize
SC = 0.5

def gc_fg(img, r, fg0):
    m = np.full(r.shape, cv2.GC_BGD, np.uint8)
    m[cv2.dilate(r, np.ones((41, 41), np.uint8)) > 0] = cv2.GC_PR_BGD
    m[r > 0] = cv2.GC_PR_FGD
    m[(cv2.erode(r, np.ones((15, 15), np.uint8)) > 0) & fg0] = cv2.GC_FGD
    bg, fgm = np.zeros((1, 65)), np.zeros((1, 65))
    cv2.grabCut(img, m, None, bg, fgm, 4, cv2.GC_INIT_WITH_MASK)
    return (m == cv2.GC_FGD) | (m == cv2.GC_PR_FGD)

def iou(P, x, fg):
    r = S.render(P, x, SC, fg.shape)
    if r.sum() < 20: return 0.0
    fo = S.OUTFRAC["f"]; extra = r.sum() * fo / max(1 - fo, 1e-3); rr = r > 0
    return (rr & fg).sum() / max((rr | fg).sum() + extra, 1)

def nm(P, x, fg, fix_psi=None, step=1.0):
    if fix_psi is None:
        f = lambda z: -iou(P, z, fg); st = np.array([2, 2, 2, 0.02, 0.02, 0.02]) * step
    else:
        f = lambda z: -iou(P, np.r_[fix_psi, z], fg); x = x[1:]; st = np.array([2, 2, 0.02, 0.02, 0.02]) * step
    sim = np.vstack([x] + [x + np.eye(len(x))[i] * st[i] for i in range(len(x))])
    o = minimize(f, x, method="Nelder-Mead", options=dict(initial_simplex=sim, xatol=1e-4, fatol=1e-6, maxiter=1200, maxfev=1200))
    return (o.x if fix_psi is None else np.r_[fix_psi, o.x]), -o.fun

if __name__ == "__main__":
    init = json.load(open(f"s24_campose_{VAR}.json")); fn = f"s25_refine_{VAR}.json"
    out = json.load(open(fn)) if os.path.exists(fn) else {}
    for ep in EPS:
        e = c11.load_episode(int(ep)); img0 = cv2.imread(f"cfr/pub{ep}_f0.png")
        P = np.vstack([trimesh.sample.sample_surface(c11.glb_mesh(n), 15000, seed=0)[0] @ c11.R_of(e["pose"][0, j, 3:]).T
                       + e["pose"][0, j, :3] for j, n in enumerate(e["names"])])
        img, fg0, dc = masks(img0, SC); r0 = init[ep]; x = np.array([r0["psi"], r0["th"], r0["ph"]] + r0["C"])
        for rnd in range(2):
            fg = gc_fg(img, S.render(P, x, SC, fg0.shape), fg0)
            cands = [nm(P, x + d, fg) for d in (np.zeros(6), np.r_[3, 0, 0, 0, 0.0, 0], np.r_[-3, 0, 0, 0, 0.0, 0])]
            x, sc = max(cands, key=lambda t: t[1])
        prof = {}
        for dpsi in (-4, -2, 2, 4):
            prof[dpsi] = float(nm(P, x, fg, fix_psi=x[0] + dpsi, step=0.5)[1])
        vis = img.copy(); m = S.render(P, x, SC, fg.shape) > 0; vis[m] = (0.5 * vis[m] + [0, 0, 127]).astype(np.uint8)
        cn, _ = cv2.findContours(fg.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE); cv2.drawContours(vis, cn, -1, (0, 255, 0), 1)
        cv2.putText(vis, f"{ep} psi {x[0]:.1f} iou {sc:.2f}", (10, 40), 0, 1.2, (0, 255, 255), 3); cv2.imwrite(f"cfr/ref_{VAR}_{ep}.png", vis)
        c = P.mean(0)
        out[ep] = dict(iou=float(sc), psi=float(x[0]), th=float(x[1]), ph=float(x[2]), C=x[3:].tolist(), C_rel_obj=(x[3:] - c).tolist(),
                       profile={str(k): v for k, v in prof.items()}, psi_s24=r0["psi"])
        json.dump(out, open(fn, "w"), indent=1)
        print(f"ep {ep:>2} IoU {sc:.3f} psi {x[0]:7.2f} (s24 {r0['psi']:7.2f}) th {x[1]:5.1f} ph {x[2]:5.1f} Crel {np.round(x[3:]-c,3)} "
              f"profile dIoU {[round(v - sc, 4) for v in prof.values()]}", flush=True)
