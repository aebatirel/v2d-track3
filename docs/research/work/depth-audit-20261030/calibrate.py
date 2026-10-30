#!/usr/bin/env python3
"""Depth-audit calibration (GROUND-TRUTH SIDE, diagnostics only; run strictly after every audit has been written).

Joins the per-frame audit scores (pipeline/depth_audit.py -> AUDIT_ROOT/ep<N>/audit.npz, inference side, GT-free)
with the per-frame registered ADD of the same perception track against mocap (pipeline/score_registered.py
--per_frame -> LABELS/ep<N>_pf.npz, key perception_adds_cm = the kit's symmetric ADD, perception_add_cm = plain ADD)
and reports how well the audit separates frames with ADD > 2 cm. The rule is fixed in PREREG.md (this folder).

AUROC = Mann-Whitney U / (n_pos n_neg) with average ranks for ties (scipy.stats.rankdata), positives = ADD > thr.
95 % CI: episode-cluster bootstrap (episodes resampled with replacement, 2000 draws, seed 0), percentile interval.

Usage: python calibrate.py --audit_root audit/public --labels DIR [--labels_s2 DIR] --out calib
"""
import argparse
import csv
import json
import os

import numpy as np
from scipy.stats import rankdata, spearmanr

PRIMARY = [0, 2, 11, 12, 13, 18, 21, 22, 24, 26, 27, 31, 39, 40, 41, 42, 43, 44, 45]
SEPARATE = [23]
THIN = {'mini_sweeper', 'mini_dust_pan'}


def auroc(s, y):
    s, y = np.asarray(s, float), np.asarray(y, bool)
    ok = np.isfinite(s)
    s, y = s[ok], y[ok]
    n1, n0 = int(y.sum()), int((~y).sum())
    if n1 == 0 or n0 == 0:
        return np.nan, n1, n0
    r = rankdata(s)
    return float((r[y].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)), n1, n0


def boot_ci(per_ep, n=2000, seed=0):
    """per_ep: list of (scores, labels) per episode; resample episodes."""
    rng = np.random.default_rng(seed)
    k = len(per_ep)
    vals = []
    for _ in range(n):
        idx = rng.integers(0, k, k)
        s = np.concatenate([per_ep[i][0] for i in idx])
        y = np.concatenate([per_ep[i][1] for i in idx])
        v = auroc(s, y)[0]
        if np.isfinite(v):
            vals.append(v)
    if not vals:
        return None
    return [round(float(np.percentile(vals, 2.5)), 4), round(float(np.percentile(vals, 97.5)), 4), len(vals)]


def load(ep, a):
    A = np.load(os.path.join(a.audit_root, f'ep{ep}', 'audit.npz'), allow_pickle=False)
    L = np.load(os.path.join(a.labels, f'ep{ep}_pf.npz'), allow_pickle=False)
    S2 = np.load(os.path.join(a.labels_s2, f'ep{ep}_pf.npz'), allow_pickle=False) if a.labels_s2 else None
    an = [str(x) for x in A['names']]
    ln = [str(x) for x in L['names']]
    if sorted(an) != sorted(ln):
        raise SystemExit(f'ep{ep}: audit objects {an} != label objects {ln}')
    fa, fl = A['frames'], L['frames']
    j = np.searchsorted(fl, fa)
    if not (j < len(fl)).all() or not (fl[np.minimum(j, len(fl) - 1)] == fa).all():
        raise SystemExit(f'ep{ep}: audit frames not all in label frames')
    rows = []
    for b, n in enumerate(an):
        k = ln.index(n)
        col = dict(
            ep=np.full(len(fa), ep), frame=fa, obj=np.array([n] * len(fa)),
            valid=A['valid'][:, b], hidden=A['hidden'][:, b], n_sel=A['n_sel'][:, b], n_alone=A['n_alone'][:, b],
            behind=A['behind'][:, b], front=A['front'][:, b], behind_any=A['behind_any'][:, b],
            front_any=A['front_any'][:, b], med_r_cm=A['med_r_cm'][:, b], vis_frac=A['vis_frac'][:, b],
            hand_frac=A['hand_frac'][:, b], rest_mask=A['rest_mask'][:, b], rest_h_cm=A['rest_h_cm'][:, b],
            moving=A['moving'][:, b],
            adds_cm=L['perception_adds_cm'][j, k], add_cm=L['perception_add_cm'][j, k],
            pos_cm=L['perception_pos_cm'][j, k],
            adds_s2_cm=(S2['perception_adds_cm'][j, k] if S2 is not None else np.full(len(fa), np.nan)))
        rows.append(col)
    return {key: np.concatenate([r[key] for r in rows]) for key in rows[0]}


def scores(R):
    """name -> (score array, eligibility mask). Higher = more likely a tracking error."""
    v = R['valid']
    anyok = R['n_sel'] >= 50
    rest = R['rest_mask'] & np.isfinite(R['rest_h_cm'])
    return {
        'behind (PRIMARY)': (R['behind'], v),
        'front': (R['front'], v),
        'behind+front': (R['behind'] + R['front'], v),
        'abs_med_r': (np.abs(R['med_r_cm']), v),
        'behind_any': (R['behind_any'], anyok),
        'front_any': (R['front_any'], anyok),
        'behind_any+front_any': (R['behind_any'] + R['front_any'], anyok),
        '1-vis_frac': (1 - R['vis_frac'], R['n_alone'] > 0),
        'abs_rest_h (rest frames)': (np.abs(R['rest_h_cm']), rest),
    }


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--audit_root', required=True)
    p.add_argument('--labels', required=True)
    p.add_argument('--labels_s2', default=None)
    p.add_argument('--out', required=True)
    p.add_argument('--thr', type=float, default=2.0)
    p.add_argument('--boot', type=int, default=2000)
    p.add_argument('--episodes', default=None, help='override the primary set (testing only; the verdict uses PREREG)')
    p.add_argument('--separate', default=None)
    a = p.parse_args()
    global PRIMARY, SEPARATE
    if a.episodes:
        PRIMARY = [int(x) for x in a.episodes.split(',')]
    if a.separate is not None:
        SEPARATE = [int(x) for x in a.separate.split(',') if x]
    os.makedirs(a.out, exist_ok=True)
    eps = PRIMARY + SEPARATE
    D = {e: load(e, a) for e in eps}
    out = dict(rule='PREREG.md: informative iff pooled AUROC >= 0.75 with >= 8 primary episodes contributing a valid '
                    'positive; falsified iff < 0.65; else inconclusive', thr_cm=a.thr, primary_episodes=PRIMARY,
               separate=SEPARATE)

    def pooled(eplist, score_name, label_key, thr, obj_filter=None, boot=True):
        per = []
        for e in eplist:
            R = D[e]
            s, m = scores(R)[score_name]
            if obj_filter is not None:
                m = m & np.isin(R['obj'], list(obj_filter))
            y = R[label_key] > thr
            m = m & np.isfinite(R[label_key])
            per.append((s[m], y[m]))
        s = np.concatenate([x[0] for x in per]) if per else np.array([])
        y = np.concatenate([x[1] for x in per]) if per else np.array([], bool)
        v, n1, n0 = auroc(s, y)
        res = dict(auroc=None if not np.isfinite(v) else round(v, 4), n_pos=n1, n_neg=n0,
                   episodes_with_pos=int(sum(x[1].sum() > 0 for x in per)))
        if boot and np.isfinite(v):
            res['ci95'] = boot_ci([x for x in per if len(x[0])], a.boot)
        return res

    # --- primary
    prim = pooled(PRIMARY, 'behind (PRIMARY)', 'adds_cm', a.thr)
    v = prim['auroc']
    if v is None:
        verdict = 'inconclusive (no positives or no negatives)'
    elif v < 0.65:
        verdict = 'FALSIFIED (pooled AUROC < 0.65)'
    elif v >= 0.75 and prim['episodes_with_pos'] >= 8:
        verdict = 'INFORMATIVE (pooled AUROC >= 0.75, >= 8 episodes with positives)'
    else:
        verdict = 'INCONCLUSIVE (0.65 <= AUROC < 0.75, or < 8 episodes with positives)'
    out['primary'] = dict(prim, score='behind', label=f'symmetric registered ADD > {a.thr} cm', verdict=verdict)

    # --- hidden / ineligible accounting (primary set)
    tot = dict(object_frames=0, valid=0, hidden=0, small=0, pos_all=0, pos_valid=0, pos_hidden=0, pos_small=0)
    for e in PRIMARY:
        R = D[e]
        y = R['adds_cm'] > a.thr
        hid = R['hidden']
        small = ~hid & ~R['valid']
        tot['object_frames'] += len(y)
        tot['valid'] += int(R['valid'].sum())
        tot['hidden'] += int(hid.sum())
        tot['small'] += int(small.sum())
        tot['pos_all'] += int(y.sum())
        tot['pos_valid'] += int((y & R['valid']).sum())
        tot['pos_hidden'] += int((y & hid).sum())
        tot['pos_small'] += int((y & small).sum())
    tot['share_of_positives_hidden'] = round(tot['pos_hidden'] / max(tot['pos_all'], 1), 4)
    tot['positive_rate_valid'] = round(tot['pos_valid'] / max(tot['valid'], 1), 4)
    tot['positive_rate_hidden'] = round(tot['pos_hidden'] / max(tot['hidden'], 1), 4)
    out['accounting'] = tot

    # --- all scores x labels (pooled, primary set)
    labels = [('adds_cm', a.thr), ('add_cm', a.thr), ('adds_cm', 1.0), ('adds_cm', 3.0), ('adds_cm', 5.0)]
    if a.labels_s2:
        labels.insert(1, ('adds_s2_cm', a.thr))
    grid = {}
    for sn in scores(D[PRIMARY[0]]):
        for lk, th in labels:
            grid[f'{sn} | {lk}>{th:g}'] = pooled(PRIMARY, sn, lk, th, boot=(lk == 'adds_cm' and th == a.thr))
    out['grid'] = grid

    # --- per class
    classes = sorted({o for e in PRIMARY for o in np.unique(D[e]['obj'])})
    out['per_class'] = {}
    for c in classes:
        eps_c = [e for e in PRIMARY if c in set(D[e]['obj'])]
        r = pooled(eps_c, 'behind (PRIMARY)', 'adds_cm', a.thr, obj_filter={c})
        r['episodes'] = eps_c
        r['rule_applies'] = r['n_pos'] >= 30
        out['per_class'][c] = r
    eps_thin = [e for e in PRIMARY if THIN & set(D[e]['obj'])]
    out['per_class']['THIN (sweeper+dust pan)'] = dict(pooled(eps_thin, 'behind (PRIMARY)', 'adds_cm', a.thr,
                                                              obj_filter=THIN), episodes=eps_thin)

    # --- per episode
    pe = []
    within = []
    for e in eps:
        R = D[e]
        s, m = scores(R)['behind (PRIMARY)']
        y = R['adds_cm'] > a.thr
        v, n1, n0 = auroc(s[m], y[m])
        row = dict(ep=e, objects='+'.join(dict.fromkeys(R['obj'].tolist())), object_frames=int(len(y)),
                   valid=int(m.sum()), hidden=int(R['hidden'].sum()), pos_valid=n1, neg_valid=n0,
                   pos_hidden=int((y & R['hidden']).sum()), auroc=None if not np.isfinite(v) else round(v, 4),
                   behind_mean_valid=round(float(np.nanmean(s[m])), 4) if m.any() else None,
                   adds_median_cm=round(float(np.nanmedian(R['adds_cm'])), 3),
                   adds_p90_cm=round(float(np.nanpercentile(R['adds_cm'], 90)), 3),
                   auroc_any=None)
        s2, m2 = scores(R)['behind_any+front_any']
        v2 = auroc(s2[m2], y[m2])[0]
        row['auroc_behind_any+front_any'] = None if not np.isfinite(v2) else round(v2, 4)
        for b, o in enumerate(dict.fromkeys(R['obj'].tolist())):
            mo = m & (R['obj'] == o)
            vo = auroc(s[mo], y[mo])
            row[f'obj{b}'] = dict(name=o, auroc=None if not np.isfinite(vo[0]) else round(vo[0], 4), n_pos=vo[1],
                                  n_neg=vo[2], behind_mean=round(float(np.nanmean(s[mo])), 4) if mo.any() else None,
                                  share_adds_gt_thr=round(float(y[R['obj'] == o].mean()), 4))
        pe.append(row)
        if e in PRIMARY and n1 >= 10 and n0 >= 10:
            within.append(v)
    out['per_episode'] = pe
    out['within_episode_mean_auroc'] = dict(mean=round(float(np.mean(within)), 4) if within else None,
                                            n_episodes=len(within),
                                            values=[round(float(x), 4) for x in within])

    # --- episode-object level: does the mean score track the share of bad frames? (exploratory)
    xs, ys = [], []
    for e in PRIMARY:
        R = D[e]
        for o in dict.fromkeys(R['obj'].tolist()):
            mo = R['valid'] & (R['obj'] == o)
            if mo.sum() >= 20:
                xs.append(float(np.nanmean(R['behind'][mo])))
                ys.append(float((R['adds_cm'][R['obj'] == o] > a.thr).mean()))
    rho = spearmanr(xs, ys) if len(xs) >= 5 else None
    out['episode_object_spearman_behind_vs_bad_share'] = None if rho is None else dict(
        rho=round(float(rho.statistic), 4), p=round(float(rho.pvalue), 4), n=len(xs))

    json.dump(out, open(os.path.join(a.out, 'calib.json'), 'w'), indent=1)
    # CSVs
    keys = ['ep', 'objects', 'object_frames', 'valid', 'hidden', 'pos_valid', 'neg_valid', 'pos_hidden', 'auroc',
            'auroc_behind_any+front_any', 'behind_mean_valid', 'adds_median_cm', 'adds_p90_cm']
    with open(os.path.join(a.out, 'per_episode.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(keys + ['obj0', 'obj0_auroc', 'obj0_npos', 'obj0_behind_mean', 'obj1', 'obj1_auroc', 'obj1_npos',
                           'obj1_behind_mean'])
        for r in pe:
            extra = []
            for b in range(2):
                o = r.get(f'obj{b}')
                extra += [o['name'], o['auroc'], o['n_pos'], o['behind_mean']] if o else ['', '', '', '']
            w.writerow([r[k] for k in keys] + extra)
    cols = ['ep', 'frame', 'obj', 'valid', 'hidden', 'n_sel', 'behind', 'front', 'behind_any', 'front_any', 'med_r_cm',
            'vis_frac', 'hand_frac', 'rest_mask', 'rest_h_cm', 'moving', 'adds_cm', 'add_cm', 'adds_s2_cm']
    with open(os.path.join(a.out, 'per_frame.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(cols)
        for e in eps:
            R = D[e]
            for i in range(len(R['ep'])):
                w.writerow([(f'{R[c][i]:.4g}' if isinstance(R[c][i], (float, np.floating)) else
                             (int(R[c][i]) if isinstance(R[c][i], (bool, np.bool_)) else R[c][i])) for c in cols])
    print(json.dumps(dict(primary=out['primary'], accounting=out['accounting'],
                          within=out['within_episode_mean_auroc'],
                          spearman=out['episode_object_spearman_behind_vs_bad_share']), indent=1))


if __name__ == '__main__':
    main()
