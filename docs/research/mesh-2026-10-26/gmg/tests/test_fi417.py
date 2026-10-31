"""T-I1 additions of PREREG F-I4.17 (post hoc, board slot round 3, decision 2: low-piece body of <= 3 frame-aligned
rectangles cut into boxes; contact-budget gate part 1; new freeze).

  GMG_MODE=dev python docs/research/mesh-2026-10-26/gmg/tests/test_fi417.py               (venv python, everything)
  GMG_MODE=dev python .../test_fi417.py W10                                              (one class)
  GMG_MODE=dev python .../test_fi417.py W10.test_k5_t8_s2_physics                        (one test)

F-I4.17.6 step 2 (code checks; a failure is a code defect):
  CodeChecks   (ii) the fit on exact rasters: an exact I-mask gives IoU 1.0 and its theta, a rectangle mask one
               rectangle, a T-mask two; (iii) the box partition tiles exactly: an I with a waist slot 5 boxes (default
               3), a rectangle with a slot 3 boxes (default 1); (iv) the part-1 counter on one box at rest on a plane:
               nefc = 4 ncon at every step (pyramidal, condim 3). (i) the REV 16 byte identity is
               build/I/fi417_identity.py (two processes: the 3b7e6d0 code and this code, both at REV 16).
F-I4.17.3 (b) (freeze inputs; fixtures of F-I4.16.2 unchanged, tests/test_fi416.w10_episode):
  W10          k = 1..9 under REV 17: both CARVE through the waiver route (T1) with the low-piece body on both (IoU >=
               0.90; a polygon fallback misses), keep-out <= 0.3 cm3 per hull, |w - (t + 2)| <= 1.0 mm on both; part-1
               counts reported for every cell (synthetic table: normal -d, 1 mm beyond the lowest vertex along d);
               k = 5 (t 8, sigma_e 2) also P2-P7 on 16 copies (F-I4.16.3 (b) thresholds) and part 1 PASS.
Report only (not freeze inputs; the assertions state the predictions):
  W10Report    w10p (P130: A's IoU < 0.90 -> polygon fallback), w10n (P131).
  ReRuns       w7, w8, w8b of test_fi415.WaiverR2 under REV 17 (P132: IoU >= 0.90 on every board and both CARVE).
  W1           w1 at t = 10 mm under REV 17 (P134: one rectangle, IoU >= 0.95, 3 slotted and 1 default box, CARVE).
  GateValidity F-I4.17.1 gate validity check (P125): part 1 on the round-2 ep24 r0 pieces (polygon prisms 57 / 77,
               default 50 / 71; committed in build/I/results/slot2-ep24/fi4o/r0) in the ep24 scenes S1 = f246 / S2 =
               f218 (the clean ep24 bundle b4ext4-b61e8aa from the scratch store; skipped if absent): the gate should
               FAIL the round-2 prisms against their one-box control; the control as 'delivered' must PASS (ratio 1).
Results: <scratchpad>/gmg/interlock/test_fi417.json (env FI417_OUT overrides).
"""
import glob
import json
import os
import sys
import time
import unittest

os.environ.setdefault('GMG_MODE', 'dev')
HERE = os.path.dirname(os.path.abspath(__file__))
GMG = os.path.dirname(HERE)
MR = os.path.dirname(GMG)
for p_ in (MR, HERE):
    if p_ not in sys.path:
        sys.path.insert(0, p_)
from gmg import guard  # noqa: E402
import numpy as np  # noqa: E402
import trimesh  # noqa: E402

from gmg import interlock as IL, platebody as PB, contactgate_fi4 as CG  # noqa: E402
import test_interlock as TI  # noqa: E402
import test_fi415 as T15  # noqa: E402
import test_fi416 as T16  # noqa: E402

OUT = os.environ.get('FI417_OUT', os.path.join(guard.SCRATCH_DEFAULT, 'gmg', 'interlock', 'test_fi417.json'))
RES = {}
REV17 = 17
CAP = 82
EP24_BUNDLE = os.path.join(guard.SCRATCH_DEFAULT, 'gmg', 'runs', '20261031-b4ext4-b61e8aa', 'bundle', 'public', 'ep24')
R2_R0 = os.path.join(GMG, 'build', 'I', 'results', 'slot2-ep24', 'fi4o', 'r0')
_summary16 = T16.summary16


def summary17(recs, sides, b=None):
    """test_fi416.summary16 plus the F-I4.17 fields (body kind, low-piece fit, box counts, FREE shares)."""
    s = _summary16(recs, sides, b)
    for r in recs:
        x = r['target']
        if x not in s:
            continue
        w = r.get('waiver_fi4') or {}
        bd = (w.get('body') or {}).get(x) or {}
        lp = bd.get('low_piece') or {}
        s[x].update(body_kind=bd.get('body_kind'), iou=lp.get('iou'), n_rect=lp.get('n_rect'),
                    low_piece={k: v for k, v in lp.items() if k not in ('rule',)} or None,
                    free_share_reports=bd.get('free_share_reports'), f_i416_polygon=bd.get('f_i416_polygon'))
    return s


T15.summary15 = summary17                  # WaiverR2 (ReRuns) records the F-I4.17 fields too


def freeze_b17(s, t_mm):
    """F-I4.17.3 (b), geometric part, one cell: both CARVE via the waiver route (T1) with the low-piece body (IoU >=
    0.90), boxes within the cap and tiling exactly, keep-out <= 0.3 cm3 per hull, |w - (t + 2)| <= 1.0 mm."""
    m = []
    for o in ('A', 'B'):
        r = s.get(o)
        if r is None:
            m.append(f'no component on {o}')
            continue
        if r['decision'] != 'CARVE' or r['tier'] != 'T1' or r['submitted'] or 'owner_waiver_fi4' not in r['flags'] \
                or r.get('w_mm') is None:
            m.append(f'{o} not carved by the waiver route: {r["decision"]} {r["tier"]} gate {r.get("gate_fail")} '
                     f'body {r.get("body_why")}')
            continue
        if r.get('body_kind') != 'low_piece':
            m.append(f'{o} body {r.get("body_kind")} (IoU {r.get("iou")})')
        for kk in ('default_pieces', 'slotted_pieces'):
            p = r.get(kk) or {}
            if not p or p.get('over_cap') or p.get('n', 999) > CAP or not p.get('tiling_ok'):
                m.append(f'{o} {kk} {p}')
        if 'keepout' not in r or r['keepout']['max_cm3'] > 0.3:
            m.append(f'{o} keep-out {r.get("keepout")}')
        if abs(r['w_mm'] - (t_mm + 2.0)) > 1.0:
            m.append(f'{o} width {r["w_mm"]} vs t + 2 = {t_mm + 2.0}')
    return m


def part1(b, recs, replay=False, extra_sets=None):
    W = {r['target']: r for r in recs if r.get('_waiver')}
    if set(W) != {'A', 'B'}:
        return None
    run = W['A']['_comp'].run
    g = CG.gate_pair(b, 'A', 'B', run, W, extra_sets=extra_sets, replay=replay)
    return {k: v for k, v in g.items() if k != 'per_set'}


def boxes(s):
    return {o: dict(slotted=((s.get(o) or {}).get('slotted_pieces') or {}).get('n'),
                    default=((s.get(o) or {}).get('default_pieces') or {}).get('n')) for o in 'AB'}


def run_cell17(key, k, t_mm, sig_e, physics=False, gate=True, **kw):
    t0 = time.time()
    PB.REV = REV17
    b, fix = T16.w10_episode(k, t_mm, sig_e, **kw)
    cand = dict(A=T16.iplate10(t_mm * 1e-3), B=T16.iplate10(t_mm * 1e-3))
    recs, sides = TI.run_pair(b, cand, waiver=True)
    s = summary17(recs, sides, b)
    out = dict(fixture=fix, summary=s, misses_b=freeze_b17(s, t_mm), boxes=boxes(s),
               iou={o: (s.get(o) or {}).get('iou') for o in 'AB'},
               body_kind={o: (s.get(o) or {}).get('body_kind') for o in 'AB'}, fi4_rev=PB.REV)
    carved = all((s.get(o) or {}).get('w_mm') is not None for o in 'AB')
    if gate and carved:
        tg = time.time()
        out['part1'] = part1(b, recs, replay=physics)
        out['part1_sec'] = round(time.time() - tg, 1)
    if physics and carved:
        out['physics'] = T16._physics(b, recs, key)
    out['sec'] = round(time.time() - t0, 1)
    RES[key] = out
    return out


class CodeChecks(unittest.TestCase):
    """F-I4.17.6 step 2 (ii)-(iv)."""

    def test_fit_exact_rasters(self):
        out = {}
        M = np.zeros((115, 69), bool)
        M[:, 3:66] = True
        M[:10, :] = True
        M[-10:, :] = True
        f = PB.low_piece_fit(M)
        out['I'] = f
        self.assertEqual(f['theta'], (3, 66, 10, 0, 69, 10, 0, 69))
        self.assertAlmostEqual(f['iou'], 1.0, places=12)
        M = np.zeros((50, 30), bool)
        M[:, 5:25] = True
        f = PB.low_piece_fit(M)
        out['rect'] = f
        self.assertEqual(f['n_rect'], 1)
        self.assertAlmostEqual(f['iou'], 1.0, places=12)
        M = np.zeros((60, 40), bool)
        M[:, 10:30] = True
        M[:15, :] = True
        f = PB.low_piece_fit(M)
        out['T'] = f
        self.assertEqual(f['n_rect'], 2)
        self.assertAlmostEqual(f['iou'], 1.0, places=12)
        RES['code_fit'] = out

    def test_partition_tiles(self):
        R = np.array([[-115, -68.5], [-95, -68.5], [-95, -62.5], [95, -62.5], [95, -68.5], [115, -68.5], [115, 68.5],
                      [95, 68.5], [95, 62.5], [-95, 62.5], [-95, 68.5], [-115, 68.5]], float)
        bd, idf = PB.box_partition(R)
        sl = PB.slotted_polygon(R, (-4.7, 4.7, -1.0, 70.0))
        bs, isl = PB.box_partition(sl['rings'][0])
        Q = np.array([[-100, -50], [100, -50], [100, 50], [-100, 50]], float)
        qd, iqd = PB.box_partition(Q)
        qs, iqs = PB.box_partition(PB.slotted_polygon(Q, (-4.0, 4.0, 0.0, 60.0))['rings'][0])
        RES['code_partition'] = dict(I_default=idf, I_slot=isl, rect_default=iqd, rect_slot=iqs)
        self.assertEqual((len(bd), len(bs), len(qd), len(qs)), (3, 5, 1, 3))
        for inf in (idf, isl, iqd, iqs):
            self.assertTrue(inf['tiling_ok'], inf)
            self.assertLessEqual(inf['tiling_diff_mm2'], 1e-6, inf)

    def test_counter_box_on_plane(self):
        import mujoco
        from gmg import simpieces as SP
        s = np.array([[x, y, z] for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)], float)
        big, small = [s * np.array([0.1, 0.06, 0.004])], [s * np.array([0.01, 0.01, 0.004])]
        opt = CG.options()
        Th = np.eye(4)
        Th[2, 3] = 0.004
        Tg = np.eye(4)
        Tg[2, 3] = 0.5
        m = mujoco.MjModel.from_xml_string(CG.count_xml(big, small, Th, Tg, np.array([0, 0, 1.0]), 0.0,
                                                        SP.props(big, 0.3), SP.props(small, 0.3), opt))
        d = mujoco.MjData(m)
        rows = []
        for _ in range(100):
            mujoco.mj_step(m, d)
            rows.append((int(d.ncon), int(d.nefc)))
        RES['code_counter'] = dict(steps=len(rows), last=rows[-1], all_4x=all(e == 4 * c for c, e in rows),
                                   options=opt)
        self.assertTrue(all(e == 4 * c for c, e in rows), rows[:5])
        self.assertGreater(rows[-1][0], 0)


class W10(unittest.TestCase):
    """F-I4.17.3 (b): the nine full-outline cells under REV 17 (freeze inputs)."""

    def _cell(self, k, physics=False):
        t_mm, sg = T16.CELLS[k]
        out = run_cell17(f'w10_k{k}', k, t_mm, sg, physics=physics)
        m = list(out['misses_b'])
        if physics:
            ph = out.get('physics')
            if ph is None or not ph['pass_P2_P7']:
                m.append(f'P2-P7 {None if ph is None else ph["acceptance"]}')
            p1 = out.get('part1')
            if p1 is None or not p1['pass_']:
                m.append(f'part 1 {None if p1 is None else CG.summary_line(p1)}')
        self.assertEqual(m, [], m)

    def test_k1_t6_s1(self):
        self._cell(1)

    def test_k2_t6_s2(self):
        self._cell(2)

    def test_k3_t6_s3(self):
        self._cell(3)

    def test_k4_t8_s1(self):
        self._cell(4)

    def test_k5_t8_s2_physics(self):
        """The physics cell: geometric checks, P2-P7 on 16 copies and contact-gate part 1."""
        self._cell(5, physics=True)

    def test_k6_t8_s3(self):
        self._cell(6)

    def test_k7_t10_s1(self):
        self._cell(7)

    def test_k8_t10_s2(self):
        self._cell(8)

    def test_k9_t10_s3(self):
        self._cell(9)


class W10Report(unittest.TestCase):
    """Report only: w10p (P130) and w10n (P131) under REV 17."""

    def test_w10p_occluded(self):
        out = run_cell17('w10p', 10, 8, 2.0, occlude=True)
        s = out['summary']
        a = s.get('A') or {}
        out['P130'] = dict(iou_A=a.get('iou'), body_A=a.get('body_kind'),
                           holds=bool(a.get('iou') is not None and a['iou'] < 0.90 and
                                      a.get('body_kind') == 'f_i416_polygon_fallback'))
        self.assertTrue(out['P130']['holds'], out['P130'])

    def test_w10n_isotropic3(self):
        out = run_cell17('w10n', 11, 8, 3.0, sig_n=3.0, declared=3.0)
        s = out['summary']
        pl = {o: (s.get(o) or {}).get('plate_t_mm') for o in 'AB'}
        out['P131'] = dict(plate_t_mm=pl, iou=out['iou'], both_carve=not out['misses_b'],
                           holds=bool(not out['misses_b'] and all(v is not None and abs(v - 8.0) <= 1.0
                                                                  for v in pl.values())))
        self.assertTrue(out['P131']['holds'], out['P131'])


class ReRuns(T15.WaiverR2):
    """Report only: w7, w8, w8b of F-I4.15.7 under REV 17 (P132); fixtures and seeds unchanged."""
    REV = 17

    def _w8(self, sigma, key, tilt=0.0, physics=True):
        out, m = super()._w8(sigma, key, tilt=tilt, physics=physics)
        s = out['summary']
        out['P132'] = dict(iou={o: (s.get(o) or {}).get('iou') for o in 'AB'},
                           body_kind={o: (s.get(o) or {}).get('body_kind') for o in 'AB'}, boxes=boxes(s))
        RES['rerun_' + key] = out
        return out, m

    def test_w7_one_face(self):
        try:
            super().test_w7_one_face()
        finally:
            RES['rerun_w7'] = dict(summary=TI.RESULTS.get('w7_r2', {}).get(10),
                                   misses=TI.RESULTS.get('w7_r2_misses'), t_source=TI.RESULTS.get('w7_sources'))


_KEEP = ('test_w7_one_face', 'test_w8_i_cross', 'test_w8b_i_cross_sigma3')
for _n in [n for n in dir(T15.WaiverR2) if n.startswith('test_') and n not in _KEEP]:
    setattr(ReRuns, _n, unittest.skip('F-I4.17: not a re-run')(lambda self: None))


class W1(unittest.TestCase):
    """Report only: P134 (w1 at t = 10 mm under REV 17)."""

    def test_w1_t10(self):
        rev0 = PB.REV
        PB.REV = REV17
        try:
            b, cand, recs, sides = TI._waiver_case(10)
            s = summary17(recs, sides, b)
        finally:
            PB.REV = rev0
        m, wm = T15.w_checks(s, 10)
        bx = boxes(s)
        out = dict(summary=s, misses=m, width_misses=wm, boxes=bx, iou={o: (s.get(o) or {}).get('iou') for o in 'AB'},
                   n_rect={o: (s.get(o) or {}).get('n_rect') for o in 'AB'})
        out['P134'] = bool(not m and all((s.get(o) or {}).get('n_rect') == 1 and (s.get(o) or {}).get('iou', 0) >= 0.95
                                         and bx[o]['slotted'] == 3 and bx[o]['default'] == 1 for o in 'AB'))
        RES['w1_t10_rev17'] = out
        self.assertTrue(out['P134'], out)


def _load_r0(r0, obj, sub=''):
    fs = sorted(glob.glob(os.path.join(r0, sub, obj, 'piece_*.obj')))
    return [np.asarray(trimesh.load(f, force='mesh').vertices, np.float64) for f in fs]


class GateValidity(unittest.TestCase):
    """F-I4.17.1 gate validity check (report; P125) on the round-2 ep24 r0 pieces in the ep24 scenes."""

    def test_round2_r0(self):
        if not os.path.isdir(EP24_BUNDLE):
            self.skipTest(f'ep24 bundle not here: {EP24_BUNDLE}')
        man = json.load(open(os.path.join(R2_R0, 'manifest.json')))
        o, p = 'wooden_piece_1', 'wooden_piece_2'
        ph = json.load(open(os.path.join(os.path.dirname(R2_R0), f'physics_{o}_{p}.json')))
        dec = json.load(open(os.path.join(os.path.dirname(R2_R0), 'decisions.json')))
        f1 = int(ph['P2']['frame'])
        f2 = None
        for r in dec:
            if r.get('target') == o and r.get('decision') == 'CARVE':
                f2 = int((r.get('run') or {}).get('assembled', [None])[0])
        b = IL.load_bundle_any(EP24_BUNDLE)
        scenes = CG.scenes_frames(b, o, p, {'S1': f1, 'S2': f2})
        bodies = {x: man['owner_waiver']['objects'][x]['body']['box'] for x in (o, p)}
        sets = {'r2_prisms': (_load_r0(R2_R0, o), _load_r0(R2_R0, p)),
                'r2_default': (_load_r0(R2_R0, o, '_default'), _load_r0(R2_R0, p, '_default')),
                'control': (CG.control_hulls(bodies[o]), CG.control_hulls(bodies[p]))}
        t0 = time.time()
        g = CG.gate(scenes, sets, delivered='r2_prisms', control='control', lower=True)
        g2 = CG.gate(scenes, {'control_as_delivered': sets['control'], 'control': sets['control']},
                     delivered='control_as_delivered', control='control')
        out = dict(frames=dict(S1=f1, S2=f2), pieces={k: [len(h), len(q)] for k, (h, q) in sets.items()},
                   gate_r2={k: v for k, v in g.items() if k != 'per_set'}, per_copy_r2=g['per_set'],
                   control_vs_control=dict(pass_=g2['pass_'], ratio=g2['ratio_delivered_to_control'],
                                           summary=g2['summary']),
                   P125_flagged=bool(not g['pass_']), sec=round(time.time() - t0, 1),
                   r0_manifest_sha='see build/I/results/slot2-ep24/fi4o/r0/manifest.json')
        RES['gate_validity'] = out
        self.assertTrue(g2['pass_'], g2['summary'])
        self.assertFalse(g['pass_'], CG.summary_line(g))


def tearDownModule():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    out = dict(fi4_rev=REV17, fi417=RES, fi416_res=T16.RES, fi415_res=T15.RES, test_interlock_results=TI.RESULTS)
    with open(OUT, 'w') as f:
        json.dump(out, f, indent=1, default=IL._jdefault)
    print('results ->', OUT)


if __name__ == '__main__':
    unittest.main(verbosity=2)
