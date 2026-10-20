# Stage B3: row-wise stereo of the spoon silhouette edges (rectified c/b, mono, wood bright vs table) -> 3-D limb points.
# For a round section viewed at cross-section elevation alpha the two limb points sit at hc +- rho cos(alpha), so their mean
# height is the centreline height hc; for the bowl the outer silhouette is the rim, whose two sides give the roll.
# Only rows where the spoon axis is >= 25 deg from the image rows are used (edges must cross the epipolar lines).
# Usage: b_estereo.py <tag> <k>   -> out/b/estereo_<tag>_k<k>.json
import sys, json, numpy as np, cv2
sys.path.insert(0, '/Users/aebatirel/Documents/Code/v2d-research/work/20/scripts'); from b_lib import *
tag, k = sys.argv[1], int(sys.argv[2]); ep = int(tag.lstrip('pe')); SPL = 'public' if tag[0] == 'p' else 'evaluation'
rec = [r for r in json.load(open(f'{OUT}/meas_{tag}.json')) if r['k'] == k and r.get('triple')][0]
gb = cv2.cvtColor(read_frames(SPL, ep, 'b', [k])[k], cv2.COLOR_BGR2GRAY); gc = cv2.cvtColor(read_frames(SPL, ep, 'c', [k])[k], cv2.COLOR_BGR2GRAY)
rc, rbs, fdy, dinfo = rect_pair(gc, gb)                       # b resampled by the local dy field
rc = cv2.GaussianBlur(rc.astype(np.float32), (0, 0), 0.8); rbs = cv2.GaussianBlur(rbs.astype(np.float32), (0, 0), 0.8)
c, n = np.array(rec['plane_c']), np.array(rec['plane_n']); M = np.array(rec['M_r'])
foot = lambda X: X - ((X - c) @ n)[..., None] * n
F = foot(M); O = 0.5 * (F[0] + F[1]); u = F[2] - O; u /= np.linalg.norm(u); wv = np.cross(n, u)
if (M[0] - O) @ wv < 0: wv = -wv                                  # + toward M1's side
s_m = (M - O) @ u


def proj(X):
    return FR * X[..., 0] / X[..., 2] + CXR, FR * X[..., 1] / X[..., 2] + CYR


def edge_pair(I, x0, half=70):
    """Wood segment around x0 on one row: returns sub-pixel (xl, xr) of the steepest bright->dark transitions."""
    xs = np.arange(int(x0) - half, int(x0) + half + 1)
    if xs[0] < 2 or xs[-1] > RSZ[0] - 3: return None
    p = I[xs]; g = np.gradient(p); i0 = half
    wood = np.median(p[i0 - 2:i0 + 3])
    if wood < 140: return None
    out = []
    for step in (-1, 1):
        i = i0
        while 0 < i < len(p) - 1 and p[i] > wood - 0.25 * (wood - 60): i += step
        if not 3 < i < len(p) - 4: return None
        # steepest descent (outward) within +-4 px of the threshold crossing
        seg = np.arange(i - 4, i + 5); gg = -step * g[seg]; j = seg[np.argmax(gg)]
        if -step * g[j] < 8: return None
        a, b_, cc = -step * g[j - 1], -step * g[j], -step * g[j + 1]; den = a - 2 * b_ + cc
        off = 0.5 * (a - cc) / den if den < 0 else 0.0
        out.append(xs[j] + np.clip(off, -1, 1))
    return out[0], out[1]


rows = []
ss = np.arange(-0.170, s_m[2] + 0.005, 0.0005)
for hguess in (0.015,):
    P = O[None] + ss[:, None] * u + hguess * n
    xa, ya = proj(P)
    # angle of the axis to the image rows
    ang = np.degrees(np.arctan2(np.abs(np.gradient(ya)), np.abs(np.gradient(xa))))
    Pb = P.copy(); disp_exp = FR * BASE / P[:, 2]
    for y in range(int(np.ceil(ya.min())), int(np.floor(ya.max())) + 1):
        i = np.argmin(np.abs(ya - y));
        if abs(ya[i] - y) > 1 or ang[i] < 25: continue
        ec = edge_pair(rc[y], xa[i]); eb = edge_pair(rbs[y], xa[i] - disp_exp[i])
        if ec is None or eb is None: continue
        for side, (xc_, xb_) in enumerate(zip(ec, eb)):
            d = xc_ - xb_
            if not (0.6 * disp_exp[i] < d < 1.4 * disp_exp[i]): continue
            X = tri_rect(np.array([xc_]), np.array([float(y)]), np.array([xb_]), np.array([float(y)]))[0]
            rows.append(dict(y=y, side=side, s=float((X - O) @ u * 1e3), w=float((X - O) @ wv * 1e3), h=float((X - c) @ n * 1e3),
                             d=float(d), ang=float(ang[i])))
json.dump(dict(tag=tag, k=k, s_markers=(s_m * 1e3).tolist(), w_markers=((M - O) @ wv * 1e3).tolist(),
               h_markers=((M - c) @ n * 1e3).tolist(), rows=rows), open(f'{OUT}/estereo_{tag}_k{k}.json', 'w'))
# summary in 15 mm bins of s: per side (M1 side = w>0) mean h, w
R_ = np.array([[r['s'], r['w'], r['h']] for r in rows]) if rows else np.zeros((0, 3))
print(f'{tag} k{k}: rows {len(rows)} | markers s {np.round(s_m*1e3,1)} w {np.round((M-O)@wv*1e3,1)} h {np.round((M-c)@n*1e3,1)}')
for s0 in np.arange(-160, s_m[2] * 1e3 + 1, 15):
    sel = (R_[:, 0] >= s0) & (R_[:, 0] < s0 + 15)
    a, b_ = sel & (R_[:, 1] > 0), sel & (R_[:, 1] <= 0)
    if a.sum() + b_.sum() == 0: continue
    f = lambda m, j: f'{np.median(R_[m, j]):6.1f}' if m.sum() else '     -'
    print(f'  s {s0:5.0f}..{s0+15:4.0f}: M1side n{a.sum():3d} w {f(a,1)} h {f(a,2)} | M2side n{b_.sum():3d} w {f(b_,1)} h {f(b_,2)}'
          + (f' | mid h {0.5*(np.median(R_[a,2])+np.median(R_[b_,2])):5.1f} halfwidth {0.5*(np.median(R_[a,1])-np.median(R_[b_,1])):5.1f} centre w {0.5*(np.median(R_[a,1])+np.median(R_[b_,1])):5.1f}' if a.sum() and b_.sum() else ''))
