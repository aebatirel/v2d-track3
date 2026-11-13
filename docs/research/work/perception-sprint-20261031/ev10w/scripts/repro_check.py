"""Per-frame comparison of my ev10 reproduction with their committed per-frame CSV (2a11301 out/ev10_intrusion_per_frame.csv)."""
import sys, csv, json, numpy as np
mine = json.load(open(sys.argv[1])); Z = np.load(sys.argv[2]); rows = list(csv.DictReader(open(sys.argv[3])))
names = [str(x) for x in Z['objects']]; ib, ig = names.index('blue_cup'), names.index('beige_cup'); T = len(rows)
vol = {ib: np.zeros(T), ig: np.zeros(T)}
for i in range(len(Z['fp_frame'])):
    vol[int(Z['fp_target'][i])][int(Z['fp_frame'][i])] = float(Z['intr_vol_m3'][i]) * 1e6
f = lambda k: np.array([float(r[k]) if r[k] not in ('', 'nan') else np.nan for r in rows])
d_bb = np.abs(vol[ib] - f('A_beige_in_blue_cm3')).max(); d_gb = np.abs(vol[ig] - f('A_blue_in_beige_cm3')).max()
g_mine = np.array([np.nan if v is None else v for v in mine['per_frame']['floor_gap_mm']]); g_th = f('A_floor_gap_mm')
both = np.isfinite(g_mine) & np.isfinite(g_th)
res = dict(frames=T, max_abs_diff_beige_in_blue_cm3=float(d_bb), max_abs_diff_blue_in_beige_cm3=float(d_gb),
           floor_gap_nan_pattern_equal=bool((np.isfinite(g_mine) == np.isfinite(g_th)).all()),
           floor_gap_max_abs_diff_mm=float(np.abs(g_mine[both] - g_th[both]).max()),
           depth_max_theirs_A_mm=float(np.nanmax(np.maximum(f('A_beige_in_blue_dmax_mm'), f('A_blue_in_beige_dmax_mm')))),
           depth_max_mine_mm=float(max(mine['per_frame']['depth_mm'])))
print(json.dumps(res)); json.dump(res, open(sys.argv[4], 'w'), indent=1)
