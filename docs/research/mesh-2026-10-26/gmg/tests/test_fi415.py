"""T-I1 additions of PREREG F-I4.15 (post hoc, board slot round 2: outline-polygon plate body, prisms, t from all points).

  GMG_MODE=dev python docs/research/mesh-2026-10-26/gmg/tests/test_fi415.py                (venv python)
  GMG_MODE=dev python .../test_fi415.py WaiverR2.test_w8_i_cross                         (one test)

F-I4.15.7:
  w1-w7 re-run with the F-I4.15 code (class WaiverR2 = test_interlock.Waiver with w1's "three box pieces" read as "prisms
      that tile the slotted polygon exactly (area difference <= 1 mm2), within the cap"; every other threshold as
      before; the t = 6 mm width miss and t = 25 mm out of scope stay recorded cases, reported either way);
  w6c the step-2 estimator on ALL points (replaces w6b): t = 6, 10, 18 mm x sigma 1, 3 mm, |t - true| <= 1.0 mm;
  w8  I-shaped cross: two plates 230 mm long, 125 mm wide at the waist, 136 mm over 20 mm at each end, t = 7 mm,
      two-sided cameras, sigma 1 mm, slot in the waist at mid-length, waiver on: both CARVE; end - waist within 3 mm of
      11 mm on both polygons; D from the waist edge and |D_A + D_B - W_x| <= 10 mm; w within 1 mm of t + 2 mm; centre
      within 2 mm; prisms tile exactly within the cap; keep-out 0.0 cm3; FREE share of the polygon body below the
      rectangle body's; P3 (16 copies) <= 0.5 cm, <= 5 deg, overlap < 1.0 cm3;
  w8b w8 at sigma 3 mm (the 9 mm inlier band exceeds t);
  w9  w8 with the partner turned 2.5 deg about the host's a_T at the assembled frames (ramped in over the last 10
      insertion frames: fixture choice, stated before the first run); reported (P56: P3 passes).
Results: <scratchpad>/gmg/interlock/test_fi415.json (env FI415_OUT overrides). Nothing is read from disk but code.
"""
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
from scipy.spatial.transform import Rotation as Rot  # noqa: E402

from gmg import interlock as IL, platebody as PB, simphys as PH  # noqa: E402
import test_interlock as TI  # noqa: E402

OUT = os.environ.get('FI415_OUT', os.path.join(guard.SCRATCH_DEFAULT, 'gmg', 'interlock', 'test_fi415.json'))
RES = {}
L_I, W_WAIST, W_END, END_LEN = 0.230, 0.125, 0.136, 0.020          # F-I4.15.7 w8 (ep24 shape in round numbers)


def iplate(t, slot=None, w_slot=None):
    """I-shaped plate along x (230 mm), y (125 mm waist, 136 mm over 20 mm at each end), z (t); slot 'top' (y > 0) or
    'bottom' (y < 0) in the waist at x = 0, width w_slot (default t), from the waist edge to the centre line."""
    parts = [trimesh.creation.box(extents=[L_I, W_WAIST, t])]
    for sx in (-1, 1):
        e = trimesh.creation.box(extents=[END_LEN, W_END, t])
        e.apply_translation([sx * (L_I - END_LEN) / 2, 0, 0])
        parts.append(e)
    m = trimesh.boolean.union(parts, engine='manifold')
    if slot is None:
        return m
    w = w_slot or t
    cut = trimesh.creation.box(extents=[w, W_WAIST / 2 + 0.01, t + 0.02])
    cut.apply_translation([0, (W_WAIST / 4 + 0.005) * (1 if slot == 'top' else -1), 0])
    return trimesh.boolean.difference([m, cut], engine='manifold')


def i_episode(t, sigma=1.0, tilt_deg=0.0, seed=0):
    """TI.cross_episode with I-shaped evidence for both plates (slot-less, bridged), two-sided cameras; object-episode
    sigma set to SIGMA (mm; the synthetic points keep their 1 mm noise, as w6). tilt_deg: B turned about the world z
    (= A's a_T) through the crossing at the assembled frames, ramped linearly over the last 10 insertion frames."""
    b, world_B = TI.cross_episode(t, two_sided=True, mesh_b=iplate(t), seed=seed)
    rng = np.random.default_rng(seed + 101)
    T = int(b.meta['T'])
    b._obs['A'] = TI.evidence_obs(iplate(t), rng, T, two_sided=True)
    b.meta['sigma_mm'] = dict(A=sigma, B=sigma)
    if tilt_deg:
        pre, n_ins = 10, 60
        for f in range(pre, T):
            lam = min(1.0, max(0.0, (f - (pre + n_ins - 10)) / 10.0))
            if lam <= 0:
                continue
            Rz = np.eye(4)
            Rz[:3, :3] = Rot.from_euler('z', lam * tilt_deg, degrees=True).as_matrix()
            wb = Rz @ world_B[f]
            b.poses['cam_T_B'][f] = (b.poses['cam_T_A'][f].astype(np.float64) @ wb).astype(np.float32)
    return b


def keepout(b, x, y, sides, r):
    from gmg.tools.interlock_dev import partner_occ_lin
    fr = [f for rr in sides[x].runs for f in rr.build]
    occ = partner_occ_lin(b, x, y, sides[x].ev, fr, max(c.nmin for c in sides[x].comps))
    g = PB.keepout_gate(sides[x].ev, r['_waiver']['body'], r['_waiver']['slot'], r['_waiver']['slotted'], occ)
    return g['report']['slotted_plate']


def summary15(recs, sides, b=None):
    """TI._waiver_summary plus the F-I4.15 body, slot and piece fields (and keep-out when B is given)."""
    s = TI._waiver_summary(recs, sides)
    for r in recs:
        x = r['target']
        if x not in s:
            continue
        w = r.get('waiver_fi4') or {}
        bd = (w.get('body') or {}).get(x) or {}
        sl = (w.get('slot') or {}).get(x) or {}
        pl = (w.get('plate') or {}).get(x) or {}
        s[x].update(fi4_rev=w.get('fi4_rev'), t_down_mm=pl.get('t_down_mm'), t_all_mm=(pl.get('t_all') or {}).get('t_mm'),
                    polygon={k: v for k, v in (bd.get('polygon') or {}).items() if k != 'poly_mm'},
                    widths_mm=bd.get('widths_mm'), free_share=bd.get('free_share'),
                    default_pieces=bd.get('default_pieces'), slotted_pieces=bd.get('slotted_pieces'),
                    D_rect_mm=sl.get('D_rect_mm'), u_e_poly_mm=sl.get('u_e_poly_mm'), u_rect_mm=sl.get('u_rect_mm'),
                    entry_edge_shift_mm=sl.get('entry_edge_shift_mm'), body_why=bd.get('why'))
        if b is not None and r.get('_waiver'):
            y = 'B' if x == 'A' else 'A'
            s[x]['keepout'] = keepout(b, x, y, sides, r)
    return s


def w_checks(s, t_mm, centre_tol=2.0):
    """The w1 checks under F-I4.15 (F-I4.15.7): CARVE T1 not submitted; centre within 2 mm; prisms tile exactly
    (<= 1 mm2) within the cap; keep-out <= 0.3 cm3; cross-lap within 10 mm. Width misses separately."""
    m, wm = [], []
    for o in ('A', 'B'):
        if o not in s:
            m.append(f'no component on {o}')
            continue
        r = s[o]
        if r['decision'] != 'CARVE' or r['tier'] != 'T1' or r['submitted'] or 'owner_waiver_fi4' not in r['flags']:
            m.append(f'{o} decision {r["decision"]} {r["tier"]} {r["flags"]} gate {r.get("gate_fail")} '
                     f'body {r.get("body_why")}')
            continue
        if abs(r['w_mm'] - (t_mm + 2.0)) > 1.0:
            wm.append(f'{o} width {r["w_mm"]} (t measured {r["plate_t_mm"]})')
        if abs(r['centre_mm']) > centre_tol:
            m.append(f'{o} centre {r["centre_mm"]}')
        sp = r.get('slotted_pieces') or {}
        if not (sp.get('tiling_ok') and not sp.get('over_cap') and sp.get('all_convex')):
            m.append(f'{o} pieces {sp}')
        if 'keepout' in r and r['keepout']['max_cm3'] > 0.3:
            m.append(f'{o} keep-out {r["keepout"]}')
    cl = (s.get('A') or {}).get('crosslap') or {}
    if not cl.get('ok') or abs(cl.get('diff_mm', 99)) > 10.0:
        m.append(f'crosslap {cl}')
    return m, wm


def p3_of(b, recs, copies=16, label='T-I1 F-I4.15'):
    W = {r['target']: r for r in recs if r.get('_waiver')}
    run = W['A']['_comp'].run
    ph = PH.pair_physics(b, 'A', 'B', W['A']['_waiver']['slotted'], W['B']['_waiver']['slotted'], run,
                         {x: W[x]['_waiver']['slot_cm3'] for x in 'AB'}, W['A']['_waiver']['default'],
                         W['B']['_waiver']['default'], copies, label)
    ph.pop('overlap_series', None)
    acc = PB.acceptance(ph, {}, {x: len(W[x]['_waiver']['slotted']) for x in 'AB'})
    return ph, acc


class WaiverR2(TI.Waiver):
    """F-I4.15.7: w1-w7 re-run with the F-I4.15 code (inherits test_interlock.Waiver: w2, w3, w4 unchanged; w6 and w7
    use the overridden _w1). Results land in test_interlock.RESULTS and are copied into this module's output."""

    def _w1(self, thicknesses, prep=None, key='w1'):
        res, miss, wmiss = {}, {}, {}
        for t_mm in thicknesses:
            b, cand, recs, sides = TI._waiver_case(t_mm, prep=prep)
            s = summary15(recs, sides, b)
            res[t_mm] = s
            TI.RESULTS.setdefault(key + '_r2', {})[t_mm] = s
            if t_mm == 25 and any(not s[o].get('in_scope') for o in s):
                if any(s[o]['old'] is not None for o in s):
                    miss[t_mm] = 'out of scope but a waiver decision recorded'
                continue
            m, wm = w_checks(s, t_mm)
            if m:
                miss[t_mm] = m
            if wm:
                wmiss[t_mm] = wm
        TI.RESULTS[f'{key}_r2_misses'] = dict(other=miss, width=wmiss)
        return res, miss, wmiss

    def test_w1_t6_width_known_miss(self):
        """F-I4.13 known miss (t = 6 mm width), a recorded case under F-I4.15 (t now from all points): reported either
        way; this test asserts the pre-registered w1 width tolerance, so a pass here is the changed outcome."""
        res, miss, wmiss = self._w1((6,), key='w1_t6')
        self.assertEqual(miss, {}, miss)
        self.assertEqual(wmiss, {}, wmiss)

    def test_w6_inflated_sigma(self):
        """F-I4.14 w6 under F-I4.15 (t from all points): t = 10 mm, sigma 3 mm: CARVE both, the w1 checks, widths within
        1 mm of t + 2 (the F-I4.14 miss was the step-1 estimate on the downsample)."""
        def prep(b):
            b.meta['sigma_mm'] = dict(A=3.0, B=3.0)
        res, miss, wmiss = self._w1((10,), prep=prep, key='w6')
        self.assertEqual(miss, {}, miss)
        self.assertEqual(wmiss, {}, wmiss)

    @unittest.skip('replaced by WaiverR2.test_w6c_all_points (F-I4.15.7)')
    def test_w6b_camera_side_estimator(self):
        pass

    def test_w5_p3(self):
        """w5 under F-I4.15: P3 on w1 at t = 10 mm, 16 jittered copies: carved lag <= 0.5 cm and <= 5 deg; the F-I4.7
        table with the real prism counts."""
        b, cand, recs, sides = TI._waiver_case(10)
        ph, acc = p3_of(b, recs, 16, 'T-I1 w5 (F-I4.15)')
        TI.RESULTS['w5_r2'] = dict(P3=ph['P3'], P2=ph['P2'], P6=ph['P6'], P7=ph['P7'], P4=ph['P4'], acceptance=acc)
        c = ph['P3']['carved']
        self.assertLessEqual(c['lag_cm_asm'], 0.5, c)
        self.assertLessEqual(c['lag_deg_asm'], 5.0, c)

    def test_w6c_all_points(self):
        """F-I4.15.7 w6c: the F-I4.15.1 estimator (camera-side split on ALL near points) of plate A in the w1 cross at
        t = 6, 10, 18 mm and sigma 1, 3 mm: |t - true| <= 1.0 mm in every cell. The reference plane is the one of the
        route (step 1 pair or step 2 largest plane); if the plate test fails, the largest plane is used and reported."""
        from gmg import structure as ST
        out, bad = {}, []
        for t_mm in (6, 10, 18):
            for sg in (1.0, 3.0):
                t = t_mm * 1e-3
                b, _ = TI.cross_episode(t, two_sided=True)
                b.meta['sigma_mm'] = dict(A=sg, B=sg)
                info = PB.plate_info(b, 'A', TI.plate(t))
                ta = info.get('t_all')
                row = dict(plate=info.get('plate'), t_source=info.get('t_source'), why=info.get('why'),
                           t_down_mm=info.get('t_down_mm'))
                if ta is None:                              # plate test failed before the estimator: direct estimate
                    P, Cm, fr, _ = PB._near_points(b, 'A', TI.plate(t))
                    K = ST.consts()
                    Pd, Cd, _ = ST._points(dict(pts=P, cam=Cm, own=np.zeros(len(P), np.uint8)), K,
                                           np.random.default_rng(0))
                    planes, _, _ = ST._planes(Pd, Cd, sg * 1e-3, K)
                    ta = PB._t_all_points(P, Cm, fr, planes[0]['n'], planes[0]['d'], K)
                    row['reference'] = 'largest plane (route failed first)'
                row.update(t_all_mm=ta.get('t_mm'), ok=ta.get('ok'), checks=ta.get('checks'),
                           faces=ta.get('faces'))
                out[f't{t_mm}_s{sg}'] = row
                if not ta.get('ok') or abs(ta['t_mm'] - t_mm) > 1.0:
                    bad.append((t_mm, sg, row.get('t_all_mm')))
        RES['w6c'] = out
        self.assertEqual(bad, [], bad)

    def _w8(self, sigma, key, tilt=0.0, physics=True):
        t_mm = 7
        b = i_episode(t_mm * 1e-3, sigma=sigma, tilt_deg=tilt)
        cand = dict(A=iplate(t_mm * 1e-3), B=iplate(t_mm * 1e-3))
        recs, sides = TI.run_pair(b, cand, waiver=True)
        s = summary15(recs, sides, b)
        m, wm = w_checks(s, t_mm)
        for o in ('A', 'B'):
            r = s.get(o) or {}
            wd = r.get('widths_mm') or {}
            if wd and abs(wd['end_minus_waist'] - 11.0) > 3.0:
                m.append(f'{o} end - waist {wd["end_minus_waist"]} mm (true 11)')
            fs = r.get('free_share') or {}
            if fs and not (fs['polygon']['free'] < fs['rectangle']['free']):
                m.append(f'{o} FREE share polygon {fs["polygon"]["free"]} not below rectangle {fs["rectangle"]["free"]}')
            if r.get('u_e_poly_mm') is not None:
                sh = r.get('entry_edge_shift_mm')
                if sh is None or sh < 3.0:              # the waist edge lies inside the rectangle (end-width) edge
                    m.append(f'{o} D not from the waist edge (shift {sh} mm)')
        if wm:
            m += wm
        out = dict(summary=s, misses=m)
        if physics and all((s.get(o) or {}).get('decision') == 'CARVE' for o in 'AB'):
            t0 = time.time()
            ph, acc = p3_of(b, recs, 16, f'T-I1 {key} (F-I4.15)')
            p3 = ph['P3']
            out.update(P3={k: p3.get(k) for k in ('carved', 'default', 'nocollide', 'judge')}, P2=ph['P2'],
                       P4=ph['P4'], P6={k: v for k, v in ph['P6'].items()}, P7=ph['P7'], acceptance=acc,
                       sec=round(time.time() - t0, 1))
            j = p3['judge']
            c = p3['carved']
            if not (c['lag_cm_asm'] <= 0.5 and c['lag_deg_asm'] <= 5.0 and
                    ph['P6']['carved_asm_median'] < 1.0 and j['pass_']):
                m.append(f'P3 carved {c} overlap {ph["P6"]["carved_asm_median"]} judge {j}')
        RES[key] = out
        return out, m

    def test_w8_i_cross(self):
        """F-I4.15.7 w8 (I-shaped cross, sigma 1 mm)."""
        out, m = self._w8(1.0, 'w8')
        self.assertEqual(m, [], m)

    def test_w8b_i_cross_sigma3(self):
        """F-I4.15.7 w8b (w8 at sigma 3 mm)."""
        out, m = self._w8(3.0, 'w8b')
        self.assertEqual(m, [], m)

    def test_w9_tilt(self):
        """F-I4.15.7 w9 (w8 with the partner turned 2.5 deg about a_T at the assembled frames): reported; P56 = P3
        passes (<= 0.5 cm / 5 deg, overlap < 1.0 cm3)."""
        out, m = self._w8(1.0, 'w9', tilt=2.5)
        p3m = [x for x in m if x.startswith('P3')]
        RES['w9_other_misses'] = [x for x in m if not x.startswith('P3')]
        self.assertEqual(p3m, [], p3m)


def tearDownModule():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    out = dict(fi4_rev=PB.REV, fi415=RES, test_interlock_results=TI.RESULTS)
    with open(OUT, 'w') as f:
        json.dump(out, f, indent=1, default=IL._jdefault)
    print('results ->', OUT)


if __name__ == '__main__':
    unittest.main(verbosity=2)
