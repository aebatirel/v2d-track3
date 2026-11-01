"""Does lathe_obs.fit_axis's TIE (1.25) opening tie-break change the C0 cup axis? GT-free (our obs points only)."""
import sys, numpy as np
sys.path.insert(0, '/home/user/v2d-track3/docs/research/mesh-2026-10-26/scripts')
import lathe_obs as L
from scipy.cluster.vq import kmeans2
Z = np.load(sys.argv[1]); P = Z['pts'].astype(np.float64); C = Z['cam'].astype(np.float64)
key = np.floor(P / 0.0015).astype(np.int64); _, first = np.unique(key, axis=0, return_index=True); P, C = P[first], C[first]
sub = np.random.default_rng(0).choice(len(P), min(60000, len(P)), replace=False); P, C = P[sub], C[sub]
c0 = P.mean(0); X = P - c0
n, planar = L.normals(X, C - c0, k=24); nb = np.cross(X, n); w0 = planar.clip(0, 1) ** 2
dirs = [L._irls(n, nb, planar, w0.copy(), 8)[0]]
_, lab = kmeans2(X, 6, seed=0, minit='++')
for q in range(6):
    m = lab == q
    if m.sum() > 500: dirs.append(L._irls(n, nb, planar, w0 * m, 8)[0])
dirs += list(np.linalg.eigh(np.cov(X.T))[1].T)
v = C - P; v /= np.linalg.norm(v, axis=1, keepdims=True)
inside = np.einsum('ni,ni->n', n, X - X.mean(0)) < 0
opening = None
if inside.sum() > 100:
    dirs += list(np.linalg.eigh(np.cov(X[inside].T))[1].T)
    opening = v[inside].mean(0); opening /= np.linalg.norm(opening); dirs.append(opening)
s2 = np.random.default_rng(1).choice(len(P), min(20000, len(P)), replace=False)
sc = []
for a in dirs:
    a = a / np.linalg.norm(a); abar = L._place(n, nb, planar, a); c = c0 + np.cross(a, abar); c = c + a * ((P - c) @ a).mean()
    sc.append((L.rot_consistency(P[s2], c, a), c, a))
best = min(sc, key=lambda x: x[0])
ties = [x for x in sc if x[0] <= 1.25 * best[0]]
pick = max(ties, key=lambda x: abs(x[2] @ opening)) if opening is not None else best
ang = np.degrees(np.arccos(min(1, abs(best[2] @ pick[2]))))
print('n cands', len(sc), 'best rotcons mm', round(best[0]*1e3, 3), 'n ties(1.25)', len(ties), 'pick rotcons', round(pick[0]*1e3, 3), 'angle best-vs-pick deg', round(float(ang), 2))
for f in (1.1, 1.5, 2.0):
    t = [x for x in sc if x[0] <= f * best[0]]; p = max(t, key=lambda x: abs(x[2] @ opening))
    print('TIE', f, 'n', len(t), 'angle to 1.25 pick', round(float(np.degrees(np.arccos(min(1, abs(p[2] @ pick[2]))))), 2))
