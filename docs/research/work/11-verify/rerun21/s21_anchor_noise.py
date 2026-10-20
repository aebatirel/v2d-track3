"""Stage B1c: does the anchor-yaw prior gain survive realistic tracking noise? Anchor spin error (random vs abs prior
with W=+-3, from s16) composed with the s20 noise model (1 cm / 4 deg, rest prior ON) on all objects; 4 seeds.
C anchors: random = 36 spins (10-deg grid). 2-fold: random = {0, 180}. Official score(). Research only."""
from sc11 import *
import json, sys
src = open('s20_rest_snap.py').read().split("for ep in PUBLIC:")[0]
exec(src)
L16 = json.load(open('s16_anchor_loo.json'))
out = {}
for ep in [12, 13, 21, 22, 23, 24, 26, 27]:
    x = L16[str(ep)]; e = load_episode(ep); p, nm = e['pose'], e['names']; ax = UP[nm[0]]
    def run(spins):
        R = []
        for sd in range(4):
            for s in spins:
                R.append(score_all(perturb(spin(p, 0, s, ax), nm, ep, np.random.default_rng(sd), 0.01, 4, True), p, nm, ep))
        return mean_metrics(R)
    rnd = list(np.arange(-180, 180, 10.0)) if x['sym'] == "C" else [0.0, 180.0]
    if x['sym'] == "C":
        pri = [float(wrap(x['abs_err'] + w)) for w in (-3, 3)]
    else:
        pri = [0.0]
    out[ep] = dict(sym=x['sym'], random=run(rnd), absW3=run(pri))
    print(ep, x['sym'], {k: {m: round(v[m], 3) for m in v} for k, v in out[ep].items() if isinstance(v, dict)}); sys.stdout.flush()
    json.dump(out, open('s21_anchor_noise.json', 'w'), indent=1)
