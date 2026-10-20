"""DIG 18 B7: overlay static GT objects (from a b2 validate json track) on chosen cam_a frames -> montage jpg.
usage: python b7_overlay.py <validate json> <track> <frames csv> <out jpg>"""
import sys, os, json, numpy as np, cv2, trimesh
sys.path.insert(0, "/Users/aebatirel/Documents/Code/v2d-research/work/11")
import c11
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from a1_extract import NEW, newK, maps, clip
V = json.load(open(sys.argv[1])); TR = sys.argv[2]; FRS = [int(x) for x in sys.argv[3].split(",")]
w, h, f = NEW["a"]; K = newK("a"); EP = V["ep"]
e = c11.load_episode(EP); FR = list(e["frame"]); names = e["names"]; onset = V["onset"]
PTS = {n: trimesh.sample.sample_surface(c11.glb_mesh(n), 15000, seed=0)[0][::3] for n in names}
R = {r["frame"]: r for r in V["rows"] if r["track"] == TR}
(m1, m2), _ = maps("a"); cap = cv2.VideoCapture(clip("public", EP, "a")); out = []; t = 0
while True:
    ok, fr = cap.read()
    if not ok or t > max(FRS): break
    if t in FRS and t in R:
        u = cv2.remap(fr, m1, m2, cv2.INTER_AREA); r = R[t]; Rwc = np.array(r["Rwc"]); C = np.array(r["C"]); i = FR.index(t)
        for j, n in enumerate(names):
            X = PTS[n] @ c11.R_of(e["pose"][i, j, 3:]).T + e["pose"][i, j, :3]; Xc = (X - C) @ Rwc; v = Xc[:, 2] > 0.05
            uv = np.round(Xc[v, :2] / Xc[v, 2:3] * f + K[:2, 2]).astype(int); k = (uv[:, 0] >= 0) & (uv[:, 0] < w) & (uv[:, 1] >= 0) & (uv[:, 1] < h)
            m = np.zeros((h, w), np.uint8); m[uv[k, 1], uv[k, 0]] = 255
            m = cv2.morphologyEx(cv2.dilate(m, np.ones((3, 3), np.uint8)), cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
            cn, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            cv2.drawContours(u, cn, -1, (0, 0, 255) if t < onset[j] - 3 else (0, 255, 255), 1)
        cv2.putText(u, f"ep{EP} f{t} {TR} res {r['shift_cm']:.2f}cm", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        out.append(cv2.resize(u, (w // 2, h // 2)))
    t += 1
while len(out) % 3: out.append(np.zeros_like(out[0]))
rows = [np.hstack(out[i:i + 3]) for i in range(0, len(out), 3)]
cv2.imwrite(sys.argv[4], np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 85]); print("wrote", sys.argv[4], len(out))
