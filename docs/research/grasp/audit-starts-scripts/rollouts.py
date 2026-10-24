"""Policy rollouts (official evaluator, best checkpoint, r1..r5) per object vs OUR reference (no ground truth):
first-step jump, per-window mean error, lift, first frame > 2 cm / 10 deg and > 5 cm, recovery (back within 2 cm
for >= 10 frames after a loss), final error. Windows: before the object's first hold, hold, after.
Usage: rollouts.py EP"""
import sys, json, glob, numpy as np
from pathlib import Path
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from common import *
sys.path.insert(0, KIT)
from v2dlb.submission_parquet import read_trajectory

ep = int(sys.argv[1]); kind = sys.argv[2] if len(sys.argv) > 2 else 'best'
gl = json.load(open(glob.glob(f'{run_dir(ep)}/refs/glock/ep{ep}/processed/*/*/ref_gl_grasp_lock.json')[0]))
holds = {}
for ph in gl['phases']:
    holds.setdefault(ph['object'], []).append((ph['hold_from'], ph['end'], ph['hand']))
if kind == 'best':
    rolls = sorted(glob.glob(f'{run_dir(ep)}/results/glock_public/ep{ep}/best/r*/episode_*.parquet'))
else:
    rolls = sorted(glob.glob(f'{run_dir(ep)}/results/glock_public/ep{ep}/curve/policy_*/episode_*.parquet'))
res = {}
for rp in rolls:
    tr = read_trajectory(Path(rp)); slots = sorted(set(tr.object_slot.tolist())); lab = rp.split('/')[-2]; res[lab] = {}
    for k in slots:
        sel = tr.object_slot == k; o = np.argsort(tr.frame_index[sel]); P = tr.pose_xyzw[sel][o]; Rf = tr.reference_xyzw[sel][o]
        name = str(tr.object_name[sel][0]) if tr.object_name is not None else str(k)
        e = 100 * np.linalg.norm(P[:, :3] - Rf[:, :3], axis=1); er = rot_deg(P[:, 3:7], Rf[:, 3:7])
        lift = 100 * (P[:, 2] - P[0, 2]); rlift = 100 * (Rf[:, 2] - Rf[0, 2]); n = len(P)
        h = holds.get(name, [])
        h0 = min(x[0] for x in h) if h else n; h1 = max(x[1] for x in h) if h else n
        bad = (e > 2) | (er > 10)
        first_bad = int(np.argmax(bad)) if bad.any() else None
        first5 = int(np.argmax(e > 5)) if (e > 5).any() else None
        rec = None
        if first5 is not None:
            ok = e < 2
            for f in range(first5, n - 10):
                if ok[f:f + 10].all():
                    rec = f; break
        win = {'pre': (0, h0), 'hold': (h0, min(h1, n)), 'post': (min(h1, n), n)}
        res[lab][name] = dict(slot=int(k), n=n, jump0_cm=round(float(e[0]), 2), jump0_deg=round(float(er[0]), 1),
                              first_bad=first_bad, first5=first5, recovered_at=rec, final_cm=round(float(e[-1]), 1), final_deg=round(float(er[-1]), 1),
                              max_lift=round(float(lift.max()), 1), ref_max_lift=round(float(rlift.max()), 1), hold=[h0, h1],
                              win={w: dict(cm=round(float(e[a:b].mean()), 1) if b > a else None, deg=round(float(er[a:b].mean()), 1) if b > a else None,
                                           in3=round(float((e[a:b] < 3).mean()), 2) if b > a else None) for w, (a, b) in win.items()},
                              e10=[round(float(x), 1) for x in e[::10]], er10=[round(float(x), 0) for x in er[::10]], lift10=[round(float(x), 1) for x in lift[::10]])
json.dump(res, open(f'{W}/out/rollouts_ep{ep}_{kind}.json', 'w'), indent=0)
for lab, r in res.items():
    for name, v in r.items():
        print(f"{lab} {name[:14]:14s} jump0 {v['jump0_cm']:5.2f}cm/{v['jump0_deg']:4.1f} | first>2cm/10deg f{v['first_bad']} >5cm f{v['first5']} rec {v['recovered_at']} | "
              f"pre {v['win']['pre']['cm']}cm/{v['win']['pre']['deg']} hold {v['win']['hold']['cm']}cm/{v['win']['hold']['deg']} in3 {v['win']['hold']['in3']} post {v['win']['post']['cm']} | lift {v['max_lift']}/{v['ref_max_lift']} final {v['final_cm']}cm")
for name in res[list(res)[0]]:
    print(name, 'err cm every 10 f:')
    for lab in res:
        print('  ', lab, res[lab][name]['e10'])
