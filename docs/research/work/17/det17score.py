"""Stage B detector pass 2: leave-one-episode-out classifier (HistGradientBoosting, one model for cam a and one for b/c)
trained on the sampled candidate features of the OTHER episodes (det_<ep>.npz), then scores ALL candidates of the held-out
episode (features recomputed from the video). usage: det17score.py heldout ep1 ep2 ...  -> out/score_<heldout>.npy"""
import sys, time, numpy as np, cv2
cv2.setNumThreads(2)
from sklearn.ensemble import HistGradientBoostingClassifier
import lib17 as L, det17lib as D
E = int(sys.argv[1]); others = [int(e) for e in sys.argv[2:] if int(e) != E]; t0 = time.time()
models = {}
for grp, cis in (('a', [0]), ('bc', [1, 2])):
    X, y, w = [], [], []
    for e in others:
        d = np.load(f'out/det_{e}.npz'); rows = d['rows']; fi = d['fidx']; lab = rows[fi, 5]; ci = rows[fi, 1]
        m = (lab >= 0) & np.isin(ci, cis)
        X.append(d['F'][m].astype(np.float32)); y.append(lab[m].astype(int)); w.append(d['fw'][m])
    X, y, w = np.vstack(X), np.concatenate(y), np.concatenate(w)
    clf = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.08, max_leaf_nodes=31, l2_regularization=1.0, random_state=0)
    clf.fit(X, y, sample_weight=w); models[grp] = clf
    print(f'held-out {E}: model {grp} trained on {len(y)} samples ({y.sum()} pos) from eps {others}; {time.time()-t0:.0f}s', flush=True)
d = np.load(f'out/det_{E}.npz'); rows = d['rows']; S = np.zeros(len(rows), np.float32)
vids = {c: L.Video(E, c) for c in 'abc'}
keys = np.unique(rows[:, :2], axis=0)
for t, ci in keys:
    t, ci = int(t), int(ci); c = 'abc'[ci]; m = np.flatnonzero((rows[:, 0] == t) & (rows[:, 1] == ci))
    BGR = vids[c].get(t); G = cv2.cvtColor(BGR, cv2.COLOR_BGR2GRAY); H = rows[m][:, 2:5].astype(float)
    F = D.features(G, BGR if c == 'a' else None, np.c_[H, np.zeros(len(H)), np.ones(len(H))]).astype(np.float16).astype(np.float32)
    S[m] = models['a' if ci == 0 else 'bc'].predict_proba(F)[:, 1]
np.save(f'out/score_{E}.npy', S); print('done', time.time() - t0)
