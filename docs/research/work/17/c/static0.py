"""Stage C (resume), evaluation of a slot-0 frame-0 estimator: pool all marker fixes of the slot-0 object over its
static prefix instead of trusting the single fix at t = 0. Prefix = frames before the object's first non-rest frame
(seg17 from GT: DIAGNOSTIC stand-in for an automatic first-contact detector, note 15). Pooled pose = rotation medoid
(chordal) and per-axis median translation of the fused poses with status >= SMIN in the prefix (VO frame; the object is
static, the VO camera carries the head motion). The pooled pose replaces slot 0's poses over the prefix; the rest is the
carry trajectory (c/ev_carry2.py). Reports f0 ADD and scorer-style AUC (one rigid transform from slot 0 at frame 0).
usage: [SMIN=2] [K=0] c/static0.py c/trk_<ep><tag>.npz ..."""
import sys, os, numpy as np
sys.path.insert(0, '/Users/aebatirel/Documents/Code/v2d-research/work/17'); sys.path.insert(0, '/Users/aebatirel/Documents/Code/v2d-research/work/17/c')
os.environ.setdefault('K', '0')
import ev17 as E, lib17 as L, det17lib as D, seg17
from ev_carry2 import carry, to_m
SMIN = int(os.environ.get('SMIN', 2))
def medoid(Rs):
    d = [np.sum(np.linalg.norm(np.einsum('ij,tjk->tik', A.T, Rs) - np.eye(3), axis=(1, 2))) for A in Rs]; return Rs[int(np.argmin(d))]
for fn in sys.argv[1:]:
    z, ep = E.load(fn); T = int(z['T']); gt = L.load_gt(ep); objs = list(z['objs']); seg = seg17.segments(gt)[0]
    if gt['names'][0] != objs[0] or str(z['PRIOR']) != 'gt': continue
    j0 = 0; nr = np.where(seg[:T, j0] != 0)[0]; P = int(nr[0]) if len(nr) else T
    st = z['status_0'][:T]; fx = np.where(st[:P] >= SMIN)[0]
    tr = {}
    for i, n in enumerate(objs):
        tr[n] = carry(z[f'Rp_{i}'][:T], z[f'tp_{i}'][:T], z[f'R_{i}'][:T], z[f't_{i}'][:T], z[f'status_{i}'][:T], 2, 0)[:2]
    Rk, tk = tr[objs[0]][0].copy(), tr[objs[0]][1].copy(); f0c = None
    if len(fx) >= 1 and P >= 1:
        Rs = z['R_0'][fx]; ts = z['t_0'][fx]; Rk[:P] = medoid(Rs); tk[:P] = np.median(ts, 0)
    Rg0, tg0 = D.gt_interp(gt, 0, E.SH); res = []
    for lab, (R0s, t0s) in (('carry', tr[objs[0]]), ('pooled', (Rk, tk))):
        R0, t0 = to_m(z, ep, R0s, t0s); V0 = E.verts(objs[0])
        f0add = np.linalg.norm(V0 @ (R0[0] - Rg0).T + (t0[0] - tg0), axis=1).mean() * 1000
        RA = Rg0 @ R0[0].T; tA = tg0 - RA @ t0[0]; a = []
        for i, n in enumerate(objs):
            j = gt['names'].index(n); Rn, tn = (R0s, t0s) if i == 0 else tr[n]; Ro, to = to_m(z, ep, Rn, tn)
            Ro = np.einsum('ij,tjk->tik', RA, Ro); to = to @ RA.T + tA; a.append(E.auc_add(E.errors(Ro, to, gt, j, E.verts(n), T)[2]))
        res.append(f'{lab}: f0 ADD {f0add:.1f} mm, scorer-style ' + ' '.join(f'{x:.3f}' for x in a) + f' mean {np.mean(a):.3f}')
    print(f'{fn} slot0 {objs[0]} static prefix {P} frames, fixes used {len(fx)} (SMIN {SMIN}) | ' + ' | '.join(res), flush=True)
