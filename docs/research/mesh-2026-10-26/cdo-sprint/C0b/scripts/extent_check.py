"""[M] GT-free pre-check for the C0b ROI cube: max |coordinate| of our own C0/obs_all observed points about the
track-frame origin, per object-episode, and the 99.9th percentile of |coordinate| per axis. Reads only our npz pts."""
import glob, json, os, sys
import numpy as np
rows = []
for f in sorted(glob.glob(sys.argv[1] + '/ep*_*.npz')):
    Z = np.load(f)
    P = Z['pts'].astype(np.float64)
    a = np.abs(P)
    rows.append(dict(file=os.path.basename(f), n=int(len(P)), max_abs_mm=[round(float(x) * 1e3, 1) for x in a.max(0)],
                     p999_abs_mm=[round(float(x) * 1e3, 1) for x in np.quantile(a, 0.999, axis=0)],
                     lo_mm=[round(float(x) * 1e3, 1) for x in Z['lo']], hi_mm=[round(float(x) * 1e3, 1) for x in Z['hi']]))
for r in rows:
    print(json.dumps(r))
print('MAX over all files (mm):', max(max(r['max_abs_mm']) for r in rows))
