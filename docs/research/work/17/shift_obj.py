"""Per-object GT-video time-offset scan (stage B resume). For z-visible marker views of MOVING objects (held/carried) in the
det sample, hit(shift) = any candidate with LOEO/holdout score >= THR within max(0.5 r, 3/2 px) and radius ratio 0.6-1.6 of
the marker projected with GT at shift s (b/c clock; cam a also -delta). No NMS (pure evidence test).
usage: [THR=0.3] shift_obj.py ep ep ..."""
import sys, os, numpy as np, collections
THR = float(os.environ.get('THR', 0.3)); SEG = ['rest', 'held', 'carried']
for ep in [int(e) for e in sys.argv[1:]]:
    d = np.load(f'out/det_{ep}.npz'); rows = d['rows']; S = np.load(f'out/score_{ep}.npy'); MK = d['MK']; SH = d['SHIFTS']; ns = len(SH)
    names = list(np.load(f'out/census_{ep}.npz')['names']); keep = S >= THR; R = rows[keep]
    idx = collections.defaultdict(list)
    for i in range(len(R)): idx[(int(R[i, 0]), int(R[i, 1]))].append(i)
    acc = collections.defaultdict(lambda: np.zeros(ns)); n = collections.Counter()
    for m in MK:
        t, ci, j, s, r = int(m[0]), int(m[1]), int(m[2]), int(m[5]), m[4]
        if s == 0: continue
        D = R[idx.get((t, ci), [])]; key = (names[j], SEG[s], 'a' if ci == 0 else 'bc'); n[key] += 1
        if len(D) == 0: continue
        rad = max(0.5 * r, 3.0 if ci == 0 else 2.0)
        for q in range(ns):
            dd = np.hypot(D[:, 2] - m[7 + q], D[:, 3] - m[7 + ns + q]); rr = D[:, 4] / r
            acc[key][q] += np.any((dd < rad) & (rr > 0.6) & (rr < 1.6))
    for key in sorted(n):
        h = acc[key] / max(n[key], 1); qb = int(np.argmax(h))
        print(f'ep {ep} {key[0]:17s} {key[1]:7s} {key[2]:2s} n {n[key]:4d} best {SH[qb]:+.2f} ({h[qb]:.2f}) | ' + ' '.join(f'{SH[q]:+.2f}:{h[q]:.2f}' for q in range(ns)))
