import glob, json, os, re, sys
root = sys.argv[1]
rows = []
for z in sorted(glob.glob(f'{root}/runs/*/results/glock_public/ep*/zero_score.txt')):
    d = os.path.dirname(z); run = z.split('/runs/')[1].split('/')[0]; ep = int(re.search(r'ep(\d+)', d.split('glock_public/')[1]).group(1))
    txt = open(z).read(); fl = float(re.search(r'floor_vs_ref ([\d.]+)', txt).group(1)); ze = float(re.search(r'sim_vs_ref ([\d.]+)', txt).group(1))
    s = f'{d}/best/summary.json'
    if not os.path.exists(s):
        continue
    j = json.load(open(s)); ck = os.path.basename(j['checkpoint']).replace('policy_', '').replace('.safetensors', '')
    rows.append((ep, run, fl, ze, j['sim_vs_ref']['mean'], j['auc']['mean'], j['auc']['std'], int(ck) / 1e6))
print('| ep | run | floor (sim_vs_ref, static) | zero action (sim_vs_ref) | zero - floor | fine-tuned sim_vs_ref (mean of 5) | registered AUC vs mocap (mean +- sd of 5) | chosen ckpt (M steps) |')
print('|---|---|---|---|---|---|---|---|')
for r in sorted(rows):
    print(f'| {r[0]} | `{r[1]}` | {r[2]:.3f} | {r[3]:.3f} | {r[3]-r[2]:+.3f} | {r[4]:.3f} | {r[5]:.3f} +- {r[6]:.3f} | {r[7]:.0f} |')
import numpy as np
z = np.array([r[3] for r in rows]); f = np.array([r[4] for r in rows]); g = np.array([r[3] - r[2] for r in rows])
from scipy.stats import spearmanr
print('n', len(rows), 'spearman(zero, fine-tuned)', spearmanr(z, f), 'spearman(zero-floor, fine-tuned)', spearmanr(g, f))
