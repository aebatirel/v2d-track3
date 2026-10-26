"""Loss budget of a packed submission (GT-free inputs + one leaderboard number). CPU, stdlib only.

Repeats the forensics-20261026 section-4 allocation on any pack: each eval episode scores sim_vs_ref x the mean public
perception accuracy of its objects (public midpoints, recorded in docs/analysis/forensics-20261026/README.md); the
spoon (no public mocap) is solved so that the 20-episode mean equals the leaderboard AUC. Also prints the policy loss
per episode ((1 - sim_vs_ref) / 20) and how much of the packed draw sits above or below the policy's 5-eval mean.
Usage: python3 loss_budget.py SUMMARY.txt LEADERBOARD_AUC [OUT.json]"""
import json
import re
import sys

OBJS = {1: ['pot', 'lid'], 3: ['pot', 'spoon'], 5: ['pot', 'spoon'], 6: ['pot', 'spoon'], 8: ['beige', 'pot'],
        10: ['blue', 'beige'], 14: ['blue', 'rack'], 15: ['rack', 'spoon'], 16: ['rack', 'spoon'],
        19: ['sweeper', 'pan'], 20: ['blue', 'pitcher'], 25: ['board', 'board'], 28: ['rack', 'pot'],
        30: ['sweeper', 'rack'], 32: ['blue', 'spoon'], 33: ['blue', 'spoon'], 35: ['spoon'], 36: ['spoon'],
        37: ['spoon'], 38: ['pan']}
# public perception accuracy midpoints (forensics-20261026 section 4; estimates, public twins vs mocap)
ACC = dict(pot=0.97, lid=0.965, blue=0.95, beige=0.93, rack=0.95, sweeper=0.96, pan=0.95, pitcher=0.66, board=0.82)
# 5-evaluation means of the packed policies (work log 24-26 Oct; None = not recorded in the repo)
MEAN5 = {10: 0.452, 14: 0.66, 25: 0.792, 32: 0.779, 33: 0.785, 1: 0.912, 3: 0.9285, 20: 0.892, 30: 0.919}


def model(svr, spoon):
    acc = dict(ACC, spoon=spoon)
    return sum(svr[e] * sum(acc[o] for o in OBJS[e]) / len(OBJS[e]) for e in OBJS) / len(OBJS)


def main():
    txt = open(sys.argv[1]).read()
    svr = {int(k): v for k, v in json.loads(re.search(r'\{.*\}', txt).group(0)).items()}
    lb = float(sys.argv[2])
    lo, hi = 0.0, 1.2
    for _ in range(60):  # bisection on the spoon accuracy
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if model(svr, mid) < lb else (lo, mid)
    spoon = (lo + hi) / 2
    acc = dict(ACC, spoon=spoon)
    rows = []
    for e in sorted(OBJS):
        a = sum(acc[o] for o in OBJS[e]) / len(OBJS[e])
        rows.append(dict(eval=e, sim_vs_ref=svr[e], policy_loss=round((1 - svr[e]) / 20, 4),
                         hidden_loss=round(svr[e] * (1 - a) / 20, 4), acc=round(a, 3),
                         draw_minus_mean5=None if e not in MEAN5 else round(svr[e] - MEAN5[e], 3)))
    out = dict(leaderboard=lb, mean_sim_vs_ref=round(sum(svr.values()) / 20, 4), implied_spoon_acc=round(spoon, 3),
               policy_loss=round(sum(r['policy_loss'] for r in rows), 4),
               hidden_loss=round(sum(r['hidden_loss'] for r in rows), 4),
               hidden_spoon_eps=round(sum(r['hidden_loss'] for r in rows if 'spoon' in OBJS[r['eval']]), 4),
               draw_luck=round(sum(r['draw_minus_mean5'] for r in rows if r['draw_minus_mean5'] is not None) / 20, 4),
               rows=rows)
    print(json.dumps({k: v for k, v in out.items() if k != 'rows'}, indent=1))
    for r in sorted(rows, key=lambda r: -(r['policy_loss'] + r['hidden_loss'])):
        print(r)
    if len(sys.argv) > 3:
        json.dump(out, open(sys.argv[3], 'w'), indent=1)


if __name__ == '__main__':
    main()
