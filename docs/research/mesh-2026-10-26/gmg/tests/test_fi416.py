"""T-I1 additions of PREREG F-I4.16 (post hoc, board slot round 3: Douglas-Peucker ladder 1.0-4.0 mm, the synthetic
freeze family w10, slot-centre and coverage reports).

  GMG_MODE=dev python docs/research/mesh-2026-10-26/gmg/tests/test_fi416.py               (venv python, everything)
  GMG_MODE=dev python .../test_fi416.py W10                                              (one class)
  GMG_MODE=dev python .../test_fi416.py W10.test_k5_t8_s2_physics                        (one test)

F-I4.16.2 / F-I4.16.3 (written before any run; seeds new in gmg/):
  W10        the nine full-outline cells k = 1..9, (t, sigma_e) = (6, 1), (6, 2), (6, 3), (8, 1), (8, 2), (8, 3), (10, 1),
             (10, 2), (10, 3): two slot-less I-shaped plates `iplate10(t)` (230 mm, waist 125 mm, ends 137 mm over 20 mm),
             `test_interlock.cross_episode(t, two_sided=True, mesh_b=iplate10(t), seed=4160 + k)`; owned points = 3000
             surface samples (sample seed 4360 + k for A, 4460 + k for B), each frame displaced in the plate's frame by
             sigma_e N(0, 1) along x and y and 1.0 mm N(0, 1) along z (rng 4260 + k: A's 100 frames, then B's); camera =
             point + 0.4 m along the face normal; grid states from the true mesh; declared sigma 1.0 mm. Freeze condition
             (b), geometric part, per cell: both CARVE through the waiver route (T1), default and slotted prisms <= 82,
             keep-out <= 0.3 cm3 per hull, |w - (t + 2)| <= 1.0 mm on both. The (t 8, sigma_e 2) cell (k = 5) also P2-P7
             on 16 copies (F-I4.7 thresholds; P3 overlap = the median over the assembled frames).
  W10Report  report only: w10p (k = 10: the k = 5 cell with 30 % of A's footprint under a hand-shaped occluder, palm
             ellipse + four finger capsules scaled by bisection; A's samples and A's grid voxels under it dropped /
             UNKNOWN) and w10n (k = 11: t 8, isotropic 3 mm noise, declared 3 mm).
  ReRuns     report only: test_fi415.WaiverR2's w7, w8, w8b at REV 16 (fixtures and seeds unchanged); w8 / w8b keep-out
             reported against 0.0 cm3 (as written in F-I4.15.7) and 0.3 cm3.
  Identity   the code regression: the F-I4.15 suite cases (w1 at t = 6, 10, 13, 18, 25; w4 o2a / o2b; w6; w7; the w3
             plate-rod cases) at REV 15 and at REV 16 in one process: same decisions, and where REV 15 builds the pair
             rung 1.0 is chosen and every piece array is identical; w6c (the estimator alone) at REV 16. w2 (waiver off)
             never reaches platebody; w5 = physics on the w1 t = 10 pieces (identical pieces, nothing to re-run).
Results: <scratchpad>/gmg/interlock/test_fi416.json (env FI416_OUT overrides). Nothing is read from disk but code.
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

from gmg import interlock as IL, platebody as PB  # noqa: E402
import test_interlock as TI  # noqa: E402
import test_fi415 as T15  # noqa: E402

OUT = os.environ.get('FI416_OUT', os.path.join(guard.SCRATCH_DEFAULT, 'gmg', 'interlock', 'test_fi416.json'))
RES = {}
REV16 = 16
L_I, W_WAIST, W_END10, END_LEN = 0.230, 0.125, 0.137, 0.020            # F-I4.16.2 iplate10
CELLS = {1: (6, 1.0), 2: (6, 2.0), 3: (6, 3.0), 4: (8, 1.0), 5: (8, 2.0), 6: (8, 3.0), 7: (10, 1.0), 8: (10, 2.0),
         9: (10, 3.0)}
CAP = 82
_summary15 = T15.summary15


def iplate10(t):
    """F-I4.16.2: I-shaped plate along x (230 mm), y (125 mm waist, 137 mm over 20 mm at each end), z (t), slot-less."""
    parts = [trimesh.creation.box(extents=[L_I, W_WAIST, t])]
    for sx in (-1, 1):
        e = trimesh.creation.box(extents=[END_LEN, W_END10, t])
        e.apply_translation([sx * (L_I - END_LEN) / 2, 0, 0])
        parts.append(e)
    return trimesh.boolean.union(parts, engine='manifold')


def footprint10(x, y):
    """The true footprint of iplate10 in its own frame (mm)."""
    return (np.abs(x) <= 115.0) & ((np.abs(y) <= 62.5) | ((np.abs(x) >= 95.0) & (np.abs(y) <= 68.5)))


def hand(s):
    """F-I4.16.2 w10p occluder in A's frame (mm): palm ellipse centred (75, 62.5), semi-axes (40 s, 30 s), united with
    four finger capsules of radius 8 s, axes from (75 + c s, 62.5) to (75 + c s, 62.5 - 70 s), c in {-27, -9, 9, 27}."""
    def inside(x, y):
        x, y = np.asarray(x, np.float64), np.asarray(y, np.float64)
        m = ((x - 75.0) / (40.0 * s)) ** 2 + ((y - 62.5) / (30.0 * s)) ** 2 <= 1.0
        for c in (-27.0, -9.0, 9.0, 27.0):
            xc = 75.0 + c * s
            yy = np.clip(y, 62.5 - 70.0 * s, 62.5)
            m |= (x - xc) ** 2 + (y - yy) ** 2 <= (8.0 * s) ** 2
        return m
    return inside


def hand_scale(target=0.300, tol=0.005):
    """Bisection on s in [0.2, 3.0] so that the occluded share of the true iplate10 footprint (0.5 mm grid) is
    0.300 +- 0.005. Returns (s, share, footprint_cm2, occluder min |x| over the footprint in mm, iterations)."""
    g = np.arange(-120.0 + 0.25, 120.0, 0.5)
    X, Y = np.meshgrid(g, np.arange(-75.0 + 0.25, 75.0, 0.5), indexing='ij')
    fp = footprint10(X, Y)
    nfp = int(fp.sum())
    lo, hi = 0.2, 3.0
    s, share, it = None, None, 0
    for it in range(1, 61):
        s = 0.5 * (lo + hi)
        m = hand(s)(X, Y) & fp
        share = float(m.sum()) / nfp
        if abs(share - target) <= tol:
            break
        if share < target:
            lo = s
        else:
            hi = s
    m = hand(s)(X, Y) & fp
    return s, share, nfp * 0.25 * 1e-2, float(np.abs(X[m]).min()), it


def evidence10(mesh, gen, n_frames, sig_mm, sample_seed, occluder=None):
    """F-I4.16.2 evidence of one plate in its own frame: 3000 surface samples (sample seed), the same in every frame,
    displaced per frame by sig_mm (x, y, z) x N(0, 1) (one (3000, 3) draw per frame from GEN, frames in order);
    camera = displaced point + 0.4 m along the sample's face normal; grid states as test_interlock.evidence_obs from
    the true mesh. OCCLUDER (x_mm, y_mm) -> bool: samples under it are dropped in every frame (the draw is still made),
    grid voxels whose centre lies under it become UNKNOWN (state 0, hits 0, free 0) at every z."""
    g = TI.grid_for(mesh)
    C = g.centres()
    ins = IL.fast_inside(mesh, C)
    d = np.zeros(len(C))
    d[ins] = IL.geom.Closest(mesh).query(C[ins])[0]
    state = np.where(ins, np.where(d <= 0.004, 2, 0), 1).astype(np.uint8)
    hits = np.where(state == 2, 20, 0).astype(np.uint16)
    free = np.where(state == 1, 20, 0).astype(np.uint16)
    P, fi = trimesh.sample.sample_surface(mesh, 3000, seed=sample_seed)
    P = np.asarray(P, np.float64)
    N = np.asarray(mesh.face_normals)[fi]
    keep = np.ones(len(P), bool)
    info = dict(samples=int(len(P)))
    if occluder is not None:
        keep = ~occluder(P[:, 0] * 1e3, P[:, 1] * 1e3)
        oc = occluder(C[:, 0] * 1e3, C[:, 1] * 1e3)
        state[oc], hits[oc], free[oc] = 0, 0, 0
        info.update(samples_kept=int(keep.sum()), voxels_unknown_by_occluder=int(oc.sum()))
    sg = np.asarray(sig_mm, np.float64) * 1e-3
    pts, cam, fr = [], [], []
    for f in range(n_frames):
        X = P + gen.standard_normal((len(P), 3)) * sg
        pts.append(X[keep])
        cam.append((X + 0.4 * N)[keep])
        fr.append(np.full(int(keep.sum()), f, np.int32))
    pts = np.concatenate(pts).astype(np.float32)
    ob = dict(pts=pts, cam=np.concatenate(cam).astype(np.float32), frame=np.concatenate(fr),
              own=np.zeros(len(pts), np.uint8), lo=g.lo, hi=g.lo + TI.VOX * np.asarray(g.shape), vox=TI.VOX,
              hits=hits.reshape(g.shape), free=free.reshape(g.shape), state=state.reshape(g.shape),
              shared=np.zeros(g.shape, np.uint16), pocc=np.zeros(g.shape, np.uint16), args='{}')
    return ob, info


def w10_episode(k, t_mm, sig_e, sig_n=1.0, declared=1.0, occlude=False):
    """One w10 cell: the bundle (T = 100) and the fixture record."""
    t = t_mm * 1e-3
    b, _ = TI.cross_episode(t, two_sided=True, mesh_b=iplate10(t), seed=4160 + k)
    gen = np.random.default_rng(4260 + k)
    T = int(b.meta['T'])
    fix = dict(k=k, t_mm=t_mm, sigma_e_mm=sig_e, sigma_n_mm=sig_n, declared_sigma_mm=declared, T=T,
               seeds=dict(pose=4160 + k, noise=4260 + k, sample_A=4360 + k, sample_B=4460 + k))
    occ = None
    if occlude:
        s, share, fp_cm2, xmin, it = hand_scale()
        occ = hand(s)
        fix['occluder'] = dict(scale=round(s, 5), share=round(share, 4), footprint_cm2=round(fp_cm2, 2),
                               min_abs_x_mm=round(xmin, 2), reaches_slot_band_10mm=bool(xmin < 10.0), iterations=it)
    sig = (sig_e, sig_e, sig_n)
    b._obs['A'], fix['A'] = evidence10(iplate10(t), gen, T, sig, 4360 + k, occluder=occ)
    b._obs['B'], fix['B'] = evidence10(iplate10(t), gen, T, sig, 4460 + k)
    b.meta['sigma_mm'] = dict(A=declared, B=declared)
    return b, fix


def summary16(recs, sides, b=None):
    """test_fi415.summary15 plus the F-I4.16 fields: ladder table, chosen eps, coverage, slot-centre report, gate, the
    rectangle-frame slot fields (installed as test_fi415.summary15, so WaiverR2's _w1 / _w8 record them too)."""
    s = _summary15(recs, sides, b)
    for r in recs:
        x = r['target']
        if x not in s:
            continue
        w = r.get('waiver_fi4') or {}
        bd = (w.get('body') or {}).get(x) or {}
        sl = (w.get('slot') or {}).get(x) or {}
        lad = bd.get('ladder') or {}
        s[x].update(ladder=lad or None, chosen_eps_mm=lad.get('chosen_eps_mm'), coverage=bd.get('coverage'),
                    coverage_report=bd.get('coverage_report'), slot_centre={k: v for k, v in (sl.get('slot_centre') or
                                                                                               {}).items()
                                                                            if not k.endswith('per_mm')} or None,
                    c_L_mm=sl.get('c_L_mm'), bottom_mm=sl.get('bottom_mm'), body_gate=w.get('gate_fail'),
                    budget_full=(w.get('budget') or {}).get(x))
    return s


T15.summary15 = summary16


def freeze_b_checks(s, t_mm):
    """F-I4.16.3 (b), geometric part, for one cell: both CARVE via the waiver route (T1), default and slotted prisms
    <= 82, keep-out <= 0.3 cm3 per hull, |w - (t + 2)| <= 1.0 mm. Returns the list of misses."""
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
        for kk in ('default_pieces', 'slotted_pieces'):
            p = r.get(kk) or {}
            if not p or p.get('over_cap') or p.get('n', 999) > CAP or not p.get('tiling_ok') or not p.get('all_convex'):
                m.append(f'{o} {kk} {p}')
        if 'keepout' not in r or r['keepout']['max_cm3'] > 0.3:
            m.append(f'{o} keep-out {r.get("keepout")}')
        if abs(r['w_mm'] - (t_mm + 2.0)) > 1.0:
            m.append(f'{o} width {r["w_mm"]} vs t + 2 = {t_mm + 2.0}')
    return m


def predictions(s, sig_e=None):
    """P62 / P63 per cell (report only): chosen rung, end - waist on the chosen polygon (true 12 mm), entry-edge shift
    >= 3 mm, d_max <= eps on every simple rung."""
    out = {}
    for o in ('A', 'B'):
        r = s.get(o) or {}
        lad = r.get('ladder') or {}
        rows = lad.get('rows') or []
        wd = r.get('widths_mm') or {}
        out[o] = dict(chosen_eps_mm=lad.get('chosen_eps_mm'),
                      end_minus_waist_mm=wd.get('end_minus_waist'),
                      i_shape_ok=bool(wd and abs(wd['end_minus_waist'] - 12.0) <= 3.0),
                      entry_edge_shift_mm=r.get('entry_edge_shift_mm'),
                      waist_edge_ok=bool(r.get('entry_edge_shift_mm') is not None and r['entry_edge_shift_mm'] >= 3.0),
                      dmax_ok=bool(rows) and all(q['d_max_mm'] <= q['eps_mm'] + 1e-9 for q in rows if q.get('simple')))
    ch = [out[o]['chosen_eps_mm'] for o in out]
    out['P62_cell'] = (None if any(c is None for c in ch) else
                       bool(all(c <= (1.5 if sig_e == 1.0 else 3.0) for c in ch)))
    out['P63_cell'] = bool(all(out[o]['i_shape_ok'] and out[o]['waist_edge_ok'] and out[o]['dmax_ok'] for o in 'AB'))
    return out


def _physics(b, recs, key):
    t0 = time.time()
    ph, acc = T15.p3_of(b, recs, 16, f'T-I1 {key} (F-I4.16)')
    p3 = ph['P3']
    c = p3['carved']
    ok = bool(acc['pass_all_but_P1'] and c['lag_cm_asm'] <= 0.5 and c['lag_deg_asm'] <= 5.0 and
              ph['P6']['carved_asm_median'] < 1.0 and p3['judge']['pass_'])
    return dict(P3={k: p3.get(k) for k in ('carved', 'default', 'nocollide', 'judge')}, P2=ph['P2'], P4=ph['P4'],
                P6=dict(ph['P6']), P7=ph['P7'], acceptance=acc, pass_P2_P7=ok, sec=round(time.time() - t0, 1))


def run_cell(key, k, t_mm, sig_e, physics=False, **kw):
    t0 = time.time()
    PB.REV = REV16
    b, fix = w10_episode(k, t_mm, sig_e, **kw)
    cand = dict(A=iplate10(t_mm * 1e-3), B=iplate10(t_mm * 1e-3))
    recs, sides = TI.run_pair(b, cand, waiver=True)
    s = summary16(recs, sides, b)
    out = dict(fixture=fix, summary=s, misses_b=freeze_b_checks(s, t_mm), predictions=predictions(s, sig_e),
               fi4_rev=PB.REV)
    if physics and all((s.get(o) or {}).get('w_mm') is not None for o in 'AB'):
        out['physics'] = _physics(b, recs, key)
    out['sec'] = round(time.time() - t0, 1)
    RES[key] = out
    return out


class W10(unittest.TestCase):
    """F-I4.16.2 / F-I4.16.3 (b): the nine full-outline cells (freeze inputs)."""

    def _cell(self, k, physics=False):
        t_mm, sg = CELLS[k]
        out = run_cell(f'w10_k{k}', k, t_mm, sg, physics=physics)
        m = list(out['misses_b'])
        if physics:
            ph = out.get('physics')
            if ph is None or not ph['pass_P2_P7']:
                m.append(f'P2-P7 {None if ph is None else ph["acceptance"]}')
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
        """The physics cell: geometric checks and P2-P7 on 16 copies."""
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
    """Report only (not freeze inputs): w10p (P65) and w10n (P66). The assertions state the predictions."""

    def test_w10p_occluded(self):
        out = run_cell('w10p', 10, 8, 2.0, occlude=True)
        s = out['summary']
        cp = ((s.get('A') or {}).get('coverage_report') or {}).get('coverage_partner')
        out['P65'] = dict(both_carve=not out['misses_b'], coverage_partner_A=cp,
                          holds=bool(not out['misses_b'] and cp is not None and 0.65 <= cp <= 0.75))
        self.assertTrue(out['P65']['holds'], out['P65'])

    def test_w10n_isotropic3(self):
        out = run_cell('w10n', 11, 8, 3.0, sig_n=3.0, declared=3.0)
        s = out['summary']
        ta = {o: (s.get(o) or {}).get('t_all_mm') for o in 'AB'}
        pl = {o: (s.get(o) or {}).get('plate_t_mm') for o in 'AB'}
        out['P66'] = dict(t_all_mm=ta, plate_t_mm=pl, t_source={o: (s.get(o) or {}).get('t_source') for o in 'AB'},
                          both_carve=not out['misses_b'],
                          holds=bool(not out['misses_b'] and all(v is not None and abs(v - 8.0) <= 1.0
                                                                 for v in pl.values())))
        self.assertTrue(out['P66']['holds'], out['P66'])


class ReRuns(T15.WaiverR2):
    """Report only: w7, w8, w8b of F-I4.15.7 under REV 16 (the ladder); fixtures and seeds unchanged. The other
    WaiverR2 tests are skipped here (class Identity covers w1-w7 as a code regression)."""
    REV = 16

    def _w8(self, sigma, key, tilt=0.0, physics=True):
        out, m = super()._w8(sigma, key, tilt=tilt, physics=physics)
        s = out['summary']
        ko = {o: ((s.get(o) or {}).get('keepout') or {}).get('max_cm3') for o in 'AB'}
        out['keepout_max_cm3'] = ko
        out['keepout_vs_0_0'] = {o: (v is not None and v <= 0.0) for o, v in ko.items()}
        out['keepout_vs_0_3'] = {o: (v is not None and v <= 0.3) for o, v in ko.items()}
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
    setattr(ReRuns, _n, unittest.skip('F-I4.16: not a re-run (class Identity covers it)')(lambda self: None))


def _pair_dump(case, rev):
    """One F-I4.15 suite case at platebody.REV = rev: decisions, waiver gate, and the piece arrays per board."""
    rev0 = PB.REV
    PB.REV = rev
    try:
        name, t_mm = case
        if name == 'w1':
            b, cand, recs, sides = TI._waiver_case(t_mm)
        elif name == 'w6':
            def prep(b):
                b.meta['sigma_mm'] = dict(A=3.0, B=3.0)
            b, cand, recs, sides = TI._waiver_case(t_mm, prep=prep)
        elif name == 'w7':
            def prep(b):                                   # test_interlock.Waiver.test_w7_one_face, unchanged
                ob = b._obs['B']
                keep = (np.asarray(ob['cam'])[:, 2] - np.asarray(ob['pts'])[:, 2]) > 1e-3
                for kk in ('pts', 'cam', 'frame', 'own'):
                    ob[kk] = np.asarray(ob[kk])[keep]
            b, cand, recs, sides = TI._waiver_case(t_mm, prep=prep)
        elif name in ('w4_o2a', 'w4_o2b'):
            sil, notches = (('solid', None) if name == 'w4_o2a' else ('see', True))
            b, cand, recs, sides = TI._waiver_case(t_mm, offset=(0, -0.011, 0), sil=sil, notches=notches)
        elif name.startswith('w3_rod'):
            r_mm = int(name[6:])
            rod = trimesh.creation.cylinder(radius=r_mm * 1e-3, height=0.200, sections=48)
            rod.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0]))
            b, cand, recs, sides = TI._waiver_case(t_mm, mesh_b=rod, cand_b=rod)
        else:
            raise ValueError(name)
    finally:
        PB.REV = rev0
    dec = TI._decisions(recs)
    out = dict(decisions={k: [v[0], v[1], v[2]] for k, v in dec.items()}, pieces={}, slot={}, eps={}, gate=None)
    for r in recs:
        w = r.get('waiver_fi4') or {}
        out['gate'] = w.get('gate_fail', out['gate'])
        if r.get('_waiver'):
            x = r['target']
            out['pieces'][x] = dict(slotted=[np.asarray(V) for V in r['_waiver']['slotted']],
                                    default=[np.asarray(V) for V in r['_waiver']['default']])
            sl = r['_waiver']['slot']
            out['slot'][x] = dict(w_mm=sl['w_mm'], c_L_mm=sl['c_L_mm'], D_mm=sl['D_mm'],
                                  n_slotted=len(r['_waiver']['slotted']), n_default=len(r['_waiver']['default']))
        if w.get('body'):
            for x, bd in w['body'].items():
                if (bd.get('ladder') or {}).get('rows') is not None:
                    out['eps'][x] = dict(chosen=bd['ladder'].get('chosen_eps_mm'),
                                         rows=[{k: q.get(k) for k in ('eps_mm', 'simple', 'fits', 'vertices',
                                                                       'reflex_vertices', 'default_prisms',
                                                                       'slotted_prisms', 'd_max_mm')}
                                               for q in bd['ladder']['rows']])
    return out


def _same_pieces(a, b):
    if set(a) != set(b):
        return False
    for x in a:
        for kk in ('slotted', 'default'):
            if len(a[x][kk]) != len(b[x][kk]):
                return False
            if not all(np.array_equal(p, q) and p.tobytes() == q.tobytes() for p, q in zip(a[x][kk], b[x][kk])):
                return False
    return True


class Identity(unittest.TestCase):
    """The REV 16 code regression on the F-I4.15 suite cases (F-I4.16.2 'Regression check', extended to every case
    the polygon route reaches): REV 15 and REV 16 in one process."""
    CASES = (('w1', 6), ('w1', 10), ('w1', 13), ('w1', 18), ('w1', 25), ('w6', 10), ('w4_o2a', 10), ('w4_o2b', 10),
             ('w3_rod15', 10), ('w3_rod8', 10), ('w7', 10))

    def test_rev15_vs_rev16(self):
        rows, bad = {}, []
        for case in self.CASES:
            t0 = time.time()
            a, b = _pair_dump(case, 15), _pair_dump(case, 16)
            key = f'{case[0]}_t{case[1]}'
            same_dec = a['decisions'] == b['decisions']
            built15 = bool(a['pieces'])
            same_p = _same_pieces(a['pieces'], b['pieces'])
            rung1 = all(v['chosen'] == 1.0 for v in b['eps'].values()) if b['eps'] else None
            row = dict(decisions_rev15=a['decisions'], decisions_rev16=b['decisions'], same_decisions=same_dec,
                       gate_rev15=a['gate'], gate_rev16=b['gate'], built_rev15=built15, built_rev16=bool(b['pieces']),
                       pieces_identical=same_p, slot_rev15=a['slot'], slot_rev16=b['slot'], ladder_rev16=b['eps'],
                       rung_1_0_both=rung1, sec=round(time.time() - t0, 1))
            rows[key] = row
            if case[0] == 'w7':                            # the re-run case: expected to change (report only)
                continue
            if not same_dec or (built15 and not (same_p and rung1)) or (built15 != bool(b['pieces'])):
                bad.append(key)
        RES['identity'] = dict(cases=rows, bad=bad, note='w7 is reported only (REV 15: B over the cap at 1.0 mm)')
        self.assertEqual(bad, [], bad)

    def test_w6c_estimator(self):
        """w6c (the F-I4.15.1 estimator alone) at REV 16: |t - true| <= 1.0 mm in all six cells (plate_info is not
        changed by F-I4.16)."""
        rev0 = PB.REV
        T15.WaiverR2.REV = REV16
        try:
            PB.REV = REV16
            T15.WaiverR2('test_w6c_all_points').test_w6c_all_points()
        finally:
            PB.REV = rev0
            T15.WaiverR2.REV = 15
            RES['w6c_rev16'] = T15.RES.get('w6c')


def tearDownModule():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    out = dict(fi4_rev=REV16, fi416=RES, fi415_res=T15.RES, test_interlock_results=TI.RESULTS)
    with open(OUT, 'w') as f:
        json.dump(out, f, indent=1, default=IL._jdefault)
    print('results ->', OUT)


if __name__ == '__main__':
    unittest.main(verbosity=2)
