# Stage A2: sub-frame time offset between streams from angular-velocity series (no GT).
# Model: w_X[k] = R_XY w_Y(k + s), s in frames; offset o_X - o_Y = s * 50 ms
# (positive => frame k of X was captured LATER than frame k of Y).
# Usage: a_sync.py <npzkey e.g. p11> [pairs=ab,cb,ac] [--band]
import sys, json, numpy as np
from scipy.interpolate import CubicSpline
from scipy.spatial.transform import Rotation as Rr
OUT = '/Users/aebatirel/Documents/Code/v2d-research/work/20/out'
CAL = json.load(open('/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public/meta/camera_calibration.json'))['cameras']
DT = 50.0

def kabsch(A, B):
    # R minimising |A - R B|^2  (rows are vectors)
    H = B.T @ A
    U, S, Vt = np.linalg.svd(H)
    d = np.sign(np.linalg.det(Vt.T @ U.T))
    return Vt.T @ np.diag([1, 1, d]) @ U.T

def fit_shift(wX, wY, grid=np.arange(-3, 3.0001, 0.01), fixR=None, idx=None, cw=None):
    # cw: optional per-component weights on the X-frame residual (e.g. [1,1,0] = pan/tilt only)
    cw = np.ones(3) if cw is None else np.asarray(cw, float)
    k = np.arange(len(wX), dtype=float)
    good = np.isfinite(wX).all(1) & np.isfinite(wY).all(1)
    kk = k[good]
    spl = CubicSpline(kk, wY[good], axis=0, extrapolate=False)
    costs = []; Rs = []
    for s in grid:
        q = kk + s
        m = (q >= kk[0]) & (q <= kk[-1])
        if idx is not None: m &= np.isin(kk, idx)
        A = wX[good][m]; B = spl(q[m])
        R = kabsch(A, B) if fixR is None else fixR
        e = A - B @ R.T
        costs.append(np.sum((e * cw) ** 2) / max(np.sum((A * cw) ** 2), 1e-12)); Rs.append(R)
    costs = np.array(costs); i = int(np.argmin(costs))
    # parabolic refinement
    if 0 < i < len(grid) - 1:
        c0, c1, c2 = costs[i - 1:i + 2]; den = c0 - 2 * c1 + c2
        ds = 0.5 * (c0 - c2) / den if den > 0 else 0.0
    else: ds = 0.0
    s = grid[i] + ds * (grid[1] - grid[0])
    return s, costs[i], Rs[i], costs

def calR(X, Y):
    # rotation such that w_X = R w_Y, from calibration (b is the reference: E_a: a->b, E_c: c->b)
    def toB(c):
        if c == 'b': return np.eye(3)
        return np.array(CAL[f'ego_cam_{c}']['extrinsics_to_stereo_left'])[:3, :3]
    return toB(X).T @ toB(Y)

if __name__ == '__main__':
    key = sys.argv[1]; pairs = (sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith('-') else 'ab,cb,ac').split(',')
    z = np.load(f'{OUT}/motion/{key}.npz')
    res = {}
    for p in pairs:
        X, Y = p[0], p[1]
        wX, wY = z[f'{X}_rv'], z[f'{Y}_rv']
        n = len(wX)
        s, c, R, costs = fit_shift(wX, wY)
        Rc = calR(X, Y)
        dR = np.degrees(np.linalg.norm(Rr.from_matrix(R @ Rc.T).as_rotvec()))
        sc, cc, _, _ = fit_shift(wX, wY, fixR=Rc)
        # blocks: quarters
        blocks = []
        for q in range(4):
            idx = np.arange(q * n // 4, (q + 1) * n // 4)
            sb, cb, _, _ = fit_shift(wX, wY, idx=idx)
            blocks.append(round(sb * DT, 2))
        mag = np.degrees(np.nanmedian(np.linalg.norm(wX, axis=1))) * 20
        res[p] = dict(ms=s * DT, cost=c, ms_calR=sc * DT, cost_calR=cc, dR_cal_deg=dR, blocks_ms=blocks,
                      cost0=float(costs[np.argmin(np.abs(np.arange(-3, 3.0001, 0.01)))]), med_w_dps=mag)
        print(f'{key} {X}-{Y}: offset {s*DT:+7.2f} ms (cost {c:.4f}; at 0: {res[p]["cost0"]:.4f}) | calR {sc*DT:+7.2f} ms '
              f'(cost {cc:.4f}) | R vs cal {dR:.2f} deg | quarters {blocks} | med|w| {mag:.1f} deg/s', flush=True)
    json.dump(res, open(f'{OUT}/sync_{key}.json', 'w'), indent=1)
