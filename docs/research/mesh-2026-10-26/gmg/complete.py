"""Completion rules (module M8 of SPEC section 7; minimal form for build step B1, full in B8).

  partner_clip(occ, obs, grow=0) -> occ          SPEC section 4 mechanism 4 / section 9 rule 2 on a voxel volume:
                                                 completed (non-OBSERVED) voxels that received a partner sample in a
                                                 contact frame (the pocc grid) are removed, optionally grown by GROW
                                                 voxels (6-connected); the target's own OBSERVED voxels are its evidence
                                                 and are never removed here (V2 judges the result)
  clip_check(mesh, bundle, obj) -> dict          the V2 (a) test applied during construction: per partner, the number
                                                 of partner samples (contact frames) inside the mesh deeper than b
                                                 below its surface, and the most in any one frame
  clip_check_grid(occ, obs, bundle, obj) -> dict the same test on a voxel volume (HULL): a sample is deep if its voxel
                                                 is occupied and the voxel's distance to the nearest unoccupied voxel
                                                 centre, minus half a voxel, exceeds b
B1 builds no structural completion (lathe, mirror, part, FUSE: B8, B11, B15), so the support-plane closing of SPEC
section 9 rule 3b is not used yet; the HULL is the only completed volume.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

from gmg import contact as CT, geom
from gmg.bundle import STATE_OBSERVED


def partner_clip(occ, obs, grow=0):
    pocc = np.asarray(obs['pocc']) > 0
    if grow:
        pocc = ndimage.binary_dilation(pocc, iterations=int(grow))
    return occ & ~(pocc & (np.asarray(obs['state']) != STATE_OBSERVED))


def clip_check(mesh, bundle, obj):
    out = dict(deep_total=0, deep_max_frame=0, partners={})
    for p in bundle.partners(obj):
        frames = bundle.contact(obj, p)['contact']
        if not frames or len(mesh.faces) == 0:
            out['partners'][p] = dict(contact_frames=len(frames), deep=0, deep_max_frame=0)
            continue
        X, _, fid, n_p = CT.partner_samples(bundle, obj, p, frames)
        b = bundle.band(obj, p)
        lo, hi = mesh.bounds
        near = np.all((X >= lo - 1e-9) & (X <= hi + 1e-9), axis=1)
        deep = np.zeros(len(X), bool)
        if near.any():
            ins, info = geom.inside(mesh, X[near])
            d, _, _ = geom.Closest(mesh).query(X[near])
            deep[np.nonzero(near)[0]] = ins & (d > b)
        per = np.bincount(np.searchsorted(np.asarray(sorted(set(frames))), fid[deep]), minlength=len(set(frames)))
        rec = dict(contact_frames=len(frames), band_mm=round(b * 1e3, 3), deep=int(deep.sum()),
                   deep_max_frame=int(per.max()) if len(per) else 0)
        out['partners'][p] = rec
        out['deep_total'] += rec['deep']
        out['deep_max_frame'] = max(out['deep_max_frame'], rec['deep_max_frame'])
    return out


def clip_check_grid(occ, obs, bundle, obj):
    lo, vox = np.asarray(obs['lo'], np.float64), float(obs['vox'])
    depth = ndimage.distance_transform_edt(np.pad(occ, 1)).astype(np.float64)[1:-1, 1:-1, 1:-1] * vox - 0.5 * vox
    out = dict(deep_total=0, deep_max_frame=0, partners={}, method='voxel depth (distance transform)')
    for p in bundle.partners(obj):
        frames = sorted(set(bundle.contact(obj, p)['contact']))
        if not frames:
            out['partners'][p] = dict(contact_frames=0, deep=0, deep_max_frame=0)
            continue
        X, _, fid, n_p = CT.partner_samples(bundle, obj, p, frames)
        b = bundle.band(obj, p)
        vi, ok = CT._vox_index(X, lo, vox, occ.shape)
        deep = np.zeros(len(X), bool)
        if ok.any():
            t = tuple(vi[ok].T)
            deep[np.nonzero(ok)[0]] = occ[t] & (depth[t] > b)
        per = np.bincount(np.searchsorted(np.asarray(frames), fid[deep]), minlength=len(frames))
        rec = dict(contact_frames=len(frames), band_mm=round(b * 1e3, 3), deep=int(deep.sum()),
                   deep_max_frame=int(per.max()) if len(per) else 0)
        out['partners'][p] = rec
        out['deep_total'] += rec['deep']
        out['deep_max_frame'] = max(out['deep_max_frame'], rec['deep_max_frame'])
    return out
