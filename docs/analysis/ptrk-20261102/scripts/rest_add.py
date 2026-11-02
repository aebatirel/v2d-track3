"""Stage 1 gate clause 3 (diagnostic, reads the scorer's per-frame errors): mean symmetric ADD over the frames the arm
changed (changed.npz from stage1.py), control vs arm, per episode. Usage: python -I rest_add.py SCRATCH CTRL ARM_TAG ARM_DIR"""
import sys, glob, json, numpy as np
S, C, A, AD = sys.argv[1:5]
rows = []
for f in sorted(glob.glob(f'{AD}/ep*/changed.npz'), key=lambda p: int(p.split('/ep')[-1].split('/')[0])):
    e = int(f.split('/ep')[-1].split('/')[0]); ch = np.load(f)
    zc, za = np.load(f'{S}/runs/{C}/ep{e}_pf.npz'), np.load(f'{S}/runs/{A}/ep{e}_pf.npz')
    names = list(zc['names']); m = np.stack([ch[n] for n in names], 1)[:len(zc['perception_adds_cm'])]
    if not m.any():
        rows.append(dict(ep=e, changed=0, lower=False)); continue
    c = float(zc['perception_adds_cm'][m].mean()); a_ = float(za['perception_adds_cm'][m].mean())
    rows.append(dict(ep=e, changed=int(m.sum()), add_ctrl=round(c, 3), add_arm=round(a_, 3), lower=a_ < c))
print(json.dumps(rows)); print('lower on', sum(r['lower'] for r in rows), 'of', len(rows))
json.dump(rows, open(f'{S}/rest_add_{A}.json', 'w'), indent=0)
