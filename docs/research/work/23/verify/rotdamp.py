"""Critic check: ball-wrist rotation residual vs passive damping (diagnostic on public GT only)."""
import glob, sys, importlib.util
import numpy as np
from scipy.signal import savgol_filter
spec = importlib.util.spec_from_file_location("cm", "/home/user/v2d-track3/docs/research/work/23/carry_model.py")
cm = importlib.util.module_from_spec(spec); spec.loader.exec_module(cm)
data = sys.argv[1]
tracks = []
for f in sorted(glob.glob(f"{data}/episode_*.parquet")):
    ep, names, pos, quat = cm.load(f)
    for j, nm in enumerate(names):
        x = cm.fill(pos[:, j]); q = cm.fill(quat[:, j])
        if not np.all(np.isfinite(x)) or len(x) < 15: continue
        for win in (9, 7):
            v = savgol_filter(x, win, 2, deriv=1, delta=cm.dt, axis=0)
            w = savgol_filter(cm.ang_vel(q), win, 2, axis=0)
            wd = savgol_filter(w, win, 2, deriv=1, delta=cm.dt, axis=0)
            mov = (np.linalg.norm(v, axis=1) > 0.05) | (np.linalg.norm(w, axis=1) > np.radians(30))
            if mov.sum() < 5: continue
            tracks.append((win, ep, nm, w[mov], wd[mov]))
print("n tracks per window:", {k: sum(1 for t in tracks if t[0] == k) for k in (9, 7)})
for I in (0.012, 0.025):
    for k, d, tau in [(25, 6, 45), (25, 3, 45), (25, 1.5, 45), (100, 12, 45), (100, 12, 100), (100, 4, 45), (100, 4, 100)]:
        zeta = d / (2 * np.sqrt(k * I))
        clip = min(1.0, tau / k)
        for win in (9, 7):
            sat_tracks, fr, nfr, p95 = 0, 0, 0, []
            for (wn, ep, nm, w, wd) in tracks:
                if wn != win: continue
                r = np.abs((I * wd + d * w) / k).max(1)
                s = r > clip
                sat_tracks += int(s.any()); fr += s.sum(); nfr += len(s); p95.append(np.percentile(r, 95))
            print(f"I={I} k={k} d={d} tau_max={tau} zeta={zeta:.2f} lag={d/k:.3f}s eff_clip={clip:.2f} SG{win}: "
                  f"sat {sat_tracks}/27, frames {100*fr/nfr:.2f}%, median p95 {np.median(p95):.3f} rad")
