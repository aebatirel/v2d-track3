import sys, json, cv2, numpy as np
sys.path.insert(0, '.'); from b_lib import *
tag, k = sys.argv[1], int(sys.argv[2]); ep = int(tag[1:])
J = json.load(open(f'{OUT}/estereo_{tag}_k{k}.json'))
gc = cv2.cvtColor(read_frames('evaluation', ep, 'c', [k])[k], cv2.COLOR_BGR2GRAY); rc = rect(gc, 'c')
rec = [r for r in json.load(open(f'{OUT}/meas_{tag}.json')) if r['k'] == k][0]
c, n = np.array(rec['plane_c']), np.array(rec['plane_n'])
im = cv2.cvtColor(rc, cv2.COLOR_GRAY2BGR)
# reconstruct pixel positions: recompute from s,w,h is awkward; re-run edge finder positions are not stored -> project 3D
M = np.array(rec['M_r']); foot = lambda X: X - ((X - c) @ n)[..., None] * n
F = foot(M); O = 0.5 * (F[0] + F[1]); u = F[2] - O; u /= np.linalg.norm(u); wv = np.cross(n, u)
if (M[0] - O) @ wv < 0: wv = -wv
for r in J['rows']:
    X = O + r['s'] * 1e-3 * u + r['w'] * 1e-3 * wv + (r['h'] * 1e-3 - (O - c) @ n) * n
    x, y = FR * X[0] / X[2] + CXR, FR * X[1] / X[2] + CYR
    col = (0, 0, 255) if r['w'] > 0 else (255, 0, 0)
    cv2.circle(im, (int(round(x)), int(round(y))), 1, col, -1)
xs = [FR * m[0] / m[2] + CXR for m in M]; ys = [FR * m[1] / m[2] + CYR for m in M]
x0, x1, y0, y1 = int(min(xs)) - 150, int(max(xs)) + 80, int(min(ys)) - 200, int(max(ys)) + 80
cr = im[max(y0, 0):y1, max(x0, 0):x1]
cv2.imwrite(f'{OUT}/edgevis_{tag}_k{k}.png', cv2.resize(cr, None, fx=2, fy=2, interpolation=cv2.INTER_NEAREST))
