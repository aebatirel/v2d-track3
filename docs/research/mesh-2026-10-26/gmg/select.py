"""The frozen GT-free selection rule S1 (module M14 of SPEC section 7; PREREG A.5 exactly; build step B5).

  pick(cands, feats=None, variant=None, *, kit_symmetric=None, gen_view_overlap=None, status=None) -> dict
      cands: the pool dict score.score_pool returns (preferred: kit_symmetric, gen_view_overlap and the pool flags
      are taken from it); or its rows (each carries them under 'pool'); or candidate metas (Candidate objects or
      dicts: cid, cls, n_params) with feats {cid: feature row}. kit_symmetric and gen_view_overlap are REQUIRED
      when the input does not carry them (hand-made rows), and must agree with it when it does (B5 round 2: a
      silent default False applied V5 to kit-symmetric objects).
      Feature keys used: E, E_reps (the paired bootstrap replicates of A.4), v1/v2/v3/v4 (dicts with 'veto'; V3
      counts only when applied, i.e. tau is set), amb (self-ambiguity with TRUSTED balls only: amb_mm, amb_floor_mm,
      flip_risk, flip_units; flip_risk None = unknown, e.g. untrusted balls without a ball-free mesh: neither safe
      nor risky for V5, last on key 2, the pick is flagged flip_risk_unknown), trusted_markers (number of trusted
      balls attached).
      variant: dict(K, b_tie, prior) (PREREG A.7 menu; default V0 = (3, 1, on)). K is used by score.plan, not here.
      status: dict(track_fail, identity_swap, low_coverage, gpu_ran) for the fallback ladder (SPEC section 13).
  Returns dict(cid, variant, best, tie_set, order, keys, trace, fallback, flags).

PREREG A.5, as frozen:
  1. Remove vetoed candidates (V1-V5). V5 removes flip-risk candidates only if at least one feasible candidate is not
     flip-risk, and never for a kit-symmetric object (beige_cup, blue_cup, white_pot_lid).
  2. best = the lowest E. Tie set T = feasible candidates with E(c) - E(best) <= b_tie x SE_diff(c).
  3. Order T lexicographically by: (1) class STRUCT, FUSE, GEN, SHELL, HULL (gen_view_overlap pool: STRUCT, SHELL,
     FUSE, GEN, HULL); (2) flip safety, larger floor((amb - floor) / floor) first, trusted balls only (skipped for
     kit-symmetric objects); (3) trusted markers attached first; (4) fewer free parameters first (only if the
     parameter prior is on); (5) lower E.
  4. The first candidate in T is the pick.
  5. Nothing feasible: the fallback ladder (SPEC section 13): ABSTAIN_HULL, PRIOR_GEN, PRIOR_PUBLIC; never
     library_v1-v4.
Determinism (B5, DEVIATIONS): A.5 leaves full ties (equal on all five keys) unordered; a sixth key, the cid string,
orders them, and best is min (E, cid), so the result never depends on the input order. A candidate whose E is
undefined (no held-out point in any block) is ranked with E = +inf and flagged.
"""
from __future__ import annotations

import math

import numpy as np

from gmg import guard

CLASSES = ('STRUCT', 'FUSE', 'GEN', 'SHELL', 'HULL')
ORDER_OVERLAP = ('STRUCT', 'SHELL', 'FUSE', 'GEN', 'HULL')
VARIANT_V0 = dict(K=3, b_tie=1, prior=True)
MENU = tuple(dict(K=k, b_tie=b, prior=p) for k in (3, 5) for b in (1, 2) for p in (True, False))
VETOES = ('V1', 'V2', 'V3', 'V4')
LADDER = ('ABSTAIN_HULL', 'PRIOR_GEN', 'PRIOR_PUBLIC')


def consts():
    return dict(
        order=guard.constant('class_order', list(CLASSES), 'informed:class order ([D] hand kits against generators)'),
        order_overlap=guard.constant('class_order_gen_view_overlap', list(ORDER_OVERLAP),
                                     'informed:class order (PREREG A.5 gen_view_overlap pool)'),
        b_tie_menu=guard.constant('variant_menu_b_tie', [1, 2], 'generic:PREREG A.7 menu b_tie in {1, 2} SE'),
        v0=guard.constant('variant_v0', dict(VARIANT_V0), 'generic:PREREG A.7 default V0 = (3, 1 SE, prior on)'),
        v5=guard.constant('v5_flip_rule', 'amb - floor < floor', 'informed:V5 (seen on library and board meshes)'),
    )


def _get(c, k, default=None):
    return c.get(k, default) if isinstance(c, dict) else getattr(c, k, default)


def _pool_flags(cands, feats, kit_symmetric, gen_view_overlap):
    """(rows-or-metas, kit_symmetric, gen_view_overlap, pool flags) from a score_pool dict, its rows or a hand-made
    list; raises if a flag is neither carried by the input nor given, or if a given one contradicts the input."""
    pool_flags = []
    if isinstance(cands, dict):
        if 'rows' not in cands:
            raise ValueError('select: a dict input must be the score_pool output (with rows)')
        carried = dict(kit_symmetric=bool(cands['kit_symmetric']), gen_view_overlap=bool(cands['gen_view_overlap']))
        pool_flags = list(cands.get('flags') or [])
        cands = cands['rows']
    else:
        tags = [_get(c, 'pool') if feats is None else _get(feats.get(_get(c, 'cid')) or {}, 'pool') for c in cands]
        carried = None
        if tags and all(isinstance(t, dict) for t in tags):
            seen = {(bool(t['kit_symmetric']), bool(t['gen_view_overlap'])) for t in tags}
            if len(seen) != 1 or len({t.get('obj') for t in tags}) != 1:
                raise ValueError(f'select: rows from different pools ({sorted(seen)})')
            ks, gv = seen.pop()
            carried = dict(kit_symmetric=ks, gen_view_overlap=gv)
    given = dict(kit_symmetric=kit_symmetric, gen_view_overlap=gen_view_overlap)
    out = {}
    for k, v in given.items():
        if carried is None:
            if v is None:
                raise ValueError(f'select: {k} is required (True / False) when the input does not carry it; pass the '
                                 f'score_pool dict, its rows, or {k}=...')
            out[k] = bool(v)
        else:
            if v is not None and bool(v) != carried[k]:
                raise ValueError(f'select: {k}={v} contradicts the pool ({carried[k]})')
            out[k] = carried[k]
    return list(cands), out['kit_symmetric'], out['gen_view_overlap'], pool_flags


def _rows(cands, feats):
    rows = []
    for c in cands:
        cid = _get(c, 'cid')
        r = dict(feats[cid]) if feats is not None else dict(c)
        for k in ('cid', 'cls', 'n_params'):
            if _get(c, k) is not None:
                r[k] = _get(c, k)
        if r.get('cls') not in CLASSES:
            raise ValueError(f'select: candidate {cid}: class {r.get("cls")!r} is not one of {CLASSES}')
        rows.append(r)
    cids = [r['cid'] for r in rows]
    if len(set(cids)) != len(cids):
        raise ValueError(f'select: duplicate cids {sorted({c for c in cids if cids.count(c) > 1})}')
    return rows


def _veto(r, key):
    v = r.get(key.lower())
    if v is None:
        return False
    if isinstance(v, dict):
        if key == 'V3' and not v.get('applied', v.get('tau') is not None):
            return False
        return bool(v.get('veto'))
    return bool(v)


def vetoes_v1_v4(r):
    """The A.3 vetoes V1-V4 of one row (V3 only when applied, i.e. tau is set)."""
    if 'vetoes' in r and isinstance(r['vetoes'], (list, tuple)) and not any(k in r for k in ('v1', 'v2', 'v3', 'v4')):
        return [v for v in r['vetoes'] if v in VETOES]
    return [k for k in VETOES if _veto(r, k)]


def _E(r):
    e = r.get('E')
    return float(e) if e is not None and np.isfinite(e) else math.inf


def _units(r):
    a = r.get('amb') or {}
    u = a.get('flip_units')
    return None if u is None else int(u)


def _flip_risk(r):
    a = r.get('amb') or {}
    return a.get('flip_risk')


def order_key(r, *, overlap, kit_symmetric, prior):
    """The A.5 lexicographic key of one tie-set row (smaller first), plus the deterministic sixth key (cid)."""
    order = ORDER_OVERLAP if overlap else CLASSES
    u = _units(r)
    k2 = 0 if kit_symmetric else (math.inf if u is None else -u)
    k3 = 0 if int(r.get('trusted_markers') or 0) > 0 else 1
    k4 = int(r.get('n_params') or 0) if prior else 0
    return (order.index(r['cls']), k2, k3, k4, _E(r), str(r['cid']))


def _se_diff(r, best):
    a, b = r.get('E_reps'), best.get('E_reps')
    if a is None or b is None:
        raise ValueError(f'select: {r["cid"]} or {best["cid"]} lacks E_reps (the paired bootstrap of A.4)')
    d = np.asarray(a, np.float64) - np.asarray(b, np.float64)
    d = d[np.isfinite(d)]                    # replicates where E is undefined for either (score.se_diff alike)
    return float(np.std(d)) if len(d) else float('nan')


def fallback(rows, status, trace):
    """SPEC section 13, in order (Normal is handled by pick): ABSTAIN_HULL (no feasible candidate, coverage not low,
    track usable): the HULL candidate, if it is watertight after the kit decode; PRIOR_GEN (TRACK_FAIL, IDENTITY_SWAP
    or low coverage, and the GPU producers ran): the lowest-E generated mesh (GEN, watertight after decode);
    PRIOR_PUBLIC otherwise (resolved by the caller: library_v5 or the gmg pick on the anchor public episode; needs
    owner decision O2). Returns (row or None, rung, flags)."""
    st = dict(track_fail=False, identity_swap=False, low_coverage=False, gpu_ran=False) | dict(status or {})
    broken = bool(st['track_fail'] or st['identity_swap'])
    shippable = [r for r in rows if not _veto(r, 'V1')]
    if not broken and not st['low_coverage']:
        hull = sorted([r for r in shippable if r['cls'] == 'HULL'], key=lambda r: (_E(r), str(r['cid'])))
        if hull:
            trace.append(dict(step='fallback', rung='ABSTAIN_HULL', cid=hull[0]['cid']))
            return hull[0], 'ABSTAIN_HULL', ['fallback', 'abstain_hull']
        trace.append(dict(step='fallback', rung='ABSTAIN_HULL', result='no HULL watertight after the kit decode'))
    if (broken or st['low_coverage']) and st['gpu_ran']:
        gen = sorted([r for r in shippable if r['cls'] == 'GEN'], key=lambda r: (_E(r), str(r['cid'])))
        if gen:
            trace.append(dict(step='fallback', rung='PRIOR_GEN', cid=gen[0]['cid']))
            return gen[0], 'PRIOR_GEN', ['fallback', 'prior_gen']
        trace.append(dict(step='fallback', rung='PRIOR_GEN', result='no GEN candidate watertight after decode'))
    trace.append(dict(step='fallback', rung='PRIOR_PUBLIC', result='resolved by the caller (library_v5 or the anchor '
                      'public pick; owner decision O2); never library_v1-v4'))
    return None, 'PRIOR_PUBLIC', ['fallback', 'prior_public', 'needs_owner_O2']


def pick(cands, feats=None, variant=None, *, kit_symmetric=None, gen_view_overlap=None, status=None):
    """PREREG A.5 (module docstring). Deterministic: the result does not depend on the order of CANDS."""
    consts()
    cands, kit_symmetric, gen_view_overlap, pool_flags = _pool_flags(cands, feats, kit_symmetric, gen_view_overlap)
    variant = dict(VARIANT_V0 if variant is None else variant)
    if variant not in [dict(m) for m in MENU]:
        raise ValueError(f'select: variant {variant} is not in the PREREG A.7 menu')
    rows = sorted(_rows(cands, feats), key=lambda r: str(r['cid']))
    st = dict(track_fail=False, identity_swap=False, low_coverage=False, gpu_ran=False) | dict(status or {})
    trace, flags = [], list(pool_flags)
    if gen_view_overlap:
        flags.append('gen_view_overlap')
    if st['low_coverage']:
        flags.append('low_coverage')
    undefined = [r['cid'] for r in rows if not np.isfinite(_E(r))]
    if undefined:
        flags.append('E_undefined')
        trace.append(dict(step='E', undefined=undefined, note='ranked with E = +inf'))
    out = dict(cid=None, variant=variant, best=None, tie_set=[], order=[], keys={}, trace=trace, fallback=None,
               flags=flags)
    if st['track_fail'] or st['identity_swap']:
        flags.append('track_fail' if st['track_fail'] else 'identity_swap')
        trace.append(dict(step='status', route='TRACK_FAIL / IDENTITY_SWAP: the ladder (SPEC section 13); no S1 pick '
                          'on a broken track'))
        row, rung, fl = fallback(rows, st, trace)
        out.update(cid=row['cid'] if row else None, fallback=rung)
        flags.extend(fl)
        return out
    # 1. vetoes V1-V4, then V5
    removed = {r['cid']: vetoes_v1_v4(r) for r in rows if vetoes_v1_v4(r)}
    feas = [r for r in rows if r['cid'] not in removed]
    trace.append(dict(step='vetoes V1-V4', removed=dict(removed),
                      not_applied=['V3 (tau not set)'] if any(isinstance(r.get('v3'), dict) and not
                                                             r['v3'].get('applied', True) for r in rows) else []))
    if kit_symmetric:
        trace.append(dict(step='V5', applied=False, reason='kit-symmetric object (PREREG A.3)'))
    else:
        risk = [r['cid'] for r in feas if _flip_risk(r) is True]
        unknown = [r['cid'] for r in feas if _flip_risk(r) is None]
        safe = [r['cid'] for r in feas if _flip_risk(r) is False]
        if risk and safe:
            for c in risk:
                removed[c] = ['V5']
            feas = [r for r in feas if r['cid'] not in risk]
            trace.append(dict(step='V5', applied=True, removed=risk, unknown=unknown))
        else:
            trace.append(dict(step='V5', applied=False, flip_risk=risk, unknown=unknown,
                              reason='no feasible candidate is free of flip risk' if risk else 'no flip-risk '
                                                                                               'candidate'))
    if not feas:
        trace.append(dict(step='feasible', n=0))
        row, rung, fl = fallback(rows, st, trace)
        out.update(cid=row['cid'] if row else None, fallback=rung)
        flags.extend(['no_feasible'] + fl)
        return out
    # 2. best and the tie band
    best = min(feas, key=lambda r: (_E(r), str(r['cid'])))
    tie = []
    for r in feas:
        dE = _E(r) - _E(best)
        sd = _se_diff(r, best)
        if r is best or dE <= variant['b_tie'] * sd:
            tie.append((r, dE, sd))
    out['best'] = best['cid']
    out['tie_set'] = [(r['cid'], round(float(d), 6) if np.isfinite(d) else None, round(s, 6)) for r, d, s in tie]
    trace.append(dict(step='tie band', best=best['cid'], E_best=_E(best), b_tie=variant['b_tie'],
                      tie_set=out['tie_set']))
    # 3. fixed priors (lexicographic), 4. the first is the pick
    keys = {r['cid']: order_key(r, overlap=gen_view_overlap, kit_symmetric=kit_symmetric, prior=variant['prior'])
            for r, _, _ in tie}
    order = sorted((r for r, _, _ in tie), key=lambda r: keys[r['cid']])
    out['order'] = [r['cid'] for r in order]
    out['keys'] = {c: [x if not (isinstance(x, float) and not np.isfinite(x)) else str(x) for x in k]
                   for c, k in keys.items()}
    trace.append(dict(step='priors', order=out['order'],
                      keys='class (' + ' > '.join(ORDER_OVERLAP if gen_view_overlap else CLASSES) + '); flip safety '
                           + ('skipped (kit-symmetric)' if kit_symmetric else 'larger floor((amb - floor) / floor) '
                              'first') + '; trusted markers first; ' + ('fewer free parameters; ' if variant['prior']
                                                                         else 'parameter prior off; ')
                           + 'lower E; cid'))
    pk = order[0]
    out['cid'] = pk['cid']
    if not kit_symmetric and _flip_risk(pk) is True:
        flags.append('flip_risk')
    if not kit_symmetric and _flip_risk(pk) is None:
        flags.append('flip_risk_unknown')
    return out
