"""Stage B: catalogue of axis-sign statistics for the public scans (published frame = R1 frame).
Every statistic is ODD under flipping its axis; value > 0 means 'keep the published direction' for the rule 's > 0'.
Polynomial moments use the 7-point degree-5 Dunavant rule per triangle (exact to degree 5).
Usage: b_feats.py [out.json]   (also importable: feats(V, F) -> dict)
"""
import os, sys, json, numpy as np, trimesh

MESH = "/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public/mesh"
NAMES = ["beige_cup", "blue_cup", "mini_dust_pan", "mini_sweeper", "plastic_dish_rack", "water_pitcher",
         "white_pot", "white_pot_lid", "wooden_piece_1", "wooden_piece_2"]
a1, b1, w1 = 0.059715871789770, 0.470142064105115, 0.132394152788506
a2, b2, w2 = 0.797426985353087, 0.101286507323456, 0.125939180544827
BARY = np.array([[1/3, 1/3, 1/3], [a1, b1, b1], [b1, a1, b1], [b1, b1, a1], [a2, b2, b2], [b2, a2, b2], [b2, b2, a2]])
WQ = np.array([0.225, w1, w1, w1, w2, w2, w2])


def quad_points(V, F):
    T = V[F]
    area = 0.5 * np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1)
    P = np.einsum("qk,nkd->nqd", BARY, T).reshape(-1, 3)
    W = (area[:, None] * WQ[None, :]).reshape(-1)
    return P, W / W.sum(), area


def r1_frame(V, F, ref=np.eye(3)):
    P, W, _ = quad_points(V, F)
    c = W @ P
    C = ((P - c) * W[:, None]).T @ (P - c)
    lam, E = np.linalg.eigh(C)
    for i in range(3):  # orient to agree with the reference axes (published frame = identity)
        if E[:, i] @ ref[:, i] < 0:
            E[:, i] *= -1
    if np.linalg.det(E) < 0:
        E[:, 0] *= -1
    return c, E, lam


def wq(x, W, q):
    o = np.argsort(x); cw = np.cumsum(W[o]); return x[o[min(np.searchsorted(cw, q), len(o) - 1)]]


def feats(V, F, ref=np.eye(3), hull=True):
    c, E, lam = r1_frame(V, F, ref)
    P, W, _ = quad_points(V, F)
    X = (P - c) @ E                 # quadrature points in the R1 frame
    Vx = (V - c) @ E                # vertices in the R1 frame
    sd = np.sqrt(lam)
    S = {}
    mu = lambda k: (W[:, None] * X**k).sum(0)
    m2, m3, m4, m5, m6 = mu(2), mu(3), mu(4), mu(5), mu(6)
    S["skew"] = m3 / m2**1.5
    S["m5"] = m5 / m2**2.5
    S["kurt"] = m4 / m2**2 - 3          # EVEN (selector only)
    # delta-method SE of sample skewness for n=1 (divide by sqrt(n))
    varm3 = m6 - m3**2 - 6 * m4 * m2 + 9 * m2**3
    cov23 = m5 - 4 * m3 * m2
    varm2 = m4 - m2**2
    S["skew_se1"] = np.sqrt(np.maximum(varm3 / m2**3 - 3 * m3 * cov23 / m2**4 + 2.25 * m3**2 * varm2 / m2**5, 0))  # EVEN
    Z = X / sd
    S["ssq"] = (W[:, None] * np.sign(Z) * Z**2).sum(0)
    S["s4"] = (W[:, None] * np.sign(Z) * Z**4).sum(0)
    S["shalf"] = (W[:, None] * np.sign(Z) * np.abs(Z)**0.5).sum(0)
    S["afrac"] = (W[:, None] * np.sign(Z)).sum(0)
    S["negmed"] = -np.array([wq(Z[:, i], W, 0.5) for i in range(3)])
    for p in (0.01, 0.05, 0.10, 0.25):
        S[f"q{int(p*100):02d}"] = np.array([wq(Z[:, i], W, 1 - p) + wq(Z[:, i], W, p) for i in range(3)])
    S["ext"] = (Vx.max(0) + Vx.min(0)) / sd
    S["absmax"] = np.array([Vx[np.argmax(np.abs(Vx[:, i])), i] for i in range(3)]) / sd   # sign of farthest point along axis
    far = Vx[np.argmax((Vx**2).sum(1))]
    S["far3d"] = far / sd
    r2 = (Z**2).sum(1)
    S["m_ar2"] = (W[:, None] * Z * r2[:, None]).sum(0)
    for i, j, nm in ((0, 1, "xy"), (0, 2, "xz"), (1, 0, "yx"), (1, 2, "yz"), (2, 0, "zx"), (2, 1, "zy")):
        S.setdefault("m_ab2", np.zeros(3)); S.setdefault("m_ac2", np.zeros(3))
    # m_ab2[a] = E[a * b^2] with b = next axis, m_ac2[a] = E[a * c^2] with c = the other one
    oth = {0: (1, 2), 1: (0, 2), 2: (0, 1)}
    S["m_lo2"] = np.array([(W * Z[:, i] * Z[:, oth[i][0]]**2).sum() for i in range(3)])   # other axis with lower index
    S["m_hi2"] = np.array([(W * Z[:, i] * Z[:, oth[i][1]]**2).sum() for i in range(3)])   # other axis with higher index
    S["m_lo_abs"] = np.array([(W * Z[:, i] * np.abs(Z[:, oth[i][0]])).sum() for i in range(3)])
    S["m_hi_abs"] = np.array([(W * Z[:, i] * np.abs(Z[:, oth[i][1]])).sum() for i in range(3)])
    # odd in a, and odd in z (valid for x,y once z is fixed): E[a z|z|], E[a z^3]; for z itself these equal ssq/s4-like
    S["m_az_absz"] = np.array([(W * Z[:, i] * Z[:, 2] * np.abs(Z[:, 2])).sum() for i in range(3)])
    S["m_az3"] = np.array([(W * Z[:, i] * Z[:, 2]**3).sum() for i in range(3)])
    S["vmean"] = Vx.mean(0) / sd
    Vu = np.unique(np.round(Vx, 7), axis=0)
    S["vmean_weld"] = Vu.mean(0) / sd
    S["vskew"] = ((Vu - Vu.mean(0))**3).mean(0) / Vu.var(0)**1.5
    m = trimesh.Trimesh(V, F, process=False)
    S["netnorm"] = (m.face_normals * m.area_faces[:, None]).sum(0) @ E / m.area
    if hull:
        h = m.convex_hull
        S["hull_surf_off"] = ((h.centroid - c) @ E) / sd
        S["hull_vol_off"] = ((h.center_mass - c) @ E) / sd
        Ph, Wh, _ = quad_points(np.asarray(h.vertices), np.asarray(h.faces))
        Xh = (Ph - Wh @ Ph) @ E
        S["hull_skew"] = (Wh[:, None] * Xh**3).sum(0) / (Wh[:, None] * Xh**2).sum(0)**1.5
    S["vol_off"] = ((m.center_mass - c) @ E) / sd
    out = {k: np.asarray(v, float).tolist() for k, v in S.items()}
    out["_c_mm"] = (c * 1e3).tolist(); out["_sd_mm"] = (sd * 1e3).tolist()
    out["_axis_dev_deg"] = np.degrees(np.arccos(np.clip(np.abs(np.diag(E.T @ ref)), 0, 1))).tolist()
    return out


def load(p):
    m = trimesh.load(p, force="mesh", process=False)
    return np.asarray(m.vertices, float), np.asarray(m.faces)


if __name__ == "__main__":
    outp = sys.argv[1] if len(sys.argv) > 1 else "/Users/aebatirel/Documents/Code/v2d-research/work/13/out/b_feats.json"
    res = {}
    for n in NAMES:
        d = f"{MESH}/{n}"
        for tag, fn in (("", f"{n}_visual.glb" if os.path.exists(f"{d}/{n}_visual.glb") else f"{n}.glb"), ("__collision", f"{n}_collision.glb")):
            if not os.path.exists(f"{d}/{fn}"):
                continue
            V, F = load(f"{d}/{fn}")
            res[n + tag] = feats(V, F)
            print(n + tag, "skew", np.round(res[n + tag]["skew"], 4), "dev", np.round(res[n + tag]["_axis_dev_deg"], 3), flush=True)
    json.dump(res, open(outp, "w"), indent=1)
