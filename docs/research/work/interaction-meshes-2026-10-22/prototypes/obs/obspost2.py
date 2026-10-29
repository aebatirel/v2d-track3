# Post-pass v2 on obsfuse2 grids (scratch, 2026-10-22; repo unchanged). GT-free: no scans, no mocap.
# Variant NAME = tau_close_gate_fsp_mesh
#   tau   : 12 | 6 | 4 | 4c12 | 6c12   truncation accumulator (mm); FcC = fine F where observed >= 3 times, else coarse C
#   close : fill | near | auto | adj | none
#           fill = recon_mesh: unknown components not touching the grid border are inside
#           adj  = observation-first: an unknown component is inside only if >= ADJ of its boundary faces touch
#                  observed-inside voxels (hidden BEHIND the object's own surface); components bounded mostly by
#                  observed free space (a gap seen around but not into) stay empty
#   gate  : g0 (none) | g1 (voxels seen free by >= 1 sample more than 3 mm behind them are never filled and count as
#           free space for the enclosure test) | g2 (the same with >= 2 samples)
#           suffix m / M: also silhouette free space (maskfuse NMF >= 3 and >= 50 % / 30 % of NMV)
#   fsp   : f0 | f1 free-space priority: observed-inside voxels with NF3 >= max(3, 0.25 W) become free
#   mesh  : bin (binary solid + gaussian 0.8 vox, as recon_mesh) | cont (marching cubes on the averaged TSDF)
# Usage: obspost2.py GRID.npz[,GRID2.npz] OUTDIR VAR[,VAR...]
import sys, json, os, time
import numpy as np
from scipy import ndimage
import trimesh
from skimage.measure import marching_cubes
sys.path.insert(0, '/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/interact/code')
import vox
KIT = '/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/loc/kit/v2d_submission_kit'
MIN_OBS = 3
ADJ = 0.5


def load(paths):
    Z = [np.load(p) for p in paths]; z0 = Z[0]
    keys = sorted({k for z in Z for k in z.files if k[0] in 'SWNM'})
    G = {k: sum(z[k].astype(np.float32) for z in Z if k in z.files) for k in keys}
    return G, tuple(z0['shape']), z0['lo'], float(z0['voxel'])


def main_part(sol, merge):
    lb, k = ndimage.label(ndimage.binary_dilation(sol, iterations=merge))
    if k == 0:
        return sol
    c0 = np.array(sol.shape) // 2; sz = ndimage.sum(sol, lb, range(1, k + 1)); cand = np.argsort(-sz)[:5] + 1
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


def build(G, shape, vx, var):
    tau, close, gate, fsp, mode = var.split('_')
    if 'c' in tau:                     # cascade: fine truncation where it has >= MIN_OBS votes, else the coarse one
        tf, tc = tau.split('c')
        Wf, Wc = G[f'W{tf}'], G[f'W{tc}']
        mf_ = np.where(Wf > 0, G[f'S{tf}'] / np.maximum(Wf, 1), 0); mc_ = np.where(Wc > 0, G[f'S{tc}'] / np.maximum(Wc, 1), 0)
        W = np.where(Wf >= MIN_OBS, Wf, Wc); mean = np.where(Wf >= MIN_OBS, mf_, mc_)
    else:
        S, W = G[f'S{tau}'], G[f'W{tau}']
        mean = np.where(W > 0, S / np.maximum(W, 1), 0)
    known = W >= MIN_OBS; inside = known & (mean < 0)
    nf3 = G['NF3'] if 'NF3' in G else G['NF']
    if fsp == 'f1':
        flip = inside & (nf3 >= np.maximum(3, 0.25 * W))
        inside = inside & ~flip
    else:
        flip = np.zeros_like(inside)
    seen_free = {'g0': np.zeros_like(known), 'g1': nf3 >= 1, 'g2': nf3 >= 2}[gate[:2]]
    mfree = np.zeros_like(known)
    if gate.endswith('m') or gate.endswith('M'):   # silhouette free space: object colour absent where nothing occludes
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
    mf = main_part(solid_fill, merge)
    unk = float((mf & ~inside).sum() / max(mf.sum(), 1))
    m_ = close if close != 'auto' else ('near' if unk > 0.5 else 'fill')
    solid = {'fill': solid_fill, 'near': solid_near, 'none': inside, 'adj': solid_adj}[m_]
    solid = main_part(solid, merge)
    if mode == 'bin':
        field = ndimage.gaussian_filter(np.where(solid, -1.0, 1.0).astype(np.float32), 0.8)
    else:
        field = np.where(known & ~flip, np.clip(mean, -1, 1), np.where(solid, -1.0, 1.0)).astype(np.float32)
        field = np.where(solid, np.minimum(field, 1.0), np.maximum(field, 0.05))
        field = np.where(solid & (~known | flip), -1.0, field)
    field = np.pad(field, 1, constant_values=1.0)
    if mfree.any():
        field = np.where(np.pad(mfree, 1), np.maximum(field, 0.5), field)
    return solid, field, dict(closing=m_, unknown_share=round(unk, 3), fsp_flipped_cm3=round(float(flip.sum()) * vx ** 3 * 1e6, 2),
                              mask_free_cm3=round(float(mfree.sum()) * vx ** 3 * 1e6, 2))


def gates(G, solid, vx, mesh):
    cm3 = lambda M: round(float(M.sum()) * vx ** 3 * 1e6, 2)  # noqa: E731
    known = G['W4'] >= MIN_OBS
    nf, nv = (G['NF3'] if 'NF3' in G else G['NF']), G['NV']
    viol = solid & (nf >= 2) & (nf >= 0.5 * np.maximum(nv, 1))
    edt = ndimage.distance_transform_edt(solid) * vx
    ridge = solid & (edt >= ndimage.maximum_filter(edt, size=3) - 1e-9)
    thk = 2 * edt[ridge] * 1e3
    hull = mesh.convex_hull
    com = mesh.center_mass if mesh.is_watertight else mesh.centroid
    sp = vox.stable_poses(np.asarray(hull.vertices), com)
    st = [d for d in sp if d['stable']]
    return dict(solid_cm3=cm3(solid), seen_free_violation_cm3=cm3(viol), filled_unobserved_cm3=cm3(solid & ~known),
                medial_thickness_mm_p10_50_90=[round(float(np.percentile(thk, q)), 1) for q in (10, 50, 90)] if len(thk) else None,
                stable_tip_ge5=int(sum(d['tip_deg'] >= 5 for d in st)),
                stable_top=[dict(n=np.round(d['normal'], 2).tolist(), tip=round(d['tip_deg'], 1), area=round(d['area_cm2'], 1),
                                 margin=round(d['margin_mm'], 1)) for d in st[:4]])


if __name__ == '__main__':
    grids = sys.argv[1].split(','); od = sys.argv[2]; os.makedirs(od, exist_ok=True)
    G, shape, lo, vx = load(grids)
    res = json.load(open(f'{od}/post.json')) if os.path.exists(f'{od}/post.json') else {}
    for var in sys.argv[3].split(','):
        t0 = time.time()
        solid, field, info = build(G, shape, vx, var)
        verts, faces, _, _ = marching_cubes(field, 0.0, spacing=(vx,) * 3)
        verts = verts - vx + lo + 0.5 * vx
        m = trimesh.Trimesh(verts, faces, process=True)
        parts = m.split(only_watertight=False)
        if len(parts) > 1:
            big = max(parts, key=lambda q: q.area)
            m = trimesh.util.concatenate([q for q in parts if q.area >= 0.05 * big.area and np.linalg.norm(q.centroid - big.centroid) < 0.15])
        full = f'{od}/{var}_full.glb'; m.export(full)
        sys.path.insert(0, KIT)
        from v2dlb.mesh_budget import budget_mesh
        vb, fb = budget_mesh(full, 4096, 4096)
        mb = trimesh.Trimesh(vb, fb, process=False); mb.export(f'{od}/{var}.glb')
        r = dict(info, **gates(G, solid, vx, m), watertight=bool(m.is_watertight),
                 volume_cm3=round(float(m.volume) * 1e6, 1) if m.is_watertight else None,
                 extents_cm=np.round(m.extents * 100, 1).tolist(), faces_full=len(m.faces), budget_watertight=bool(mb.is_watertight),
                 sec=round(time.time() - t0, 1))
        res[var] = r; print(var, json.dumps(r), flush=True)
        json.dump(res, open(f'{od}/post.json', 'w'), indent=1)
