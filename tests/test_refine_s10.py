"""S10 held-object wrist lock (pipeline/heldpose.py via pipeline/refine.py; perception sprint "heldpose", 31 Oct 2026).
Synthetic tracks and hands only, no ground truth.
  option      S10 is opt-in (not in DEFAULT_STEPS) and runs after S2;
  visibility  a sample behind a finger bone is hidden, one in front of it or off the hand is visible;
  replace     an object rigidly held by a moving synthetic hand, whose track is corrupted mid-hold, is restored to the
              rigid-grasp pose by --s10_mode replace (G estimated on the clean onset frames); frame 0 is never changed;
  untouched   an object no hand comes near is byte-identical in every mode;
  end to end  refine.main --steps S2,S10 on a synthetic perception dir: every input passes assert_inference_input and
              pose_opt.json records the hold.
Run: python tests/test_refine_s10.py   (pytest is not installed in the scoring venv)
"""
import json, os, sys, tempfile
from types import SimpleNamespace

import numpy as np
from scipy.spatial.transform import Rotation as Rot

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
import heldpose as HP  # noqa: E402
import refine  # noqa: E402

LIB = os.path.join(REPO, 'meshes', 'library_v3')
T = 80
KR = np.array([[600.2, 0, 756.8], [0, 600.2, 486.4], [0, 0, 1.0]])
# a right-hand-like joint layout in the palm frame (m): wrist at 0, MCPs ~8 cm along +x, fingers bent along -z
HAND = np.zeros((21, 3))
HAND[0] = [0, 0, 0]
for k, (y, L) in enumerate([(0.03, 0.04), (0.02, 0.08), (0.0, 0.085), (-0.018, 0.08), (-0.034, 0.072)]):
    base = 1 + 4 * k
    HAND[base] = [L * (0.5 if k == 0 else 1.0), y, 0]
    for i in range(1, 4):
        HAND[base + i] = HAND[base] + [0.02 * i, 0, -0.012 * i]


def hand_world(Wp):
    """Joints (21,3) of the synthetic hand at palm pose Wp (4x4); palm frame origin = joint mean of PALM by design."""
    J = HAND @ Wp[:3, :3].T + Wp[:3, 3]
    return J


def palm_of(J):
    return HP.palm_frames(J[None])[0]


def args(**kw):
    a = SimpleNamespace(s10_mode='replace', s10_contact_cm=2.0, s10_bridge=6, s10_min_len=10, s10_carry_cm=2.0,
                        s10_onset=15, s10_vis_g=0.6, s10_vis_hi=0.8, s10_vis_lo=0.4, s10_ramp=5, s10_smooth=5,
                        s10_trim_deg=20.0, s10_radius_cm=1.0)
    a.__dict__.update(kw)
    return a


class Box:
    """Minimal refine.Obj stand-in: a 16 x 3 x 1 cm bar (sweeper-like handle) sampled on its surface."""
    def __init__(self, name):
        rng = np.random.default_rng(0)
        half = np.array([0.08, 0.015, 0.005])
        P = rng.uniform(-1, 1, size=(600, 3)) * half
        ax = rng.integers(0, 3, 600)                        # push each sample onto one face of the box
        P[np.arange(600), ax] = np.sign(P[np.arange(600), ax]) * half[ax]
        self.name, self.S, self.V = name, P, P
        self.com = P.mean(0)


def scene():
    """Camera fixed at the world origin looking +z. The hand rests (f0-19), grasps the bar and carries it 20 cm with a
    30 deg turn (f20-59), then stays. The bar is held with a fixed grasp G_true from f20 on."""
    WC = np.tile(np.eye(4), (T, 1, 1))
    Wp = np.tile(np.eye(4), (T, 1, 1))
    for t in range(T):
        s = np.clip((t - 20) / 40, 0, 1)
        Wp[t, :3, :3] = Rot.from_euler('xyz', [180, 0, 30 * s], degrees=True).as_matrix()
        Wp[t, :3, 3] = [0.0 + 0.2 * s, 0.0, 0.55]
    J = np.stack([hand_world(Wp[t]) for t in range(T)])
    Wpalm = HP.palm_frames(J)
    G_true = np.eye(4)
    G_true[:3, 3] = [0.06, 0.0, -0.012]                    # bar centre 1.2 cm off the palm plane, along the palm
    O_true = np.einsum('tij,jk->tik', Wpalm, G_true)
    O_true[:20] = O_true[20]                                # resting before the grasp
    return WC, J, O_true


def test_option():
    assert refine.STEP_ORDER.index('S2') < refine.STEP_ORDER.index('S10')
    assert 'S10' not in refine.DEFAULT_STEPS.split(',')
    a = refine.parse_args(['--in', 'x', '--out', 'y', '--steps', 'S2,S10'])
    assert a.step_set == {'S2', 'S10'} and a.s10_mode == 'gate' and a.s10_contact_cm == 2.0


def test_visibility():
    Jc = hand_world(np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0.5], [0, 0, 0, 1.0]]))   # hand 50 cm in front
    behind = Jc[6] + [0, 0, 0.05]
    front = Jc[6] - [0, 0, 0.05]
    off = Jc[6] + [0.0, 0.2, 0.05]
    occ = HP.occluded_by_hand(np.stack([behind, front, off]), Jc, KR)
    assert occ.tolist() == [True, False, False], occ


def test_replace_restores_rigid_grasp():
    WC, J, O_true = scene()
    o = Box('mini_sweeper')
    O_trk = O_true.copy()
    for t in range(40, 55):                                 # tracker failure mid-hold: 6 cm and 40 deg off
        O_trk[t, :3, :3] = O_trk[t, :3, :3] @ Rot.from_euler('z', 40, degrees=True).as_matrix()
        O_trk[t, :3, 3] += [0.0, 0.06, 0.0]
    Jh = {'right': J}
    Mh = {'right': np.ones(T, bool)}
    O = [O_trk.copy()]
    rec = HP.step_S10(args(), [o], O, WC, Jh, Mh, KR, refine.interp_pose, log=lambda *x: None)
    h = rec['objects']['mini_sweeper']['holds']
    assert len(h) == 1 and h[0]['side'] == 'right' and h[0]['a'] <= 21, h
    err = np.linalg.norm(O[0][:, :3, 3] - O_true[:, :3, 3], axis=1) * 100
    assert err[40:55].max() < 0.5, err[40:55]               # the failure is repaired
    assert np.array_equal(O[0][0], O_trk[0])               # frame 0 untouched
    # gate mode on the same scene: the bar is not covered by the hand here, so the gate keeps (most of) the tracker
    O = [O_trk.copy()]
    rec = HP.step_S10(args(s10_mode='gate'), [o], O, WC, Jh, Mh, KR, refine.interp_pose, log=lambda *x: None)
    assert rec['objects']['mini_sweeper']['holds'][0]['vis_pred_med'] > 0.0


def test_untouched_object():
    WC, J, _ = scene()
    o = Box('mini_dust_pan')
    O_far = np.tile(np.eye(4), (T, 1, 1))
    O_far[:, :3, 3] = [0.5, 0.3, 0.8]                       # far from the hand all episode
    for mode in ('gate', 'replace', 'trans'):
        O = [O_far.copy()]
        rec = HP.step_S10(args(s10_mode=mode), [o], O, WC, {'right': J}, {'right': np.ones(T, bool)}, KR,
                          refine.interp_pose, log=lambda *x: None)
        assert rec['objects']['mini_dust_pan']['holds'] == [] and np.array_equal(O[0], O_far)


def test_end_to_end():
    WC, J, O_true = scene()
    with tempfile.TemporaryDirectory() as tmp:
        inp, out = os.path.join(tmp, 'perc'), os.path.join(tmp, 'refined')
        os.makedirs(inp)
        import trimesh
        cen = np.asarray(trimesh.load(os.path.join(LIB, 'mini_sweeper.glb'), force='mesh').vertices).mean(0)
        O = O_true.copy()
        O[:, :3, 3] -= np.einsum('tij,j->ti', O[:, :3, :3], cen)   # put our mesh's centroid where the bar's is
        camT = np.einsum('tij,tjk->tik', np.linalg.inv(WC), O).astype(np.float32)
        np.savez(os.path.join(inp, 'poses.npz'), world_T_cam=WC, cam_T_mini_sweeper=camT)
        np.savez(os.path.join(inp, 'hands_refined.npz'), KR=KR, joints_right=J.astype(np.float32),
                 measured_right=np.ones(T, bool), joints_left=np.zeros((T, 21, 3), np.float32),
                 measured_left=np.zeros(T, bool))
        for f in os.listdir(inp):
            refine.assert_inference_input(os.path.join(inp, f))
        refine.LOG.clear()
        rec = refine.main(['--in', inp, '--out', out, '--steps', 'S2,S10', '--meshes', LIB, '--s10_mode', 'replace'])
        assert rec['steps_order'] == ['S2', 'S10']
        js = json.load(open(os.path.join(out, 'pose_opt.json')))
        s10 = js['steps']['S10']
        assert s10['mode'] == 'replace' and 'mini_sweeper' in s10['objects']
        assert js['checks']['world_T_cam_byte_identical']


if __name__ == '__main__':
    for f in (test_option, test_visibility, test_replace_restores_rigid_grasp, test_untouched_object, test_end_to_end):
        f()
        print('ok', f.__name__)
