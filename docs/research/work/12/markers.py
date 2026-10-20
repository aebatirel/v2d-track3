"""Find mocap marker spheres baked into the scans (black mount + sphere)."""
import numpy as np, json
from scipy.spatial import cKDTree
from scipy.sparse.csgraph import connected_components
from meshlib import *

def sphere_fit(X):
    A = np.c_[2 * X, np.ones(len(X))]; b = (X * X).sum(1)
    s, *_ = np.linalg.lstsq(A, b, rcond=None)
    c = s[:3]; r = np.sqrt(s[3] + c @ c); return c, r

def ransac_sphere(X, rmin=0.004, rmax=0.010, it=2000, tol=0.0008, rng=np.random.default_rng(0)):
    best = (None, None, 0)
    for _ in range(it):
        S = X[rng.choice(len(X), 4, replace=False)]
        try: c, r = sphere_fit(S)
        except Exception: continue
        if not (rmin < r < rmax) or np.isnan(r): continue
        inl = np.abs(np.linalg.norm(X - c, axis=1) - r) < tol
        if inl.sum() > best[2]: best = (c, r, inl.sum())
    if best[0] is None: return None
    c, r, _ = best
    inl = np.abs(np.linalg.norm(X - c, axis=1) - r) < tol
    c, r = sphere_fit(X[inl]); inl = np.abs(np.linalg.norm(X - c, axis=1) - r) < tol
    return c, r, inl

def find_markers(name, dark=0.16, verbose=True):
    g, tex = load(name); P, C, N = sample(g, tex, 1500000, seed=2)
    d = C.max(1) < dark
    Pd = P[d]
    T = cKDTree(Pd); pairs = T.query_pairs(0.0025, output_type='ndarray')
    import scipy.sparse as sp
    G = sp.coo_matrix((np.ones(len(pairs)), (pairs[:, 0], pairs[:, 1])), shape=(len(Pd), len(Pd)))
    nc, lab = connected_components(G, directed=False)
    TT = cKDTree(P)
    res = []
    for k in range(nc):
        m = lab == k
        if m.sum() < 150: continue
        Q = Pd[m]; ext = np.ptp(Q, 0).max()
        if not (0.006 < ext < 0.035): continue
        cen = Q.mean(0)
        nb = P[TT.query_ball_point(cen, 0.022)]
        fit = ransac_sphere(nb)
        if fit is None: continue
        c, r, inl = fit
        # sphere should be mostly bright, not the dark mount
        idx = TT.query_ball_point(c, r + 0.0008)
        res.append(dict(mount=cen.tolist(), centre=c.tolist(), radius=float(r), n_dark=int(m.sum()), n_inl=int(inl.sum()), ext=float(ext),
                        bright=float(C[idx].mean()) if len(idx) else 0.0))
    if verbose:
        print(name, 'dark clusters kept', len(res))
        for q in res: print('  centre mm', np.round(np.array(q['centre']) * 1000, 1), 'r mm %.2f ndark %d ninl %d ext mm %.1f bright %.2f' % (q['radius'] * 1000, q['n_dark'], q['n_inl'], q['ext'] * 1000, q['bright']))
    return res

if __name__ == '__main__':
    allm = {}
    for n in ['blue_cup', 'beige_cup', 'white_pot_lid', 'white_pot', 'water_pitcher']:
        allm[n] = find_markers(n)
    json.dump(allm, open('out/markers_raw.json', 'w'), indent=1)
