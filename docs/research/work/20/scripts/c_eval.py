"""DIG 20 stage C evaluation (analysis only, public GT): contact rules on per-frame features -> b/c index ->
error vs GT first perturbation, and the anchor bias of the averaging window [0, c_bc - margin].
usage: c_eval.py <tag> [rule args as k=v ...]"""
import sys, os, json, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from c_lib import *
from scipy.spatial.transform import Rotation as Rot

SYNC = json.load(open(f'{ROOT}/work/20/out/sync_table.json'))['episodes']
COL = dict(k=0, touch=1, overlap=2, inside=3, dmin=4, ninl=5, med=6, chg=7, border=8)


def pairing_n(key, row):
    for s in SYNC[key]['pairing_a_to_b']:
        if s['rows'][0] <= row <= s['rows'][1]: return s['n']
    return 1


def first_hit(rows, rule, persist=2):
    hit = rule(rows)
    run = 0
    for i, h in enumerate(hit):
        run = run + 1 if h else 0
        if run >= persist: return int(rows[i - persist + 1, 0])
    return None


def mean_pose(P):
    """P: N x 7 [x y z qx qy qz qw] -> mean translation, chordal mean rotation."""
    return P[:, :3].mean(0), Rot.from_quat(P[:, 3:]).mean()


_GT = {}


def gt(ep):
    if ep not in _GT: _GT[ep] = gt_ref(ep)
    return _GT[ep]


def window_bias(ep, end):
    """window rows [0, end] inclusive (end<0 -> empty -> frame 0 only is used, bias 0 but flagged)."""
    g = gt(ep); P = g['e']['pose'][:, g['j']]
    end = int(np.floor(end))
    if end < 0: return dict(n=0, dt=0.0, dR=0.0, shift=0.0)
    t, Rm = mean_pose(P[:end + 1])
    dt = float(np.linalg.norm(t - P[0, :3]) * 1000); R0 = Rot.from_quat(P[0, 3:])
    dR = float(np.degrees((Rm * R0.inv()).magnitude()))
    # induced misalignment E = P_mean * P_0^-1 applied to every object centre in every row: mean displacement (mm)
    Rd = (Rm * R0.inv()).as_matrix(); td = t - Rd @ P[0, :3]
    X = g['e']['pose'][:, :, :3].reshape(-1, 3); X = X[np.isfinite(X).all(1)]
    shift = float(np.mean(np.linalg.norm(X @ Rd.T + td - X, axis=1)) * 1000)
    return dict(n=end + 1, dt=dt, dR=dR, shift=shift)


RULES = {
    'touch': lambda r, A: r[:, 1] >= A,
    'overlap': lambda r, A: r[:, 2] >= A,
    'inside': lambda r, A: r[:, 3] >= A,
}


def run(tag, rule, A, persist=2, margin=3, eps=PUB, verbose=True, combo=None):
    out = []
    for ep in eps:
        f = f'{OUT}/feat_{tag}_p{ep}.npz'
        if not os.path.exists(f): continue
        z = np.load(f); rows = z['rows']; g = gt(ep)
        if combo:   # earliest of several (rule, A)
            cs = [first_hit(rows, lambda r, rr=rr, AA=AA: RULES[rr](r, AA), persist) for rr, AA in combo]
            cs = [c for c in cs if c is not None]; ca = min(cs) if cs else None
        else:
            ca = first_hit(rows, lambda r: RULES[rule](r, A), persist)
        if ca is None: ca = len(rows) + 1; miss = True
        else: miss = False
        cbc = ca - pairing_n(f'p{ep}', ca)
        err = cbc - g['pert']
        wb = window_bias(ep, cbc - margin); wo = window_bias(ep, g['pert'] - 1); w1 = window_bias(ep, g['on'] - 1)
        w15 = window_bias(ep, 14)
        out.append(dict(ep=ep, name=g['name'], ca=ca, cbc=cbc, pert=g['pert'], on=g['on'], err=err, miss=miss, det=wb, orc=wo,
                        cm1=w1, f15=w15))
        if verbose:
            print(f'p{ep:2d} {g["name"][:12]:12s} a{ca:3d} bc{cbc:5.1f} pert{g["pert"]:3d} on{g["on"]:3d} err{err:+5.1f}{" MISS" if miss else ""}'
                  f' | det n{wb["n"]:3d} {wb["dt"]:4.1f}mm {wb["dR"]:4.2f}d sh{wb["shift"]:4.1f} | orc n{wo["n"]:3d} {wo["dt"]:4.1f} {wo["dR"]:4.2f} sh{wo["shift"]:4.1f}'
                  f' | 1cm n{w1["n"]:3d} {w1["dt"]:4.1f} {w1["dR"]:4.2f} sh{w1["shift"]:4.1f} | f15 {w15["dt"]:4.1f} {w15["dR"]:4.2f} sh{w15["shift"]:4.1f}')
    return out


def summary(out, label=''):
    e = np.array([o['err'] for o in out]); late = e + 0 > -3   # window end (c-3) reaches the first perturbation
    def agg(key, f):
        v = np.array([o[key][f] for o in out]); return f'{np.median(v):.2f}/{np.mean(v):.2f}/{v.max():.2f}'
    print(f'{label} n={len(out)} err median {np.median(e):+.1f} [{e.min():+.0f},{e.max():+.0f}] p10/p90 {np.percentile(e, 10):+.1f}/{np.percentile(e, 90):+.1f}'
          f' | window reaches pert (err>-3+1): {int((e >= -2).sum())} | late (err>0): {int((e > 0).sum())} | empty windows: {sum(o["det"]["n"] == 0 for o in out)}'
          f' | win len median {np.median([o["det"]["n"] for o in out]):.0f} vs oracle {np.median([o["orc"]["n"] for o in out]):.0f}')
    for key in ('det', 'orc', 'cm1', 'f15'):
        print(f'   {key}: dt mm med/mean/max {agg(key, "dt")} | dR deg {agg(key, "dR")} | induced shift mm {agg(key, "shift")}')


if __name__ == '__main__':
    tag = sys.argv[1]
    kv = dict(a.split('=') for a in sys.argv[2:])
    rule = kv.get('rule', 'touch'); A = float(kv.get('A', 120)); persist = int(kv.get('persist', 2)); margin = float(kv.get('margin', 3))
    out = run(tag, rule, A, persist, margin)
    summary(out, f'{rule} A={A} persist={persist} margin={margin}')
