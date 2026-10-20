"""Verifier: run2-relocalised cam_a poses (held-out map) vs run1 BA poses at map frames; with/without frame 0. Also b2 residual quantization."""
import json, numpy as np, pycolmap, glob
from scipy.spatial.transform import Rotation as Rot
W = "/Users/aebatirel/Documents/Code/v2d-research/work/18"
r1 = pycolmap.Reconstruction(f"{W}/run1/sparse/0"); r2 = pycolmap.Reconstruction(f"{W}/run2/sparse/0")
P1 = {}
for im in r1.images.values():
    T = im.cam_from_world(); R = T.rotation.matrix(); t = np.asarray(T.translation); P1[im.name] = (R.T, -R.T @ t)
n2 = set(im.name for im in r2.images.values())
A = json.load(open(f"{W}/b2_align_run2.json")); Ra = np.array(A["Ra"]); ta = np.array(A["ta"])
for ep in (26, 27, 31):
    F = {f["frame"]: f for f in json.load(open(f"{W}/b1/run2_p{ep}.json"))["frames"]}
    rows = []
    for nm, (Rw1, C1) in P1.items():
        if not nm.startswith(f"a/p{ep:02d}_"): continue
        fr = int(nm.split("_")[1][:4]); f = F.get(fr)
        if f is None or "a_from_world" not in f: continue
        m = np.array(f["a_from_world"]); R2 = m[:, :3].T; C2 = -m[:, :3].T @ m[:, 3]
        Rw = Ra @ R2; C = Ra @ C2 + ta
        rows.append((fr, nm in n2, 1000 * np.linalg.norm(C - C1), np.degrees(Rot.from_matrix(Rw @ Rw1.T).magnitude())))
    r = np.array([(x[2], x[3]) for x in rows]); rh = np.array([(x[2], x[3]) for x in rows if not x[1]])
    print(f"p{ep}: n={len(rows)} (in run2: {[x[0] for x in rows if x[1]]}) all med {np.median(r[:,0]):.2f} mm {np.median(r[:,1]):.3f} deg | held-out only n={len(rh)} med {np.median(rh[:,0]):.2f} mm {np.median(rh[:,1]):.3f} deg max {rh[:,0].max():.2f} mm")
for f in sorted(glob.glob(f"{W}/b2/*.json")):
    try: d = json.load(open(f))
    except Exception: continue
    rows = [r for r in d.get("rows", []) if r["track"] == "a"]
    if not rows: continue
    px = np.array([r["shift_px"] for r in rows]); cm = np.array([r["shift_cm"] for r in rows]); dep = np.array([r["depth"] for r in rows])
    vals, cnt = np.unique(np.round(px, 2), return_counts=True)
    print(f"{f.split('/')[-1]}: n={len(px)} shift_px median {np.median(px):.2f} | frac 0px {np.mean(px==0):.2f} 1px {np.mean(np.isclose(px,1)):.2f} sqrt2 {np.mean(np.isclose(px,2**.5)):.2f} | cm median {np.median(cm):.3f} | 1px at median depth = {np.median(dep)/500*100:.3f} cm")
