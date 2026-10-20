"""DIG 18 C5: AUC value of drift-free camera poses, with the OFFICIAL scorer functions (kit AUC.py) on public GT.
Camera-pose error profiles Delta(t) (camera-frame error, Delta(0)=I) measured on the 20 EVAL clips (VO vs map
relocalisation, c1 + c3 outputs; no GT involved in measuring them) are applied to PUBLIC GT object trajectories:
  X_est(t) = E(t) X_gt(t),  E(t) = T_wc0 Delta(t) T_wc0^-1  (T_wc0 = that public episode's frame-0 map camera, a8 + a9 offset)
Arms: map (iid noise sd 0.015 deg/axis, 0.7 mm/axis), VO (measured), VOx3 (scaled), lin5 (note-02 linear 5 cm common drift).
Contexts: iso (objects otherwise perfect) and stackA (note-02 'careful stereo' errors without drift).
usage: python c5_auc.py <prefix s5> <out json>"""
import sys, os, json, importlib.util, numpy as np, pandas as pd, trimesh
from scipy.spatial.transform import Rotation as Rot

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = "/Users/aebatirel/Documents/Code/v2d-research"
sp = importlib.util.spec_from_file_location("aucm", f"{ROOT}/kit/v2d_submission_kit/metric_code/track_3/AUC.py")
M = importlib.util.module_from_spec(sp); sp.loader.exec_module(M)
PFX, OUT = sys.argv[1], sys.argv[2]
EV = [1, 3, 5, 6, 8, 10, 14, 15, 16, 19, 20, 25, 28, 30, 32, 33, 35, 36, 37, 38]
PUB = [0, 2, 11, 12, 13, 18, 21, 22, 23, 24, 26, 27, 31, 39, 40, 41, 42, 43, 44]
A8 = json.load(open(f"{HERE}/a8_registration.json")); A9 = json.load(open(f"{HERE}/a9_overlay_check.json"))["episodes"]
Rm = np.array(A8["R_mocap_from_map"])


def T44(m):
    x = np.eye(4); x[:3] = np.array(m); return x


def inv(T):
    x = np.eye(4); x[:3, :3] = T[:3, :3].T; x[:3, 3] = -T[:3, :3].T @ T[:3, 3]; return x


# ---- camera-frame error profiles Delta(t) from eval clips (keyframes, linear interp in rotvec/translation) ----
prof = {}
for e in EV:
    fr, fv = f"{HERE}/c1/{PFX}_e{e}.json", f"{HERE}/c3/vo_e{e}.json"
    if not (os.path.exists(fr) and os.path.exists(fv)): continue
    Tc = {r["frame"]: T44(r["c_from_world"]) for r in json.load(open(fr))["frames"] if r.get("inl_bc", 0) >= 30}
    Tv = {r["frame"]: T44(r["c_from_c0"]) for r in json.load(open(fv))["frames"]}
    k0 = min(Tc); ks = [t for t in sorted(Tc) if t in Tv]
    rv, tr = [], []
    for t in ks:
        Tvo = Tv[t] @ inv(Tv[k0]) @ Tc[k0]          # c_from_world by VO
        D = Tc[t] @ inv(Tvo)                          # c_map_from_c_vo = Delta (camera-frame error): T_wc_vo = T_wc_map Delta
        rv.append(Rot.from_matrix(D[:3, :3]).as_rotvec()); tr.append(D[:3, 3])
    rv, tr = np.array(rv), np.array(tr); n = ks[-1] + 1; tt = np.arange(n)
    prof[e] = (np.stack([np.interp(tt, ks, rv[:, i]) for i in range(3)], 1), np.stack([np.interp(tt, ks, tr[:, i]) for i in range(3)], 1))
print("profiles", {e: len(v[0]) for e, v in prof.items()}, flush=True)

# ---- public GT + vertices ----
VC = {}


def verts(name):
    if name not in VC:
        f = f"{ROOT}/data/track_3/public/mesh/{name}/{name}.glb"
        f = f if os.path.exists(f) else f"{ROOT}/data/track_3/public/mesh/{name}/{name}_visual.glb"
        m = trimesh.load(f, force="mesh")
        VC[name] = np.asarray(trimesh.sample.sample_surface(m, 500, seed=0)[0], float)
    return VC[name]


def load_gt(ep):
    df = pd.read_parquet(f"{ROOT}/data/track_3/public/data/chunk-000/episode_{ep:06d}.parquet", columns=["frame_index", "observation.objects"])
    df = df.sort_values("frame_index"); objs = df["observation.objects"].to_list()
    names = [o["name"] for o in objs[0]]
    P = np.array([[o["pose"] for o in row] for row in objs], float)  # T x B x 7 (x,y,z,qw,qx,qy,qz)
    X = np.concatenate([P[..., :3], P[..., 4:7], P[..., 3:4]], -1)  # -> xyz + xyzw
    return names, X


def cam0(ep):
    p = A8["poses"][f"a/p{ep:02d}_0000.jpg"]; o = A9[str(ep)]["o"]
    T = np.eye(4); T[:3, :3] = np.array(p["R_wc"]); T[:3, 3] = np.array(p["C"]) + np.array([o[0], o[1], o[2]]); return T  # world_from_cam


def apply_E(X, E):
    """X: T x B x 7 (xyzw); E: T x 4 x 4 world-frame transforms"""
    Y = X.copy()
    Y[..., :3] = np.einsum("tij,tbj->tbi", E[:, :3, :3], X[..., :3]) + E[:, None, :3, 3]
    qE = Rot.from_matrix(E[:, :3, :3])
    for b in range(X.shape[1]):
        Y[:, b, 3:] = (qE * Rot.from_quat(X[:, b, 3:])).as_quat()
    return Y


def stackA(X, rng):
    """note-02 'careful stereo' without drift: anchor 0.5 cm + 2 deg (slot-0 frame 0 only), jitter 0.5 cm/axis (anchor
    frame exact), rotation jitter 2 deg/axis, scale 1 % about slot-0 start, slot-1 body rotation 5 deg"""
    Y = X.copy(); T, B, _ = X.shape
    s0 = X[0, 0, :3].copy(); Y[..., :3] = s0 + 1.01 * (X[..., :3] - s0)
    Y[..., :3] += rng.normal(0, 0.005, (T, B, 3))
    for b in range(B):
        r = Rot.from_rotvec(np.radians(rng.normal(0, 2.0, (T, 3)))) * Rot.from_quat(X[:, b, 3:])
        if b == 1:
            ax = rng.normal(size=3); ax /= np.linalg.norm(ax); r = r * Rot.from_rotvec(ax * np.radians(5))
        Y[:, b, 3:] = r.as_quat()
    Y[0, 0] = X[0, 0]
    ax = rng.normal(size=3); ax /= np.linalg.norm(ax); d = rng.normal(size=3); d /= np.linalg.norm(d)
    Y[0, 0, :3] = X[0, 0, :3] + 0.005 * d
    Y[0, 0, 3:] = (Rot.from_rotvec(ax * np.radians(2)) * Rot.from_quat(X[0, 0, 3:])).as_quat()
    return Y


def auc(Xa, Xr, V):
    a = Xa[:, None]; r = Xr[:, None]
    a = M._warp_to_reference_start(a, r)
    return M._add_auc(M._object_add(a, r, V))


rows = []
rng = np.random.default_rng(0)
for ep in PUB:
    names, X = load_gt(ep); T = len(X); V = np.stack([verts(n) for n in names]); C0 = cam0(ep)
    for e, (rv, tr) in prof.items():
        if len(rv) < T: continue
        for seed in range(2):
            r2 = np.random.default_rng(1000 * ep + 10 * e + seed)
            Xs = stackA(X, r2)
            arms = {}
            # map: iid camera noise
            D = np.tile(np.eye(4), (T, 1, 1))
            D[:, :3, :3] = Rot.from_rotvec(np.radians(r2.normal(0, 0.015, (T, 3)))).as_matrix(); D[:, :3, 3] = r2.normal(0, 0.0007, (T, 3))
            D[0] = np.eye(4); arms["map"] = D
            for nm, k in (("VOd3", 1.0 / 3), ("VO", 1.0), ("VOx3", 3.0)):
                D = np.tile(np.eye(4), (T, 1, 1)); D[:, :3, :3] = Rot.from_rotvec(k * rv[:T]).as_matrix(); D[:, :3, 3] = k * tr[:T]; arms[nm] = D
            for nm, D in arms.items():
                E = np.einsum("ij,tjk,kl->til", C0, D, inv(C0))
                rows.append(dict(ep=ep, prof=e, seed=seed, arm=nm, ctx="iso", auc=auc(apply_E(X, E), X, V)))
                rows.append(dict(ep=ep, prof=e, seed=seed, arm=nm, ctx="stackA", auc=auc(apply_E(Xs, E), X, V)))
            # linear 5 cm common drift (note 02 reference), random direction
            d = r2.normal(size=3); d /= np.linalg.norm(d); E = np.tile(np.eye(4), (T, 1, 1)); E[:, :3, 3] = np.linspace(0, 1, T)[:, None] * 0.05 * d
            rows.append(dict(ep=ep, prof=e, seed=seed, arm="lin5", ctx="iso", auc=auc(apply_E(X, E), X, V)))
            rows.append(dict(ep=ep, prof=e, seed=seed, arm="lin5", ctx="stackA", auc=auc(apply_E(Xs, E), X, V)))
    print("ep", ep, "done", len(rows), flush=True)
df = pd.DataFrame(rows); df.to_json(OUT, orient="records")
# episode-mean first (scorer averages per episode), then over episodes
g = df.groupby(["ctx", "arm", "ep"]).auc.mean().groupby(["ctx", "arm"]).agg(["mean", "min"])
print(g.to_string())
for ctx in ("iso", "stackA"):
    piv = df[df.ctx == ctx].groupby(["ep", "prof", "seed", "arm"]).auc.mean().unstack("arm")
    for a in ("VOd3", "VO", "VOx3", "lin5"):
        dd = (piv["map"] - piv[a]).groupby(level="ep").mean()
        print(f"{ctx}: map - {a}: board mean {dd.mean():+.4f} (per-ep min {dd.min():+.4f} max {dd.max():+.4f})")
    dprof = (piv["map"] - piv["VO"]).groupby(level="prof").mean()
    print(f"{ctx}: map - VO by eval drift profile:", " ".join(f"e{k}:{v:+.3f}" for k, v in dprof.items()))
