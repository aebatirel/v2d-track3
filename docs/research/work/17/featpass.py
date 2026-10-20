"""v2 features for ALL candidate rows of out/det_<ep>.npz -> out/feat2_<ep>.npy (float16). usage: featpass.py ep"""
import sys, time, numpy as np, cv2
cv2.setNumThreads(2)
import lib17 as L, det17lib as D
ep = int(sys.argv[1]); d = np.load(f'out/det_{ep}.npz'); rows = d['rows']; t0 = time.time()
F = np.zeros((len(rows), 188), np.float16); vids = {c: L.Video(ep, c) for c in 'abc'}
order = np.lexsort((rows[:, 1], rows[:, 0])); keys = np.unique(rows[:, :2], axis=0)
for t, ci in keys:
    t, ci = int(t), int(ci); c = 'abc'[ci]; m = np.flatnonzero((rows[:, 0] == t) & (rows[:, 1] == ci))
    BGR = vids[c].get(t); G = cv2.cvtColor(BGR, cv2.COLOR_BGR2GRAY)
    P = D.prep_image(G, BGR if c == 'a' else None); F[m] = D.features2(P, rows[m][:, 2:5].astype(np.float64)).astype(np.float16)
np.save(f'out/feat2_{ep}.npy', F); print('done', ep, len(rows), f'{time.time()-t0:.0f}s')
