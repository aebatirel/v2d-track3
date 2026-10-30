"""P-HULL (SPEC section 8; minimal form for build step B1): every voxel of the bundle grid that is not FREE, inside
the seeded component, above the at-rest table plane, minus the partner clip, closed by marching cubes. Always closed,
thick where unseen; the fallback of the ladder (SPEC section 13).

Choices for B1 (dev bundles, DEVIATIONS B1): the seeded component is the 6-connected component of the kept voxels
that holds the most OBSERVED voxels (dev bundles carry no seeds; the grid is the old obs_all box); 'above the table'
is the at-rest table plane of the bundle (n.x + d >= 0 at the voxel centre), and no cut is made for an object with no
rest plane; the partner clip removes non-OBSERVED voxels with pocc > 0 and is grown by one voxel at a time (at most
twice) while the construction-time V2 (a) check still finds partner samples deeper than the band."""
from __future__ import annotations

import numpy as np
import trimesh
from scipy import ndimage

from gmg import complete
from gmg.bundle import STATE_FREE, STATE_OBSERVED
from gmg.producers import Candidate

MAX_GROW = 2


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
    mesh, grow, chk = None, 0, None
    for grow in range(MAX_GROW + 1):
        occ = complete.partner_clip(occ0, obs, grow=grow)
        lab, n = ndimage.label(occ)
        if n == 0:
            break
        obs_lab = np.bincount(lab[(st == STATE_OBSERVED) & (lab > 0)], minlength=n + 1)
        keep = int(obs_lab[1:].argmax()) + 1 if obs_lab[1:].any() else int(np.bincount(lab.ravel())[1:].argmax()) + 1
        occ = lab == keep
        mesh = _march(occ, lo, vox)
        chk = complete.clip_check(mesh, b, obj)
        rep.update(components=int(n), kept_voxels=int(occ.sum()), kept_observed=int(obs_lab[keep]))
        if chk['deep_total'] == 0:
            break
    rep.update(partner_clip_grow=grow, partner_clip=chk, faces_dense=int(len(mesh.faces)) if mesh is not None else 0,
               watertight_dense=bool(mesh.is_watertight) if mesh is not None else False)
    if mesh is None:
        return []
    if chk and chk['deep_total']:
        flags.append('partner_deep_samples')
    return [Candidate(cid='hull', producer='P-HULL', cls='HULL', mesh=mesh, params=dict(grow=grow), n_params=0,
                      built_on_frames='all', flags=flags, report=rep)]
