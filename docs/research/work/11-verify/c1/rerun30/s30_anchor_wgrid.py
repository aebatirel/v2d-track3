"""Stage B retry (2026-10-06): (a) reproducibility check of s16 (cup anchors, official kit score()), (b) finer W grid.
Same error model as s16: achieved = GT except the slot-0 spin-symmetric cup carries a constant body spin about its rest-up
axis; spin error = (abs prior from the twin + w) - truth; '+-W' = mean over w = -W, +W. Also recomputes the random-spin
baseline for ep 12 (uniform over 72 spins) to compare with s16. Writes s30_anchor_wgrid.json (resumable). Research only."""
from sc11 import *
import json, os, sys, time

OUT = "s30_anchor_wgrid.json"
res = json.load(open(OUT)) if os.path.exists(OUT) else {}
old = json.load(open("s16_anchor_loo.json"))
CASES = {12: [13], 13: [12], 21: [22], 22: [21]}
WS = (0, 1, 3, 5, 10)
E = {}


def ep_(k):
    if k not in E: E[k] = load_episode(k)
    return E[k]


def yaw0(e, nm):
    j = e['names'].index(nm); return float(yaw_tilt(e['pose'][0, j, 3:], nm)[0])


def cmean(a):
    return float(np.degrees(np.angle(np.mean(np.exp(1j * np.radians(a))))))


for ep, twins in CASES.items():
    if str(ep) in res: print("skip", ep); continue
    t0 = time.time()
    e = ep_(ep); p, nm = e['pose'], e['names']; a = nm[0]; ax = UP[a]
    S = lambda s: score_all(spin(p, 0, s, ax), p, nm, ep)
    truth = yaw0(e, a); dprior = float(wrap(cmean([yaw0(ep_(t), a) for t in twins]) - truth))
    r = dict(anchor=a, abs_err=round(dprior, 2))
    for W in WS:
        r[f"abs_W{W}"] = mean_metrics([S(float(wrap(dprior + w))) for w in ((0,) if W == 0 else (-W, W))])
    if ep == 12:
        r["random"] = mean_metrics([S(s) for s in np.arange(-180, 180, 5.0)])
    # reproducibility vs s16
    o = old[str(ep)]
    r["repro_maxdiff"] = max(abs(r[k][m] - o[k][m]) for k in ("abs_W0", "abs_W3", "abs_W10") + (("random",) if ep == 12 else ())
                             for m in r[k])
    r["sec"] = round(time.time() - t0, 1)
    res[str(ep)] = r; json.dump(res, open(OUT, "w"), indent=1)
    print(ep, a, "abs_err", r["abs_err"], "repro_maxdiff", r["repro_maxdiff"], "sec", r["sec"])
    for W in WS:
        v = r[f"abs_W{W}"]; print(f"  W+-{W:<2}", " ".join(f"{m}={v[m]:.3f}" for m in v))
    sys.stdout.flush()

if all(str(k) in res for k in CASES):
    print("AGG cups 12/13/21/22 (mean over eps)")
    for W in WS:
        v = mean_metrics([res[str(k)][f"abs_W{W}"] for k in CASES])
        print(f"  W+-{W:<2}", " ".join(f"{m}={v[m]:.3f}" for m in v))
