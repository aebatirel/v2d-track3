"""Summarise out/guided_<ep>.npz. usage: guided_summ.py ep ..."""
import sys, numpy as np, collections
A = []; NM = {}
for e in sys.argv[1:]:
    z = np.load(f'out/guided_{e}.npz'); a = z['A']; A.append(np.c_[np.full(len(a), int(e)), a]); NM[int(e)] = list(z['names'])
A = np.vstack(A); cols = ['ep'] + list(z['cols']); g = lambda n: A[:, cols.index(n)]
cam, seg, r = g('cam'), g('seg'), g('r'); small = r < np.where(cam == 0, 11.5, 5.8); SEG = ['rest', 'held', 'carried']
print(f'n {len(A)}')
for key in ('w6', 'w15'):
    print(f'window {key[1:]} px (cam-a eq.): hit rate with oracle-centred / offset ({0.6*int(key[1:]):.0f} px a-eq) prediction; null false-alarm rate')
    for ci in range(3):
        for sz, sm in (('large', ~small), ('small', small)):
            line = []
            for s in range(3):
                m = (cam == ci) & sm & (seg == s) & np.isfinite(g(f'{key}_hit'))
                if m.sum() < 10: continue
                line.append(f'{SEG[s]} {np.nanmean(g(f"{key}_hit")[m]):.2f}/{np.nanmean(g(f"{key}o_hit")[m]):.2f} null {np.nanmean(g(f"{key}_null")[m]):.2f} (n{m.sum()})')
            if line: print(f'  cam {"abc"[ci]} {sz:5s}: ' + '; '.join(line))
# per-frame/object distinct hits (w6 oracle) in a, bc, abc
cnt = collections.defaultdict(list); D = collections.defaultdict(set); V = collections.defaultdict(set)
for row in A:
    ep, t, ci, j, k = int(row[0]), int(row[1]), int(row[2]), int(row[3]), int(row[4]); s = int(row[6])
    name = NM[ep][j]; V[(ep, t, j, s, name, ci)].add(k)
    if row[cols.index('w6o_hit')] == 1: D[(ep, t, j, s, name, ci)].add(k)
fr = collections.defaultdict(lambda: collections.defaultdict(set)); frd = collections.defaultdict(lambda: collections.defaultdict(set))
for key, ks in V.items(): fr[key[:5]][key[5]] |= ks
for key, ks in D.items(): frd[key[:5]][key[5]] |= ks
for key in fr:
    for cs, cis in (('a', [0]), ('bc', [1, 2]), ('abc', [0, 1, 2])):
        nv = len(set().union(*[fr[key][c] for c in cis])); nd = len(set().union(*[frd[key][c] for c in cis]))
        cnt[(key[4], SEG[key[3]], cs)].append((nv, nd))
print('\nper frame/object distinct markers HIT (w6, offset prediction): >=3 / 2 / 1 / 0  [z-visible >=3]  (frames with >=1 z-visible marker)')
for key in sorted(cnt):
    X = np.array(cnt[key]); nd, nv = X[:, 1], X[:, 0]
    print(f'  {key[0]:18s} {key[1]:8s} {key[2]:4s} n {len(X):4d}: {np.mean(nd>=3):.2f} / {np.mean(nd==2):.2f} / {np.mean(nd==1):.2f} / {np.mean(nd==0):.2f}  [{np.mean(nv>=3):.2f}]')
