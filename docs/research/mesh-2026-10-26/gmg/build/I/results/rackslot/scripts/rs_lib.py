"""rack slot pieces (evals 30, 14): shared inputs, frame sets and grids. GT-free: reads only the PACKED references'
object poses / hand-contact labels (via the collcarve2-evalcheck per-frame records and pose npz, which were built from
the packed references), the packed meshes and FlashCHORD's packed CoACD hulls. No scan, mocap, dataset parquet 'pose'
field or *_align file is read."""
import json, os
import numpy as np, trimesh
from scipy.spatial import ConvexHull
import vox

REPO = '/home/user/v2d-track3'
SCR = '/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad'
EVCK = f'{SCR}/evck'                                         # collcarve2-evalcheck work dir (inputs, poses, packed hulls)
PRECHECK = f'{REPO}/docs/research/mesh-2026-10-26/gmg/build/I/results/collcarve2-evalcheck'
RACK_MESH = f'{REPO}/meshes/library_v3/plastic_dish_rack.glb'
RACK_PACKED = f'{EVCK}/out/packed/rack_lib.npz'
GUEST = {'30': dict(name='mini_sweeper', mesh=f'{REPO}/meshes/library_v3/mini_sweeper.glb',
                    packed=f'{EVCK}/out/packed/sweeper_lib.npz'),
         '14': dict(name='blue_cup', mesh=f'{EVCK}/dl/runs/20261025-evb1420-ee7ba8e/refs/sf/ep14/assets/mesh/blue_cup/blue_cup.glb',
                    packed=f'{EVCK}/out/packed/cup_lib.npz')}
PITCH = 0.001          # rack-frame grid, 1 mm (as the precheck's visual / packed occupancy)
CLEAR = 0.001          # clearance c around the guest's packed pieces (informed: F-I5.10 c_0 1.0 mm, F-I1.14)
RUN_MIN = 5            # informed: F-I1.1 static run length >= 5 frames
CAV_MIN = 1.0          # cm3, the precheck's cavity-region threshold


def load_mesh(p):
    return vox.load(p)


def load_hulls(npz):
    z = np.load(npz)
    return [np.asarray(z[f'v{i}'], float) for i in range(int(z['n']))]


def poses(ep):
    po = np.load(f'{EVCK}/out/geo2/ep{ep}_poses.npz')
    T, ir, ig = po['T'], int(po['ir']), int(po['ig'])
    rel = np.stack([np.linalg.inv(T[f, ir]) @ T[f, ig] for f in range(len(T))])
    return dict(T=T, ir=ir, ig=ig, names=[str(x) for x in po['names']], rel=rel)


def records(ep):
    return json.load(open(f'{PRECHECK}/per_frame/ep{ep}_frames.json'))


def runs_of(mask):
    out, f, n = [], 0, len(mask)
    while f < n:
        if mask[f]:
            g = f
            while g + 1 < n and mask[g + 1]:
                g += 1
            out.append((f, g)); f = g + 1
        else:
            f += 1
    return out


def rest_frames_h0(ep):
    """SUPERSEDED 1 Nov 03:27 UTC (GATES.md amendment; H0 is not the rule's hands-off set). R under H0: frames in
    maximal runs of >= RUN_MIN consecutive frames that are H0 (no contact label in either hand), have the guest in the
    rack's cavity region (>= 1 cm3) and carry no (a) table or (b) float flag of the precheck."""
    fr = records(ep)
    rows, pair = fr['per_frame']['rows'], fr['per_frame']['pair']
    base = np.array([r['H0'] and pair[f]['V_gvis_in_rcavity'] >= CAV_MIN for f, r in enumerate(rows)])
    flag = np.array([any(x.startswith(('a_', 'b_')) for x in r['fails']) for r in rows])
    ok = base & ~flag
    R = [f for a, b in runs_of(ok) if b - a + 1 >= RUN_MIN for f in range(a, b + 1)]
    excl = dict(flagged=[(int(f), rows[f]['fails']) for f in np.nonzero(base & flag)[0]],
                short_runs=[[int(a), int(b)] for a, b in runs_of(ok) if b - a + 1 < RUN_MIN])
    return R, dict(n_base=int(base.sum()), runs=[[int(a), int(b)] for a, b in runs_of(ok) if b - a + 1 >= RUN_MIN],
                   excluded=excl)


def rest_frames(ep):
    """R (GATES.md as amended 1 Nov 03:27 UTC): frames that are hands-off under the rule's H30 (no robot hand point
    within 30 mm of either object, the precheck's H30), have the guest in the rack's cavity region (guest mesh inside
    the rack's convex hull and outside the rack mesh >= 1 cm3), and carry no (a) table or (b) float flag of the
    precheck (pose possible apart from overlap). No run-length condition."""
    fr = records(ep)
    rows, pair = fr['per_frame']['rows'], fr['per_frame']['pair']
    base = np.array([r['H30'] and pair[f]['V_gvis_in_rcavity'] >= CAV_MIN for f, r in enumerate(rows)])
    flag = np.array([any(x.startswith(('a_', 'b_')) for x in r['fails']) for r in rows])
    ok = base & ~flag
    R = [int(f) for f in np.nonzero(ok)[0]]
    return R, dict(n_base=int(base.sum()), runs=[[int(a), int(b)] for a, b in runs_of(ok)],
                   excluded=dict(flagged=[(int(f), rows[f]['fails']) for f in np.nonzero(base & flag)[0]]),
                   n_H30=int(sum(r['H30'] for r in rows)))


def gate_frames(ep, k=3):
    """G3 / G4 frames (GATES.md as amended): the precheck's contact frames that are in R, then the middle frame of
    each other run of R (longest first), then the R frames at the 25 % / 75 % / 50 % positions, until there are K."""
    R, info = rest_frames(ep)
    pre = [f for f in PRECHECK_FRAMES[ep] if f in R]
    sel = list(pre)
    runs = sorted(info['runs'], key=lambda r: -(r[1] - r[0]))
    for a, b in runs:
        if len(sel) >= k:
            break
        if not any(a <= f <= b for f in sel):
            sel.append((a + b) // 2)
    for q in (0.25, 0.75, 0.5):
        if len(sel) >= k:
            break
        f = R[int(round(q * (len(R) - 1)))]
        if f not in sel:
            sel.append(f)
    return sel[:k]


PRECHECK_FRAMES = {'30': [257, 249, 17], '14': [149, 135, 137]}


class Grid:
    """1 mm rack-frame grid over the packed rack pieces' bounding box (+ pad)."""
    def __init__(self, hulls, pad=0.004, pitch=PITCH):
        allv = np.vstack(hulls)
        self.lo = allv.min(0) - pad
        self.n = np.ceil((allv.max(0) + pad - self.lo) / pitch).astype(int)
        self.pitch = pitch

    def axes(self, a, b):
        return [self.lo[k] + (np.arange(a[k], b[k] + 1) + 0.5) * self.pitch for k in range(3)]

    def box(self, V):
        a = np.clip(np.floor((V.min(0) - self.lo) / self.pitch).astype(int), 0, self.n - 1)
        b = np.clip(np.ceil((V.max(0) - self.lo) / self.pitch).astype(int), 0, self.n - 1)
        return a, b

    def centres(self, occ):
        return self.lo + (np.argwhere(occ) + 0.5) * self.pitch

    def fill_eq(self, occ, eq, V, tol=1e-9):
        """occ |= centre-inside the polytope eq (n.x + d <= 0) within the AABB of V."""
        a, b = self.box(V)
        G = np.stack(np.meshgrid(*self.axes(a, b), indexing='ij'), -1)
        ins = np.all(G.reshape(-1, 3) @ eq[:, :3].T + eq[:, 3] <= tol, 1).reshape(G.shape[:3])
        occ[a[0]:b[0] + 1, a[1]:b[1] + 1, a[2]:b[2] + 1] |= ins
        return occ

    def hull_occ(self, V):
        occ = np.zeros(self.n, bool)
        return self.fill_eq(occ, ConvexHull(V).equations, V)

    def union_occ(self, hulls):
        occ = np.zeros(self.n, bool)
        for V in hulls:
            self.fill_eq(occ, ConvexHull(V).equations, V)
        return occ

    def mesh_occ(self, mesh):
        g = vox.voxelize(mesh, self.pitch, lo=self.lo, hi=self.lo + self.n * self.pitch)
        assert g.occ.shape == tuple(self.n), (g.occ.shape, self.n)
        return g.occ


def rest_volume(grid, guest_hulls, rels, frames, mask, clear=CLEAR):
    """Swept rest volume on the grid cells of MASK (centres): union over FRAMES of the guest's packed pieces, each
    plane pushed out by CLEAR (a polytope offset; it contains the CLEAR Minkowski dilation of each hull), placed by
    the guest-in-rack relative pose. Returns a grid-shaped bool array (False outside MASK)."""
    idx = np.argwhere(mask)
    X = grid.lo + (idx + 0.5) * grid.pitch
    o = np.argsort(X[:, 2]); X, idx = X[o], idx[o]
    z = X[:, 2]
    hit = np.zeros(len(X), bool)
    eqs = [ConvexHull(V).equations for V in guest_hulls]
    for f in frames:
        R, t = rels[f][:3, :3], rels[f][:3, 3]
        for V, e in zip(guest_hulls, eqs):
            n2 = e[:, :3] @ R.T
            d2 = e[:, 3] - n2 @ t - clear
            Vw = V @ R.T + t
            lo, hi = Vw.min(0) - 2 * clear, Vw.max(0) + 2 * clear
            a, b = np.searchsorted(z, lo[2]), np.searchsorted(z, hi[2])
            if b <= a:
                continue
            Y = X[a:b]
            m = np.all((Y >= lo) & (Y <= hi), 1) & ~hit[a:b]
            j = np.nonzero(m)[0]
            if len(j):
                ins = np.all(Y[j] @ n2.T + d2 <= 1e-9, 1)
                hit[a + j[ins]] = True
    occ = np.zeros(grid.n, bool)
    occ[idx[hit, 0], idx[hit, 1], idx[hit, 2]] = True
    return occ
