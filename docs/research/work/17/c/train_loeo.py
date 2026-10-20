"""Stage C: train + save the stage-B v2 LOEO detector models (cam a; cams b/c) for each held-out target episode.
Training data = sampled candidate rows of the OTHER public eps (out/det_<e>.npz, out/feat2_<e>.npy); target never used.
usage: c/train_loeo.py target1 target2 ...   -> c/clf_<target>.pkl {'a': model, 'bc': model}"""
import sys, time, pickle, numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
POOL = [12, 26, 21, 0, 31]; t0 = time.time(); data = {}
for e in POOL:
    d = np.load(f'out/det_{e}.npz'); F = np.load(f'out/feat2_{e}.npy', mmap_mode='r'); fi = d['fidx']
    data[e] = dict(lab=d['rows'][fi, 5], ci=d['rows'][fi, 1], F=np.asarray(F[fi], np.float32), fw=d['fw'])
for E in [int(x) for x in sys.argv[1:]]:
    out = {}
    for grp, cis in (('a', [0]), ('bc', [1, 2])):
        X, y, w = [], [], []
        for e in POOL:
            if e == E: continue
            q = data[e]; m = (q['lab'] >= 0) & np.isin(q['ci'], cis)
            X.append(q['F'][m]); y.append(q['lab'][m].astype(int)); w.append(q['fw'][m])
        X, y, w = np.vstack(X), np.concatenate(y), np.concatenate(w)
        out[grp] = HistGradientBoostingClassifier(max_iter=400, learning_rate=0.06, max_leaf_nodes=31, l2_regularization=1.0, min_samples_leaf=40, random_state=0).fit(X, y, sample_weight=w)
        print(E, grp, len(y), int(y.sum()), f'{time.time()-t0:.0f}s', flush=True)
    pickle.dump(out, open(f'c/clf_{E}.pkl', 'wb'))
print('done')
