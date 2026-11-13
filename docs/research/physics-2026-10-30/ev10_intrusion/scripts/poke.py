"""Does the carved beige cup poke OUT through the carved blue cup's wall? Beige union-surface samples (A pieces) that lie
below the blue rim but radially beyond the blue's outer surface at their height (blue outer radius per 2 mm band from
its piece surface), relative to the blue cavity axis. DIAGNOSTIC."""
import sys, glob, importlib.util, numpy as np
spec = importlib.util.spec_from_file_location('intrusion', '/home/user/v2d-track3/tools/intrusion.py'); I = importlib.util.module_from_spec(spec); spec.loader.exec_module(I)
names, O, P, Q, fps = I.load_ref(sys.argv[1]); Oi = I.inv_pose(O); REL = np.einsum('tij,tjk->tik', Oi[:, 0], O[:, 1])
UB = I.Union(sorted(glob.glob('/home/user/v2d-track3/meshes/carve/ev10/blue_cup/piece_*.obj')))
UG = I.Union(sorted(glob.glob('/home/user/v2d-track3/meshes/carve/ev10/beige_cup/piece_*.obj')))
cx, cy = 0.0026, 0.0041
SB = UB.surface(0.002); hb = -SB[:, 2]; rb = np.hypot(SB[:, 0] - cx, SB[:, 1] - cy)
edges = np.arange(hb.min(), hb.max() + 0.002, 0.002); rout = np.array([rb[(hb >= a) & (hb < a + 0.002)].max() if ((hb >= a) & (hb < a + 0.002)).any() else np.nan for a in edges])
rim = hb.max(); G = UG.surface(0.002)
print('blue outer radius at heights -85/-60/-30/0/30/60 mm:', [round(float(rout[np.argmin(abs(edges - h / 1000))]) * 1e3, 1) for h in (-85, -60, -30, 0, 30, 60)])
for f in (100, 105, 110, 117, 120, 140, 160):
    X = G @ REL[f, :3, :3].T + REL[f, :3, 3]; h = -X[:, 2]; r = np.hypot(X[:, 0] - cx, X[:, 1] - cy)
    k = np.clip(((h - edges[0]) / 0.002).astype(int), 0, len(edges) - 1); below = (h < rim) & (h >= edges[0])
    out = below & (r > rout[k] + 0.0005) & ~(UB.depth_lb(X) > 0)
    print(f, f'beige surface samples outside the blue outer wall below its rim: {out.sum()} of {below.sum()}; max radial excess {((r - rout[k])[out].max() * 1e3 if out.any() else 0):.1f} mm; their heights {np.round(np.percentile(h[out] * 1e3, [0, 50, 100]), 0) if out.any() else None} mm')
