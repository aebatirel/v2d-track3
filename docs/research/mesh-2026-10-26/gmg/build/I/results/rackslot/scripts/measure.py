"""Geometric gates G1, G1x, G2, G5 and construction checks C1-C3 (GATES.md) for one rack piece set on one or more
episodes. The packed rack is measured the same way (SET = packed).

Usage: measure.py SET OUT.json EPS     SET: a folder holding plastic_dish_rack/piece_*.obj, or 'packed'; EPS: 30,14
"""
import glob, json, os, subprocess, sys, time
import numpy as np, trimesh
from scipy.spatial import ConvexHull, cKDTree
import rs_lib as L, vox

P_GUEST = 0.0015
G1_MED, G1_MAX, G2_MAX, G5_MIN = 1.0, 3.0, 1.0, 0.90
C2_CELLS_CM3, C2_SURF_MM = 0.1, 0.5
BAND = 0.00087        # GATES.md Amendment 2: G2b counts swept cells more than half a cell diagonal from the mesh surface
COACD_TARGET = f'{L.SCR}/coacd1011'


def load_set(s):
    if s == 'packed':
        return L.load_hulls(L.RACK_PACKED), None
    fs = sorted(glob.glob(f'{s}/plastic_dish_rack/piece_*.obj'))
    return [np.asarray(trimesh.load(f, force='mesh').vertices, float) for f in fs], fs


def lookup(G, occ, X):
    ijk = np.floor((X - G.lo) / G.pitch).astype(int)
    ok = np.all((ijk >= 0) & (ijk < G.n), 1)
    out = np.zeros(len(X), bool)
    out[ok] = occ[ijk[ok, 0], ijk[ok, 1], ijk[ok, 2]]
    return out


def union_pts(hulls, pitch):
    """1.5 mm cell centres of the union of convex hulls (the precheck's guest points)."""
    allv = np.vstack(hulls); lo = allv.min(0) - 0.002; hi = allv.max(0) + 0.002
    g = L.Grid.__new__(L.Grid); g.lo = lo; g.n = np.ceil((hi - lo) / pitch).astype(int); g.pitch = pitch
    return g.centres(g.union_occ(hulls))


def coacd_check(files):
    code = r'''
import sys, json, numpy as np, trimesh
sys.path.insert(0, sys.argv[1]); import coacd
coacd.set_log_level('error')
out = []
for f in sys.argv[2:]:
    m = trimesh.load(f, force='mesh')
    parts = coacd.run_coacd(coacd.Mesh(np.ascontiguousarray(m.vertices, np.float64), np.ascontiguousarray(m.faces, np.int64)),
                            threshold=0.05, max_convex_hull=-1, preprocess_mode='auto')
    v = sum(trimesh.convex.convex_hull(np.asarray(p[0])).volume for p in parts)
    out.append(dict(file=f.split('/')[-1], parts=len(parts), vol_ratio=float(v / m.volume)))
print(json.dumps(out))
'''
    r = subprocess.run([sys.executable, '-I', '-c', code, COACD_TARGET] + files, capture_output=True, text=True)
    return json.loads(r.stdout.strip().splitlines()[-1])


def main():
    sset, out, eps = sys.argv[1], sys.argv[2], sys.argv[3].split(',')
    t0 = time.time()
    H, files = load_set(sset)
    Hp = L.load_hulls(L.RACK_PACKED)
    G = L.Grid(Hp)
    z0 = np.load(f'{L.SCR}/rackslot/grid_base.npz'); M, PK = z0['M'], z0['PK']
    CO = PK.copy() if sset == 'packed' else G.union_occ(H)
    v1 = G.pitch ** 3 * 1e6; vg = P_GUEST ** 3 * 1e6
    res = dict(set=sset, n_pieces=len(H), eps={}, union_cm3=round(CO.sum() * v1, 2),
               vol_sum_cm3=round(sum(ConvexHull(V).volume for V in H) * 1e6, 2))
    # C1-C3
    res['C1'] = dict(n=len(H), packed=len(Hp), pass_=len(H) <= len(Hp))
    lost = (M & PK & ~CO).sum() * v1
    c2 = dict(mesh_cells_lost_cm3=round(lost, 4))
    if sset != 'packed':
        rack = L.load_mesh(L.RACK_MESH)
        Sm = np.asarray(trimesh.sample.sample_surface_even(rack, int(rack.area / 0.00025 ** 2), seed=7)[0])
        eqp = [ConvexHull(V).equations for V in Hp]
        eqc = [ConvexHull(V).equations for V in H]
        def inside_any(eqs, Hs, X):
            m = np.zeros(len(X), bool)
            for e, V in zip(eqs, Hs):
                bb = np.all((X >= V.min(0) - 1e-9) & (X <= V.max(0) + 1e-9), 1) & ~m
                j = np.nonzero(bb)[0]
                if len(j):
                    m[j[np.all(X[j] @ e[:, :3].T + e[:, 3] <= 1e-9, 1)]] = True
            return m
        inP = inside_any(eqp, Hp, Sm)
        X = Sm[inP]
        outC = ~inside_any(eqc, H, X)
        d = 0.0
        if outC.any():
            Y = X[outC]
            dist = np.full(len(Y), np.inf)
            for V in H:
                m = trimesh.convex.convex_hull(V)
                dist = np.minimum(dist, np.abs(trimesh.proximity.signed_distance(m, Y)))
            d = float(dist.max() * 1e3)
        c2.update(surface_samples_in_packed=int(inP.sum()), outside_candidate=int(outC.sum()), max_out_mm=round(d, 3))
        c2['pass_'] = bool(lost <= C2_CELLS_CM3 and d <= C2_SURF_MM)
        meshes = [trimesh.load(f, force='mesh') for f in files]
        geo = [dict(file=os.path.basename(f), watertight=bool(m.is_watertight), convex=bool(m.is_convex),
                    vol_cm3=round(m.volume * 1e6, 3), verts=len(m.vertices)) for f, m in zip(files, meshes)]
        cc = coacd_check(files)
        c3ok = all(g['watertight'] and g['convex'] and g['vol_cm3'] > 0 for g in geo) and \
            all(c['parts'] == 1 and abs(c['vol_ratio'] - 1) <= 0.01 for c in cc)
        res['C3'] = dict(pass_=bool(c3ok), pieces=[dict(g, **{k: v for k, v in c.items() if k != 'file'})
                                                   for g, c in zip(geo, cc)])
    else:
        c2['pass_'] = True
        res['C3'] = dict(pass_=True, note='packed: FlashCHORD hulls themselves')
    res['C2'] = c2
    rack3 = L.load_mesh(L.RACK_MESH)
    surf3 = np.asarray(trimesh.sample.sample_surface_even(rack3, int(rack3.area / 0.0003 ** 2), seed=3)[0])
    for ep in eps:
        R, info = L.rest_frames(ep); P = L.poses(ep)
        gh = L.load_hulls(L.GUEST[ep]['packed'])
        gm = L.load_mesh(L.GUEST[ep]['mesh'])
        RV = L.rest_volume(G, gh, P['rel'], R, PK | CO)
        Xp = union_pts(gh, P_GUEST)
        Xm = vox.voxelize(gm, P_GUEST).centres()
        rows = []
        for f in R:
            T = P['rel'][f]
            A = Xp @ T[:3, :3].T + T[:3, 3]; B = Xm @ T[:3, :3].T + T[:3, 3]
            a_c, a_m = lookup(G, CO, A), lookup(G, M, A)
            b_c, b_m = lookup(G, CO, B), lookup(G, M, B)
            rows.append(dict(frame=int(f), V_pp=a_c.sum() * vg, V_pm=a_m.sum() * vg, V_vv=b_m.sum() * vg,
                             E=(a_c.sum() - a_m.sum()) * vg, beyond_packed_guest=(a_c & ~a_m).sum() * vg,
                             beyond_mesh_guest=(b_c & ~b_m).sum() * vg))
        col = lambda k: np.array([r[k] for r in rows])
        g1 = dict(median=float(np.median(col('V_pp'))), max=float(col('V_pp').max()),
                  floor_vv_median=float(np.median(col('V_vv'))), floor_vv_max=float(col('V_vv').max()),
                  floor_pm_median=float(np.median(col('V_pm'))), floor_pm_max=float(col('V_pm').max()))
        g1['pass_'] = bool(g1['median'] <= G1_MED and g1['max'] <= G1_MAX)
        g1['floor_blocks'] = bool(g1['floor_pm_median'] > G1_MED or g1['floor_pm_max'] > G1_MAX)
        g1x = dict(median=float(np.median(col('E'))), max=float(col('E').max()), min=float(col('E').min()))
        g1x['pass_'] = bool(g1x['median'] <= G1_MED and g1x['max'] <= G1_MAX)
        swc = G.centres(RV & CO & ~M)
        dsw = cKDTree(surf3).query(swc)[0] if len(swc) else np.zeros(0)
        sw = len(swc) * v1
        sw_b = float((dsw > BAND).sum()) * v1
        g2 = dict(swept_cm3=round(sw, 3), pass_as_written=bool(sw <= G2_MAX), G2b_beyond_band_cm3=round(sw_b, 3),
                  band_mm=BAND * 1e3, per_frame_max_guest_packed=float(col('beyond_packed_guest').max()),
                  per_frame_max_guest_mesh=float(col('beyond_mesh_guest').max()), pass_=bool(sw_b <= G2_MAX))
        base = (PK & ~RV).sum(); kept = (CO & PK & ~RV).sum()
        g5 = dict(kept_ratio=round(kept / base, 4), packed_outside_RV_cm3=round(base * v1, 2),
                  lost_cm3=round((base - kept) * v1, 2), added_outside_packed_cm3=round((CO & ~PK).sum() * v1, 3),
                  pass_=bool(kept / base >= G5_MIN))
        res['eps'][ep] = dict(R=info['runs'], n_R=len(R), RV_cm3=round(RV.sum() * v1, 2), G1=g1, G1x=g1x, G2=g2,
                              G5=g5, rows=[{k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()}
                                           for r in rows])
        print(ep, json.dumps({k: res['eps'][ep][k] for k in ('G1', 'G1x', 'G2', 'G5')}), flush=True)
    res['secs'] = round(time.time() - t0, 1)
    print(json.dumps({k: res[k] for k in ('n_pieces', 'union_cm3', 'C1', 'C2')}), 'C3', res['C3'].get('pass_'))
    json.dump(res, open(out, 'w'), indent=1, default=float)


if __name__ == '__main__':
    main()
