"""Free-space-guided convex decomposition of our mesh for the simulator (mesh pipeline v5, docs/mesh-v5-spec-draft.md
section 8.2; port of the v5 study's s5coll/scripts/decomp.py with the needed vox2 functions, 2026-10-22). Mesh only:
no scan, no mocap. Needs NVIDIA Warp (the FlashCHORD venv has it); runs on CPU.

Why: FlashCHORD runs CoACD (threshold 0.05) on each collision mesh; its hulls fill cavities and slots, so stacked or
nested objects start inside each other's hulls (ep2 lid on the pot, ep26 pot in the rack) and boards cannot slot
[M, 2026-10-22]. FlashCHORD's CoACD returns each of our convex pieces unchanged (<= 0.024 mm, 256 of 256), so writing
one <collision> element per piece (make_assets.py --pieces) makes the simulator use exactly these hulls.

Recipe (input: the full-resolution mesh in the body frame, never the 4096-face file):
  1. solid = winding number < 0 on a grid (pitch >= 1.5 mm, <= ~1.2 M points; chunked inside-tests);
  2. free = grid points more than MARGIN outside the mesh (0.75 mm; 0.5 mm suggested with a partner weight);
  3. a piece is the convex hull of the mesh surface samples and solid points inside a convex cell; its excess is the
     (weighted) free volume inside its hull. The piece with the largest excess is split by the plane that minimises the
     children's summed excess (PCA axes of the piece, of the whole solid and of the piece's free points, 19 offset
     quantiles plus the free points' extremes and median; cells overlap by 1 mm across a cut);
  4. stop when every piece holds <= TOL cm3 (0.3) or at the cap: 32 pieces, 64 when the solid is above 300 cm3;
  5. each hull is reduced to <= 64 vertices by furthest-point insertion (MuJoCo's hull limit), so the simulator's hull
     is the one written here (an inner approximation, reported).
Optional partner weighting (spec section 7): free points that another object, posed by OUR tracks, occupies within
1 mm at the given frames weigh LAM (10) instead of 1.

Acceptance (spec section 8.3) is checked elsewhere (hull overlap vs mesh overlap, union <= 1.25 x solid, rest replay).
Usage: python collision_decomp.py MESH OUT_DIR [--tol 0.3] [--max 0 (auto 32/64)] [--pitch 0] [--margin 0.75]
       [--partner MESH_B POSES NAME_A NAME_B FRAMES --lam 10]
Writes OUT_DIR/piece_XX.obj and OUT_DIR/decomp.json.
"""
import argparse, json, os, time

import numpy as np
import trimesh
from scipy.spatial import ConvexHull

try:                                                    # NVIDIA Warp: the FlashCHORD venv has it
    import warp as wp
    wp.config.quiet = True

    @wp.kernel
    def _sd_winding(mesh: wp.uint64, pts: wp.array(dtype=wp.vec3), maxd: float, out: wp.array(dtype=float)):
        """Signed distance, winding-number sign (the v5 study's vox2._sd_w, same query parameters)."""
        i = wp.tid(); p = pts[i]
        q = wp.mesh_query_point_sign_winding_number(mesh, p, maxd, 2.0, 0.5)
        d = maxd
        if q.result:
            d = wp.length(p - wp.mesh_eval_position(mesh, q.face, q.u, q.v)) * q.sign
        out[i] = d
except ImportError:                                     # importable without Warp (decompose() then fails)
    wp = None


class SignedDistance:
    """Signed distance to a mesh by Warp (negative inside, winding-number sign), on CPU."""

    def __init__(self, m):
        if wp is None:
            raise ImportError('collision_decomp needs NVIDIA Warp (run it in the FlashCHORD venv)')
        wp.init()
        with wp.ScopedDevice('cpu'):
            self.wm = wp.Mesh(points=wp.array(np.asarray(m.vertices, np.float32), dtype=wp.vec3),
                              indices=wp.array(np.asarray(m.faces, np.int32).ravel(), dtype=int), support_winding_number=True)

    def __call__(self, P, maxd=0.1):
        if len(P) == 0:
            return np.zeros(0, np.float32)
        with wp.ScopedDevice('cpu'):
            out = wp.zeros(len(P), dtype=float)
            wp.launch(_sd_winding, dim=len(P), inputs=[self.wm.id, wp.array(np.ascontiguousarray(P, np.float32), dtype=wp.vec3), maxd, out])
            return out.numpy()


def inside(eq, Q, tol=1e-9, chunk=4000000):
    """Points inside a convex hull (all facet planes); chunked so (points x facets) stays small."""
    out = np.zeros(len(Q), bool)
    if len(Q) == 0:
        return out
    step = max(1000, chunk // max(1, len(eq)))
    for i in range(0, len(Q), step):
        out[i:i + step] = np.all(Q[i:i + step] @ eq[:, :3].T + eq[:, 3] <= tol, axis=1)
    return out


def reduce_hull(V, k):
    """At most k vertices by furthest-point insertion (MuJoCo keeps at most 64 hull vertices)."""
    if len(V) <= k:
        return V
    c = V.mean(0); ax = np.linalg.svd(V - c, full_matrices=False)[2]
    sel = sorted({int(np.argmax(V @ (s * u))) for u in ax for s in (1, -1)} | {int(np.argmax(np.linalg.norm(V - c, axis=1)))})
    while len(sel) < k:
        try:
            eq = ConvexHull(V[sel]).equations
        except Exception:
            sel.append(int(np.argmax(np.linalg.norm(V - V[sel].mean(0), axis=1)))); continue
        dist = (V @ eq[:, :3].T + eq[:, 3]).max(1)
        j = int(np.argmax(dist))
        if dist[j] <= 1e-7:
            break
        sel.append(j)
    return V[sel]


def decompose(m, tol=0.3, max_pieces=0, pitch=0.0, margin=0.75, overlap=1.0, nsurf=120000, maxv=64, partner=None,
              lam=10.0, contact_mm=1.0, log=print):
    """Convex pieces of mesh m. Returns (list of hull vertex arrays, report dict). partner = (mesh_b, poses_npz,
    name_a, name_b, 'f0:f1:step') weights free points the partner occupies (our tracks) by lam."""
    t0 = time.time()
    m = trimesh.Trimesh(np.asarray(m.vertices), np.asarray(m.faces), process=True)
    sd = SignedDistance(m)
    pitch = pitch or max(0.0015, (np.prod(m.extents + 0.006) / 1.2e6) ** (1 / 3))
    lo = m.bounds[0] - 2 * pitch; n = np.ceil((m.bounds[1] + 2 * pitch - lo) / pitch).astype(int) + 1
    G = np.stack(np.meshgrid(*[lo[k] + pitch * np.arange(n[k]) for k in range(3)], indexing='ij'), -1).reshape(-1, 3)
    d = sd(G, maxd=1.0)
    SOL = G[d < 0]; FREE = G[d > margin * 1e-3]; FW = np.ones(len(FREE))
    VOX = pitch ** 3 * 1e6
    if not max_pieces:
        max_pieces = 64 if len(SOL) * VOX > 300 else 32                # spec 8.2 step 5 (new, GT-free) [H]
    if partner:
        mb, pp, na, nb, fr = partner
        mB = trimesh.load(mb, force='mesh'); sdB = SignedDistance(mB); Pz = np.load(pp)
        TA, TB = Pz[f'cam_T_{na}'], Pz[f'cam_T_{nb}']
        occ = np.zeros(len(FREE), bool); f0, f1, fs = map(int, fr.split(':'))
        for t in range(f0, min(f1, len(TA)), fs):
            T = np.linalg.inv(TB[t]) @ TA[t]
            occ |= sdB(FREE @ T[:3, :3].T + T[:3, 3], 1.0) < contact_mm * 1e-3
        FW[occ] = lam
        log(f'interaction weighting: {occ.sum() * VOX:.2f} cm3 of free space occupied by {nb} (x{lam})')
    SURF = np.vstack([trimesh.sample.sample_surface(m, nsurf, seed=0)[0], m.vertices if len(m.vertices) < 60000 else np.zeros((0, 3))])
    PTS = np.vstack([SURF, SOL])
    gax = np.linalg.svd(SOL - SOL.mean(0), full_matrices=False)[2]
    rng = np.random.default_rng(0)
    log(f'faces {len(m.faces)} watertight {m.is_watertight} solid {len(SOL) * VOX:.1f} cm3 (pitch {pitch * 1e3:.2f} mm, '
        f'{len(G)} pts), mesh volume {m.volume * 1e6 if m.is_watertight else float("nan"):.1f} cm3, cap {max_pieces}')

    class Piece:
        def __init__(self, idx):
            self.idx = idx
            h = ConvexHull(PTS[idx]); self.eq, self.V = h.equations, PTS[idx][h.vertices]
            k = inside(self.eq, FREE)
            self.F = FREE[k]; self.FWt = FW[k]; self.excess = self.FWt.sum() * VOX

    def split_candidates(pc):
        P = PTS[pc.idx]
        axes = [*np.linalg.svd(P - P.mean(0), full_matrices=False)[2], *gax]
        if len(pc.F) >= 10:
            axes += [*np.linalg.svd(pc.F - pc.F.mean(0), full_matrices=False)[2]]
        U = []
        for u in axes:
            u = u / np.linalg.norm(u)
            if all(abs(u @ w) < 0.985 for w in U):
                U.append(u)
        sub = P if len(P) <= 8000 else P[rng.choice(len(P), 8000, replace=False)]
        ks = np.arange(len(pc.F)) if len(pc.F) <= 60000 else rng.choice(len(pc.F), 60000, replace=False)
        Fs = pc.F[ks]; Ws = pc.FWt[ks]; scale = len(pc.F) / max(1, len(Fs)); best = None
        for u in U:
            s = sub @ u; offs = list(np.quantile(s, np.linspace(0.05, 0.95, 19)))
            if len(pc.F):
                fs = pc.F @ u; offs += [fs.min() - 0.5 * pitch, fs.max() + 0.5 * pitch, float(np.median(fs))]
            for o in offs:
                L = sub[s <= o + overlap * 1e-3]; R = sub[s >= o - overlap * 1e-3]
                if len(L) < 20 or len(R) < 20:
                    continue
                try:
                    eL = ConvexHull(L).equations; eR = ConvexHull(R).equations
                except Exception:
                    continue
                sc = (Ws[inside(eL, Fs)].sum() + Ws[inside(eR, Fs)].sum()) * scale * VOX
                if best is None or sc < best[0]:
                    best = (sc, u, o)
        return best

    pieces = [Piece(np.arange(len(PTS)))]; steps = []
    while len(pieces) < max_pieces:
        pieces.sort(key=lambda p: -p.excess)
        pc = pieces[0]
        if pc.excess <= tol:
            break
        best = split_candidates(pc)
        if best is None or best[0] >= 0.9 * pc.excess:              # cannot improve this piece: freeze it
            steps.append(dict(stuck=round(pc.excess, 3))); pc.excess = -pc.excess - 1e-9; continue
        s = PTS[pc.idx] @ best[1]
        l = Piece(pc.idx[s <= best[2] + overlap * 1e-3]); r = Piece(pc.idx[s >= best[2] - overlap * 1e-3])
        steps.append(dict(parent=round(pc.excess, 3), est=round(best[0], 3), children=[round(l.excess, 3), round(r.excess, 3)]))
        pieces = pieces[1:] + [l, r]
        log(f'  split {len(pieces) - 1}->{len(pieces)}: excess {pc.excess:.2f} -> {l.excess:.2f} + {r.excess:.2f} cm3')
    for p in pieces:
        p.excess = abs(p.excess)
    hulls, rows, eqs = [], [], []
    for k, p in enumerate(sorted(pieces, key=lambda p: -len(p.idx))):
        V = reduce_hull(p.V, maxv); eq = ConvexHull(V).equations; h = trimesh.convex.convex_hull(V)
        hulls.append(V); eqs.append(eq)
        rows.append(dict(file=f'piece_{k:02d}.obj', verts=len(h.vertices), vol_cm3=round(h.volume * 1e6, 2), excess_cm3=round(p.excess, 3),
                         excess_after_reduce_cm3=round(int(inside(eq, FREE).sum()) * VOX, 3),
                         weighted_excess=round(float(FW[inside(eq, FREE)].sum() * VOX), 3)))
    cov = np.zeros(len(G), bool)
    for eq in eqs:
        cov |= inside(eq, G)
    ins = d < 0; fr = d > margin * 1e-3
    rep = dict(pitch_mm=round(pitch * 1e3, 2), tol_cm3=tol, max=max_pieces, margin_mm=margin, n_pieces=len(rows),
               solid_cm3=round(ins.sum() * VOX, 1), union_cm3=round(cov.sum() * VOX, 1),
               union_over_solid=round(cov.sum() / max(1, ins.sum()), 3), free_in_union_cm3=round((cov & fr).sum() * VOX, 2),
               solid_uncovered_cm3=round((ins & ~cov).sum() * VOX, 2),
               max_piece_excess_cm3=max(o['excess_after_reduce_cm3'] for o in rows), sec=round(time.time() - t0, 1),
               partner=list(partner) if partner else None, lam=lam, pieces=rows, log=steps)
    return hulls, rep


def write(hulls, rep, out):
    os.makedirs(out, exist_ok=True)
    for k, V in enumerate(hulls):
        trimesh.convex.convex_hull(V).export(f'{out}/piece_{k:02d}.obj')
    json.dump(rep, open(f'{out}/decomp.json', 'w'), indent=1)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('mesh'); ap.add_argument('out')
    ap.add_argument('--tol', type=float, default=0.3); ap.add_argument('--max', type=int, default=0)
    ap.add_argument('--pitch', type=float, default=0.0); ap.add_argument('--margin', type=float, default=0.75)
    ap.add_argument('--partner', nargs=5, metavar=('MESH_B', 'POSES', 'NAME_A', 'NAME_B', 'FRAMES'), default=None)
    ap.add_argument('--lam', type=float, default=10.0)
    a = ap.parse_args()
    m = trimesh.load(a.mesh, force='mesh')
    hulls, rep = decompose(m, tol=a.tol, max_pieces=a.max, pitch=a.pitch, margin=a.margin, partner=a.partner, lam=a.lam,
                           log=lambda *x: print(*x, flush=True))
    rep['mesh'] = a.mesh; write(hulls, rep, a.out)
    print(json.dumps({k: v for k, v in rep.items() if k not in ('pieces', 'log')}))


if __name__ == '__main__':
    main()
