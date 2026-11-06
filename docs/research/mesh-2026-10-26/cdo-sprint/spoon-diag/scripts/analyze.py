"""Spoon vs blue cup (evals 32, 33) and spoon vs dish rack (eval 16): does the simulator's collision geometry block what
our reference asks? GT-free: reads only the object pose columns of OUR packed reference parquets (ref_gl_ilc.parquet)
and OUR meshes (simulator assets of the packed runs, library_v3, the C0 blue-cup lathe profile).

Containers are tested three ways:
  vis   - solid of the visual / simulator mesh (exact parity voxelisation, 1 mm);
  hull  - union of the CoACD pieces (FlashCHORD call: threshold 0.05, max_convex_hull -1, preprocess auto; run_coacd.py);
  lathe - (cup only) the C0 lathe ep21_blue_cup_g1, analytic solid of revolution from its .lathe.json profile.
Spoon solid = the spoon simulator mesh voxelised at SPOON_PITCH, posed per frame in the container frame.
Usage: analyze.py SCRIPTS_DIR CONFIG.json OUT_DIR
"""
import json, sys, time
import numpy as np
import pyarrow.parquet as pq
from scipy.ndimage import distance_transform_edt
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation as R

sys.path.insert(0, sys.argv[1]); import vox  # noqa: E402

cfg = json.load(open(sys.argv[2])); OUT = sys.argv[3]
PITCH = 0.001; SPOON_PITCH = 0.0015; WALL = 0.003
cm3 = lambda n, p: float(n) * p ** 3 * 1e6


def ref_poses(path):
    t = pq.read_table(path, columns=['object_body_names', 'object_body_position', 'object_body_wxyz']).to_pylist()[0]
    names = list(t['object_body_names']); pos = np.array(t['object_body_position'], float)
    q = np.array(t['object_body_wxyz'], float)[..., [1, 2, 3, 0]]
    T = np.tile(np.eye(4), (len(pos), len(names), 1, 1))
    T[..., :3, :3] = R.from_quat(q.reshape(-1, 4)).as_matrix().reshape(len(pos), len(names), 3, 3); T[..., :3, 3] = pos
    return names, T


def load_hulls(npz):
    d = np.load(npz); H = [np.asarray(d[f'v{i}'], float) for i in range(int(d['n']))]
    eqs = [ConvexHull(h).equations for h in H]
    return H, eqs, [(h.min(0), h.max(0)) for h in H]


def hull_test(eqs, boxes, P):
    """inside-any-hull mask and penetration depth (max over containing pieces of the distance to that piece's surface)."""
    ins = np.zeros(len(P), bool); pen = np.zeros(len(P))
    for e, (lo, hi) in zip(eqs, boxes):
        cand = np.flatnonzero(np.all((P >= lo - 1e-9) & (P <= hi + 1e-9), 1))
        if not len(cand):
            continue
        s = P[cand] @ e[:, :3].T + e[:, 3]
        smax = s.max(1); inn = smax <= 1e-9
        ins[cand[inn]] = True; pen[cand[inn]] = np.maximum(pen[cand[inn]], -smax[inn])
    return ins, pen


def pip(px, py, poly):
    """point-in-polygon (even-odd) for arrays px, py against a closed polygon (N,2)."""
    x = poly[:, 0]; y = poly[:, 1]; xj = np.roll(x, 1); yj = np.roll(y, 1)
    out = np.zeros(px.shape, bool)
    for a, b, c, d in zip(x, y, xj, yj):
        cond = ((b > py) != (d > py))
        with np.errstate(divide='ignore', invalid='ignore'):
            xi = (c - a) * (py - b) / (d - b) + a
        out ^= cond & (px < xi)
    return out


class Lathe:
    def __init__(self, path):
        d = json.load(open(path)); self.c = np.array(d['centre']); self.a = np.array(d['axis']) / np.linalg.norm(d['axis'])
        self.poly = np.array(d['profile'])

    def rh(self, P):
        v = P - self.c; h = v @ self.a; r = np.linalg.norm(v - np.outer(h, self.a), axis=1); return r, h

    def inside(self, P):
        r, h = self.rh(P); return pip(r, h, self.poly)


def cup_frame(g):
    """axis and radial profile of the cup from its own solid: per 1 mm slice along the PCA axis the convex hull of the
    solid section (centroid -> axis line fit; area-equivalent radius -> R_out). h = 0 at the base, rim = top of the wall."""
    P = g.centres(); c0 = P.mean(0)
    w, U = np.linalg.eigh(np.cov((P - c0).T)); ax = U[:, np.argmax(w)]
    s = (P - c0) @ ax
    # orient the axis base -> opening: the opening end has the hollower last 3 cm
    def fill(sel):
        Q = P[sel] - c0; return len(Q)
    lo_n = fill(s < s.min() + 0.03); hi_n = fill(s > s.max() - 0.03)
    if hi_n > lo_n:
        ax = -ax; s = -s
    e1 = np.cross(ax, [1, 0, 0]); e1 = e1 if np.linalg.norm(e1) > 0.3 else np.cross(ax, [0, 1, 0]); e1 /= np.linalg.norm(e1)
    e2 = np.cross(ax, e1)
    hs = np.arange(s.min(), s.max() + PITCH, PITCH); cents, areas, hv = [], [], []
    for h0 in hs:
        sel = (s >= h0) & (s < h0 + PITCH)
        if sel.sum() < 30:
            continue
        Q = P[sel] - c0; q = np.stack([Q @ e1, Q @ e2], 1)
        try:
            ch = ConvexHull(q)
        except Exception:
            continue
        vtx = q[ch.vertices]; A = ch.volume                          # 2-D hull: vertices counter-clockwise, volume = area
        x, y = vtx[:, 0], vtx[:, 1]; xs, ys = np.roll(x, -1), np.roll(y, -1); cr = x * ys - xs * y; As = cr.sum() / 2
        cx = ((x + xs) * cr).sum() / (6 * As); cy = ((y + ys) * cr).sum() / (6 * As)
        cents.append([cx, cy]); areas.append(A); hv.append(h0 + PITCH / 2)
    cents, areas, hv = map(np.array, (cents, areas, hv))
    big = areas > 300e-6                                           # sections of at least 3 cm^2 (drops floating specks)
    base_s, rim_s = hv[big].min() - PITCH / 2, hv[big].max() + PITCH / 2
    k = big & (hv > base_s + 0.01) & (hv < rim_s - 0.005)
    A_ = np.c_[np.ones(k.sum()), hv[k]]
    cx = np.linalg.lstsq(A_, cents[k, 0], rcond=None)[0]; cy = np.linalg.lstsq(A_, cents[k, 1], rcond=None)[0]
    p0 = c0 + (cx[0] + cx[1] * base_s) * e1 + (cy[0] + cy[1] * base_s) * e2 + base_s * ax
    d = ax + cx[1] * e1 + cy[1] * e2; d /= np.linalg.norm(d)
    Rout = np.sqrt(areas / np.pi)
    return dict(p0=p0, axis=d, h=hv - base_s, Rout=Rout, big=big, rim=rim_s - base_s, e1=e1)


def rh(F, P):
    v = P - F['p0']; h = v @ F['axis']; r = np.linalg.norm(v - np.outer(h, F['axis']), axis=1); return r, h


def Rout_at(F, h):
    k = F['big']; return np.interp(h, F['h'][k], F['Rout'][k], left=np.nan, right=np.nan)


def cup_cavity_report(F, g, eqs, boxes, lathe, floor):
    """solid share of the cavity cylinder r < R_out(h) - WALL, floor < h < rim, by 1 cm band, for vis / hull / lathe."""
    lo = g.lo; n = np.array(g.occ.shape)
    G = np.stack(np.meshgrid(*[lo[k] + (np.arange(n[k]) + .5) * PITCH for k in range(3)], indexing='ij'), -1).reshape(-1, 3)
    r, h = rh(F, G); Rin = Rout_at(F, h) - WALL
    cav = (h > floor) & (h < F['rim']) & (r < Rin)
    Gc = G[cav]; hc = h[cav]
    v_vis = g.occ.reshape(-1)[cav]; v_hull, _ = hull_test(eqs, boxes, Gc); v_lat = lathe.inside(Gc)
    bands = []
    for b0 in np.arange(0, F['rim'], 0.01):
        sel = (hc >= b0) & (hc < b0 + 0.01)
        if sel.sum() == 0:
            continue
        bands.append(dict(h_cm=[round(b0 * 100, 1), round(min(b0 + .01, F['rim']) * 100, 1)], cavity_cm3=round(cm3(sel.sum(), PITCH), 1),
                          vis_solid=round(float(v_vis[sel].mean()), 3), hull_solid=round(float(v_hull[sel].mean()), 3),
                          lathe_solid=round(float(v_lat[sel].mean()), 3)))
    # highest 1 mm slice with >= 50 % of the cavity cross-section solid
    def top50(m):
        hb = np.floor(hc / PITCH).astype(int); top = None
        for b in np.unique(hb):
            if m[hb == b].mean() >= 0.5:
                top = (b + 1) * PITCH
        return top
    rep = dict(cavity_cm3=round(cm3(cav.sum(), PITCH), 1),
               vis_solid_cm3=round(cm3(v_vis.sum(), PITCH), 1), hull_solid_cm3=round(cm3(v_hull.sum(), PITCH), 1),
               lathe_solid_cm3=round(cm3(v_lat.sum(), PITCH), 1),
               vis_top50_h_cm=None if top50(v_vis) is None else round(top50(v_vis) * 100, 1),
               hull_top50_h_cm=None if top50(v_hull) is None else round(top50(v_hull) * 100, 1),
               lathe_top50_h_cm=None if top50(v_lat) is None else round(top50(v_lat) * 100, 1),
               bands=bands)
    # azimuthal (r, h) occupancy maps for the plot
    rb = np.arange(0, 0.06, 0.002); hb = np.arange(-0.005, F['rim'] + 0.01, 0.002)
    near = (r < 0.06) & (h > -0.005) & (h < F['rim'] + 0.01)
    Gn = G[near]; rn, hn = r[near], h[near]
    mv = g.occ.reshape(-1)[near]; mh, _ = hull_test(eqs, boxes, Gn); ml = lathe.inside(Gn)
    cnt = np.histogram2d(rn, hn, [rb, hb])[0]
    maps = {k: (np.histogram2d(rn[m], hn[m], [rb, hb])[0] / np.maximum(cnt, 1)) for k, m in (('vis', mv), ('hull', mh), ('lathe', ml))}
    return rep, dict(rb=rb, hb=hb, **maps)


def main():
    t0 = time.time(); results = {}; plots = {}
    for ep, c in cfg['episodes'].items():
        names, T = ref_poses(c['ref'])
        ci = names.index(c['container']); si = names.index('wooden_spoon')
        cont = vox.load(c['container_mesh']); g = vox.voxelize(cont, PITCH)
        edt = distance_transform_edt(g.occ) * PITCH
        H, eqs, boxes = load_hulls(c['hulls'])
        sp = vox.load(c['spoon_mesh']); gs = vox.voxelize(sp, SPOON_PITCH); S = gs.centres()
        res = dict(ref=c['ref_store_path'], ref_md5=c['ref_md5'], container_mesh=c['container_mesh_label'], spoon_mesh=c['spoon_mesh_label'],
                   frames=int(len(T)), container_vis_cm3=round(cm3(g.occ.sum(), PITCH), 1), container_mesh_vol_cm3=round(abs(cont.volume) * 1e6, 1),
                   hull_pieces=len(H), hull_union_note='piece volumes overlap; union measured on the voxel grid',
                   spoon_solid_cm3=round(cm3(len(S), SPOON_PITCH), 1))
        is_cup = c['container'] == 'blue_cup'
        if is_cup:
            F = cup_frame(vox.voxelize(vox.load(cfg['cup_frame_mesh']), PITCH)); lathe = Lathe(cfg['lathe_json'])   # frame from library_v3 (no support fill)
            # lathe floor/rim in the cup frame (its own axis, mapped)
            lr, lh = lathe.rh(F['p0'] + np.outer([0, F['rim']], F['axis']))
            floor = cfg['cup_floor_m']
            cav, maps = cup_cavity_report(F, g, eqs, boxes, lathe, floor)
            res['cup_frame'] = dict(axis=np.round(F['axis'], 4).tolist(), base_point_mm=np.round(F['p0'] * 1000, 1).tolist(),
                                    rim_h_cm=round(F['rim'] * 100, 2), floor_h_cm=round(floor * 100, 2), wall_mm=WALL * 1000,
                                    Rout_rim_mm=round(float(Rout_at(F, F['rim'] - 0.002)) * 1000, 1),
                                    Rout_mid_mm=round(float(Rout_at(F, F['rim'] / 2)) * 1000, 1),
                                    Rout_base_mm=round(float(Rout_at(F, 0.01)) * 1000, 1),
                                    lathe_axis_vs_cup_axis_deg=round(float(np.degrees(np.arccos(abs(lathe.a @ F['axis'])))), 2),
                                    lathe_h_of_cup_base_and_rim_mm=np.round(lh * 1000, 1).tolist())
            res['cavity'] = cav; plots[ep] = dict(maps=maps)
        rows = []
        for f in range(len(T)):
            M = np.linalg.inv(T[f, ci]) @ T[f, si]; X = S @ M[:3, :3].T + M[:3, 3]
            lo, hi = g.lo - 0.02, g.lo + np.array(g.occ.shape) * PITCH + 0.02
            near = np.all((X > lo) & (X < hi), 1); Xn = X[near]
            row = dict(f=f, near_pts=int(near.sum()))
            iv = g.lookup(Xn) if len(Xn) else np.zeros(0, bool)
            ih, pen = hull_test(eqs, boxes, Xn) if len(Xn) else (np.zeros(0, bool), np.zeros(0))
            ijk = np.floor((Xn[iv] - g.lo) / PITCH).astype(int)
            row.update(vis_cm3=cm3(iv.sum(), SPOON_PITCH), hull_cm3=cm3(ih.sum(), SPOON_PITCH), hull_only_cm3=cm3((ih & ~iv).sum(), SPOON_PITCH),
                       vis_pen_mm=float(edt[ijk[:, 0], ijk[:, 1], ijk[:, 2]].max() * 1000) if iv.any() else 0.0,
                       hull_pen_mm=float(pen.max() * 1000) if ih.any() else 0.0)
            if is_cup:
                r, h = rh(F, X); Rin = Rout_at(F, h) - WALL
                incav = (h > floor) & (h < F['rim']) & (r < Rin)
                il = lathe.inside(X[incav]) if incav.any() else np.zeros(0, bool)
                inside_open = (r < Rout_at(F, np.clip(h, 0.002, F['rim'] - 0.002))) & (h < F['rim'])
                row.update(cavity_cm3=cm3(incav.sum(), SPOON_PITCH),
                           depth_below_rim_mm=float((F['rim'] - h[incav].min()) * 1000) if incav.any() else 0.0,
                           lowest_h_in_footprint_mm=float(h[inside_open].min() * 1000) if inside_open.any() else None,
                           cav_vis_cm3=cm3(g.lookup(X[incav]).sum(), SPOON_PITCH) if incav.any() else 0.0,
                           cav_hull_cm3=cm3(hull_test(eqs, boxes, X[incav])[0].sum(), SPOON_PITCH) if incav.any() else 0.0,
                           lathe_cm3=cm3(lathe.inside(Xn).sum(), SPOON_PITCH) if len(Xn) else 0.0, cav_lathe_cm3=cm3(il.sum(), SPOON_PITCH),
                           spoon_min_dist_axis_mm=float(r.min() * 1000), spoon_h_at_closest_mm=float(h[np.argmin(r)] * 1000))
            rows.append({k: (round(v, 3) if isinstance(v, float) else v) for k, v in row.items()})
        res['per_frame'] = rows
        A = {k: np.array([r_[k] if r_.get(k) is not None else np.nan for r_ in rows], float) for k in rows[0]}
        summ = {}
        for k in ('vis_cm3', 'hull_cm3', 'hull_only_cm3', 'vis_pen_mm', 'hull_pen_mm') + (('cavity_cm3', 'depth_below_rim_mm', 'cav_vis_cm3', 'cav_hull_cm3', 'lathe_cm3', 'cav_lathe_cm3') if is_cup else ()):
            v = A[k]; summ[k] = dict(max=round(float(np.nanmax(v)), 2), argmax=int(np.nanargmax(v)), frames_gt_1=int((v > 1).sum()),
                                     frames_gt_0=int((v > 0).sum()))
        res['summary'] = summ
        if is_cup:
            fm = int(np.nanargmax(A['depth_below_rim_mm'])); M = np.linalg.inv(T[fm, ci]) @ T[fm, si]; X = S @ M[:3, :3].T + M[:3, 3]
            r, h = rh(F, X); plots[ep]['spoon_rh'] = (fm, r, h)
            plots[ep]['Rout'] = (F['h'][F['big']], F['Rout'][F['big']]); plots[ep]['rim'] = F['rim']; plots[ep]['floor'] = floor
        else:
            fm = int(np.nanargmax(A['hull_only_cm3'])) if np.nanmax(A['hull_only_cm3']) > 0 else int(np.nanargmax(A['hull_cm3']))
        results[ep] = res
        print(ep, json.dumps(res['summary']), round(time.time() - t0, 1), flush=True)
        if not is_cup:
            # rack section data for the plot: rack voxels and hull-only voxels in the spoon's neighbourhood
            plots[ep] = dict(spoon_frames={})
            for tag, ff in (('max', fm), ('last', len(T) - 1)):
                M = np.linalg.inv(T[ff, ci]) @ T[ff, si]; X = S @ M[:3, :3].T + M[:3, 3]
                lo, hi = X.min(0) - 0.03, X.max(0) + 0.03
                n = np.array(g.occ.shape); Gc = g.centres(); Gc = Gc[np.all((Gc > lo) & (Gc < hi), 1)]
                gi = np.stack(np.meshgrid(*[np.arange(lo[k], hi[k], 0.002) for k in range(3)], indexing='ij'), -1).reshape(-1, 3)
                hh, _ = hull_test(eqs, boxes, gi); vv = g.lookup(gi)
                plots[ep]['spoon_frames'][tag] = dict(f=ff, spoon=X, rack=Gc, hull_only=gi[hh & ~vv])
    json.dump(results, open(f'{OUT}/spoon_diag.json', 'w'), indent=1)
    flat = {}
    for ep, d in plots.items():
        if 'maps' in d:
            for k, v in d['maps'].items():
                flat[f'{ep}/map_{k}'] = np.asarray(v)
            fm, r, h = d['spoon_rh']; flat[f'{ep}/spoon_f'] = np.array(fm); flat[f'{ep}/spoon_r'] = r; flat[f'{ep}/spoon_h'] = h
            flat[f'{ep}/Rout_h'], flat[f'{ep}/Rout'] = d['Rout']; flat[f'{ep}/rim'] = np.array(d['rim']); flat[f'{ep}/floor'] = np.array(d['floor'])
        else:
            for tag, x in d['spoon_frames'].items():
                for k, v in x.items():
                    flat[f'{ep}/{tag}_{k}'] = np.asarray(v)
    np.savez_compressed(f'{OUT}/plotdata.npz', **flat)
    print('done', round(time.time() - t0, 1))


main()
