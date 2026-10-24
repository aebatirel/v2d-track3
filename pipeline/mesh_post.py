"""Evidence grids -> solid -> mesh, with the GT-free gates (mesh pipeline v5, docs/mesh-v5-spec-draft.md section 4.3;
port of the v5 study's obspost2.build / gates, obspost5.main_part_lc / make_mesh and gate_ev, 2026-10-22). Reads only
our own evidence grids (recon_mesh.py --mode obs --save_grid): no scan, no mocap.

Variant NAME = tau_close_gate_fsp_mesh[@lcNN]; the frozen v5 variant is 4c12_adj_g2_f0_cont@lc25 on 'nobc' grids:
  tau   4c12: the 4 mm TSDF mean where it has >= 3 votes, else the 12 mm mean (also 12, 6, 4, 6c12)
  close adj: an unknown component not touching the grid border is filled only if >= 50 % of its boundary faces touch
        observed-inside voxels (also fill, near, auto, none)
  gate  g2: voxels seen free by >= 2 samples more than 3 mm behind them are never filled (g0, g1; suffix m / M adds
        silhouette free space)
  fsp   f0 (f1: observed-inside voxels with NF3 >= max(3, 0.25 W) become free)
  mesh  cont: marching cubes on the averaged TSDF (bin: binary solid + gaussian 0.8 voxel)
  @lc25 main part: merge components by an 8 mm dilation; among those >= 25 % of the largest keep the one nearest the
        grid centre (the earlier rule's 5 largest let a ~1 cm3 fragment win in the pitcher and the rack)
Grid modes: def (as fused) | nobc (the per-frame below-table votes removed: S-NB, W-NB; spec 4.4 / D2).
Gates (spec 4.5): G1 seen-free violation (solid voxels with NF3 >= 2 and >= 0.5 NV) <= 0.5 cm3; G2 unexplained
evidence (own zero crossings, W12 >= 5, |mean12| < 0.25, M0 >= 5, farther than 8 mm from the solid's boundary)
<= 0.05; G5 reported: the solid's share decided only by the 12 mm accumulator. X, C and topology live in mesh_gates.

Usage: python mesh_post.py OUT_DIR GRID.npz[,GRID2.npz ...] [--mode nobc] [--var 4c12_adj_g2_f0_cont@lc25] [--kit KIT]
Writes OUT_DIR/<var>_full.glb (full resolution; collision pieces are built from it), OUT_DIR/<var>.glb (decimated by
pipeline/mesh_decimate.py) and OUT_DIR/<var>.json (gates and topology).
"""
import argparse, json, os, sys, time

import numpy as np
import trimesh
from scipy import ndimage

MIN_OBS = 3
ADJ = 0.5
FROZEN = '4c12_adj_g2_f0_cont@lc25'


def load(paths, mode='nobc'):
    """Sum per-episode grids (same lattice). mode nobc removes the per-frame below-table votes from S* and W*."""
    G, meta = {}, None
    for p in paths:
        z = np.load(p)
        Ge = {k: z[k].astype(np.float32) for k in z.files if k[0] in 'SWNM'}
        if mode == 'nobc':
            if 'NB' not in z.files:
                raise ValueError(f'{p}: no NB counter, cannot remove the below-table votes')
            for k in [k for k in Ge if k[0] in 'SW' and k[1:].isdigit()]:
                Ge[k] = Ge[k] - z['NB'].astype(np.float32)
        m = (tuple(z['shape']), z['lo'], float(z['voxel']))
        if meta is None:
            meta = m
        if m[0] != meta[0] or not np.allclose(m[1], meta[1]):
            raise ValueError(f'{p}: grid lattice differs from the first grid')
        for k, v in Ge.items():
            G[k] = G.get(k, 0) + v
    return G, meta[0], meta[1], meta[2]


def main_part(sol, merge, frac=None):
    """The kept component after an 8 mm merge: nearest the grid centre among the 5 largest, or (frac) among those
    >= frac x the largest."""
    lb, k = ndimage.label(ndimage.binary_dilation(sol, iterations=merge))
    if k == 0:
        return sol
    c0 = np.array(sol.shape) // 2; sz = ndimage.sum(sol, lb, range(1, k + 1))
    cand = np.argsort(-sz)[:5] + 1 if frac is None else [q + 1 for q in np.argsort(-sz)[:5] if sz[q] >= frac * sz.max()]
    best = cand[int(np.argmin([np.min(np.linalg.norm(np.argwhere(lb == q) - c0, axis=1)) for q in cand]))]
    return sol & (lb == best)


def boundary_inside_share(lab, nl, inside):
    """Per unknown component: share of its 6-neighbour boundary faces that touch observed-inside voxels."""
    fin = np.zeros(nl + 1); fall = np.zeros(nl + 1)
    for ax in range(3):
        for sh in (1, -1):
            nb_in = np.roll(inside, sh, ax); nb_lab = np.roll(lab, sh, ax)
            sl = [slice(None)] * 3; sl[ax] = slice(0, 1) if sh == 1 else slice(-1, None)
            nb_in[tuple(sl)] = False; nb_lab[tuple(sl)] = 0
            face = (lab > 0) & (nb_lab != lab)
            fall += np.bincount(lab[face], minlength=nl + 1)
            fin += np.bincount(lab[face & nb_in], minlength=nl + 1)
    return fin / np.maximum(fall, 1)


def build(G, shape, vx, var=FROZEN):
    """(solid, padded field for marching cubes, info)."""
    frac = None
    if '@lc' in var:
        var, lc = var.split('@lc'); frac = float(lc) / 100
    tau, close, gate, fsp, mode = var.split('_')
    if 'c' in tau:
        tf, tc = tau.split('c')
        Wf, Wc = G[f'W{tf}'], G[f'W{tc}']
        mf_ = np.where(Wf > 0, G[f'S{tf}'] / np.maximum(Wf, 1), 0); mc_ = np.where(Wc > 0, G[f'S{tc}'] / np.maximum(Wc, 1), 0)
        W = np.where(Wf >= MIN_OBS, Wf, Wc); mean = np.where(Wf >= MIN_OBS, mf_, mc_)
        coarse_only = Wf < MIN_OBS
    else:
        S, W = G[f'S{tau}'], G[f'W{tau}']
        mean = np.where(W > 0, S / np.maximum(W, 1), 0); coarse_only = np.zeros(W.shape, bool)
    known = W >= MIN_OBS; inside = known & (mean < 0)
    nf3 = G['NF3'] if 'NF3' in G else G['NF']
    if fsp == 'f1':
        flip = inside & (nf3 >= np.maximum(3, 0.25 * W)); inside = inside & ~flip
    else:
        flip = np.zeros_like(inside)
    seen_free = {'g0': np.zeros_like(known), 'g1': nf3 >= 1, 'g2': nf3 >= 2}[gate[:2]]
    mfree = np.zeros_like(known)
    if gate.endswith(('m', 'M')):
        r = 0.5 if gate.endswith('m') else 0.3
        mfree = (G['NMF'] >= 3) & (G['NMF'] >= r * np.maximum(G['NMV'], 1))
        inside = inside & ~mfree; seen_free = seen_free | mfree
    cand = ~known & ~seen_free
    lab, nl = ndimage.label(cand)
    border = np.unique(np.r_[lab[0].ravel(), lab[-1].ravel(), lab[:, 0].ravel(), lab[:, -1].ravel(),
                             lab[:, :, 0].ravel(), lab[:, :, -1].ravel()])
    enclosed = (lab > 0) & ~np.isin(lab, border[border > 0])
    solid_fill = inside | (cand & enclosed)
    near_vox = int(round(0.012 / vx))
    solid_near = ndimage.binary_fill_holes(inside | (cand & ndimage.binary_dilation(inside, iterations=near_vox))) & ~seen_free
    share = boundary_inside_share(lab, nl, inside)
    okc = np.zeros(nl + 1, bool); okc[1:] = share[1:] >= ADJ; okc[border[border > 0]] = False
    solid_adj = inside | (cand & okc[lab])
    merge = int(round(0.008 / vx))
    mf = main_part(solid_fill, merge, frac)
    unk = float((mf & ~inside).sum() / max(mf.sum(), 1))
    m_ = close if close != 'auto' else ('near' if unk > 0.5 else 'fill')
    solid = {'fill': solid_fill, 'near': solid_near, 'none': inside, 'adj': solid_adj}[m_]
    solid = main_part(solid, merge, frac)
    if mode == 'bin':
        field = ndimage.gaussian_filter(np.where(solid, -1.0, 1.0).astype(np.float32), 0.8)
    else:
        field = np.where(known & ~flip, np.clip(mean, -1, 1), np.where(solid, -1.0, 1.0)).astype(np.float32)
        field = np.where(solid, np.minimum(field, 1.0), np.maximum(field, 0.05))
        field = np.where(solid & (~known | flip), -1.0, field)
    field = np.pad(field, 1, constant_values=1.0)
    if mfree.any():
        field = np.where(np.pad(mfree, 1), np.maximum(field, 0.5), field)
    info = dict(closing=m_, unknown_share=round(unk, 3), fsp_flipped_cm3=round(float(flip.sum()) * vx ** 3 * 1e6, 2),
                mask_free_cm3=round(float(mfree.sum()) * vx ** 3 * 1e6, 2),
                g5_coarse_only_share=round(float((solid & coarse_only & known).sum() / max(solid.sum(), 1)), 3))
    return solid, field, info


def make_mesh(field, lo, vx):
    """Marching cubes at 0 on the padded field; fragments under 5 % of the largest area or 15 cm away are dropped."""
    from skimage.measure import marching_cubes
    verts, faces, _, _ = marching_cubes(field, 0.0, spacing=(vx,) * 3)
    verts = verts - vx + lo + 0.5 * vx
    m = trimesh.Trimesh(verts, faces, process=True)
    parts = m.split(only_watertight=False)
    if len(parts) > 1:
        big = max(parts, key=lambda q: q.area)
        m = trimesh.util.concatenate([q for q in parts if q.area >= 0.05 * big.area and np.linalg.norm(q.centroid - big.centroid) < 0.15])
    return m


def stable_poses(hull_vertices, com, ang_tol=3.0, off_tol=0.0015, min_area=0.0):
    """Resting poses on a plane (the study's vox.stable_poses): hull faces grouped into near-coplanar support regions;
    stable iff the COM projects inside the support polygon; margin, tip angle atan(margin / COM height), area."""
    from scipy.spatial import ConvexHull
    H = ConvexHull(hull_vertices); eq = H.equations; nrm = eq[:, :3]; tri = H.simplices
    order = np.argsort(-np.linalg.norm(np.cross(hull_vertices[tri[:, 1]] - hull_vertices[tri[:, 0]],
                                                   hull_vertices[tri[:, 2]] - hull_vertices[tri[:, 0]]), axis=1))
    used = np.zeros(len(tri), bool); out = []; cosT = np.cos(np.radians(ang_tol))
    for f in order:
        if used[f]:
            continue
        n0 = nrm[f]; h0 = (hull_vertices @ n0).max()
        sel = (~used) & (nrm @ n0 >= cosT)
        vd = h0 - hull_vertices[tri] @ n0
        sel &= (vd.max(1) <= off_tol); sel[f] = True; used |= sel
        P = hull_vertices[np.unique(tri[sel])]; P = P[(h0 - P @ n0) <= off_tol]
        e1 = np.cross(n0, [1, 0, 0] if abs(n0[0]) < 0.9 else [0, 1, 0]); e1 /= np.linalg.norm(e1); e2 = np.cross(n0, e1)
        q = np.stack([P @ e1, P @ e2], 1); c2 = np.array([com @ e1, com @ e2]); hgt = h0 - com @ n0
        if len(q) >= 3:
            try:
                h2 = ConvexHull(q); poly = q[h2.vertices]; area = h2.volume
            except Exception:
                poly = q; area = 0.0
        else:
            poly = q; area = 0.0
        if area <= min_area or len(poly) < 3:
            inside = False; margin = -1.0
        else:
            e = np.roll(poly, -1, 0) - poly
            nn = np.stack([e[:, 1], -e[:, 0]], 1); nn /= np.linalg.norm(nn, axis=1, keepdims=True)
            sd = ((c2 - poly) * nn).sum(1); inside = bool(np.all(sd <= 0)); margin = float(-sd.max())
        out.append(dict(normal=n0.tolist(), area_cm2=float(area * 1e4), com_height_cm=float(hgt * 100), margin_mm=float(margin * 1e3),
                        stable=inside, tip_deg=float(np.degrees(np.arctan2(max(margin, 0), hgt))) if inside else 0.0))
    out.sort(key=lambda d: -d['tip_deg'])
    return out


def evidence(G):
    W = G['W12']; m12 = np.where(W > 0, G['S12'] / np.maximum(W, 1e-9), 1)
    return (W >= 5) & (np.abs(m12) < 0.25) & (G['M0'] >= 5)


def gates(G, solid, vx, mesh):
    cm3 = lambda M: round(float(M.sum()) * vx ** 3 * 1e6, 2)  # noqa: E731
    known = G['W4'] >= MIN_OBS
    nf, nv = (G['NF3'] if 'NF3' in G else G['NF']), G['NV']
    viol = solid & (nf >= 2) & (nf >= 0.5 * np.maximum(nv, 1))
    edt = ndimage.distance_transform_edt(solid) * vx
    ridge = solid & (edt >= ndimage.maximum_filter(edt, size=3) - 1e-9); thk = 2 * edt[ridge] * 1e3
    ev = evidence(G); bnd = solid & ~ndimage.binary_erosion(solid)
    d_b = ndimage.distance_transform_edt(~bnd) * vx; d_ev = ndimage.distance_transform_edt(~ev) * vx
    com = mesh.center_mass if mesh.is_watertight else mesh.centroid
    st = [d for d in stable_poses(np.asarray(mesh.convex_hull.vertices), com) if d['stable']]
    return dict(solid_cm3=cm3(solid), g1_seen_free_violation_cm3=cm3(viol), filled_unobserved_cm3=cm3(solid & ~known),
                g2_unexplained8=round(float((d_b[ev] > 0.008).mean()), 3) if ev.any() else None,
                unexplained4=round(float((d_b[ev] > 0.004).mean()), 3) if ev.any() else None,
                unsupported4=round(float((d_ev[bnd] > 0.004).mean()), 3) if bnd.any() else None, evidence_vox=int(ev.sum()),
                medial_thickness_mm_p10_50_90=[round(float(np.percentile(thk, q)), 1) for q in (10, 50, 90)] if len(thk) else None,
                stable_tip_ge5=int(sum(d['tip_deg'] >= 5 for d in st)),
                stable_top=[dict(n=np.round(d['normal'], 2).tolist(), tip=round(d['tip_deg'], 1), area=round(d['area_cm2'], 1),
                                 margin=round(d['margin_mm'], 1)) for d in st[:4]])


def topo(m):
    return dict(watertight=bool(m.is_watertight), bodies=int(m.body_count), euler=int(m.euler_number), faces=int(len(m.faces)),
                vol_cm3=round(float(m.volume) * 1e6, 1) if m.is_watertight else None)


def run(grids, out, mode='nobc', var=FROZEN, decimate=True):
    t0 = time.time(); os.makedirs(out, exist_ok=True)
    G, shape, lo, vx = load(grids, mode)
    solid, field, info = build(G, shape, vx, var)
    m = make_mesh(field, lo, vx)
    vn = var.replace('@', '_at_'); full = f'{out}/{vn}_full.glb'; m.export(full)
    rec = dict(grids=grids, mode=mode, var=var, full=full, **info, full_topo=topo(m), extents_cm=np.round(m.extents * 100, 1).tolist())
    rec.update(gates(G, solid, vx, m))
    rec['g1_pass'] = rec['g1_seen_free_violation_cm3'] <= 0.5
    rec['g2_pass'] = rec['g2_unexplained8'] is not None and rec['g2_unexplained8'] <= 0.05
    if decimate:
        import mesh_decimate
        try:
            md, dinfo = mesh_decimate.decimate(m); md.export(f'{out}/{vn}.glb'); rec['decimate'] = dinfo
        except mesh_decimate.GateFail as e:
            rec['decimate'] = dict(gate_fail=str(e)[:300])
    rec['sec'] = round(time.time() - t0, 1)
    json.dump(rec, open(f'{out}/{vn}.json', 'w'), indent=1)
    return m, rec


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('out'); ap.add_argument('grids')
    ap.add_argument('--mode', default='nobc', choices=['def', 'nobc']); ap.add_argument('--var', default=FROZEN)
    ap.add_argument('--no_decimate', action='store_true')
    a = ap.parse_args()
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    _, rec = run(a.grids.split(','), a.out, a.mode, a.var, not a.no_decimate)
    print(json.dumps({k: v for k, v in rec.items() if k not in ('stable_top',)}))


if __name__ == '__main__':
    main()
