"""Stage B retry: reuse scripts-prev/meshframe/canon.py on the 10 public scans; check origin/axes vs published
frame (identity) and which xy_rule reproduces each published roll; compare skews with out/b_feats.json."""
import sys, os, json, numpy as np, trimesh
sys.path.insert(0, "/Users/aebatirel/Documents/Code/v2d-research/scripts-prev/meshframe")
import canon
MESH = "/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public/mesh"
NAMES = ["beige_cup", "blue_cup", "mini_dust_pan", "mini_sweeper", "plastic_dish_rack", "water_pitcher",
         "white_pot", "white_pot_lid", "wooden_piece_1", "wooden_piece_2"]
BF = json.load(open("/Users/aebatirel/Documents/Code/v2d-research/work/13/out/b_feats.json"))
tot = {}
for n in NAMES:
    d = f"{MESH}/{n}"; fn = f"{n}_visual.glb" if os.path.exists(f"{d}/{n}_visual.glb") else f"{n}.glb"
    m = trimesh.load(f"{d}/{fn}", force="mesh", process=False)
    V, F = np.asarray(m.vertices, float), np.asarray(m.faces)
    row = [n]
    for rule in ("skew_x", "skew_y", "hybrid"):
        R, c, w = canon.canonical_frame(V, F, rule)
        ok = np.allclose(np.diag(R), 1, atol=1e-6)
        tot[rule] = tot.get(rule, 0) + ok
        row.append(f"{rule}:{'OK' if ok else 'flip' if np.allclose(np.diag(R),[-1,-1,1],atol=1e-6) else 'other'}")
    sk = [canon.third_moment(V, F, c, np.eye(3)[i]) for i in range(3)]
    dsk = np.max(np.abs(np.array(sk) - np.array(BF[n]["skew"])))
    row.append(f"|c|={np.linalg.norm(c)*1e3:.4f}mm skew={np.round(sk,4)} max|d vs b_feats|={dsk:.1e}")
    print(" ".join(row), flush=True)
print("totals (published roll reproduced):", tot)
