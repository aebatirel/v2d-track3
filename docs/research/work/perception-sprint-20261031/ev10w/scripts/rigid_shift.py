"""M2 interlock rule: the minimal rigid motion of the beige cup (translation <= 1 cm combined with a tilt <= 3 deg) that
brings the nest intrusion I <= 2 cm3 (and to 0), per frame, on OUR reference. DIAGNOSTIC, GT-free.
I(pose) = max(beige 2 mm lattice samples inside the blue pieces, blue lattice samples inside the beige pieces) x 8e-3 cm3,
the intrusion.py definition (same lattices: Union.lattice(0.002)); the inside test is a lookup in a 0.5 mm occupancy
grid of each union (voxel centre inside by depth_lb > 0), checked against the exact intrusion.py volumes at the
reference pose (reported as grid_vs_exact). Motion, in the blue file frame: tilt Rd (0-3 deg in 1 deg steps about 8 axes
perpendicular to the blue lathe axis, through the beige pieces' centre) then translation t (|t| <= 10 mm): coarse grid
2 mm in the blue lathe frame, then a 0.5 mm refinement around the 6 best coarse poses per frame.
Usage: rigid_shift.py REF CARVE_DIR BLUE_PROFILE.npz FRAMES(a:b:step) OUT.json [INTRUSION_SUMMARY.json]"""
import sys, glob, json, importlib.util, time
import numpy as np
spec = importlib.util.spec_from_file_location('intrusion', '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/ev10w/tree/tools/intrusion.py')
I = importlib.util.module_from_spec(spec); spec.loader.exec_module(I)
ref, carve, pb, frs, outp = sys.argv[1:6]; exact = json.load(open(sys.argv[6]))['per_frame']['I_cm3'] if len(sys.argv) > 6 else None
a_, b_, st_ = (int(x) for x in frs.split(':'))
names, O, P, Q, fps = I.load_ref(ref); ib, ig = names.index('blue_cup'), names.index('beige_cup')
Oi = I.inv_pose(O); REL = np.einsum('tij,tjk->tik', Oi[:, ib], O[:, ig])
B = np.load(pb); c0b, db, e1b, e2b = (np.asarray(B[k], float) for k in ('c0', 'd', 'e1', 'e2'))
UB = I.Union(sorted(glob.glob(f'{carve}/blue_cup/piece_*.obj'))); UG = I.Union(sorted(glob.glob(f'{carve}/beige_cup/piece_*.obj')))
SB, SG = UB.lattice(0.002), UG.lattice(0.002); VOX = 8e-3
H = 0.0005


class Grid:
    def __init__(self, U):
        self.lo = U.alo - 2 * H; n = np.ceil((U.ahi + 2 * H - self.lo) / H).astype(int) + 1; self.n = n
        ax = [self.lo[k] + H * np.arange(n[k]) for k in range(3)]
        occ = np.zeros(n, bool)
        for i, x in enumerate(ax[0]):
            g = np.stack(np.meshgrid([x], ax[1], ax[2], indexing='ij'), -1).reshape(-1, 3)
            occ[i] = (U.depth_lb(g) > I.EPS).reshape(n[1], n[2])
        self.occ = occ

    def count(self, X):
        k = np.round((X - self.lo) / H).astype(np.int64)
        ok = np.all((k >= 0) & (k < self.n), 1)
        k = k[ok]
        return int(self.occ[k[:, 0], k[:, 1], k[:, 2]].sum())


t0 = time.time(); GB, GG = Grid(UB), Grid(UG); t_grid = time.time() - t0
cG = (UG.alo + UG.ahi) / 2                                        # beige pieces' centre (beige file frame)


def rot(axis, deg):
    axis = axis / np.linalg.norm(axis); t = np.radians(deg)
    K = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    return np.eye(3) + np.sin(t) * K + (1 - np.cos(t)) * K @ K


ROTS = [(0.0, 0.0, np.eye(3))] + [(d, az, rot(np.cos(np.radians(az)) * e1b + np.sin(np.radians(az)) * e2b, d))
                                  for d in (1.0, 2.0, 3.0) for az in range(0, 360, 45)]
L = np.stack([e1b, e2b, db], 1)                                   # lathe -> file directions
g = np.arange(-0.010, 0.010 + 1e-9, 0.002); TC = np.stack(np.meshgrid(g, g, g, indexing='ij'), -1).reshape(-1, 3)
TC = TC[np.linalg.norm(TC, axis=1) <= 0.010 + 1e-9]


def I_of(R, t):
    """R, t: the beige pose in the blue frame (beige file -> blue file)."""
    nb = GB.count(SG @ R.T + t)
    Ri = R.T; ti = -Ri @ t; ng = GG.count(SB @ Ri.T + ti)
    return max(nb, ng) * VOX


rows = []
for f in range(a_, b_ + 1, st_):
    R0, t0_ = REL[f, :3, :3], REL[f, :3, 3]; c = R0 @ cG + t0_
    base = I_of(R0, t0_)
    cand = []
    for (deg, az, Rd) in ROTS:
        R = Rd @ R0; tr = Rd @ (t0_ - c) + c                     # tilt about the beige centre
        for tl in TC:
            tw = L @ tl
            cand.append((I_of(R, tr + tw), float(np.linalg.norm(tl)), deg, az, tl))
    cand.sort(key=lambda z: (z[0], z[1] + z[2] / 300))
    # refine around the 6 best coarse poses (0.5 mm steps, +-1.5 mm), same tilt
    best = list(cand[:6]); fine = np.arange(-0.0015, 0.0015 + 1e-9, 0.0005)
    FG = np.stack(np.meshgrid(fine, fine, fine, indexing='ij'), -1).reshape(-1, 3)
    for (v, n_, deg, az, tl) in cand[:6]:
        Rd = rot(np.cos(np.radians(az)) * e1b + np.sin(np.radians(az)) * e2b, deg) if deg else np.eye(3)
        R = Rd @ R0; tr = Rd @ (t0_ - c) + c
        for dl in FG:
            t2 = tl + dl
            if np.linalg.norm(t2) > 0.010 + 1e-9:
                continue
            best.append((I_of(R, tr + L @ t2), float(np.linalg.norm(t2)), deg, az, t2))
    best.sort(key=lambda z: (z[0], z[1] + z[2] / 300))
    allc = cand + best
    def minimal(thr):
        ok = [z for z in allc if z[0] <= thr + 1e-9]
        if not ok:
            return None
        z = min(ok, key=lambda z: (z[1] + z[2] / 300, z[1]))     # smallest motion (1 deg ~ 3.3 mm for ranking)
        return dict(I_cm3=round(z[0], 3), shift_mm=round(z[1] * 1e3, 2), tilt_deg=z[2], tilt_az_deg=z[3],
                    t_lathe_mm=(np.asarray(z[4]) * 1e3).round(2).tolist())
    zb = best[0]
    r = dict(frame=f, I_grid_ref=round(base, 3), I_exact_ref=exact[f] if exact else None,
             min_I_within_bound=round(zb[0], 3), argmin=dict(shift_mm=round(zb[1] * 1e3, 2), tilt_deg=zb[2], tilt_az_deg=zb[3],
                                                            t_lathe_mm=(np.asarray(zb[4]) * 1e3).round(2).tolist()),
             clear_le2=minimal(2.0), clear_0=minimal(0.0),
             translation_only_min_I=round(min(z[0] for z in allc if z[2] == 0.0), 3))
    rows.append(r); print(json.dumps(r), flush=True)
json.dump(dict(DIAGNOSTIC='GT-free M2 rigid-shift search (ev10w/scripts/rigid_shift.py)', ref=ref, carve=carve, frames=frs,
               grid_mm=H * 1e3, grid_build_s=round(t_grid, 1), rotations=len(ROTS), coarse_translations=len(TC), rows=rows),
          open(outp, 'w'), indent=1)
print('done', outp, round(time.time() - t0, 1), 's')
