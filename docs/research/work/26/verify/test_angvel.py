import importlib.util, numpy as np, sys
from scipy.spatial.transform import Rotation as R
spec = importlib.util.spec_from_file_location("cm", sys.argv[1]); cm = importlib.util.module_from_spec(spec); spec.loader.exec_module(cm)
dt = cm.dt; T = 40
rng = np.random.default_rng(0)
def wxyz(rot): q = rot.as_quat(); return np.concatenate([q[:, 3:], q[:, :3]], 1)
for case in range(4):
    w_true = rng.normal(size=3); w_true *= (1.0 + 2 * case) / np.linalg.norm(w_true)   # 1,3,5,7 rad/s
    R0 = R.from_rotvec(rng.normal(size=3))
    t = np.arange(T) * dt
    # world-frame constant angular velocity: R(t) = exp(w t) R0
    Rw = R.from_rotvec(np.outer(t, w_true)) * R0
    q = wxyz(Rw)
    q[rng.random(T) < 0.5] *= -1                       # random sign flips
    w_est = cm.ang_vel(q.copy())
    err_world = np.abs(w_est[1:] - w_true).max()
    # body-frame expectation: w_body = R^T w_world
    w_body = Rw.inv().apply(w_true)
    err_body = np.abs(w_est[1:] - w_body[1:]).max()
    # body-frame constant angular velocity: R(t) = R0 exp(w t)
    Rb = R0 * R.from_rotvec(np.outer(t, w_true))
    w_est_b = cm.ang_vel(wxyz(Rb))
    w_world_b = Rb.apply(w_true)
    print(f"|w|={np.linalg.norm(w_true):.1f} rad/s ({np.degrees(np.linalg.norm(w_true))*dt:.1f} deg/frame): "
          f"world-const max err vs world {err_world:.2e}, vs body {err_body:.2e}; "
          f"body-const max err vs rotated-world {np.abs(w_est_b[1:]-w_world_b[1:]).max():.2e} "
          f"(midpoint-rotated {np.abs(w_est_b[1:]-Rb[:-1].apply(w_true)).max():.2e})")
# large rotation per frame (> pi): aliasing
w = np.array([0, 0, 1.0]) * np.radians(200) / dt
q = wxyz(R.from_rotvec(np.outer(np.arange(5) * dt, w)))
print("200 deg/frame true", np.degrees(w[2]) * dt, "est deg/frame", np.degrees(cm.ang_vel(q)[1:, 2] * dt))
# first-row duplication / alignment
print("row0 equals row1:", np.allclose(cm.ang_vel(wxyz(Rw))[0], cm.ang_vel(wxyz(Rw))[1]))
