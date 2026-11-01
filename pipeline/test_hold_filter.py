"""Unit checks of pipeline/hold_filter.py filter_object (2026-11-01; numpy/scipy only). Run: python -I test_hold_filter.py"""
import os, sys, types
import numpy as np
from scipy.spatial.transform import Rotation as R
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hold_filter as HF  # noqa: E402

a = types.SimpleNamespace(win=15, hampel=3.0, blend=4, rest='freeze', rest_win=10, flag_cm=3.0, glitch_cm=5.0)
T = 120; rng = np.random.default_rng(0)
# wrist: rests until 30, carries along x 30..90, rests after; object rigidly 6 cm in front of the wrist while held
wp = np.zeros((T, 3)); wp[30:90, 0] = np.linspace(0, 0.3, 60); wp[90:, 0] = 0.3
wr = R.from_rotvec(np.outer(np.linspace(0, 0.5, T), [0, 0, 1.0]))
off = np.array([0.06, 0, 0]); OP = wp + wr.apply(off); Rin = wr * R.from_rotvec([0.1, 0, 0])
OP[:30] = OP[30]; OP[90:] = OP[89]; Rq = Rin.as_quat(); Rq[:30] = Rq[30]; Rq[90:] = Rq[89]; Rin = R.from_quat(Rq)
true_P = OP.copy()
noisy = OP + rng.normal(size=OP.shape) * 0.002           # 2 mm perception noise everywhere
noisy[50:68] += np.array([0.15, 0, 0])                  # an 18-frame 15 cm glitch inside the hold (eval-32-like)
noisy[105:, 1] += np.linspace(0, 0.04, T - 105)          # slow 4 cm perception drift after the object has settled (no hand)
P, q, inf = HF.filter_object(noisy, Rin, [('left', 25, 95)], {'left': (wp, wr), 'right': (wp + 5, wr)}, a)
err_in = np.linalg.norm(noisy - true_P, axis=1); err_out = np.linalg.norm(P - true_P, axis=1)
assert err_out[50:68].max() < 0.01, err_out[50:68]; print(f'PASS in-hold glitch removed: max err {100 * err_in[50:68].max():.1f} -> {100 * err_out[50:68].max():.2f} cm')
assert err_out[30:90].mean() < 0.6 * err_in[30:90].mean(); print(f'PASS hold noise reduced: mean {100 * err_in[30:90].mean():.2f} -> {100 * err_out[30:90].mean():.2f} cm')
assert inf['rest'][-1]['flag'] and err_out[100:].max() < 0.01, (inf['rest'], err_out[100:].max())
print(f'PASS post-release drift frozen and flagged: {100 * err_in[100:].max():.1f} -> {100 * err_out[100:].max():.2f} cm')
assert np.allclose(np.linalg.norm(q, axis=1), 1, atol=1e-9); print('PASS unit quaternions')

# ---- glitch mode (default): minimal change -------------------------------------------------------------------------
g = types.SimpleNamespace(gwin=61, glitch_cm=5.0, vmax_cms=150.0, fps=20.0, rest='freeze', rest_win=10, rest_cm=1.5, flag_cm=3.0)
OPc = OP.copy()                                          # a genuine carry (x 0 -> 0.3 m over f30-90), no glitch
P, q, inf = HF.repair_object(OPc, Rin, [('left', 25, 95)], {'left': (wp, wr), 'right': (wp + 5, wr)}, g)
assert inf['glitch_frames'] == 0 and np.abs(P[25:95] - OPc[25:95]).max() < 1e-12, inf
print('PASS glitch mode leaves a genuine carry untouched')
OPg = OPc.copy(); OPg[50:68] += np.array([0.0, 0.15, 0])   # eval-32-like: 18 frames 15 cm sideways inside the hold, then back
P, q, inf = HF.repair_object(OPg, Rin, [('left', 25, 95)], {'left': (wp, wr), 'right': (wp + 5, wr)}, g)
e = np.linalg.norm(P - OPc, axis=1)
assert e[50:68].max() < 0.005 and np.abs(P[:48] - OPc[:48]).max() < 1e-12, (e[45:70], inf['glitch_runs'])
print(f"PASS glitch mode removes the 18-frame 15 cm swing (max err {100 * e[50:68].max():.2f} cm), runs {inf['glitch_runs']}")
OPr = OPc.copy(); OPr[100:, 1] += rng.normal(size=T - 100) * 0.003   # rest jitter (3 mm) -> frozen
OPr2 = OPc.copy(); OPr2[100:, 1] += np.linspace(0, 0.06, T - 100)     # 6 cm no-hand motion -> flagged, kept
P, q, inf = HF.repair_object(OPr, Rin, [('left', 25, 95)], {'left': (wp, wr), 'right': (wp + 5, wr)}, g)
assert inf['rest'][-1]['frozen'] and np.ptp(P[100:], 0).max() < 1e-12; print('PASS rest jitter frozen')
P, q, inf = HF.repair_object(OPr2, Rin, [('left', 25, 95)], {'left': (wp, wr), 'right': (wp + 5, wr)}, g)
assert inf['rest'][-1]['flag'] and not inf['rest'][-1]['frozen'] and np.abs(P[100:] - OPr2[100:]).max() < 1e-12, inf['rest']
print('PASS large no-hand motion flagged and kept')
