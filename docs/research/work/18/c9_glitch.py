"""DIG 18 C9: GT-free temporal consistency gate for map keyframes. For keyframe t with map neighbours t-s and t+s,
predict the c pose at t from each neighbour with VO v2 relative motion; a glitch = the map pose at t disagrees with
BOTH predictions while the two predictions agree. Reads no GT.
usage: python c9_glitch.py <prefix e.g. s5> <thr_mm> [eps...]"""
import json, sys, numpy as np
from scipy.spatial.transform import Rotation as Rot
P, THR = sys.argv[1], float(sys.argv[2])
EV = [int(x) for x in sys.argv[3:]] or [1, 3, 5, 6, 8, 10, 14, 15, 16, 19, 20, 25, 28, 30, 32, 33, 35, 36, 37, 38]
def T44(m): x = np.eye(4); x[:3] = np.array(m); return x
def cen(T): return -T[:3, :3].T @ T[:3, 3]
def rdeg(A, B): return np.degrees(np.linalg.norm(Rot.from_matrix(A[:3, :3] @ B[:3, :3].T).as_rotvec()))
allm, flags, n = [], [], 0
for e in EV:
    K = {r["frame"]: r for r in json.load(open(f"c1/{P}_e{e}.json"))["frames"] if r.get("inl_bc", 0) >= 30}
    V = {r["frame"]: T44(r["c_from_c0"]) for r in json.load(open(f"c3/vo_e{e}.json"))["frames"] if "c_from_c0" in r}
    ts = sorted(K); s = ts[1] - ts[0] if len(ts) > 1 else 5
    for t in ts:
        if t - s not in K or t + s not in K or any(u not in V for u in (t - s, t, t + s)): continue
        M = T44(K[t]["c_from_world"]); preds = []
        for u in (t - s, t + s):
            rel = V[t] @ np.linalg.inv(V[u]); preds.append(rel @ T44(K[u]["c_from_world"]))
        dL, dR = (np.linalg.norm(cen(M) - cen(p)) * 1000 for p in preds); dLR = np.linalg.norm(cen(preds[0]) - cen(preds[1])) * 1000
        rL, rR = (rdeg(M, p) for p in preds)
        m = min(dL, dR); allm.append(m); n += 1
        if m > THR and dLR < 0.5 * m:
            flags.append((e, t, round(dL, 2), round(dR, 2), round(dLR, 2), round(min(rL, rR), 3), K[t]["inl_bc"]))
allm = np.array(allm)
print(f"{P}: keyframes tested {n}; min(dL,dR) median {np.median(allm):.2f} p90 {np.percentile(allm,90):.2f} p99 {np.percentile(allm,99):.2f} max {allm.max():.2f} mm")
print(f"glitches (min dist > {THR} mm and the two VO predictions agree to < half of it): {len(flags)} = {100*len(flags)/max(n,1):.2f} %")
for f in flags: print("  e%d t=%d dL %.2f dR %.2f dLR %.2f mm rot %.3f deg inl %d" % f)
