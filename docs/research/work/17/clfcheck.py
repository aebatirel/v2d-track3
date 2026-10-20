import sys, numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score, average_precision_score
eps = [12, 26, 21, 0, 31]
def load(e, cis):
    d = np.load(f'out/det_{e}.npz'); r = d['rows']; fi = d['fidx']; lab = r[fi, 5]; ci = r[fi, 1]; m = (lab >= 0) & np.isin(ci, cis)
    return d['F'][m].astype(np.float32), lab[m].astype(int), d['fw'][m], r[fi][m]
for grp, cis in (('a', [0]), ('bc', [1, 2])):
    for E in eps:
        tr = [load(e, cis) for e in eps if e != E]; X = np.vstack([t[0] for t in tr]); y = np.concatenate([t[1] for t in tr]); w = np.concatenate([t[2] for t in tr])
        clf = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.08, max_leaf_nodes=31, l2_regularization=1.0, random_state=0).fit(X, y, sample_weight=w)
        Xt, yt, wt, rt = load(E, cis); p = clf.predict_proba(Xt)[:, 1]
        roi = rt[:, 7] > 0
        print(f'{grp} held-out {E}: n {len(yt)} pos {yt.sum()} AUC {roc_auc_score(yt, p, sample_weight=wt):.3f} AP(w) {average_precision_score(yt, p, sample_weight=wt):.3f} AP roi {average_precision_score(yt[roi], p[roi], sample_weight=wt[roi]):.3f}; train AP {average_precision_score(y, clf.predict_proba(X)[:,1], sample_weight=w):.3f}; pos with p>0.5 {np.mean(p[yt==1]>0.5):.2f}', flush=True)
