"""Hybrid emulation summary (analysis only). For PRIOR=gt tracker runs: AUC of ADD (kit thresholds) per object for
 prior-only (emulated model-based tracker), fused (marker fix where status >= MINST, else prior) and carry (marker
 correction C = prior^-1 * fix interpolated between fix frames and held at the ends, applied to the prior everywhere).
usage: [MINST=2] c/ev_carry.py c/trk_<ep><tag>.npz ..."""
import sys, os, numpy as np
from scipy.spatial.transform import Rotation as Rot, Slerp
sys.path.insert(0, '/Users/aebatirel/Documents/Code/v2d-research/work/17'); sys.path.insert(0, '/Users/aebatirel/Documents/Code/v2d-research/work/17/c')
import lib17 as L, seg17
from ev17 import load, to_mocap, errors, auc_add, verts
MINST = int(os.environ.get('MINST', 2)); SEG = ['rest', 'held', 'carried']
for fn in sys.argv[1:]:
    z, ep = load(fn); T = int(z['T']); gt = L.load_gt(ep); seg = seg17.segments(gt)[0]
    print(f'{fn} PN {z["PN"].tolist()} MINST {MINST}')
    for i, n in enumerate(z['objs']):
        j = gt['names'].index(n); V = verts(n); st = z[f'status_{i}'][:T]; fix = np.flatnonzero(st >= MINST)
        Rp, tp = to_mocap(z, ep, i, T, 'p'); Rf, tf = to_mocap(z, ep, i, T, '')
        Rf = np.where((st >= MINST)[:, None, None], Rf, Rp); tf = np.where((st >= MINST)[:, None], tf, tp)
        if len(fix) >= 1:
            C = Rot.from_matrix(np.einsum('tji,tjk->tik', Rp[fix], Rf[fix])); d = tf[fix] - tp[fix]
            if len(fix) >= 2:
                tt = np.clip(np.arange(T), fix[0], fix[-1]); Ci = Slerp(fix, C)(tt).as_matrix()
                di = np.stack([np.interp(tt, fix, d[:, k]) for k in range(3)], 1)
            else: Ci = np.repeat(C.as_matrix(), T, 0); di = np.repeat(d, T, 0)
            Rc = np.einsum('tij,tjk->tik', Rp, Ci); tc = tp + di
        else: Rc, tc = Rp, tp
        out = {}
        for lab, (R_, t_) in (('prior', (Rp, tp)), ('fused', (Rf, tf)), ('carry', (Rc, tc))):
            et, er, ea = errors(R_, t_, gt, j, V, T); out[lab] = (auc_add(ea), np.median(ea), np.median(er), ea)
        line = f'  {n:18s} fix frac {np.mean(st >= MINST):.2f} | ' + ' | '.join(f'{k} AUC {v[0]:.3f} ADD {v[1]:.1f} mm rot {v[2]:.1f} deg' for k, v in out.items())
        print(line)
        for s in range(3):
            m = seg[:T, j] == s
            if m.sum() >= 5: print(f'      {SEG[s]:8s} n{m.sum():4d} fix {np.mean(st[m] >= MINST):.2f} ADD-AUC prior {auc_add(out["prior"][3][m]):.3f} fused {auc_add(out["fused"][3][m]):.3f} carry {auc_add(out["carry"][3][m]):.3f}')
