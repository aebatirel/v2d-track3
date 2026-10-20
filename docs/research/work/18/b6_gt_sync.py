"""DIG 18 B6: which camera stream is mocap GT synchronous with? (public GT, analysis only)
For frames where the moving object moves fast, project its GT pose interpolated at t+delta into
  cam_a (pose: cam_a own PnP at t, offset from b2 'a')  and  cam_c (pose: rig c_from_world at t, offset from b2 'rigS'),
and measure the truncated chamfer of the projected contour to Canny edges at zero shift. The delta minimising the
mean chamfer is that camera's lag relative to GT (frame units, 50 ms).
usage: python b6_gt_sync.py <ep> <reloc json> <validate json>"""
import sys, os, json, numpy as np, cv2, trimesh
sys.path.insert(0, "/Users/aebatirel/Documents/Code/v2d-research/work/11")
import c11
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from a1_extract import NEW, newK, maps, clip
from scipy.spatial.transform import Rotation as Rot, Slerp

EP = int(sys.argv[1]); RL = json.load(open(sys.argv[2])); V = json.load(open(sys.argv[3]))
REG = json.load(open(f"{HERE}/a13_registration_refined.json")); Rm = np.array(REG["R_mocap_from_map"]); tz = REG["t_z"]
e = c11.load_episode(EP); FR = list(e["frame"]); names = e["names"]
P = e["pose"]; disp = np.array([np.nanmax(np.linalg.norm(P[:, j, :3] - P[0, j, :3], axis=1)) for j in range(len(names))])
j = int(np.argmax(disp)); name = names[j]
pts = trimesh.sample.sample_surface(c11.glb_mesh(name), 15000, seed=0)[0][::2]
pos = P[:, j, :3]; quat = P[:, j, 3:]; ok = np.isfinite(pos).all(1)
idx = np.array(FR)[ok]; sl = Slerp(idx, Rot.from_quat(quat[ok]))
speed = np.r_[0, np.linalg.norm(np.diff(pos, axis=0), axis=1) * 20]  # m/s


def gt_at(t):
    if t < idx[0] or t > idx[-1]: return None
    p = np.array([np.interp(t, idx, pos[ok][:, k]) for k in range(3)]); return pts @ sl(t).as_matrix().T + p


def mocap(T34):
    T = np.array(T34); R, t = T[:3, :3], T[:3, 3]; C = -R.T @ t; return Rm @ R.T, Rm @ C + np.array([0, 0, tz])


cams = {"a": dict(key="a_from_world", ok="inl_a", off=np.array(V["offsets"]["a"])),
        "c": dict(key="c_from_world", ok="inl_bc", off=np.array(V["offsets"]["rigS"]))}
sel = [t for t in range(3, len(FR) - 3) if speed[t] > 0.15 and np.isfinite(pos[t]).all()]
rows = {r["frame"]: r for r in RL["frames"]}
deltas = np.arange(-3.0, 3.01, 0.25)
res = {}
for cam, cd in cams.items():
    w, h, f = NEW[cam]; K = newK(cam); (m1, m2), _ = maps(cam); cap = cv2.VideoCapture(clip("public", EP, cam)); DT = {}
    t = 0
    while True:
        okk, fr = cap.read()
        if not okk: break
        if t in sel:
            g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY); u = cv2.remap(g, m1, m2, cv2.INTER_AREA if cam == "a" else cv2.INTER_LINEAR)
            DT[t] = cv2.distanceTransform(255 - cv2.Canny(cv2.GaussianBlur(u, (5, 5), 0), 30, 90), cv2.DIST_L2, 3)
        t += 1
    C = np.zeros(len(deltas)); n = 0
    per = []
    for t in sel:
        r = rows.get(t)
        if r is None or r.get(cd["ok"], 0) < 30: continue
        Rwc, Cw = mocap(r[cd["key"]]); Cw = Cw + cd["off"]; cs = []
        for d in deltas:
            X = gt_at(t + d)
            if X is None: cs.append(np.nan); continue
            Xc = (X - Cw) @ Rwc; v = Xc[:, 2] > 0.05; uv = Xc[v, :2] / Xc[v, 2:3] * f + K[:2, 2]
            m = np.zeros((h, w), np.uint8); u = np.round(uv).astype(int); k = (u[:, 0] >= 0) & (u[:, 0] < w) & (u[:, 1] >= 0) & (u[:, 1] < h)
            if k.sum() < 50: cs.append(np.nan); continue
            m[u[k, 1], u[k, 0]] = 255; m = cv2.morphologyEx(cv2.dilate(m, np.ones((3, 3), np.uint8)), cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
            cn, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE); cp = np.vstack([c.reshape(-1, 2) for c in cn])
            cs.append(float(np.mean(np.minimum(DT[t][cp[:, 1], cp[:, 0]], 15))))
        cs = np.array(cs)
        if np.isfinite(cs).all(): per.append(cs)
    per = np.array(per); mc = per.mean(0); b = int(np.argmin(mc))
    # parabola refinement + bootstrap over frames
    def best_of(M):
        m_ = M.mean(0); i = int(np.clip(np.argmin(m_), 1, len(deltas) - 2)); y0, y1, y2 = m_[i - 1:i + 2]
        den = y0 - 2 * y1 + y2; return deltas[i] + (0.25 * 0.5 * (y0 - y2) / den if den > 0 else 0)
    rng = np.random.default_rng(0); bs = [best_of(per[rng.integers(0, len(per), len(per))]) for _ in range(300)]
    res[cam] = dict(n=len(per), best=float(best_of(per)), boot_p5_p95=np.percentile(bs, [5, 95]).tolist(), curve=dict(zip(deltas.round(2).tolist(), mc.round(3).tolist())))
    print(f"ep {EP} {name} cam_{cam}: n={len(per)} fast frames; best GT delta {res[cam]['best']:+.2f} frames "
          f"(boot p5-p95 {np.round(res[cam]['boot_p5_p95'], 2)}); chamfer at -1/0/+1: {mc[deltas.tolist().index(-1.0)]:.2f}/{mc[deltas.tolist().index(0.0)]:.2f}/{mc[deltas.tolist().index(1.0)]:.2f}", flush=True)
json.dump(res, open(f"{HERE}/b6/gt_sync_p{EP}.json", "w"), indent=1)
