"""Stage B1: LOO value of a task yaw prior for a symmetric slot-0 anchor, official kit score() for all 5 metrics.
Achieved = GT except the slot-0 anchor carries a constant body spin about its rest-up symmetry axis (UP) in every frame.
Continuous (C) anchors: spin error = (prior + w) - truth. Two-fold (2) anchors: geometry gives the axis exactly; the
prior (+w) only picks the branch {truth, truth+180}. Random: C = uniform over 72 spins; 2 = 50/50 branch.
W (world-yaw knowledge error) in {0, +-3, +-10}: '+-' results are the mean of both signs. Research only."""
from sc11 import *
import json, os, sys

OUT = "s16_anchor_loo.json"
res = json.load(open(OUT)) if os.path.exists(OUT) else {}
CASES = {11: ("C", []), 12: ("C", [13]), 13: ("C", [12]), 21: ("C", [22]), 22: ("C", [21]),
         23: ("2", [24]), 24: ("2", [23]), 26: ("2", [27, 12, 13, 31]), 27: ("2", [26, 12, 13, 31]),
         31: ("2", [18])}   # 26/27 rack + 31 sweeper: cross-task abs prior from every other ep holding that object
CURVE = [0, 2, 5, 10, 15, 20, 30, 45, 60, 90, 135, 180]
E = {}


def ep_(k):
    if k not in E: E[k] = load_episode(k)
    return E[k]


def yaw0(e, nm):
    j = e['names'].index(nm); return float(yaw_tilt(e['pose'][0, j, 3:], nm)[0])


def bearing0(e):
    p = e['pose'][0]; d = p[1, :2] - p[0, :2]; return float(np.degrees(np.arctan2(d[1], d[0])))


def cmean(a):
    return float(np.degrees(np.angle(np.mean(np.exp(1j * np.radians(a))))))


for ep, (sym, twins) in CASES.items():
    if str(ep) in res: print("skip", ep); continue
    e = ep_(ep); p, nm = e['pose'], e['names']; a = nm[0]; ax = UP[a]
    r = dict(task=e['task'], anchor=a, sym=sym, twins=twins)
    S = lambda s: score_all(spin(p, 0, s, ax), p, nm, ep)
    # sign check: spin about UP by +s raises the anchor yaw by ~s
    chk = float(wrap(yaw_tilt(spin(p, 0, 20, ax)[0, 0, 3:], a)[0] - yaw0(e, a)))
    r['signcheck_spin20_dyaw'] = round(chk, 2)
    r['curve'] = {d: mean_metrics([S(d), S(-d)]) if d not in (0, 180) else S(d) for d in CURVE}
    if sym == "C":
        r['random'] = mean_metrics([S(s) for s in np.arange(-180, 180, 5.0)])
    else:
        r['random'] = mean_metrics([S(0), S(180)])
    if twins:
        truth = yaw0(e, a)
        prior_abs = cmean([yaw0(ep_(t), a) for t in twins])
        dprior = float(wrap(prior_abs - truth))            # estimate - truth before W
        r['abs_prior'] = round(prior_abs, 2); r['abs_err'] = round(dprior, 2)
        for W in (0, 3, 10):
            L = []
            for w in ((0,) if W == 0 else (-W, W)):
                err = float(wrap(dprior + w))
                if sym == "2":
                    err = 0.0 if abs(err) < 90 else 180.0
                L.append(S(err))
            r[f'abs_W{W}'] = mean_metrics(L)
        if sym == "C" and len(nm) == 2:   # world-free priors from the twin (as in s15) for comparison
            def rel(x): return float(wrap(yaw0(x, a) - yaw0(x, x['names'][1])))
            def brg(x): return float(wrap(yaw0(x, a) - bearing0(x)))
            for k, f in (("rel", rel), ("brg", brg)):
                d = float(wrap(cmean([f(ep_(t)) for t in twins]) - f(e)))
                r[f'{k}_err'] = round(d, 2); r[k] = S(d)
        if sym == "2":
            r['margin_deg'] = round(90 - abs(dprior), 1)
    res[str(ep)] = r
    json.dump(res, open(OUT, "w"), indent=1)
    show = {k: v for k, v in r.items() if k not in ('curve',)}
    print(ep, json.dumps(show)[:900]); sys.stdout.flush()
