"""Stage B2c: value of the table-height + stable-rest-pose prior on static on-table segments, official score(), at three
vision noise levels. Per static on-table segment (s8, zmin < 0.612 m) every object gets a constant error (pos sigma s per
axis, rotation sigma a about a random axis); moving frames get i.i.d. noise of the same sigmas. 'prior' replaces the z and
tilt parts of each static-segment error by the residual of snapping to (table plane + stable face): z sigma 1 mm and tilt
sigma 1 deg about a random horizontal axis ([E] our own table-plane fit error; the GT rest spread itself is <=0.5 mm /
<=0.5 deg, s8), keeping the x, y and yaw (world-z rotation) parts. 4 seeds per level. Research only."""
from sc11 import *
import json, os, sys
rest = json.load(open('s8_rest.json'))
OUT = 's20_rest_snap.json'
res = json.load(open(OUT)) if os.path.exists(OUT) else {}
LEVELS = [(0.005, 2), (0.01, 4), (0.02, 8)]


def static_seg(ep, nm, T):
    seg = np.full(T, -1); k = 0
    for r in rest.get(nm, []):
        if r['ep'] == ep and r['zmin'] < 0.612:
            seg[r['f0']:r['f1'] + 1] = k; k += 1
    return seg


def yaw_part(dR):
    """rotation about world z closest to dR (twist about z)."""
    q = dR.as_quat(); q2 = np.array([0, 0, q[2], q[3]]); n = np.linalg.norm(q2)
    return Rot.from_quat(q2 / n) if n > 1e-12 else Rot.identity()


def perturb(p, names, ep, rng, s, a, prior):
    o = p.copy(); T = len(p)
    for j, nm in enumerate(names):
        seg = static_seg(ep, nm, T)
        for g in np.unique(seg[seg >= 0]):
            idx = np.where(seg == g)[0]
            dp = rng.normal(0, s, 3); ax = rng.normal(size=3); ax /= np.linalg.norm(ax)
            dR = Rot.from_rotvec(ax * np.radians(rng.normal(0, a)))
            # independent draws for the prior residual (drawn in both branches to keep the RNG streams aligned)
            zres = rng.normal(0, 0.001); h = rng.normal(size=2); h /= np.linalg.norm(h)
            tres = Rot.from_rotvec(np.r_[h, 0] * np.radians(rng.normal(0, 1.0)))
            if prior:
                dp[2] = zres; dR = tres * yaw_part(dR)
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
    e = load_episode(ep); p, nm = e['pose'], e['names']; T = len(p)
    frac = float(np.mean([(static_seg(ep, n, T) >= 0).mean() for n in nm]))
    r = dict(task=e['task'], static_frac=round(frac, 3))
    for s, a in LEVELS:
        for prior in (False, True):
            L = [score_all(perturb(p, nm, ep, np.random.default_rng(sd), s, a, prior), p, nm, ep) for sd in range(4)]
            r[f"{'prior' if prior else 'vision'}_{s*100:g}cm_{a}deg"] = mean_metrics(L)
    res[str(ep)] = r; json.dump(res, open(OUT, 'w'), indent=1)
    print(ep, e['task'], 'static', round(frac, 2), ' '.join(f"{k}:{v['AUC']:.3f}/{v['MP-SR']:.2f}" for k, v in r.items() if isinstance(v, dict)))
    sys.stdout.flush()
