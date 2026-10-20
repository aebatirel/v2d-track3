"""Verifier (dig 13, claim C1): independent geometry statistics along STORED axes for Track 2 (npz) and Track 3 (GLB).
Own code; does not import dig-13 modules. Per scan: area centroid, sd along stored axes, extents along stored axes,
eigen-order, exact skew along stored axes (closed form for linear f over triangles), MC cross-check of skew, and
single-point influence-function SD of the skew (se1, delta method) from an area-weighted sample.
Writes out/v_geom.jsonl (one line per scan, resumable)."""
import os, sys, json, numpy as np, pygltflib
OUT = "/Users/aebatirel/Documents/Code/v2d-research/work/13-verify/out/v_geom.jsonl"
os.makedirs(os.path.dirname(OUT), exist_ok=True)
T2 = "/Users/aebatirel/Documents/Code/v2d-research/work/13/t2"
T3 = "/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public/mesh"
rng = np.random.default_rng(7)


def glb_load(path):
    g = pygltflib.GLTF2().load(path); blob = g.binary_blob()
    CT = {5121: np.uint8, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}; NC = {"SCALAR": 1, "VEC3": 3}
    def acc(i):
        a = g.accessors[i]; bv = g.bufferViews[a.bufferView]
        st = (bv.byteOffset or 0) + (a.byteOffset or 0); dt = np.dtype(CT[a.componentType])
        n = a.count * NC[a.type]
        assert bv.byteStride in (None, 0, dt.itemsize * NC[a.type])
        return np.frombuffer(blob[st:st + n * dt.itemsize], dtype=dt).reshape(-1, NC[a.type])
    Vs, Fs, off = [], [], 0
    for m in g.meshes:
        for p in m.primitives:
            V = acc(p.attributes.POSITION).astype(np.float64); F = acc(p.indices).reshape(-1, 3).astype(np.int64)
            Vs.append(V); Fs.append(F + off); off += len(V)
    return np.concatenate(Vs), np.concatenate(Fs)


def sample(T, area, n):
    i = rng.choice(len(area), n, p=area / area.sum())
    u, v = rng.random(n), rng.random(n); m = u + v > 1; u[m], v[m] = 1 - u[m], 1 - v[m]
    t = T[i]; return t[:, 0] + u[:, None] * (t[:, 1] - t[:, 0]) + v[:, None] * (t[:, 2] - t[:, 0])


def stats(V, F):
    T = V[F]; area = 0.5 * np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1); A = area.sum()
    c = (area[:, None] * T.mean(1)).sum(0) / A
    Q = T - c
    # exact moments of linear f over a triangle: int f^2 = A/6 * h2, int f^3 = A/10 * h3
    a, b, d = Q[:, 0], Q[:, 1], Q[:, 2]
    m2 = (area[:, None] * (a * a + b * b + d * d + a * b + a * d + b * d)).sum(0) / 6 / A
    h3 = a ** 3 + b ** 3 + d ** 3 + a * a * (b + d) + b * b * (a + d) + d * d * (a + b) + a * b * d
    m3 = (area[:, None] * h3).sum(0) / 10 / A
    skew = m3 / m2 ** 1.5
    # covariance (full) for eigen order
    C = np.zeros((3, 3))
    for i in range(3):
        for j in range(3):
            C[i, j] = (area * (sum(Q[:, k, i] * Q[:, k, j] for k in range(3)) + Q[:, :, i].sum(1) * Q[:, :, j].sum(1))).sum() / 12 / A
    w, E = np.linalg.eigh(C)
    dev = [float(np.degrees(np.arccos(min(1.0, np.max(np.abs(E[:, i])))))) for i in range(3)]
    ext = (V.max(0) - V.min(0))
    # MC cross-check + influence-function SD for skew
    P = sample(T, area, 400000) - c
    z = P - P.mean(0); s2 = (z ** 2).mean(0); s3 = (z ** 3).mean(0); g = s3 / s2 ** 1.5
    IF = ((z ** 3 - s3) - 3 * s2 * z) / s2 ** 1.5 - 1.5 * s3 * (z ** 2 - s2) / s2 ** 2.5
    return dict(centroid_mm=(1000 * c).round(3).tolist(), sd_mm=(1000 * np.sqrt(m2)).round(2).tolist(),
                ext_mm=(1000 * ext).round(1).tolist(), eig_sd_mm=(1000 * np.sqrt(w)).round(2).tolist(),
                eig_dev_deg=np.round(dev, 3).tolist(), skew=skew.round(5).tolist(), skew_mc=g.round(4).tolist(),
                se1=IF.std(0).round(3).tolist(), nF=int(len(F)), offdiag_max=float(np.abs(C - np.diag(np.diag(C))).max() / np.sqrt(np.outer(np.diag(C), np.diag(C))).max()))


if __name__ == "__main__":
    done = set()
    if os.path.exists(OUT):
        done = {json.loads(l)["name"] for l in open(OUT)}
    jobs = []
    for f in sorted(os.listdir(T2)):
        if f.endswith(".npz"): jobs.append(("T2", f[:-4], os.path.join(T2, f)))
    for d in sorted(os.listdir(T3)):
        fs = sorted(os.listdir(os.path.join(T3, d)))
        vis = [x for x in fs if x.endswith("_visual.glb")] or [x for x in fs if x == d + ".glb"]
        jobs.append(("T3", d, os.path.join(T3, d, vis[0])))
    for tr, name, p in jobs:
        if name in done: continue
        if tr == "T2":
            z = np.load(p); V, F = z["V"], z["F"]
        else:
            V, F = glb_load(p)
        S = stats(V, F); S.update(name=name, track=tr, file=os.path.basename(p))
        with open(OUT, "a") as fo: fo.write(json.dumps(S) + "\n")
        print(tr, name, S["sd_mm"], S["skew"], S["skew_mc"], flush=True)
