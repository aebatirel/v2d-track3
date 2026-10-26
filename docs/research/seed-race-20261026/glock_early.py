"""Grasp-lock fine-tunes (70M steps): does the early checkpoint score predict the best of the checkpoint curve? (26 Oct,
companion of early_predict.py). Reads the 'glock epN: curve ...' lines of job logs (glock_public.sh; sim_vs_ref vs OUR
reference, GT-free). Logs: runs/<run>/job.log in the HF store for the runs of 23-26 Oct.
Usage: python glock_early.py LOG_DIR"""
import collections, glob, json, re, sys

import numpy as np

rows = {}
for f in glob.glob(f'{sys.argv[1]}/*.log'):
    run = f.split('/')[-1][:-4]
    for line in open(f, errors='ignore'):
        m = re.search(r'glock ep(\d+): curve (.*)', line)
        if m:
            c = {int(a): float(b) for a, b in re.findall(r'(\d+)M sim_vs_ref ([0-9.]+)', m.group(2))}
            if len(c) >= 4:
                rows[(run, int(m.group(1)), tuple(sorted(c.items())))] = c   # one copy of a curve logged twice
C = [(k[1], c) for k, c in rows.items()]


def at(c, frac):
    return c[min(c, key=lambda s: abs(s - frac * max(c)))]


def rank(x):
    return np.argsort(np.argsort(x))


e = np.array([at(c, 0.4) for _, c in C]); best = np.array([max(c.values()) for _, c in C])
by = collections.defaultdict(list)
for ep, c in C:
    by[ep].append(c)
ok = tot = 0
for R in by.values():
    for i in range(len(R)):
        for j in range(i + 1, len(R)):
            a, b = at(R[i], 0.4), at(R[j], 0.4)
            if abs(a - b) > 0.1:
                tot += 1; ok += (a > b) == (max(R[i].values()) > max(R[j].values()))
steps = [abs(b - a) for _, c in C for a, b in zip([c[k] for k in sorted(c)][:-1], [c[k] for k in sorted(c)][1:])]
print(json.dumps(dict(
    n_curves=len(C), n_episodes=len(by),
    pearson_40_best=round(float(np.corrcoef(e, best)[0, 1]), 3),
    spearman_40_best=round(float(np.corrcoef(rank(e), rank(best))[0, 1]), 3),
    same_episode_leader_at_40_gap_gt_0_1_has_better_best=f'{ok}/{tot}',
    mean_abs_change_between_checkpoints=round(float(np.mean(steps)), 3),
    best_checkpoint_position_p10_p25_p50_p75_p90=np.round(
        np.percentile([max(c, key=c.get) / max(c) for _, c in C], [10, 25, 50, 75, 90]), 2).tolist()), indent=1))
