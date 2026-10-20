"""Stage C (resume): saved replacement for the unsaved inline 'carry' evaluator of C5/C6. EVALUATION ONLY (reads GT).
For a hybrid-emulation run (PRIOR=gt), the marker correction at fix frames (status >= SMIN) is
   rotation  Rc = Rp^T R   (body frame; a spin error lives here)
   translation dt = t - tp (world frame)
and is interpolated between fix frames (slerp / linear; held constant before the first and after the last fix), optionally
smoothed by a running median over +-K fixes (rejects isolated wrong fixes), then applied to the prior at every frame:
   R' = Rp Rc(t), t' = tp + dt(t).
This is OFFLINE smoothing (uses later fixes), which is legal for the challenge (whole video is available at inference).
Reports AUC (kit thresholds 1-9 cm, MODE=reg cameras, GT at t+SH) for prior / fused / carry variants, the frame-0 ADD,
and the scorer-style slot-0 frame-0 alignment.
usage: [SMIN=2] [K=0] c/ev_carry2.py c/trk_<ep><tag>.npz [...]"""
import sys, os, numpy as np
from scipy.spatial.transform import Rotation as Rot, Slerp
sys.path.insert(0, '/Users/aebatirel/Documents/Code/v2d-research/work/17'); sys.path.insert(0, '/Users/aebatirel/Documents/Code/v2d-research/work/17/c')
import ev17 as E, lib17 as L, det17lib as D
SMIN = int(os.environ.get('SMIN', 2)); K = int(os.environ.get('K', 0))
def carry(Rp, tp, R, t, stt, smin=SMIN, k=K):
    T = len(Rp); fx = np.where(stt >= smin)[0]
    if len(fx) == 0: return Rp.copy(), tp.copy(), 0
    Rc = np.einsum('tji,tjk->tik', Rp[fx], R[fx]); dt = t[fx] - tp[fx]
    if k > 0:   # running median over +-k fixes (translation per axis; rotation by chordal L1-ish: medoid of rotvecs)
        rv = Rot.from_matrix(Rc).as_rotvec(); rv2, dt2 = rv.copy(), dt.copy()
        for i in range(len(fx)):
            a, b = max(0, i - k), min(len(fx), i + k + 1); W = rv[a:b]
            j = np.argmin([np.sum(np.linalg.norm(Rot.from_rotvec(W).inv().as_matrix() @ Rot.from_rotvec(w).as_matrix() - np.eye(3), axis=(1, 2))) for w in W])
            rv2[i] = W[j]; dt2[i] = np.median(dt[a:b], axis=0)
        Rc, dt = Rot.from_rotvec(rv2).as_matrix(), dt2
    tt = np.clip(np.arange(T), fx[0], fx[-1]).astype(float)
    if len(fx) == 1: Ri = np.repeat(Rc, T, 0); di = np.repeat(dt, T, 0)
    else:
        Ri = Slerp(fx.astype(float), Rot.from_matrix(Rc))(tt).as_matrix(); di = np.stack([np.interp(tt, fx, dt[:, a]) for a in range(3)], 1)
    return np.einsum('tij,tjk->tik', Rp, Ri), tp + di, len(fx)
def to_m(z, ep, R, t):
    import json
    Treg = np.array(json.load(open(f'out/reg2_{ep}.json'))['Treg']); return np.einsum('ij,tjk->tik', Treg[:3, :3], R), t @ Treg[:3, :3].T + Treg[:3, 3]
if __name__ == "__main__":
  for fn in sys.argv[1:]:
      z, ep = E.load(fn); T = int(z['T']); gt = L.load_gt(ep); objs = list(z['objs'])
      if not ('PRIOR' in z.files and str(z['PRIOR']) == 'gt'): print(fn, 'not a hybrid run'); continue
      poses = {}
      for i, n in enumerate(objs):
          stt = z[f'status_{i}'][:T]; Rp, tp, R, t = z[f'Rp_{i}'][:T], z[f'tp_{i}'][:T], z[f'R_{i}'][:T], z[f't_{i}'][:T]
          Rk, tk, nfx = carry(Rp, tp, R, t, stt); poses[n] = {'prior': (Rp, tp), 'fused': (R, t), 'carry': (Rk, tk)}
      line = f'{fn} SMIN {SMIN} K {K}:'
      for i, n in enumerate(objs):
          j = gt['names'].index(n); V = E.verts(n); out = []
          for lab in ('prior', 'fused', 'carry'):
              Ro, to = to_m(z, ep, *poses[n][lab]); et, er, ea = E.errors(Ro, to, gt, j, V, T)
              out.append(f'{lab} {E.auc_add(ea):.3f} (f0 ADD {ea[0]:.0f} r {er[0]:.0f})')
          line += f'\n  {n}: ' + ' | '.join(out) + f' | fix frames {int(np.sum(z[f"status_{i}"][:T] >= SMIN))}'
      if gt['names'][0] == objs[0]:   # scorer-style: one rigid transform from slot 0 at frame 0
          Rg0, tg0 = D.gt_interp(gt, 0, 0 + E.SH); sc = []
          for lab in ('prior', 'fused', 'carry'):
              R0, t0 = to_m(z, ep, *poses[objs[0]][lab]); RA = Rg0 @ R0[0].T; tA = tg0 - RA @ t0[0]; a = []
              for n in objs:
                  j = gt['names'].index(n); Ro, to = to_m(z, ep, *poses[n][lab]); Ro = np.einsum('ij,tjk->tik', RA, Ro); to = to @ RA.T + tA
                  a.append(E.auc_add(E.errors(Ro, to, gt, j, E.verts(n), T)[2]))
              sc.append(f'{lab} ' + ' '.join(f'{x:.3f}' for x in a) + f' mean {np.mean(a):.3f}')
          line += '\n  SCORER-STYLE: ' + ' | '.join(sc)
      print(line, flush=True)
