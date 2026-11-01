"""B5 tests of gmg/select.py: the frozen selection rule S1 (PREREG A.5) and the fallback ladder (SPEC section 13).

  GMG_MODE=dev python docs/research/mesh-2026-10-26/gmg/tests/test_select.py           (venv python)

Pure logic on hand-made feature rows (no file, no bundle): vetoes V1-V5, the tie band with the paired bootstrap
SE_diff, the lexicographic priors in both class orders, the deterministic tie order (pass condition of SPEC 24 B5:
"the tie order is deterministic"), the ladder. The synthetic-scene tests of V5 with trusted balls are in
test_score.py (B5Synthetic).
"""
import itertools
import os
import sys
import unittest

os.environ.setdefault('GMG_MODE', 'dev')
HERE = os.path.dirname(os.path.abspath(__file__))
GMG = os.path.dirname(HERE)
MR = os.path.dirname(GMG)
if MR not in sys.path:
    sys.path.insert(0, MR)
from gmg import guard  # noqa: E402,F401
import numpy as np  # noqa: E402

from gmg import select as S  # noqa: E402

N_REPS = 200


def reps(E, sd=0.0, seed=0, base=None):
    """Bootstrap replicates of a candidate with mean E: BASE (shared noise, paired) + its own noise of SD sd."""
    rng = np.random.default_rng(seed)
    b = np.zeros(N_REPS) if base is None else base
    own = rng.normal(0.0, 1.0, N_REPS)
    own = (own - own.mean()) / own.std() * sd if sd > 0 else np.zeros(N_REPS)
    return E + b + own


def pick(cands, *a, **kw):
    """S.pick on hand-made rows (they carry no pool tag): kit_symmetric and gen_view_overlap default to False here;
    select.pick itself requires them for such input (InputTests.test_pool_flags_required_or_carried)."""
    kw.setdefault('kit_symmetric', False)
    kw.setdefault('gen_view_overlap', False)
    return S.pick(cands, *a, **kw)


def row(cid, cls, E, *, sd=0.0, seed=0, base=None, n_params=0, units=3, risk=False, markers=0, v1=False, v2=False,
        v3=False, v3_applied=True, v4=False, floor=1.0):
    amb = None if units is None else dict(amb_mm=floor * (units + 1.5), amb_floor_mm=floor, flip_units=units,
                                          flip_risk=risk)
    return dict(cid=cid, cls=cls, E=E, E_reps=reps(E, sd, seed, base), n_params=n_params, amb=amb,
                trusted_markers=markers, v1=dict(veto=v1), v2=dict(veto=v2),
                v3=dict(veto=v3, applied=v3_applied, tau=0.1 if v3_applied else None), v4=dict(veto=v4))


class ImportTests(unittest.TestCase):
    def test_stdlib_select_not_shadowed(self):
        import select as stdlib_select
        self.assertTrue(hasattr(stdlib_select, 'select'), 'gmg/select.py must only be imported as gmg.select')
        self.assertEqual(S.__name__, 'gmg.select')


class VetoTests(unittest.TestCase):
    def test_v1_v4_removed(self):
        rows = [row('a', 'STRUCT', 1.0, v1=True), row('b', 'STRUCT', 1.1, v2=True), row('c', 'SHELL', 1.2, v3=True),
                row('d', 'SHELL', 1.3, v4=True), row('e', 'HULL', 5.0)]
        p = pick(rows)
        self.assertEqual(p['cid'], 'e')
        self.assertEqual(p['trace'][0]['removed'], {'a': ['V1'], 'b': ['V2'], 'c': ['V3'], 'd': ['V4']})

    def test_v3_counts_only_when_applied(self):
        rows = [row('a', 'STRUCT', 1.0, v3=True, v3_applied=False), row('b', 'SHELL', 1.0)]
        p = pick(rows)
        self.assertEqual(p['cid'], 'a')
        self.assertIn('V3 (tau not set)', p['trace'][0]['not_applied'])

    def test_v5_removes_flip_risk_only_if_a_safe_one_exists(self):
        rows = [row('a', 'STRUCT', 1.0, risk=True, units=0), row('b', 'SHELL', 1.0, units=2)]
        p = pick(rows)
        self.assertEqual(p['cid'], 'b')
        v5 = [t for t in p['trace'] if t['step'] == 'V5'][0]
        self.assertTrue(v5['applied']); self.assertEqual(v5['removed'], ['a'])
        self.assertEqual(p['trace'][0]['removed'], {})                  # the V1-V4 trace does not list V5
        self.assertNotIn('flip_risk', p['flags'])
        rows = [row('a', 'STRUCT', 1.0, risk=True, units=0), row('b', 'SHELL', 1.0, risk=True, units=-1)]
        p = pick(rows)
        self.assertEqual(p['cid'], 'a')                         # V5 not applied: all feasible are flip-risk
        self.assertIn('flip_risk', p['flags'])
        v5 = [t for t in p['trace'] if t['step'] == 'V5'][0]
        self.assertFalse(v5['applied'])

    def test_v5_safe_candidate_vetoed_elsewhere_does_not_count(self):
        rows = [row('a', 'STRUCT', 1.0, risk=True, units=0), row('b', 'SHELL', 1.0, units=2, v2=True)]
        p = pick(rows)
        self.assertEqual(p['cid'], 'a')                         # b is not feasible, so V5 cannot apply
        self.assertIn('flip_risk', p['flags'])

    def test_v5_and_flip_key_skipped_for_kit_symmetric(self):
        rows = [row('a', 'STRUCT', 1.0, risk=True, units=0, n_params=5), row('b', 'STRUCT', 1.0, units=4, n_params=9)]
        p = pick(rows, kit_symmetric=True)
        self.assertEqual(p['cid'], 'a')                         # flip key skipped: fewer parameters decides
        self.assertNotIn('flip_risk', p['flags'])
        p = pick(rows, kit_symmetric=False)
        self.assertEqual(p['cid'], 'b')                         # V5 removes a


class TieBandTests(unittest.TestCase):
    def test_band_uses_paired_se_diff(self):
        base = np.random.default_rng(9).normal(0, 0.5, N_REPS)          # shared (paired) variation: cancels
        best = row('best', 'SHELL', 1.00, base=base, sd=0.0)
        near = row('near', 'STRUCT', 1.05, base=base, sd=0.10, seed=1)   # dE 0.05 <= 1 x 0.10
        far = row('far', 'STRUCT', 1.30, base=base, sd=0.10, seed=2)     # dE 0.30 > 1 x and > 2 x 0.10
        p = pick([best, near, far])
        self.assertEqual(p['best'], 'best')
        self.assertEqual(sorted(c for c, _, _ in p['tie_set']), ['best', 'near'])
        self.assertEqual(p['cid'], 'near')                      # STRUCT before SHELL
        se = {c: s for c, _, s in p['tie_set']}
        self.assertAlmostEqual(se['near'], 0.10, places=6)      # the shared noise cancels in the paired difference
        self.assertEqual(se['best'], 0.0)
        p2 = pick([best, near, far], variant=dict(K=3, b_tie=2, prior=True))
        self.assertEqual(sorted(c for c, _, _ in p2['tie_set']), ['best', 'near'])
        far2 = row('far', 'STRUCT', 1.15, base=base, sd=0.10, seed=2)    # 0.15: out at 1 SE, in at 2 SE
        self.assertNotIn('far', [c for c, _, _ in pick([best, near, far2])['tie_set']])
        self.assertIn('far', [c for c, _, _ in pick([best, near, far2],
                                                      variant=dict(K=3, b_tie=2, prior=True))['tie_set']])

    def test_variant_must_be_in_menu(self):
        with self.assertRaises(ValueError):
            pick([row('a', 'SHELL', 1.0)], variant=dict(K=4, b_tie=1, prior=True))
        self.assertEqual(len(S.MENU), 8)
        self.assertIn(S.VARIANT_V0, [dict(m) for m in S.MENU])

    def test_missing_reps_raise(self):
        r = row('a', 'SHELL', 1.0); r2 = row('b', 'SHELL', 1.1)
        del r2['E_reps']
        with self.assertRaises(ValueError):
            pick([r, r2])


class OrderTests(unittest.TestCase):
    """PREREG A.5 step 3 keys, each deciding when all earlier keys are equal; every row is in the tie set (equal E,
    zero SE) unless stated."""

    def test_class_order(self):
        rows = [row(c.lower(), c, 1.0) for c in ('HULL', 'SHELL', 'GEN', 'FUSE', 'STRUCT')]
        self.assertEqual(pick(rows)['order'], ['struct', 'fuse', 'gen', 'shell', 'hull'])
        self.assertEqual(pick(rows, gen_view_overlap=True)['order'], ['struct', 'shell', 'fuse', 'gen', 'hull'])
        self.assertIn('gen_view_overlap', pick(rows, gen_view_overlap=True)['flags'])

    def test_flip_units_then_markers_then_params_then_E_then_cid(self):
        rows = [row('p_u1', 'SHELL', 1.0, units=1),
                row('p_u3_m0_n2', 'SHELL', 1.0, units=3, markers=0, n_params=2),
                row('p_u3_m2_n9', 'SHELL', 1.0, units=3, markers=2, n_params=9),
                row('p_u3_m2_n4_E2', 'SHELL', 1.0 + 1e-9, sd=0.01, seed=7, units=3, markers=2, n_params=4),
                row('p_u3_m2_n4_b', 'SHELL', 1.0, units=3, markers=2, n_params=4),
                row('p_u3_m2_n4_a', 'SHELL', 1.0, units=3, markers=2, n_params=4)]
        p = pick(rows)
        self.assertEqual(p['order'], ['p_u3_m2_n4_a', 'p_u3_m2_n4_b', 'p_u3_m2_n4_E2', 'p_u3_m2_n9',
                                      'p_u3_m0_n2', 'p_u1'])
        p = pick(rows, variant=dict(K=3, b_tie=1, prior=False))          # parameter prior off: E, then cid
        self.assertEqual(p['order'], ['p_u3_m2_n4_a', 'p_u3_m2_n4_b', 'p_u3_m2_n9', 'p_u3_m2_n4_E2',
                                      'p_u3_m0_n2', 'p_u1'])

    def test_infinite_flip_units_rank_first(self):
        rows = [row('a', 'SHELL', 1.0, units=5), row('b', 'SHELL', 1.0, units=10 ** 6)]
        self.assertEqual(pick(rows)['cid'], 'b')

    def test_unknown_amb_ranks_last_within_class(self):
        rows = [row('a', 'SHELL', 1.0, units=None), row('b', 'SHELL', 1.0, units=-1, risk=True)]
        p = pick(rows)
        self.assertEqual(p['order'], ['b', 'a'])

    def test_deterministic_under_every_input_order(self):
        """Pass condition (SPEC 24 B5): the tie order is deterministic. Full ties on all five A.5 keys are ordered
        by cid; best is min (E, cid); every permutation of the input and repeated calls give the same result."""
        base = np.random.default_rng(3).normal(0, 0.2, N_REPS)
        rows = [row('z_struct', 'STRUCT', 1.02, base=base, sd=0.05, seed=4, units=2, n_params=6),
                row('a_struct', 'STRUCT', 1.02, base=base, sd=0.05, seed=4, units=2, n_params=6),
                row('m_struct', 'STRUCT', 1.00, base=base, units=2, n_params=6),
                row('shell', 'SHELL', 1.00, base=base, units=2),
                row('hull', 'HULL', 1.00, base=base, units=5, markers=3),
                row('gen', 'GEN', 1.01, base=base, sd=0.05, seed=5, units=2)]
        ref = pick(rows)
        self.assertEqual(ref['order'], ['m_struct', 'a_struct', 'z_struct', 'gen', 'shell', 'hull'])
        self.assertEqual(ref['best'], 'hull')                   # E 1.00 three times: min (E, cid)
        n = 0
        for perm in itertools.permutations(rows):
            p = pick(list(perm))
            self.assertEqual((p['cid'], p['order'], p['best'], p['tie_set']),
                             (ref['cid'], ref['order'], ref['best'], ref['tie_set']))
            n += 1
        self.assertEqual(n, 720)
        twin = [row('b', 'SHELL', 1.0), row('a', 'SHELL', 1.0)]          # equal E: best by cid
        self.assertEqual(pick(twin)['best'], 'a')
        self.assertEqual(pick(twin[::-1])['best'], 'a')

    def test_undefined_E_ranked_last(self):
        rows = [row('a', 'SHELL', float('nan')), row('b', 'HULL', 3.0)]
        p = pick(rows)
        self.assertEqual(p['cid'], 'b'); self.assertIn('E_undefined', p['flags'])


class LadderTests(unittest.TestCase):
    def _vetoed(self):
        return [row('s', 'SHELL', 1.0, v2=True), row('h', 'HULL', 5.0, v2=True), row('g', 'GEN', 2.0, v3=True),
                row('g2', 'GEN', 1.5, v3=True, v1=True)]

    def test_abstain_hull(self):
        p = pick(self._vetoed())
        self.assertEqual((p['cid'], p['fallback']), ('h', 'ABSTAIN_HULL'))
        self.assertIn('no_feasible', p['flags'])

    def test_hull_must_be_watertight(self):
        rows = [row('s', 'SHELL', 1.0, v2=True), row('h', 'HULL', 5.0, v1=True)]
        p = pick(rows)
        self.assertEqual((p['cid'], p['fallback']), (None, 'PRIOR_PUBLIC'))
        self.assertIn('needs_owner_O2', p['flags'])

    def test_low_coverage_prior_gen_or_public(self):
        p = pick(self._vetoed(), status=dict(low_coverage=True, gpu_ran=True))
        self.assertEqual((p['cid'], p['fallback']), ('g', 'PRIOR_GEN'))   # g2 is not watertight after decode
        p = pick(self._vetoed(), status=dict(low_coverage=True, gpu_ran=False))
        self.assertEqual((p['cid'], p['fallback']), (None, 'PRIOR_PUBLIC'))

    def test_low_coverage_with_feasible_is_normal(self):
        rows = [row('s', 'SHELL', 1.0), row('h', 'HULL', 5.0)]
        p = pick(rows, status=dict(low_coverage=True))
        self.assertEqual((p['cid'], p['fallback']), ('s', None))
        self.assertIn('low_coverage', p['flags'])

    def test_track_fail_skips_normal_pick(self):
        rows = [row('s', 'SHELL', 1.0), row('h', 'HULL', 5.0), row('g', 'GEN', 3.0)]
        p = pick(rows, status=dict(track_fail=True, gpu_ran=True))
        self.assertEqual((p['cid'], p['fallback']), ('g', 'PRIOR_GEN'))
        p = pick(rows, status=dict(identity_swap=True))
        self.assertEqual((p['cid'], p['fallback']), (None, 'PRIOR_PUBLIC'))
        self.assertIn('identity_swap', p['flags'])


class InputTests(unittest.TestCase):
    def test_cands_and_feats(self):
        from gmg.producers import Candidate
        cands = [Candidate(cid='a', producer='P-X', cls='SHELL', mesh=None, params={}, n_params=0),
                 Candidate(cid='b', producer='P-Y', cls='STRUCT', mesh=None, params={}, n_params=3)]
        feats = {'a': row('a', 'SHELL', 1.0), 'b': row('b', 'HULL', 1.0)}      # the candidate's class wins
        p = pick(cands, feats)
        self.assertEqual(p['cid'], 'b')

    def test_bad_class_and_duplicates(self):
        with self.assertRaises(ValueError):
            pick([row('a', 'LIBRARY', 1.0)])
        with self.assertRaises(ValueError):
            pick([row('a', 'SHELL', 1.0), row('a', 'HULL', 2.0)])

    def test_pool_flags_required_or_carried(self):
        """B5 round 2: kit_symmetric / gen_view_overlap are taken from the score_pool dict or its rows' pool tags,
        required for untagged input, and a contradicting keyword raises (no silent default False)."""
        rows = [row('safe', 'HULL', 2.0), row('risky', 'SHELL', 1.0, units=0, risk=True)]
        with self.assertRaises(ValueError):
            S.pick(rows)                                                     # untagged rows, no flags given
        with self.assertRaises(ValueError):
            S.pick(rows, kit_symmetric=True)
        tag = dict(obj='blue_cup', kit_symmetric=True, gen_view_overlap=False)
        pool = dict(obj='blue_cup', kit_symmetric=True, gen_view_overlap=False, flags=['gen_input_frames_missing'],
                    rows=[dict(r, pool=dict(tag)) for r in rows])
        for inp in (pool, pool['rows'], pool['rows'][::-1]):
            p = S.pick(inp)
            v5 = [t for t in p['trace'] if t['step'] == 'V5'][0]
            self.assertFalse(v5['applied'])                                  # kit-symmetric: V5 skipped
            self.assertEqual(p['cid'], 'risky')
            self.assertNotIn('flip_risk', p['flags'])
        self.assertIn('gen_input_frames_missing', S.pick(pool)['flags'])     # pool flags reach the pick
        self.assertEqual(S.pick(pool, kit_symmetric=True, gen_view_overlap=False)['cid'], 'risky')
        with self.assertRaises(ValueError):
            S.pick(pool, kit_symmetric=False)                                # contradicts the pool
        with self.assertRaises(ValueError):
            S.pick(pool['rows'], gen_view_overlap=True)
        other = dict(tag, obj='beige_cup')
        with self.assertRaises(ValueError):                                  # rows of two pools
            S.pick([pool['rows'][0], dict(pool['rows'][1], pool=other)])
        with self.assertRaises(ValueError):
            S.pick({'kit_symmetric': True})                                  # a dict that is not a pool
        cands = [dict(cid='safe', cls='HULL', n_params=0), dict(cid='risky', cls='SHELL', n_params=0)]
        feats = {r['cid']: r for r in pool['rows']}
        self.assertEqual(S.pick(cands, feats)['cid'], 'risky')               # tags read from feats too
        self.assertEqual(pick(rows)['cid'], 'safe')                          # not kit-symmetric: V5 applies

    def test_partly_tagged_rows_raise(self):
        """B5 round 3 (verifier's break input 2): one untagged row must not switch off the pool check. Two rows of a
        kit-symmetric pool plus one untagged row, with a contradicting keyword, raised nothing and let V5 change the
        pick; now partly tagged input raises whatever the keywords."""
        tag = dict(obj='blue_cup', K=3, kit_symmetric=True, gen_view_overlap=False, flags=[])
        rows = [dict(row('safe', 'HULL', 2.0), pool=dict(tag)),
                dict(row('risky', 'SHELL', 1.0, units=0, risk=True), pool=dict(tag))]
        self.assertEqual(S.pick(rows)['cid'], 'risky')                       # all tagged: kit-symmetric, no V5
        mixed = rows + [row('extra', 'HULL', 9.0)]
        for kw in (dict(kit_symmetric=False, gen_view_overlap=False), dict(kit_symmetric=True, gen_view_overlap=False),
                   {}):
            with self.assertRaises(ValueError):
                S.pick(mixed, **kw)
        cands = [dict(cid=r['cid'], cls=r['cls'], n_params=0) for r in mixed]
        feats = {r['cid']: r for r in mixed}
        with self.assertRaises(ValueError):                                  # the feats path alike
            S.pick(cands, feats, kit_symmetric=False, gen_view_overlap=False)

    def test_variant_K_must_match_pool(self):
        """B5 round 3 (verifier's probe 3): a K = 3 pool picked with a K = 5 variant was accepted and recorded K = 5
        (mislabelled A.7 variants); now the variant's K is checked against the pool dict and the row tags."""
        tag = dict(obj='x', K=3, kit_symmetric=False, gen_view_overlap=False, flags=[])
        pool = dict(obj='x', K=3, kit_symmetric=False, gen_view_overlap=False, flags=[],
                    rows=[dict(row('a', 'SHELL', 1.0), pool=dict(tag)), dict(row('b', 'HULL', 2.0), pool=dict(tag))])
        v5 = dict(K=5, b_tie=1, prior=True)
        for inp in (pool, pool['rows']):
            with self.assertRaises(ValueError):
                S.pick(inp, variant=v5)
            self.assertEqual(S.pick(inp)['variant']['K'], 3)                 # V0 (K = 3) matches
            self.assertEqual(S.pick(inp, variant=dict(K=3, b_tie=2, prior=False))['cid'], 'a')
        tag5 = dict(tag, K=5)
        rows5 = [dict(r, pool=dict(tag5)) for r in pool['rows']]
        self.assertEqual(S.pick(rows5, variant=v5)['variant']['K'], 5)
        with self.assertRaises(ValueError):
            S.pick(rows5)                                                    # V0 is K = 3
        with self.assertRaises(ValueError):                                  # rows of a K = 3 and a K = 5 pool
            S.pick([pool['rows'][0], rows5[1]])
        self.assertEqual(pick([row('a', 'SHELL', 1.0)], variant=v5)['cid'], 'a')   # hand-made rows: no pool K

    def test_pool_flags_travel_in_row_tags(self):
        """B5 round 3 (builder's open problem 7): score_pool writes the pool flags into every row's tag, so the pick
        on the rows alone carries them too."""
        tag = dict(obj='x', K=3, kit_symmetric=False, gen_view_overlap=False,
                   flags=['gen_input_frames_missing', 'v3_no_shell_reference'])
        rows = [dict(row('a', 'SHELL', 1.0), pool=dict(tag)), dict(row('b', 'HULL', 2.0), pool=dict(tag))]
        p = S.pick(rows)
        self.assertIn('gen_input_frames_missing', p['flags']); self.assertIn('v3_no_shell_reference', p['flags'])
        pool = dict(obj='x', K=3, kit_symmetric=False, gen_view_overlap=False, flags=list(tag['flags']), rows=rows)
        self.assertEqual(sorted(S.pick(pool)['flags']), sorted(p['flags']))

    def test_unknown_flip_risk_is_neither_safe_nor_risky(self):
        """B5 round 2: amb unknown (untrusted balls, no ball-free mesh; score.amb_unknown) does not make V5 apply,
        is not removed by it, ranks last on key 2, and a pick with it is flagged flip_risk_unknown."""
        unk = dict(amb_mm=None, amb_floor_mm=None, flip_risk=None, flip_units=None, unknown=True)
        a = row('a', 'STRUCT', 1.0, units=0, risk=True)
        b = dict(row('b', 'STRUCT', 1.0), amb=dict(unk))
        p = pick([a, b])
        v5 = [t for t in p['trace'] if t['step'] == 'V5'][0]
        self.assertFalse(v5['applied']); self.assertEqual(v5['unknown'], ['b'])
        self.assertEqual(p['order'], ['a', 'b']); self.assertIn('flip_risk', p['flags'])
        b2 = dict(row('b', 'STRUCT', 0.5), amb=dict(unk))                    # b alone in the tie band
        p = pick([a, b2])
        self.assertEqual(p['cid'], 'b'); self.assertIn('flip_risk_unknown', p['flags'])
        self.assertNotIn('flip_risk', p['flags'])
        c = row('c', 'HULL', 3.0, units=2, risk=False)                       # a safe one: V5 removes a only
        p = pick([a, b, c])
        v5 = [t for t in p['trace'] if t['step'] == 'V5'][0]
        self.assertTrue(v5['applied']); self.assertEqual(v5['removed'], ['a'])
        self.assertEqual(p['cid'], 'b'); self.assertIn('flip_risk_unknown', p['flags'])
        self.assertNotIn('flip_risk_unknown', pick([a, b], kit_symmetric=True)['flags'])

    def test_se_diff_skips_undefined_replicates(self):
        a = row('a', 'SHELL', 1.0, sd=0.1, seed=1)
        b = row('b', 'STRUCT', 1.05, sd=0.1, seed=2)
        ref = pick([a, b])['tie_set']
        a2, b2 = dict(a, E_reps=a['E_reps'].copy()), dict(b, E_reps=b['E_reps'].copy())
        a2['E_reps'][:5] = np.nan; b2['E_reps'][3:8] = np.nan                # replicates with E undefined
        d = (b['E_reps'] - a['E_reps'])[8:]
        t = dict((c, s) for c, _, s in pick([a2, b2])['tie_set'])
        self.assertAlmostEqual(t['b'], round(float(np.std(d)), 6), places=6)
        self.assertEqual([c for c, _, _ in ref], sorted(t))


if __name__ == '__main__':
    if guard.mode() != 'dev':
        raise SystemExit('test_select runs in GMG_MODE=dev')
    res = unittest.main(argv=[sys.argv[0]] + sys.argv[1:], verbosity=2, exit=False)
    sys.exit(0 if res.result.wasSuccessful() else 1)
