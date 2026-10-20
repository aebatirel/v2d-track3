# Local rectified vertical misalignment field dy(x, y) = y_b - y_c from LK matches over the whole frame, quadratic fit.
import sys, json, cv2, numpy as np
sys.path.insert(0, '.'); from b_lib import *
def dy_field(rc, rb, n=6000):
    p = cv2.goodFeaturesToTrack(rc, n, 0.002, 6, blockSize=7); init = p.copy(); init[:, 0, 0] -= 50
    lk = dict(winSize=(21, 21), maxLevel=4, criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 50, 0.005))
    pb, s1, _ = cv2.calcOpticalFlowPyrLK(rc, rb, p, init, flags=cv2.OPTFLOW_USE_INITIAL_FLOW, **lk)
    pc, s2, _ = cv2.calcOpticalFlowPyrLK(rb, rc, pb, None, **lk)
    q, qb, qc = p.reshape(-1, 2), pb.reshape(-1, 2), pc.reshape(-1, 2); d = q[:, 0] - qb[:, 0]
    ok = (s1[:, 0] & s2[:, 0]).astype(bool) & (np.linalg.norm(qc - q, axis=1) < 0.2) & (d > 3) & (d < 250) & (np.abs(qb[:, 1] - q[:, 1]) < 8)
    # keep only corner-like points (2-D localisable): min eigenvalue
    eig = cv2.cornerMinEigenVal(rc, 7); e = eig[q[:, 1].astype(int).clip(0, RSZ[1] - 1), q[:, 0].astype(int).clip(0, RSZ[0] - 1)]
    ok &= e > np.percentile(e[ok], 40)
    x, y, dyv = q[ok, 0], q[ok, 1], qb[ok, 1] - q[ok, 1]
    X = lambda x, y: np.c_[np.ones_like(x), x / 1000, y / 1000, (x / 1000) ** 2, x * y / 1e6, (y / 1000) ** 2]
    keep = np.ones(len(x), bool)
    for _ in range(4):
        cf = np.linalg.lstsq(X(x[keep], y[keep]), dyv[keep], rcond=None)[0]; r = dyv - X(x, y) @ cf
        keep = np.abs(r) < max(3 * 1.4826 * np.median(np.abs(r[keep])), 0.25)
    return (lambda xx, yy: X(np.atleast_1d(xx).astype(float), np.atleast_1d(yy).astype(float)) @ cf), dict(n=int(keep.sum()), rms=float(np.sqrt(np.mean(r[keep] ** 2))), x=x, y=y, dy=dyv, keep=keep)
if __name__ == '__main__':
    tag, k = sys.argv[1], int(sys.argv[2]); ep = int(tag[1:]); spl = 'public' if tag[0] == 'p' else 'evaluation'
    gb = cv2.cvtColor(read_frames(spl, ep, 'b', [k])[k], cv2.COLOR_BGR2GRAY); gc = cv2.cvtColor(read_frames(spl, ep, 'c', [k])[k], cv2.COLOR_BGR2GRAY)
    rc, rb = rect(gc, 'c'), rect(gb, 'b'); f, info = dy_field(rc, rb)
    print(tag, k, 'n', info['n'], 'resid rms', round(info['rms'], 3), 'global median', round(float(np.median(info['dy'])), 2))
    for yy in range(100, 1000, 150):
        print('  y', yy, ' '.join(f'{f(xx, yy)[0]:5.2f}' for xx in range(100, 1600, 150)))
    # binned raw medians for comparison
    for yy in range(100, 1000, 150):
        row = []
        for xx in range(100, 1600, 150):
            m = info['keep'] & (np.abs(info['x'] - xx) < 75) & (np.abs(info['y'] - yy) < 75)
            row.append(f'{np.median(info["dy"][m]):5.2f}' if m.sum() > 5 else '    .')
        print('  raw y', yy, ' '.join(row))
