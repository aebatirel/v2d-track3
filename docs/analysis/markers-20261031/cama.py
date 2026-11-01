"""Block-4 precondition check (GT-free part): marker fixes with ego_cam_a as a third view.

Calibration AS GIVEN, chained exactly as pipeline/hands_mp.py geometry(): ego_cam_a's extrinsic maps a -> ego_cam_b,
the ego pair's left_to_right maps c -> b, R1 rectifies c; T_a_rect = R_ab^T (R_lr R1^T X_rect + T_lr - t_ab). The 14-term
cam-a distortion is applied by cv2.projectPoints. Stereo frame k pairs with cam-a frame k + offset; the offset (0..3)
is chosen per episode, GT-free, as the one whose predicted marker projections (from the b/c fixes) land closest to
cam-a circle detections.
Per frame: pose0 = the frozen b/c fix (census fix file, >= 2 markers) or our track; each layout marker is searched in
cam a (circle detector of detect.py, relaxed thresholds as guided.py) inside a window of 12 mm (fix) / 30 mm (track)
around its projection; the pose is then refined on ALL observations (b/c labelled detections in the rectified pair +
cam-a circles) by robust reprojection least squares (sigma 0.5 px each view), dropping cam-a observations with
residual > 4 px; gate 5 cm / 30 deg vs our track. Output per frame: pose, markers seen in b/c, in a, in total.
Inputs: videos, calibration, our tracks, the frozen census fix files and guided detections. No ground truth.
Usage: python cama.py SPLIT EP OBJ OUT_NPZ
"""
import json, os, sys, time
import numpy as np, cv2
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation as Rot
sys.path.insert(0, os.path.dirname(__file__))
import mlib, detect

VID_A = {'eval': f'{mlib.S}/mk/dl/track_3/evaluation/videos/chunk-000/observation.images.ego_cam_a/episode_{{:06d}}.mp4',
         'public': f'{mlib.S}/mk/dl/track_3/public/videos/chunk-000/observation.images.ego_cam_a/episode_{{:06d}}.mp4'}
SIG, DROP_A, GATE_T, GATE_R = 0.5, 4.0, 0.05, 30.0


def geometry():
    C = json.load(open(mlib.CALIB)); cam = C['cameras']
    sp = [p for p in C['stereo_pairs'] if p['camera'] == 'ego'][0]
    K_ = lambda n: np.array(cam[n]['intrinsic_matrix'], float)
    D_ = lambda n: np.array(cam[n]['distortion_coefficients'], float)
    Kc, dc, Kb, db = K_('ego_cam_c'), D_('ego_cam_c'), K_('ego_cam_b'), D_('ego_cam_b')
    E = np.array(sp['left_to_right'], float); R_lr, T_lr = E[:3, :3].copy(), E[:3, 3].copy()
    R1, R2, P1, P2, Q, _, _ = cv2.stereoRectify(Kc, dc, Kb, db, (1280, 800), R_lr, T_lr.reshape(3, 1), alpha=0,
                                                newImageSize=(1600, 1000), flags=cv2.CALIB_ZERO_DISPARITY)
    Eab = np.array(cam['ego_cam_a']['extrinsics_to_stereo_left'], float); R_ab, t_ab = Eab[:3, :3], Eab[:3, 3]
    T = np.eye(4); T[:3, :3] = R_ab.T @ R_lr @ R1.T; T[:3, 3] = R_ab.T @ (T_lr - t_ab)
    return K_('ego_cam_a'), D_('ego_cam_a'), T


class CamA:
    def __init__(self):
        self.K, self.D, self.T = geometry(); self.f = 0.5 * (self.K[0, 0] + self.K[1, 1])

    def proj(self, X):
        Xa = np.atleast_2d(X) @ self.T[:3, :3].T + self.T[:3, 3]
        u, _ = cv2.projectPoints(Xa.reshape(-1, 1, 3), np.zeros(3), np.zeros(3), self.K, self.D)
        return u.reshape(-1, 2), Xa[:, 2]


def read_a(path, idx):
    cap = cv2.VideoCapture(path); want = set(idx); out = {}; k = 0
    while want and k <= max(idx):
        ok, f = cap.read()
        if not ok:
            break
        if k in want:
            out[k] = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
        k += 1
    return out


def detect_a(img, u, z, ca, win_m):
    r0 = ca.f * detect.R_VIS / z; w = ca.f * win_m / z
    rect = (int(u[0] - w), int(u[1] - w), int(u[0] + w), int(u[1] + w))
    if rect[0] < 0 or rect[1] < 0 or rect[2] >= img.shape[1] or rect[3] >= img.shape[0]:
        return []
    return detect.circles(img, rect, 0.65 * r0, 1.35 * r0, k=6, min_sup=0.30, max_isd=20.0, min_dark=10.0)


def fit(P0, Lb, obs_bc, obs_a, rig, ca, dv0):
    """obs_bc: {j: (uL, uR)}, obs_a: {j: u}; returns pose 4x4, residual dict."""
    def res(x):
        R = Rot.from_rotvec(x[:3]).as_matrix(); t = x[3:]
        out = []
        if obs_bc:
            js = sorted(obs_bc); X = Lb[js] @ R.T + t; uL, uR = rig.proj(X)
            for i, j in enumerate(js):
                oL, oR = obs_bc[j]
                out += list((uL[i] - oL) / SIG) + [(uR[i, 0] - oR[0]) / SIG]
        if obs_a:
            js = sorted(obs_a); X = Lb[js] @ R.T + t; ua, _ = ca.proj(X)
            for i, j in enumerate(js):
                out += list((ua[i] - obs_a[j]) / SIG)
        return np.array(out)
    x0 = np.r_[Rot.from_matrix(P0[:3, :3]).as_rotvec(), P0[:3, 3]]
    r = least_squares(res, x0, loss='huber', f_scale=3.0, max_nfev=200)
    P = np.eye(4); P[:3, :3] = Rot.from_rotvec(r.x[:3]).as_matrix(); P[:3, 3] = r.x[3:]
    ra = {}
    if obs_a:
        js = sorted(obs_a); ua, _ = ca.proj(Lb[js] @ P[:3, :3].T + P[:3, 3])
        ra = {j: float(np.linalg.norm(ua[i] - obs_a[j])) for i, j in enumerate(js)}
    return P, ra


def main():
    split, ep, obj, outp = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
    t0 = time.time(); rig = mlib.Rig(); ca = CamA()
    F = np.load(f'{mlib.S}/mk/scan/fix_{split}{ep}_{obj}.npz'); Lb = F['layout']; labs = json.loads(str(F['labs']))
    J = json.load(open(f'{mlib.S}/mk/scan/{split}{ep}_{obj}_g.json')); dv0 = J['dv0']
    T = np.load(mlib.poses_path(split, ep))[f'cam_T_{obj}'].astype(float)
    N = min(len(F['n']), len(T)); k = len(Lb)
    imgs = read_a(VID_A[split].format(ep), list(range(N + 4)))
    # GT-free frame offset: b/c >= 2-marker fixes predict the markers in cam a
    fr = [t for t in range(N) if F['n'][t] >= 2][::max(1, int(np.sum(F['n'] >= 2)) // 60)]
    off_d = {}
    for off in range(4):
        d = []
        for t in fr:
            if t + off not in imgs:
                continue
            X = Lb @ F['fix'][t][:3, :3].T + F['fix'][t][:3, 3]; ua, za = ca.proj(X)
            for j in range(k):
                c = detect_a(imgs[t + off], ua[j], za[j], ca, 0.012)
                if c:
                    d.append(min(np.hypot(q['u'] - ua[j, 0], q['v'] - ua[j, 1]) for q in c))
        off_d[off] = (float(np.median(d)) if d else 99.0, len(d))
    off = min(off_d, key=lambda o: off_d[o][0])
    poses = np.full((N, 4, 4), np.nan); n_bc = np.zeros(N, int); n_a = np.zeros(N, int); n_all = np.zeros(N, int)
    seen = np.zeros((N, k), bool); seen_a = np.zeros((N, k), bool); ra_med = np.full(N, np.nan)
    for t in range(N):
        if t + off not in imgs:
            continue
        fixed = F['n'][t] >= 2 and np.all(np.isfinite(F['fix'][t]))
        P0 = F['fix'][t] if fixed else T[t]
        lab = {int(j): i for j, i in labs[t].items()} if labs[t] else {}
        obs_bc = {j: (np.array(J['dets'][t][i]['uL']), np.array([J['dets'][t][i]['uR'][0], J['dets'][t][i]['uR'][1] + dv0]))
                  for j, i in lab.items()}
        X = Lb @ P0[:3, :3].T + P0[:3, 3]
        if np.any(X[:, 2] < 0.15):
            continue
        ua, za = ca.proj(X); obs_a = {}
        for j in range(k):
            c = detect_a(imgs[t + off], ua[j], za[j], ca, 0.012 if fixed else 0.03)
            if c:
                q = min(c, key=lambda q: np.hypot(q['u'] - ua[j, 0], q['v'] - ua[j, 1]) / max(q['sup'], 0.1))
                obs_a[j] = np.array([q['u'], q['v']])
        if len(set(obs_bc) | set(obs_a)) < 2:
            continue
        for _ in range(3):
            P, ra = fit(P0, Lb, obs_bc, obs_a, rig, ca, dv0)
            bad = [j for j, r in ra.items() if r > DROP_A]
            if not bad:
                break
            for j in bad:
                obs_a.pop(j)
            if len(set(obs_bc) | set(obs_a)) < 2:
                P = None; break
        if P is None:
            continue
        dt = np.linalg.norm(P[:3, 3] - T[t][:3, 3]); dr = np.degrees(Rot.from_matrix(P[:3, :3] @ T[t][:3, :3].T).magnitude())
        if dt > GATE_T or dr > GATE_R:
            continue
        poses[t] = P; n_bc[t] = len(obs_bc); n_a[t] = len(obs_a); n_all[t] = len(set(obs_bc) | set(obs_a))
        for j in obs_bc: seen[t, j] = True
        for j in obs_a: seen[t, j] = True; seen_a[t, j] = True
        if ra:
            ra_med[t] = float(np.median(list(ra.values())))
    np.savez_compressed(outp, poses=poses, n_bc=n_bc, n_a=n_a, n_all=n_all, seen=seen, seen_a=seen_a, ra_med=ra_med,
                        rest=F['rest'][:N], hand=F['hand'][:N] if len(F['hand']) else np.zeros(0), offset=off)
    print(json.dumps(dict(split=split, ep=ep, obj=obj, offset=off, offset_px={o: [round(v[0], 2), v[1]] for o, v in off_d.items()},
                          fix_bc2=int((F['n'][:N] >= 2).sum()), fix_bc3=int((F['n'][:N] >= 3).sum()),
                          fix_abc2=int((n_all >= 2).sum()), fix_abc3=int((n_all >= 3).sum()),
                          a_resid_px_med=round(float(np.nanmedian(ra_med)), 2) if np.isfinite(ra_med).any() else None,
                          seconds=round(time.time() - t0))), flush=True)


if __name__ == '__main__':
    main()
