"""Stage C (resume), evaluation only: spin hypothesis chosen by the tracker (E3 runs) vs the correct correction
(360 - SPIN), on fix frames (status >= 2) and per segment (rest/held/carried from GT kinematics, seg17).
usage: c/spin_stats.py c/trk_<ep>_s<deg>.npz ..."""
import sys, numpy as np
sys.path.insert(0, '/Users/aebatirel/Documents/Code/v2d-research/work/17')
import lib17 as L, seg17
for fn in sys.argv[1:]:
    z = np.load(fn); ep = int(fn.split('_')[1]); sp = float(fn.split('_s')[-1].split('.')[0].split('n')[0]); T = int(z['T'])
    gt = L.load_gt(ep); seg = seg17.segments(gt)[0]; objs = list(z['objs'])
    for i, n in enumerate(objs):
        if f'spin_{i}' not in z.files: continue
        s = z[f'spin_{i}'][:T]; st = z[f'status_{i}'][:T]; sg = seg[:T, gt['names'].index(n)]; want = (360 - sp) % 360
        ok = np.abs(((s - want + 180) % 360) - 180) <= 15; fx = st >= 2
        first = np.where(fx)[0]; f0 = first[0] if len(first) else -1
        txt = ' '.join(f'{lab} {int((ok & fx & (sg == k)).sum())}/{int((fx & (sg == k)).sum())}' for k, lab in enumerate(('rest', 'held', 'carried')))
        vals, cnt = np.unique(s[fx], return_counts=True)
        print(f'{fn} {n}: correct spin on fix frames {int((ok & fx).sum())}/{int(fx.sum())} ({txt}); first fix t={f0} correct={bool(ok[f0]) if f0 >= 0 else None}; chosen values ' + ', '.join(f'{v:.0f}:{c}' for v, c in zip(vals, cnt)))
