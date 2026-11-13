"""Beige (A pieces) radius vs carved-blue cavity radius per height at selected frames (blue frame, blue cavity axis). DIAGNOSTIC."""
import sys, glob, importlib.util, numpy as np
spec = importlib.util.spec_from_file_location('intrusion', '/home/user/v2d-track3/tools/intrusion.py'); I = importlib.util.module_from_spec(spec); spec.loader.exec_module(I)
names, O, P, Q, fps = I.load_ref(sys.argv[1]); Oi = I.inv_pose(O); REL = np.einsum('tij,tjk->tik', Oi[:, 0], O[:, 1])
UB = I.Union(sorted(glob.glob('/home/user/v2d-track3/meshes/carve/ev10/blue_cup/piece_*.obj')))
UG = I.Union(sorted(glob.glob('/home/user/v2d-track3/meshes/carve/ev10/beige_cup/piece_*.obj')))
cx, cy = 0.0026, 0.0041; G = UG.surface(0.002)
def cavity_r(h):          # smallest radius (any angle) at height h where a ray from the axis outward meets a blue piece
    ang = np.linspace(0, 2 * np.pi, 72, endpoint=False); rs = np.arange(0, 0.06, 0.0005)
    X = np.stack([np.c_[cx + rs * np.cos(a), cy + rs * np.sin(a), np.full(len(rs), -h)] for a in ang])
    ins = (UB.depth_lb(X.reshape(-1, 3)) > 0).reshape(len(ang), len(rs))
    first = np.array([rs[np.argmax(row)] if row.any() else np.nan for row in ins]); return np.nanmedian(first), np.nanmin(first)
for f in (110, 140):
    X = G @ REL[f, :3, :3].T + REL[f, :3, 3]; h = -X[:, 2]; r = np.hypot(X[:, 0] - cx, X[:, 1] - cy)
    print('frame', f, 'beige lowest point h', round(h.min() * 1e3, 1), 'mm')
    for hb in (-80, -70, -60, -50, -40, -20, 0, 20, 40):
        k = (h >= hb / 1000 - 0.002) & (h < hb / 1000 + 0.002)
        if k.any():
            cm, cmin = cavity_r(hb / 1000)
            print(f'  h {hb:+d} mm: beige outer r median/max {np.median(np.sort(r[k])[-max(1, k.sum()//4):])*1e3:.1f}/{r[k].max()*1e3:.1f} mm | blue cavity r median/min {cm*1e3:.1f}/{cmin*1e3:.1f} mm')
