"""Radial geometry of carved cup pieces (DIAGNOSTIC): per height h = -z (blue/beige file frame) the union's inner radius
(first hit along rays from the axis) and outer radius (last inside sample), median/min/max over 72 azimuths; also the
library_v3 mesh's outer radius (max r of its vertices per height bin). Usage: geom.py CARVE_DIR OUT.json"""
import sys, glob, json, importlib.util, numpy as np, trimesh
spec = importlib.util.spec_from_file_location('intrusion', '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/ev10w/tree/tools/intrusion.py')
I = importlib.util.module_from_spec(spec); spec.loader.exec_module(I)
C, outp = sys.argv[1:3]
AX = {'blue_cup': (0.0026, 0.0041), 'beige_cup': None}
res = {}
for n in ('blue_cup', 'beige_cup'):
    U = I.Union(sorted(glob.glob(f'{C}/{n}/piece_*.obj')))
    if AX[n] is None:      # beige: axis = centroid of the pieces' vertices in x,y (lathe, near-vertical axis)
        cx, cy = U.V[:, 0].mean(), U.V[:, 1].mean()
    else:
        cx, cy = AX[n]
    ang = np.linspace(0, 2 * np.pi, 72, endpoint=False); rs = np.arange(0, 0.065, 0.00025)
    rows = []
    for hb in np.arange(-0.096, 0.090, 0.002):
        X = np.stack([np.c_[cx + rs * np.cos(a), cy + rs * np.sin(a), np.full(len(rs), -hb)] for a in ang])
        ins = (U.depth_lb(X.reshape(-1, 3)) > 0).reshape(len(ang), len(rs))
        if not ins.any():
            continue
        first = np.array([rs[np.argmax(r)] if r.any() else np.nan for r in ins])
        last = np.array([rs[len(r) - 1 - np.argmax(r[::-1])] if r.any() else np.nan for r in ins])
        solid_axis = bool(ins[:, 0].all())
        rows.append(dict(h_mm=round(hb * 1e3, 1), inner_med=float(np.nanmedian(first) * 1e3), inner_min=float(np.nanmin(first) * 1e3),
                         inner_max=float(np.nanmax(first) * 1e3), outer_med=float(np.nanmedian(last) * 1e3), outer_min=float(np.nanmin(last) * 1e3),
                         outer_max=float(np.nanmax(last) * 1e3), solid_at_axis=solid_axis))
    res[n] = dict(axis_xy_mm=[cx * 1e3, cy * 1e3], rows=rows, vol_hull_cm3=float(sum(v[0] for v in U.vol) * 1e6), pieces=len(U.H))
for n in ('blue_cup', 'beige_cup'):
    m = trimesh.load(f'/home/user/v2d-track3/meshes/library_v3/{n}.glb', force='mesh'); V = np.asarray(m.vertices)
    cx, cy = res[n]['axis_xy_mm'][0] / 1e3, res[n]['axis_xy_mm'][1] / 1e3; h = -V[:, 2]; r = np.hypot(V[:, 0] - cx, V[:, 1] - cy)
    res[n]['libv3_outer'] = [dict(h_mm=round(hb * 1e3, 1), r_max=float(r[(h >= hb - 1e-3) & (h < hb + 1e-3)].max() * 1e3) if ((h >= hb - 1e-3) & (h < hb + 1e-3)).any() else None)
                             for hb in np.arange(-0.096, 0.090, 0.004)]
json.dump(res, open(outp, 'w'), indent=1)
for n in res:
    print(n, 'axis', np.round(res[n]['axis_xy_mm'], 2), 'pieces', res[n]['pieces'])
    for r in res[n]['rows'][::3]:
        print(f"  h {r['h_mm']:+6.1f}  inner med/min {r['inner_med']:5.1f}/{r['inner_min']:5.1f}  outer med/min/max {r['outer_med']:5.1f}/{r['outer_min']:5.1f}/{r['outer_max']:5.1f} solid_axis {r['solid_at_axis']}")
