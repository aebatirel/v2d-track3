"""c2 = c1 + budgeted merges + vertex welding (a NEW candidate; c1 is kept as measured).

Why (c1 measured [M]): the many small cut cells multiply the guest-rack and rack-table contact pairs (eval 14 pair
scene 552-612 rows, 10-16 of 16 copies over 512; packed 300-336), and C3's is_convex flag failed on slivers of 4-12 um.
What: starting from c1's pieces, greedy merges of piece pairs into their joint hull, cheapest first by the F' cells
(GATES.md Amendment 2: F beyond the 0.87 mm surface band) the merge adds; a merge may add new fill outside the packed
union only up to MERGE_MAX_CM3 and never where the guest goes at any frame of the scope's episodes; merging stops when
the F' cells added by all merges reach BUDGET_CM3 or the count reaches the packed count (43). Every written piece is
the convex hull of its vertices snapped to a 10 um grid (welds the slivers; moves the surface by <= 9 um).
BUDGET_CM3 = 0.5: half of G2b's 1.0 cm3 allowance (generic), so G2b stays <= c1's leftover + 0.5.

Usage: merge2.py SCOPE C1_DIR OUT_DIR
"""
import glob, json, os, sys, time
import numpy as np, trimesh
from scipy.spatial import ConvexHull, cKDTree
import rs_lib as L

BUDGET_CM3, MERGE_MAX_CM3, BAND, SNAP = 0.5, 2.0, 0.00087, 1e-5


def snap_hull(V):
    W = np.unique(np.round(V / SNAP) * SNAP, axis=0)
    m = trimesh.convex.convex_hull(W)
    return m


def main():
    scope, c1, out = sys.argv[1], sys.argv[2], sys.argv[3]
    eps = ['30', '14'] if scope == 'both' else [scope]
    os.makedirs(f'{out}/plastic_dish_rack', exist_ok=True)
    lf = open(f'{out}/build.log', 'w')

    def log(s):
        line = time.strftime('%H:%M:%S ', time.gmtime()) + s
        print(line, flush=True); lf.write(line + '\n'); lf.flush()
    t0 = time.time()
    Hp = L.load_hulls(L.RACK_PACKED); G = L.Grid(Hp)
    z0 = np.load(f'{L.SCR}/rackslot/grid_base.npz'); M, PK = z0['M'], z0['PK']
    rack = L.load_mesh(L.RACK_MESH)
    RV = np.zeros(G.n, bool); swept_all = []
    for ep in eps:
        R, _ = L.rest_frames(ep); P = L.poses(ep); gh = L.load_hulls(L.GUEST[ep]['packed'])
        RV |= L.rest_volume(G, gh, P['rel'], R, PK)
        swept_all.append((gh, P['rel']))
    S3 = np.asarray(trimesh.sample.sample_surface_even(rack, int(rack.area / 0.0003 ** 2), seed=3)[0])
    fi = np.argwhere(RV & PK & ~M)
    d = cKDTree(S3).query(G.lo + (fi + 0.5) * G.pitch)[0]
    Fp = np.zeros(G.n, bool); k = fi[d > BAND]; Fp[k[:, 0], k[:, 1], k[:, 2]] = True
    b1 = json.load(open(f'{c1}/build.json'))
    files = sorted(glob.glob(f'{c1}/plastic_dish_rack/piece_*.obj'))
    pieces = [dict(V=np.asarray(trimesh.load(f, force='mesh').vertices, float), tag=os.path.basename(f),
                   kind=b1['pieces'][i]['kind'], src=b1['pieces'][i]['src'], uid=i) for i, f in enumerate(files)]
    occs = [G.hull_occ(p['V']) for p in pieces]
    log(f"scope {scope}: c1 {len(pieces)} pieces, F' {Fp.sum() / 1e3:.2f} cm3, F' in c1 "
        f"{(Fp & np.any(occs, axis=0)).sum() / 1e3:.3f} cm3 ({time.time() - t0:.0f} s)")

    def in_swept_all(occ):
        return int(sum(L.rest_volume(G, gh, rel, list(range(len(rel))), occ).sum() for gh, rel in swept_all))
    cache, merges, spent, uid = {}, [], 0, len(pieces)

    def pair_eval(a, b):
        Va, Vb = pieces[a]['V'], pieces[b]['V']
        if np.any(Va.min(0) > Vb.max(0) + 0.002) or np.any(Vb.min(0) > Va.max(0) + 0.002):
            return None
        mo = G.hull_occ(np.vstack([Va, Vb]))
        added = mo & ~(occs[a] | occs[b])
        nf = int((added & ~PK).sum())
        if nf * 1e-3 > MERGE_MAX_CM3:
            return None
        return (int((added & Fp).sum()), nf, int(added.sum()))
    while len(pieces) > len(Hp):
        best = None
        for a in range(len(pieces)):
            for b in range(a + 1, len(pieces)):
                kk = (pieces[a]['uid'], pieces[b]['uid'])
                if kk not in cache:
                    cache[kk] = pair_eval(a, b)
                ev = cache[kk]
                if ev is None or spent + ev[0] > BUDGET_CM3 * 1e3:
                    continue
                if best is None or ev < best[0]:
                    best = (ev, a, b)
        if best is None:
            break
        (fa, nf, na), a, b = best
        if nf > 0:
            mo = G.hull_occ(np.vstack([pieces[a]['V'], pieces[b]['V']]))
            if in_swept_all(mo & ~(occs[a] | occs[b]) & ~PK) > 0:
                cache[(pieces[a]['uid'], pieces[b]['uid'])] = None
                continue
        Vm = np.vstack([pieces[a]['V'], pieces[b]['V']]); Vm = Vm[ConvexHull(Vm).vertices]
        spent += fa
        merges.append(dict(a=pieces[a]['tag'], b=pieces[b]['tag'], Fprime_cells_added=fa, new_fill_cells=nf,
                           added_cells=na, Fprime_spent_cm3=spent / 1e3))
        tag = f"({pieces[a]['tag']}+{pieces[b]['tag']})"
        srcs = [x for p in (pieces[a], pieces[b]) for x in (p['src'] if isinstance(p['src'], list) else [p['src']])]
        mo = G.hull_occ(Vm)
        pieces = [p for kq, p in enumerate(pieces) if kq not in (a, b)] + [dict(V=Vm, tag=tag, kind='merged', src=srcs, uid=uid)]
        occs = [o for kq, o in enumerate(occs) if kq not in (a, b)] + [mo]
        uid += 1
        log(f'merge {len(merges)}: +{fa} F\' cells (spent {spent / 1e3:.3f} cm3), new fill {nf}, -> {len(pieces)} pieces')
    out_files = []
    for kq, p in enumerate(pieces):
        m = snap_hull(p['V']) if p['kind'] != 'packed' else trimesh.convex.convex_hull(p['V'])
        f = f'{out}/plastic_dish_rack/piece_{kq:02d}.obj'
        m.export(f)
        m2 = trimesh.load(f, force='mesh')
        out_files.append(dict(file=os.path.basename(f), kind=p['kind'], src=p['src'], tag=p['tag'], verts=len(m2.vertices),
                              vol_cm3=round(m2.volume * 1e6, 3), convex=bool(m2.is_convex), watertight=bool(m2.is_watertight)))
    b2 = dict(b1, scope=scope, from_c1=c1.split('/')[-1], merges2=merges, pieces=out_files, n_pieces=len(out_files),
              constants2=dict(BUDGET_CM3=BUDGET_CM3, MERGE_MAX_CM3=MERGE_MAX_CM3, BAND=BAND, SNAP=SNAP),
              Fprime_spent_cm3=spent / 1e3, secs2=round(time.time() - t0, 1))
    json.dump(b2, open(f'{out}/build.json', 'w'), indent=1, default=float)
    log(f'done: {len(out_files)} pieces, F\' spent {spent / 1e3:.3f} cm3, non-convex flags '
        f'{sum(not x["convex"] for x in out_files)}, {time.time() - t0:.0f} s')


if __name__ == '__main__':
    main()
