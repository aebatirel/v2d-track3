# In-plane bend check from 3-D edge stereo: bowl silhouette centre (paired far/near points per row, s -115..-60 mm) relative to the
# handle axis line (paired handle limbs, s +100..+160) extrapolated. Positive = bowl toward M1's side.
import json, glob, numpy as np
OUT = '/Users/aebatirel/Documents/Code/v2d-research/work/20/out/b'
for f in sorted(glob.glob(f'{OUT}/estereo_e*_k*.json')):
    J = json.load(open(f)); R = np.array([[r['y'], r['side'], r['s'], r['w'], r['h']] for r in J['rows']]) if J['rows'] else None
    if R is None: continue
    sM = np.array(J['s_markers']); H, B = [], []
    for y in np.unique(R[:, 0]):
        m = R[:, 0] == y
        if m.sum() != 2: continue
        a, b = R[m]; wd = abs(a[3] - b[3]); s = (a[2] + b[2]) / 2; w = (a[3] + b[3]) / 2
        if sM[1] + 20 < s < sM[2] - 12 and 15 < wd < 25: H.append((s, w))
        if -115 < s < -60 and wd > 35: B.append((s, w))
    if len(H) < 20 or len(B) < 10: print(f.split('estereo_')[1][:-5], 'handle', len(H), 'bowl', len(B), '-> skip'); continue
    H, B = np.array(H), np.array(B); c = np.polyfit(H[:, 0], H[:, 1], 1)
    off = B[:, 1] - np.polyval(c, B[:, 0]); m3 = J['w_markers'][2] - np.polyval(c, sM[2])
    print(f"{f.split('estereo_')[1][:-5]:8s} handle {len(H)} slope {c[0]*1e3:+.1f} mm/m | bowl rows {len(B)} centre vs handle line {np.median(off):+.2f} "
          f"(IQR {np.percentile(off,25):+.1f}..{np.percentile(off,75):+.1f}) | M3 vs line {m3:+.1f} | lat M1 {J['w_markers'][0]-np.polyval(c, sM[0]):+.1f} M2 {J['w_markers'][1]-np.polyval(c, sM[1]):+.1f}")
