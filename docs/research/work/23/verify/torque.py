import sys, importlib.util, numpy as np
from scipy.signal import savgol_filter
spec = importlib.util.spec_from_file_location("sens", sys.argv[3]); S = importlib.util.module_from_spec(spec)
sys.argv = sys.argv[:3]; spec.loader.exec_module(S)
dt = S.dt; I = 0.021
for win in (9, 7):
    print(f"-- SG window {win}, I={I} (hand 0.008-0.009 + armature 0.01), tau_max 45 Nm per child axis --")
    for k, d in [(25, 6.0), (50, 8.5), (100, 12.0), (200, 17.0), (1200, 60.0)]:
        tr_ax, tr_nm, fr, frn, n = 0, 0, 0, 0, 0; peak = 0
        clip_eff = min(1.0, 45.0 / k)
        for tr in S.TR:
            x = tr["x"]
            v = savgol_filter(x, win, 2, deriv=1, delta=dt, axis=0)
            w = savgol_filter(S.cm.ang_vel(tr["q"].copy()), win, 2, axis=0)
            wd = savgol_filter(w, win, 2, deriv=1, delta=dt, axis=0)
            mov = (np.linalg.norm(v, axis=1) > 0.05) | (np.linalg.norm(w, axis=1) > np.radians(30))
            if mov.sum() < 5: continue
            tau = (I * wd + d * w)[mov]
            ax = np.abs(tau).max(1); nm = np.linalg.norm(tau, axis=1)
            lim = k * clip_eff
            tr_ax += (ax > lim).any(); tr_nm += (nm > lim).any(); fr += (ax > lim).sum(); frn += (nm > lim).sum(); n += mov.sum()
            peak = max(peak, nm.max())
        print(f"k {k:5d} d {d:5.1f}: effective rot clip {clip_eff:.2f} rad (torque {k*clip_eff:.0f} Nm); tracks over (world max-axis / norm) {tr_ax}/{tr_nm}; frames {100*fr/n:.2f}% / {100*frn/n:.2f}%; peak required torque {peak:.1f} Nm")
