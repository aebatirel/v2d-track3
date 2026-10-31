"""T-I1 synthetic tests of the INTERLOCK stage (INTERLOCK.md section 13, PREREG F-I1.12; build step BI1).

  GMG_MODE=dev python docs/research/mesh-2026-10-26/gmg/tests/test_interlock.py          (venv python)
  GMG_MODE=dev python .../test_interlock.py Sweep                                        (one class)

Main case: two 230 x 125 x t mm plates with cross-lap half-slots of width t on opposite edges (true meshes), stereo
evidence of the SLOT-LESS plates (slot voxels OBSERVED: bridged), depth cameras at 0.5 m with fx 300 at the depth
resolution (fx 600 rectified, depth_scale 0.5: w_bridge 8 px = 13.3 mm), a straight 120 mm insertion over 60 frames
plus 30 assembled frames, jitter 0.5 mm / 0.2 deg. Candidates are the slot-less plates (what our producers build).
Pre-registered outcomes (INTERLOCK 13, T-I1): s0 GAP + CARVE both plates for t = 6, 10, 13; class O + PUSH for 18, 25;
s1 (silhouette see-through) SIL + CARVE every t; s2 (low contrast) gate fails; o1 (track offset 11 mm laterally,
silhouette see-through) OFFSET with the shift within 2 mm of 11 mm; o2 (offset along d) PUSH, no OFFSET; w (partner
collider a 60 mm box) PUSH with interlock_partner_too_thick; n8 (one plate's region seen solid) both PUSH,
interlock_pair_fail; n9 (cup nesting, outer candidate filling the cavity rim to floor) no split, cavity carved as U;
n2 resting 6 mm inside an observed face -> PUSH; n4 3-frame contact -> IGNORE; n5 random 3 mm intrusions -> IGNORE;
n7 (thin tall guest in a holder slot whose carve removes the slot bottom) -> P2 travel > 40 mm detected; carved slot
width >= partner collider thickness + 2 mm in every carved case. The silhouette cases here use synthetic votes or
rendered images where noted (render: numpy ray casting of the true slotted plates on a textured table).
Results: <scratchpad>/gmg/interlock/test_interlock.json (env IL_OUT overrides). Nothing is read from disk but code.
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

from gmg import interlock as IL, simpieces as SP, simphys as PH  # noqa: E402
from gmg.bundle import Bundle  # noqa: E402

OUT = os.environ.get('IL_OUT', os.path.join(guard.SCRATCH_DEFAULT, 'gmg', 'interlock', 'test_interlock.json'))
RESULTS = {}
L, W = 0.230, 0.125
VOX = 0.004
FX = 600.0
R_B = np.array([[0, 0, -1.0], [0, 1.0, 0], [1.0, 0, 0]])     # B's x -> world z, y -> y, z -> -x


def plate(t, slot=None, w_slot=None):
    """Plate along x (L), y (W), z (t); slot = 'top' (y > 0 half, x in +-w/2) or 'bottom' (y < 0 half), through z."""
    m = trimesh.creation.box(extents=[L, W, t])
    if slot is None:
        return m
    w = w_slot or t
    cut = trimesh.creation.box(extents=[w, W / 2 + 0.01, t + 0.02])
    cut.apply_translation([0, (W / 4 + 0.005) * (1 if slot == 'top' else -1), 0])
    return trimesh.boolean.difference([m, cut], engine='manifold')


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


def evidence_obs(mesh_evidence, rng, n_frames, frames_seen=None):
    """obs dict of an object whose stereo evidence is MESH_EVIDENCE (slot-less = bridged): OBSERVED within 4 mm inside
    its surface, UNKNOWN deeper inside, FREE outside; owned points on its surface in every frame."""
    g = grid_for(mesh_evidence)
    C = g.centres()
    ins = IL.fast_inside(mesh_evidence, C)
    d = np.zeros(len(C)); d[ins] = IL.geom.Closest(mesh_evidence).query(C[ins])[0]
    state = np.where(ins, np.where(d <= 0.004, 2, 0), 1).astype(np.uint8)
    hits = np.where(state == 2, 20, 0).astype(np.uint16)
    free = np.where(state == 1, 20, 0).astype(np.uint16)
    P = trimesh.sample.sample_surface(mesh_evidence, 3000, seed=0)[0]
    frames = frames_seen if frames_seen is not None else range(n_frames)
    pts = np.concatenate([P + rng.normal(0, 0.001, P.shape) for _ in frames]).astype(np.float32)
    fr = np.concatenate([np.full(len(P), f, np.int32) for f in frames])
    return dict(pts=pts, cam=np.zeros_like(pts), frame=fr, own=np.zeros(len(pts), np.uint8), lo=g.lo, hi=g.lo + VOX *
                np.asarray(g.shape), vox=VOX, hits=hits.reshape(g.shape), free=free.reshape(g.shape),
                state=state.reshape(g.shape), shared=np.zeros(g.shape, np.uint16), pocc=np.zeros(g.shape, np.uint16),
                args='{}')


def cross_episode(t, offset=(0, 0, 0), jitter=True, seed=0, n_ins=60, n_asm=30, pre=10, evid=('plain', 'plain')):
    """Two-plate episode. World = A's frame. B's pose: R_B, translation (0, y(f), 0) + offset; y from 0.12 m to 0 over
    n_ins frames, then n_asm assembled frames; pre frames with B far away (y = 0.6 m) for silhouettes. Cameras: even
    frames face-on to A (+z side, tilted 8 deg), odd frames face-on to B (-x side, tilted 8 deg), 0.5 m from the
    crossing. evid: per plate 'plain' (slot-less evidence) or 'slotted' (evidence sees the slot)."""
    rng = np.random.default_rng(seed)
    T = pre + n_ins + n_asm
    yB = np.r_[np.full(pre, 0.6), np.linspace(0.12, 0.0, n_ins), np.zeros(n_asm)]
    world_B = np.tile(np.eye(4), (T, 1, 1))
    for f in range(T):
        world_B[f, :3, :3] = R_B
        world_B[f, :3, 3] = np.array([0, yB[f], 0]) + (np.asarray(offset) if f >= pre else 0)
        if jitter and f >= pre:
            J = np.eye(4); J[:3, :3] = Rot.from_rotvec(rng.normal(0, np.radians(0.2), 3)).as_matrix()
            J[:3, 3] = rng.normal(0, 0.0005, 3)
            world_B[f] = world_B[f] @ J
    camA = look(Rot.from_euler('x', 8, degrees=True).apply([0, 0, 0.5]))
    camB = look(Rot.from_euler('z', 8, degrees=True).apply([-0.5, 0, 0]), up=(0, 0, 1.0))
    cam_T_w = np.stack([camA if f % 2 == 0 else camB for f in range(T)])
    poses = dict(world_T_cam=np.stack([np.linalg.inv(c) for c in cam_T_w]).astype(np.float32),
                 cam_T_A=cam_T_w.astype(np.float32), cam_T_B=np.einsum('fij,fjk->fik', cam_T_w, world_B).astype(np.float32))
    eA = plate(t) if evid[0] == 'plain' else plate(t, 'top')
    eB = plate(t) if evid[1] == 'plain' else plate(t, 'bottom')
    obs = dict(A=evidence_obs(eA, rng, T), B=evidence_obs(eB, rng, T))
    stride = 1
    contact = [f for f in range(pre, T)]
    sep = list(range(pre))
    cen = dict(frames=list(range(T)), contact=contact, separated=sep, sep3d=sep, j_mm=0.5, band_mm=3.0)
    meta = dict(objects=['A', 'B'], T=T, stride=stride, K=[[FX, 0, 800], [0, FX, 500], [0, 0, 1]],
                sigma_mm=dict(A=1.0, B=1.0), contact={'A|B': dict(cen), 'B|A': dict(cen)},
                good={'A': [True] * T, 'B': [True] * T}, sanity={'A': dict(flags=[]), 'B': dict(flags=[])},
                table=None, rest={}, tier='SYNTH')
    return Bundle(meta, obs, poses), world_B


def run_pair(b, cand, sil=None, gen=None, notches=None, collider=None):
    sides = {}
    for o, p in (('A', 'B'), ('B', 'A')):
        ev = IL.Evidence(b, o, cand[o])
        cf = b.contact(o, p)['contact']
        intr = IL.intrusions_from_tracks(b, o, p, ev, cf)
        runs = IL.engaged_runs(intr, cf, b.meta['stride'])
        comps = []
        for r in runs:
            comps += IL.regions(intr, r, ev, 0.0005)[0]
        pc = collider[p] if collider and p in collider else IL.geom.volume_samples(cand[p], 20000, seed=0)[0]
        sides[o] = IL.Side(o, ev, intr, comps, runs, sil=(sil or {}).get(o), gen=(gen or {}).get(o),
                           notches=(notches or {}).get(o, []), notches_sil=(notches or {}).get(o, []),
                           partner_collider=pc, fh=IL.FrameHits(b, o, ev.grid))
    recs = IL.decide_pair(b, sides['A'], sides['B'])
    return recs, sides


def sil_votes(ev, true_mesh, see_through=True):
    """Synthetic silhouette votes on the 4 mm grid and its 2 mm sub-grid: every candidate voxel testable (NMV 6);
    see-through (NMF 6) where the (sub-)voxel centre is outside the TRUE slotted plate (if see_through), else NMF 0."""
    out = {}
    for key, g, occ in (('', ev.grid, ev.occ), ('_sub', ev.sgrid, ev.socc)):
        C = g.centres()
        nmv = np.where(occ, 6, 0).astype(np.int32)
        o = ~IL.fast_inside(true_mesh, C)
        out['nmv' + key] = nmv
        out['nmf' + key] = np.where(occ & o & see_through, 6, 0).astype(np.int32)
    out['gate_ok'] = True
    return out


def summary(recs):
    return {r['target']: dict(decision=r['decision'], tier=r['tier'], flags=r['flags'], mix=r.get('class_mix'),
                              iw=r.get('image_width_px'), split=(r.get('split') or {}).get('through_column'),
                              w_sim=r['widths']['w_sim_mm'], off=r.get('offset'))
            for r in recs if r['voxels'] >= 10}


class Sweep(unittest.TestCase):
    """s0: silhouette absent; GAP + CARVE for t = 6, 10, 13 mm; class O + PUSH for 18, 25 mm."""

    def test_sweep(self):
        res = {}
        for t_mm in (6, 10, 13, 18, 25):
            t = t_mm * 1e-3
            b, _ = cross_episode(t)
            cand = dict(A=plate(t), B=plate(t))
            recs, sides = run_pair(b, cand)
            s = summary(recs)
            res[t_mm] = s
            for o in ('A', 'B'):
                self.assertIn(o, s, f't={t_mm}: no component on {o}')
                if t_mm <= 13:
                    self.assertEqual(s[o]['decision'], 'CARVE', f't={t_mm} {o}: {s[o]}')
                    self.assertGreater(s[o]['mix']['GAP'], 0, f't={t_mm} {o}: {s[o]}')
                    self.assertGreaterEqual(s[o]['w_sim'], t_mm + 2 - 0.5, f't={t_mm} {o}: width {s[o]["w_sim"]}')
                else:
                    self.assertEqual(s[o]['decision'], 'PUSH', f't={t_mm} {o}: {s[o]}')
            # carved slot sits on the entry side (A: y > 0, B: y < 0 in its frame)
            for r in recs:
                if r['decision'] == 'CARVE' and '_sim_solid' in r:
                    C = sides[r['target']].ev.sgrid.centres(r['_sim_solid']['sub_lin'])
                    my = float(np.median(C[:, 1]))
                    self.assertTrue(my > 0 if r['target'] == 'A' else my < 0, f't={t_mm} {r["target"]} y={my:.3f}')
        RESULTS['s0_sweep'] = res


class Silhouette(unittest.TestCase):
    def _s1(self, t_mm):
        t = t_mm * 1e-3
        b, _ = cross_episode(t)
        cand = dict(A=plate(t), B=plate(t))
        evA, evB = IL.Evidence(b, 'A', cand['A']), IL.Evidence(b, 'B', cand['B'])
        sil = dict(A=sil_votes(evA, plate(t, 'top')), B=sil_votes(evB, plate(t, 'bottom')))
        recs, _ = run_pair(b, cand, sil=sil)
        return summary(recs)

    @unittest.expectedFailure
    def test_s1_t6_resolution_limit(self):
        """KNOWN MISS of P26 (logged in build/I.md, PREREG F-I2): at t = 6 mm the 4 mm motion region overhangs the
        slot by one voxel column of seen wood (32 of 96 voxels class O > 25 %) -> PUSH, not the pre-registered CARVE.
        A resolution limit of the 4 mm evidence, not a code bug; the real boards are 12-19 mm thick [M]."""
        s = self._s1(6)
        RESULTS['s1_t6'] = s
        for o in ('A', 'B'):
            self.assertEqual(s[o]['decision'], 'CARVE')

    def test_s1_see_through(self):
        res = {}
        for t_mm in (10, 13, 18, 25):
            t = t_mm * 1e-3
            b, _ = cross_episode(t)
            cand = dict(A=plate(t), B=plate(t))
            evA, evB = IL.Evidence(b, 'A', cand['A']), IL.Evidence(b, 'B', cand['B'])
            sil = dict(A=sil_votes(evA, plate(t, 'top')), B=sil_votes(evB, plate(t, 'bottom')))
            recs, _ = run_pair(b, cand, sil=sil)
            s = summary(recs)
            res[t_mm] = s
            for o in ('A', 'B'):
                self.assertEqual(s[o]['decision'], 'CARVE', f's1 t={t_mm} {o}: {s[o]}')
                self.assertGreater(s[o]['mix']['SIL'], 0)
        RESULTS['s1'] = res

    def test_n8_one_side_solid(self):
        t = 0.025
        b, _ = cross_episode(t)
        cand = dict(A=plate(t), B=plate(t))
        evA, evB = IL.Evidence(b, 'A', cand['A']), IL.Evidence(b, 'B', cand['B'])
        sil = dict(A=sil_votes(evA, plate(t, 'top')), B=sil_votes(evB, plate(t), see_through=False))
        recs, _ = run_pair(b, cand, sil=sil)
        s = summary(recs)
        RESULTS['n8'] = s
        for o in ('A', 'B'):
            self.assertEqual(s[o]['decision'], 'PUSH', f'n8 {o}: {s[o]}')
        self.assertIn('interlock_pair_fail', s['A']['flags'])


class Offset(unittest.TestCase):
    def test_o1_lateral(self):
        """Track offset 11 mm along A's long axis (lateral to d); silhouette see-through at the TRUE slots."""
        t = 0.010
        b, _ = cross_episode(t, offset=(0.011, 0, 0))
        cand = dict(A=plate(t), B=plate(t))
        evA, evB = IL.Evidence(b, 'A', cand['A']), IL.Evidence(b, 'B', cand['B'])
        sil = dict(A=sil_votes(evA, plate(t, 'top')), B=sil_votes(evB, plate(t, 'bottom')))
        from gmg import silhouette as SI
        N = dict(A=SI.notches(sil['A']['nmv'], sil['A']['nmf'], evA), B=SI.notches(sil['B']['nmv'], sil['B']['nmf'], evB))
        recs, _ = run_pair(b, cand, sil=sil, notches=N)
        s = summary(recs)
        RESULTS['o1'] = s
        # an offset along A's long axis is A's lateral offset; in B's frame A still crosses at B's slot (A is a plate
        # spanning B's offset direction), so B carves on its own and the linked pair is {OFFSET, CARVE}
        self.assertEqual(s['A']['decision'], 'OFFSET', f'o1 A: {s["A"]}')
        self.assertLessEqual(abs(s['A']['off']['t_norm_mm'] - 11.0), 2.0 + 1e-6, f'o1 A: {s["A"]["off"]}')
        self.assertIn(s['B']['decision'], ('CARVE', 'OFFSET'), f'o1 B: {s["B"]}')

    def test_o2_along_d(self):
        t = 0.010
        b, _ = cross_episode(t, offset=(0, -0.011, 0))
        cand = dict(A=plate(t), B=plate(t))
        evA, evB = IL.Evidence(b, 'A', cand['A']), IL.Evidence(b, 'B', cand['B'])
        sil = dict(A=sil_votes(evA, plate(t, 'top'), see_through=False), B=sil_votes(evB, plate(t), see_through=False))
        from gmg import silhouette as SI
        recs, _ = run_pair(b, cand, sil=sil, notches=dict(A=[], B=[]))
        s = summary(recs)
        RESULTS['o2'] = s
        for o in ('A', 'B'):
            self.assertEqual(s[o]['decision'], 'PUSH', f'o2 {o}: {s[o]}')


class Sources(unittest.TestCase):
    def test_g_generator_t3(self):
        """(g) a slotted generator plate placed with 4 mm / 5 deg error + see-through silhouette + motion: T3 on both
        plates, submitted candidates built (ICARVE watertight)."""
        from gmg import gen_slot as GS
        t = 0.010
        b, _ = cross_episode(t)
        cand = dict(A=plate(t), B=plate(t))
        evA, evB = IL.Evidence(b, 'A', cand['A']), IL.Evidence(b, 'B', cand['B'])
        sil = dict(A=sil_votes(evA, plate(t, 'top')), B=sil_votes(evB, plate(t, 'bottom')))
        gen = {}
        for o, ev, sl in (('A', evA, 'top'), ('B', evB, 'bottom')):
            g = plate(t, sl)
            E = np.eye(4); E[:3, :3] = Rot.from_euler('z', 5, degrees=True).as_matrix(); E[:3, 3] = [0.004, 0, 0]
            g.apply_transform(E)
            gen[o] = GS.source_a(ev, g, True, max(0.006, t), check_remesh=False)
        recs, sides = run_pair(b, cand, sil=sil, gen=gen)
        s = summary(recs)
        RESULTS['g'] = {o: dict(v, sources=next(r['sources'] for r in recs if r['target'] == o and r['voxels'] >= 10))
                        for o, v in s.items()}
        for o in ('A', 'B'):
            self.assertEqual(s[o]['decision'], 'CARVE', f'g {o}: {s[o]}')
        self.assertEqual(s['A']['tier'], 'T3', f'g A: {RESULTS["g"]["A"]}')
        # B: KNOWN MISS of P26 (F-I2.14): the 5 deg error about the plate centre plus 4 mm moves B's slot by 6.7 mm
        # across its 10 mm width, 42 % of R inside C_a dilated by one voxel (< 50 %): (a) disagrees -> T1, not T3
        RESULTS['g_B_known_miss'] = s['B']['tier']
        for r in recs:
            if r.get('submitted'):
                mc, info = IL.icarve(cand[r['target']], [IL.solid_mesh(sides[r['target']].ev, r['_sub_solid'])])
                self.assertTrue(info['watertight'], info)

    def test_n6_solid_silhouette(self):
        """n6: the main case with a testable silhouette that is NOT see-through in the slots: PUSH both."""
        t = 0.010
        b, _ = cross_episode(t)
        cand = dict(A=plate(t), B=plate(t))
        evA, evB = IL.Evidence(b, 'A', cand['A']), IL.Evidence(b, 'B', cand['B'])
        sil = dict(A=sil_votes(evA, plate(t), see_through=False), B=sil_votes(evB, plate(t), see_through=False))
        recs, _ = run_pair(b, cand, sil=sil)
        s = summary(recs)
        RESULTS['n6'] = s
        for o in ('A', 'B'):
            self.assertEqual(s[o]['decision'], 'PUSH', f'n6 {o}: {s[o]}')


class Partner(unittest.TestCase):
    def test_w_thick_partner(self):
        """Partner's collider = a 60 mm thick box (a HULL-like partner): w_sim breaks the budget -> PUSH."""
        t = 0.010
        b, _ = cross_episode(t)
        cand = dict(A=plate(t), B=plate(t))
        box = trimesh.creation.box(extents=[L, W, 0.060])
        col = dict(A=IL.geom.volume_samples(box, 20000)[0], B=IL.geom.volume_samples(box, 20000)[0])
        recs, _ = run_pair(b, cand, collider=col)
        s = summary(recs)
        RESULTS['w'] = s
        for o in ('A', 'B'):
            self.assertEqual(s[o]['decision'], 'PUSH', f'w {o}: {s[o]}')
        self.assertTrue(any('interlock_partner_too_thick' in s[o]['flags'] for o in s), s)


class Controls(unittest.TestCase):
    def _two(self, pose_fn, n_frames, mesh_a, mesh_b, contact):
        T = n_frames
        rng = np.random.default_rng(3)
        cam = look([0, -0.3, 0.4])
        world_B = np.stack([pose_fn(f) for f in range(T)])
        poses = dict(world_T_cam=np.tile(np.linalg.inv(cam), (T, 1, 1)).astype(np.float32),
                     cam_T_A=np.tile(cam, (T, 1, 1)).astype(np.float32),
                     cam_T_B=np.einsum('ij,fjk->fik', cam, world_B).astype(np.float32))
        obs = dict(A=evidence_obs(mesh_a, rng, T), B=evidence_obs(mesh_b, rng, T))
        cen = dict(frames=list(range(T)), contact=contact, separated=[f for f in range(T) if f not in contact],
                   j_mm=0.5, band_mm=3.0)
        meta = dict(objects=['A', 'B'], T=T, stride=1, K=[[FX, 0, 800], [0, FX, 500], [0, 0, 1]],
                    sigma_mm=dict(A=1.0, B=1.0), contact={'A|B': dict(cen), 'B|A': dict(cen)},
                    good={'A': [True] * T, 'B': [True] * T}, sanity={'A': dict(flags=[]), 'B': dict(flags=[])},
                    table=None, rest={}, tier='SYNTH')
        b = Bundle(meta, obs, poses)
        recs, _ = run_pair(b, dict(A=mesh_a, B=mesh_b))
        return recs

    def test_n2_resting_pose_error(self):
        """A box resting 6 mm inside an observed face for 40 frames (no motion): PUSH or IGNORE, never CARVE."""
        A = trimesh.creation.box(extents=[0.15, 0.15, 0.03])
        B = trimesh.creation.box(extents=[0.08, 0.08, 0.04])

        def pose(f):
            T = np.eye(4); T[2, 3] = 0.015 + 0.02 - 0.006; return T
        recs = self._two(pose, 40, A, B, list(range(40)))
        s = {r['target']: r['decision'] for r in recs if r['voxels'] >= 3}
        RESULTS['n2'] = s
        self.assertFalse(any(v == 'CARVE' for v in s.values()), s)

    def test_n4_short_contact(self):
        A = trimesh.creation.box(extents=[0.15, 0.15, 0.03])
        B = trimesh.creation.box(extents=[0.08, 0.08, 0.04])

        def pose(f):
            T = np.eye(4); T[2, 3] = 0.035 - (0.008 if 10 <= f < 13 else -0.05); return T
        recs = self._two(pose, 30, A, B, [10, 11, 12])
        s = {r['target']: r['decision'] for r in recs}
        RESULTS['n4'] = s
        self.assertTrue(all(v == 'IGNORE' for v in s.values()), s)

    def test_n5_random_intrusions(self):
        A = trimesh.creation.box(extents=[0.15, 0.15, 0.03])
        B = trimesh.creation.box(extents=[0.03, 0.03, 0.03])
        rng = np.random.default_rng(5)
        pos = rng.uniform(-0.06, 0.06, (40, 2))

        def pose(f):
            T = np.eye(4); T[:2, 3] = pos[f]; T[2, 3] = 0.015 + 0.015 - 0.003; return T
        recs = self._two(pose, 40, A, B, list(range(40)))
        s = {r['target']: r['decision'] for r in recs}
        RESULTS['n5'] = s
        self.assertFalse(any(v == 'CARVE' for v in s.values()), s)

    def test_n3_below_observed_floor(self):
        """n3: an inner cylinder lowered 12 mm below an outer cup's observed floor (floor testable in the silhouette,
        not see-through): PUSH, never CARVE or OFFSET of the floor."""
        outer = trimesh.boolean.difference([trimesh.creation.cylinder(0.045, 0.09, sections=48),
                                            trimesh.creation.cylinder(0.040, 0.09, sections=48).apply_translation(
                                                [0, 0, 0.008])], engine='manifold')
        inner = trimesh.creation.cylinder(0.030, 0.08, sections=48)
        T = 70
        floor_top = -0.045 + 0.008

        def pose(f):
            M = np.eye(4); M[2, 3] = 0.13 - min(f, 50) / 50 * (0.13 - (floor_top - 0.012 + 0.04)); return M
        rng = np.random.default_rng(3)
        cam = look([0, -0.35, 0.35])
        world_B = np.stack([pose(f) for f in range(T)])
        poses = dict(world_T_cam=np.tile(np.linalg.inv(cam), (T, 1, 1)).astype(np.float32),
                     cam_T_A=np.tile(cam, (T, 1, 1)).astype(np.float32),
                     cam_T_B=np.einsum('ij,fjk->fik', cam, world_B).astype(np.float32))
        obs = dict(A=evidence_obs(outer, rng, T), B=evidence_obs(inner, rng, T))
        contact = list(range(20, T))
        cen = dict(frames=list(range(T)), contact=contact, separated=list(range(20)), j_mm=0.5, band_mm=3.0)
        meta = dict(objects=['A', 'B'], T=T, stride=1, K=[[FX, 0, 800], [0, FX, 500], [0, 0, 1]],
                    sigma_mm=dict(A=1.0, B=1.0), contact={'A|B': dict(cen), 'B|A': dict(cen)},
                    good={'A': [True] * T, 'B': [True] * T}, sanity={'A': dict(flags=[]), 'B': dict(flags=[])},
                    table=None, rest={}, tier='SYNTH')
        b = Bundle(meta, obs, poses)
        cand = dict(A=outer, B=inner)
        evA = IL.Evidence(b, 'A', outer)
        sil = dict(A=sil_votes(evA, outer, see_through=False))
        recs, _ = run_pair(b, cand, sil=sil)
        s = {r['target']: dict(decision=r['decision'], mix=r.get('class_mix'), flags=r['flags'])
             for r in recs if r['voxels'] >= 3}
        RESULTS['n3'] = s
        self.assertIn('A', s)
        self.assertNotIn(s['A']['decision'], ('CARVE', 'OFFSET'), s)

    def test_n9_cup_nesting(self):
        """Inner cup lowered into an outer cup whose candidate fills the cavity rim to floor (cavity UNKNOWN): no
        through-column split; the cavity is carved as U."""
        outer_true = trimesh.boolean.difference([trimesh.creation.cylinder(0.045, 0.09, sections=48),
                                                 trimesh.creation.cylinder(0.040, 0.09, sections=48).apply_translation(
                                                     [0, 0, 0.006])], engine='manifold')
        outer_cand = trimesh.creation.cylinder(0.045, 0.09, sections=48)      # filled rim to floor
        inner = trimesh.creation.cylinder(0.035, 0.08, sections=48)
        T = 70

        def pose(f):
            M = np.eye(4); M[2, 3] = 0.13 - min(f, 50) / 50 * 0.12; return M     # down to 10 mm above the floor
        rng = np.random.default_rng(9)
        cam = look([0, -0.35, 0.35])
        world_B = np.stack([pose(f) for f in range(T)])
        poses = dict(world_T_cam=np.tile(np.linalg.inv(cam), (T, 1, 1)).astype(np.float32),
                     cam_T_A=np.tile(cam, (T, 1, 1)).astype(np.float32),
                     cam_T_B=np.einsum('ij,fjk->fik', cam, world_B).astype(np.float32))
        oA = evidence_obs(outer_true, rng, T)
        # the cavity is UNKNOWN (never seen), the outer wall OBSERVED, outside FREE
        g = grid_for(outer_true); C = g.centres()
        cav = IL.fast_inside(outer_cand, C) & ~IL.fast_inside(outer_true, C)
        st = oA['state'].ravel().copy(); st[cav] = 0; oA['state'] = st.reshape(oA['state'].shape)
        obs = dict(A=oA, B=evidence_obs(inner, rng, T))
        contact = list(range(20, T))
        cen = dict(frames=list(range(T)), contact=contact, separated=list(range(20)), j_mm=0.5, band_mm=3.0)
        meta = dict(objects=['A', 'B'], T=T, stride=1, K=[[FX, 0, 800], [0, FX, 500], [0, 0, 1]],
                    sigma_mm=dict(A=1.0, B=1.0), contact={'A|B': dict(cen), 'B|A': dict(cen)},
                    good={'A': [True] * T, 'B': [True] * T}, sanity={'A': dict(flags=[]), 'B': dict(flags=[])},
                    table=None, rest={}, tier='SYNTH')
        b = Bundle(meta, obs, poses)
        recs, _ = run_pair(b, dict(A=outer_cand, B=inner))
        s = summary(recs)
        RESULTS['n9'] = s
        self.assertEqual(s['A']['decision'], 'CARVE', s)
        self.assertFalse(s['A']['split'], s)
        self.assertGreater(s['A']['mix']['U'], 0, s)


class Pieces(unittest.TestCase):
    def test_box_removal_and_travel(self):
        """simpieces.remove_box cuts an exact slot out of convex hulls; n7: a thin tall guest in a holder slot whose
        carve removes the slot's bottom support falls through (P2 gravity travel > 40 mm detected)."""
        holder = trimesh.creation.box(extents=[0.10, 0.10, 0.06])
        H = [np.asarray(holder.vertices)]
        slot = dict(axes=np.eye(3).tolist(), centre=[0, 0, 0.015], half=[0.010, 0.020, 0.0151])
        cut, touched = SP.remove_box(H, slot)
        vol = SP.hull_volume(cut) * 1e6
        self.assertEqual(touched, 1)
        self.assertAlmostEqual(vol, 0.10 * 0.10 * 0.06 * 1e6 - 0.02 * 0.04 * (0.03 + 0.0001) * 1e6, delta=0.05)
        guest = [np.asarray(trimesh.creation.box(extents=[0.015, 0.030, 0.250]).apply_translation([0, 0, 0.125 +
                                                                                                    0.0]).vertices)]
        # guest stands in the 30 mm deep slot (bottom at z = 0); a second carve removes the slot bottom (through)
        T = np.eye(4)
        tr, base = PH.free_travel(cut, guest, T, {'gravity': [0, 0, -1.0]})
        through, _ = SP.remove_box(H, dict(axes=np.eye(3).tolist(), centre=[0, 0, 0], half=[0.010, 0.020, 0.031]))
        tr2, _ = PH.free_travel(through, guest, T, {'gravity': [0, 0, -1.0]})
        RESULTS['n7'] = dict(slot_travel_mm=round(tr['gravity'] * 1e3, 1), through_travel_mm=round(tr2['gravity'] * 1e3, 1))
        self.assertLessEqual(tr['gravity'], 0.004)
        self.assertGreater(tr2['gravity'], 0.040)


class Contract(unittest.TestCase):
    def test_export_roundtrip(self):
        """write_export -> validate -> carve_from_intrusions on the synthetic cross (t = 10 mm): same decisions as the
        tracks path; a geom-frame (shifted) export is refused by the fiducial check."""
        import tempfile
        t = 0.010
        b, world_B = cross_episode(t)
        cand = dict(A=plate(t), B=plate(t))
        with tempfile.TemporaryDirectory(dir=guard.SCRATCH_DEFAULT) as td:
            sim = os.path.join(td, 'r0')
            built = {o: SP.build(cand[o], IL.Evidence(b, o, cand[o], sub=False)) for o in ('A', 'B')}
            SP.write_round(sim, 999, 'public', 0, {o: dict(visual=cand[o], hulls=built[o]['default'], carve={})
                                                   for o in ('A', 'B')}, dict(source='synthetic'), 'test')
            path = os.path.join(td, 'intr.npz')
            IL.write_export(path, b, sim, ('A', 'B'), reference=dict(path='synthetic', sha256='0' * 64,
                                                                    provenance=dict(chain=['synthetic test'])))
            ok, rep = IL.validate(path, sim, synthetic_ok=True)
            RESULTS['contract_valid'] = dict(ok=ok, reasons=rep.get('refused'))
            self.assertTrue(ok, rep)
            bad = os.path.join(td, 'bad.npz')
            IL.write_export(bad, b, sim, ('A', 'B'), reference=dict(path='synthetic', sha256='0' * 64,
                                                                   provenance=dict(chain=['synthetic test'])),
                            shift_fiducials=0.003)
            ok2, rep2 = IL.validate(bad, sim, synthetic_ok=True)
            RESULTS['contract_shifted'] = dict(ok=ok2, reasons=rep2.get('refused'))
            self.assertFalse(ok2)


def tearDownModule():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w') as f:
        json.dump(RESULTS, f, indent=1, default=IL._jdefault)
    print('results ->', OUT)


if __name__ == '__main__':
    unittest.main(verbosity=2)
