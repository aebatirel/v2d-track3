"""Where are the outer-wall out-of-roundness outliers (>2 mm) of each cup, markers (16 mm) excluded? Cluster them."""
import numpy as np, json, sys, trimesh
from scipy.spatial import cKDTree
sys.path.insert(0, '/Users/aebatirel/Documents/Code/v2d-research/work/12-verify')
from v_c1_geo2 import ROOT, M, frame
for name in sys.argv[1:]:
    fit = json.load(open(f'/Users/aebatirel/Documents/Code/v2d-research/work/12-verify/c1_geo2_{name}.json'))
    p, a = np.array(fit['p']), np.array(fit['a'])
    g = list(trimesh.load(f'{ROOT}/mesh/{name}/{name}.glb').geometry.values())[0]
    P = np.asarray(trimesh.sample.sample_surface(g, 300000, seed=1)[0])
    allm = np.array([q['centre'] for q in M[name]])
    mk = np.array([q['centre'] for q in M[name] if 6.5e-3 < q['radius'] < 8.6e-3 and q['bright'] > 0.55])
    P = P[cKDTree(mk).query(P)[0] > 0.016]
    e1, e2 = frame(a); Y = P - p; h = Y @ a; rr = Y - np.outer(h, a); r = np.linalg.norm(rr, axis=1)
    th = np.degrees(np.arctan2(rr @ e2, rr @ e1))
    hb = np.floor(h / 0.004).astype(int); tb = np.floor((th + 180) / 5).astype(int)
    rmax = {}
    for i in np.argsort(r):
        rmax[(hb[i], tb[i])] = i   # last = max r
    keys = np.array(list(rmax.keys())); idx = np.array(list(rmax.values()))
    out = []
    for hv in np.unique(keys[:, 0]):
        s = keys[:, 0] == hv
        if s.sum() < 60: continue
        med = np.median(r[idx[s]])
        for i in idx[s]:
            if abs(r[i] - med) > 0.002: out.append((h[i] * 1e3, th[i], (r[i] - med) * 1e3, *(P[i] * 1e3)))
    out = np.array(out)
    print(name, 'n outer bins >2 mm:', len(out))
    # cluster by 3D position 15 mm
    used = np.zeros(len(out), bool)
    for i in np.argsort(-np.abs(out[:, 2])):
        if used[i]: continue
        c = np.linalg.norm(out[:, 3:] - out[i, 3:], axis=1) < 20; c &= ~used; used |= c
        dm = cKDTree(allm * 1e3).query(out[i, 3:])
        print('  cluster n=%d  h %.0f mm  theta %.0f deg  dev max %+.1f mm  xyz %s  nearest raw-marker-list entry %.0f mm (r=%.1f bright=%.2f)' % (
            c.sum(), out[i, 0], out[i, 1], out[i, 2], np.round(out[i, 3:]).astype(int), dm[0], M[name][dm[1]]['radius'] * 1e3, M[name][dm[1]]['bright']))
