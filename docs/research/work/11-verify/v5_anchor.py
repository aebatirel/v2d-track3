"""Verifier for dig-11 claim C5: independent re-implementation (own loader, own metric code, own yaw/spin model) of the
slot-0 anchor-prior experiment. Public GT only (analysis). usage: python v5_anchor.py [nverts] [seed]"""
import json, sys, numpy as np, pyarrow.parquet as pq, trimesh
from scipy.spatial.transform import Rotation as Rot
ROOT = "/Users/aebatirel/Documents/Code/v2d-research"; PUB = f"{ROOT}/data/track_3/public"
NV = int(sys.argv[1]) if len(sys.argv) > 1 else 500; SEED = int(sys.argv[2]) if len(sys.argv) > 2 else 0


def load(ep):
    t = pq.read_table(f"{PUB}/data/chunk-000/episode_{ep:06d}.parquet")
    names = json.loads(t.schema.metadata[b"objects"]); df = t.to_pandas().sort_values("frame_index")
    P = np.full((len(df), len(names), 7), np.nan)
    for i, objs in enumerate(df["observation.objects"]):
        for o in objs:
            p = np.asarray(o["pose"], float); P[i, names.index(o["name"])] = [*p[:3], p[4], p[5], p[6], p[3]]
    assert np.isfinite(P).all(), ep
    return names, P


_V = {}
def verts(n):
    if n not in _V:
        import os; f = f"{PUB}/mesh/{n}/{n}.glb"; f = f if os.path.exists(f) else f.replace(".glb", "_visual.glb")
        s = trimesh.load(f, force="scene"); m = trimesh.util.concatenate(list(s.dump()))
        _V[n] = trimesh.sample.sample_surface(m, NV, seed=SEED)[0]
    return _V[n]


def sym_axis(n):
    """body-frame symmetry axis = principal axis whose 180/arbitrary spin best preserves the mesh (own estimate)."""
    v = verts(n) - verts(n).mean(0); w, U = np.linalg.eigh(v.T @ v)
    return U


def metrics(ach, ref, names):
    # warp: align achieved slot-0 frame-0 pose onto reference slot-0 frame-0 pose (one rigid transform)
    Ra0 = Rot.from_quat(ach[0, 0, 3:]); Rr0 = Rot.from_quat(ref[0, 0, 3:]); Ral = Rr0 * Ra0.inv()
    off = ref[0, 0, :3] - Ral.apply(ach[0, 0, :3])
    T, B, _ = ach.shape; w = np.empty_like(ach)
    for b in range(B):
        w[:, b, :3] = Ral.apply(ach[:, b, :3]) + off; w[:, b, 3:] = (Ral * Rot.from_quat(ach[:, b, 3:])).as_quat()
    Ra = Rot.from_quat(w[..., 3:].reshape(-1, 4)).as_matrix().reshape(T, B, 3, 3)
    Rr = Rot.from_quat(ref[..., 3:].reshape(-1, 4)).as_matrix().reshape(T, B, 3, 3)
    add = np.stack([np.linalg.norm(np.einsum("tij,vj->tvi", Ra[:, b] - Rr[:, b], verts(names[b])) + (w[:, b, :3] - ref[:, b, :3])[:, None], axis=-1).mean(1) for b in range(B)], 1)
    th = np.arange(0.01, 0.10, 0.01); x = np.linspace(0, 1, th.size)
    auc = np.mean([np.trapezoid([np.mean(add[:, b] < t) for t in th], x=x) for b in range(B)])
    pos = np.linalg.norm(w[..., :3] - ref[..., :3], axis=-1).mean(0)
    dot = np.clip(np.abs(np.sum(w[..., 3:] * ref[..., 3:], -1)), 0, 1); ang = (2 * np.arccos(dot)).mean(0)
    sp = float(pos.mean() <= 0.1 and ang.mean() <= 0.5)
    mp = float(np.all((pos < 0.03) & (np.degrees(ang) < 30)))
    rpe = []
    for a in range(B):
        for c in range(a + 1, B):
            la = np.einsum("tji,tj->ti", Ra[:, a], w[:, c, :3] - w[:, a, :3]); lr = np.einsum("tji,tj->ti", Rr[:, a], ref[:, c, :3] - ref[:, a, :3])
            rpe.append(np.linalg.norm(la - lr, axis=-1))
    rpe = float(np.mean(rpe) * 100) if rpe else 0.0
    kp = np.vstack([np.eye(3), -np.eye(3)]) * 0.05
    ka = w[..., None, :3] + np.einsum("tbij,kj->tbki", Ra, kp); kr = ref[..., None, :3] + np.einsum("tbij,kj->tbki", Rr, kp)
    mppe = float(np.linalg.norm(ka - kr, axis=-1).mean() * 100)
    return np.array([auc, sp, mp, rpe, mppe])


def spin(P, axis_body, deg):
    o = P.copy(); o[:, 0, 3:] = (Rot.from_quat(P[:, 0, 3:]) * Rot.from_rotvec(np.radians(deg) * np.asarray(axis_body))).as_quat(); return o


def yaw_about(q, up_b, ref_b):
    """heading of body ref axis (perp. to the symmetry axis) projected onto world xy, deg."""
    h = Rot.from_quat(q).apply(ref_b); return np.degrees(np.arctan2(h[1], h[0]))


if __name__ == "__main__":
    UPB = {"blue_cup": [0, 0, -1], "wooden_piece_1": [1, 0, 0], "plastic_dish_rack": [1, 0, 0], "mini_sweeper": [0, 0, 1]}
    HB = {"blue_cup": [1, 0, 0], "wooden_piece_1": [0, 0, 1], "plastic_dish_rack": [0, 0, 1], "mini_sweeper": [0, 1, 0]}
    CASES = {12: ("C", [13]), 13: ("C", [12]), 21: ("C", [22]), 22: ("C", [21]), 23: ("2", [24]), 24: ("2", [23]),
             26: ("2", [27, 12, 13, 31]), 27: ("2", [26, 12, 13, 31]), 31: ("2", [18])}
    D = {}
    def yawof(ep, n):
        names, P = D.setdefault(ep, load(ep)); j = names.index(n); return yaw_about(P[0, j, 3:], UPB[n], HB[n])
    cm = lambda a: np.degrees(np.angle(np.mean(np.exp(1j * np.radians(a)))))
    wr = lambda a: (a + 180) % 360 - 180
    out = {}
    for ep, (sym, tw) in CASES.items():
        names, P = D.setdefault(ep, load(ep)); a = names[0]; ax = UPB[a]
        S = lambda s: metrics(spin(P, ax, s), P, names)
        truth = yawof(ep, a); prior = cm([yawof(t, a) for t in tw]); d = wr(prior - truth)
        r = dict(err=round(float(d), 2))
        r["random"] = np.mean([S(s) for s in np.arange(-180, 180, 5.0)], 0) if sym == "C" else np.mean([S(0), S(180)], 0)
        for W in (0, 3, 10):
            L = []
            for w in ((0,) if W == 0 else (-W, W)):
                e = wr(d + w)
                if sym == "2": e = 0.0 if abs(e) < 90 else 180.0
                L.append(S(e))
            r[f"W{W}"] = np.mean(L, 0)
        out[ep] = (sym, r)
        print(ep, sym, a, "err", r["err"], {k: np.round(v, 3).tolist() for k, v in r.items() if k != "err"}, flush=True)
    for sym in "C2":
        for k in ("random", "W0", "W3", "W10"):
            v = np.mean([r[k] for s, r in out.values() if s == sym], 0)
            print("AGG", sym, k, "AUC/SP/MP/RPE/MPPE", np.round(v, 3).tolist())
