"""ev10-cavsafe measures beside the precheck's evalcheck.py / contacts.py (GATES.md gate 3; report-only extras).
GT-free: reads our lathe profiles (approach2-scripts/lathe_fit2.py on library_v3), the piece OBJ files, the
library_v3 visual meshes and the packed reference's replayed poses (evalcheck.py's ep<tag>_poses.npz).

  gate 3   cavity intrusion of the receiver (blue cup) pieces: C = { h_mouth <= h <= h_floor, rho < r_in(h) } in the blue
           lathe frame, r_in = r - 3 mm linear between profile bins, h_mouth = first wall bin, h_floor = h_base - 3 mm;
           depth = max(r_in(h) - rho) over the pieces' vertices, surface samples <= 0.5 mm apart and interior points of
           a 0.5 mm grid; intruding volume on that grid. Correction (first run, 03:01 UTC): at the floor plane
           r_in - rho is not a depth (a base hull's top face lies ON the floor plane h = h_floor, where r_in - rho
           reaches 30 mm at the axis). Reported: depth_radial (the pre-registered measure) for the wall pieces, and for
           all pieces the distance into the cavity, min(r_in(h) - rho, h_floor - h), with points at h >= h_floor -
           0.001 mm on the floor plane, not in the cavity
  guest    outward excursion of the guest (beige) pieces beyond its shrunk lathe profile r_s = r - 8 mm (G1's target)
           and beyond the unshrunk lathe profile r (the beige outer surface as the lathe sees it): max(rho - r(h))
  floor    at every frame: (i) the guest's visual mesh (1.5 mm grid) inside the receiver's visual mesh (1 mm occupancy),
           split into the part inside the blue lathe cavity C (the visual mesh fills its own cavity there: no
           cavity-respecting piece set keeps it) and the part outside C (the meshes cross at the wall / base: pose);
           (ii) design floor: the exact shrunk beige lathe body (rho <= r_s, 1 mm grid) outside C and inside the blue's
           outer envelope (rho <= r / cos(pi/12), h_mouth <= h <= h_base): what remains for perfect pieces of this
           lathe design (shrink 8 mm, wall 3 mm, these profiles) at these poses
Usage: python -I cavsafe_measure.py PROF_DIR PACKED_PIECES CAND_PIECES POSES.npz OUT.json
"""
import glob, json, os, sys
import numpy as np, trimesh
from scipy.spatial import ConvexHull

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'collcarve2-evalcheck', 'scripts'))
import vox  # noqa: E402  (the precheck's exact parity voxeliser)

prof_dir, packed_dir, cand_dir, poses, out = sys.argv[1:6]
REPO = '/home/user/v2d-track3'
T_WALL, SHRINK, SEG = 0.003, 0.008, 12
SP = 0.0005


class Lathe:
    def __init__(self, name, shrink=0.0, ext=0.0):
        z = np.load(os.path.join(prof_dir, f'{name}_profile.npz'))
        self.c0, self.d, self.e1, self.e2 = (np.asarray(z[k], float) for k in ('c0', 'd', 'e1', 'e2'))
        h = np.asarray(z['prof_h'], float); r = np.asarray(z['prof_r'], float); o = np.argsort(h)
        self.h, self.r = h[o], r[o]
        self.shrink, self.t_fit = shrink, float(z['t'])
        self.h_ext = self.h.max() + ext                      # base extension (beige: 7.1 mm, as ev10)

    def hr(self, X):
        Q = np.asarray(X, float) - self.c0; hh = Q @ self.d
        return hh, np.linalg.norm(Q - hh[:, None] * self.d, axis=1)

    def R(self, hh, shrink=None):
        s = self.shrink if shrink is None else shrink
        return np.interp(hh, self.h, self.r) - s                # flat beyond the end bins


def load_pieces(d, n):
    return [np.asarray(trimesh.load(p, force='mesh').vertices, float) for p in sorted(glob.glob(f'{d}/{n}/piece_*.obj'))]


def piece_points(V, sp=SP):
    m = trimesh.convex.convex_hull(V)
    k = max(int(np.ceil(m.area / sp ** 2)), 1)
    S = np.asarray(trimesh.sample.sample_surface_even(m, k, seed=0)[0])
    lo, hi = V.min(0), V.max(0)
    ax = [np.arange(lo[i] + sp / 2, hi[i], sp) for i in range(3)]
    G = np.stack(np.meshgrid(*ax, indexing='ij'), -1).reshape(-1, 3) if all(len(a) for a in ax) else np.zeros((0, 3))
    if len(G):
        e = ConvexHull(V).equations
        G = G[np.all(G @ e[:, :3].T + e[:, 3] <= 1e-12, 1)]
    return np.vstack([V, S]), G


blue = Lathe('blue_cup')
h_mouth = blue.h.min(); h_base = blue.h.max(); h_floor = h_base - T_WALL


def cavity_depth(X, radial=False):
    hh, rho = blue.hr(X)
    dep = blue.R(hh) - T_WALL - rho
    if not radial:
        dep = np.minimum(dep, h_floor - hh)
    dep[(hh < h_mouth) | (hh >= h_floor - 1e-6)] = -np.inf
    return dep


res = dict(_note=__doc__.split('\n')[0], cavity=dict(h_mouth_mm=h_mouth * 1e3, h_floor_mm=h_floor * 1e3, wall_mm=3.0,
                                                    sample_mm=SP * 1e3, tolerance_mm=0.001))
# ---------------------------------------------------------------- gate 3 + guest excursion, per piece set
beige = Lathe('beige_cup_v3', shrink=SHRINK, ext=0.0071)
for tag, d in (('packed', packed_dir), ('cand', cand_dir)):
    rec = {}
    bp = load_pieces(d, 'blue_cup')
    dmax, dradw, vol, per, perr = -np.inf, -np.inf, 0, [], []
    for i, V in enumerate(bp):
        Ssurf, G = piece_points(V)
        G = G if len(G) else np.zeros((0, 3))
        ds, dg = cavity_depth(Ssurf), cavity_depth(G)
        m = max(ds.max(), dg.max() if len(dg) else -np.inf)
        mr = max(cavity_depth(Ssurf, True).max(), cavity_depth(G, True).max() if len(G) else -np.inf)
        per.append(round(float(m) * 1e3, 4) if np.isfinite(m) else None)
        perr.append(round(float(mr) * 1e3, 4) if np.isfinite(mr) else None)
        dmax = max(dmax, m); vol += int((dg > 0).sum())
        if i < 36:                    # ev10 layout; for 8-sector sets the extra indices are floor / base pieces,
                                      # whose points lie at h >= h_floor and so never count
            dradw = max(dradw, mr)
    rec['receiver'] = dict(pieces=len(bp), cavity_depth_max_mm=round(float(dmax) * 1e3, 4),
                           depth_radial_wall_pieces_max_mm=round(float(dradw) * 1e3, 4),
                           cavity_intrusion_cm3=round(vol * SP ** 3 * 1e6, 3),
                           pieces_intruding=int(sum(1 for p in per if p is not None and p > 0.001)),
                           depth_per_piece_mm=per, depth_radial_per_piece_mm=perr,
                           gate3_pass=bool(dmax * 1e3 <= 0.001 and dradw * 1e3 <= 0.001))
    gp = load_pieces(d, 'beige_cup')
    ex_s, ex_v = -np.inf, -np.inf
    for V in gp:
        Ssurf, _ = piece_points(V)
        hh, rho = beige.hr(Ssurf)
        ex_s = max(ex_s, float((rho - beige.R(hh)).max())); ex_v = max(ex_v, float((rho - beige.R(hh, 0.0)).max()))
    rec['guest'] = dict(pieces=len(gp), excursion_beyond_shrunk_profile_mm=round(ex_s * 1e3, 4),
                        excursion_beyond_unshrunk_profile_mm=round(ex_v * 1e3, 4))
    res[tag] = rec
    print(tag, json.dumps({k: {kk: vv for kk, vv in v.items() if not kk.startswith('depth_') or kk.endswith('max_mm')} for k, v in rec.items()}),
          flush=True)

# ---------------------------------------------------------------- floor, per frame (same for both piece sets)
P = np.load(poses); T = P['T']; ir, ig = int(P['ir']), int(P['ig']); names = [str(x) for x in P['names']]
assert names[ir] == 'blue_cup' and names[ig] == 'beige_cup', names


def mesh(n):
    m = trimesh.load(f'{REPO}/meshes/library_v3/{n}.glb', force='mesh')
    return trimesh.Trimesh(np.asarray(m.vertices, float), np.asarray(m.faces), process=True)


Rv = vox.voxelize(mesh('blue_cup'), 0.001)
Gpts = vox.voxelize(mesh('beige_cup'), 0.0015).centres()
# exact shrunk beige lathe body on a 1 mm grid, in the beige frame
hs = np.arange(beige.h.min() + 0.0005, beige.h_ext, 0.001)
rmax = float(beige.R(hs).max())
u = np.arange(-rmax, rmax + 1e-9, 0.001) + 0.0005
U, W = np.meshgrid(u, u, indexing='ij'); U, W = U.ravel(), W.ravel()
pts = []
for hh in hs:
    k = np.hypot(U, W) <= beige.R(np.array([hh]))[0]
    pts.append(beige.c0 + hh * beige.d + U[k, None] * beige.e1 + W[k, None] * beige.e2)
GL = np.vstack(pts)
sec = 1 / np.cos(np.pi / SEG)
rows = []
for f in range(T.shape[0]):
    Trg = np.linalg.inv(T[f, ir]) @ T[f, ig]
    X = Gpts @ Trg[:3, :3].T + Trg[:3, 3]
    inv = Rv.lookup(X); inc = cavity_depth(X) > 0
    Y = GL @ Trg[:3, :3].T + Trg[:3, 3]
    hh, rho = blue.hr(Y)
    env = (hh >= h_mouth) & (hh <= h_base) & (rho <= blue.R(hh) * sec)
    rows.append(dict(frame=f, V_visual=float(inv.sum()) * 0.0015 ** 3 * 1e6,
                     V_visual_in_cavity=float((inv & inc).sum()) * 0.0015 ** 3 * 1e6,
                     V_visual_outside_cavity=float((inv & ~inc).sum()) * 0.0015 ** 3 * 1e6,
                     V_design_floor=float((env & ~(cavity_depth(Y) > 0)).sum()) * 1e-3 ** 3 * 1e6))
res['floor'] = dict(beige_lathe_body_cm3=round(len(GL) * 1e-3, 2), frames=rows)
json.dump(res, open(out, 'w'), indent=1)
R = [x for x in rows if 124 <= x['frame'] <= 160]
for k in ('V_visual', 'V_visual_in_cavity', 'V_visual_outside_cavity', 'V_design_floor'):
    v = np.array([x[k] for x in R])
    print(f'f124-160 {k}: median {np.median(v):.2f} min {v.min():.2f} max {v.max():.2f}')
