"""Guided + learned: for each z-visible marker (det sample), among the pass-1 Hough candidates within W px (cam-a eq.) of a
predicted centre (true + random offset 0.6 W), take the highest LOEO v2 score; hit if it is >= THR and matches the true
centre (max(0.5 r, 3/2 px), radius ratio 0.6-1.6). Null: same at a point 3 r away (false pick rate = best score >= THR).
usage: guided_learned.py W THR ep ..."""
import sys, numpy as np, collections
import lib17 as L
W, THR = float(sys.argv[1]), float(sys.argv[2]); eps = [int(e) for e in sys.argv[3:]]; FA = L.cam('a')[0][0, 0]
SEG = ['rest', 'held', 'carried']; res = collections.defaultdict(list); nul = collections.defaultdict(list); per = collections.defaultdict(lambda: collections.defaultdict(set)); vis = collections.defaultdict(lambda: collections.defaultdict(set))
rng = np.random.default_rng(0)
for ep in eps:
    d = np.load(f'out/det_{ep}.npz'); rows = d['rows']; S = np.load(f'out/score_{ep}.npy'); MK = d['MK']; SH = d['SHIFTS']; ns = len(SH)
    ia, ib = int(np.argmin(np.abs(SH + 0.25))), int(np.argmin(np.abs(SH + 0.5))); names = list(np.load(f'out/census_{ep}.npz')['names'])
    idx = collections.defaultdict(list)
    for i, (t, ci) in enumerate(rows[:, :2].astype(int)): idx[(t, ci)].append(i)
    idx = {k: np.array(v) for k, v in idx.items()}
    for m in MK:
        t, ci, j, k, r, s = int(m[0]), int(m[1]), int(m[2]), int(m[3]), m[4], int(m[5]); q = ia if ci == 0 else ib
        u, v = m[7 + q], m[7 + ns + q]; w = W / (FA / L.cam('abc'[ci])[0][0, 0]); tol = max(0.5 * r, 3.0 if ci == 0 else 2.0)
        ii = idx.get((t, ci), np.array([], int)); small = r < (11.5 if ci == 0 else 5.8)
        vis[(ep, t, j, names[j], s)][ci].add(k)
        def best(pu, pv):
            if len(ii) == 0: return None
            dd = np.hypot(rows[ii, 2] - pu, rows[ii, 3] - pv); rr = rows[ii, 4] / r; ok = (dd <= w) & (rr > 0.6) & (rr < 1.6)
            if not ok.any(): return None
            b = ii[ok][np.argmax(S[ii[ok]])]; return b if S[b] >= THR else None
        a = rng.uniform(0, 2 * np.pi); b = best(u + 0.6 * w * np.cos(a), v + 0.6 * w * np.sin(a))
        hit = b is not None and np.hypot(rows[b, 2] - u, rows[b, 3] - v) <= tol
        res[(ci, s, small)].append(hit)
        if hit: per[(ep, t, j, names[j], s)][ci].add(k)
        a = rng.uniform(0, 2 * np.pi); nul[(ci, s, small)].append(best(u + 3 * r * np.cos(a), v + 3 * r * np.sin(a)) is not None)
print(f'W {W} px a-eq, THR {THR}: hit rate (null false-pick rate)')
for ci in range(3):
    for sm in (False, True):
        print(f'  cam {"abc"[ci]} {"small" if sm else "large"}: ' + '; '.join(f'{SEG[s]} {np.mean(res[(ci,s,sm)]):.2f} ({np.mean(nul[(ci,s,sm)]):.2f}) n{len(res[(ci,s,sm)])}' for s in range(3) if len(res[(ci, s, sm)]) >= 10))
cnt = collections.defaultdict(list)
for key in vis:
    for cs, cis in (('a', [0]), ('bc', [1, 2]), ('abc', [0, 1, 2])):
        nv = len(set().union(*[vis[key][c] for c in cis])); nd = len(set().union(*[per[key][c] for c in cis])) if key in per else 0
        cnt[(key[3], SEG[key[4]], cs)].append((nv, nd))
print('per frame/object distinct markers hit: >=3 / >=2  [z-visible >=3] (frames with >=1 z-visible marker)')
for key in sorted(cnt):
    if key[2] != 'abc': continue
    X = np.array(cnt[key]); print(f'  {key[0]:18s} {key[1]:8s} {key[2]:4s} n {len(X):4d}: {np.mean(X[:,1]>=3):.2f} / {np.mean(X[:,1]>=2):.2f}  [{np.mean(X[:,0]>=3):.2f}]')
