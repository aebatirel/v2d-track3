# Stage B4b: body-frame marker offsets from one held frame (bowl plane roughly facing the camera).
# Row-wise edge stereo on the field-warped rectified pair along the spoon (initial axis = mid(M1,M2) -> M3 from b_held):
#   handle rows (s > +25 mm past mid(M1,M2), before M3 - 12 mm): limb pairs -> 3-D midpoints -> axis line (exact for a round rod);
#   bowl rows (s < -30 mm): left/right silhouette points (= rim in a frontal view) -> lateral direction y (paired rows).
# Body frame: z = axis (bowl -> M3), y = mean paired rim direction orthogonalised to z, x = z cross... (sign set below).
# Reports marker (lateral y, out-of-plane x, station s) relative to the axis line, plus diagnostics.
# Usage: b_heldgeom.py <ep> <k> [k ...]  -> out/b/heldgeom_e<ep>.jsonl
import sys, json, numpy as np, cv2
sys.path.insert(0, '/Users/aebatirel/Documents/Code/v2d-research/work/20/scripts'); from b_lib import *
ep = int(sys.argv[1]); KS = [int(x) for x in sys.argv[2:]]
H = {json.loads(l)['k']: json.loads(l) for l in open(f'{OUT}/held_e{ep}.jsonl')}


def proj(X): return FR * X[..., 0] / X[..., 2] + CXR, FR * X[..., 1] / X[..., 2] + CYR


def edge_pair(I, x0, half=60, minc=25):
    xs = np.arange(int(x0) - half, int(x0) + half + 1)
    if xs[0] < 2 or xs[-1] > RSZ[0] - 3: return None
    p = I[xs]; g = np.gradient(p); i0 = half; wood = np.median(p[i0 - 2:i0 + 3]); out = []
    for step in (-1, 1):
        i = i0
        while 0 < i < len(p) - 1 and p[i] > wood - 0.3 * max(wood - 60, minc): i += step
        if not 3 < i < len(p) - 4: return None
        seg = np.arange(i - 4, i + 5); j = seg[np.argmax(-step * g[seg])]
        if -step * g[j] < 6: return None
        a, b_, cc = -step * g[j - 1], -step * g[j], -step * g[j + 1]; den = a - 2 * b_ + cc
        out.append(xs[j] + (np.clip(0.5 * (a - cc) / den, -1, 1) if den < 0 else 0.0))
    return out[0], out[1], wood


res = []
for k in KS:
    h = H[k]; M = np.array(h['M_r'])
    gb = cv2.cvtColor(read_frames('evaluation', ep, 'b', [k])[k], cv2.COLOR_BGR2GRAY); gc = cv2.cvtColor(read_frames('evaluation', ep, 'c', [k])[k], cv2.COLOR_BGR2GRAY)
    rc, rbw, fdy, dinfo = rect_pair(gc, gb); rc = cv2.GaussianBlur(rc.astype(np.float32), (0, 0), 0.8); rbw = cv2.GaussianBlur(rbw.astype(np.float32), (0, 0), 0.8)
    O = 0.5 * (M[0] + M[1]); z = M[2] - O; z /= np.linalg.norm(z)
    tri_n = np.cross(M[1] - M[0], M[2] - M[0]); tri_n -= (tri_n @ z) * z; tri_n /= np.linalg.norm(tri_n)
    for it in range(2):
        ss = np.arange(-0.175, (M[2] - O) @ z + 0.005, 0.0005); P = O[None] + ss[:, None] * z
        xa, ya = proj(P); dexp = FR * BASE / P[:, 2]
        ang = np.degrees(np.arctan2(np.abs(np.gradient(ya)), np.abs(np.gradient(xa))))
        pts = []
        for y in range(int(np.ceil(ya.min())), int(np.floor(ya.max())) + 1):
            i = np.argmin(np.abs(ya - y))
            if abs(ya[i] - y) > 1 or ang[i] < 30: continue
            ec = edge_pair(rc[y], xa[i]); eb = edge_pair(rbw[y], xa[i] - dexp[i])
            if ec is None or eb is None: continue
            row = []
            for xc_, xb_ in zip(ec[:2], eb[:2]):
                d = xc_ - xb_
                if not (0.85 * dexp[i] < d < 1.15 * dexp[i]): row = None; break
                row.append(tri_rect(np.array([xc_]), np.array([float(y)]), np.array([xb_]), np.array([float(y)]))[0])
            if row: pts.append((ss[i], row[0], row[1]))
        if not pts: break
        S = np.array([p[0] for p in pts]); L = np.array([p[1] for p in pts]); Rr = np.array([p[2] for p in pts]); W = np.linalg.norm(Rr - L, axis=1)
        sM = (M - O) @ z
        hand = (S > sM[1] + 0.02) & (S < sM[2] - 0.012) & (W > 0.014) & (W < 0.026)
        if hand.sum() < 8: break
        Cm = 0.5 * (L[hand] + Rr[hand]); c0 = Cm.mean(0); _, _, vt = np.linalg.svd(Cm - c0); zz = vt[0] * np.sign(vt[0] @ z)
        res_ax = np.linalg.norm((Cm - c0) - ((Cm - c0) @ zz)[:, None] * zz, axis=1)
        keep = res_ax < max(3 * np.median(res_ax), 0.0015); Cm = Cm[keep]; c0 = Cm.mean(0); _, _, vt = np.linalg.svd(Cm - c0); zz = vt[0] * np.sign(vt[0] @ z)
        O = c0 - ((c0 - O) @ zz) * zz + 0 * zz; z = zz                     # re-anchor the axis line; iterate the row search once
    if not pts or hand.sum() < 8:
        print(k, 'too few handle rows', len(pts)); continue
    # axis line: c0 + t z.  Bowl rows (s < -30 mm from mid(M1,M2) along the new axis)
    sB = (0.5 * (L + Rr) - c0) @ z; s12 = (0.5 * (M[0] + M[1]) - c0) @ z
    bowl = (sB < s12 - 0.030) & (W > 0.025)
    dirs = Rr[bowl] - L[bowl]; dirs -= (dirs @ z)[:, None] * z; dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)
    y0 = np.median(dirs, axis=0); y0 /= np.linalg.norm(y0)
    # orient y toward M1's side, x = y cross z ... choose x toward the camera-facing side for reporting, then sign by M2 later
    if (M[0] - c0) @ y0 < 0: y0 = -y0
    x0 = np.cross(y0, z)
    def body(X):
        t = (X - c0) @ z; foot = c0 + t * z; return float((X - foot) @ y0 * 1e3), float((X - foot) @ x0 * 1e3), float(t * 1e3)
    mk = [body(X) for X in M]
    # rim centre and rim offset from the axis plane along x (bowl rows)
    mid = 0.5 * (L[bowl] + Rr[bowl]); mb = [body(X) for X in mid]
    view = c0 - A_centre_r if 'A_centre_r' in dir() else c0; view = c0 / np.linalg.norm(c0)
    rec = dict(k=k, n_rows=len(pts), n_handle=int(keep.sum()), n_bowl=int(bowl.sum()), axis_rms_mm=float(np.sqrt(np.mean(res_ax[keep] ** 2)) * 1e3),
               handle_halfwidth_mm=float(np.median(W[hand]) * 500), markers=mk, bowl_mid_y=float(np.median([m[0] for m in mb])) if mb else None,
               bowl_mid_x=float(np.median([m[1] for m in mb])) if mb else None, x_dot_view=float(x0 @ view), z_dot_view=float(z @ view),
               y_spread_deg=float(np.degrees(np.median(np.arccos(np.clip(dirs @ y0, -1, 1))))) if len(dirs) else None)
    res.append(rec)
    with open(f'{OUT}/heldgeom_e{ep}.jsonl', 'a') as f: f.write(json.dumps(rec) + '\n')
    print(f"{ep} k{k}: rows {len(pts)} handle {keep.sum()} bowl {bowl.sum()} | axis rms {rec['axis_rms_mm']:.2f} hw {rec['handle_halfwidth_mm']:.1f} | "
          f"M1 y {mk[0][0]:+.1f} x {mk[0][1]:+.1f} s {mk[0][2]:.0f} | M2 y {mk[1][0]:+.1f} x {mk[1][1]:+.1f} s {mk[1][2]:.0f} | M3 y {mk[2][0]:+.1f} x {mk[2][1]:+.1f} s {mk[2][2]:.0f} | "
          f"bowl mid y {rec['bowl_mid_y']} x {rec['bowl_mid_x']} | x.view {rec['x_dot_view']:+.2f} z.view {rec['z_dot_view']:+.2f} ydisp {rec['y_spread_deg']}", flush=True)
