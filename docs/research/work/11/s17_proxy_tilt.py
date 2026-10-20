"""Stage B1b/B2a. (1) Eval-order proxies: public twins re-ordered to the eval slot order (ev10 <- ep 11 with blue cup in
slot 0; ev19 <- ep 18 with sweeper in slot 0): spin-error curves + random baseline. (2) Anchor TILT error curve (constant
body-frame rotation of the slot-0 object about a world-horizontal axis at frame 0, mean over 8 azimuths) for every
public episode: value of a stable-rest-pose + table-plane prior that pins the anchor tilt to ~1 deg. Official score().
Research only."""
from sc11 import *
import json, os, sys
OUT = "s17_proxy_tilt.json"
res = json.load(open(OUT)) if os.path.exists(OUT) else {}


def reorder(e, order):
    e = dict(e); e['pose'] = e['pose'][:, order]; e['names'] = [e['names'][i] for i in order]; return e


if 'proxy' not in res:
    res['proxy'] = {}
    for tag, ep, sym in (("ev10<-ep11rev", 11, "C"), ("ev19<-ep18rev", 18, "2")):
        e = reorder(load_episode(ep), [1, 0]); p, nm = e['pose'], e['names']; ax = UP[nm[0]]
        S = lambda s: score_all(spin(p, 0, s, ax), p, nm, ep)
        r = dict(anchor=nm[0], sym=sym)
        r['curve'] = {d: (mean_metrics([S(d), S(-d)]) if d not in (0, 180) else S(d)) for d in [2, 5, 10, 15, 20, 30, 45, 90, 180]}
        r['random'] = mean_metrics([S(s) for s in np.arange(-180, 180, 5.0)]) if sym == "C" else mean_metrics([S(0), S(180)])
        res['proxy'][tag] = r; print(tag, json.dumps(r)[:1500]); sys.stdout.flush()
    json.dump(res, open(OUT, "w"), indent=1)

TILTS = [1, 2, 3, 5, 8]
res.setdefault('tilt', {})
for ep in PUBLIC:
    if str(ep) in res['tilt']: continue
    e = load_episode(ep); p, nm = e['pose'], e['names']
    R0 = R_of(p[0, 0, 3:])
    r = {}
    for t in TILTS:
        L = []
        for phi in np.radians(np.arange(0, 360, 45)):
            b = R0.T @ np.array([np.cos(phi), np.sin(phi), 0.0])
            L.append(score_all(spin(p, 0, t, b), p, nm, ep))
        r[t] = mean_metrics(L)
    res['tilt'][str(ep)] = dict(task=e['task'], anchor=nm[0], nobj=len(nm), **{str(k): v for k, v in r.items()})
    json.dump(res, open(OUT, "w"), indent=1)
    print(ep, e['task'], nm[0], " | ".join(f"{t}:" + "/".join(f"{v[m]:.2f}" for m in ("AUC", "SP-SR", "MP-SR", "RPE", "MPPE")) for t, v in r.items()))
    sys.stdout.flush()
