"""T-I14 synthetic tests of the collision carve, round 2 (PREREG F-I5.15 (9), F-I5.16 (4); INTERLOCK.md 21.13.11,
21.14.6; build step 2 of the round-2 workflow, 31 Oct). New file; the round-1 tests (test_collcarve.py) are unchanged.

  GMG_MODE=dev python docs/research/mesh-2026-10-26/gmg/tests/test_collcarve2.py               (venv python)
  GMG_MODE=dev python .../test_collcarve2.py Rings.test_r3_intrusion                            (one test)

Fixtures (GT-free by construction: synthetic meshes, tracks and stereo evidence, as T-I12; test_collcarve's
builders are reused):
  cup / pot  the T-I12 tapered cup (outer radius 35 -> 40 mm over 95 mm, 3.0 deg, wall 4 mm, base 6 mm) and the T-I12
             pot (r 100 mm, 120 mm, wall 4 mm, base 6 mm); r3: the same cup at 256 facets (analytic formula)
  r1         round-1 construction (8-sector chords) on a 5.36 mm-wall cup (r_out 42.5 -> 47.6 mm, the real cups' wall)
  r4 / r5    straight-tapered cups t = 5.36 mm, 3 deg, flat 6 mm base, r_out 47.6 mm / 98.4 mm at the rim (P97)
  p1-p4      precheck fixtures (P85): p1 guest 10 mm into the table, p2 guest 10 mm above everything, p3 co-located
             wall-crossing cups on the table, p4 = n1 at rest
  n1         the T-I12 x1 nest: guest's outer surface tangent to the host's inner wall at a true rest 20 mm above the
             host bottom, tracked 9.5 mm too deep (0.5 mm radially), coaxial approach, hands off for the last 50
             frames; the guest's sectors half a sector offset from the host's (rotation pi / N_s about the axis)
  n3         n1 with a 1 mm lateral offset (P82); tn0 = the exact rest on axis, tn1 = the exact rest depth with 1 mm
             lateral offset (the orchestrator's "true nest on-axis and 1 mm off"; reported as measured); n2a = the
             exact rest with ALIGNED sectors (P83 aligned leg, diagnostic)
  g1-g3      contact gate (P96; the orchestrator's 2 x 77-piece scene): g1 two free 7 x 11 tile sets (77 pieces
             each) stacked face to face on the table -> contact_overflow; g2 delivered = the packed default's hull
             split in four -> contact_ratio; g3 delivered = the packed default -> pass, ratio 1.0
  controls   x6 plate pair untouched, x10 flag off unchanged, under the round-2 context; round 1 still reachable
Results: <scratchpad>/gmg/interlock/test_collcarve2.json (env CC2_OUT overrides). COPIES = 16 unless CC_COPIES is set
(a smaller value is a smoke run, never a T-I14 result).
"""
import json
import math
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

from gmg import interlock as IL, cavpieces as CP, collcarve as CC, contactgate5 as CG  # noqa: E402
import test_collcarve as T1  # noqa: E402

OUT = os.environ.get('CC2_OUT', os.path.join(guard.SCRATCH_DEFAULT, 'gmg', 'interlock', 'test_collcarve2.json'))
RESULTS = {}
COPIES = int(os.environ.get('CC_COPIES', '16'))
AXIS = T1.AXIS
TAN = T1.TAN
log = T1.log


def _save():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    prev = {}
    if os.path.exists(OUT):
        try:
            prev = json.load(open(OUT))
        except Exception:                                            # noqa: BLE001
            prev = {}
    prev.update(RESULTS)
    with open(OUT, 'w') as fh:
        json.dump(prev, fh, indent=1, default=IL._jdefault)


def _strip(d, keys=('per_copy',)):
    if isinstance(d, dict):
        return {k: _strip(v, keys) for k, v in d.items() if k not in keys}
    if isinstance(d, list):
        return [_strip(v, keys) for v in d]
    return d


# ------------------------------------------------------------------------------------------------ fixtures
def pot():
    return trimesh.boolean.difference([trimesh.creation.cylinder(0.100, 0.120, sections=128).apply_translation(
        [0, 0, 0.060]), trimesh.creation.cylinder(0.096, 0.120, sections=128).apply_translation([0, 0, 0.066])],
        engine='manifold')


def tapered_cup(r_rim, t=0.00536, h=0.095, base=0.006, tan=None, n=128):
    """Straight-tapered cup: outer radius r_rim at the rim, 3 deg taper, wall t, flat solid base."""
    tan = TAN if tan is None else tan
    rb = r_rim - tan * h
    out = T1.frustum(rb, r_rim, 0.0, h, n=n)
    inner = T1.frustum(rb - t + tan * base, rb - t + tan * (h + 0.02), base, h + 0.02, n=n)
    return trimesh.boolean.difference([out, inner], engine='manifold')


def rz(deg):
    M = np.eye(4)
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    M[:2, :2] = [[c, -s], [s, c]]
    return M


_ROUTES = {}


def routes(b, meshes, lathe=None, key=None, plate=None, force_route=None):
    """Default pieces (route_pieces2) per object; cached by KEY (the routes do not depend on the poses); the evidence
    is rebuilt on B."""
    cap = CP.piece_cap(len(meshes))
    out = {}
    for o, m in meshes.items():
        ck = (key, o) if key else None
        ev = IL.Evidence(b, o, m, sub=False)
        if ck and ck in _ROUTES:
            r = _ROUTES[ck]
        else:
            t = time.time()
            la = (lathe or {}).get(o)
            r = CP.route_pieces2(m, ev, cap, lathe_axis=la, lathe_ok=la is not None,
                                 plate_like=bool((plate or {}).get(o)), sigma=b.sigma(o),
                                 skip=(force_route or {}).get(o, ()), log=log)
            r['sec'] = round(time.time() - t, 1)
            if ck:
                _ROUTES[ck] = r
        out[o] = dict(hulls=r['hulls'], body=m, route=r['route'], lathe=r.get('lathe'),
                      plate_like=bool((plate or {}).get(o)), handle_hulls=r.get('handle_hulls') or [], cap=cap, ev=ev,
                      gate_default=r['gate'], tried=r['tried'],
                      n_ring=len(r['hulls']) - r.get('n_handle', 0))
        log('pieces r2', o, r['route'], len(r['hulls']), 'n_s', None if r.get('lathe') is None else
            r['lathe'][1]['n_s'], r['gate'])
    return out


def _layout_rows(obj):
    for t in obj['tried']:
        if t['route'] == '2_lathe':
            return [{k: v for k, v in row.items() if k not in ('handle', 'share_detail')}
                    for row in t['report']['tried']]
    return None


Z_TRUE = T1.Z_TRUE
RB_G = 0.035 - 0.004 + TAN * Z_TRUE


def nest_case(depth_err=0.0095, offset=(0.0, 0.0), phase_deg=None, T=90, n_slow=40, slow_mm=20.0, jitter=True,
              n_s=12):
    """The x1 geometry: host cup A at the origin, guest cup B lowered along -z to Z_TRUE - depth_err, OFFSET lateral
    from the slow phase on; PHASE_DEG (default half a sector, 180 / N_s) rotates B about its axis."""
    host = T1.cup()
    guest = T1.cup(rb=RB_G)
    ph = 180.0 / n_s if phase_deg is None else phase_deg
    pose0 = T1.nest_motion(Z_TRUE - depth_err, T, offset=offset, n_slow=n_slow, slow_mm=slow_mm)

    def pose(f):
        return pose0(f) @ rz(ph)
    b = T1.episode(host, guest, pose, T, list(range(10, T)), jitter=jitter)
    b.hands = T1.hands_for(pose, T, 16 + n_slow)
    return b, dict(A=host, B=guest)


def run2(b, meshes, key, lathe=None, physics=True, hands=None, route_key=None, floor=True, **kw):
    t = time.time()
    objects = routes(b, meshes, lathe, key=route_key)
    ctx, rep = CC.run_pairs2(b, objects, copies=COPIES, log=log, physics=physics, hands=hands, **kw)
    W = ctx.results[('A', 'B')]
    out = dict(routes={o: v['route'] for o, v in objects.items()}, pieces={o: len(v['hulls']) for o, v in objects.items()},
               n_s={o: None if v.get('lathe') is None else v['lathe'][1]['n_s'] for o, v in objects.items()},
               layout_search={o: _layout_rows(v) for o, v in objects.items()},
               result=_strip(CC.public_result(W)), push=ctx.push)
    fl = gt = None
    if floor and physics:
        fl, gt = CC.floor_and_gate(ctx, visuals=meshes, synthetic=True, log=log)
        out['floor'] = _strip(fl)
        out['gate'] = _strip(gt, keys=('per_copy', 'config'))
        out['gate_config'] = dict(path=gt['config']['path'], sha256=gt['config']['sha256'],
                                  values=gt['config']['values'])
    out['sec'] = round(time.time() - t, 1)
    RESULTS[key] = out
    _save()
    return objects, ctx, W, fl, gt


def s_delivered(fl, W):
    """S rows on the delivered pieces: the floor rows (all precheck-passing floor frames) and the acceptance rows."""
    rows = []
    for k, v in (fl or {}).get('pairs', {}).items():
        for r in v.get('rows', []):
            if 'S' in r:
                rows.append(dict(src='floor', frame=r['frame'], disp_mm=r['S']['disp_mm'], tilt_deg=r['S']['tilt_deg'],
                                 pass_=r['S']['pass_'], ref_pass=r['S_ref']['pass_'],
                                 ref_disp_mm=r['S_ref'].get('disp_mm')))
    return rows


# ------------------------------------------------------------------------------------------------ rings
class Rings(unittest.TestCase):
    def _sweep(self, mesh, name):
        P = CP.Profile2(mesh, *AXIS, 0.001)
        rows = {}
        for n_s in (8, 12, 16):
            lay = CP.build_layout(P, n_s, 'b1', {})
            hl = CP.layout_hulls(P, lay)
            it = CP.intrusion2(P, lay, hl)
            co = CP.continuity2(P, lay, hl)
            rows[n_s] = dict(n_r=lay['n_r'], min_wall_mm=round(lay['min_wall_mm'], 4), ring_cm3=round(lay['ring_cm3'], 3),
                             intrusion_construction_mm=it['max_mm'], intrusion_positive_rays=it['n_positive'],
                             construction_rays=it['rays'], continuity=co)
            log(name, n_s, rows[n_s]['min_wall_mm'], it['max_mm'], co['ok'], co.get('intrusion_max_mm'))
        return P, rows

    def test_r3_intrusion(self):
        """Orchestrator item: cavity intrusion of the ring pieces <= 0 at 8 / 12 / 16 sectors on a tapered cup and a pot
        profile (construction rays: <= 1e-6 m by construction, measured; continuity rays: reported, P71 <= 0.3 mm);
        r3 (P87): the analytic 256-facet cup, min wall within 0.05 mm of the formula."""
        out = {}
        for name, mesh in (('cup', T1.cup()), ('pot', pot())):
            _, rows = self._sweep(mesh, name)
            out[name] = rows
            for n_s, r in rows.items():
                ic = r['intrusion_construction_mm']           # None: no piece left on any ray (all walls negative)
                self.assertTrue(ic is None or ic <= 1e-3, (name, n_s, r))
                self.assertEqual(r['intrusion_positive_rays'], 0, (name, n_s))
                ci = r['continuity'].get('intrusion_max_mm')
                self.assertTrue(ci is None or ci <= 0.3, (name, n_s, ci))
        # r3 analytic: outer r_o(h) = 35 + TAN h, inner r_i(h) = 31 + TAN h (h >= 6 mm), one band 6 -> 95 mm
        cup256 = T1.frustum(0.035, 0.035 + TAN * 0.095, 0.0, 0.095, n=256)
        inner = T1.frustum(0.031 + TAN * 0.006, 0.031 + TAN * 0.115, 0.006, 0.115, n=256)
        m = trimesh.boolean.difference([cup256, inner], engine='manifold')
        P, rows = self._sweep(m, 'r3')
        form = {}
        for n_s, r in rows.items():
            th = math.pi / n_s
            r['formula_note'] = 'min over both band ends of R cos(theta) - rho and R - rho / cos(theta), round profile'

            # the rule's chord is fitted at the construction rays (integer degrees): the outermost ray of a sector sits
            # psi_max = theta - (distance of the edge to the nearest inner ray) from mid-sector
            vals, vals_c = [], []
            for sct in range(n_s):
                e0, e1 = math.degrees(2 * th) * sct, math.degrees(2 * th) * (sct + 1)
                gap = min(math.ceil(e0 - 1e-9) - e0, e1 - math.floor(e1 + 1e-9))   # edge to its nearest inner ray
                psi_max = th - math.radians(gap)
                for h in (0.006, 0.095):
                    ro, ri = 0.035 + TAN * h, 0.031 + TAN * h
                    R = ro * math.cos(psi_max) / math.cos(th)
                    vals += [R * math.cos(th) - ri, R - ri / math.cos(th)]
                    vals_c += [ro * math.cos(th) - ri, ro - ri / math.cos(th)]
            form[n_s] = round(min(vals) * 1e3, 4)
            r['formula_min_wall_mm'] = form[n_s]
            r['formula_continuous_min_wall_mm'] = round(min(vals_c) * 1e3, 4)
            self.assertTrue(r['intrusion_construction_mm'] is None or r['intrusion_construction_mm'] <= 1e-3)
            self.assertLess(abs(r['min_wall_mm'] - form[n_s]), 0.05, (n_s, r['min_wall_mm'], form[n_s]))
        out['r3'] = rows
        RESULTS['r3_intrusion'] = out
        _save()

    def test_r1_round1_chords(self):
        """P87 r1 and the non-self-referential continuity check: round 1's 8-sector chord rings on a 5.36 mm-wall cup
        sit inside the cavity (intrusion > 0 on the construction rays) and fail continuity2 (gaps > 1 %), while round
        1's own self-referential check (points between its own chords) passes."""
        m = tapered_cup(0.0476)
        L, _ = CP.Lathe.from_mesh(m, *AXIS, 0.001)
        pcs = L.pieces(8)
        hl = L.hulls(pcs)
        own = CP.continuity(L, hl, pcs)
        P = CP.Profile2(m, *AXIS, 0.001)
        lay = CP.build_layout(P, 8, 'b1', {})            # only for the ray set (wall starts)
        it = CP.intrusion2(P, lay, hl)
        co = CP.continuity2(P, lay, hl)
        RESULTS['r1'] = dict(round1_self_check=own, intrusion_construction=it, continuity2=co)
        _save()
        self.assertTrue(own['ok'], own)
        self.assertGreater(it['max_mm'], 0.5, it)
        self.assertFalse(co['ok'], co)
        self.assertGreater(co['gap_share'], 0.01, co)

    def test_r2_forced_ring_and_thin(self):
        """P87 r2: a forced 1 mm ring above the base is caught by continuity2; and a self-consistent set that covers
        only a third of the SHELL wall (outer faces moved 3 mm in) passes a self-referential test but fails
        continuity2 (non-self-referential: the rays are tested against the SHELL)."""
        m = T1.cup()
        P = CP.Profile2(m, *AXIS, 0.001)
        lay = CP.build_layout(P, 12, 'b1', {})
        base = CP.continuity2(P, lay, CP.layout_hulls(P, lay))
        ring = dict(lay, pieces=[dict(p, h0=p['h0'] + 0.001, rho0=CP._lin(p, 'rho', p['h0'] + 0.001),
                                      R0=CP._lin(p, 'R', p['h0'] + 0.001)) if p['kind'] == 'wall' else p
                                 for p in lay['pieces']])
        cr = CP.continuity2(P, ring, CP.layout_hulls(P, ring))
        thin = dict(lay, pieces=[dict(p, R0=p['R0'] - 0.0018, R1=p['R1'] - 0.0018) if p['kind'] == 'wall' else p
                                 for p in lay['pieces']])
        th_h = CP.layout_hulls(P, thin)
        # self-referential probe: points at the middle of each piece's own wall (between its faces) lie inside it
        H = CP.Hulls(th_h)
        mids = np.vstack([V.mean(0)[None] for V in th_h])
        self_ok = bool(H.inside(mids, tol=1e-9).all())
        ct = CP.continuity2(P, thin, th_h)
        RESULTS['r2'] = dict(default=base, forced_ring=cr, thin=dict(self_check=self_ok, continuity2=ct))
        _save()
        self.assertTrue(base['ok'], base)
        self.assertFalse(cr['ok'], cr)
        self.assertGreater(cr['worst_height_gap_share'], 0.5, cr)
        self.assertTrue(self_ok)
        self.assertFalse(ct['ok'], ct)

    def test_r4_r5_search(self):
        """P97: the smallest-layout search on straight-tapered cups (t = 5.36 mm, 3 deg, flat base): r4 (r_out 47.6
        mm) accepted at 12 sectors, b1, one band (n_r = 13), the 8-sector candidate failing (iii); r5 (r_out 98.4 mm)
        at 16 sectors, b1, one band (n_r = 17), the 8- and 12-sector candidates failing (iii). Asserted: the accepted
        layouts; the failing check of the earlier candidates is recorded (a miss of P97's '(iii)' clause is
        reported, not asserted)."""
        out = {}
        for name, r_rim, want in (('r4', 0.0476, 12), ('r5', 0.0984, 16)):
            m = tapered_cup(r_rim)
            b = T1.episode(m, trimesh.creation.box(extents=[0.02] * 3), lambda f: np.array(
                [[1, 0, 0, 0.5], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1.0]]), 6, [], jitter=False)
            ev = IL.Evidence(b, 'A', m, sub=False)
            P = CP.Profile2(m, *AXIS, 0.001)
            t = time.time()
            acc, rep = CP.search_layout(P, m, ev, 82, log=log)
            rows = [{k: v for k, v in r_.items() if k not in ('handle', 'share_detail')} for r_ in rep['tried']]
            out[name] = dict(accepted=rep.get('accepted'), tried=rows, sec=round(time.time() - t, 1))
            log(name, rep.get('accepted'), [(r_['n_s'], r_['base'], r_['n_r'], r_.get('fail')) for r_ in rows])
            self.assertIsNotNone(acc, rows)
            self.assertEqual(acc['layout']['n_s'], want, rep.get('accepted'))
            self.assertEqual(acc['layout']['base'], 'b1')
            self.assertEqual(acc['layout']['n_r'], want + 1)
        RESULTS['r4_r5'] = out
        _save()


# ------------------------------------------------------------------------------------------------ precheck
class Precheck(unittest.TestCase):
    def test_p1_p4(self):
        """P85: p1 (guest 10 mm into the table) fails (a); p2 (guest 10 mm above everything) fails (b); p3
        (co-located, wall-crossing cups on the table) fails (c); p4 (n1 at rest) passes."""
        host = T1.cup()
        guest = T1.cup(rb=RB_G)
        Fh, Fg = CC.Faithful(host), CC.Faithful(guest)
        tb = ([0, 0, 1.0], 0.0)
        I = np.eye(4)
        out = {}
        # p1: guest stands 10 mm into the table, 150 mm away from the host
        T = np.eye(4); T[0, 3] = 0.15; T[2, 3] = -0.010
        out['p1'] = CC.precheck(Fh, Fg, I, T, tb, host, guest)
        # p2: guest 10 mm above the table, 150 mm away
        T = np.eye(4); T[0, 3] = 0.15; T[2, 3] = 0.010
        out['p2'] = CC.precheck(Fh, Fg, I, T, tb, host, guest)
        # p3: a straight-walled cup (r 37.5 mm) co-located with the tapered host: walls cross at mid height
        wc = trimesh.boolean.difference([trimesh.creation.cylinder(0.0375, 0.095, sections=96).apply_translation(
            [0, 0, 0.0475]), trimesh.creation.cylinder(0.0335, 0.095, sections=96).apply_translation([0, 0, 0.0535])],
            engine='manifold')
        out['p3'] = CC.precheck(Fh, CC.Faithful(wc), I, np.eye(4), tb, host, wc)
        # p4: n1 at rest (9.5 mm too deep: 0.5 mm radially)
        T = np.eye(4); T[2, 3] = Z_TRUE - 0.0095
        out['p4'] = CC.precheck(Fh, Fg, I, T, tb, host, guest)
        RESULTS['precheck'] = out
        _save()
        log('precheck', {k: (v['fail'], v['fails']) for k, v in out.items()})
        self.assertEqual(out['p1']['fail'], 'a_table', out['p1'])
        self.assertEqual(out['p2']['fail'], 'b_support', out['p2'])
        self.assertEqual(out['p3']['fails'], ['c_overlap'], out['p3'])
        self.assertTrue(out['p4']['pass_'], out['p4'])


# ------------------------------------------------------------------------------------------------ nests
class Nest(unittest.TestCase):
    """The nested-cup fixtures. Asserted per fixture: what PREREG F-I5.15 / F-I5.16 predicted (P81, P82, P83, P98) and
    the orchestrator's 'passes S on the delivered pieces' where it applies; every number is in the results file."""

    def _run(self, key, **kw):
        b, M = nest_case(**kw)
        objects, ctx, W, fl, gt = run2(b, M, key, lathe=dict(A=AXIS, B=AXIS), hands=b.hands, route_key='cups')
        s = dict(deliver=W.get('deliver'), why=W.get('why'), receiver=W.get('receiver'),
                 n_s={o: v['lathe'][1]['n_s'] for o, v in objects.items() if v.get('lathe')},
                 components=[dict(why=c.get('why'), ok_frames=c.get('ok_frames'),
                                  precheck={f: p.get('fails') for f, p in (c.get('precheck') or {}).items()},
                                  c_mm=(c.get('clearance') or {}).get('c_mm'),
                                  sigma_wall=(c.get('clearance') or {}).get('sigma_wall'),
                                  off_axis=c.get('off_axis')) for c in W.get('components') or []],
                 caps=_strip(W.get('caps')), tests=(W.get('acceptance') or {}).get('tests'),
                 failing=(W.get('acceptance') or {}).get('failing'),
                 S_accept=[dict(f=r['frame'], carved=r['carved'].get('disp_mm'), carved_pass=r['carved']['pass_'],
                                ref=r['ref'].get('disp_mm'), ref_pass=r['ref']['pass_'], default=r['default'].get('disp_mm'))
                           for r in ((W.get('acceptance') or {}).get('S') or {}).get('frames', [])],
                 S_delivered=s_delivered(fl, W), floor_pass=(fl or {}).get('pass_'),
                 floor_fails=(fl or {}).get('fails'), g1=(gt or {}).get('g1_pass'),
                 g1_pairs={k: v['verdict'] for k, v in (gt or {}).get('pairs', {}).items()})
        RESULTS[key]['summary'] = s
        _save()
        log(key, json.dumps(s, default=IL._jdefault)[:3000])
        return s

    def test_n1(self):
        """P81 / P98: n1 carved and delivered (c = 0.10 mm, S <= 4 mm / 5 deg, topology kept, min wall >= 1.5 mm,
        removed <= 0.5, P2-P7 and the floor pass, G1 passes); the orchestrator's on-axis nest passes S on the delivered
        pieces."""
        s = self._run('n1')
        self.assertTrue(str(s['deliver']).startswith('carved'), s)
        self.assertEqual(s['components'][0]['c_mm'], 0.1, s)
        self.assertTrue(s['S_delivered'] and all(r['pass_'] for r in s['S_delivered']), s['S_delivered'])
        self.assertTrue(s['floor_pass'], s['floor_fails'])
        self.assertTrue(s['g1'], s['g1_pairs'])

    def test_n3(self):
        """P82: n3 (n1 with a 1 mm lateral offset) carved and delivered; the orchestrator's 1 mm off-axis nest passes S
        on the delivered pieces."""
        s = self._run('n3', offset=(0.001, 0.0))
        self.assertTrue(str(s['deliver']).startswith('carved'), s)
        self.assertTrue(s['S_delivered'] and all(r['pass_'] for r in s['S_delivered']), s['S_delivered'])

    def test_tn0_exact_on_axis(self):
        """Orchestrator: a true nest (the exact rest, on axis, sectors half offset): nothing to carve; S on the
        delivered (default) pieces passes (P83's half-offset leg: mean drop <= 2 mm)."""
        s = self._run('tn0', depth_err=0.0)
        self.assertTrue(s['S_delivered'] and all(r['pass_'] for r in s['S_delivered']), s['S_delivered'])

    def test_tn1_exact_1mm_off(self):
        """Orchestrator: the exact rest depth with a 1 mm lateral offset; S on the delivered pieces (reported; no
        pre-registered outcome)."""
        s = self._run('tn1', depth_err=0.0, offset=(0.001, 0.0))
        self.assertTrue(s['S_delivered'] and all(r['pass_'] for r in s['S_delivered']), s['S_delivered'])

    def test_n2a_aligned(self):
        """P83 aligned leg (diagnostic): the exact rest with ALIGNED 12-sector rings lets the guest drop >= 4 mm (S
        fails on the delivered default pieces) while the 64-sector references hold it (mean drop <= 2 mm)."""
        s = self._run('n2a', depth_err=0.0, phase_deg=0.0)
        rows = s['S_delivered']
        self.assertTrue(rows, s)
        self.assertTrue(all(not r['pass_'] for r in rows), rows)


# ------------------------------------------------------------------------------------------------ contact gate
def tiles(nx, ny, z0, t=0.01, size=0.02):
    out = []
    for i in range(nx):
        for j in range(ny):
            bx = trimesh.creation.box(extents=[size, size, t])
            bx.apply_translation([(i - nx / 2 + 0.5) * size, (j - ny / 2 + 0.5) * size, z0 + t / 2])
            out.append(np.asarray(bx.vertices))
    return out


class Gate(unittest.TestCase):
    """P96 and the orchestrator's 2 x 77-piece scene: two free objects (P1 settle scene) stacked face to face on the
    table under the sim=rl limits; the packed default = FlashCHORD's CoACD (0.05, coacd 1.0.11) of the slab."""

    @classmethod
    def setUpClass(cls):
        cls.cfg = CG.sim_rl()
        cls.opt = CG.options(cls.cfg)
        slab = trimesh.creation.box(extents=[0.14, 0.22, 0.01])
        slab.apply_translation([0, 0, 0.005])
        cls.slab = slab
        cls.packed, cls.pinfo = CG.packed_default(slab)
        cls.I = np.eye(4)
        cls.TB = np.eye(4); cls.TB[2, 3] = 0.010
        cls.table = ([0, 0, 1.0], 0.0)

    def _row(self, A, B, stop=False):
        return CG.count_scene('settle', A, B, self.I, self.TB, self.table, self.opt, copies=COPIES,
                              stop_on_overflow=stop)

    def test_g1_g3(self):
        A = tiles(7, 11, 0.0)
        Bt = tiles(7, 11, 0.0)
        t = time.time()
        d77 = self._row(A, Bt, stop=True)
        pk = self._row(self.packed, self.packed)
        v1 = CG.g1([dict(scene='settle', frame=0, gated=True, sets=dict(delivered=d77, packed=pk))], self.opt)
        v3 = CG.g1([dict(scene='settle', frame=0, gated=True, sets=dict(delivered=pk, packed=pk))], self.opt)
        RESULTS['gate_g1_g3'] = dict(config=dict(path=self.cfg['path'], sha256=self.cfg['sha256'],
                                                 values=self.cfg['values']), options=self.opt, packed_info=self.pinfo,
                                     g1_2x77=dict(verdict=v1, delivered=_strip(d77), packed=_strip(pk)),
                                     g3_packed_control=dict(verdict=v3), sec=round(time.time() - t, 1),
                                     note='g1 delivered copies stop at their first overflowing step (the verdict is '
                                          'overflow; maxima are lower bounds)')
        _save()
        log('gate', v1, v3)
        self.assertEqual(len(self.packed), 1, self.pinfo)
        self.assertFalse(v1['pass_']); self.assertEqual(v1['fail'], 'contact_overflow', v1)
        self.assertTrue(v3['pass_'], v3); self.assertEqual(v3['ratio'], 1.0)

    def test_g2_split(self):
        """g2: the packed hull split in four across its faces (2 x 2 tiles per object) -> contact_ratio (no overflow)."""
        A = tiles(2, 2, 0.0, size=None or 0.07)
        A = [V * np.array([1.0, 0.22 / 0.14, 1.0]) for V in A]
        d4 = self._row(A, A)
        pk = self._row(self.packed, self.packed)
        v2 = CG.g1([dict(scene='settle', frame=0, gated=True, sets=dict(delivered=d4, packed=pk))], self.opt)
        RESULTS['gate_g2'] = dict(verdict=v2, delivered=_strip(d4), packed=_strip(pk))
        _save()
        self.assertFalse(v2['pass_'], v2)
        self.assertEqual(v2['fail'], 'contact_ratio', v2)


# ------------------------------------------------------------------------------------------------ controls
class Controls(unittest.TestCase):
    def test_x6_x10_round2(self):
        """P89: under the round-2 context a plate pair is left to F-I4 (records identical with and without it) and
        decide_pair without the context is the F-I1..F-I3 path (omitted == None)."""
        A = trimesh.creation.box(extents=[0.23, 0.125, 0.01])
        Bm = trimesh.creation.box(extents=[0.23, 0.125, 0.01])
        Rb = np.array([[0, 0, -1.0], [0, 1.0, 0], [1.0, 0, 0]])

        def pose(f):
            M = np.eye(4); M[:3, :3] = Rb; M[1, 3] = max(0.12 - f * 0.002, 0.0); return M
        b = T1.episode(A, Bm, pose, 90, list(range(90)), table_z=-0.2)
        objects = routes(b, dict(A=A, B=Bm), plate=dict(A=True, B=True), force_route=dict(A=('3',), B=('3',)))

        def sides():
            s = {}
            for t, q in (('A', 'B'), ('B', 'A')):
                evc = CC.collider_evidence(b, t, objects[t]['hulls'], mesh=objects[t]['body'])
                intr = CC.intrusions_colliders(b, t, q, evc, CC.collider_samples(objects[q]['hulls']),
                                               b.contact(t, q)['contact'])
                s[t] = IL.make_side(b, t, q, evc, intr, b.contact(t, q)['contact'], sources={}, identity='eval',
                                    partner_collider=CC.collider_samples(objects[q]['hulls']))
            return s
        s = sides(); r0 = [IL.public(r) for r in IL.decide_pair(b, s['A'], s['B'])]
        s = sides(); r1 = [IL.public(r) for r in IL.decide_pair(b, s['A'], s['B'], waiver_fi5=None)]
        s = sides()
        ctx = CC.FI5R2(b, objects, copies=COPIES, log=log, physics=False)
        r2 = [IL.public(r) for r in IL.decide_pair(b, s['A'], s['B'], waiver_fi5=ctx)]
        s = sides()
        ctx1 = CC.FI5(b, objects, copies=COPIES, log=log, physics=False)
        r3 = [IL.public(r) for r in IL.decide_pair(b, s['A'], s['B'], waiver_fi5=ctx1)]
        strip = (lambda rs: [{k: v for k, v in r.items() if k != 'waiver_fi5'} for r in rs])
        RESULTS['x6_x10_r2'] = dict(n=len(r0), decisions=[r['decision'] for r in r0], same_off=r0 == r1,
                                    same_plate_r2=strip(r2) == r0, same_plate_r1=strip(r3) == r0,
                                    scope=ctx.results[('A', 'B')].get('scope'), rev_default=CC.REV)
        _save()
        self.assertEqual(r0, r1)
        self.assertEqual(strip(r2), r0)
        self.assertEqual(strip(r3), r0)
        self.assertIn('plate pair', ctx.results[('A', 'B')].get('scope', ''))
        self.assertEqual(CC.REV, 1)

    def test_rev1_reachable(self):
        """Round 1 stays reachable: run_episode's default revision is 1 and the rev-1 route ladder is unchanged (the
        T-I12 x9 builder check reproduces)."""
        host = T1.cup()
        L, info = CP.Lathe.from_mesh(host, *AXIS, 0.001)
        p0 = L.pieces(16)
        c0 = CP.continuity(L, L.hulls(p0), p0)
        p1 = L.pieces(16, ring_gap_m=0.001)
        c1 = CP.continuity(L, L.hulls(p1), p1)
        RESULTS['rev1_reachable'] = dict(rev_default=CC.REV, x9_builder=c0['ok'], x9_forced_ring=c1['ok'])
        _save()
        self.assertEqual(CC.REV, 1)
        self.assertTrue(c0['ok']); self.assertFalse(c1['ok'])


def tearDownModule():
    _save()
    print('results ->', OUT)


if __name__ == '__main__':
    unittest.main(verbosity=2)
