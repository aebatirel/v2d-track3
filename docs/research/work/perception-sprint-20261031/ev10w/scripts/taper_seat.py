"""Taper of both carved cups and the coaxial seat line on OUR reference (DIAGNOSTIC, GT-free).
Taper: outer-radius slope of the lathe profiles (blue: as carved, cavity = r_out - wall; beige: r_out - shrink), fitted
by least squares over height bands, as dr/ds and angle atan(dr/ds); expected sink per mm of radial widening =
1 / (slope_beige_outer) if the guest rests on a tapered seat (dr/tan(taper)).
Seat line: per frame f100-160 the beige carve is moved coaxial with the blue lathe axis (tilt and lateral offset
removed, same height along the axis, m2.py's construction); excess(s) = beige outer radius (max of surface samples in a
2 mm bin) - blue cavity radius. The seat = the height of the largest excess above the beige's bottom 8 mm (the base-ring
contact). Reported per frame and as the median over f100-160 (the build rule's seat line) and f118-160.
Usage: taper_seat.py REF CARVE_DIR BLUE_PROFILE.npz BEIGE_PROFILE.npz BEIGE_SHRINK_M WALL_M OUT.json"""
import sys, glob, json, importlib.util
import numpy as np
spec = importlib.util.spec_from_file_location('intrusion', '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/ev10w/tree/tools/intrusion.py')
I = importlib.util.module_from_spec(spec); spec.loader.exec_module(I)
ref, carve, pb, pg, shrink, wall, outp = sys.argv[1:8]; shrink, wall = float(shrink), float(wall)
B, G = np.load(pb), np.load(pg)
c0b, db, e1b, e2b = (np.asarray(B[k], float) for k in ('c0', 'd', 'e1', 'e2')); c0g, dg = np.asarray(G['c0'], float), np.asarray(G['d'], float)
hb, rb = np.asarray(B['prof_h'], float), np.asarray(B['prof_r'], float); o = np.argsort(hb); hb, rb = hb[o], rb[o]
hg, rg = np.asarray(G['prof_h'], float), np.asarray(G['prof_r'], float) - shrink; o = np.argsort(hg); hg, rg = hg[o], rg[o]
s_floor = float(B['hb_plane']) - wall
hd = lambda s: -(c0b[2] + s * db[2]) * 1e3                       # blue s -> diagnostic height (mm)
s_of_hd = lambda h: (-h / 1e3 - c0b[2]) / db[2]


def slope(h, r, lo, hi):
    k = (h >= lo) & (h <= hi); A = np.c_[h[k], np.ones(k.sum())]; m = np.linalg.lstsq(A, r[k], rcond=None)[0][0]
    return dict(band_s_mm=[round(lo * 1e3, 1), round(hi * 1e3, 1)], dr_ds=round(float(m), 4), taper_deg=round(float(np.degrees(np.arctan(abs(m)))), 2))


# blue: base at high s, mouth at low s -> radius decreases toward the base: dr/ds < 0. Report |slope| per band.
tap = dict(blue_outer=dict(full=slope(hb, rb, hb.min(), s_floor), upper_hd_gt_m40=slope(hb, rb, hb.min(), s_of_hd(-40)),
                           lower_hd_lt_m40=slope(hb, rb, s_of_hd(-40), s_floor)),
           beige_outer=dict(full=slope(hg, rg, hg.min(), hg.max()), lower_60mm=slope(hg, rg, hg.max() - 0.060, hg.max()),
                            upper=slope(hg, rg, hg.min(), hg.max() - 0.060)))
for k in ('full', 'lower_hd_lt_m40'):
    tap['blue_outer'][k]['sink_mm_per_mm_widening'] = round(1 / abs(tap['blue_outer'][k]['dr_ds']), 1)
tap['beige_outer']['lower_60mm']['sink_mm_per_mm_widening'] = round(1 / abs(tap['beige_outer']['lower_60mm']['dr_ds']), 1)

names, O, P, Q, fps = I.load_ref(ref); ib, ig = names.index('blue_cup'), names.index('beige_cup')
Oi = I.inv_pose(O); REL = np.einsum('tij,tjk->tik', Oi[:, ib], O[:, ig])
UG = I.Union(sorted(glob.glob(f'{carve}/beige_cup/piece_*.obj'))); GS = UG.surface(0.002)
cav = lambda s: np.interp(s, hb, rb) - wall
rows = []
for f in range(100, 161):
    R = REL[f].copy(); a = R[:3, :3] @ dg; v = np.cross(a, db); sn = np.linalg.norm(v); cs = a @ db
    K = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    Rc = np.eye(3) + K + K @ K * ((1 - cs) / sn ** 2) if sn > 1e-12 else np.eye(3)
    p = R[:3, :3] @ c0g + R[:3, 3]; foot = c0b + ((p - c0b) @ db) * db
    R[:3, :3] = Rc @ R[:3, :3]; R[:3, 3] = foot - R[:3, :3] @ c0g
    X = GS @ R[:3, :3].T + R[:3, 3]; Y = X - c0b; s = Y @ db; rr = np.hypot(Y @ e1b, Y @ e2b)
    smax = min(s.max(), s_floor); bins = np.arange(s.min() + 0.002, smax - 0.008, 0.002)   # exclude the bottom 8 mm
    ex = []
    for sb in bins:
        k = (s >= sb - 0.001) & (s < sb + 0.001)
        if k.sum() >= 5:
            ex.append((sb, float(rr[k].max() - cav(sb))))
    ex = np.array(ex); j = int(np.argmax(ex[:, 1]))
    rows.append(dict(frame=f, seat_hd_mm=round(hd(ex[j, 0]), 1), seat_excess_mm=round(ex[j, 1] * 1e3, 2),
                     beige_bottom_hd_mm=round(hd(min(s.max(), 1.0)), 1),
                     min_excess_band_mm=round(float(ex[:, 1].min()) * 1e3, 2)))
med = lambda lst: round(float(np.median(lst)), 1)
seat = dict(f100_160_median_hd_mm=med([r['seat_hd_mm'] for r in rows]), f118_160_median_hd_mm=med([r['seat_hd_mm'] for r in rows[18:]]),
            f100_117_median_hd_mm=med([r['seat_hd_mm'] for r in rows[:18]]),
            seat_excess_mm_median=med([r['seat_excess_mm'] for r in rows]))
out = dict(DIAGNOSTIC='GT-free taper and coaxial seat line (ev10w/scripts/taper_seat.py)', taper=tap, seat=seat, rows=rows,
           s_floor_mm=round(s_floor * 1e3, 2), floor_hd_mm=round(hd(s_floor), 1))
json.dump(out, open(outp, 'w'), indent=1)
print(json.dumps(tap, indent=None)); print(json.dumps(seat)); print('floor at h_diag', out['floor_hd_mm'])
for r in rows[::6]:
    print(r)
