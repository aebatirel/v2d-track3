"""Sensitivity of the MC rule to its parameters (19 public eps): late windows, early slack, bias. Also the
contact-only (C) onset error distribution and leave-one-episode-out choice of (T, kappa, L, A).
usage: c_grid.py"""
import sys, os, itertools, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from c_lib import *
from c_eval import pairing_n, window_bias, gt
import c_eval2 as E


def evaluate(T, kappa, L, A, margin=3, eps=PUB):
    out = []
    for ep in eps:
        g = gt(ep); c = E.contact_a(ep, A); m = E.motion_a(ep, T, kappa=kappa)
        ca = c if L == 'C' else (m if L is None else min(m, c + L))
        ca = min(ca, g['n'] - 1); cbc = ca - pairing_n(f'p{ep}', ca); end = cbc - margin
        wb = window_bias(ep, min(end, g['n'] - 1))
        out.append(dict(ep=ep, cbc=cbc, er=cbc - g['pert'], eb=cbc - g['pert_r'], end=end, late_r=end >= g['pert_r'],
                        n=wb['n'], dR=wb['dR'], dt=wb['dt'], sh=wb['shift'], slack=(g['pert_r'] - 1) - end))
    return out


def stat(o):
    dR = np.array([x['dR'] for x in o]); sh = np.array([x['sh'] for x in o]); n = np.array([x['n'] for x in o])
    late = sum(x['late_r'] for x in o); empty = int((n == 0).sum())
    return late, empty, float(np.median(n)), float(dR.max()), float(np.percentile(dR, 90)), float(sh.max()), float(np.mean(sh))


if __name__ == '__main__':
    # contact-only error distribution
    for A in (60, 120, 240, 480):
        o = evaluate(2.0, 0.15, 'C', A)
        er = np.array([x['er'] for x in o]); eb = np.array([x['eb'] for x in o])
        print(f'C only A={A}: err raw median {np.median(er):+.0f} p10/p90 {np.percentile(er, 10):+.0f}/{np.percentile(er, 90):+.0f} '
              f'| robust median {np.median(eb):+.0f} p10/p90 {np.percentile(eb, 10):+.0f}/{np.percentile(eb, 90):+.0f} | late(rob) {sum(x["late_r"] for x in o)} '
              f'empty {sum(x["n"] == 0 for x in o)} | per-ep raw: ' + ' '.join(f'p{x["ep"]}:{x["er"]:+.0f}' for x in o), flush=True)
    for T, kap in ((1.5, 0.15), (2.0, 0.15), (3.0, 0.15), (2.0, 0.0), (2.0, 0.1), (2.0, 0.25)):
        o = evaluate(T, kap, None, 120)
        eb = np.array([x['eb'] for x in o])
        print(f'M only T={T} kappa={kap}: err robust median {np.median(eb):+.0f} | late {sum(x["late_r"] for x in o)} empty {sum(x["n"] == 0 for x in o)}'
              f' | ' + ' '.join(f'p{x["ep"]}:{x["eb"]:+.0f}' for x in o), flush=True)
    print('grid MC: T kappa L A -> late empty n_med dRmax dRp90 shmax shmean')
    G = {}
    for T, kap, L, A in itertools.product((1.5, 2.0, 2.5, 3.0), (0.0, 0.1, 0.15, 0.25), (5, 10, 20, 40), (60, 120, 240)):
        o = evaluate(T, kap, L, A); G[(T, kap, L, A)] = o
        s = stat(o)
        if (L in (10, 20) and A == 120) or s[0] > 3: print(f'  {T} {kap} {L} {A} -> ' + ' '.join(f'{v:.2f}' if isinstance(v, float) else str(v) for v in s), flush=True)
    # leave-one-episode-out: choose params minimising (mean induced shift + 0.002 * mean slack) on the other 18
    picks = []; res = []
    for ep in PUB:
        best = None
        for key, o in G.items():
            oo = [x for x in o if x['ep'] != ep]
            cost = np.mean([x['sh'] for x in oo]) + 0.002 * np.mean([max(x['slack'], 0) for x in oo])
            if best is None or cost < best[0]: best = (cost, key)
        x = [y for y in G[best[1]] if y['ep'] == ep][0]; picks.append(best[1]); res.append(x)
    s = stat(res)
    print('LOEO held-out: late', s[0], 'empty', s[1], 'n_med', s[2], 'dRmax %.2f dRp90 %.2f shmax %.2f shmean %.2f' % s[3:])
    from collections import Counter
    print('LOEO picks:', Counter(picks).most_common(5))
