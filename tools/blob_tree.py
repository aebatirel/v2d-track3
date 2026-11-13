#!/usr/bin/env python3
"""Pre-registered blob-feature decision tree vs the gate score (2026-11-12; rule: docs/work-log.md ~23:05 UTC).

Joins tools/blob_features.py rows with per-row labels (episode, object, frame, label 0/1) and runs:
  model     DecisionTreeClassifier(max_depth=3, min_samples_leaf=50, class_weight='balanced', random_state=0)
  eval      leave-one-episode-out; pooled out-of-fold AUROC; the gate score's AUROC on the same rows;
            difference with a 95% CI from 2,000 paired episode-bootstrap resamples (seed 20261112)
  verdict   adds value: OOF AUROC >= 0.75, difference >= 0.05, CI of the difference above 0
            no added value: difference < 0.02; otherwise inconclusive; inconclusive also when the positive share is
            < 10% or > 90%
Labels come from physics (test C: zero-residual replay vs our reference), not from ground truth.
Usage: blob_tree.py FEATURES.csv LABELS.csv OUT.json
"""
import csv, json, sys

import numpy as np
from sklearn.tree import DecisionTreeClassifier, export_text

FEATS = ['score', 'h_demand', 'h_up', 'gap', 'contacts', 'hands', 'F_N', 'tau_Nm']


def auroc(y, s):
    """Mann-Whitney AUROC with ties counted half; None when one class is missing."""
    y = np.asarray(y, int); s = np.asarray(s, float); pos, neg = s[y == 1], s[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return None
    order = np.argsort(np.concatenate([pos, neg]), kind='mergesort'); allv = np.concatenate([pos, neg])[order]
    ranks = np.empty(len(allv)); i = 0
    while i < len(allv):
        j = i
        while j + 1 < len(allv) and allv[j + 1] == allv[i]:
            j += 1
        ranks[i:j + 1] = (i + j) / 2 + 1; i = j + 1
    r = np.empty(len(allv)); r[order] = ranks
    return float((r[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def make_tree():
    return DecisionTreeClassifier(max_depth=3, min_samples_leaf=50, class_weight='balanced', random_state=0)


def run(feat_csv, lab_csv):
    F = {(r['episode'], r['object'], int(r['frame'])): r for r in csv.DictReader(open(feat_csv))}
    L = {(r['episode'], r['object'], int(r['frame'])): int(r['label']) for r in csv.DictReader(open(lab_csv))}
    keys = sorted(set(F) & set(L))
    if len(keys) != len(F) or len(keys) != len(L):
        raise SystemExit(f'row mismatch: features {len(F)}, labels {len(L)}, joined {len(keys)}')
    X = np.array([[float(F[k][f]) for f in FEATS] for k in keys]); y = np.array([L[k] for k in keys])
    ep = np.array([k[0] for k in keys]); eps = sorted(set(ep))
    oof = np.full(len(y), np.nan)
    for e in eps:
        tr, te = ep != e, ep == e
        if len(set(y[tr])) < 2:
            oof[te] = 0.5; continue
        oof[te] = make_tree().fit(X[tr], y[tr]).predict_proba(X[te])[:, 1]
    gate = X[:, 0]
    a_tree, a_gate = auroc(y, oof), auroc(y, gate)
    rng = np.random.default_rng(20261112); idx = {e: np.nonzero(ep == e)[0] for e in eps}; diffs = []
    for _ in range(2000):
        pick = np.concatenate([idx[e] for e in rng.choice(eps, len(eps), replace=True)])
        at, ag = auroc(y[pick], oof[pick]), auroc(y[pick], gate[pick])
        if at is not None and ag is not None:
            diffs.append(at - ag)
    lo, hi = (np.percentile(diffs, [2.5, 97.5]).tolist() if diffs else [None, None])
    share = float(y.mean()); d = None if a_tree is None or a_gate is None else a_tree - a_gate
    if share < 0.10 or share > 0.90 or d is None:
        verdict = 'inconclusive (positive share outside 10-90% or a class missing)'
    elif a_tree >= 0.75 and d >= 0.05 and lo is not None and lo > 0:
        verdict = 'adds value'
    elif d < 0.02:
        verdict = 'no added value'
    else:
        verdict = 'inconclusive'
    full = make_tree().fit(X, y)
    return dict(rows=int(len(y)), episodes=len(eps), positive_share=round(share, 4),
                episodes_with_positives=int(sum(y[ep == e].any() for e in eps)),
                auroc_tree_oof=None if a_tree is None else round(a_tree, 4), auroc_gate=None if a_gate is None else round(a_gate, 4),
                diff=None if d is None else round(d, 4), diff_ci95=[None if v is None else round(v, 4) for v in (lo, hi)],
                bootstrap_valid=len(diffs), verdict=verdict,
                tree_all_rows=export_text(full, feature_names=FEATS, decimals=3),
                importances=dict(zip(FEATS, np.round(full.feature_importances_, 4).tolist())))


if __name__ == '__main__':
    out = run(sys.argv[1], sys.argv[2])
    json.dump(out, open(sys.argv[3], 'w'), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != 'tree_all_rows'}, indent=1)); print(out['tree_all_rows'])
