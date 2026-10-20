"""Verifier: sliding-window a-b and b-c offsets (+-15 intervals, rig R fixed from the whole fit) and per-stream
|w| spike ratios, to localise integer pairing changes (drops)."""
import sys, numpy as np
from v_sync import *
for key in sys.argv[1:]:
    z = np.load(f'{OD}/{key}.npz'); Wa, Wb, Wc = fill(z['Wa'][:, 0]), fill(z['Wb']), fill(z['Wc'])
    n = len(Wb); _, _, Rab = vec_offset(Wa, Wb)
    out = []
    for c in range(15, n - 15, 5):
        ks = np.arange(c - 15, c + 16); s, cost, _ = vec_offset(Wa, Wb, R=Rab, ks=ks); out.append((c, s * 50, cost))
    segs = ' '.join(f'{c}:{s:+.0f}' for c, s, _ in out)
    ma, mb, mc = (np.linalg.norm(w, axis=1) for w in (Wa, Wb, Wc))
    def ratio(m):
        r = np.full(len(m), np.nan)
        for k in range(2, len(m) - 2): r[k] = m[k] / max(np.median(np.r_[m[k-2:k], m[k+1:k+3]]), 1e-4)
        return r
    ra, rb, rc = ratio(ma), ratio(mb), ratio(mc)
    sa = [(k, round(ra[k], 2), round(rb[k], 2)) for k in range(n) if np.isfinite(ra[k]) and ra[k] > 2.5 and rb[k] < 1.6]
    sb = [(k, round(rb[k], 2), round(rc[k], 2), round(ra[k], 2)) for k in range(n) if np.isfinite(rb[k]) and rb[k] > 2.5 and rc[k] > 2.5 and ra[k] < 1.6]
    print(f'{key}: slide a-b ms by centre: {segs}\n   a-only spikes (k, ra, rb): {sa}\n   bc-only spikes (k, rb, rc, ra): {sb}', flush=True)
