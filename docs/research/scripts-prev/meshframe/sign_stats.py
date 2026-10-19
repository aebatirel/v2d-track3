"""Search for a sign convention: compute many candidate per-axis sign statistics
for each public visual mesh and report which are consistent across all meshes."""
import glob, os, json, itertools
import numpy as np
import trimesh

HERE = os.path.dirname(__file__)
ROOT = os.path.join(HERE, "..", "t3", "public", "mesh")


def h3(a, b, c):
    return (a**3 + b**3 + c**3 + a*a*b + a*a*c + b*b*a + b*b*c + c*c*a + c*c*b + a*b*c)


def stats_for(path):
    m = trimesh.load(path, force="mesh", process=False)
    V = np.asarray(m.vertices, float); F = np.asarray(m.faces)
    T = V[F]
    area = 0.5 * np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1)
    A = area.sum()
    c = (area[:, None] * T.mean(1)).sum(0) / A
    S = {}
    f = T - c  # (n,3,3)
    m2 = np.array([(area * ((f[:, 0, i]**2 + f[:, 1, i]**2 + f[:, 2, i]**2 + f[:, 0, i]*f[:, 1, i] + f[:, 0, i]*f[:, 2, i] + f[:, 1, i]*f[:, 2, i]) / 6)).sum() / A for i in range(3)])
    m3 = np.array([(area * h3(f[:, 0, i], f[:, 1, i], f[:, 2, i]) / 10).sum() / A for i in range(3)])
    S["surf_skew_exact"] = m3 / m2**1.5
    Vc = V - c
    S["vert_third"] = (Vc**3).mean(0) / Vc.var(0)**1.5
    S["vert_mean"] = Vc.mean(0)
    S["bbox_centre"] = 0.5 * (V.max(0) + V.min(0)) - c
    S["vert_count_pos_minus_neg"] = (np.sign(Vc)).mean(0)
    # area-weighted fraction of surface on + side (median proxy): >0.5 means median >0 -> mean<median
    tc = T.mean(1) - c
    S["area_frac_pos_minus_half"] = np.array([(area * (tc[:, i] > 0)).sum() / A - 0.5 for i in range(3)])
    # volume
    mm = trimesh.load(path, force="mesh", process=True)
    S["vol_centroid"] = np.asarray(mm.center_mass) - c
    # signed volume integral of x^3 via sampled interior is costly; use divergence: skip
    # extreme points: farthest surface point along each axis (max |coord|) sign
    S["farthest_extreme_sign"] = np.where(V.max(0) - c > c - V.min(0), 1.0, -1.0)
    # area-weighted normal sum (open meshes): sign of net normal along axis
    fn = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]) * 0.5
    S["net_area_normal"] = fn.sum(0)
    # first moment of |x| asymmetry: E[x^+ ] - E[x^-] is zero by centroid; use E[x^2 sign x]
    S["surf_signed_square"] = np.array([(area * np.sign(tc[:, i]) * tc[:, i]**2).sum() / A for i in range(3)])
    return {k: np.asarray(v, float) for k, v in S.items()}


def main():
    names, allS = [], []
    for p in sorted(glob.glob(os.path.join(ROOT, "*", "*.glb"))):
        if p.endswith("_collision.glb"):
            continue
        n = os.path.basename(p)[:-4].replace("_visual", "")
        names.append(n); allS.append(stats_for(p))
    keys = list(allS[0].keys())
    res = {}
    for k in keys:
        M = np.array([s[k] for s in allS])  # (10,3)
        print(f"\n== {k}")
        for n, row in zip(names, M):
            print(f"   {n:18s} " + "  ".join(f"{v:+.4g}" for v in row))
        sg = np.sign(M)
        print("   sign pattern per axis (x,y,z):", ["".join("+" if s > 0 else "-" for s in sg[:, i]) for i in range(3)])
        res[k] = M.tolist()
    json.dump(dict(names=names, stats=res), open(os.path.join(HERE, "sign_stats.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
