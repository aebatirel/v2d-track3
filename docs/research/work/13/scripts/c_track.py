"""Stage C: per-frame accuracy of a stereo marker-triangle tracker for the spoon (thin, 3 markers), analytic MC.
Cameras: ego_cam_b/c pinhole f=567 px, 1280x800, baseline 75 mm (optionally + ego_cam_a f=1150 px, 2028x1520, 37 mm
from the stereo left). Markers in the spoon body frame (origin = R1 centroid of the prior-mean spoon model, axes =
construction axes: z bowl->handle, x convex back, y toward M1). Noise: iid Gaussian on each 2D marker centre.
Reports roll (about body z), tilt (body z direction), origin error, ADD over spoon surface samples, MPPE (+-5 cm keypoints).
Also: 2-marker cases, and a +-2 mm marker-model error (systematic)."""
import sys, json, numpy as np
sys.path.insert(0, "/Users/aebatirel/Documents/Code/v2d-research/work/13/scripts")
from c_cdo import spoon, PRIOR_MEAN
from spoon_model import frame_and_skews

rng = np.random.default_rng(7)
V, F = spoon(PRIOR_MEAN, True)
c, w, E, sk, A = frame_and_skews(V, F)
# marker centres in construction coords (same formulas as c_cdo.spoon)
from c_cdo import body
_, _, halfw = body(**PRIOR_MEAN["body"])
r, bh = PRIOR_MEAN["r_marker"], PRIOR_MEAN["base_h"]
M = np.array([[0, +(halfw(PRIOR_MEAN["m1_z"]) + bh + 0.85 * r), PRIOR_MEAN["m1_z"]],
              [0, -(halfw(PRIOR_MEAN["m2_z"]) + bh + 0.85 * r), PRIOR_MEAN["m2_z"]],
              [0, 0, PRIOR_MEAN["body"]["L"] + bh + 0.85 * r]]) - c
T = V[F]; ar = 0.5 * np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1)
idx = rng.choice(len(F), 500, p=ar / ar.sum()); SURF = T[idx].mean(1) - c
KP = 0.05 * np.vstack([np.eye(3), -np.eye(3)])

CAMS = {"b": (567.3, np.zeros(3)), "c": (567.3, np.array([0.075, 0, 0])), "a": (1149.8, np.array([-0.037, 0, 0]))}


def rand_rot():
    q = rng.normal(size=4); q /= np.linalg.norm(q); w_, x, y, z = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w_), 2 * (x * z + y * w_)],
                     [2 * (x * y + z * w_), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w_)],
                     [2 * (x * z - y * w_), 2 * (y * z + x * w_), 1 - 2 * (x * x + y * y)]])


def triangulate(uvs, cams):
    A, b = [], []
    for (u, v), cam in zip(uvs, cams):
        f, t = CAMS[cam]
        A.append([f, 0, -u]); b.append(f * t[0] - u * t[2])
        A.append([0, f, -v]); b.append(f * t[1] - v * t[2])
    return np.linalg.lstsq(np.array(A), np.array(b), rcond=None)[0]


def project(X, cam):
    f, t = CAMS[cam]; Y = X - t
    return f * Y[0] / Y[2], f * Y[1] / Y[2]


def kabsch(P, Q):
    pc, qc = P.mean(0), Q.mean(0)
    U, _, Vt = np.linalg.svd((P - pc).T @ (Q - qc))
    D = np.diag([1, 1, np.sign(np.linalg.det(Vt.T @ U.T))])
    R = Vt.T @ D @ U.T
    return R, qc - R @ pc


def errs(R, t, Re, te):
    dR = R.T @ Re
    ang = np.degrees(np.arccos(np.clip((np.trace(dR) - 1) / 2, -1, 1)))
    zt, ze = R[:, 2], Re[:, 2]
    tilt = np.degrees(np.arccos(np.clip(zt @ ze, -1, 1)))
    # roll: rotation of x about z after aligning z
    xr = dR[:, 0]; roll = np.degrees(np.arctan2(xr[1], xr[0]))
    add = np.linalg.norm((SURF @ Re.T + te) - (SURF @ R.T + t), axis=1).mean()
    mppe = np.linalg.norm((KP @ Re.T + te) - (KP @ R.T + t), axis=1).mean()
    return ang, tilt, abs(roll), 1000 * np.linalg.norm(te - t), 100 * add, 100 * mppe


def run(n, cams, sig, model_err_mm=0.0, flat=False):
    out = []
    for _ in range(n):
        if flat:   # resting on a table seen from a head camera pitched ~50 deg down at ~0.55 m
            yaw = rng.uniform(0, 2 * np.pi); pitch = np.radians(rng.uniform(40, 60))
            Rt = np.array([[np.cos(yaw), -np.sin(yaw), 0], [np.sin(yaw), np.cos(yaw), 0], [0, 0, 1]])
            # body x (convex back) points DOWN into the table when concave-up: body x -> -table normal
            Rb = np.column_stack([[0, 0, -1], [0, 1, 0], [1, 0, 0]]).astype(float)  # x->-Zt, y->Yt, z->Xt
            Rcam = np.array([[1, 0, 0], [0, -np.sin(pitch), -np.cos(pitch)], [0, np.cos(pitch), -np.sin(pitch)]])
            R = Rcam @ Rt @ Rb; t = np.array([rng.uniform(-0.1, 0.1), rng.uniform(-0.05, 0.1), 0.55])
        else:
            R = rand_rot(); t = np.array([rng.uniform(-0.15, 0.15), rng.uniform(-0.1, 0.1), rng.uniform(0.35, 0.7)])
        W = M @ R.T + t
        Mmod = M + model_err_mm * 1e-3 * rng.normal(size=M.shape)
        obs = []
        for X in W:
            uvs = [np.array(project(X, cm)) + sig * rng.normal(size=2) for cm in cams]
            obs.append(triangulate(uvs, cams))
        Re, te = kabsch(Mmod, np.array(obs))
        out.append(errs(R, t, Re, te))
    o = np.array(out)
    return dict(rot_med=np.median(o[:, 0]), rot_p90=np.percentile(o[:, 0], 90), tilt_med=np.median(o[:, 1]),
                roll_med=np.median(o[:, 2]), roll_p90=np.percentile(o[:, 2], 90), pos_med_mm=np.median(o[:, 3]),
                add_med_cm=np.median(o[:, 4]), add_p90_cm=np.percentile(o[:, 4], 90), mppe_med_cm=np.median(o[:, 5]),
                frac_rot_gt30=float(np.mean(o[:, 0] > 30)))


if __name__ == "__main__":
    print("marker centres rel. to R1 centroid (mm):", np.round(1000 * M, 1).tolist(), "centroid z (mm)", round(1000 * c[2], 1))
    print("R1 eigen sd (mm):", np.round(1000 * np.sqrt(w), 1).tolist())
    rows = [("b+c sig0.5 random", ["b", "c"], 0.5, 0, False), ("b+c sig1.0 random", ["b", "c"], 1.0, 0, False),
            ("b+c sig2.0 random (blur)", ["b", "c"], 2.0, 0, False), ("a+b+c sig0.5 random", ["a", "b", "c"], 0.5, 0, False),
            ("b+c sig0.5 model+-2mm", ["b", "c"], 0.5, 2.0, False), ("b+c sig0.5 flat-on-table", ["b", "c"], 0.5, 0, True),
            ("a+b+c sig0.5 flat-on-table", ["a", "b", "c"], 0.5, 0, True)]
    for nm, cams, sig, me, fl in rows:
        res = run(3000, cams, sig, me, fl)
        print(nm, json.dumps({k: round(float(v), 3) for k, v in res.items()}), flush=True)
