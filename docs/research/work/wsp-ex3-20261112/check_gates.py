"""Check gate fidelity of an edit on recorded traces: gate value vs the true excess computed from qpos.
Usage: python -I check_gates.py WORKSHOP_DIR EDIT_NPZ SPEC TRACE [TRACE ...]
SPEC: comma list of unit:joint_id:threshold:sign (sign +1 upper limit, -1 lower limit), kappa 10."""
import sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import net
C, edit, spec = sys.argv[1:4]
w = net.load(edit); ref = np.load(f'{C}/assets/reference.npz')['robot_target']
specs = [tuple(float(x) for x in s.split(':')) for s in spec.split(',')]
for tr in sys.argv[4:]:
    t = np.load(tr); obs = t['obs']; fr = t['frames'][:len(obs)]; qp = t['qpos'][:len(obs)]
    _, A = net.forward(w, obs, acts=True)
    for u, j, th, sg in specs:
        u, j = int(u), int(j); off = qp[:, j] - ref[fr, j]; true = 10 * np.maximum(0, sg * (off - th)); g = A['e0'][:, u]
        fire = fr[g > 0]
        c = np.corrcoef(g, true)[0, 1] if true.any() and g.any() else float('nan')
        print(f'{os.path.basename(tr):18s} unit {u:4d} joint {j:2d}: gate frames {int((g>0).sum()):4d} (true {int((true>0).sum()):4d}); '
              f'first {fire[0] if len(fire) else None}; corr {c:.3f}; max gate {g.max():.2f} true {true.max():.2f}; '
              f'mean |gate-true| {np.abs(g-true).mean():.3f}')
