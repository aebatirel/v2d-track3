import sys, json, numpy as np, trimesh
for p in sys.argv[1:]:
    m = trimesh.load(p, force='mesh'); P, fi = trimesh.sample.sample_surface(m, 80000, seed=0); P = np.asarray(P)
    c = np.median(P, 0); v = P - c; r = np.linalg.norm(v[:, :2], axis=1); z = v[:, 2]
    core = (r < 0.015)  # surface near the axis: the closed base (and nothing else for an open cup)
    lo, hi = np.percentile(z[r < 0.07], [1, 99])
    zc = z[core]
    print(p.split('/')[-1], 'z-range mm %.1f..%.1f' % (lo*1e3, hi*1e3), 'n_core', core.sum(),
          'core z median mm %.1f' % (np.median(zc)*1e3 if core.sum() else float('nan')),
          '-> base at', ('-z (opening +z)' if np.median(zc) < 0 else '+z (opening -z)') if core.sum() else '?')
