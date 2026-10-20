"""Verifier r2, C4: is the top-down separation an artefact of the GT-fitted 6-pt camera, which includes the by-eye pixel
(1273,888) of the very sphere the true branch is checked against?
Public ep 11 f0 cam a (analysis only: GT poses place the scan markers, as in v_c3_branch.py).
cam6 = 6-pt PnP (as claimed); cam5 = 5-pt PnP without (1273,888).
For each camera and pose perturbation (beige centre N(0, sc) per axis, tilt N(0, st)), fit each branch (start 0 and
-131 deg; best assignment of the two blobs; spin + table-plane shift, 5 mm prior) to the two detected beige blobs,
predict the third marker, and score the topdown cues there (circular-edge completeness best within 6 px; dark-pixel
fraction in the disk). Report how often the true branch scores higher. Usage: c4_noncirc.py [ndraw]"""
import numpy as np, json, sys, itertools, cv2, os
W12 = '/Users/aebatirel/Documents/Code/v2d-research/work/12'; sys.path.insert(0, W12); os.chdir(W12)
from pnp_check import variant, world_markers, T_of, solve as pnp_solve
from selfsim import good_markers
from scipy.spatial.transform import Rotation as Rr
from scipy.optimize import least_squares
ND = int(sys.argv[1]) if len(sys.argv) > 1 else 30
K, D = variant(False)
UV6 = np.array([[795, 988], [1044, 1022], [950, 1290], [1260, 1059], [1479, 984], [1273, 888]], float)
X, lab, objs = world_markers(11, 0, ['blue_cup', 'beige_cup'])
cams = {}
e6, (perm6, rv6, tv6, _) = pnp_solve(UV6, X, K, D); cams['cam6'] = (rv6, tv6, e6)
e5, (perm5, rv5, tv5, ee5) = pnp_solve(UV6[:5], X, K, D); cams['cam5'] = (rv5, tv5, e5)
print('cam6 %.2f px assign %s; cam5 %.2f px assign %s' % (e6, [lab[i] for i in perm6], e5, [lab[i] for i in perm5]))
AX = json.load(open(f'{W12}/out/axes2.json'))
name = 'beige_cup'; T = T_of(objs[name]['pose']); mk = good_markers(name); p, a = np.array(AX[name]['p']), np.array(AX[name]['a'])
B = np.array([[1261, 1058], [1480, 982]], float)
# --- image cues (same definitions as c2/topdown.py and c2/topdown2.py)
im = cv2.imread(W12 + '/b/fr/p11_a_0000.png'); g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY).astype(np.float32)
gs = cv2.GaussianBlur(g, (0, 0), 1.5); gx = cv2.Sobel(gs, cv2.CV_32F, 1, 0); gy = cv2.Sobel(gs, cv2.CV_32F, 0, 1); gm = np.hypot(gx, gy)
V = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)[..., 2].astype(np.float32) / 255
r0 = 18.5; ang = np.linspace(0, 2 * np.pi, 72, endpoint=False); yy, xx = np.mgrid[-19:20, -19:20]; disk = xx ** 2 + yy ** 2 <= r0 ** 2
def samp(img, x, y): return cv2.remap(img, x.astype(np.float32), y.astype(np.float32), cv2.INTER_LINEAR)
def circ(cx, cy):
    best = 0
    for r in r0 * np.array([0.85, 0.92, 1.0, 1.08, 1.15]):
        x = (cx + r * np.cos(ang))[None]; y = (cy + r * np.sin(ang))[None]
        rad = np.abs(samp(gx, x, y) * np.cos(ang) + samp(gy, x, y) * np.sin(ang)).ravel()
        loc = gm[int(cy - 2.5 * r):int(cy + 2.5 * r), int(cx - 2.5 * r):int(cx + 2.5 * r)].mean() + 1e-6
        best = max(best, float((rad > 0.5 * loc).mean() * rad.mean() / loc))
    return best
def circ6(cx, cy, rho=6, step=2):
    return max(circ(cx + dx, cy + dy) for dx in range(-rho, rho + 1, step) for dy in range(-rho, rho + 1, step) if dx * dx + dy * dy <= rho * rho)
def dark(x, y):
    sl = (slice(int(round(y)) - 19, int(round(y)) + 20), slice(int(round(x)) - 19, int(round(x)) + 20)); return float((V[sl][disk] < 0.2).mean())
# --- branch fit
def place(Tc, d_deg, sh):
    mk2 = (mk - p) @ Rr.from_rotvec(a * np.radians(d_deg)).as_matrix().T + p
    Wp = mk2 @ Tc[:3, :3].T + Tc[:3, 3]; Wp[:, :2] += sh; return Wp
def fit_branch(Tc, rv, tv, d0):
    proj = lambda Wp: cv2.projectPoints(np.ascontiguousarray(Wp, float), rv, tv, K, D)[0].reshape(-1, 2)
    best = None
    for i, j in itertools.permutations(range(3), 2):
        f = lambda q: np.r_[(proj(place(Tc, q[0], q[1:3]))[[i, j]] - B).ravel() / 4.0, q[1:3] / 0.005]
        s = least_squares(f, np.r_[d0, 0, 0])
        if abs(((s.x[0] - d0) + 180) % 360 - 180) > 25: continue
        rr = np.linalg.norm(proj(place(Tc, s.x[0], s.x[1:3]))[[i, j]] - B, axis=1)
        if best is None or rr.max() < best[0]:
            third = [k for k in range(3) if k not in (i, j)][0]
            best = (rr.max(), proj(place(Tc, s.x[0], s.x[1:3]))[third], s.x, rr)
    return best
rng = np.random.default_rng(5); out = {}
for cname, (rv, tv, e) in cams.items():
    for sc, st in [(0, 0), (2, 0), (2, 1), (5, 1)]:
        recs = []
        n = 1 if (sc, st) == (0, 0) else ND
        for t in range(n):
            Tc = T.copy()
            if sc or st:
                Tc[:3, 3] = T[:3, 3] + rng.normal(0, sc * 1e-3, 3)
                Tc[:3, :3] = Rr.from_rotvec(np.r_[rng.normal(0, np.radians(st), 2), 0]).as_matrix() @ T[:3, :3]
            bt = fit_branch(Tc, rv, tv, 0.0); bw = fit_branch(Tc, rv, tv, -131.0)
            pt, pw = bt[1], bw[1]
            ct, cw = circ6(*pt), circ6(*pw); dt, dw = dark(*pt), dark(*pw)
            recs.append(dict(pt=pt.tolist(), pw=pw.tolist(), fit_t=bt[0], fit_w=bw[0], spin_t=float(bt[2][0]), spin_w=float(bw[2][0]),
                             dist_true_to_byeye=float(np.linalg.norm(pt - [1273, 888])), circ_t=ct, circ_w=cw, dark_t=dt, dark_w=dw))
        R_ = recs; key = f'{cname}_sc{sc}_st{st}'; out[key] = R_
        f = lambda k: np.array([r[k] for r in R_])
        print('%s: n %d | 2-blob fit max px true %.1f / wrong %.1f (median) | true pred to by-eye sphere px median %.1f max %.1f | '
              'circ true>wrong %.2f (med %.2f vs %.2f) | dark true>wrong %.2f (med %.3f vs %.3f) | wrong fits better %.2f' % (
              key, len(R_), np.median(f('fit_t')), np.median(f('fit_w')), np.median(f('dist_true_to_byeye')), f('dist_true_to_byeye').max(),
              (f('circ_t') > f('circ_w')).mean(), np.median(f('circ_t')), np.median(f('circ_w')), (f('dark_t') > f('dark_w')).mean(),
              np.median(f('dark_t')), np.median(f('dark_w')), (f('fit_w') < f('fit_t')).mean()), flush=True)
        if n == 1: print('   true pred %s, wrong pred %s' % (np.round(R_[0]['pt']).tolist(), np.round(R_[0]['pw']).tolist()))
json.dump(out, open('/Users/aebatirel/Documents/Code/v2d-research/work/12-verify/r2/c4_noncirc.json', 'w'))
