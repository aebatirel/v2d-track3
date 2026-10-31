"""M2 (mesh session note): is the eval-10 nest intrusion spread all round the blue cup's axis, or one-sided? DIAGNOSTIC,
GT-free (our reference and our pieces only). Axis = the blue cup's lathe axis (approach-2 profile c0, d, e1, e2 in the
blue file frame: the axis the carved cavity is built on), s = height along it (base at high s), h_diag = -z (the
diagnostic's height). Per frame of REF:
  - relative axis tilt (deg) of the beige lathe axis vs the blue lathe axis, and the beige axis's radial offset from the
    blue axis (mm) at the blue floor (s_floor) and at h_diag = -40 mm;
  - the beige base's height above the blue inner floor along the blue axis (mm);
  - intruding samples of both ordered pairs (intrusion.py output, expressed in the blue file frame): azimuth about the
    blue axis; max over 360 half-plane orientations of the volume fraction in one 180 deg half (one-sided >= 0.75);
    resultant length of the unit azimuth vectors; 12-sector histogram; fraction of the volume below h_diag = -40 mm;
  - radial mismatch per height (f110, f140 and the median over a range): beige carve outer radius about the BLUE axis
    (max over its surface samples in a 2 mm bin) minus the blue cavity radius (lathe r_out - wall), and the same with
    the beige moved coaxial (its own axis on the blue axis, same height and tilt removed).
Usage: m2.py REF DIAG.npz CARVE_DIR BLUE_PROFILE.npz BEIGE_PROFILE.npz BEIGE_EXT_M WALL_M OUT.json"""
import sys, glob, json, importlib.util
import numpy as np, trimesh
spec = importlib.util.spec_from_file_location('intrusion', '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/ev10w/tree/tools/intrusion.py')
I = importlib.util.module_from_spec(spec); spec.loader.exec_module(I)
ref, dz, carve, pb, pg, ext_g, wall, outp = sys.argv[1:9]; ext_g, wall = float(ext_g), float(wall)
names, O, P, Q, fps = I.load_ref(ref); T = len(O); ib, ig = names.index('blue_cup'), names.index('beige_cup')
Oi = I.inv_pose(O); REL = np.einsum('tij,tjk->tik', Oi[:, ib], O[:, ig])
B = np.load(pb); G = np.load(pg)
c0b, db, e1b, e2b = (np.asarray(B[k], float) for k in ('c0', 'd', 'e1', 'e2'))
c0g, dg = np.asarray(G['c0'], float), np.asarray(G['d'], float)
hb_b, t_b = float(B['hb_plane']), wall; s_floor = hb_b - t_b                   # blue inner floor (base hi)
hb_g = float(G['hb_plane']) + ext_g                                              # beige base plane (extended)
hpb = np.asarray(B['prof_h'], float); rpb = np.asarray(B['prof_r'], float); o = np.argsort(hpb); hpb, rpb = hpb[o], rpb[o]
s_of_hdiag = lambda hd: (-hd - c0b[2]) / db[2]                                  # axis point with file z = -hd
s40 = s_of_hdiag(-0.040)


def to_lathe(X):
    Y = X - c0b
    return Y @ db, Y @ e1b, Y @ e2b


def axis_offset_at(s_plane, p, a):
    """Radial distance from the blue axis where the line p + u a crosses the plane s = s_plane."""
    sp = (p - c0b) @ db; sa = a @ db; u = (s_plane - sp) / sa; X = p + u * a
    s, x, y = to_lathe(X[None])
    return float(np.hypot(x, y)[0])


Z = np.load(dz); fr, tg, pts = Z['frame'], Z['target'], Z['pts_local'].astype(float)
pitch3 = 8e-9
UG = I.Union(sorted(glob.glob(f'{carve}/beige_cup/piece_*.obj'))); GS = UG.surface(0.002)
cav_r = lambda s: np.interp(s, hpb, rpb) - t_b
rows = []
for f in range(T):
    R = REL[f]; a = R[:3, :3] @ dg; p = R[:3, :3] @ c0g + R[:3, 3]
    tilt = float(np.degrees(np.arccos(np.clip(a @ db, -1, 1))))
    base_pt = R[:3, :3] @ (c0g + hb_g * dg) + R[:3, 3]
    r = dict(frame=f, rel_tilt_deg=round(tilt, 2), off_at_floor_mm=round(axis_offset_at(s_floor, p, a) * 1e3, 2),
             off_at_h40_mm=round(axis_offset_at(s40, p, a) * 1e3, 2),
             beige_base_above_floor_mm=round(float(s_floor - (base_pt - c0b) @ db) * 1e3, 2))
    m = fr == f
    if m.any():
        X = pts[m]; t = tg[m]
        Xg = X[t == ig]; X = np.r_[X[t == ib], Xg @ R[:3, :3].T + R[:3, 3]]            # all in the blue frame
        s, x, y = to_lathe(X); th = np.arctan2(y, x)
        phis = np.radians(np.arange(360)); frac = max(float((np.cos(th - ph) >= 0).mean()) for ph in phis)
        hd = -X[:, 2]
        hist = np.histogram(np.degrees(th) % 360, bins=12, range=(0, 360))[0]
        r.update(n=int(len(X)), vol_cm3_both=round(len(X) * pitch3 * 1e6, 2), half_frac=round(frac, 3),
                 resultant=round(float(np.hypot(np.cos(th).mean(), np.sin(th).mean())), 3),
                 frac_below_h40=round(float((hd < -0.040).mean()), 3), sector_counts=hist.tolist(),
                 mean_dir_deg=round(float(np.degrees(np.arctan2(np.sin(th).mean(), np.cos(th).mean()))), 1))
    rows.append(r)


def mismatch(f, coaxial=False):
    R = REL[f].copy()
    if coaxial:                       # rotate the beige so its axis = the blue axis, translate so the axis lines coincide
        a = R[:3, :3] @ dg; v = np.cross(a, db); sn = np.linalg.norm(v); cs = a @ db
        K = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
        Rc = np.eye(3) + K + K @ K * ((1 - cs) / sn ** 2) if sn > 1e-12 else np.eye(3)
        p = R[:3, :3] @ c0g + R[:3, 3]; sp = (p - c0b) @ db; foot = c0b + sp * db   # beige axis point -> blue axis, same s
        R[:3, :3] = Rc @ R[:3, :3]
        R[:3, 3] = foot - R[:3, :3] @ c0g
    X = GS @ R[:3, :3].T + R[:3, 3]; s, x, y = to_lathe(X); rr = np.hypot(x, y)
    out = []
    for sb in np.arange(s40 - 0.044, s_floor + 1e-9, 0.004):   # from h_diag ~ +4 mm down to the floor
        k = (s >= sb - 0.002) & (s < sb + 0.002)
        if k.sum() < 5:
            continue
        out.append(dict(s_mm=round(sb * 1e3, 1), h_diag_mm=round(-(c0b[2] + sb * db[2]) * 1e3, 1), beige_r_max_mm=round(float(rr[k].max()) * 1e3, 2),
                        cavity_r_mm=round(float(cav_r(sb)) * 1e3, 2), excess_mm=round(float(rr[k].max() - cav_r(sb)) * 1e3, 2)))
    return out


res = dict(DIAGNOSTIC='GT-free M2 geometry of our eval-10 reference (ev10w/scripts/m2.py)', ref=ref, diag=dz, carve=carve,
           blue_axis=dict(c0_mm=(c0b * 1e3).round(2).tolist(), d=db.round(4).tolist(), tilt_vs_file_z_deg=round(float(np.degrees(np.arccos(abs(db[2])))), 2)),
           s_floor_mm=round(s_floor * 1e3, 2), s_at_h40_mm=round(s40 * 1e3, 2), rows=rows,
           mismatch={str(f): dict(as_tracked=mismatch(f), coaxial=mismatch(f, True)) for f in (100, 105, 110, 117, 120, 130, 140, 150, 160)})
summ = {}
for lab, a_, b_ in (('f47-99', 47, 99), ('f100-117', 100, 117), ('f118-160', 118, 160), ('f100-160', 100, 160)):
    rr_ = [r for r in rows[a_:b_ + 1] if r.get('n')]
    st = lambda k: dict(min=round(float(np.min([r[k] for r in rr_])), 2), median=round(float(np.median([r[k] for r in rr_])), 2),
                        max=round(float(np.max([r[k] for r in rr_])), 2)) if rr_ else None
    allr = rows[a_:b_ + 1]
    summ[lab] = dict(intruding_frames=len(rr_), one_sided_frames=int(sum(r['half_frac'] >= 0.75 for r in rr_)), half_frac=st('half_frac'),
                     resultant=st('resultant'), frac_below_h40=st('frac_below_h40'), mean_dir_deg=st('mean_dir_deg'),
                     rel_tilt_deg=dict(median=float(np.median([r['rel_tilt_deg'] for r in allr])), max=float(np.max([r['rel_tilt_deg'] for r in allr]))),
                     off_at_floor_mm=dict(median=float(np.median([r['off_at_floor_mm'] for r in allr])), max=float(np.max([r['off_at_floor_mm'] for r in allr]))),
                     off_at_h40_mm=dict(median=float(np.median([r['off_at_h40_mm'] for r in allr])), max=float(np.max([r['off_at_h40_mm'] for r in allr]))),
                     beige_base_above_floor_mm=dict(min=float(np.min([r['beige_base_above_floor_mm'] for r in allr])),
                                                    median=float(np.median([r['beige_base_above_floor_mm'] for r in allr])),
                                                    max=float(np.max([r['beige_base_above_floor_mm'] for r in allr]))),
                     sector_counts=np.sum([r['sector_counts'] for r in rr_], 0).tolist() if rr_ else None)
res['summary'] = summ
json.dump(res, open(outp, 'w'), indent=1)
print(json.dumps(res['blue_axis']), 's_floor', res['s_floor_mm'], 's_h40', res['s_at_h40_mm'])
for k, v in summ.items():
    print(k, json.dumps(v))
for f in (110, 140):
    print('frame', f)
    for x, y in zip(res['mismatch'][str(f)]['as_tracked'], res['mismatch'][str(f)]['coaxial']):
        print(f"  h {x['h_diag_mm']:+6.1f}  cav {x['cavity_r_mm']:5.1f}  beige(tracked) {x['beige_r_max_mm']:5.1f} ex {x['excess_mm']:+5.1f} | coaxial {y['beige_r_max_mm']:5.1f} ex {y['excess_mm']:+5.1f}")
