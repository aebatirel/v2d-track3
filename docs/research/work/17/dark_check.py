"""Texture cross-check: dark (mount-like) clusters of 6-40 mm extent not explained by a catalogued sphere."""
import sys, json, numpy as np, scipy.sparse as sp
from scipy.spatial import cKDTree
from scipy.sparse.csgraph import connected_components
from markers_cat import load, sample
cat = json.load(open(sys.argv[1]))
for n, L in cat.items():
    g, tex = load(n); P, C, N, area = sample(g, tex, 1_500_000, seed=2)
    lum = C.mean(1); d = lum < 0.2; Pd = P[d]
    pairs = cKDTree(Pd).query_pairs(0.0025, output_type='ndarray')
    G = sp.coo_matrix((np.ones(len(pairs)), (pairs[:, 0], pairs[:, 1])), shape=(len(Pd), len(Pd)))
    nc, lab = connected_components(G, directed=False)
    S = np.array([q['c'] for q in L]) if L else np.zeros((0, 3))
    out = []
    for k in range(nc):
        m = lab == k
        if m.sum() < 100: continue
        Q = Pd[m]; ext = np.ptp(Q, 0).max(); cen = Q.mean(0)
        if not (0.006 < ext < 0.045): continue
        dmin = np.min(np.linalg.norm(S - cen, axis=1)) if len(S) else 1
        out.append((dmin, cen, ext, m.sum()))
    print(n, 'dark clusters', len(out), 'unexplained (>15 mm from a sphere):')
    for dmin, cen, ext, cnt in out:
        if dmin > 0.015: print('   cen mm', np.round(cen * 1000, 1), 'ext mm %.1f n %d dmin mm %.0f' % (ext * 1000, cnt, dmin * 1000))
