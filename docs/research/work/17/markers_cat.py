"""Stage A1: marker sphere catalogue from the public scans by a fixed-radius normal-Hough transform.
Each surface sample p with unit outward normal n votes for a sphere centre c = p - r n (r in 5.5..9 mm).
Peaks = sphere centres. Refine: LSQ sphere on samples within r+1.5 mm, inliers |d-r|<0.6 mm, iterate.
Report radius, rms, coverage (fraction of the sphere's directions with samples), colour (sphere, ring below)."""
import sys, json, os, numpy as np, trimesh
from scipy.spatial import cKDTree
R = '/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public/mesh'
def load(n):
    p = f'{R}/{n}/{n}.glb'
    if not os.path.exists(p): p = f'{R}/{n}/{n}_visual.glb'
    s = trimesh.load(p); g = list(s.geometry.values())[0]
    tex = np.asarray(g.visual.material.baseColorTexture.convert('RGB')).astype(np.float32) / 255.
    return g, tex
def sample(g, tex, n, seed=0):
    rng = np.random.default_rng(seed); a = g.area_faces
    fi = rng.choice(len(a), size=n, p=a / a.sum()); r1, r2 = rng.random(n), rng.random(n); s1 = np.sqrt(r1)
    b = np.stack([1 - s1, s1 * (1 - r2), s1 * r2], 1)
    P = (b[:, :, None] * g.vertices[g.faces[fi]]).sum(1)
    uv = (b[:, :, None] * g.visual.uv[g.faces[fi]]).sum(1); H, W = tex.shape[:2]
    u = np.clip((uv[:, 0] % 1.0) * (W - 1), 0, W - 1); v = np.clip((1 - (uv[:, 1] % 1.0)) * (H - 1), 0, H - 1)
    C = tex[v.round().astype(int), u.round().astype(int)]
    N = g.face_normals[fi]
    return P, C, N, a.sum()
def sphere_fit(X):
    A = np.c_[2 * X, np.ones(len(X))]; b = (X * X).sum(1); s, *_ = np.linalg.lstsq(A, b, rcond=None)
    c = s[:3]; return c, np.sqrt(max(s[3] + c @ c, 0))
def fib(k=200):
    i = np.arange(k) + 0.5; phi = np.arccos(1 - 2 * i / k); th = np.pi * (1 + 5 ** 0.5) * i
    return np.c_[np.cos(th) * np.sin(phi), np.sin(th) * np.sin(phi), np.cos(phi)]
DIRS = fib(200)
RMIN = float(os.environ.get("RMIN", "0.0055"))
def run(name, nsamp=2_000_000):
    g, tex = load(name); P, C, N, area = sample(g, tex, nsamp)
    dens = nsamp / (area * 1e6)  # samples per mm^2
    # orientation: outward if normals point away from centroid on average
    sgn = np.sign(np.mean(((P - P.mean(0)) * N).sum(1)))
    N = N * sgn
    T = cKDTree(P)
    peaks = []
    for r in np.arange(RMIN, 0.0091, 0.0005):
        Cc = P - r * N
        key = np.floor(Cc / 0.0015).astype(np.int64)
        k1 = key[:, 0] * 1_000_003 ** 2 + key[:, 1] * 1_000_003 + key[:, 2]
        u, inv, cnt = np.unique(k1, return_inverse=True, return_counts=True)
        # expected votes for a full sphere of radius r: 4 pi r^2 * dens (spread over a few voxels)
        thr = 0.08 * 4 * np.pi * (r * 1e3) ** 2 * dens
        for j in np.where(cnt > thr)[0]:
            m = inv == j; peaks.append((Cc[m].mean(0), r, cnt[j]))
    # refine + dedupe
    res = []
    for c0, r0, v in sorted(peaks, key=lambda t: -t[2]):
        if any(np.linalg.norm(c0 - q['c']) < 0.006 for q in res): continue
        c, r = c0, r0
        for _ in range(6):
            idx = np.array(T.query_ball_point(c, r + 0.0015))
            if len(idx) < 50: break
            d = np.linalg.norm(P[idx] - c, axis=1); inl = idx[np.abs(d - r) < 0.0006]
            # also require normals consistent with the sphere (outward)
            rad = (P[inl] - c); rad /= np.linalg.norm(rad, axis=1, keepdims=True)
            inl = inl[(rad * N[inl]).sum(1) > 0.7]
            if len(inl) < 50: break
            c, r = sphere_fit(P[inl])
        else:
            pass
        if len(idx) < 50 or len(inl) < 50 or not (RMIN - 0.0005 < r < 0.0095): continue
        if any(np.linalg.norm(c - q['c']) < 0.006 for q in res): continue
        d = np.linalg.norm(P[inl] - c, axis=1); rms = np.sqrt(np.mean((d - r) ** 2))
        rad = (P[inl] - c); rad /= np.linalg.norm(rad, axis=1, keepdims=True)
        cov = np.mean((DIRS @ rad.T).max(1) > np.cos(np.radians(12)))
        area_mm2 = len(inl) / dens
        # colour of sphere inliers and of a ring just below the sphere (mount)
        col = C[inl].mean(0)
        ring = np.array(T.query_ball_point(c, r + 0.006)); dr = np.linalg.norm(P[ring] - c, axis=1)
        ring = ring[(dr > r + 0.0015)]
        rcol = C[ring].mean(0) if len(ring) else np.zeros(3)
        res.append(dict(c=c, r=float(r), rms=float(rms), cov=float(cov), n=int(len(inl)), area_mm2=float(area_mm2),
                        votes=int(v), col=col.tolist(), ring_col=rcol.tolist()))
    return res, dens
if __name__ == '__main__':
    names = sys.argv[1:] or sorted(os.listdir(R))
    out = {}
    for n in names:
        res, dens = run(n)
        print(f'{n}: density {dens:.2f}/mm2, candidates {len(res)}', flush=True)
        for q in sorted(res, key=lambda q: -q['area_mm2']):
            print('   c mm', np.round(q['c'] * 1000, 1), f"r {q['r']*1000:.2f} rms {q['rms']*1000:.2f} cov {q['cov']:.2f} area {q['area_mm2']:.0f}mm2 votes {q['votes']} col {np.round(q['col'],2)} ring {np.round(q['ring_col'],2)}")
        out[n] = [dict(q, c=q['c'].tolist()) for q in res]
    json.dump(out, open('out/markers_cand_' + ('all' if not sys.argv[1:] else '_'.join(names)) + '.json', 'w'), indent=1)
