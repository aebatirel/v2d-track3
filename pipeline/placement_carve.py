"""Collision-copy placement carve (2026-10-30; H5 follow-up: evals 1, 14, 28, 30 have reference poses at rest that
the default collision hulls cannot reach). GT-free: our meshes and our own reference parquet, nothing else.

FlashCHORD replaces every collision mesh by CoACD hulls (threshold 0.05), which fill cavities and gaps (rack slots,
the pot's mouth, the lid's underside), and our reconstructed meshes are closed solids. Where our reference puts a
GUEST at rest on or in a HOST (cup in the rack, sweeper in the rack, lid on the pot, pot on the rack), the two hull
sets overlap: the simulator pushes them apart and the policy is asked to hold a pose physics will not keep. This tool
changes only the SIMULATOR collision copy, never the submitted mesh (CD-O, registration and visuals are untouched):

  place ASSETS REF.parquet --host H --guest G --out OUT_DIR
    1. meshes ASSETS/mesh/<n>/<n>.glb as make_assets.py writes them; hulls = FlashCHORD's own convex_decompose
       (interaction_carve.fc_hulls: same function, same parameters), i.e. the hulls the simulator builds today;
    2. rest-contact frames: the guest is still RELATIVE to the host (5-frame median < 0.2 cm and < 1 deg per frame;
       world motion allowed, e.g. a lid riding on a carried pot) and its hulls overlap the host's hulls by > 0.3 cm3
       (3 mm grid); runs of >= 5 such frames form segments; the last one is the placement ("placed" = its first
       frame), one that contains frame 0 is the initial rest; --segments ends (v3) claims from these two only,
       dropping intermediate (often hand-held) segments;
    3. the claim, on a 1.5 mm grid over up to 40 segment frames: every point inside the host's hulls that is
       (a) within MARGIN (1.5 mm) of the guest's solid (signed distance), or (b) within MARGIN of the guest's hulls
       but not inside the host's own solid (fill against fill). Mutual case: host solid (+MARGIN) inside the guest's
       hull FILL (outside the guest's solid) is real host material (a rim, a prong) that the guest's cavity fill
       swallows; if it is >= 0.5 cm3 it is removed from the GUEST's hulls instead and kept in the host (cutting the
       host there would remove the material the guest rests on). Below 0.5 cm3 the guest stays unchanged and the
       host takes all of (a) + (b). By construction the carved hull sets do not overlap at the claim frames;
    4. every hull that holds claim points is replaced by its convex parts outside a cover of those points: an
       oriented box (PCA) of the hull's claim points, split at the median along its longest axis (one level) while
       the box is > 3x the claim's volume; each box removes at most 6 disjoint convex parts (one per face). Hulls
       without claim points stay whole. Pieces < 2e-8 m3 or thinner than a 0.2 mm inscribed ball are dropped;
    5. hull-hull overlap (guest's hulls inside the host's hulls, 1.5 mm grid, cm3) before and after at frame 0, the
       placed frame, all rest-contact frames and a stride-4 sample of every frame;
    6. writes OUT_DIR/<name>/piece_XX.obj for every carved object (one convex piece each; make_assets.py --pieces, or
       the 'assets' mode here, turns them into one <collision> each, which FlashCHORD's CoACD keeps unchanged) and
       OUT_DIR/carve.json.

  assets SRC_ASSETS CARVE_DIR OUT_ASSETS
    copy of SRC_ASSETS whose URDFs for the carved objects list the pieces as <collision> elements (visual mesh and
    inertial unchanged), for the settle test and training.

Needs NVIDIA Warp and FlashCHORD: run in the FlashCHORD venv, CPU. Method notes: docs/research/notes/19-collision-hulls.md,
25-support-consistent-meshes.md; the slot carve for the boards is interaction_carve.py.
"""
import argparse, glob, json, os, re, shutil, sys, time

import numpy as np
import trimesh
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation as R

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from collision_decomp import SignedDistance, inside  # noqa: E402
from interaction_carve import clip, fc_hulls, load_mesh, ref_poses  # noqa: E402

PITCH, COARSE, MARGIN = 0.0015, 0.003, 0.0015
REST_CM, REST_DEG, CONTACT_CM3, MIN_SEG, MAX_FR = 0.2, 1.0, 0.3, 5, 40
MUTUAL_CM3, DEBRIS_M3, FILL, DEPTH, MIN_PTS = 0.5, 2e-8, 3.0, 1, 3


class Hulls:
    """Convex hulls with facet equations and AABBs for fast point membership."""

    def __init__(self, hulls):
        self.V = [np.asarray(V, float) for V in hulls]
        self.EQ = [ConvexHull(V).equations for V in self.V]
        self.lo = np.array([V.min(0) for V in self.V]); self.hi = np.array([V.max(0) for V in self.V])

    def member(self, X, tol=0.0):
        """Index of the first hull containing each point (-1: none); tol offsets every facet outward (m)."""
        out = np.full(len(X), -1)
        for k, eq in enumerate(self.EQ):
            sel = np.flatnonzero((out < 0) & np.all(X > self.lo[k] - tol, 1) & np.all(X < self.hi[k] + tol, 1))
            if len(sel):
                out[sel[inside(eq, X[sel], tol=tol + 1e-9)]] = k
        return out

    def volume(self):
        return float(sum(ConvexHull(V).volume for V in self.V))


def grid(lo, hi, p):
    n = np.ceil((hi - lo) / p).astype(int) + 1
    return np.stack(np.meshgrid(*[lo[k] + p * np.arange(n[k]) for k in range(3)], indexing='ij'), -1).reshape(-1, 3)


def hull_grid(H, p):
    """Grid points (pitch p) inside the union of the hulls: the collision solid."""
    P = np.vstack(H.V); G = grid(P.min(0) - p, P.max(0) + p, p)
    return G[H.member(G) >= 0]


def apply(T, X):
    return X @ T[:3, :3].T + T[:3, 3]


def overlap_cm3(Hhost, Gguest, rel, frames, p):
    """Volume of the guest's collision solid (grid Gguest, pitch p, guest frame) inside the host's hulls, per frame."""
    v = p ** 3 * 1e6; lo, hi = Hhost.lo.min(0), Hhost.hi.max(0); out = []
    for f in frames:
        X = apply(rel[f], Gguest); X = X[np.all((X > lo) & (X < hi), 1)]
        out.append(float((Hhost.member(X) >= 0).sum() * v))
    return np.array(out)


def med5(x):
    return np.array([np.median(x[max(0, i - 2):i + 3]) for i in range(len(x))])


def segments(mask, min_len):
    out, i = [], 0
    while i < len(mask):
        if mask[i]:
            j = i
            while j + 1 < len(mask) and mask[j + 1]:
                j += 1
            if j - i + 1 >= min_len:
                out.append([i, j])
            i = j + 1
        else:
            i += 1
    return out


def box_planes(c, U, e):
    """Six (n, d) half-spaces n.x + d <= 0 of an oriented box (centre c, axes = columns of U, half extents e)."""
    pl = []
    for k in range(3):
        for s in (1.0, -1.0):
            n = s * U[:, k]; pl.append((n, -(n @ c + e[k])))
    return pl


def cover(P, vox, depth=0):
    """Oriented boxes covering points P (claim voxels of volume vox, m3): PCA box, median split while loose."""
    c0 = P.mean(0)
    if len(P) >= 4:
        w, U = np.linalg.eigh(np.cov((P - c0).T)); U = U[:, ::-1]
    else:
        U = np.eye(3)
    s = (P - c0) @ U; lo, hi = s.min(0) - PITCH, s.max(0) + PITCH
    e = (hi - lo) / 2; c = c0 + U @ ((hi + lo) / 2)
    if depth < DEPTH and len(P) > 50 and np.prod(2 * e) > FILL * len(P) * vox:
        k = int(np.argmax(e)); m = np.median(s[:, k]); L = s[:, k] <= m
        if 0 < L.sum() < len(P):
            return cover(P[L], vox, depth + 1) + cover(P[~L], vox, depth + 1)
    return [(c, U, e)]


def subtract_boxes(V, boxes):
    """Convex parts of hull V outside every box (sequential: each box splits each part into <= 6 disjoint parts)."""
    parts = [V]
    for c, U, e in boxes:
        pl = box_planes(c, U, e); nxt = []
        for P in parts:
            if clip(P, pl) is None:
                nxt.append(P); continue
            for i in range(6):
                n, d = pl[i]; Q = clip(P, [(-n, -d)] + pl[:i])   # outside face i, inside faces 0..i-1
                if Q is not None:
                    nxt.append(Q)
        parts = nxt
    return parts


def carve_hulls(H, X):
    """Replace every hull of H holding claim points X (host-frame, grid) by its parts outside a box cover of them."""
    owner = H.member(X); vox = PITCH ** 3; out, info, dropped = [], [], [0, 0.0]
    for k, V in enumerate(H.V):
        P = X[owner == k]
        if len(P) < MIN_PTS:
            out.append(V); continue
        boxes = cover(P, vox); parts = []
        for Q in subtract_boxes(V, boxes):
            vol = ConvexHull(Q).volume
            if vol < DEBRIS_M3:
                dropped[0] += 1; dropped[1] += vol
            else:
                parts.append(Q)
        out += parts
        info.append(dict(hull=k, claim_cm3=round(len(P) * vox * 1e6, 2), boxes=len(boxes), parts=len(parts),
                         hull_cm3=round(ConvexHull(V).volume * 1e6, 2),
                         kept_cm3=round(sum(ConvexHull(Q).volume for Q in parts) * 1e6, 2)))
    return out, info, dict(n=dropped[0], cm3=round(dropped[1] * 1e6, 4))


def place(a):
    t_start = time.time()
    names = [a.host, a.guest]
    mesh = {n: load_mesh(f'{a.assets}/mesh/{n}/{n}.glb') for n in names}
    sd = {n: SignedDistance(mesh[n]) for n in names}
    H = {n: Hulls(fc_hulls(mesh[n])) for n in names}
    TH, TG = ref_poses(a.ref, names); nF = len(TH); rel = np.linalg.inv(TH) @ TG             # guest in host, per frame
    v, vc = PITCH ** 3 * 1e6, COARSE ** 3 * 1e6

    # 2. rest-contact frames
    sp = np.r_[0, np.linalg.norm(np.diff(rel[:, :3, 3], axis=0), axis=1) * 100]
    ang = np.r_[0, np.degrees(R.from_matrix(np.einsum('fij,fkj->fik', rel[1:, :3, :3], rel[:-1, :3, :3])).magnitude())]
    still = (med5(sp) < a.rest_cm) & (med5(ang) < a.rest_deg)
    Gc = hull_grid(H[a.guest], COARSE); fr2 = np.arange(0, nF, 2)
    oc = np.interp(np.arange(nF), fr2, overlap_cm3(H[a.host], Gc, rel, fr2, COARSE))
    segs = segments(still & (oc > CONTACT_CM3), MIN_SEG)
    rep = dict(tool='placement_carve place', assets=a.assets, ref=a.ref, host=a.host, guest=a.guest, frames=nF,
               margin_mm=a.margin * 1e3, pitch_mm=PITCH * 1e3, rest_cm=a.rest_cm, rest_deg=a.rest_deg, rest_contact_segments=segs,
               coarse_overlap_cm3_max=round(float(oc.max()), 2), coarse_overlap_argmax=int(np.argmax(oc)),
               hulls_default={n: len(H[n].V) for n in names},
               hull_cm3_default={n: round(H[n].volume() * 1e6, 1) for n in names})
    if not segs:
        rep.update(carved=False, reason='no rest-contact segment'); return rep
    if a.segments == 'ends':                                     # placement only: initial rest + final placement
        segs = ([segs[0]] if segs[0][0] == 0 and len(segs) > 1 else []) + [segs[-1]]
    rep.update(segments_mode=a.segments, claim_segments=segs)
    placed = segs[-1][0]; initial = segs[0][0] if segs[0][0] == 0 else None
    seg_fr = np.concatenate([np.arange(s, e + 1) for s, e in segs])
    claim_fr = seg_fr[np.unique(np.linspace(0, len(seg_fr) - 1, min(MAX_FR, len(seg_fr))).round().astype(int))]
    rep.update(placed_frame=int(placed), initial_rest_frame=initial, claim_frames=claim_fr.tolist())

    # 3. claim: guest-frame candidate points near the guest's solid or hulls
    mg = load_mesh(f'{a.assets}/mesh/{a.guest}/{a.guest}.glb')
    Pg = np.vstack(H[a.guest].V); lo = np.minimum(Pg.min(0), mg.bounds[0]) - 2 * a.margin
    hi = np.maximum(Pg.max(0), mg.bounds[1]) + 2 * a.margin; G = grid(lo, hi, PITCH)
    dg = sd[a.guest](G); in_hg_m = H[a.guest].member(G, tol=a.margin) >= 0
    keep = (dg < a.margin) | in_hg_m; G, dg, in_hg_m = G[keep], dg[keep], in_hg_m[keep]
    in_hg = H[a.guest].member(G) >= 0
    lo_h, hi_h = H[a.host].lo.min(0) - a.margin, H[a.host].hi.max(0) + a.margin
    claim_a, claim_b, mut = [], [], np.zeros(len(G), bool)        # (a) guest solid, (b) fill-fill / host-in-fill
    for f in claim_fr:
        X = apply(rel[f], G); box = np.all((X > lo_h) & (X < hi_h), 1); idx = np.flatnonzero(box)
        if not len(idx):
            continue
        dh = sd[a.host](X[idx]); inH = H[a.host].member(X[idx]) >= 0
        A = inH & (dg[idx] < a.margin)
        B = inH & ~A & in_hg_m[idx]
        Bfill = B & (dh >= 0)                                    # fill against fill: always the host's
        Bhost = B & (dh < 0)                                     # host material in the guest's (offset) hull fill
        mut[idx[in_hg[idx] & (dg[idx] >= 0) & (dh < a.margin)]] = True
        claim_a.append(X[idx[A]]); claim_b.append((X[idx[Bfill]], X[idx[Bhost]]))
    Xa = np.vstack(claim_a) if claim_a else np.zeros((0, 3))
    Xbf = np.vstack([b[0] for b in claim_b]) if claim_b else np.zeros((0, 3))
    Xbh = np.vstack([b[1] for b in claim_b]) if claim_b else np.zeros((0, 3))
    q = lambda X: np.unique(np.round(X / PITCH).astype(np.int64), axis=0) * PITCH if len(X) else X   # dedupe on grid
    Xa, Xbf, Xbh = q(Xa), q(Xbf), q(Xbh); Gm = G[mut]
    mutual_cm3 = len(Gm) * v; mutual = mutual_cm3 >= MUTUAL_CM3
    Xhost = np.vstack([Xa, Xbf] + ([] if mutual else [Xbh]))
    rep.update(claim_cm3=dict(guest_solid=round(len(Xa) * v, 2), fill_fill=round(len(Xbf) * v, 2),
                              host_material_in_guest_fill=round(len(Xbh) * v, 2), guest_side_mutual=round(mutual_cm3, 2)),
               mutual=bool(mutual))

    # 4. carve
    cut = {}
    hh, info_h, drop_h = carve_hulls(H[a.host], Xhost); cut[a.host] = (hh, info_h, drop_h)
    if mutual:
        hg, info_g, drop_g = carve_hulls(H[a.guest], Gm); cut[a.guest] = (hg, info_g, drop_g)
    Hc = {n: Hulls(cut[n][0]) if n in cut else H[n] for n in names}

    # 5. overlap before / after
    chk = sorted(set(range(0, nF, 4)) | set(seg_fr.tolist()) | {0, placed, nF - 1})
    Gd = hull_grid(H[a.guest], PITCH); Gcut = Gd[Hc[a.guest].member(Gd) >= 0]          # same grid before / after
    od = overlap_cm3(H[a.host], Gd, rel, chk, PITCH); ok = overlap_cm3(Hc[a.host], Gcut, rel, chk, PITCH)
    ci = {f: i for i, f in enumerate(chk)}; segi = [ci[f] for f in seg_fr]
    rep['overlap_cm3'] = dict(
        placed=[round(od[ci[placed]], 2), round(ok[ci[placed]], 2)],
        frame0=[round(od[ci[0]], 2), round(ok[ci[0]], 2)], last=[round(od[ci[nF - 1]], 2), round(ok[ci[nF - 1]], 2)],
        rest_max=[round(float(od[segi].max()), 2), round(float(ok[segi].max()), 2)],
        rest_mean=[round(float(od[segi].mean()), 2), round(float(ok[segi].mean()), 2)],
        all_max=[round(float(od.max()), 2), round(float(ok.max()), 2)], all_argmax=int(chk[int(np.argmax(od))]),
        max_increase=round(float((ok - od).max()), 3), checked_frames=len(chk), note='[default, carved]')
    rep['overlap_cm3']['placed_reduction_pct'] = round(100 * (1 - ok[ci[placed]] / od[ci[placed]]), 1) if od[ci[placed]] > 0 else None
    for n, (hs, info, drop) in cut.items():
        vols = [ConvexHull(V).volume for V in hs]
        rep[f'carve_{n}'] = dict(hulls_before=len(H[n].V), hulls_touched=len(info), pieces=len(hs),
                                 hull_cm3_before=round(H[n].volume() * 1e6, 1), hull_cm3_after=round(sum(vols) * 1e6, 1),
                                 min_piece_m3=float(min(vols)), dropped=drop, touched=info)
    os.makedirs(a.out, exist_ok=True)
    for n, (hs, _, _) in cut.items():
        d = f'{a.out}/{n}'; os.makedirs(d, exist_ok=True)
        for old in glob.glob(f'{d}/piece_*.obj'):
            os.remove(old)
        for k, V in enumerate(hs):
            trimesh.convex.convex_hull(V).export(f'{d}/piece_{k:02d}.obj')
    rep.update(carved=True, carved_objects=list(cut), sec=round(time.time() - t_start, 1))
    return rep


def assets(a):
    if os.path.exists(a.out_assets):
        shutil.rmtree(a.out_assets)
    shutil.copytree(a.src_assets, a.out_assets)
    done = []
    for d in sorted(glob.glob(f'{a.carve_dir}/*/')):
        n = os.path.basename(d.rstrip('/')); pcs = sorted(glob.glob(f'{d}/piece_*.obj'))
        if not pcs:
            continue
        cols = []
        for k, p in enumerate(pcs):
            shutil.copy(p, f'{a.out_assets}/mesh/{n}/col_{k:02d}.obj')
            cols.append(f'    <collision>\n      <origin xyz="0 0 0" rpy="0 0 0"/>\n      <geometry><mesh filename='
                        f'"../mesh/{n}/col_{k:02d}.obj" scale="1 1 1"/></geometry>\n    </collision>')
        u = f'{a.out_assets}/urdf/{n}_rigid.urdf'; s = open(u).read()
        s2 = re.sub(r'\s*<collision>.*?</collision>', '', s, flags=re.S)
        s2 = s2.replace('  </link>', '\n'.join(cols) + '\n  </link>', 1)
        assert s2.count('<collision>') == len(pcs), u
        open(u, 'w').write(s2); done.append([n, len(pcs)])
    print(json.dumps(dict(out=a.out_assets, carved=done)))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='mode', required=True)
    s = sub.add_parser('place'); s.add_argument('assets'); s.add_argument('ref')
    s.add_argument('--host', required=True); s.add_argument('--guest', required=True); s.add_argument('--out', required=True)
    s.add_argument('--margin', type=float, default=MARGIN)
    s.add_argument('--segments', choices=['all', 'ends'], default='all',
                   help="claim from every rest-contact segment, or only the one at frame 0 and the last ('ends', v3)")
    s.add_argument('--rest_cm', type=float, default=REST_CM); s.add_argument('--rest_deg', type=float, default=REST_DEG)
    s2 = sub.add_parser('assets'); s2.add_argument('src_assets'); s2.add_argument('carve_dir'); s2.add_argument('out_assets')
    a = ap.parse_args()
    if a.mode == 'assets':
        return assets(a)
    rep = place(a)
    os.makedirs(a.out, exist_ok=True)
    json.dump(rep, open(f'{a.out}/carve.json', 'w'), indent=1)
    print(json.dumps({k: v for k, v in rep.items() if k not in ('claim_frames',) and not k.startswith('carve_')}))
    for k, x in rep.items():
        if k.startswith('carve_'):
            print(k, json.dumps({kk: vv for kk, vv in x.items() if kk != 'touched'}))


if __name__ == '__main__':
    main()
