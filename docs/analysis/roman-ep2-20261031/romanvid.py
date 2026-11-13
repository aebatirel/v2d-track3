"""Video for Roman (public ep2, pot + lid): each object separated and tracked on its own, its 6-DoF time series against
motion capture, the error split into delay / noise / drift, and the per-object Kalman filter he proposed.
Left: the real colour camera with each object's tracked mesh in its own colour, the motion-capture pose as white dots
(DIAGNOSTIC: public episode only, mocap mapped into our world by the fitted world transform and body offsets), our hand
keypoints, and a status box per object. Right: per object, position (ours vs mocap), position error per axis with the
measured +-2 sigma noise band, rotation error per axis; grey = a hand is near the object. Bottom: what was measured.
Usage: romanvid.py VIDEO_A POSES.npz HANDS_REFINED.npz SERIES.npz KF.json LAGNOISE.json MESHDIR OUT.mp4
"""
import json, subprocess, sys
import cv2
import numpy as np
import trimesh
from scipy.spatial.transform import Rotation as R

vid, posesf, handsf, seriesf, kff, lnf, meshdir, outf = sys.argv[1:9]
Pz = np.load(posesf); Hh = np.load(handsf); S = np.load(seriesf, allow_pickle=True); KF = json.load(open(kff)); LN = json.load(open(lnf))
names = [str(n) for n in S['names']]; WcT = Pz['world_T_cam'].astype(float); T = WcT.shape[0]
Ka, Da, off = Hh['Ka'], Hh['Da'], int(Hh['a_offset']); T_ra = np.linalg.inv(Hh['T_rect_a'].astype(float))
Wf = S['Wf']; COL = {names[0]: (0, 140, 255), names[1]: (255, 200, 0)}  # BGR: pot orange, lid cyan
AX = [(80, 80, 255), (80, 220, 80), (255, 140, 60)]  # x red, y green, z blue (BGR)
meshes = {}
for n in names:
    m = trimesh.load(f'{meshdir}/{n}.glb', force='mesh')
    if len(m.faces) > 1500:
        idx = np.random.default_rng(0).choice(len(m.faces), 1500, replace=False); m = trimesh.Trimesh(m.vertices, m.faces[idx], process=False)
    meshes[n] = m


def proj(Xw, k):  # world points -> camera-a pixels
    C = np.linalg.inv(WcT[min(k, T - 1)]); Xc = Xw @ C[:3, :3].T + C[:3, 3]; Xa = Xc @ T_ra[:3, :3].T + T_ra[:3, 3]
    uv, _ = cv2.projectPoints(Xa.reshape(-1, 1, 3), np.zeros(3), np.zeros(3), Ka, Da); return uv.reshape(-1, 2), Xa[:, 2] > 0.05


def ours_T(n, k):
    return Pz['world_T_cam'][k].astype(float) @ Pz[f'cam_T_{n}'][k].astype(float)


def truth_T(n, k):  # mocap pose of the scan body mapped into our world and our mesh frame (inv(Wf) G inv(X))
    p, rv = S[f'{n}_gt_p'][k], S[f'{n}_gt_r'][k]
    A0 = Wf @ ours_T(n, 0) @ S[f'{n}_X']; R0 = A0[:3, :3]
    G = np.eye(4); G[:3, :3] = R0 @ R.from_rotvec(rv).as_matrix(); G[:3, 3] = p
    return np.linalg.inv(Wf) @ G @ np.linalg.inv(S[f'{n}_X'])


BONES = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8), (0, 9), (9, 10), (10, 11), (11, 12), (0, 13), (13, 14),
         (14, 15), (15, 16), (0, 17), (17, 18), (18, 19), (19, 20), (5, 9), (9, 13), (13, 17)]

# ---------- static plots (right panel), drawn once with cv2; a cursor is added per frame
PW, PH = 840, 176; X0, X1 = 70, PW - 12


def plot(series, colors, styles, title, unit, band=None, shade=None, sym=False):
    img = np.full((PH, PW, 3), 22, np.uint8)
    allv = np.concatenate([s.ravel() for s in series]); lo, hi = np.percentile(allv, 0.5), np.percentile(allv, 99.5)
    if band is not None:
        lo, hi = min(lo, -2.5 * band), max(hi, 2.5 * band)
    if sym:
        m = max(abs(lo), abs(hi)); lo, hi = -m, m
    pad = 0.08 * (hi - lo + 1e-9); lo, hi = lo - pad, hi + pad; Y0, Y1 = 26, PH - 18
    fx = lambda t: int(X0 + (X1 - X0) * t / (T - 1)); fy = lambda v: int(Y1 - (Y1 - Y0) * (v - lo) / (hi - lo))
    if shade is not None:
        for t in np.flatnonzero(shade):
            cv2.rectangle(img, (fx(t), Y0), (fx(t) + max(1, (X1 - X0) // T), Y1), (48, 48, 48), -1)
    if band is not None:
        cv2.rectangle(img, (X0, fy(2 * band)), (X1, fy(-2 * band)), (60, 70, 60), -1)
    if lo < 0 < hi:
        cv2.line(img, (X0, fy(0)), (X1, fy(0)), (90, 90, 90), 1)
    for v in (lo + pad, hi - pad):
        cv2.putText(img, f'{v:+.1f}', (4, fy(v) + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (170, 170, 170), 1, cv2.LINE_AA)
    for s, c, st in zip(series, colors, styles):
        pts = np.array([[fx(t), fy(v)] for t, v in enumerate(s)], np.int32)
        if st == 'dash':
            for i in range(0, len(pts) - 1, 4):
                cv2.line(img, tuple(pts[i]), tuple(pts[min(i + 2, len(pts) - 1)]), c, 1, cv2.LINE_AA)
        else:
            cv2.polylines(img, [pts], False, c, 1 if st == 'thin' else 2, cv2.LINE_AA)
    cv2.putText(img, f'{title} [{unit}]', (X0, 17), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (235, 235, 235), 1, cv2.LINE_AA)
    return img, fx


panels = []
for n in names:
    p, gp = S[f'{n}_raw_p'] * 100, S[f'{n}_gt_p'] * 100; p = p - gp[0]; gp = gp - gp[0]
    e = p - gp; e = e - e.mean(0)
    re = np.rad2deg(S[f'{n}_raw_r'] - S[f'{n}_gt_r']); re = re - re.mean(0)
    kf = (S[f'{n}_kf_medium_p'] * 100 - S[f'{n}_gt_p'] * 100); kf = kf - kf.mean(0)
    sig = LN[n]['noise_rms_cm'] / np.sqrt(3); held = S[f'{n}_held']
    short = n.replace('white_', '')
    a, fx = plot([gp[:, 0], gp[:, 1], gp[:, 2], p[:, 0], p[:, 1], p[:, 2]], AX + AX, ['dash'] * 3 + ['solid'] * 3,
                 f'{short}: position from frame 0 (x right, y down, z depth; solid ours, dashed mocap)', 'cm', shade=held)
    b, _ = plot([e[:, 0], e[:, 1], e[:, 2], np.linalg.norm(kf, axis=1)], AX + [(200, 200, 200)], ['solid'] * 3 + ['thin'],
                f'{short}: position error per axis, constant removed (band = +-2 sigma noise; grey line = Kalman |err|)', 'cm', band=sig, shade=held, sym=True)
    c, _ = plot([re[:, 0], re[:, 1], re[:, 2]], AX, ['solid'] * 3, f'{short}: rotation error per axis, constant removed', 'deg', shade=held, sym=True)
    panels += [a, b, c]
right = np.concatenate(panels, 0)  # 6 x 176 = 1056 tall

# ---------- text panel
ln = LN; kfj = KF
lines = [
    'Public episode 2 (pot + lid). Each object has its OWN detector and tracker (no VLM needed: the episode lists its objects).',
    'Colour = our tracked mesh (orange pot, cyan lid). White dots = motion-capture truth (diagnostic, public episode only).',
    'Green / magenta = our hand keypoints. Grey in the plots = a hand is near that object.',
    f"Measured vs truth: pot {ln[names[0]]['rms_total_cm']:.2f} cm RMS, lid {ln[names[1]]['rms_total_cm']:.2f} cm RMS (after one constant offset per object).",
    f"  delay: our track lags truth by {ln[names[0]]['best_delay_ms']:.0f} / {ln[names[1]]['best_delay_ms']:.0f} ms (half a frame); shifting it back cuts ADD"
    f" {kfj[names[0]]['raw']['add_mean_cm']:.2f}->{kfj[names[0]]['raw_advanced_0.545']['add_mean_cm']:.2f} / {kfj[names[1]]['raw']['add_mean_cm']:.2f}->{kfj[names[1]]['raw_advanced_0.545']['add_mean_cm']:.2f} cm",
    f"  noise (fast jitter): {ln[names[0]]['noise_rms_cm']:.2f} / {ln[names[1]]['noise_rms_cm']:.2f} cm;  slow drift: {ln[names[0]]['slow_drift_rms_cm']:.2f} / {ln[names[1]]['slow_drift_rms_cm']:.2f} cm",
    '  The error spikes when an object moves fast (pick-up, put-down): error ~ speed x delay. That is the delay, not noise.',
    f"Per-object Kalman (const. velocity, still unless a hand touches it), ADD cm at obs. noise low/med/high:",
    f"  pot {kfj[names[0]]['kf_low']['add_mean_cm']:.2f}/{kfj[names[0]]['kf_medium']['add_mean_cm']:.2f}/{kfj[names[0]]['kf_high']['add_mean_cm']:.2f}"
    f" (raw {kfj[names[0]]['raw']['add_mean_cm']:.2f}),  lid {kfj[names[1]]['kf_low']['add_mean_cm']:.2f}/{kfj[names[1]]['kf_medium']['add_mean_cm']:.2f}/{kfj[names[1]]['kf_high']['add_mean_cm']:.2f}"
    f" (raw {kfj[names[1]]['raw']['add_mean_cm']:.2f});  offline smoother {kfj[names[0]]['rts_medium']['add_mean_cm']:.2f} / {kfj[names[1]]['rts_medium']['add_mean_cm']:.2f}",
]
TXT = np.full((1080 - 810, 1080, 3), 14, np.uint8)
for i, s in enumerate(lines):
    cv2.putText(TXT, s, (12, 22 + 26 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.47 if i < 3 else 0.5, (225, 225, 225) if i >= 3 else (180, 200, 180), 1, cv2.LINE_AA)

# ---------- frames
ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', '1920x1080', '-r', '20', '-i', '-',
                       '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '20', outf], stdin=subprocess.PIPE)
cap = cv2.VideoCapture(vid)
for _ in range(off):  # perception frame k <-> camera-a frame k + a_offset
    cap.read()
last = None
for k in range(T):
    ok, f = cap.read()
    last = f if ok else last
    img = last.copy(); ov = img.copy()
    for n in names:
        m = meshes[n]; Tk = ours_T(n, k); Vw = m.vertices @ Tk[:3, :3].T + Tk[:3, 3]; uv, ok = proj(Vw, k)
        for fc in m.faces:
            if ok[fc].all():
                cv2.fillConvexPoly(ov, uv[fc].astype(np.int32), COL[n], cv2.LINE_AA)
        Tg = truth_T(n, k); sub = m.vertices[::max(1, len(m.vertices) // 250)]
        uvg, okg = proj(sub @ Tg[:3, :3].T + Tg[:3, 3], k)
        for (u, v), o in zip(uvg, okg):
            if o:
                cv2.circle(img, (int(u), int(v)), 4, (255, 255, 255), -1, cv2.LINE_AA)
    img = cv2.addWeighted(ov, 0.38, img, 0.62, 0)
    for side, col in (('left', (80, 255, 80)), ('right', (255, 80, 255))):
        if Hh[f'valid_{side}'][k]:
            uv, ok = proj(Hh[f'joints_{side}'][k].astype(float), k)
            for a, b in BONES:
                if ok[a] and ok[b]:
                    cv2.line(img, tuple(uv[a].astype(int)), tuple(uv[b].astype(int)), col, 3, cv2.LINE_AA)
    img = cv2.rotate(img, cv2.ROTATE_180)  # camera a is mounted upside down
    cam = cv2.resize(img, (1080, 810), interpolation=cv2.INTER_AREA)
    for i, n in enumerate(names):  # status box per object
        e = np.linalg.norm(S[f'{n}_raw_p'][k] - S[f'{n}_gt_p'][k]) * 100
        st = 'HAND NEAR' if S[f'{n}_held'][k] else 'STILL'
        x0, y0 = 12, 12 + 66 * i
        cv2.rectangle(cam, (x0, y0), (x0 + 370, y0 + 58), (20, 20, 20), -1); cv2.rectangle(cam, (x0, y0), (x0 + 370, y0 + 58), COL[n], 2)
        cv2.putText(cam, f'{n}  [{st}]', (x0 + 10, y0 + 22), cv2.FONT_HERSHEY_SIMPLEX, 0.58, COL[n], 2, cv2.LINE_AA)
        cv2.putText(cam, f'error now {e:.2f} cm | delay {LN[n]["best_delay_ms"]:.0f} ms | noise {LN[n]["noise_rms_cm"]:.2f} cm',
                    (x0 + 10, y0 + 46), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (230, 230, 230), 1, cv2.LINE_AA)
    cv2.putText(cam, f'frame {k}  t = {k / 20:.2f} s', (850, 790), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
    rp = right.copy(); cx = fx(k)
    cv2.line(rp, (cx, 0), (cx, rp.shape[0]), (255, 255, 255), 1)
    canvas = np.zeros((1080, 1920, 3), np.uint8)
    canvas[:810, :1080] = cam; canvas[810:, :1080] = TXT; canvas[12:12 + rp.shape[0], 1080:1920] = rp
    ff.stdin.write(canvas.tobytes())
ff.stdin.close(); ff.wait()
print('wrote', outf)
