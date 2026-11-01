"""Floor gap (DIAGNOSTIC), analysis "A" of ev10_intrusion/scripts/gap.py (commit 2a11301) with the carve directory as a
parameter (their gap.py hard-codes meshes/carve/ev10 and also runs the slow library_v3 analysis B, not needed here).
The heightmap / analyse code is copied verbatim from gap.py. Per frame of REF, in the blue cup's file frame (world up
~ -z): floor_gap_mm = beige lowest point height minus the blue inner-floor height (median top-surface height within
1.5 cm of the cavity axis); over_floor = that point is within 40 mm of the cavity axis.
Usage: gapA.py REF CARVE_DIR OUT.json"""
import sys, glob, json, importlib.util
import numpy as np, trimesh
spec = importlib.util.spec_from_file_location('intrusion', sys.argv[4] if len(sys.argv) > 4 else
                                              '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/ev10w/tree/tools/intrusion.py')
I = importlib.util.module_from_spec(spec); spec.loader.exec_module(I)
ref, CARVE, outp = sys.argv[1:4]
names, O, P, Q, fps = I.load_ref(ref); T = len(O); ib, ig = names.index('blue_cup'), names.index('beige_cup')
Oi = I.inv_pose(O)
REL = np.einsum('tij,tjk->tik', Oi[:, ib], O[:, ig])          # beige file -> blue file


def pieces_mesh(d):
    return trimesh.util.concatenate([trimesh.load(f, force='mesh', process=False) for f in sorted(glob.glob(f'{d}/piece_*.obj'))])


def heightmap(inside, lo, hi, h=0.0015, dz=0.0005):
    xs = np.arange(lo[0], hi[0] + h, h); ys = np.arange(lo[1], hi[1] + h, h); zs = np.arange(lo[2] - dz, hi[2] + dz, dz)
    gx, gy = (g.ravel() for g in np.meshgrid(xs, ys, indexing='ij')); H = np.full(len(gx), np.nan)
    for z in zs[::-1][::-1]:
        todo = np.isnan(H)
        if not todo.any():
            break
        X = np.c_[gx[todo], gy[todo], np.full(todo.sum(), z)]
        ins = inside(X); idx = np.nonzero(todo)[0][ins]; H[idx] = -z
    return xs, ys, H.reshape(len(xs), len(ys))


def analyse(inside, lo, hi, beige_pts, tag):
    xs, ys, H = heightmap(inside, lo, hi); h = xs[1] - xs[0]
    rim = np.nanmax(H)
    cav = H < rim - 0.01
    gx, gy = np.meshgrid(xs, ys, indexing='ij'); cx, cy = gx[cav].mean(), gy[cav].mean()
    rr = np.hypot(gx - cx, gy - cy)
    floor = float(np.nanmedian(H[cav & (rr < 0.015)])); cav_r = float(rr[cav].max())
    print(tag, f'blue rim height {rim*1e3:.1f} mm, inner floor {floor*1e3:.1f} mm (file z {-floor*1e3:.1f}), cavity radius <= {cav_r*1e3:.1f} mm, axis ({cx*1e3:.1f}, {cy*1e3:.1f}) mm')
    res = []
    for f in range(T):
        X = beige_pts @ REL[f, :3, :3].T + REL[f, :3, 3]; hz = -X[:, 2]
        k = np.argmin(hz); low = float(hz[k])
        i = np.clip(np.round((X[:, 0] - xs[0]) / h).astype(int), 0, len(xs) - 1); j = np.clip(np.round((X[:, 1] - ys[0]) / h).astype(int), 0, len(ys) - 1)
        Hp = H[i, j]; inb = (X[:, 0] >= xs[0]) & (X[:, 0] <= xs[-1]) & (X[:, 1] >= ys[0]) & (X[:, 1] <= ys[-1]) & np.isfinite(Hp) & (np.hypot(X[:, 0] - cx, X[:, 1] - cy) < 0.040)
        vc = (hz - Hp)[inb]
        res.append(dict(frame=f, beige_low_h_mm=low * 1e3, floor_gap_mm=(low - floor) * 1e3, over_floor=bool(np.hypot(X[k, 0] - cx, X[k, 1] - cy) < 0.04),
                        low_r_mm=float(np.hypot(X[k, 0] - cx, X[k, 1] - cy) * 1e3),
                        vclear_mm=float(vc.min() * 1e3) if len(vc) else np.nan,
                        n_below_top=int((vc < 0).sum()), n_pts_in_footprint=int(inb.sum())))
    return dict(rim_mm=rim * 1e3, floor_mm=floor * 1e3, cavity_r_mm=cav_r * 1e3, axis_mm=[cx * 1e3, cy * 1e3]), res


def surf(m, n=40000):
    return np.vstack([trimesh.sample.sample_surface(m, n, seed=0)[0], m.vertices])


UA = I.Union(sorted(glob.glob(f'{CARVE}/blue_cup/piece_*.obj'))); gA = pieces_mesh(f'{CARVE}/beige_cup')
out = dict(A=analyse(lambda X: UA.depth_lb(X) > 0, UA.alo, UA.ahi, surf(gA), 'A'), carve=CARVE, ref=ref,
           DIAGNOSTIC='GT-free floor gap (ev10w/scripts/gapA.py = gap.py analysis A, carve dir as parameter); no score')
json.dump(out, open(outp, 'w'), indent=1, default=float); print('wrote', outp)
