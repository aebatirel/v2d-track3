"""Verifier: independent re-derivation of per-frame spin correctness and the temporal vote from saved E3 npz files
(cup = object 0). Vote variants: weights (3-marker x2 or x1), window +-15 or exact bin, tolerance for 'correct'.
usage: spin_check.py npz ..."""
import sys, numpy as np
def dang(a, b): return np.abs(((np.asarray(a) - b + 180) % 360) - 180)
for fn in sys.argv[1:]:
    z = np.load(fn); base = fn.split('/')[-1]; sp = float(base.split('_s')[-1].split('.')[0].split('n')[0]); want = (360 - sp) % 360
    T = int(z['T']); s = z['spin_0'][:T]; st = z['status_0'][:T]; fx = st >= 2
    ok15 = dang(s, want) <= 15; ok0 = dang(s, want) < 1
    vals, cnt = np.unique(dang(s[fx], want), return_counts=True)
    line = f'{base}: fix {fx.sum()} (3m {np.sum(st==3)}) per-frame ok(+-15) {np.sum(ok15 & fx)} exact {np.sum(ok0 & fx)} | |err| hist ' + ' '.join(f'{v:.0f}:{c}' for v, c in zip(vals, cnt))
    g = np.arange(0, 360, 15)
    for lab, m in (('all', np.ones(T, bool)), ('t<40', np.arange(T) < 40)):
        f = fx & m
        for wl, w in (('w2', np.where(st[f] == 3, 2.0, 1.0)), ('w1', np.ones(f.sum()))):
            for win in (15, 0):
                sc = np.array([np.sum(w * (dang(s[f], a) <= win + 0.1)) for a in g]); k = int(np.argmax(sc)); wv = g[k]
                ru = max([sc[i] for i in range(len(g)) if dang(g[i], wv) > 30] or [0])
                dec = 'ABST' if not (sc[k] >= 4 and sc[k] >= 2 * ru) else ('OK' if dang(wv, want) <= 15 else 'WRONG')
                line += f'\n   {lab} {wl} win{win}: winner {wv} err {dang(wv, want):.0f} score {sc[k]:.0f}/{ru:.0f} -> {dec}'
    print(line)
