"""T-I12 synthetic tests of the collision carve (PREREG F-I5.9, INTERLOCK.md section 21; build step of the
collision-carve workflow, 31 Oct). New file (the shared tests/test_interlock.py was being edited by the board-slot
workflow when this build started; T-I1 stays there).

  GMG_MODE=dev python docs/research/mesh-2026-10-26/gmg/tests/test_collcarve.py            (venv python)
  GMG_MODE=dev python .../test_collcarve.py Cups.test_x1                                   (one test)

Fixtures (GT-free by construction: synthetic meshes, synthetic tracks, synthetic stereo evidence as in T-I1):
  cups      tapered cups (outer radius 35 -> 40 mm over 95 mm, taper 3.0 deg, wall 4 mm, base 6 mm); the guest's outer
            surface is the host's inner surface (tangent along the wall) at a true rest 20 mm above the host's bottom;
            the guest approaches along the axis, slows over the last 12 mm (24 frames) and rests 40 frames; the track is
            9.5 mm too deep (0.5 mm radially, x1) or offset laterally at the rest frames (x2, x3)
  lidpot    a pot (r 100 mm, 120 mm, wall 4 mm) and a flat lid (r 102 mm, 4 mm) slid 30 mm across the rim 0.6 mm too
            low, then resting
  rack      a U-shaped rack (base plate and two prongs, slot 84 mm) and a cup lowered 60 mm into the slot 1.0 mm into
            one prong all the way down, resting on the base plate
  sweeper   a 20 x 20 x 200 mm stick lowered 40 mm into a 60 mm holder block with a 22 mm square blind hole, 2 mm off
            centre (1 mm into one hole wall), tracked 0.5 mm into the hole floor at rest
Pre-registered outcomes (F-I5.9 T-I12): x1 both lathe, receiver = host (s >= 0.8 vs <= 0.2), c 0.05-0.15 mm, no empty
ring, gate passes, CARVE delivered with S and P2-P7 passing; x2 (3 mm one-sided offset with the guest's bottom edge in
the host wall: a shelf) CARVE delivered; x3 (offset pockets only the tapered wall) S fails, default delivered; x4 (x1,
c forced 1.0 mm) S or P2 gravity fails; x5 (x1 with 6 build frames 10 mm deeper) overshoot flagged and not carved,
CARVE delivered (and with the exclusion disabled S fails); x6 plate pair untouched; x7 controls no carve; x8 a flat
plate never takes the lathe route, a folded sheet with a forced lathe fails the gate and falls to route 3; x9 a forced
1 mm ring is caught by the continuity check; x10 flag off unchanged; x11 an open box via route 3 passes the gate with
its opening empty. Additional cases asked by the orchestrator (no pre-registered outcome; reported as measured):
x2b = x2 with a 5 mm offset (the eval-10 offset); lidpot, rack, sweeper (P45-P47 analogues).
Results: <scratchpad>/gmg/interlock/test_collcarve.json (env CC_OUT overrides).
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
if MR not in sys.path:
    sys.path.insert(0, MR)
from gmg import guard  # noqa: E402
import numpy as np  # noqa: E402
import trimesh  # noqa: E402
from scipy.spatial.transform import Rotation as Rot  # noqa: E402

from gmg import interlock as IL, cavpieces as CP, collcarve as CC  # noqa: E402
from gmg.bundle import Bundle  # noqa: E402

OUT = os.environ.get('CC_OUT', os.path.join(guard.SCRATCH_DEFAULT, 'gmg', 'interlock', 'test_collcarve.json'))
RESULTS = {}
VOX = 0.004
FX = 600.0
COPIES = int(os.environ.get('CC_COPIES', '16'))
TAN = 0.005 / 0.095            # cup taper (radius change per height): 3.01 deg


def log(*a):
    print(time.strftime('%H:%M:%S'), *a, flush=True)


# ------------------------------------------------------------------------------------------------ fixtures
def look(c, target=(0, 0, 0), up=(0, 0, 1.0)):
    c = np.asarray(c, float); t = np.asarray(target, float)
    z = t - c; z /= np.linalg.norm(z)
    up = np.asarray(up, float)
    if abs(z @ up) > 0.95:
        up = np.array([0, 1.0, 0])
    x = np.cross(z, up); x /= np.linalg.norm(x); y = np.cross(z, x)
    R = np.stack([x, y, z]); T = np.eye(4); T[:3, :3] = R; T[:3, 3] = -R @ c
    return T


def grid_for(mesh, pad=4):
    lo = mesh.bounds[0] - pad * VOX
    shape = np.ceil((mesh.bounds[1] + pad * VOX - lo) / VOX).astype(int)
    return IL.Grid(lo, VOX, shape)


def evidence_obs(mesh, rng, n_frames, npts=1500):
    """T-I1 evidence: OBSERVED within 4 mm inside the surface, UNKNOWN deeper, FREE outside; owned points on the
    surface in every frame."""
    g = grid_for(mesh)
    C = g.centres()
    ins = IL.fast_inside(mesh, C)
    d = np.zeros(len(C)); d[ins] = IL.geom.Closest(mesh).query(C[ins])[0]
    state = np.where(ins, np.where(d <= 0.004, 2, 0), 1).astype(np.uint8)
    hits = np.where(state == 2, 20, 0).astype(np.uint16)
    free = np.where(state == 1, 20, 0).astype(np.uint16)
    P, _ = trimesh.sample.sample_surface(mesh, npts, seed=0)
    pts = np.concatenate([P + rng.normal(0, 0.001, P.shape) for _ in range(n_frames)]).astype(np.float32)
    fr = np.concatenate([np.full(len(P), f, np.int32) for f in range(n_frames)])
    return dict(pts=pts, cam=np.zeros_like(pts), frame=fr, own=np.zeros(len(pts), np.uint8), lo=g.lo,
                hi=g.lo + VOX * np.asarray(g.shape), vox=VOX, hits=hits.reshape(g.shape), free=free.reshape(g.shape),
                state=state.reshape(g.shape), shared=np.zeros(g.shape, np.uint16), pocc=np.zeros(g.shape, np.uint16),
                args='{}')


def episode(mesh_a, mesh_b, pose_b, T, contact, table_z=0.0, seed=0, jitter=True):
    """A fixed at the world origin (world = A's frame), B at pose_b(f); one fixed camera; table plane z = table_z;
    jitter 0.5 mm / 0.2 deg on B's track (T-I1 jitter)."""
    rng = np.random.default_rng(seed)
    cam = look([0, -0.45, 0.45])
    world_B = np.stack([pose_b(f) for f in range(T)])
    if jitter:
        for f in range(T):
            J = np.eye(4); J[:3, :3] = Rot.from_rotvec(rng.normal(0, np.radians(0.2), 3)).as_matrix()
            J[:3, 3] = rng.normal(0, 0.0005, 3)
            world_B[f] = world_B[f] @ J
    poses = dict(world_T_cam=np.tile(np.linalg.inv(cam), (T, 1, 1)).astype(np.float32),
                 cam_T_A=np.tile(cam, (T, 1, 1)).astype(np.float32),
                 cam_T_B=np.einsum('ij,fjk->fik', cam, world_B).astype(np.float32))
    obs = dict(A=evidence_obs(mesh_a, rng, T), B=evidence_obs(mesh_b, rng, T))
    cen = dict(frames=list(range(T)), contact=list(contact), separated=[f for f in range(T) if f not in set(contact)],
               j_mm=0.5, band_mm=3.0)
    meta = dict(objects=['A', 'B'], T=T, stride=1, K=[[FX, 0, 800], [0, FX, 500], [0, 0, 1]],
                sigma_mm=dict(A=1.0, B=1.0), contact={'A|B': dict(cen), 'B|A': dict(cen)},
                good={'A': [True] * T, 'B': [True] * T}, sanity={'A': dict(flags=[]), 'B': dict(flags=[])},
                table=dict(n=[0, 0, 1.0], d=-float(table_z)), rest={}, tier='SYNTH')
    return Bundle(meta, obs, poses)


def frustum(r0, r1, z0, z1, n=64, x0=(0.0, 0.0)):
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    V = np.vstack([np.c_[x0[0] + r0 * np.cos(a), x0[1] + r0 * np.sin(a), np.full(n, z0)],
                   np.c_[x0[0] + r1 * np.cos(a), x0[1] + r1 * np.sin(a), np.full(n, z1)]])
    return trimesh.convex.convex_hull(V)


def cup(rb=0.035, h=0.095, wall=0.004, base=0.006, tan=TAN, guest_taper=None):
    """Tapered cup with its bottom at z = 0: outer r(z) = rb + tan z, inner r(z) - wall from z = base. guest_taper
    (x3): the outer surface's taper (the inner keeps tan)."""
    to = tan if guest_taper is None else guest_taper
    out = frustum(rb, rb + to * h, 0.0, h)
    inner = frustum(rb - wall + tan * base, rb - wall + tan * (h + 0.02), base, h + 0.02)
    return trimesh.boolean.difference([out, inner], engine='manifold')


def nest_motion(z_rest, T, n_far=16, n_slow=24, z_top=0.20, slow_mm=12.0, offset=(0.0, 0.0), dip=None):
    """B along -z: from z_top to z_rest + slow over n_far frames, then the last slow_mm over n_slow frames, then rest;
    OFFSET (lateral, m) applied from the slow phase on; DIP: (frames, depth m) extra depth at those frames."""
    zs = np.r_[np.linspace(z_top, z_rest + slow_mm * 1e-3, n_far, endpoint=False),
               np.linspace(z_rest + slow_mm * 1e-3, z_rest, n_slow), np.full(T - n_far - n_slow, z_rest)]

    def pose(f):
        M = np.eye(4); M[2, 3] = zs[f]
        if f >= n_far:
            M[0, 3], M[1, 3] = offset
        if dip is not None and f in dip[0]:
            M[2, 3] -= dip[1]
        return M
    return pose


def objects_for(b, meshes, lathe=None, plate=None, cap=None, force_route=None):
    out = {}
    cap = cap or CP.piece_cap(len(meshes))
    for o, m in meshes.items():
        ev = IL.Evidence(b, o, m, sub=False)
        la = (lathe or {}).get(o)
        r = CP.route_pieces(m, ev, cap, lathe_axis=la, lathe_ok=la is not None,
                            plate_like=bool((plate or {}).get(o)), sigma=b.sigma(o),
                            skip=(force_route or {}).get(o, ()))
        out[o] = dict(hulls=r['hulls'], body=m, route=r['route'], lathe=r.get('lathe'),
                      plate_like=bool((plate or {}).get(o)), n_ring=len(r['hulls']) - r.get('n_handle', 0),
                      cap=cap, ev=ev, gate_default=r['gate'], tried=r['tried'])
        log('pieces', o, r['route'], len(r['hulls']), r['gate'])
    return out


def run(b, meshes, key, lathe=None, plate=None, physics=True, force_route=None, **kw):
    t = time.time()
    objects = objects_for(b, meshes, lathe, plate, force_route=force_route)
    ctx, rep = CC.run_pairs(b, objects, copies=COPIES, log=log, physics=physics, **kw)
    W = ctx.results[('A', 'B')]
    pub = CC.public_result(W)
    RESULTS[key] = dict(routes={o: v['route'] for o, v in objects.items()},
                        pieces={o: len(v['hulls']) for o, v in objects.items()},
                        gate_default={o: v['gate_default'] for o, v in objects.items()},
                        overlap_track=rep['overlap_track'], result=pub,
                        decisions=[dict(target=d['target'], decision=d['decision'], flags=d['flags'],
                                        gates=d.get('waiver_fi5_gates')) for d in rep['decisions']],
                        sec=round(time.time() - t, 1))
    _save()
    return objects, ctx, W, rep


def _save():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w') as fh:
        json.dump(RESULTS, fh, indent=1, default=IL._jdefault)


Z_TRUE = 0.020                 # true rest of the guest's bottom above the host's bottom
AXIS = ([0.0, 0, 0], [0.0, 0, 1.0])


def cups_case(depth_err=0.0095, offset=(0.0, 0.0), guest_taper=None, dip=None, T=90, n_slow=40, slow_mm=20.0):
    host = cup()
    rb_g = 0.035 - 0.004 + TAN * Z_TRUE
    guest = cup(rb=rb_g, guest_taper=guest_taper)
    if guest_taper is not None:            # x3: tangent at the host rim, narrower below (no shelf)
        guest = cup(rb=rb_g + (TAN - guest_taper) * (0.095 - Z_TRUE), guest_taper=guest_taper)
    pose = nest_motion(Z_TRUE - depth_err, T, offset=offset, dip=dip, n_slow=n_slow, slow_mm=slow_mm)
    contact = list(range(10, T))
    b = episode(host, guest, pose, T, contact)
    return b, dict(A=host, B=guest)


def summary(W):
    acc = W.get('acceptance') or {}
    comp = (W.get('components') or [{}])[0]
    return dict(in_scope=W.get('in_scope'), receiver=W.get('receiver'), deliver=W.get('deliver'),
                containment=(W.get('receiver_info') or {}).get('containment'),
                c_mm=(comp.get('clearance') or {}).get('c_mm'), sigma_sup=(comp.get('clearance') or {}).get('sigma_sup'),
                overshoot=len(comp.get('overshoot_frames') or []), caps=W.get('caps'),
                tests=acc.get('tests'), failing=acc.get('failing'),
                S=[dict(f=r['frame'], carved={k: r['carved'].get(k) for k in ('disp_mm', 'dz_mm', 'lateral_mm', 'tilt_deg',
                                                                             'pass_')},
                        default={k: r['default'].get(k) for k in ('disp_mm', 'dz_mm', 'tilt_deg', 'pass_')})
                   for r in (acc.get('S') or {}).get('frames', [])],
                P2=(acc.get('P2') or {}).get('carved_mm'), P2_default=(acc.get('P2') or {}).get('default_mm'),
                shift=((W.get('report') or {}).get('rigid_shift') or {}).get('cleared_share'),
                one_sided=((W.get('report') or {}).get('one_sided') or {}).get('one_sided_share'),
                gates=W.get('gates'), carve=W.get('carve'))


# ------------------------------------------------------------------------------------------------ tests
class Cups(unittest.TestCase):
    def test_x1a_first_fixture(self):
        """The first x1 fixture (slow phase 12 mm over 24 frames, 50 rest frames; 17:59 UTC): the receiver's sweep share
        read 0.494 < 0.5 (waiver_gate_fail:sweep, no carve). Kept as a recorded case: the moves-through gate depends on
        the share of moving build frames. Asserted: no carve is delivered (what the gate does here)."""
        b, M = cups_case(n_slow=24, slow_mm=12.0)
        objects, ctx, W, rep = run(b, M, 'x1a', lathe=dict(A=AXIS, B=AXIS), physics=False)
        s = summary(W); RESULTS['x1a']['summary'] = s; _save()
        log('x1a', json.dumps(s, default=IL._jdefault)[:2000])
        self.assertFalse(str(s['deliver'] or '').startswith('carved'), s)

    def test_x1(self):
        b, M = cups_case()
        objects, ctx, W, rep = run(b, M, 'x1', lathe=dict(A=AXIS, B=AXIS))
        s = summary(W); RESULTS['x1']['summary'] = s; _save()
        log('x1', json.dumps(s, default=IL._jdefault)[:3000])
        self.assertEqual(objects['A']['route'], '2_lathe'); self.assertEqual(objects['B']['route'], '2_lathe')
        self.assertEqual(s['receiver'], 'A', s)
        self.assertGreaterEqual(s['containment']['A'], 0.8); self.assertLessEqual(s['containment']['B'], 0.2)
        self.assertTrue(0.05 <= s['c_mm'] <= 0.15, s['c_mm'])
        self.assertTrue(str(s['deliver']).startswith('carved'), s)

    def test_x2(self):
        b, M = cups_case(depth_err=0.0, offset=(0.003, 0.0))
        objects, ctx, W, rep = run(b, M, 'x2', lathe=dict(A=AXIS, B=AXIS))
        s = summary(W); RESULTS['x2']['summary'] = s; _save()
        log('x2', json.dumps(s, default=IL._jdefault)[:3000])
        self.assertTrue(str(s['deliver']).startswith('carved'), s)

    def test_x2b_5mm(self):
        b, M = cups_case(depth_err=0.0, offset=(0.005, 0.0))
        objects, ctx, W, rep = run(b, M, 'x2b', lathe=dict(A=AXIS, B=AXIS))
        s = summary(W); RESULTS['x2b']['summary'] = s; _save()
        log('x2b', json.dumps(s, default=IL._jdefault)[:3000])
        self.assertIsNotNone(s['deliver'])                           # no pre-registered outcome: reported

    def test_x3(self):
        b, M = cups_case(depth_err=0.0, offset=(0.003, 0.0), guest_taper=TAN * 2.0)
        objects, ctx, W, rep = run(b, M, 'x3', lathe=dict(A=AXIS, B=AXIS))
        s = summary(W); RESULTS['x3']['summary'] = s; _save()
        log('x3', json.dumps(s, default=IL._jdefault)[:3000])
        self.assertEqual(s['deliver'], 'default', s)
        self.assertIn('S', s['failing'] or [], s)

    def test_x4(self):
        b, M = cups_case()
        objects, ctx, W, rep = run(b, M, 'x4', lathe=dict(A=AXIS, B=AXIS), c_override=0.001)
        s = summary(W); RESULTS['x4']['summary'] = s; _save()
        log('x4', json.dumps(s, default=IL._jdefault)[:3000])
        self.assertEqual(s['deliver'], 'default', s)
        self.assertTrue('S' in (s['failing'] or []) or 'P2' in (s['failing'] or []), s)

    def test_x5(self):
        T = 90
        dip = (list(range(50, 56)), 0.010)
        b, M = cups_case(dip=dip, T=T)
        objects, ctx, W, rep = run(b, M, 'x5', lathe=dict(A=AXIS, B=AXIS))
        s = summary(W); RESULTS['x5']['summary'] = s; _save()
        log('x5', json.dumps(s, default=IL._jdefault)[:3000])
        comp = W['components'][0]
        over = {x['f'] for x in comp['overshoot_frames']}
        build_dip = [f for f in dip[0] if f in set(W['components'][0].get('build', []) or dip[0])]
        RESULTS['x5']['overshoot_frames'] = sorted(over)
        self.assertTrue(over and over <= set(dip[0]), over)
        self.assertTrue(str(s['deliver']).startswith('carved'), s)
        objects, ctx, W2, rep = run(b, M, 'x5_no_exclusion', lathe=dict(A=AXIS, B=AXIS), no_overshoot=True)
        s2 = summary(W2); RESULTS['x5_no_exclusion']['summary'] = s2; _save()
        log('x5 no exclusion', json.dumps(s2, default=IL._jdefault)[:2000])
        self.assertIn('S', s2['failing'] or [], s2)


class Routes(unittest.TestCase):
    def test_x8_plate_never_lathe(self):
        plate = trimesh.creation.box(extents=[0.23, 0.125, 0.008])
        b = episode(plate, trimesh.creation.box(extents=[0.02] * 3), lambda f: np.eye(4) @ np.diag([1, 1, 1, 1.0]) +
                    np.array([[0, 0, 0, 0.5], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]), 6, [], jitter=False)
        ev = IL.Evidence(b, 'A', plate, sub=False)
        r = CP.route_pieces(plate, ev, 82, lathe_axis=([0, 0, 0], [0, 0, 1.0]), lathe_ok=True, plate_like=True,
                            sigma=0.001, skip=('3',))
        RESULTS['x8_plate'] = dict(route=r['route'], tried=[t['route'] for t in r['tried']],
                                   lathe_skipped=[t.get('skipped') for t in r['tried']])
        self.assertNotEqual(r['route'], '2_lathe')
        self.assertTrue(any(t['route'] == '2_lathe' and t.get('skipped') for t in r['tried']), r['tried'])

    def test_x8_folded_sheet(self):
        a = trimesh.creation.box(extents=[0.10, 0.08, 0.004]); a.apply_translation([0.05, 0, 0])
        a.apply_transform(trimesh.transformations.rotation_matrix(math.radians(30), [0, 1, 0]))
        c = a.copy(); c.apply_transform(trimesh.transformations.rotation_matrix(math.pi, [0, 0, 1]))
        sheet = trimesh.boolean.union([a, c], engine='manifold')
        b = episode(sheet, trimesh.creation.box(extents=[0.02] * 3), lambda f: np.array(
            [[1, 0, 0, 0.5], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1.0]]), 6, [], jitter=False)
        ev = IL.Evidence(b, 'A', sheet, sub=False)
        r = CP.route_pieces(sheet, ev, 82, lathe_axis=([0, 0, 0], [0, 0, 1.0]), lathe_ok=True, plate_like=False,
                            sigma=0.001)
        rows = [dict(route=t['route'], gate=t.get('gate'), why=(t.get('report') or {}).get('why')) for t in r['tried']]
        RESULTS['x8_sheet'] = dict(route=r['route'], tried=rows)
        _save()
        log('x8 sheet', json.dumps(RESULTS['x8_sheet'], default=IL._jdefault)[:2000])
        self.assertNotEqual(r['route'], '2_lathe', rows)
        self.assertTrue(rows[0]['route'] == '2_lathe' and not (rows[0]['gate'] or {}).get('pass_', False), rows)

    def test_x9_ring(self):
        host = cup()
        L, info = CP.Lathe.from_mesh(host, *AXIS, 0.001)
        p0 = L.pieces(16); c0 = CP.continuity(L, L.hulls(p0), p0)
        p1 = L.pieces(16, ring_gap_m=0.001); c1 = CP.continuity(L, L.hulls(p1), p1)
        RESULTS['x9'] = dict(builder=c0, forced_ring=c1)
        self.assertTrue(c0['ok'], c0)
        self.assertFalse(c1['ok'], c1)

    def test_x11_open_box(self):
        outer = trimesh.creation.box(extents=[0.16, 0.12, 0.08])
        inner = trimesh.creation.box(extents=[0.152, 0.112, 0.08]); inner.apply_translation([0, 0, 0.006])
        box = trimesh.boolean.difference([outer, inner], engine='manifold')
        b = episode(box, trimesh.creation.box(extents=[0.02] * 3), lambda f: np.array(
            [[1, 0, 0, 0.5], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1.0]]), 6, [], jitter=False)
        ev = IL.Evidence(b, 'A', box, sub=False)
        r = CP.route_pieces(box, ev, 82, lathe_ok=False, sigma=0.001)
        centre_in = bool(CP.Hulls(r['hulls']).inside(np.array([[0, 0, 0.01], [0, 0, 0.03], [0.05, 0.03, 0.02]])).any())
        RESULTS['x11'] = dict(route=r['route'], n=len(r['hulls']), gate=r['gate'], opening_point_inside=centre_in,
                              tried=[dict(route=t['route'], gate=t.get('gate'), rep=t.get('report'))
                                     for t in r['tried']])
        _save()
        log('x11', json.dumps(RESULTS['x11'], default=IL._jdefault)[:2000])
        self.assertEqual(r['route'], '3_coacd', RESULTS['x11'])
        self.assertTrue(r['gate']['pass_'])
        self.assertFalse(centre_in)


class Controls(unittest.TestCase):
    def _boxes(self, pose, T, contact, key):
        A = trimesh.creation.box(extents=[0.15, 0.15, 0.03])
        Bm = trimesh.creation.box(extents=[0.08, 0.08, 0.04])
        b = episode(A, Bm, pose, T, contact, table_z=-0.015, jitter=False)
        objects, ctx, W, rep = run(b, dict(A=A, B=Bm), key, physics=False, force_route=dict(A=('3',), B=('3',)))
        return W, rep

    def test_x7_n2_resting(self):
        def pose(f):
            M = np.eye(4); M[2, 3] = 0.015 + 0.02 - 0.006; return M
        W, rep = self._boxes(pose, 40, list(range(40)), 'x7_n2')
        RESULTS['x7_n2']['summary'] = dict(in_scope=W.get('in_scope'), gates=W.get('gates'))
        self.assertFalse(W.get('in_scope'), W.get('gates'))

    def test_x7_n4_transient(self):
        def pose(f):
            M = np.eye(4); M[2, 3] = 0.035 - (0.008 if 10 <= f < 13 else -0.05); return M
        W, rep = self._boxes(pose, 30, [10, 11, 12], 'x7_n4')
        self.assertFalse(W.get('in_scope'), W)

    def test_x7_wander(self):
        rng = np.random.default_rng(5)
        pos = rng.uniform(-0.06, 0.06, (40, 2))

        def pose(f):
            M = np.eye(4); M[:2, 3] = pos[f]; M[2, 3] = 0.015 + 0.02 - 0.003; return M
        W, rep = self._boxes(pose, 40, list(range(40)), 'x7_wander')
        self.assertFalse(W.get('in_scope') and str(W.get('deliver', '')).startswith('carved'), W)


class Plates(unittest.TestCase):
    def test_x6_plate_pair_and_x10_flag_off(self):
        """x6: a plate pair is left to F-I4 (records identical with and without the F-I5 context); x10: decide_pair
        without the context is the F-I1..F-I3 path (identical records for waiver_fi5 omitted and None)."""
        A = trimesh.creation.box(extents=[0.23, 0.125, 0.01])
        Bm = trimesh.creation.box(extents=[0.23, 0.125, 0.01])
        Rb = np.array([[0, 0, -1.0], [0, 1.0, 0], [1.0, 0, 0]])

        def pose(f):
            M = np.eye(4); M[:3, :3] = Rb; M[1, 3] = max(0.12 - f * 0.002, 0.0); return M
        b = episode(A, Bm, pose, 90, list(range(90)), table_z=-0.2)
        objects = objects_for(b, dict(A=A, B=Bm), plate=dict(A=True, B=True), force_route=dict(A=('3',), B=('3',)))

        def sides():
            s = {}
            for t, q in (('A', 'B'), ('B', 'A')):
                evc = CC.collider_evidence(b, t, objects[t]['hulls'], mesh=objects[t]['body'])
                intr = CC.intrusions_colliders(b, t, q, evc, CC.collider_samples(objects[q]['hulls']),
                                               b.contact(t, q)['contact'])
                s[t] = IL.make_side(b, t, q, evc, intr, b.contact(t, q)['contact'], sources={}, identity='eval',
                                    partner_collider=CC.collider_samples(objects[q]['hulls']))
            return s
        s = sides()
        r0 = [IL.public(r) for r in IL.decide_pair(b, s['A'], s['B'])]
        s = sides()
        r1 = [IL.public(r) for r in IL.decide_pair(b, s['A'], s['B'], waiver_fi5=None)]
        s = sides()
        ctx = CC.FI5(b, objects, copies=COPIES, log=log, physics=False)
        r2 = [IL.public(r) for r in IL.decide_pair(b, s['A'], s['B'], waiver_fi5=ctx)]
        strip = (lambda rs: [{k: v for k, v in r.items() if k != 'waiver_fi5'} for r in rs])
        RESULTS['x6_x10'] = dict(n=len(r0), decisions=[r['decision'] for r in r0],
                                 same_off=r0 == r1, same_plate=strip(r2) == r0,
                                 scope=ctx.results[('A', 'B')].get('scope'))
        _save()
        self.assertEqual(r0, r1)
        self.assertEqual(strip(r2), r0)
        self.assertIn('plate pair', ctx.results[('A', 'B')].get('scope', ''))


class Others(unittest.TestCase):
    def test_lidpot(self):
        pot = trimesh.boolean.difference([trimesh.creation.cylinder(0.100, 0.120, sections=96).apply_translation(
            [0, 0, 0.060]), trimesh.creation.cylinder(0.096, 0.120, sections=96).apply_translation([0, 0, 0.066])],
            engine='manifold')
        lid = trimesh.creation.cylinder(0.102, 0.004, sections=96)
        T = 80
        z = 0.120 + 0.002 - 0.0006

        def pose(f):
            M = np.eye(4); M[2, 3] = z if f >= 10 else z + 0.05
            M[0, 3] = 0.030 * max(0.0, 1 - (f - 10) / 30.0) if f >= 10 else 0.03
            return M
        b = episode(pot, lid, pose, T, list(range(10, T)))
        objects, ctx, W, rep = run(b, dict(A=pot, B=lid), 'lidpot', force_route=dict(A=('2',), B=('2',)))
        s = summary(W); RESULTS['lidpot']['summary'] = s; _save()
        log('lidpot', json.dumps(s, default=IL._jdefault)[:3000])
        self.assertIsNotNone(W.get('in_scope'))

    def test_rack(self):
        base = trimesh.creation.box(extents=[0.20, 0.10, 0.010]).apply_translation([0, 0, 0.005])
        p1 = trimesh.creation.box(extents=[0.012, 0.10, 0.09]).apply_translation([-0.048, 0, 0.055])
        p2 = trimesh.creation.box(extents=[0.012, 0.10, 0.09]).apply_translation([0.048, 0, 0.055])
        rack = trimesh.boolean.union([base, p1, p2], engine='manifold')
        c = cup()
        T = 90
        # cup rests on the base plate (z = 0.010); its outer radius at mid height ~ 37.5 mm; the prong faces at
        # x = +-0.042; the track puts the cup 5.5 mm towards +x: about 1 mm into the +x prong over its upper part
        pose = nest_motion(0.010, T, n_far=14, n_slow=40, z_top=0.20, slow_mm=60.0, offset=(0.0055, 0.0))

        def pose2(f):
            M = pose(f); M[0, 3] = 0.0055; return M
        b = episode(rack, c, pose2, T, list(range(10, T)))
        objects, ctx, W, rep = run(b, dict(A=rack, B=c), 'rack', lathe=dict(B=AXIS))
        s = summary(W); RESULTS['rack']['summary'] = s; _save()
        log('rack', json.dumps(s, default=IL._jdefault)[:3000])
        self.assertIsNotNone(W.get('in_scope'))

    def test_sweeper(self):
        blk = trimesh.creation.box(extents=[0.06, 0.06, 0.06]).apply_translation([0, 0, 0.03])
        hole = trimesh.creation.box(extents=[0.022, 0.022, 0.06]).apply_translation([0, 0, 0.02 + 0.03])
        holder = trimesh.boolean.difference([blk, hole], engine='manifold')
        stick = trimesh.creation.box(extents=[0.020, 0.020, 0.200]).apply_translation([0, 0, 0.100])
        T = 90
        pose = nest_motion(0.020 - 0.0005, T, n_far=14, n_slow=40, z_top=0.25, slow_mm=45.0)

        def pose2(f):
            M = pose(f); M[0, 3] = 0.002; return M
        b = episode(holder, stick, pose2, T, list(range(10, T)))
        objects, ctx, W, rep = run(b, dict(A=holder, B=stick), 'sweeper')
        s = summary(W); RESULTS['sweeper']['summary'] = s; _save()
        log('sweeper', json.dumps(s, default=IL._jdefault)[:3000])
        self.assertIsNotNone(W.get('in_scope'))


def tearDownModule():
    _save()
    print('results ->', OUT)


if __name__ == '__main__':
    unittest.main(verbosity=2)
