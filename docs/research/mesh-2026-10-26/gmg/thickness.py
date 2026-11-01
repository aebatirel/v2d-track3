"""Unseen-wall thickness default t0 (PREREG A.1; SPEC section 8; build step B1 for t0_dev, B13 for the clean t0).

  two_sided_measurements(obs) -> (T (m,), info)
      the finite two-sided thicknesses that autokit/shell.shell_sheet measures on the owned points: the same calls in
      the same order as shell_sheet steps 1-3 (finite filter, point_normals, grazing / planarity filter,
      directional_samples, two_sided_thickness), stopping before resolve_sides, so every measurement counts once per
      sample (shell_sheet's report rounds the share and the median, so it cannot be used for the counts)
  aggregate(per_episode) -> dict
      A.1: per object-episode the median of its finite measurements; per object the median over its episodes; t0 =
      the median over objects, clamped to [1.5 mm, 8 mm]; fittable if at least 5 objects have at least 200 finite
      measurements over their episodes; otherwise the pre-registered fallback 2.5 mm (scan-coincident, brief leak)
"""
from __future__ import annotations

import numpy as np

CLAMP = (0.0015, 0.008)          # PREREG A.1 / A.6: sensor floor about 2 sigma; two voxels
MIN_OBJECTS, MIN_MEAS = 5, 200   # PREREG A.1 fittability
FALLBACK = 0.0025                # PREREG A.1 fallback, labelled scan-coincident (brief leak)


def two_sided_measurements(obs):
    from autokit import shell as SH
    P = np.asarray(obs['pts'], np.float64); C = np.asarray(obs['cam'], np.float64)
    F = np.asarray(obs['frame']) if 'frame' in obs else np.zeros(len(P), int)
    own = np.asarray(obs.get('own', np.zeros(len(P), np.uint8)))
    ok = np.all(np.isfinite(P), 1) & np.all(np.isfinite(C), 1) & (own == 0)
    P, C, F = P[ok], C[ok], F[ok]
    info = dict(points=int(len(P)))
    if len(P) < SH.PATCH_MIN_PTS:
        info['empty'] = 'too few points'
        return np.zeros(0), info
    n, planar = SH.point_normals(P, C, F, SH.VOXEL)
    front = (np.einsum('ij,ij->i', n, SH._unit(C - P)) >= SH.COS_GRAZE) & (planar >= SH.PLANAR_MIN)
    P, n = P[front], n[front]
    if len(P) < 16:
        info['empty'] = 'too few front points'
        return np.zeros(0), info
    smp = SH.directional_samples(P, n, SH.VOXEL)
    S, N = smp['s'], smp['n']
    info['samples'] = int(len(S))
    if len(S) < 16:
        info['empty'] = 'too few samples'
        return np.zeros(0), info
    T = SH.two_sided_thickness(S, N)
    T = T[np.isfinite(T)]
    info.update(measured=int(len(T)), median_mm=round(float(np.median(T)) * 1e3, 4) if len(T) else None)
    return T, info


def aggregate(per_episode):
    """per_episode: [{obj, ep, n, median_m}] -> A.1 result dict (t0_m, fittable, per_object, ...)."""
    objs = {}
    for r in per_episode:
        if r['n'] > 0 and r['median_m'] is not None:
            objs.setdefault(r['obj'], []).append(r)
    per_obj = {}
    for o, rows in sorted(objs.items()):
        per_obj[o] = dict(episodes=[r['ep'] for r in rows], n=int(sum(r['n'] for r in rows)),
                          median_m=float(np.median([r['median_m'] for r in rows])))
    big = [o for o, d in per_obj.items() if d['n'] >= MIN_MEAS]
    fittable = len(big) >= MIN_OBJECTS
    raw = float(np.median([d['median_m'] for d in per_obj.values()])) if per_obj else None
    out = dict(rule='PREREG A.1', objects=per_obj, objects_with_200=big, fittable=bool(fittable),
               t0_raw_m=raw, clamp_m=list(CLAMP))
    if fittable:
        out.update(t0_m=float(np.clip(raw, *CLAMP)), origin='fitted:own')
    else:
        out.update(t0_m=FALLBACK, origin='fallback:scan-coincident (brief leak), PREREG A.1 not fittable')
    return out
