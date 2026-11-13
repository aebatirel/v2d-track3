"""Offline model of the Joint6_R command loop under a virtual-limit gate (analysis only; no simulator).

Drive: the unedited policy's recorded Joint6_R pre-tanh z5(t) and stream rms(t) from a trace. The action pipeline is
simulation.py's process_action for this joint (input scale, 0.3/0.7 filter, clip, reference add, joint limits,
0.75 EMA, 0.012 rad max step), and q(t+1) = target(t) (the recorded J6_R tracking error is <= 0.04 rad).
Usage: python -I j6_loop_model.py WORKSHOP_DIR ACTOR TRACE THRESH K [K ...]
"""
import json, sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import net
C, actor, trace, th = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4])
Ks = [float(x) for x in sys.argv[5:]]
m = json.load(open(f'{C}/assets/model/runtime.json')); a = m['action']
s, sc, clip, ema, step = (a[k][5] for k in ('input_scale', 'scale', 'clip', 'final_target_ema', 'max_target_step'))
lo, hi = m['joint_lower'][5], m['joint_upper'][5]
ref = np.load(f'{C}/assets/reference.npz')['robot_target'][:, 5]
t = np.load(trace); obs = t['obs']; fr = t['frames'][:len(obs)]
w = net.load(actor); _, A = net.forward(w, obs, acts=True)
z, rms = A['mean'][:, 5], A['rms'][:, 0]
for K in Ks:
    filt = 0.0; tgt = None; q = obs[0, 19]; out = []
    for i in range(len(obs)):
        f = fr[i]; exc = max(0.0, (q - ref[f]) - th)
        zz = z[i] - K * exc * 1.2 / rms[i]
        act = np.tanh(zz); raw = act / ((1 - abs(act)) + abs(act) / s)
        filt = float(np.clip(0.3 * filt + 0.7 * raw * sc, -clip, clip))
        target = float(np.clip(ref[min(f + 1, len(ref) - 1)] + filt, lo, hi))
        prev = tgt if tgt is not None else ref[min(f + 1, len(ref) - 1)]
        target = ema * prev + (1 - ema) * target; target = float(np.clip(target, prev - step, prev + step))
        tgt = target; q = target; out.append((f, q - ref[min(f + 1, len(ref) - 1)], act))
    o = np.array(out)
    sel = [np.flatnonzero(o[:, 0] == f)[0] for f in (290, 305, 313, 321, 329, 337, 345, 352) if f in o[:, 0]]
    win = (o[:, 0] >= 300) & (o[:, 0] <= 352)
    flips = int((np.abs(np.diff(o[win, 2])) > 0.5).sum())
    print(f'K={K:5.1f}: offset at 290/305/313/321/329/337/345/352 =', np.round(o[sel, 1], 3),
          f'max offset 300-352 {o[win, 1].max():.3f}; action jumps >0.5 per frame: {flips}; action range {o[win,2].min():.2f}..{o[win,2].max():.2f}')
