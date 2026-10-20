"""Stage B retry (2026-10-06): split the s20 rest-snap gain into table height (z only) and stable face (tilt only).
Identical noise model, seeds and RNG stream as s20 (static on-table segments get a constant error; moving frames i.i.d.).
Modes: vision (no prior), z (z error -> 1 mm residual), tilt (rotation -> yaw part + 1 deg tilt residual), both (= s20
'prior'; checked against s20_rest_snap.json). Official kit score(), 20 public eps, 4 seeds, 2 noise levels. Research only."""
from sc11 import *
import json, os, sys
rest = json.load(open('s8_rest.json'))
old = json.load(open('s20_rest_snap.json'))
OUT = 's31_rest_split.json'
res = json.load(open(OUT)) if os.path.exists(OUT) else {}
LEVELS = [(0.01, 4), (0.02, 8)]
MODES = ("vision", "z", "tilt", "both")


def static_seg(ep, nm, T):
    seg = np.full(T, -1); k = 0
    for r in rest.get(nm, []):
        if r['ep'] == ep and r['zmin'] < 0.612:
            seg[r['f0']:r['f1'] + 1] = k; k += 1
    return seg


def yaw_part(dR):
    q = dR.as_quat(); q2 = np.array([0, 0, q[2], q[3]]); n = np.linalg.norm(q2)
    return Rot.from_quat(q2 / n) if n > 1e-12 else Rot.identity()


def perturb(p, names, ep, rng, s, a, mode):
    o = p.copy(); T = len(p)
    for j, nm in enumerate(names):
        seg = static_seg(ep, nm, T)
        for g in np.unique(seg[seg >= 0]):
            idx = np.where(seg == g)[0]
            dp = rng.normal(0, s, 3); ax = rng.normal(size=3); ax /= np.linalg.norm(ax)
            dR = Rot.from_rotvec(ax * np.radians(rng.normal(0, a)))
            zres = rng.normal(0, 0.001); h = rng.normal(size=2); h /= np.linalg.norm(h)
            tres = Rot.from_rotvec(np.r_[h, 0] * np.radians(rng.normal(0, 1.0)))
            if mode in ("z", "both"):
                dp[2] = zres
            if mode in ("tilt", "both"):
                dR = tres * yaw_part(dR)
            o[idx, j, :3] += dp
            o[idx, j, 3:] = (dR * Rot.from_quat(p[idx, j, 3:])).as_quat()
        mv = np.where(seg < 0)[0]
        if len(mv):
            o[mv, j, :3] += rng.normal(0, s, (len(mv), 3))
            ax = rng.normal(size=(len(mv), 3)); ax /= np.linalg.norm(ax, axis=1, keepdims=True)
            o[mv, j, 3:] = (Rot.from_rotvec(ax * np.radians(rng.normal(0, a, (len(mv), 1)))) * Rot.from_quat(p[mv, j, 3:])).as_quat()
    return o


for ep in PUBLIC:
    if str(ep) in res: continue
    e = load_episode(ep); p, nm = e['pose'], e['names']
    r = dict(task=e['task'])
    for s, a in LEVELS:
        lv = f"{s*100:g}cm_{a}deg"
        for mode in MODES:
            L = [score_all(perturb(p, nm, ep, np.random.default_rng(sd), s, a, mode), p, nm, ep) for sd in range(4)]
            r[f"{mode}_{lv}"] = mean_metrics(L)
        o = old[str(ep)]
        r[f"repro_{lv}"] = max(max(abs(r[f"vision_{lv}"][m] - o[f"vision_{lv}"][m]) for m in o[f"vision_{lv}"]),
                               max(abs(r[f"both_{lv}"][m] - o[f"prior_{lv}"][m]) for m in o[f"prior_{lv}"]))
    res[str(ep)] = r; json.dump(res, open(OUT, 'w'), indent=1)
    print(ep, e['task'], ' '.join(f"{k}:{v['AUC']:.3f}" if isinstance(v, dict) else f"{k}:{v:.1e}" for k, v in r.items() if k != 'task'))
    sys.stdout.flush()

if all(str(k) in res for k in PUBLIC):
    for s, a in LEVELS:
        lv = f"{s*100:g}cm_{a}deg"
        base = np.array([res[str(k)][f"vision_{lv}"]['AUC'] for k in PUBLIC])
        print(lv, "max repro diff vs s20:", max(res[str(k)][f"repro_{lv}"] for k in PUBLIC))
        for mode in MODES:
            v = mean_metrics([res[str(k)][f"{mode}_{lv}"] for k in PUBLIC])
            d = np.array([res[str(k)][f"{mode}_{lv}"]['AUC'] for k in PUBLIC]) - base
            print(f"  {mode:6s}", " ".join(f"{m}={v[m]:.3f}" for m in v),
                  f"| dAUC/ep min/med/max {d.min():+.3f} {np.median(d):+.3f} {d.max():+.3f}")
