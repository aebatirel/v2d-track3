"""Sampling SD of the sample-based sign statistics (published frame, centred at the sample mean), n points per draw.
Output: out/b_sample.json {obj: {stat: [sd_x, sd_y, sd_z]}} at n = N (scale by sqrt(N/n) for other n)."""
import sys; sys.path.insert(0, "/Users/aebatirel/Documents/Code/v2d-research/work/13/scripts")
import json, os, numpy as np
from b_feats import MESH, NAMES, load

N = int(sys.argv[1]) if len(sys.argv) > 1 else 100000
REP = int(sys.argv[2]) if len(sys.argv) > 2 else 40


def sample(T, cum, n, rng):
    i = np.searchsorted(cum, rng.random(n) * cum[-1])
    r1 = np.sqrt(rng.random(n)); r2 = rng.random(n)
    return T[i, 0] * (1 - r1)[:, None] + T[i, 1] * (r1 * (1 - r2))[:, None] + T[i, 2] * (r1 * r2)[:, None]


def sstats(X):
    X = X - X.mean(0); sd = X.std(0); Z = X / sd; S = {}
    m2 = (X**2).mean(0)
    S["skew"] = (X**3).mean(0) / m2**1.5; S["m5"] = (X**5).mean(0) / m2**2.5
    S["ssq"] = (np.sign(Z) * Z**2).mean(0); S["s4"] = (np.sign(Z) * Z**4).mean(0)
    S["shalf"] = (np.sign(Z) * np.abs(Z)**0.5).mean(0); S["afrac"] = np.sign(Z).mean(0)
    S["negmed"] = -np.median(Z, 0)
    for p in (1, 5, 10, 25):
        q = np.percentile(Z, [p, 100 - p], axis=0); S[f"q{p:02d}"] = q[0] + q[1]
    S["ext"] = Z.max(0) + Z.min(0)
    S["absmax"] = np.array([Z[np.argmax(np.abs(Z[:, i])), i] for i in range(3)])
    S["far3d"] = Z[np.argmax((X**2).sum(1))]
    r2 = (Z**2).sum(1); S["m_ar2"] = (Z * r2[:, None]).mean(0)
    oth = {0: (1, 2), 1: (0, 2), 2: (0, 1)}
    S["m_lo2"] = np.array([(Z[:, i] * Z[:, oth[i][0]]**2).mean() for i in range(3)])
    S["m_hi2"] = np.array([(Z[:, i] * Z[:, oth[i][1]]**2).mean() for i in range(3)])
    S["m_lo_abs"] = np.array([(Z[:, i] * np.abs(Z[:, oth[i][0]])).mean() for i in range(3)])
    S["m_hi_abs"] = np.array([(Z[:, i] * np.abs(Z[:, oth[i][1]])).mean() for i in range(3)])
    S["m_az_absz"] = (Z * (Z[:, 2] * np.abs(Z[:, 2]))[:, None]).mean(0)
    S["m_az3"] = (Z * (Z[:, 2]**3)[:, None]).mean(0)
    return S


if __name__ == "__main__":
    rng = np.random.default_rng(5); out = {}
    for n in NAMES:
        d = f"{MESH}/{n}"; fn = f"{n}_visual.glb" if os.path.exists(f"{d}/{n}_visual.glb") else f"{n}.glb"
        V, F = load(f"{d}/{fn}"); T = V[F]
        area = 0.5 * np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1); cum = np.cumsum(area)
        draws = [sstats(sample(T, cum, N, rng)) for _ in range(REP)]
        out[n] = {k: np.std([d_[k] for d_ in draws], 0).tolist() for k in draws[0]}
        out[n]["_mean"] = {k: np.mean([d_[k] for d_ in draws], 0).tolist() for k in draws[0]}
        print(n, "sd(skew)", np.round(out[n]["skew"], 4), "sd(shalf)", np.round(out[n]["shalf"], 4), flush=True)
    json.dump(dict(N=N, REP=REP, sd=out), open("/Users/aebatirel/Documents/Code/v2d-research/work/13/out/b_sample.json", "w"))
