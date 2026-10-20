"""Verifier: per-episode dAUC (det, cm1) with 24 seeds, iid 3 cm, to see whether per-clip worst cases are stable."""
import json, numpy as np
from v_c2auc import *
gt = {r['ep']: r for r in json.load(open(f'{ROOT}/work/20-verify/v_c12.json'))}
NS = 24; out = {}
for ep in PUB:
    names, P = load(ep); g = gt[ep]; d = {'det': [], 'cm1': [], 'orr': []}
    for sd in range(NS):
        rng = np.random.default_rng(31337 * ep + sd); ach0 = base(P, 'iid', 0.03, rng)
        f0, _ = auc(ach0, P, names)
        for k, w in dict(det=g['end'], cm1=g['on'] - 1, orr=g['pert_r'] - 1).items():
            ach = ach0.copy(); W = P[:w + 1, 0]; ach[0, 0, :3] = W[:, :3].mean(0); ach[0, 0, 3:] = karcher(W[:, 3:]).as_quat()
            d[k].append(auc(ach, P, names)[0] - f0)
    out[ep] = {k: (float(np.mean(v)), float(np.std(v) / np.sqrt(NS))) for k, v in d.items()}
    print(f'p{ep:2d}', {k: f'{m:+.4f}+-{s:.4f}' for k, (m, s) in out[ep].items()}, flush=True)
for k in ('det', 'orr', 'cm1'):
    m = np.array([out[e][k][0] for e in PUB]); print(k, f'mean {m.mean():+.4f} min {m.min():+.4f} (p{PUB[int(np.argmin(m))]})')
