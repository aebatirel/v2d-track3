# Post-pass on obsfuse grids: closing / meshing variants + GT-free gates (no scans, no mocap).
# Variants (comma list via --var), each NAME = tau_closing_gate_mesh:
#   tau   : 12 | 6 | 4 (mm truncation accumulator)
#   close : fill | near | auto | none     (auto = recon_mesh rule: near if the never-observed share > 0.5)
#   gate  : g0 (as recon_mesh) | g1 (unknown voxels with >= 1 seen-free observation are free and never filled)
#   mesh  : bin (binary solid + gaussian 0.8 vox, as recon_mesh) | cont (marching cubes on the averaged TSDF where
#           observed; +-1 elsewhere)
# Usage: obspost.py GRID.npz OUTDIR VAR[,VAR...]   e.g. 12_auto_g0_bin,4_auto_g1_cont
import sys, json, os, time
import numpy as np
from scipy import ndimage
import trimesh
from skimage.measure import marching_cubes
sys.path.insert(0, '/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/interact/code')
import vox
KIT = '/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/loc/kit/v2d_submission_kit'
MIN_OBS = 3


def load(paths):
    Z = [np.load(p) for p in paths]; z0 = Z[0]
    G = {k: sum(z[k].astype(np.float32) for z in Z) for k in z0.files if k[0] in 'SWNM'}
    return G, tuple(z0['shape']), z0['lo'], float(z0['voxel'])


def main_part(sol, merge):
    lb, k = ndimage.label(ndimage.binary_dilation(sol, iterations=merge))
    if k == 0:
        return sol
    c0 = np.array(sol.shape) // 2; sz = ndimage.sum(sol, lb, range(1, k + 1)); cand = np.argsort(-sz)[:5] + 1
    best = cand[int(np.argmin([np.min(np.linalg.norm(np.argwhere(lb == q) - c0, axis=1)) for q in cand]))]
    return sol & (lb == best)


def build(G, shape, vx, var):
    tau, close, gate, mode = var.split('_')
    S, W = G[f'S{tau}'], G[f'W{tau}']
    mean = np.where(W > 0, S / np.maximum(W, 1), 0)
    known = W >= MIN_OBS; inside = known & (mean < 0)
    seen_free = G['NF'] >= 1
    cand = ~known & ~(seen_free if gate == 'g1' else np.zeros_like(known))     # fillable never-observed voxels
    lab, nl = ndimage.label(~known if gate == 'g0' else cand)
    border = np.unique(np.r_[lab[0].ravel(), lab[-1].ravel(), lab[:, 0].ravel(), lab[:, -1].ravel(),
                             lab[:, :, 0].ravel(), lab[:, :, -1].ravel()])
    solid_fill = inside | (cand & (lab > 0) & ~np.isin(lab, border[border > 0]))
    near_vox = int(round(0.012 / vx))
    solid_near = ndimage.binary_fill_holes(inside | (cand & ndimage.binary_dilation(inside, iterations=near_vox)))
    if gate == 'g1':
        solid_near &= ~(~known & seen_free)
    merge = int(round(0.008 / vx))
    mf = main_part(solid_fill, merge)
    unk = float((mf & ~inside).sum() / max(mf.sum(), 1))
    m_ = close if close != 'auto' else ('near' if unk > 0.5 else 'fill')
    solid = {'fill': solid_fill, 'near': solid_near, 'none': inside}[m_]
    solid = main_part(solid, merge)
    if mode == 'bin':
        field = ndimage.gaussian_filter(np.where(solid, -1.0, 1.0).astype(np.float32), 0.8)
    else:
        field = np.where(known, np.clip(mean, -1, 1), np.where(solid, -1.0, 1.0)).astype(np.float32)
        field = np.where(solid, np.minimum(field, 1.0), np.maximum(field, 0.05))     # outside the kept solid: positive
        field = np.where(solid & ~known, -1.0, field)
    field = np.pad(field, 1, constant_values=1.0)
    return solid, field, dict(closing=m_, unknown_share=round(unk, 3))


def gates(G, solid, vx, mesh):
    cm3 = lambda M: round(float(M.sum()) * vx ** 3 * 1e6, 2)  # noqa: E731
    W = G['W12']; known = W >= MIN_OBS
    nf, nv = G['NF'], G['NV']
    viol = solid & (nf >= 2) & (nf >= 0.5 * np.maximum(nv, 1))
    M0, M1, M2 = G['M0'], G['M1'], G['M2']
    mean12 = np.where(W > 0, G['S12'] / np.maximum(W, 1), 1)
    surf = (np.abs(mean12) < 0.25) & (M0 >= 5)
    var = M2[surf] / M0[surf] - (M1[surf] / M0[surf]) ** 2
    sig = float(np.median(np.sqrt(np.maximum(var, 0)))) if surf.any() else float('nan')
    hull = mesh.convex_hull
    com = mesh.center_mass if mesh.is_watertight else mesh.centroid
    sp = vox.stable_poses(np.asarray(hull.vertices), com)
    st = [d for d in sp if d['stable']]
    return dict(solid_cm3=cm3(solid), seen_free_violation_cm3=cm3(viol), filled_unobserved_cm3=cm3(solid & ~known),
                filled_unobserved_share=round(float((solid & ~known).sum() / max(solid.sum(), 1)), 3),
                sigma_eff_mm=round(sig * 1e3, 2),
                stable_tip_ge5=int(sum(d['tip_deg'] >= 5 for d in st)),
                stable_top=[dict(n=np.round(d['normal'], 2).tolist(), tip=round(d['tip_deg'], 1), area=round(d['area_cm2'], 1),
                                 margin=round(d['margin_mm'], 1)) for d in st[:5]])


if __name__ == '__main__':
    grids = sys.argv[1].split(','); od = sys.argv[2]; os.makedirs(od, exist_ok=True)
    G, shape, lo, vx = load(grids)
    res = {}
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
        r = dict(info, **gates(G, solid, vx, m), watertight=bool(m.is_watertight), volume_cm3=round(float(m.volume) * 1e6, 1) if m.is_watertight else None,
                 extents_cm=np.round(m.extents * 100, 1).tolist(), faces_full=len(m.faces), budget_watertight=bool(mb.is_watertight),
                 sec=round(time.time() - t0, 1))
        res[var] = r; print(var, json.dumps(r), flush=True)
    json.dump(res, open(f'{od}/post.json', 'w'), indent=1)
