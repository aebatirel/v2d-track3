"""Effect of dropping the 20 eval frame-0 stereo planes from A8's gravity/height (run1 map)."""
import json, numpy as np, pycolmap
W = "/Users/aebatirel/Documents/Code/v2d-research/work/18"
rec = pycolmap.Reconstruction(f"{W}/run1/sparse/0"); A5 = json.load(open(f"{W}/a5_stereo_table.json"))
cams = {}
for im in rec.images.values():
    T = im.cam_from_world(); cams[im.name] = (T.rotation.matrix(), np.asarray(T.translation))
def est(pub_only):
    N, H = [], []
    for r in A5:
        if not r.get("ok") or r["ninl"] < 3000 or r["sig_deg"] > 1.0: continue
        if pub_only and r["name"].startswith("e"): continue
        R, t = cams["c/" + r["name"]]; n_c = np.array(r["n"]); N.append(R.T @ n_c); H.append(-(n_c @ t + r["d_table"]))
    N = np.array(N); up = N.mean(0); up /= np.linalg.norm(up); H = np.array(H) / (N @ up); return up, np.median(H), len(N)
u1, h1, n1 = est(False); u0, h0, n0 = est(True)
print("all", n1, "pub-only", n0, "up angle diff %.4f deg" % np.degrees(np.arccos(np.clip(u1 @ u0, -1, 1))), "height median diff %.2f mm" % (1000 * (h1 - h0)))
