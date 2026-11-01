import sys, json, numpy as np, trimesh
def fit_axis(path, iters=8, rmax=0.07):
    m = trimesh.load(path, force='mesh')
    P, _ = trimesh.sample.sample_surface(m, 60000, seed=0)
    P = np.asarray(P)
    d = np.array([0, 0, 1.0]); c = P.mean(0)
    for _ in range(iters):
        # keep points near the current axis
        v = P - c; h = v @ d; rv = v - np.outer(h, d); r = np.linalg.norm(rv, axis=1)
        Q = P[r < rmax]; v = Q - c; h = v @ d
        e1 = np.cross(d, [1, 0, 0]); e1 /= np.linalg.norm(e1); e2 = np.cross(d, e1)
        lo, hi = np.percentile(h, [5, 95]); edges = np.linspace(lo, hi, 13)
        cs = []; hs = []
        for a, b in zip(edges[:-1], edges[1:]):
            s = (h >= a) & (h < b)
            if s.sum() < 200: continue
            x = v[s] @ e1; y = v[s] @ e2
            A = np.c_[2 * x, 2 * y, np.ones_like(x)]; sol, *_ = np.linalg.lstsq(A, x**2 + y**2, rcond=None)
            cs.append(c + sol[0] * e1 + sol[1] * e2 + 0.5 * (a + b) * d); hs.append(0.5 * (a + b))
        cs = np.array(cs); mu = cs.mean(0)
        u, s_, vt = np.linalg.svd(cs - mu); dn = vt[0]
        if dn @ d < 0: dn = -dn
        d, c = dn / np.linalg.norm(dn), mu
    return d, c
def ang(a, b):
    return float(np.degrees(np.arccos(np.clip(abs(np.dot(a, b)) / np.linalg.norm(a) / np.linalg.norm(b), -1, 1))))
lib = sys.argv[1]; dl, cl = fit_axis(lib)
out = {'library_v3': {'axis_fit': dl.round(4).tolist(), 'tilt_from_z_deg': round(ang(dl, [0, 0, 1]), 2)}}
for p in sys.argv[2:]:
    df, cf = fit_axis(p)
    lj = p.replace('.glb', '.lathe.json'); la = np.array(json.load(open(lj))['axis'])
    out[p.split('/')[-1]] = {'axis_lathe_json': la.round(4).tolist(), 'axis_fit': df.round(4).tolist(),
        'fit_vs_lathe_json_deg': round(ang(df, la), 2), 'tilt_vs_library_v3_deg (lathe axis)': round(ang(la, dl), 2),
        'tilt_vs_library_v3_deg (fit)': round(ang(df, dl), 2), 'axis_offset_mm': round(float(np.linalg.norm(np.cross(cf - cl, dl)) * 1000), 1)}
print(json.dumps(out, indent=1))
