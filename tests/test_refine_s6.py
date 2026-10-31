"""S6 static hold in pipeline/refine.py (tracker-fix PLAN §2 M1; 31 Oct 2026). Synthetic tracks only, no ground truth.
  rule        an object freezes when its horizontal centroid travel stays < 2 cm and, unless axisymmetric, its rotation
              < 10 deg; a lift along the plane normal does not count (ep11's blue cup rises 5.4 cm in the track);
  end to end  refine.main with --steps S6,S2 on a synthetic perception dir with a moving camera: the frame-0 depth plane
              (det_rules.table_plane, camera 0 -> world) is used, the frozen object holds its frame-0 world pose on every
              frame, the other object is untouched by S6, and every input passes assert_inference_input.
Run: pytest tests/test_refine_s6.py   (or python tests/test_refine_s6.py)
"""
import json, os, sys, tempfile
from types import SimpleNamespace

import numpy as np
from scipy.spatial.transform import Rotation as Rot

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
import refine  # noqa: E402

LIB = os.path.join(REPO, 'meshes', 'library_v3')
T = 60
UP = Rot.from_euler('xyz', [-50, 10, 5], degrees=True).as_matrix() @ np.array([0, 0, 1.0])   # a tilted world "up"


def basis(n):
    e1 = np.cross(n, [1.0, 0, 0])
    e1 /= np.linalg.norm(e1)
    return e1, np.cross(n, e1)


def track(h_cm=0.0, v_cm=0.0, spin_deg=0.0, tilt_deg=0.0, n=UP, start=(0.1, 0.0, 0.5), cen=np.zeros(3)):
    """World poses (T,4,4) whose vertex centroid CEN travels h_cm along the plane, rises v_cm along N (peak mid-episode)
    and turns spin_deg about N plus tilt_deg about a horizontal axis."""
    e1, _ = basis(n)
    s = np.sin(np.linspace(0, np.pi, T))                           # 0 -> 1 -> 0
    O = np.tile(np.eye(4), (T, 1, 1))
    for t in range(T):
        R = Rot.from_rotvec(np.radians(spin_deg) * s[t] * n).as_matrix() @ Rot.from_rotvec(np.radians(tilt_deg) * s[t] * e1).as_matrix()
        c = np.asarray(start) + (h_cm * s[t] * e1 + v_cm * s[t] * n) / 100
        O[t, :3, :3] = R
        O[t, :3, 3] = c - R @ cen
    return O


def args(**kw):
    a = SimpleNamespace(s6_hmax_cm=2.0, s6_rmax_deg=10.0, s6_axisym='blue_cup,beige_cup')
    a.__dict__.update(kw)
    return a


def obj(name):
    return SimpleNamespace(name=name, V=np.random.default_rng(0).normal(size=(50, 3)) * 0.03)


def test_order_and_option():
    assert refine.STEP_ORDER.index('S0') < refine.STEP_ORDER.index('S6') < refine.STEP_ORDER.index('S2')
    assert refine.STEP_ORDER.index('S6') < min(refine.STEP_ORDER.index(s) for s in ('S1', 'S3', 'S4', 'S5'))
    a = refine.parse_args(['--in', 'x', '--out', 'y', '--steps', 'S6,S2'])
    assert a.step_set == {'S6', 'S2'} and a.s6_hmax_cm == 2.0 and a.s6_rmax_deg == 10.0
    assert 'S6' not in refine.DEFAULT_STEPS.split(',')                  # opt-in only


def test_rule():
    objs = [obj(n) for n in ('blue_cup', 'plastic_dish_rack', 'mini_sweeper', 'beige_cup', 'white_pot', 'wooden_piece_1')]
    O = [track(h_cm=0.9, v_cm=5.4, spin_deg=40, cen=objs[0].V.mean(0)),       # ep11 blue cup: lifted, spins: FREEZE
         track(h_cm=0.6, v_cm=0.8, spin_deg=3, cen=objs[1].V.mean(0)),        # static rack: FREEZE
         track(h_cm=1.0, spin_deg=25, cen=objs[2].V.mean(0)),                # turns in place, not axisymmetric: keep
         track(h_cm=17.0, v_cm=20.0, spin_deg=20, cen=objs[3].V.mean(0)),    # carried cup: keep
         track(h_cm=2.05, cen=objs[4].V.mean(0)),                             # just over 2 cm sideways: keep
         track(h_cm=1.0, tilt_deg=12, cen=objs[5].V.mean(0))]                 # tilts 12 deg: keep
    O0 = [x.copy() for x in O]
    rec = refine.step_S6(args(), objs, O, (UP, 0.3, 'test plane'))
    assert rec['frozen'] == ['blue_cup', 'plastic_dish_rack'], rec['frozen']
    for j, o in enumerate(objs):
        r = rec['objects'][o.name]
        if o.name in rec['frozen']:
            assert all(np.array_equal(O[j][t], O0[j][0]) for t in range(T))
            assert set(r['others_at_peak']) == {p.name for p in objs} - {o.name}
        else:
            assert np.array_equal(O[j], O0[j])
    b = rec['objects']['blue_cup']
    assert abs(b['hmax_cm'] - 0.9) < 0.01 and abs(b['v_peak_cm'] - 5.4) < 0.01 and b['axisymmetric']
    assert abs(rec['objects']['mini_sweeper']['rmax_deg'] - 25) < 0.01
    # a wrong (camera-frame) normal would turn the 5.4 cm lift into horizontal travel and keep the cup
    O = [track(h_cm=0.9, v_cm=5.4, spin_deg=40, cen=objs[0].V.mean(0))]
    assert refine.step_S6(args(), objs[:1], O, (np.array([0, 0, 1.0]), 0.0, 'wrong'))['frozen'] == []
    # no plane: skipped, nothing changed
    O = [track(h_cm=0.5, cen=objs[0].V.mean(0))]
    O0 = O[0].copy()
    rec = refine.step_S6(args(), objs[:1], O, (None, None, 'no plane: test'))
    assert rec['skipped'] and rec['frozen'] == [] and np.array_equal(O[0], O0)


def synthetic_dir(d, KR):
    """poses.npz (moving camera; world = camera 0 rotated, so a camera-frame normal is wrong in the world), depth0.npy of
    a table plane, hands.npz with KR only. Objects: blue_cup lifted 5 cm (static), beige_cup carried 15 cm."""
    rng = np.random.default_rng(1)
    W = np.tile(np.eye(4), (T, 1, 1))
    W0R = Rot.from_euler('xyz', [35, -20, 10], degrees=True).as_matrix()
    for t in range(T):
        W[t, :3, :3] = W0R @ Rot.from_rotvec(rng.normal(size=3) * 0.02).as_matrix()
        W[t, :3, 3] = np.array([0.3, -0.2, 0.1]) + rng.normal(size=3) * 0.01
    nc = np.array([0.0, -0.8, -0.6])                                # table normal in camera 0 (y down, up = -y)
    cc = 0.5                                                        # n.x + c = 0, 0.5 m from the camera
    H_, W_ = 1000, 1600
    vv, uu = np.mgrid[0:H_, 0:W_]
    ray = np.stack([(uu - KR[0, 2]) / KR[0, 0], (vv - KR[1, 2]) / KR[1, 1], np.ones_like(uu, float)], -1)
    z = -cc / (ray @ nc)
    depth = np.where((z > 0.2) & (z < 1.0), z, 0).astype(np.float32)
    np.save(os.path.join(d, 'depth0.npy'), depth)
    np.savez(os.path.join(d, 'hands.npz'), KR=KR)
    up = W[0, :3, :3] @ nc                                          # the true world up
    import trimesh
    cen = {n: np.asarray(trimesh.load(os.path.join(LIB, f'{n}.glb'), force='mesh').vertices, float).mean(0)
           for n in ('blue_cup', 'beige_cup')}
    p0 = W[0, :3, :3] @ np.array([0.0, 0.05, 0.45]) + W[0, :3, 3]
    O = {'blue_cup': track(h_cm=0.8, v_cm=5.0, spin_deg=30, n=up, start=p0, cen=cen['blue_cup']),
         'beige_cup': track(h_cm=15.0, v_cm=12.0, spin_deg=10, n=up, start=p0 + 0.15 * basis(up)[1], cen=cen['beige_cup'])}
    camT = {n: np.einsum('tij,tjk->tik', np.linalg.inv(W), O[n]).astype(np.float32) for n in O}
    np.savez(os.path.join(d, 'poses.npz'), world_T_cam=W, **{f'cam_T_{n}': camT[n] for n in O})
    return W, camT, up


def test_end_to_end():
    KR = np.array([[600.2, 0, 756.8], [0, 600.2, 486.4], [0, 0, 1.0]])
    with tempfile.TemporaryDirectory() as tmp:
        inp, out = os.path.join(tmp, 'perc'), os.path.join(tmp, 'refined')
        os.makedirs(inp)
        W, camT, up = synthetic_dir(inp, KR)
        for f in os.listdir(inp):
            refine.assert_inference_input(os.path.join(inp, f))     # must not raise
        refine.LOG.clear()
        rec = refine.main(['--in', inp, '--out', out, '--steps', 'S6,S2', '--meshes', LIB])
        s6 = rec['steps']['S6']
        assert s6['frozen'] == ['blue_cup'], s6
        assert s6['plane']['source'].startswith('det_rules.table_plane')
        assert np.degrees(np.arccos(abs(np.dot(s6['plane']['n'], up)))) < 1.0
        assert rec['steps_order'] == ['S6', 'S2']
        V = np.load(os.path.join(out, 'poses_world_vo.npz'))
        b0 = W[0] @ camT['blue_cup'][0].astype(np.float64)
        assert np.abs(V['blue_cup'] - b0[None]).max() < 1e-5            # float32 camera poses: ~1e-7
        P = np.load(os.path.join(out, 'poses.npz'))
        assert P['cam_T_blue_cup'][0].tobytes() == camT['blue_cup'][0].tobytes()
        assert not np.allclose(V['beige_cup'], V['beige_cup'][:1])        # carried cup still moves
        js = json.load(open(os.path.join(out, 'pose_opt.json')))
        assert js['steps']['S6']['objects']['beige_cup']['frozen'] is False
        assert js['steps']['S6']['delta']['beige_cup']['frames_changed'] == 0


if __name__ == '__main__':
    for f in (test_order_and_option, test_rule, test_end_to_end):
        f()
        print('ok', f.__name__)
