"""S13 zero-lag position smoother (pipeline/rts.py via pipeline/refine.py; perception sprint "rts", 31 Oct 2026).
Synthetic tracks and hands only, no ground truth.
  option      S13 is opt-in (not in DEFAULT_STEPS), runs after S2, and its defaults are the pre-registered values;
  reference   rts_smooth equals the reference kf(..., smooth=True) of docs/analysis/roman-ep2-20261031/all20.py
              (branch claude/keen-heisenberg-engcwz at 4fc29ef, copied below) to 1e-12 m;
  line        a still track is unchanged up to float noise; a constant-velocity line too after its first 30
              frames (the v0 = 0 start prior bends its start by < 0.1 mm);
  noise       white position noise is reduced;
  gate        the hand gate marks exactly the frames with a valid joint within 3.5 cm of the posed vertices, ignores
              invalid hand frames, and switches q (a step during near frames is followed, without hands it is smoothed);
  rotations   every rotation block is byte-identical, the output has the input's length and last row;
  end to end  refine.main --steps S2,S13 on a synthetic perception dir: every input passes assert_inference_input,
              pose_opt.json records S13, the written rotations equal those of --steps S2.
Run: python tests/test_refine_s13.py   (pytest is not installed in the scoring venv)
"""
import json, os, sys, tempfile
from types import SimpleNamespace

import numpy as np
from scipy.spatial.transform import Rotation as Rot

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
import refine  # noqa: E402
import rts  # noqa: E402

LIB = os.path.join(REPO, 'meshes', 'library_v3')
T = 120
DT = 1 / 20.0


def kf_reference(z, gate, sig, q_free, q_still, smooth=False, lead=0.0):
    """all20.py kf at 4fc29ef, verbatim apart from line breaks (the reference implementation of the task)."""
    T_, D = z.shape; F = np.array([[1, DT], [0, 1]]); Hm = np.array([[1.0, 0.0]]); out = np.zeros_like(z)
    for a in range(D):
        x = np.array([z[0, a], 0.0]); P = np.diag([sig ** 2, 1.0]); xs, Ps, xp_l, Pp_l = [], [], [], []
        for t in range(T_):
            q = q_free if gate[t] else q_still; Q = q * np.array([[DT ** 3 / 3, DT ** 2 / 2], [DT ** 2 / 2, DT]])
            if t > 0:
                x = F @ x; P = F @ P @ F.T + Q
            xp_l.append(x.copy()); Pp_l.append(P.copy())
            S = Hm @ P @ Hm.T + sig ** 2; K = P @ Hm.T / S
            x = x + (K * (z[t, a] - Hm @ x)).ravel(); P = (np.eye(2) - K @ Hm) @ P; xs.append(x.copy()); Ps.append(P.copy())
        if smooth:
            for t in range(T_ - 2, -1, -1):
                C = Ps[t] @ F.T @ np.linalg.inv(Pp_l[t + 1]); xs[t] = xs[t] + C @ (xs[t + 1] - xp_l[t + 1])
                Ps[t] = Ps[t] + C @ (Ps[t + 1] - Pp_l[t + 1]) @ C.T
        out[:, a] = [s[0] + s[1] * lead * DT for s in xs]
    return out


def args(**kw):
    a = refine.parse_args(['--in', 'x', '--out', 'y', '--steps', 'S2,S13'])
    a.__dict__.update(kw)
    return a


def cup():
    return refine.Obj('blue_cup', os.path.join(LIB, 'blue_cup.glb'))


def track(p, rot_deg_per_frame=1.5):
    """(T,4,4) poses with positions p (T,3) and a rotation turning about a tilted axis."""
    O = np.tile(np.eye(4), (len(p), 1, 1))
    ax = np.array([0.3, 0.2, 0.93]) / np.linalg.norm([0.3, 0.2, 0.93])
    O[:, :3, :3] = Rot.from_rotvec(np.radians(rot_deg_per_frame) * np.arange(len(p))[:, None] * ax).as_matrix()
    O[:, :3, 3] = p
    return O


class Hands:
    """np.load-like hands file: .files and item access."""
    def __init__(self, **arrs):
        self.d = arrs
        self.files = list(arrs)

    def __getitem__(self, k):
        return self.d[k]


def no_hands_far():
    J = np.full((T, 21, 3), 5.0)
    return Hands(joints_left=J, valid_left=np.ones(T, bool), joints_right=J, valid_right=np.ones(T, bool))


def test_option():
    assert 'S13' not in refine.DEFAULT_STEPS.split(',')
    assert refine.DEFAULT_STEPS == 'S0,S1,S2,S3,S4'
    so = refine.STEP_ORDER
    assert so.index('S2') < so.index('S13') and so[:10] == ['S0', 'S6', 'S11', 'S12', 'S1', 'S3', 'S4', 'S5', 'S2', 'S10']
    a = args()
    assert a.step_set == {'S2', 'S13'}
    assert (a.s13_sigma, a.s13_q_near, a.s13_q_far, a.s13_near_m, a.s13_fps, a.s13_verts) == (0.008, 4.0, 0.04, 0.035, 20.0, 300)
    assert refine.parse_args(['--in', 'x', '--out', 'y']).step_set == {'S0', 'S1', 'S2', 'S3', 'S4'}


def test_matches_reference():
    rng = np.random.default_rng(3)
    z = np.cumsum(rng.normal(0, 0.004, size=(T, 3)), 0) + rng.normal(0, 0.003, size=(T, 3))
    gate = rng.random(T) < 0.3
    for sig, qn, qf in ((0.008, 4.0, 0.04), (0.002, 1.0, 1.0), (0.016, 64.0, 1e-4)):
        ours = rts.rts_smooth(z, gate, sig, qn, qf, DT)
        ref = kf_reference(z, gate, sig, qn, qf, smooth=True)
        assert np.abs(ours - ref).max() < 1e-12, np.abs(ours - ref).max()


def test_line_unchanged():
    """A still track is unchanged to float noise. A moving straight line is too, except the first frames: the
    pre-registered start state has v0 = 0 with variance 1 (m/s)^2, a prior that bends the line's start by < 0.1 mm."""
    t = np.arange(T)[:, None]
    for p, moving in ((np.tile([0.1, -0.2, 0.7], (T, 1)), False),                                    # still
                      (np.array([0.1, -0.2, 0.7]) + t * DT * np.array([0.08, -0.05, 0.02]), True)):   # 10 cm/s line
        for near in (np.zeros(T, bool), np.arange(T) % 7 < 3):
            ps = rts.rts_smooth(p, near, 0.008, 4.0, 0.04, DT)
            assert ps.shape == p.shape
            e = np.abs(ps - p).max(1)
            if moving:
                assert e[:30].max() < 1e-4 and e[30:].max() < 1e-9, (e[:30].max(), e[30:].max())
            else:
                assert e.max() < 1e-12, e.max()


def test_noise_reduced():
    rng = np.random.default_rng(1)
    t = np.arange(T)[:, None]
    for truth in (np.tile([0.0, 0.0, 0.5], (T, 1)), 0.05 * np.sin(t * DT * 2 * np.pi * 0.25) * np.array([[1, 0.5, 0.2]])):
        z = truth + rng.normal(0, 0.003, size=truth.shape)
        ps = rts.rts_smooth(z, np.zeros(T, bool), 0.008, 4.0, 0.04, DT)
        e0 = np.sqrt(np.mean((z - truth) ** 2))
        e1 = np.sqrt(np.mean((ps - truth) ** 2))
        assert e1 < 0.5 * e0, (e0, e1)


def test_hand_gate_switches_q():
    o = cup()
    p = np.tile([0.0, 0.0, 0.5], (T, 1))
    p[60:] += [0.03, 0.0, 0.0]                                   # a 3 cm step at f60 (a hand moves the cup)
    O = track(p, 0.0)
    V = rts.gate_vertices(o.path, 300)
    v0 = V[np.argmax(V[:, 0])]                                   # the vertex furthest along +x
    J = np.full((T, 21, 3), 5.0)
    for t in range(50, 70):                                      # one joint 2 cm outside that vertex on f50-69
        J[t, 4] = O[t, :3, :3] @ v0 + O[t, :3, 3] + [0.02, 0.0, 0.0]
    J[40, 4] = O[40, :3, :3] @ v0 + O[40, :3, 3]                # touching on f40, but that hand frame is not valid
    valid = np.ones(T, bool)
    valid[40] = False
    H = Hands(joints_right=J, valid_right=valid)
    rec = None
    for hands, label in ((H, 'near'), (no_hands_far(), 'far'), (None, 'none')):
        OO = [O.copy()]
        rec = rts.step_S13(args(), [o], OO, hands, refine.checked, lambda *a: None)
        near = rec['_aux']['S13_blue_cup_near']
        if label == 'near':
            assert np.array_equal(np.nonzero(near)[0], np.arange(50, 70)), np.nonzero(near)[0]
            assert abs(rec['_aux']['S13_blue_cup_hand_m'][55] - 0.02) < 1e-9
            e_near = np.abs(OO[0][:, 0, 3] - p[:, 0])
        else:
            assert not near.any()
            e_far = np.abs(OO[0][:, 0, 3] - p[:, 0])
            if label == 'none':
                assert rec['hands'] == 'no hands file: no frame near'
    # hand near (q 4.0): the 3 cm step is followed (6.3 mm at the step frames, < 1 mm two frames away); q 0.04
    # everywhere: rounded over many frames (12 mm at the step, > 3 mm two frames away)
    assert e_near.max() < 0.0065 and e_far.max() > 0.010, (e_near.max(), e_far.max())
    assert e_near[[57, 62]].max() < 0.001 and e_far[[57, 62]].min() > 0.003, (e_near[[57, 62]], e_far[[57, 62]])
    ref = kf_reference(p, np.isin(np.arange(T), np.arange(50, 70)), 0.008, 4.0, 0.04, smooth=True)
    OO = [O.copy()]
    rts.step_S13(args(), [o], OO, H, refine.checked, lambda *a: None)
    assert np.abs(OO[0][:, :3, 3] - ref).max() < 1e-12


def test_rotations_byte_identical():
    rng = np.random.default_rng(5)
    o = cup()
    p = np.array([0.1, 0.0, 0.6]) + np.cumsum(rng.normal(0, 0.003, size=(T, 3)), 0)
    O_in = track(p, 2.0)
    O = [O_in.copy()]
    rec = rts.step_S13(args(), [o], O, no_hands_far(), refine.checked, lambda *a: None)
    assert O[0].shape == O_in.shape and O[0].dtype == O_in.dtype
    assert O[0][:, :3, :3].tobytes() == O_in[:, :3, :3].tobytes()
    assert O[0][:, 3, :].tobytes() == O_in[:, 3, :].tobytes()
    assert not np.array_equal(O[0][:, :3, 3], O_in[:, :3, 3])
    assert rec['objects']['blue_cup']['near_frames'] == 0 and rec['rotation'] == 'unchanged'
    O1 = [O_in[:1].copy()]
    rec1 = rts.step_S13(args(), [o], O1, None, refine.checked, lambda *a: None)
    assert 'skipped' in rec1 and O1[0].tobytes() == O_in[:1].tobytes()


def test_end_to_end():
    rng = np.random.default_rng(7)
    t = np.arange(T)[:, None]
    p = np.array([0.05, 0.02, 0.55]) + np.clip(t - 40, 0, 40) * DT * np.array([0.1, 0.0, 0.02]) + rng.normal(0, 0.002, (T, 3))
    O = track(p, 1.0)
    WC = np.tile(np.eye(4), (T, 1, 1))
    WC[:, :3, 3] = [0.0, 0.0, -0.1]
    with tempfile.TemporaryDirectory() as tmp:
        inp = os.path.join(tmp, 'perc')
        os.makedirs(inp)
        camT = np.einsum('tij,tjk->tik', np.linalg.inv(WC), O).astype(np.float32)
        J = np.full((T, 21, 3), 5.0, np.float32)
        np.savez(os.path.join(inp, 'poses.npz'), world_T_cam=WC, cam_T_blue_cup=camT)
        np.savez(os.path.join(inp, 'hands_refined.npz'), joints_right=J, valid_right=np.ones(T, bool),
                 measured_right=np.ones(T, bool), joints_left=J, valid_left=np.zeros(T, bool), measured_left=np.zeros(T, bool))
        for f in os.listdir(inp):
            refine.assert_inference_input(os.path.join(inp, f))
        outs = {}
        for st in ('S2', 'S2,S13'):
            out = os.path.join(tmp, st.replace(',', '_'))
            refine.LOG.clear()
            rec = refine.main(['--in', inp, '--out', out, '--steps', st, '--meshes', LIB])
            assert rec['steps_order'] == st.split(',')
            outs[st] = out
        js = json.load(open(os.path.join(outs['S2,S13'], 'pose_opt.json')))
        s13 = js['steps']['S13']
        assert s13['sigma_m'] == 0.008 and s13['objects']['blue_cup']['near_frames'] == 0
        assert s13['hands']['right']['valid_key'] == 'valid_right' and s13['hands']['left']['valid_frames'] == 0
        assert js['checks']['world_T_cam_byte_identical'] and js['checks']['finite']
        A = np.load(os.path.join(outs['S2'], 'poses_world_vo.npz'))['blue_cup']
        B = np.load(os.path.join(outs['S2,S13'], 'poses_world_vo.npz'))['blue_cup']
        assert A.shape == B.shape == (T, 4, 4)
        dR = np.degrees(np.linalg.norm(Rot.from_matrix(np.einsum('tji,tjk->tik', A[:, :3, :3], B[:, :3, :3])).as_rotvec(), axis=1))
        assert dR.max() < 1e-4, dR.max()
        assert np.abs(A[:, :3, 3] - B[:, :3, 3]).max() > 1e-4
        aux = np.load(os.path.join(outs['S2,S13'], 'pose_opt_aux.npz'))
        assert 'S13_blue_cup_near' in aux.files and len(aux['S13_blue_cup_change_cm']) == T


if __name__ == '__main__':
    for f in (test_option, test_matches_reference, test_line_unchanged, test_noise_reduced, test_hand_gate_switches_q,
              test_rotations_byte_identical, test_end_to_end):
        f()
        print('ok', f.__name__)
