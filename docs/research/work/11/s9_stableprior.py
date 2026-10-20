"""Value of a stable-pose prior (table height + discrete tilt from public GT) on static on-table segments.
Noise model: per static segment constant error (pos sigma 1 cm/axis, rot 4 deg about a random axis), applied to
every object incl. slot 0 frame 0. 'prior' variant removes the z and tilt components (keeps x, y, yaw error).
Moving frames get i.i.d. 1 cm / 4 deg noise in both variants. Official scorer functions."""
from c11 import *
import json
exec(open('s3_loo.py').read().split("CUPEPS = ")[0])
rest = json.load(open('s8_rest.json'))
def static_mask(ep, nm, T):
    m = np.zeros(T, bool); seg = np.zeros(T, int) - 1; k = 0
    for r in rest.get(nm, []):
        if r['ep'] == ep and r['zmin'] < 0.612:
            m[r['f0']:r['f1'] + 1] = True; seg[r['f0']:r['f1'] + 1] = k; k += 1
    return m, seg
def perturb(p, names, ep, rng, prior):
    o = p.copy(); T = len(p)
    for j, nm in enumerate(names):
        m, seg = static_mask(ep, nm, T)
        up_w = None
        for t in range(T):
            pass
        # per-segment constant errors
        for s in np.unique(seg[seg >= 0]):
            idx = np.where(seg == s)[0]
            dp = rng.normal(0, 0.01, 3); ax = rng.normal(size=3); ax /= np.linalg.norm(ax); ang = np.radians(rng.normal(0, 4))
            if prior:
                dp[2] = 0; ax = np.array([0, 0, 1.0])  # keep only yaw component (world vertical) of the error
                ang = ang * 1.0
            dR = Rot.from_rotvec(ax * ang)
            o[idx, j, :3] += dp
            o[idx, j, 3:] = (dR * Rot.from_quat(p[idx, j, 3:])).as_quat()
        mv = np.where(seg < 0)[0]
        if len(mv):
            o[mv, j, :3] += rng.normal(0, 0.01, (len(mv), 3))
            ax = rng.normal(size=(len(mv), 3)); ax /= np.linalg.norm(ax, axis=1, keepdims=True)
            o[mv, j, 3:] = (Rot.from_rotvec(ax * np.radians(rng.normal(0, 4, (len(mv), 1)))) * Rot.from_quat(p[mv, j, 3:])).as_quat()
    return o
res = {}
for ep in PUBLIC:
    e = load_episode(ep); p, nm = e['pose'], e['names']
    T = len(p); frac = np.mean([static_mask(ep, n, T)[0].mean() for n in nm])
    r = {}
    for prior in (False, True):
        L = [metrics(perturb(p, nm, ep, np.random.default_rng(s), prior), p, nm) for s in range(6)]
        r['prior' if prior else 'noprior'] = {k: float(np.mean([d[k] for d in L])) for k in L[0]}
    res[ep] = r
    print(f"ep{ep:2d} static-frac {frac:.2f}  no-prior " + " ".join(f"{k}={v:.3f}" for k, v in r['noprior'].items()) + "  | prior " + " ".join(f"{k}={v:.3f}" for k, v in r['prior'].items()))
for k in ('noprior', 'prior'):
    print(k, " ".join(f"{m}={np.mean([res[e][k][m] for e in res]):.3f}" for m in res[PUBLIC[0]][k]))
json.dump(res, open('s9_stableprior.json', 'w'), indent=1)
