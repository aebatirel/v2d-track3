import json, sys, numpy as np
G = json.load(open(sys.argv[1]))
R = [(0, 37), (38, 46), (47, 99), (100, 117), (118, 160)]
for k in ('A_carve_ev10', 'B_libv3_mesh'):
    meta, rows = G[k]; print(k, {a: round(v, 1) if isinstance(v, float) else v for a, v in meta.items()})
    fg = np.array([r['floor_gap_mm'] for r in rows]); vc = np.array([r['vclear_mm'] for r in rows]); lr = np.array([r['low_r_mm'] for r in rows])
    for a, b in R:
        s = slice(a, b + 1)
        print(f'  f{a}-{b}: floor_gap min/med/max {np.nanmin(fg[s]):.1f}/{np.nanmedian(fg[s]):.1f}/{np.nanmax(fg[s]):.1f}  vclear min/med {np.nanmin(vc[s]):.1f}/{np.nanmedian(vc[s]):.1f}  frames vclear<0: {(vc[s] < 0).sum()}  low_r med {np.nanmedian(lr[s]):.1f}')
X = G['B_libv3_mesh_exact_intrusion']['rows']
for a, b in R:
    s = X[a:b + 1]
    v1 = np.array([r['beige_in_blue_vol_cm3'] for r in s]); d1 = np.array([r['beige_in_blue_depth_max_mm'] for r in s])
    v2 = np.array([r['blue_in_beige_vol_cm3'] for r in s]); d2 = np.array([r['blue_in_beige_depth_max_mm'] for r in s])
    m1 = np.array([r['beige_in_blue_depth_med_mm'] for r in s])
    print(f'Bmesh f{a}-{b}: beige-in-blue frames {(v1>0).sum()} vol max/med {v1.max():.1f}/{np.median(v1[v1>0]) if (v1>0).any() else 0:.1f} depth max {d1.max():.1f} (per-frame med depth med {np.median(m1[v1>0]) if (v1>0).any() else 0:.1f}) | blue-in-beige frames {(v2>0).sum()} vol max {v2.max():.1f} depth max {d2.max():.1f}')
for f in (0, 37, 38, 42, 46, 50, 60, 80, 95, 100, 105, 110, 117, 120, 130, 140, 150, 160):
    a, b = G['A_carve_ev10'][1][f], G['B_libv3_mesh'][1][f]
    print(f, 'A gap', round(a['floor_gap_mm'], 1), 'vclr', round(a['vclear_mm'], 1), '| B gap', round(b['floor_gap_mm'], 1), 'vclr', round(b['vclear_mm'], 1))
