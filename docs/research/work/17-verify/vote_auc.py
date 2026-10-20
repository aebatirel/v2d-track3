"""Verifier (evaluation only): AUC of the emulated prior after applying the VOTED constant spin correction (vote = w2, +-15 deg
window, abstain rule winner>=4 and >=2x runner-up outside +-30; abstain -> prior unchanged), vs prior, per-frame-choice carry
(as in ev_carry2) and an oracle constant correction. Run with cwd work/17. usage: vote_auc.py npz ..."""
import sys, numpy as np
sys.path.insert(0, '/Users/aebatirel/Documents/Code/v2d-research/work/17'); sys.path.insert(0, '/Users/aebatirel/Documents/Code/v2d-research/work/17/c')
import ev17 as E, ev_carry2 as C, lib17 as L
from scipy.spatial.transform import Rotation as Rot
def dang(a, b): return np.abs(((np.asarray(a) - b + 180) % 360) - 180)
def vote(s, st, m):
    f = (st >= 2) & m; w = np.where(st[f] == 3, 2.0, 1.0); g = np.arange(0, 360, 15)
    sc = np.array([np.sum(w * (dang(s[f], a) <= 15.1)) for a in g]); k = int(np.argmax(sc)); wv = g[k]
    ru = max([sc[i] for i in range(len(g)) if dang(g[i], wv) > 30] or [0])
    return (None if not (sc[k] >= 4 and sc[k] >= 2 * ru) else wv)
for fn in sys.argv[1:]:
    z, ep = E.load(fn); T = int(z['T']); gt = L.load_gt(ep); n = str(z['objs'][0]); j = gt['names'].index(n); V = E.verts(n)
    base = fn.split('/')[-1]; sp = float(base.split('_s')[-1].split('.')[0].split('n')[0]); want = (360 - sp) % 360
    Rp, tp, st, s = z['Rp_0'][:T], z['tp_0'][:T], z['status_0'][:T], z['spin_0'][:T]
    ax = np.array([0, 0, 1.0]); out = []
    def auc(R, t):
        Ro, to = C.to_m(z, ep, R, t); return E.auc_add(E.errors(Ro, to, gt, j, V, T)[2])
    out.append(f'prior {auc(Rp, tp):.3f}')
    for lab, m in (('vote_all', np.ones(T, bool)), ('vote_t<40', np.arange(T) < 40)):
        wv = vote(s, st, m)
        if wv is None: out.append(f'{lab} ABSTAIN'); continue
        Rv = Rp @ Rot.from_rotvec(ax * np.radians(wv)).as_matrix(); out.append(f'{lab} {wv} {auc(Rv, tp):.3f}')
    Ro_ = Rp @ Rot.from_rotvec(ax * np.radians(want)).as_matrix(); out.append(f'oracle {auc(Ro_, tp):.3f}')
    Rk, tk, _ = C.carry(Rp, tp, z['R_0'][:T], z['t_0'][:T], st, 2, 0); out.append(f'carry {auc(Rk, tk):.3f}')
    print(base, n, ' | '.join(out), flush=True)
