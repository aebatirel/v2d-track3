"""Summarise out/census_<ep>.npz over episodes: per object x segment x camera-set, fraction of (frame, object) with
>=3 / 2 / 1 / 0 z-visible markers; marker radius (px) and image speed (px/frame).  usage: summ17.py ep [ep ...]"""
import sys, os, numpy as np, collections
import lib17 as L, seg17
eps = [int(e) for e in sys.argv[1:]]
SEG = ['rest', 'held', 'carried']; CS = {'a': [0], 'b': [1], 'c': [2], 'b|c': [1, 2], 'a|b|c': [0, 1, 2]}
cnt = collections.defaultdict(list); rad = collections.defaultdict(list); spd = collections.defaultdict(list); nfr = collections.Counter()
for ep in eps:
    z = np.load(f'out/{os.environ.get("PFX", "census_")}{ep}.npz'); VIS, names, nk, small = z['VIS'], z['names'], z['nk'], z['small']; seg = seg17.segments(L.load_gt(ep))[0]
    T = VIS.shape[0]
    for j, n in enumerate(names):
        if nk[j] == 0: continue
        for t in range(T):
            s = SEG[seg[t, j]]; nfr[(n, s)] += 1
            for cs, ci in CS.items():
                m = VIS[t, ci, j, :nk[j]].any(0).sum(); cnt[(n, s, cs)].append(m)
            for ci, c in enumerate('abc'):
                for k in range(nk[j]):
                    if VIS[t, ci, j, k]:
                        key = (c, 'small' if small[j, k] else 'large')
                        rad[key].append(z['RPX'][t, ci, j, k]);
                        if np.isfinite(z['SPD'][t, ci, j, k]): spd[(c, s)].append(z['SPD'][t, ci, j, k])
print('episodes', eps)
print(f'{"object":18s} {"seg":8s} {"frames":>6s} | ' + ' | '.join(f'{cs:^19s}' for cs in CS))
print(' ' * 36 + ' | '.join('>=3   2    1    0  ' for _ in CS))
for n in sorted(set(k[0] for k in nfr)):
    for s in SEG:
        if nfr[(n, s)] == 0: continue
        row = []
        for cs in CS:
            m = np.array(cnt[(n, s, cs)])
            row.append(f'{np.mean(m>=3):.2f} {np.mean(m==2):.2f} {np.mean(m==1):.2f} {np.mean(m==0):.2f}')
        print(f'{n:18s} {s:8s} {nfr[(n,s)]:6d} | ' + ' | '.join(row))
print('\nmarker radius px (visible): median [p10, p90]')
for k in sorted(rad): r = np.array(rad[k]); print(f'  cam {k[0]} {k[1]:5s} n {len(r):6d}: {np.median(r):5.1f} [{np.percentile(r,10):5.1f}, {np.percentile(r,90):5.1f}]')
print('\nmarker image speed px/frame (own px; visible): median [p75, p90]')
for k in sorted(spd): r = np.array(spd[k]); print(f'  cam {k[0]} {k[1]:8s} n {len(r):6d}: {np.median(r):5.1f} [{np.percentile(r,75):5.1f}, {np.percentile(r,90):5.1f}]')
