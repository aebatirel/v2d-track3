"""P-HULL (SPEC section 8; minimal form for build step B1): every voxel of the bundle grid that is not FREE, inside
the seeded component, above the at-rest table plane, minus the partner clip, closed by marching cubes. Always closed,
thick where unseen; the fallback of the ladder (SPEC section 13).

Choices for B1 (dev bundles, DEVIATIONS B1): the seeded component is the 6-connected component of the kept voxels
that holds the most OBSERVED voxels (dev bundles carry no seeds; the grid is the old obs_all box); 'above the table'
is the at-rest table plane of the bundle (n.x + d >= 0 at the voxel centre), and no cut is made for an object with no
rest plane; the partner clip removes non-OBSERVED voxels with pocc > 0 and is grown by one voxel at a time (at most
twice) while the construction-time V2 (a) check on the voxel volume (complete.clip_check_grid) still finds partner
samples deeper than the band. V2 on the packed mesh (score.v2) judges the result.

Packable surface (B1, DEVIATIONS 52): the 4 mm marching-cubes surface of a hull is often of high genus (voxel-scale
tunnels; ep11 beige cup: Euler number -134, 17016 faces), and decimating it 4x to the 4000-face budget leaves
non-manifold edges at every fast_simplification setting (B1 notes). So the surface is marched at the finest integer
coarsening k = 1, 2, 3 of the 4 mm grid whose budget fit (autokit program.fit_budget, as the packer does) is
watertight. A coarse voxel is kept if at least half of its fine voxels are kept and none of them is a non-OBSERVED
partner voxel (pocc > 0 grown as the fine clip was); then the seeded component is taken again (_coarsen). The fine
grid, its states and the construction check stay at 4 mm; the report records k and every try."""
from __future__ import annotations

import numpy as np
import trimesh
from scipy import ndimage

from gmg import complete
from gmg.bundle import STATE_FREE, STATE_OBSERVED
from gmg.producers import Candidate

MAX_GROW = 2
MAX_COARSEN = 3


def _coarsen(occ, partner, observed, k):
    """k x k x k blocks of the 4 mm grid: a block is kept if at least half of its fine voxels are kept (majority, no
    outward swelling) and none of its fine voxels is a non-OBSERVED partner voxel (the partner clip at the coarse
    resolution); then the component holding the most OBSERVED fine voxels."""
    if k == 1:
        return occ
    sh = [-(-n // k) * k for n in occ.shape]

    def blocks(a):
        pad = np.zeros(sh, bool)
        pad[:a.shape[0], :a.shape[1], :a.shape[2]] = a
        return pad.reshape(sh[0] // k, k, sh[1] // k, k, sh[2] // k, k)
    co = (blocks(occ).sum(axis=(1, 3, 5)) >= (k ** 3 + 1) // 2) & ~blocks(partner & ~observed).any(axis=(1, 3, 5))
    lab, n = ndimage.label(co)
    if n == 0:
        return co
    ob = np.bincount(lab[blocks(observed & occ).any(axis=(1, 3, 5)) & (lab > 0)], minlength=n + 1)
    keep = int(ob[1:].argmax()) + 1 if ob[1:].any() else int(np.bincount(lab.ravel())[1:].argmax()) + 1
    return lab == keep


def _packable(mesh, budget):
    from autokit import program
    m, info = program.fit_budget(mesh, [], budget)
    m = trimesh.Trimesh(np.asarray(m.vertices), np.asarray(m.faces), process=True)
    return bool(m.is_watertight and len(m.faces) <= budget), int(len(m.faces))


def _march(occ, lo, vox):
    from skimage import measure
    pad = np.pad(occ.astype(np.float32), 1)
    v, f, _, _ = measure.marching_cubes(pad, level=0.5)
    v = lo + (v - 1 + 0.5) * vox
    m = trimesh.Trimesh(v, f[:, ::-1], process=True)
    if m.is_watertight and m.volume < 0:
        m.invert()
    return m


def produce(ctx, frames=None):
    if frames is not None:
        raise NotImplementedError('HULL fold rebuilds (grids from training frames) come with B5')
    b, obj = ctx['bundle'], ctx['obj']
    obs = b.obs(obj)
    st = np.asarray(obs['state'])
    lo, vox = np.asarray(obs['lo'], np.float64), float(obs['vox'])
    occ0 = st != STATE_FREE
    rep = dict(voxels_not_free=int(occ0.sum()), observed=int((st == STATE_OBSERVED).sum()))
    flags = []
    pl = b.rest_plane(obj)
    if pl is not None:
        idx = np.indices(st.shape).reshape(3, -1).T
        h = (lo + (idx + 0.5) * vox) @ pl[0] + pl[1]
        occ0 &= (h >= 0).reshape(st.shape)
        rep['table_cut'] = int((h < 0).sum())
    else:
        flags.append('no_rest_plane_no_table_cut')
    mesh, grow, chk, occ_m, grow_m = None, 0, None, None, 0
    for grow in range(MAX_GROW + 1):
        occ = complete.partner_clip(occ0, obs, grow=grow)
        lab, n = ndimage.label(occ)
        if n == 0:
            break
        obs_lab = np.bincount(lab[(st == STATE_OBSERVED) & (lab > 0)], minlength=n + 1)
        keep = int(obs_lab[1:].argmax()) + 1 if obs_lab[1:].any() else int(np.bincount(lab.ravel())[1:].argmax()) + 1
        occ = lab == keep
        chk = complete.clip_check_grid(occ, obs, b, obj)
        mesh, occ_m, grow_m = _march(occ, lo, vox), occ, grow
        rep.update(components=int(n), kept_voxels=int(occ.sum()), kept_observed=int(obs_lab[keep]))
        if chk['deep_total'] == 0:
            break
    rep.update(partner_clip_grow=grow_m, partner_clip=chk, faces_dense=int(len(mesh.faces)) if mesh is not None else 0,
               watertight_dense=bool(mesh.is_watertight) if mesh is not None else False)
    if mesh is None:
        return []
    from gmg import guard
    budget = guard.constant('pack_budget_faces', 4000, 'kit:PREREG A.6 4000 faces (kit 4096)')
    partner = np.asarray(obs['pocc']) > 0
    if grow_m:
        partner = ndimage.binary_dilation(partner, iterations=int(grow_m))
    tries, k_used = [], None
    for k in range(1, MAX_COARSEN + 1):
        if k == 1:
            mk = mesh
        else:
            co = _coarsen(occ_m, partner, st == STATE_OBSERVED, k)
            if not co.any():
                tries.append(dict(k=k, empty=True))
                continue
            mk = _march(co, lo, k * vox)
        ok, nf = _packable(mk, budget)
        tries.append(dict(k=k, faces_dense=int(len(mk.faces)), euler=int(mk.euler_number),
                          watertight_dense=bool(mk.is_watertight), packed_faces=nf, packed_watertight=ok))
        if ok:
            mesh, k_used = mk, k
            break
    if k_used is None:
        k_used = 1                                   # nothing packs watertight: keep the 4 mm surface (V1 vetoes it)
        flags.append('not_packable_watertight')
    elif k_used > 1:
        flags.append(f'surface_coarsened_x{k_used}')
    rep.update(coarsen_k=k_used, surface_vox_mm=round(k_used * vox * 1e3, 3), coarsen_tries=tries)
    if chk and chk['deep_total']:
        flags.append('partner_deep_samples')
    return [Candidate(cid='hull', producer='P-HULL', cls='HULL', mesh=mesh, params=dict(grow=grow_m, coarsen_k=k_used),
                      n_params=0, built_on_frames='all', flags=flags, report=rep)]
