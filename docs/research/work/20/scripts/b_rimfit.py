# Rest roll from the FAR bowl rim only (the far silhouette is the true rim; the near one is the wall): fit h = a + b s + c w to
# far-side bowl edge points (s in [-132, -40] mm from mid(M1,M2), w > 0 = M1 side). roll = atan(c) (M1 side up if > 0),
# pitch = atan(b). Bootstrap over rows for the SE.
import json, sys, glob, numpy as np
OUT = '/Users/aebatirel/Documents/Code/v2d-research/work/20/out/b'
rng = np.random.default_rng(0); allr = []
for f in sorted(glob.glob(f'{OUT}/estereo_e*_k*.json')):
    J = json.load(open(f)); R = np.array([[r['s'], r['w'], r['h']] for r in J['rows']]) if J['rows'] else np.zeros((0, 3))
    m = (R[:, 0] > -132) & (R[:, 0] < -40) & (R[:, 1] > 5) if len(R) else np.zeros(0, bool)
    if m.sum() < 25: continue
    X = R[m]; A = np.c_[np.ones(len(X)), X[:, 0], X[:, 1]]
    keep = np.ones(len(X), bool)
    for _ in range(3):
        cf = np.linalg.lstsq(A[keep], X[keep, 2], rcond=None)[0]; r = X[:, 2] - A @ cf; keep = np.abs(r) < max(3 * 1.4826 * np.median(np.abs(r[keep])), 1.0)
    bs = []
    for _ in range(300):
        i = rng.choice(np.nonzero(keep)[0], keep.sum()); bs.append(np.linalg.lstsq(A[i], X[i, 2], rcond=None)[0])
    bs = np.array(bs); roll = np.degrees(np.arctan(cf[2])); pitch = np.degrees(np.arctan(cf[1]))
    sr = np.degrees(np.arctan(bs[:, 2])).std(); sp = np.degrees(np.arctan(bs[:, 1])).std()
    tag = f.split('estereo_')[1][:-5]; allr.append((tag, roll, sr, pitch, sp, cf[0], keep.sum(), np.ptp(X[keep, 1])))
    print(f'{tag:8s} n {keep.sum():3d} w-range {np.ptp(X[keep,1]):4.1f} mm | roll {roll:+5.1f} +- {sr:.1f} deg | pitch {pitch:+5.1f} +- {sp:.1f} deg | a {cf[0]:5.1f} mm | res {np.sqrt(np.mean(r[keep]**2)):.2f} mm')
