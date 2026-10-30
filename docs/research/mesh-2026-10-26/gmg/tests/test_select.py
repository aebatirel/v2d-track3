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
        p = S.pick(rows)
        self.assertEqual(p['cid'], 'e')
        self.assertEqual(p['trace'][0]['removed'], {'a': ['V1'], 'b': ['V2'], 'c': ['V3'], 'd': ['V4']})

    def test_v3_counts_only_when_applied(self):
        rows = [row('a', 'STRUCT', 1.0, v3=True, v3_applied=False), row('b', 'SHELL', 1.0)]
        p = S.pick(rows)
        self.assertEqual(p['cid'], 'a')
        self.assertIn('V3 (tau not set)', p['trace'][0]['not_applied'])

    def test_v5_removes_flip_risk_only_if_a_safe_one_exists(self):
        rows = [row('a', 'STRUCT', 1.0, risk=True, units=0), row('b', 'SHELL', 1.0, units=2)]
        p = S.pick(rows)
        self.assertEqual(p['cid'], 'b')
        v5 = [t for t in p['trace'] if t['step'] == 'V5'][0]
        self.assertTrue(v5['applied']); self.assertEqual(v5['removed'], ['a'])
        self.assertEqual(p['trace'][0]['removed'], {})                  # the V1-V4 trace does not list V5
        self.assertNotIn('flip_risk', p['flags'])
        rows = [row('a', 'STRUCT', 1.0, risk=True, units=0), row('b', 'SHELL', 1.0, risk=True, units=-1)]
        p = S.pick(rows)
        self.assertEqual(p['cid'], 'a')                         # V5 not applied: all feasible are flip-risk
        self.assertIn('flip_risk', p['flags'])
        v5 = [t for t in p['trace'] if t['step'] == 'V5'][0]
        self.assertFalse(v5['applied'])

    def test_v5_safe_candidate_vetoed_elsewhere_does_not_count(self):
        rows = [row('a', 'STRUCT', 1.0, risk=True, units=0), row('b', 'SHELL', 1.0, units=2, v2=True)]
        p = S.pick(rows)
        self.assertEqual(p['cid'], 'a')                         # b is not feasible, so V5 cannot apply
        self.assertIn('flip_risk', p['flags'])

    def test_v5_and_flip_key_skipped_for_kit_symmetric(self):
        rows = [row('a', 'STRUCT', 1.0, risk=True, units=0, n_params=5), row('b', 'STRUCT', 1.0, units=4, n_params=9)]
        p = S.pick(rows, kit_symmetric=True)
        self.assertEqual(p['cid'], 'a')                         # flip key skipped: fewer parameters decides
        self.assertNotIn('flip_risk', p['flags'])
        p = S.pick(rows, kit_symmetric=False)
        self.assertEqual(p['cid'], 'b')                         # V5 removes a


class TieBandTests(unittest.TestCase):
    def test_band_uses_paired_se_diff(self):
        base = np.random.default_rng(9).normal(0, 0.5, N_REPS)          # shared (paired) variation: cancels
        best = row('best', 'SHELL', 1.00, base=base, sd=0.0)
        near = row('near', 'STRUCT', 1.05, base=base, sd=0.10, seed=1)   # dE 0.05 <= 1 x 0.10
        far = row('far', 'STRUCT', 1.30, base=base, sd=0.10, seed=2)     # dE 0.30 > 1 x and > 2 x 0.10
        p = S.pick([best, near, far])
        self.assertEqual(p['best'], 'best')
        self.assertEqual(sorted(c for c, _, _ in p['tie_set']), ['best', 'near'])
        self.assertEqual(p['cid'], 'near')                      # STRUCT before SHELL
        se = {c: s for c, _, s in p['tie_set']}
        self.assertAlmostEqual(se['near'], 0.10, places=6)      # the shared noise cancels in the paired difference
        self.assertEqual(se['best'], 0.0)
        p2 = S.pick([best, near, far], variant=dict(K=3, b_tie=2, prior=True))
        self.assertEqual(sorted(c for c, _, _ in p2['tie_set']), ['best', 'near'])
        far2 = row('far', 'STRUCT', 1.15, base=base, sd=0.10, seed=2)    # 0.15: out at 1 SE, in at 2 SE
        self.assertNotIn('far', [c for c, _, _ in S.pick([best, near, far2])['tie_set']])
        self.assertIn('far', [c for c, _, _ in S.pick([best, near, far2],
                                                      variant=dict(K=3, b_tie=2, prior=True))['tie_set']])

    def test_variant_must_be_in_menu(self):
        with self.assertRaises(ValueError):
            S.pick([row('a', 'SHELL', 1.0)], variant=dict(K=4, b_tie=1, prior=True))
        self.assertEqual(len(S.MENU), 8)
        self.assertIn(S.VARIANT_V0, [dict(m) for m in S.MENU])

    def test_missing_reps_raise(self):
        r = row('a', 'SHELL', 1.0); r2 = row('b', 'SHELL', 1.1)
        del r2['E_reps']
        with self.assertRaises(ValueError):
            S.pick([r, r2])


class OrderTests(unittest.TestCase):
    """PREREG A.5 step 3 keys, each deciding when all earlier keys are equal; every row is in the tie set (equal E,
    zero SE) unless stated."""

    def test_class_order(self):
        rows = [row(c.lower(), c, 1.0) for c in ('HULL', 'SHELL', 'GEN', 'FUSE', 'STRUCT')]
        self.assertEqual(S.pick(rows)['order'], ['struct', 'fuse', 'gen', 'shell', 'hull'])
        self.assertEqual(S.pick(rows, gen_view_overlap=True)['order'], ['struct', 'shell', 'fuse', 'gen', 'hull'])
        self.assertIn('gen_view_overlap', S.pick(rows, gen_view_overlap=True)['flags'])

    def test_flip_units_then_markers_then_params_then_E_then_cid(self):
        rows = [row('p_u1', 'SHELL', 1.0, units=1),
                row('p_u3_m0_n2', 'SHELL', 1.0, units=3, markers=0, n_params=2),
                row('p_u3_m2_n9', 'SHELL', 1.0, units=3, markers=2, n_params=9),
                row('p_u3_m2_n4_E2', 'SHELL', 1.0 + 1e-9, sd=0.01, seed=7, units=3, markers=2, n_params=4),
                row('p_u3_m2_n4_b', 'SHELL', 1.0, units=3, markers=2, n_params=4),
                row('p_u3_m2_n4_a', 'SHELL', 1.0, units=3, markers=2, n_params=4)]
        p = S.pick(rows)
        self.assertEqual(p['order'], ['p_u3_m2_n4_a', 'p_u3_m2_n4_b', 'p_u3_m2_n4_E2', 'p_u3_m2_n9',
                                      'p_u3_m0_n2', 'p_u1'])
        p = S.pick(rows, variant=dict(K=3, b_tie=1, prior=False))          # parameter prior off: E, then cid
        self.assertEqual(p['order'], ['p_u3_m2_n4_a', 'p_u3_m2_n4_b', 'p_u3_m2_n9', 'p_u3_m2_n4_E2',
                                      'p_u3_m0_n2', 'p_u1'])

    def test_infinite_flip_units_rank_first(self):
        rows = [row('a', 'SHELL', 1.0, units=5), row('b', 'SHELL', 1.0, units=10 ** 6)]
        self.assertEqual(S.pick(rows)['cid'], 'b')

    def test_unknown_amb_ranks_last_within_class(self):
        rows = [row('a', 'SHELL', 1.0, units=None), row('b', 'SHELL', 1.0, units=-1, risk=True)]
        p = S.pick(rows)
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
        ref = S.pick(rows)
        self.assertEqual(ref['order'], ['m_struct', 'a_struct', 'z_struct', 'gen', 'shell', 'hull'])
        self.assertEqual(ref['best'], 'hull')                   # E 1.00 three times: min (E, cid)
        n = 0
        for perm in itertools.permutations(rows):
            p = S.pick(list(perm))
            self.assertEqual((p['cid'], p['order'], p['best'], p['tie_set']),
                             (ref['cid'], ref['order'], ref['best'], ref['tie_set']))
            n += 1
        self.assertEqual(n, 720)
        twin = [row('b', 'SHELL', 1.0), row('a', 'SHELL', 1.0)]          # equal E: best by cid
        self.assertEqual(S.pick(twin)['best'], 'a')
        self.assertEqual(S.pick(twin[::-1])['best'], 'a')

    def test_undefined_E_ranked_last(self):
        rows = [row('a', 'SHELL', float('nan')), row('b', 'HULL', 3.0)]
        p = S.pick(rows)
        self.assertEqual(p['cid'], 'b'); self.assertIn('E_undefined', p['flags'])


class LadderTests(unittest.TestCase):
    def _vetoed(self):
        return [row('s', 'SHELL', 1.0, v2=True), row('h', 'HULL', 5.0, v2=True), row('g', 'GEN', 2.0, v3=True),
                row('g2', 'GEN', 1.5, v3=True, v1=True)]

    def test_abstain_hull(self):
        p = S.pick(self._vetoed())
        self.assertEqual((p['cid'], p['fallback']), ('h', 'ABSTAIN_HULL'))
        self.assertIn('no_feasible', p['flags'])

    def test_hull_must_be_watertight(self):
        rows = [row('s', 'SHELL', 1.0, v2=True), row('h', 'HULL', 5.0, v1=True)]
        p = S.pick(rows)
        self.assertEqual((p['cid'], p['fallback']), (None, 'PRIOR_PUBLIC'))
        self.assertIn('needs_owner_O2', p['flags'])

    def test_low_coverage_prior_gen_or_public(self):
        p = S.pick(self._vetoed(), status=dict(low_coverage=True, gpu_ran=True))
        self.assertEqual((p['cid'], p['fallback']), ('g', 'PRIOR_GEN'))   # g2 is not watertight after decode
        p = S.pick(self._vetoed(), status=dict(low_coverage=True, gpu_ran=False))
        self.assertEqual((p['cid'], p['fallback']), (None, 'PRIOR_PUBLIC'))

    def test_low_coverage_with_feasible_is_normal(self):
        rows = [row('s', 'SHELL', 1.0), row('h', 'HULL', 5.0)]
        p = S.pick(rows, status=dict(low_coverage=True))
        self.assertEqual((p['cid'], p['fallback']), ('s', None))
        self.assertIn('low_coverage', p['flags'])

    def test_track_fail_skips_normal_pick(self):
        rows = [row('s', 'SHELL', 1.0), row('h', 'HULL', 5.0), row('g', 'GEN', 3.0)]
        p = S.pick(rows, status=dict(track_fail=True, gpu_ran=True))
        self.assertEqual((p['cid'], p['fallback']), ('g', 'PRIOR_GEN'))
        p = S.pick(rows, status=dict(identity_swap=True))
        self.assertEqual((p['cid'], p['fallback']), (None, 'PRIOR_PUBLIC'))
        self.assertIn('identity_swap', p['flags'])


class InputTests(unittest.TestCase):
    def test_cands_and_feats(self):
        from gmg.producers import Candidate
        cands = [Candidate(cid='a', producer='P-X', cls='SHELL', mesh=None, params={}, n_params=0),
                 Candidate(cid='b', producer='P-Y', cls='STRUCT', mesh=None, params={}, n_params=3)]
        feats = {'a': row('a', 'SHELL', 1.0), 'b': row('b', 'HULL', 1.0)}      # the candidate's class wins
        p = S.pick(cands, feats)
        self.assertEqual(p['cid'], 'b')

    def test_bad_class_and_duplicates(self):
        with self.assertRaises(ValueError):
            S.pick([row('a', 'LIBRARY', 1.0)])
        with self.assertRaises(ValueError):
            S.pick([row('a', 'SHELL', 1.0), row('a', 'HULL', 2.0)])


if __name__ == '__main__':
    if guard.mode() != 'dev':
        raise SystemExit('test_select runs in GMG_MODE=dev')
    res = unittest.main(argv=[sys.argv[0]] + sys.argv[1:], verbosity=2, exit=False)
    sys.exit(0 if res.result.wasSuccessful() else 1)
