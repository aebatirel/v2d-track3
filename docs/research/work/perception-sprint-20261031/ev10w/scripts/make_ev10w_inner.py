"""Inner-radius file for the ev10w blue cup (PREREG build rule, exception case: M2 said NOT-GEOMETRY, so the widening
is applied below the seat line only). GT-free: our reference and our pieces.
For every blue profile bin s (profile coordinate along d, base at high s) whose diagnostic height h = -z of its axis
point is below SEAT_HD (mm): r_in(s) = min(max(r(s) - WALL, R_g(s) + 1 mm), r(s) - MIN_WALL), where R_g(s) = max over
frames FA..FB of the reference of the ev10 beige pieces' surface samples' radial distance from the blue lathe axis within
+-1 mm of s (the beige as tracked, offset and tilt included). Elsewhere r_in = NaN (the tool's default r - wall).
band_edges (profile bin values): the default first edge (hw.min + 60 mm), then the first widened bin, then every 5th
bin (10 mm) to the last wall bin, so the widened heights get their own convex pieces (a 60 mm band would bridge the widened cavity back toward the unwidened rim).
Usage: make_ev10w_inner.py REF BEIGE_CARVE_DIR BLUE_PROFILE.npz SEAT_HD_MM WALL MIN_WALL FA FB OUT.npz"""
import sys, glob, json, importlib.util
import numpy as np
spec = importlib.util.spec_from_file_location('intrusion', '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/ev10w/tree/tools/intrusion.py')
I = importlib.util.module_from_spec(spec); spec.loader.exec_module(I)
ref, gcarve, pb, seat, wall, mwall, fa, fb, outp = sys.argv[1:10]
seat, wall, mwall, fa, fb = float(seat), float(wall), float(mwall), int(fa), int(fb)
B = np.load(pb); c0, d, e1, e2 = (np.asarray(B[k], float) for k in ('c0', 'd', 'e1', 'e2'))
h = np.asarray(B['prof_h'], float); r = np.asarray(B['prof_r'], float); o = np.argsort(h); h, r = h[o], r[o]
hb = float(h.max()); wallbins = h <= hb - wall
hd = -(c0[2] + h * d[2]) * 1e3
names, O, P, Q, fps = I.load_ref(ref); ib, ig = names.index('blue_cup'), names.index('beige_cup')
Oi = I.inv_pose(O); REL = np.einsum('tij,tjk->tik', Oi[:, ib], O[:, ig])
GS = I.Union(sorted(glob.glob(f'{gcarve}/beige_cup/piece_*.obj'))).surface(0.002)
Rg = np.full(len(h), -np.inf)
for f in range(fa, fb + 1):
    X = GS @ REL[f, :3, :3].T + REL[f, :3, 3] - c0; s = X @ d; rr = np.hypot(X @ e1, X @ e2)
    for i in np.nonzero(wallbins & (hd < seat))[0]:
        k = np.abs(s - h[i]) <= 0.001
        if k.any():
            Rg[i] = max(Rg[i], float(rr[k].max()))
r_in = np.full(len(h), np.nan); rows = []
for i in np.nonzero(wallbins & (hd < seat))[0]:
    want = max(r[i] - wall, Rg[i] + 0.001) if np.isfinite(Rg[i]) else r[i] - wall
    r_in[i] = min(want, r[i] - mwall)
    rows.append(dict(s_mm=round(h[i] * 1e3, 1), h_diag_mm=round(hd[i], 1), r_out_mm=round(r[i] * 1e3, 2), r_in_ev10_mm=round((r[i] - wall) * 1e3, 2),
                     Rg_mm=round(Rg[i] * 1e3, 2) if np.isfinite(Rg[i]) else None, want_mm=round(want * 1e3, 2), r_in_mm=round(r_in[i] * 1e3, 2),
                     wall_mm=round((r[i] - r_in[i]) * 1e3, 2), cap_binds=bool(want > r[i] - mwall)))
s_seat = (-seat / 1e3 - c0[2]) / d[2]
# band edges must be profile bin values: the tool assigns bin k to a band when b0 <= h_k <= b1, so adjacent bands share
# their edge bin only if the edge IS a bin (an edge between bins leaves a 2 mm ring with no wall: the first build, v0)
hwb = h[wallbins]; wid = np.nonzero(wallbins & (hd < seat))[0]
e0 = hwb[np.argmin(np.abs(hwb - (hwb.min() + 0.060)))]; e1_ = h[wid[0]]
edges = [e0, e1_] + [h[i] for i in wid[5::5] if h[i] < hwb.max()]
np.savez(outp, h=h, r_in=r_in, band_edges=np.array(edges))
rep = dict(rule='r_in = min(max(r - wall, R_g + 1 mm), r - min_wall) below the seat line (PREREG exception case)', ref=ref,
           frames=[fa, fb], seat_hd_mm=seat, s_seat_mm=round(s_seat * 1e3, 2), wall_mm=wall * 1e3, min_wall_mm=mwall * 1e3,
           band_edges_mm=np.round(np.array(edges) * 1e3, 2).tolist(), bins=rows,
           cap_binds_bins=int(sum(x['cap_binds'] for x in rows)), n_bins=len(rows))
json.dump(rep, open(outp[:-4] + '.json', 'w'), indent=1)
print(json.dumps({k: v for k, v in rep.items() if k != 'bins'}))
for x in rows:
    print(x)
