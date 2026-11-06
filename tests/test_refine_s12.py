"""S12 cup-nest constraint in pipeline/refine.py / pipeline/nest.py (perception sprint "mask10", 31 Oct 2026). Synthetic
tracks with our cup meshes, no ground truth.
  rule      a beige cup lowered into a static blue cup whose TRACK rises 4 cm during the nest: the blue cup is held at its
            pre-nest pose (V1) / height (V1h) / frame-0 height (support) from the window start; frame 0 is untouched;
            the beige cup is untouched (inner none)
  guards    a blue cup lifted 5 cm before the nest is left alone (G1); a stack carried 6 cm sideways releases the hold;
            cups that never become coaxial give no window; a roster without two cups is skipped
  opt-in    S12 is not in DEFAULT_STEPS and runs after S11, before S2
Run: python tests/test_refine_s12.py   (or pytest)
"""
import os, sys
from types import SimpleNamespace

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
import refine  # noqa: E402
import nest  # noqa: E402

LIB = os.path.join(REPO, 'meshes', 'library_v3')
T = 80
N_UP = np.array([0, 0, 1.0])


def args(**kw):
    a = refine.parse_args(['--in', 'x', '--out', 'y', '--steps', 'S12,S2'])
    a.__dict__.update(kw)
    return a


def objs():
    return [refine.Obj(n, os.path.join(LIB, f'{n}.glb')) for n in ('blue_cup', 'beige_cup')]


def place(o, xyz):
    """Pose putting o's vertex centroid at xyz (identity rotation; our cup meshes' axes are close to z)."""
    P = np.eye(4)
    P[:3, 3] = np.asarray(xyz, float) - o.V.mean(0)
    return P


def scene(blue_lift_cm=2.5, pre_lift_cm=0.0, carry_cm=0.0, coax=True):
    """Blue at rest (bottom on z=0 roughly); beige comes from the side (f0-20), above the blue (f20-40), down into it
    (f40-60), nested to the end with its centroid 3 cm above the blue's (ep11 mocap: 3.2 cm). The blue TRACK rises blue_lift_cm over f45-60 and stays; pre_lift_cm lifts the blue
    track already at f10-35 (a hand-held outer); carry_cm moves blue and beige sideways from f65."""
    ob = objs()
    hb = -ob[0].V.min(0)[2] + ob[0].V.mean(0)[2]                      # centroid height with the bottom at z = 0
    O = [np.zeros((T, 4, 4)), np.zeros((T, 4, 4))]
    for t in range(T):
        lift = blue_lift_cm / 100 * np.clip((t - 45) / 15, 0, 1)
        pre = pre_lift_cm / 100 * (1.0 if 10 <= t else 0.0)
        cx = carry_cm / 100 * np.clip((t - 65) / 10, 0, 1)
        O[0][t] = place(ob[0], [cx, 0, hb + lift + pre])
        if t < 20:
            b = [0.25 - 0.01 * t, 0, hb]
        elif t < 40:
            b = [0.05 - 0.0025 * (t - 20), 0, hb + 0.20]
        else:
            b = [0.0, 0, hb + 0.20 - 0.17 * np.clip((t - 40) / 20, 0, 1)]   # ends 3 cm above the blue centroid
        if not coax:
            b[0] += 0.08
        b[0] += cx
        O[1][t] = place(ob[1], b)
    return ob, O


def lab_for(O, ob):
    return [dict(moving=np.zeros(T, bool), hand_cm=np.full(T, np.inf)) for _ in ob]


def run(mode='hold', **kw):
    ob, O = scene(**kw)
    O_in = [x.copy() for x in O]
    rec = nest.step_S12(args(s12_mode=mode), ob, O, (N_UP, 0.0, 'test'), lab_for(O, ob), np.tile(np.eye(4), (T, 1, 1)),
                        None, None, None, refine.checked, lambda *a: None)
    return ob, O_in, O, rec


def height(o, O):
    return (O[:, :3, :3] @ o.V.mean(0) + O[:, :3, 3]) @ N_UP


def test_hold_removes_lift():
    for mode in ('hold', 'height', 'support'):
        ob, O_in, O, rec = run(mode)
        w = [x for x in rec['windows'] if x.get('applied')]
        assert len(w) == 1 and w[0]['outer'] == 'blue_cup' and 20 < w[0]['start'] < 45, rec['windows']
        h_in, h = height(ob[0], O_in[0]), height(ob[0], O[0])
        assert h_in[-1] - h_in[0] > 0.024                              # the synthetic track lift
        assert abs(h[-1] - h[0]) < 1e-3, (mode, h[-1] - h[0])          # held at the pre-nest / frame-0 height
        assert np.array_equal(O[0][0], O_in[0][0])                     # frame 0 untouched
        assert all(np.array_equal(O[1][t], O_in[1][t]) for t in range(T))   # inner untouched (inner none)


def test_known_limit_track_climbs_above_inner():
    """Documented fragility [M, synthetic]: nested(t) is tested on the TRACKED outer, so when its lift exceeds the true
    inner-over-outer offset (here 4 cm > 3 cm) for more than --s12_bridge frames, the inner is no longer 'above' the
    outer, the window ends there and the hold is released (ramped back to the lifted track). On ep11 (P_o and the scan
    arm) and on eval 10's stored track the offset stays positive, so the frozen rule held to the end there."""
    ob, O_in, O, rec = run(blue_lift_cm=4.0)
    w = [x for x in rec['windows'] if x.get('applied')][0]
    assert w['released_by'] == 'window end' and w['hold_end'] < T
    h_in, h = height(ob[0], O_in[0]), height(ob[0], O[0])
    assert abs((h[-1] - h[0]) - (h_in[-1] - h_in[0])) < 1e-6           # the lift is back after the release


def test_g1_lifted_outer_left_alone():
    ob, O_in, O, rec = run(pre_lift_cm=5.0)
    assert rec['windows'] and not any(w.get('applied') for w in rec['windows'])
    assert 'G1' in rec['windows'][0]['reason']
    assert all(np.array_equal(O[0][t], O_in[0][t]) for t in range(T))


def test_carried_stack_releases():
    ob, O_in, O, rec = run(carry_cm=6.0)
    w = [x for x in rec['windows'] if x.get('applied')][0]
    assert w['released_by'] == 'outer moved horizontally' and w['hold_end'] < T
    assert np.allclose(O[0][-1], O_in[0][-1])                          # back on the track after the ramp


def test_no_window_when_not_coaxial():
    ob, O_in, O, rec = run(coax=False)
    assert not rec['windows'] and all(np.array_equal(O[j], O_in[j]) for j in range(2))


def test_skip_without_two_cups_and_opt_in():
    ob = objs()[:1]
    O = [np.tile(np.eye(4), (T, 1, 1))]
    rec = nest.step_S12(args(), ob, O, (N_UP, 0.0, 'test'), lab_for(O, ob), np.tile(np.eye(4), (T, 1, 1)), None, None,
                        None, refine.checked, lambda *a: None)
    assert 'skipped' in rec
    assert 'S12' not in refine.DEFAULT_STEPS.split(',')
    so = refine.STEP_ORDER
    assert so.index('S11') < so.index('S12') < so.index('S2')


def test_cup_geometry_orientation():
    """The cavity floor of the eval-10 collision pieces is found near the base (0.42 / 0.74 cm), not at the rim."""
    pcs = os.path.join(REPO, 'meshes', 'carve', 'ev10')
    for o, lo, hi in zip(objs(), (0.2, 0.5), (0.7, 1.0)):
        g = nest.CupGeom(o, pcs, refine.checked)
        assert lo < g.floor_above_base_cm < hi, (o.name, g.floor_above_base_cm)


if __name__ == '__main__':
    for k, f in list(globals().items()):
        if k.startswith('test_'):
            f()
            print('ok', k)
