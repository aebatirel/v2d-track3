"""LOEO scoring with v2 features (out/feat2_<ep>.npy). For each held-out ep: train cam-a and b/c HistGradientBoosting models on
the sampled rows (det_<ep>.npz fidx/fw, labels >= 0) of the other eps; score ALL rows -> out/score_<ep>.npy (overwrites v1).
usage: det17score2.py ep1 ep2 ..."""
import sys, time, numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score, average_precision_score
eps = [int(e) for e in sys.argv[1:]]; t0 = time.time(); data = {}
for e in eps:
    d = np.load(f'out/det_{e}.npz'); F = np.load(f'out/feat2_{e}.npy', mmap_mode='r'); fi = d['fidx']
    data[e] = dict(rows=d['rows'], F=F, fi=fi, fw=d['fw'])
for E in eps:
    S = np.zeros(len(data[E]['rows']), np.float32)
    for grp, cis in (('a', [0]), ('bc', [1, 2])):
        X, y, w = [], [], []
        for e in eps:
            if e == E: continue
            q = data[e]; lab = q['rows'][q['fi'], 5]; m = (lab >= 0) & np.isin(q['rows'][q['fi'], 1], cis)
            X.append(np.asarray(q['F'][q['fi'][m]], np.float32)); y.append(lab[m].astype(int)); w.append(q['fw'][m])
        X, y, w = np.vstack(X), np.concatenate(y), np.concatenate(w)
        clf = HistGradientBoostingClassifier(max_iter=400, learning_rate=0.06, max_leaf_nodes=31, l2_regularization=1.0, min_samples_leaf=40, random_state=0).fit(X, y, sample_weight=w)
        q = data[E]; mm = np.isin(q['rows'][:, 1], cis); S[mm] = clf.predict_proba(np.asarray(q['F'][mm], np.float32))[:, 1]
        lab = q['rows'][q['fi'], 5]; ms = (lab >= 0) & np.isin(q['rows'][q['fi'], 1], cis); p = S[q['fi'][ms]]
        print(f'held-out {E} {grp}: train {len(y)} ({y.sum()} pos); held-out sampled AUC {roc_auc_score(lab[ms], p, sample_weight=q["fw"][ms]):.3f} AP {average_precision_score(lab[ms], p, sample_weight=q["fw"][ms]):.3f}; pos p>0.5 {np.mean(p[lab[ms]==1]>0.5):.2f}; {time.time()-t0:.0f}s', flush=True)
    np.save(f'out/score_{E}.npy', S)
print('done')
