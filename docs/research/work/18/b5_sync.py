"""DIG 18 B5: a vs mono-pair (c) time offset from world-frame angular increments of the relocalised tracks (no GT).
usage: python b5_sync.py <reloc json>..."""
import sys, json, numpy as np
from scipy.spatial.transform import Rotation as R
for fn in sys.argv[1:]:
    fr = json.load(open(fn))["frames"]; tag = json.load(open(fn))["tag"]
    fr = [r for r in fr if r.get("inl_a", 0) >= 30 and r.get("inl_bc", 0) >= 30]
    Ra = np.array([np.array(r["a_from_world"])[:3, :3].T for r in fr]); Rc = np.array([np.array(r["c_from_world"])[:3, :3].T for r in fr])
    wa = np.array([R.from_matrix(Ra[t] @ Ra[t - 1].T).as_rotvec() for t in range(1, len(fr))])
    wc = np.array([R.from_matrix(Rc[t] @ Rc[t - 1].T).as_rotvec() for t in range(1, len(fr))])
    res = []
    for tau in np.arange(-3.0, 3.001, 0.05):
        i = np.arange(len(wc)); x = np.clip(i + tau, 0, len(wc) - 1); lo = np.floor(x).astype(int); hi = np.minimum(lo + 1, len(wc) - 1)
        f = (x - lo)[:, None]; wci = (1 - f) * wc[lo] + f * wc[hi]; m = slice(4, -4)
        res.append((float(np.degrees(np.sqrt(((wa[m] - wci[m]) ** 2).sum(1).mean()))), round(float(tau), 2)))
    b = min(res); z = [r for r in res if r[1] == 0][0]
    print(f"{tag}: a(t) best matches c(t{b[1]:+.2f} frames) = {b[1] * 50:+.0f} ms; rms {b[0]:.4f} deg/frame (tau=0: {z[0]:.4f}); "
          f"profile " + " ".join(f"{t:+.1f}:{v:.3f}" for v, t in sorted(res, key=lambda r: r[1]) if abs(t * 2 - round(t * 2)) < 1e-6))
