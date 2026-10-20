"""Fresh-holdout scoring (stage B resume): train the v2 cam-a and b/c HistGradientBoosting models (same settings as
det17score2.py) on ALL training eps' sampled rows, score every candidate row of each holdout ep -> out/score_<ep>.npy.
usage: det17score_hold.py "12 26 21 0 31" 13 22"""
import sys, time, numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score, average_precision_score
train = [int(e) for e in sys.argv[1].split()]; hold = [int(e) for e in sys.argv[2:]]; t0 = time.time(); data = {}
for e in train + hold:
    d = np.load(f'out/det_{e}.npz'); F = np.load(f'out/feat2_{e}.npy', mmap_mode='r')
    data[e] = dict(rows=d['rows'], F=F, fi=d['fidx'], fw=d['fw'])
S = {E: np.zeros(len(data[E]['rows']), np.float32) for E in hold}
for grp, cis in (('a', [0]), ('bc', [1, 2])):
    X, y, w = [], [], []
    for e in train:
        q = data[e]; lab = q['rows'][q['fi'], 5]; m = (lab >= 0) & np.isin(q['rows'][q['fi'], 1], cis)
        X.append(np.asarray(q['F'][q['fi'][m]], np.float32)); y.append(lab[m].astype(int)); w.append(q['fw'][m])
    X, y, w = np.vstack(X), np.concatenate(y), np.concatenate(w)
    clf = HistGradientBoostingClassifier(max_iter=400, learning_rate=0.06, max_leaf_nodes=31, l2_regularization=1.0, min_samples_leaf=40, random_state=0).fit(X, y, sample_weight=w)
    for E in hold:
        q = data[E]; mm = np.isin(q['rows'][:, 1], cis); S[E][mm] = clf.predict_proba(np.asarray(q['F'][mm], np.float32))[:, 1]
        lab = q['rows'][q['fi'], 5]; ms = (lab >= 0) & np.isin(q['rows'][q['fi'], 1], cis); p = S[E][q['fi'][ms]]
        print(f'holdout {E} {grp}: train {len(y)} ({y.sum()} pos); sampled AUC {roc_auc_score(lab[ms], p, sample_weight=q["fw"][ms]):.3f} AP {average_precision_score(lab[ms], p, sample_weight=q["fw"][ms]):.3f}; pos p>0.5 {np.mean(p[lab[ms]==1]>0.5):.2f}; {time.time()-t0:.0f}s', flush=True)
for E in hold: np.save(f'out/score_{E}.npy', S[E])
print('done')
