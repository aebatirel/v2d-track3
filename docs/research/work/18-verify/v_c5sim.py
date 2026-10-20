"""Verifier: independent re-derivation of part of C5 (iso context): own drift profiles from c1/s5 + c3 VO, frame-0 cam_a from
note 11's GT-fitted s25_refine_native cameras (independent of A8/A9), own vertex sampling; kit AUC functions.
Compares per-(public ep, eval profile) VO / VOx3 / VOd3 gains with c5_auc.json."""
import json, importlib.util, numpy as np, pandas as pd, trimesh, os
from scipy.spatial.transform import Rotation as Rot
ROOT = "/Users/aebatirel/Documents/Code/v2d-research"; W = f"{ROOT}/work/18"
sp = importlib.util.spec_from_file_location("aucm", f"{ROOT}/kit/v2d_submission_kit/metric_code/track_3/AUC.py")
M = importlib.util.module_from_spec(sp); sp.loader.exec_module(M)
EV = [1, 3, 5, 6, 8, 10, 14, 15, 16, 19, 20, 25, 28, 30, 32, 33, 35, 36, 37, 38]
S25 = json.load(open(f"{ROOT}/work/11/s25_refine_native.json"))
def Rwc(psi, th, ph):  # note 11 convention (columns right, down, forward)
    p, t = np.radians(psi), np.radians(th); f = np.array([np.cos(t) * np.cos(p), np.cos(t) * np.sin(p), -np.sin(t)])
    r = np.cross(f, [0, 0, 1.0]); r /= np.linalg.norm(r); d = np.cross(f, r)
    Rr = Rot.from_rotvec(f * np.radians(ph)).as_matrix(); return np.column_stack([Rr @ r, Rr @ d, f])
def H(m): x = np.eye(4); x[:3] = np.array(m); return x
prof = {}; maxdrift = {}
for e in EV:
    Tc = {r["frame"]: H(r["c_from_world"]) for r in json.load(open(f"{W}/c1/s5_e{e}.json"))["frames"] if r.get("inl_bc", 0) >= 30}
    Tv = {r["frame"]: H(r["c_from_c0"]) for r in json.load(open(f"{W}/c3/vo_e{e}.json"))["frames"]}
    Tv.setdefault(0, np.eye(4))
    ks = [k for k in sorted(Tc) if k in Tv]; Wm0 = np.linalg.inv(Tc[ks[0]])
    rv, tr = [], []
    for k in ks:
        Wm = np.linalg.inv(Tc[k]); Wv = Wm0 @ np.linalg.inv(Tv[ks[0]]) @ np.linalg.inv(np.linalg.inv(Tv[ks[0]])) @ np.linalg.inv(Tv[k]) if False else Wm0 @ Tv[ks[0]] @ np.linalg.inv(Tv[k])
        D = np.linalg.inv(Wm) @ Wv  # camera-frame error: W_vo = W_map D
        rv.append(Rot.from_matrix(D[:3, :3]).as_rotvec()); tr.append(D[:3, 3])
    rv, tr = np.array(rv), np.array(tr); n = ks[-1] + 1; tt = np.arange(n)
    prof[e] = (np.stack([np.interp(tt, ks, rv[:, i]) for i in range(3)], 1), np.stack([np.interp(tt, ks, tr[:, i]) for i in range(3)], 1))
    maxdrift[e] = (1000 * np.linalg.norm(tr, axis=1).max(), np.degrees(np.linalg.norm(rv, axis=1).max()))
print("max VO-vs-map drift (mm, deg):", {e: (round(a, 1), round(b, 2)) for e, (a, b) in maxdrift.items()})
rng = np.random.default_rng(7); VC = {}
def verts(name):
    if name not in VC:
        f = f"{ROOT}/data/track_3/public/mesh/{name}/{name}.glb"
        f = f if os.path.exists(f) else f"{ROOT}/data/track_3/public/mesh/{name}/{name}_visual.glb"
        v = np.asarray(trimesh.load(f, force="mesh").vertices, float); VC[name] = v[rng.choice(len(v), min(800, len(v)), replace=False)]
    return VC[name]
c5 = pd.read_json(f"{W}/c5_auc.json"); c5 = c5[c5.ctx == "iso"].groupby(["ep", "prof", "arm"]).auc.mean()
out = []
for ep in [12, 13, 21, 22, 26, 0]:
    df = pd.read_parquet(f"{ROOT}/data/track_3/public/data/chunk-000/episode_{ep:06d}.parquet", columns=["frame_index", "observation.objects"]).sort_values("frame_index")
    objs = df["observation.objects"].to_list(); names = [o["name"] for o in objs[0]]
    P = np.array([[o["pose"] for o in row] for row in objs], float); T = len(P)
    X = np.concatenate([P[..., :3], P[..., 4:7], P[..., 3:4]], -1); V = np.stack([verts(n) for n in names])
    s = S25[str(ep)]; C0 = np.eye(4); C0[:3, :3] = Rwc(s["psi"], s["th"], s["ph"]); C0[:3, 3] = s["C"]
    for e, (rv, tr) in prof.items():
        if len(rv) < T: continue
        for nm, k in (("VOd3", 1 / 3), ("VO", 1.0), ("VOx3", 3.0)):
            D = np.tile(np.eye(4), (T, 1, 1)); D[:, :3, :3] = Rot.from_rotvec(k * rv[:T]).as_matrix(); D[:, :3, 3] = k * tr[:T]
            E = C0 @ D @ np.linalg.inv(C0)
            Y = X.copy(); Y[..., :3] = np.einsum("tij,tbj->tbi", E[:, :3, :3], X[..., :3]) + E[:, None, :3, 3]
            for b in range(X.shape[1]): Y[:, b, 3:] = (Rot.from_matrix(E[:, :3, :3]) * Rot.from_quat(X[:, b, 3:])).as_quat()
            a = M._warp_to_reference_start(Y[:, None], X[:, None]); auc = M._add_auc(M._object_add(a, X[:, None], V))
            out.append(dict(ep=ep, prof=e, arm=nm, gain=1 - auc, c5_gain=c5.get((ep, e, "map"), np.nan) - c5.get((ep, e, nm), np.nan)))
o = pd.DataFrame(out); o.to_json("v_c5sim.json", orient="records")
for nm in ("VOd3", "VO", "VOx3"):
    s = o[o.arm == nm]; print(f"{nm}: n {len(s)} my gain mean {s.gain.mean():+.4f} c5 gain mean {s.c5_gain.mean():+.4f} | |diff| median {np.median(np.abs(s.gain - s.c5_gain)):.4f} max {np.max(np.abs(s.gain - s.c5_gain)):.4f}")
s = o[o.arm == "VO"].groupby("prof")[["gain", "c5_gain"]].mean(); print(s.round(3).T.to_string())
