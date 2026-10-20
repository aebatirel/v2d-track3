"""DIG 20 stage C: combined contact (c_detect touch) + object-motion (c_motion) rules -> anchor window end; errors vs
raw and robust GT perturbation; window bias (mm, deg, induced object shift) and official AUC on top of a 3 cm base
error (analysis only, public GT).
usage: c_eval2.py [rule=MC] [A=120] [T=2.0] [L=10] [margin=3] [auc=1]"""
import sys, os, json, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from c_lib import *
from c_eval import pairing_n, first_hit, window_bias, gt
F = 500.0


def contact_a(ep, A, persist=2, tag='v2'):
    f = f'{OUT}/feat_{tag}_p{ep}.npz'
    if not os.path.exists(f): return None
    r = np.load(f)['rows']
    c = first_hit(r, lambda x: x[:, 1] >= A, persist)
    return c if c is not None else 10 ** 4


MTAG = 't2'


def step_mag_mm(ep, tag=None):
    tag = tag or MTAG
    z = np.load(f'{OUT}/mot_{tag}_p{ep}.npz'); r = z['rows']; r0 = float(z['r0']); depth = float(z['z'])
    st = r[:, 1:4]; ok = np.isfinite(st).all(1)
    px = np.where(ok, np.hypot(st[:, 0], st[:, 1]) + np.radians(np.abs(np.nan_to_num(st[:, 2]))) * r0, 0.0)
    return r[:, 0].astype(int), px * depth / F * 1000, np.nan_to_num(r[:, 6], nan=99.0)  # mm at object depth; head flow px


KAPPA = 0.15


def motion_a(ep, T, W=5, S=None, kappa=None):
    """first a-index with a single step >= T + kappa * head-flow (mm; head flow in px), or (if S) a W-step sum >= S mm."""
    kappa = KAPPA if kappa is None else kappa
    k, mm, hf = step_mag_mm(ep)
    for i in range(len(k)):
        if mm[i] >= T + kappa * hf[i]: return int(k[i])
        if S is not None and i >= W - 1 and mm[i - W + 1:i + 1].sum() >= S: return int(k[i - W + 1])
    return 10 ** 4


def decide(ep, rule, A, T, L, S=None):
    c = contact_a(ep, A); m = motion_a(ep, T, S=S)
    if rule == 'C': ca = c
    elif rule == 'M': ca = m
    else: ca = min(m, c + L)
    return ca, c, m


if __name__ == '__main__':
    kv = dict(a.split('=') for a in sys.argv[1:])
    rule = kv.get('rule', 'MC'); A = float(kv.get('A', 120)); T = float(kv.get('T', 2.0)); L = int(kv.get('L', 10))
    margin = float(kv.get('margin', 3)); KAPPA = float(kv.get('kappa', 0.15)); do_auc = int(kv.get('auc', 1)); S = float(kv['S']) if 'S' in kv else None
    if do_auc: from c_auc import auc_window
    R = []
    for ep in PUB:
        if not os.path.exists(f'{OUT}/feat_v2_p{ep}.npz'): continue
        g = gt(ep); ca, c, m = decide(ep, rule, A, T, L, S)
        n = pairing_n(f'p{ep}', min(ca, g['n'] - 1)); cbc = ca - n; end = cbc - margin
        wb = window_bias(ep, min(end, g['n'] - 1)); wo = window_bias(ep, g['pert'] - 1); wr = window_bias(ep, g['pert_r'] - 1)
        w1 = window_bias(ep, g['on'] - 1)
        row = dict(ep=ep, ca=ca, c=c, m=m, cbc=cbc, end=end, pert=g['pert'], pert_r=g['pert_r'], on=g['on'],
                   e_raw=cbc - g['pert'], e_rob=cbc - g['pert_r'], det=wb, orc=wo, orr=wr, cm1=w1)
        if do_auc:
            row['auc'] = {k: auc_window(ep, v, 0.03, 4) for k, v in dict(det=min(end, g['n'] - 1), orc=g['pert_r'] - 1, cm1=g['on'] - 1, f0=0).items()}
        R.append(row)
        print(f'p{ep:2d} {g["name"][:12]:12s} C a{c:5d} M a{m:5d} -> bc{cbc:5.0f} | pert {g["pert"]:3d}/{g["pert_r"]:3d} on {g["on"]:3d} | err raw {cbc - g["pert"]:+5.0f} rob {cbc - g["pert_r"]:+5.0f}'
              f' | win n{wb["n"]:3d} {wb["dt"]:4.1f}mm {wb["dR"]:4.2f}d sh{wb["shift"]:4.1f} | orc_r n{wr["n"]:3d} {wr["dR"]:4.2f}d sh{wr["shift"]:4.1f} | 1cm {w1["dR"]:4.2f}d sh{w1["shift"]:4.1f}'
              + (f' | dAUC det {row["auc"]["det"] - row["auc"]["f0"]:+.4f} 1cm {row["auc"]["cm1"] - row["auc"]["f0"]:+.4f}' if do_auc else ''), flush=True)
    er = np.array([r['e_raw'] for r in R]); eb = np.array([r['e_rob'] for r in R])
    print(f'== rule {rule} A={A} T={T}mm kappa={KAPPA} L={L} margin={margin} S={S}: n={len(R)}')
    print(f'   onset err vs raw pert: median {np.median(er):+.1f}, p10/p90 {np.percentile(er, 10):+.1f}/{np.percentile(er, 90):+.1f}, range [{er.min():+.0f},{er.max():+.0f}]; '
          f'window end >= raw pert (late): {int((er - margin >= 0).sum())}')
    print(f'   onset err vs robust pert: median {np.median(eb):+.1f}, p10/p90 {np.percentile(eb, 10):+.1f}/{np.percentile(eb, 90):+.1f}, range [{eb.min():+.0f},{eb.max():+.0f}]; '
          f'late: {int((eb - margin >= 0).sum())}; empty windows {sum(r["det"]["n"] == 0 for r in R)}')
    for key in ('det', 'orc', 'orr', 'cm1'):
        v = lambda f: np.array([r[key][f] for r in R])
        print(f'   {key:4s}: n med {np.median(v("n")):4.0f} | dt mm med/p90/max {np.median(v("dt")):.2f}/{np.percentile(v("dt"), 90):.2f}/{v("dt").max():.2f}'
              f' | dR deg {np.median(v("dR")):.2f}/{np.percentile(v("dR"), 90):.2f}/{v("dR").max():.2f} | shift mm {np.median(v("shift")):.2f}/{np.percentile(v("shift"), 90):.2f}/{v("shift").max():.2f}')
    if do_auc:
        for key in ('det', 'orc', 'cm1'):
            d = np.array([r['auc'][key] - r['auc']['f0'] for r in R])
            print(f'   dAUC vs exact f0 ({key}): mean {d.mean():+.4f} min {d.min():+.4f}')
    json.dump(R, open(f'{OUT}/eval2_{rule}_A{A:g}_T{T:g}_L{L}_m{margin:g}.json', 'w'), default=float, indent=0)
