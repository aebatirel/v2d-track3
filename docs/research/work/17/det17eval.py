"""Stage B detector evaluation (LOEO scores from det17score.py). Per image: detections = candidates with score >= thr, greedy
NMS (suppress centres within the larger radius of a kept one). Recall vs z-visible projected markers (MK rows, GT at SH);
precision full-frame (frames with full-frame Hough only) and inside the object ROIs; per-frame/object counts of detected markers; GT-video time-offset scan.
usage: det17eval.py ep ep ...  (env THR=0.5)"""
import sys, os, numpy as np, collections
eps = [int(e) for e in sys.argv[1:]]; THRS = (0.1, 0.3, 0.5, 0.7, 0.9); THR = float(os.environ.get('THR', 0.5))
SEG = ['rest', 'held', 'carried']
from det17lib import match
from det17lib import nms as _nms
SC = 10
nms = lambda D: _nms(D, SC)
rec = collections.defaultdict(list); prec = collections.defaultdict(list); nfp = collections.defaultdict(list)
cnt = collections.defaultdict(list); shift_hits = collections.defaultdict(lambda: collections.defaultdict(list)); SHIFTS = None
for ep in eps:
    d = np.load(f'out/det_{ep}.npz'); rows = d['rows']; S = np.load(f'out/score_{ep}.npy'); MK = d['MK']; SH = float(d['SH'])
    SHIFTS = d['SHIFTS']; ns = len(SHIFTS); i0 = int(np.argmin(np.abs(SHIFTS - SH)))
    R = np.c_[rows, S]  # t ci x y r lab mid roi seg ff score
    names = list(np.load(f'out/census_{ep}.npz')['names'])
    imgs = collections.defaultdict(list)
    for i in range(len(R)): imgs[(int(R[i, 0]), int(R[i, 1]))].append(i)
    kept = {thr: {} for thr in THRS}
    for key, ii in imgs.items():
        D = R[ii]
        for thr in THRS:
            K = nms(D[D[:, SC] >= thr]) if (D[:, SC] >= thr).any() else np.zeros((0, 11)); kept[thr][key] = K
            ffi = bool(D[0, 9])
            for k in K:
                if k[5] < 0: continue  # near a projected marker but not a visible-marker match: ignore
                if ffi: prec[(thr, key[1], 'full')].append(k[5] == 1)
                if k[7] > 0: prec[(thr, key[1], 'roi')].append(k[5] == 1)
            if ffi: nfp[(thr, key[1], 'full')].append(int(np.sum(K[:, 5] == 0)) if len(K) else 0)
            nfp[(thr, key[1], 'roi')].append(int(np.sum((K[:, 5] == 0) & (K[:, 7] > 0))) if len(K) else 0)
    # recall + per-frame counts
    det_mk = collections.defaultdict(set); vis_mk = collections.defaultdict(set)
    for m in MK:
        t, ci, j, k, r, s, spd = int(m[0]), int(m[1]), int(m[2]), int(m[3]), m[4], int(m[5]), m[6]
        u, v = m[7 + i0], m[7 + ns + i0]
        for thr in THRS:
            K = kept[thr].get((t, ci), np.zeros((0, 11)))
            hit = match(K, u, v, r, ci); rec[(thr, ci, s, 'small' if r < (11.5 if ci == 0 else 5.8) else 'large')].append(hit)
            if thr == THR:
                vis_mk[(ep, t, j, 'abc'[ci])].add(k)
                if hit: det_mk[(ep, t, j, 'abc'[ci])].add(k)
        if s == 2 or s == 1:
            K = kept[THR].get((t, ci), np.zeros((0, 11)))
            for q in range(ns): shift_hits[('a' if ci == 0 else 'bc', SEG[s])][q].append(match(K, m[7 + q], m[7 + ns + q], r, ci))
    seg = d['seg']; frames = sorted(set((int(m[0])) for m in MK))
    for t in sorted(set(int(x) for x in rows[:, 0])):
        for j in range(seg.shape[1]):
            s = SEG[seg[t, j]]
            for cs in ('a', 'b', 'c', 'bc', 'abc'):
                nv = len(set().union(*[vis_mk.get((ep, t, j, c), set()) for c in cs])); nd = len(set().union(*[det_mk.get((ep, t, j, c), set()) for c in cs]))
                cnt[(names[j], s, cs)].append((nv, nd))
print('episodes', eps)
print('\nRECALL of z-visible markers (rows: thr, cam, seg, size): n, recall')
for thr in THRS:
    line = []
    for ci in range(3):
        for s in range(3):
            for sz in ('large', 'small'):
                v = rec.get((thr, ci, s, sz))
                if v and len(v) >= 10: line.append(f'{"abc"[ci]}-{SEG[s][:4]}-{sz[0]} {np.mean(v):.2f} (n{len(v)})')
    print(f' thr {thr}: ' + '; '.join(line))
print('\nPRECISION (ignoring detections near hidden/unmatched projected markers) and false detections per image')
for thr in THRS:
    print(f' thr {thr}: ' + '; '.join(f'{"abc"[ci]}-{w} P {np.mean(prec[(thr, ci, w)]):.2f} (n{len(prec[(thr, ci, w)])}) FP/img {np.mean(nfp[(thr, ci, w)]):.1f}' for ci in range(3) for w in ('full', 'roi') if prec.get((thr, ci, w))))
print(f'\nPER-FRAME distinct markers per object at thr {THR}: fraction with >=3 / 2 / 1 / 0 DETECTED (z-visible >=3 in brackets)')
for key in sorted(cnt):
    A = np.array(cnt[key]); nd, nv = A[:, 1], A[:, 0]
    print(f'  {key[0]:18s} {key[1]:8s} {key[2]:4s} n {len(A):4d}: det {np.mean(nd>=3):.2f} / {np.mean(nd==2):.2f} / {np.mean(nd==1):.2f} / {np.mean(nd==0):.2f}  [zvis>=3 {np.mean(nv>=3):.2f}]')
print(f'\nGT-video time offset scan (thr {THR}; recall of moving-object markers vs GT shift in frames, b/c clock; cam a also -delta)')
for key in sorted(shift_hits):
    h = shift_hits[key]; print(f'  {key[0]:2s} {key[1]:8s} n {len(h[0]):4d}: ' + ' '.join(f'{SHIFTS[q]:+.2f}:{np.mean(h[q]):.2f}' for q in range(len(SHIFTS))))
