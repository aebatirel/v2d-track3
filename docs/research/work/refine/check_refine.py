"""Self-checks for pipeline/refine.py (no ground truth; synthetic data plus one real perception dir).
  1. SE(3) helpers: exp/log round trip, interpolation end points, bi-invariance (left and right frame changes).
  2. S2 on a constant screw motion: O'(t) equals the exact pose at t + 0.545; the last frame is held.
  3. On PERC_DIR (optional): --steps none is byte-identical; S4 alone keeps frame 0 byte-identical; output keys are
     world_T_cam + cam_T_<roster> only; world_T_cam byte-identical for every step set.
Usage: python -I check_refine.py [PERC_DIR WORK_DIR]"""
import os, subprocess, sys
import numpy as np

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'pipeline'))
import refine as RF  # noqa: E402

rng = np.random.default_rng(0)


def rand_pose(scale=0.3):
    T = np.eye(4)
    T[:3, :3] = RF.rot_from_rotvec(rng.normal(size=3))
    T[:3, 3] = rng.normal(size=3) * scale
    return T


ok = True
for _ in range(50):
    A, B, G, H = rand_pose(), rand_pose(), rand_pose(), rand_pose()
    w, v = RF.se3_log(A)
    ok &= np.allclose(RF.se3_exp(w, v), A, atol=1e-9)
    ok &= np.allclose(RF.interp_pose(A, B, 0.0), A) and np.allclose(RF.interp_pose(A, B, 1.0), B)
    al = rng.uniform()
    ok &= np.allclose(RF.interp_pose(G @ A, G @ B, al), G @ RF.interp_pose(A, B, al), atol=1e-9)     # left
    ok &= np.allclose(RF.interp_pose(A @ H, B @ H, al), RF.interp_pose(A, B, al) @ H, atol=1e-9)     # right
print('1 se3 helpers', 'OK' if ok else 'FAIL')
all_ok = ok

# 2. constant screw motion
xi_w, xi_v = np.array([0.02, -0.05, 0.03]), np.array([0.004, 0.002, -0.006])
O0 = rand_pose()
Tn = 40
traj = np.stack([O0 @ RF.se3_exp(t * xi_w, t * xi_v) for t in range(Tn)])
a = RF.parse_args(['--in', 'x', '--out', 'y', '--steps', 'S2'])
out, _ = RF.step_S2(a, [traj])
exact = np.stack([O0 @ RF.se3_exp(min(t + 0.545, Tn - 1) * xi_w, min(t + 0.545, Tn - 1) * xi_v) for t in range(Tn)])
ok = np.allclose(out[0], exact, atol=1e-9) and np.array_equal(out[0][-1], traj[-1])
print('2 S2 exact on screw motion, last frame held', 'OK' if ok else 'FAIL')
all_ok &= ok

if len(sys.argv) > 2:
    perc, work = sys.argv[1], sys.argv[2]
    P = np.load(os.path.join(perc, 'poses.npz'))
    names = [k[6:] for k in P.files if k.startswith('cam_T_')]

    def run(steps, tag):
        o = os.path.join(work, tag)
        subprocess.run([sys.executable, '-I', os.path.join(REPO, 'pipeline', 'refine.py'), '--in', perc, '--out', o,
                        '--steps', steps, '--force'], check=True, capture_output=True)
        return np.load(os.path.join(o, 'poses.npz')), np.load(os.path.join(o, 'poses_world_vo.npz'))

    Q, V = run('none', 'none')
    V0 = np.load(os.path.join(perc, 'poses_world_vo.npz'))
    ok = all(Q[k].tobytes() == P[k].tobytes() for k in P.files) and all(V[n].tobytes() == V0[n].tobytes() for n in names)
    print('3a --steps none byte-identical', 'OK' if ok else 'FAIL'); all_ok &= ok
    Q, _ = run('S4', 's4')
    ok = all(Q[f'cam_T_{n}'][0].tobytes() == P[f'cam_T_{n}'][0].tobytes() for n in names)
    print('3b S4 keeps frame 0 byte-identical', 'OK' if ok else 'FAIL'); all_ok &= ok
    for steps in ('S1', 'S2', 'S3', 'S5', 'S1,S2,S3,S4', 'S1,S2,S3,S4,S5'):
        Q, V = run(steps, steps.replace(',', ''))
        ok = (Q.files == ['world_T_cam'] + [f'cam_T_{n}' for n in names] and Q['world_T_cam'].tobytes() == P['world_T_cam'].tobytes()
              and all(np.isfinite(Q[f'cam_T_{n}']).all() and len(Q[f'cam_T_{n}']) == len(P['world_T_cam']) for n in names)
              and all(np.allclose(V[n], np.einsum('tij,tjk->tik', P['world_T_cam'], Q[f'cam_T_{n}'].astype(float)), atol=1e-12) for n in names))
        print(f'3c {steps}: keys, world_T_cam, frames, world file consistent', 'OK' if ok else 'FAIL'); all_ok &= ok
print('ALL OK' if all_ok else 'SOME CHECKS FAILED')
sys.exit(0 if all_ok else 1)
