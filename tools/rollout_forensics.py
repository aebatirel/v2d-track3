"""Where and when do the submitted rollouts leave our reference? (2026-10-26, forensics for the owner; reporting only.)
Reads official evaluator rollouts (episode_XXXXXX.parquet: achieved and reference object poses per step; the same files
the submission packs) and, per episode and object: the position error (cm) and rotation error (deg) of the simulated
object against our reference per frame, the reference's own motion (cm/frame; when the object is carried), the frame
the error first stays above 2 cm for 10 frames (onset), and the share of frames above 2 / 5 cm. No ground truth: this is
simulation against our own reference, the part of the score the policy controls.
Usage: rollout_forensics.py RESULTS_DIR OUT.json [--png OUT.png] [--scores summary.json-line]"""
import argparse, glob, json, os

import numpy as np
import pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as R

ap = argparse.ArgumentParser(); ap.add_argument('results'); ap.add_argument('out'); ap.add_argument('--png')
a = ap.parse_args()
res = {}
for f in sorted(glob.glob(f'{a.results}/episode_*.parquet')):
    ep = int(os.path.basename(f)[8:14]); t = pq.read_table(f).to_pydict()
    env = np.array(t['environment_id']); keep = env == env.min()
    names = list(dict.fromkeys(np.array(t['object_body_name'])[keep])); step = np.array(t['step'])[keep]
    met = json.load(open(f[:-8] + '.json'))['metrics']; row = dict(add_auc=round(met['add_auc'], 4), frames=int(step.max()) + 1, objects={})
    for k, n in enumerate(names):
        sel = np.array(t['object_body_name'])[keep] == n; o = np.argsort(step[sel])

        def col(p, c):
            return np.array(t[f'{p}_{c}'])[keep][sel][o]
        A = np.stack([col('achieved_position', c) for c in 'xyz'], 1); B = np.stack([col('reference_position', c) for c in 'xyz'], 1)
        qa = np.stack([col('achieved_quaternion', c) for c in 'xyzw'], 1); qb = np.stack([col('reference_quaternion', c) for c in 'xyzw'], 1)
        e = np.linalg.norm(A - B, axis=1) * 100; r = np.degrees((R.from_quat(qa) * R.from_quat(qb).inv()).magnitude())
        sp = np.r_[0, np.linalg.norm(np.diff(B, axis=0), axis=1) * 100]
        mv = np.flatnonzero(np.linalg.norm(B - B[0], axis=1) * 100 > 2.0)            # reference leaves its start by 2 cm
        over = e > 2.0; run = np.convolve(over, np.ones(10, int), 'valid') == 10
        onset = int(np.argmax(run)) if run.any() else None
        row['objects'][n] = dict(err_cm_median=round(float(np.median(e)), 2), err_cm_p90=round(float(np.percentile(e, 90)), 2),
                                 err_cm_end=round(float(e[-1]), 2), rot_deg_median=round(float(np.median(r)), 1), rot_deg_end=round(float(r[-1]), 1),
                                 share_over_2cm=round(float(over.mean()), 3), share_over_5cm=round(float((e > 5).mean()), 3),
                                 onset_frame=onset, ref_first_move_frame=int(mv[0]) if len(mv) else None,
                                 ref_path_cm=round(float(sp.sum()), 1), err_cm=np.round(e, 2).tolist(), rot_deg=np.round(r, 1).tolist(),
                                 ref_speed_cm=np.round(sp, 2).tolist())
    res[ep] = row
    print(ep, row['add_auc'], {n: {k: v for k, v in o.items() if k not in ('err_cm', 'rot_deg', 'ref_speed_cm')} for n, o in row['objects'].items()}, flush=True)
json.dump(res, open(a.out, 'w'))
if a.png:
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    eps = sorted(res); fig, ax = plt.subplots(5, 4, figsize=(20, 17)); ax = ax.ravel()
    for i, ep in enumerate(eps):
        r = res[ep]; x = ax[i]; x2 = x.twinx()
        for j, (n, o) in enumerate(r['objects'].items()):
            c = f'C{j}'; x.plot(o['err_cm'], c, lw=1.4, label=f'{n} cm'); x2.plot(o['rot_deg'], c, lw=0.8, ls=':', label=f'{n} deg')
            x.fill_between(range(len(o['ref_speed_cm'])), 0, np.clip(o['ref_speed_cm'], 0, 3) * 2, color=c, alpha=0.12, lw=0)
            if o['onset_frame'] is not None:
                x.axvline(o['onset_frame'], color=c, ls='--', lw=0.8)
        x.set_ylim(0, 20); x2.set_ylim(0, 90); x.axhline(2, color='k', lw=0.5, ls=':')
        x.set_title(f"eval {ep}: sim vs our reference add_auc {r['add_auc']:.3f}", fontsize=10)
        if i == 0:
            x.legend(fontsize=7, loc='upper left'); x2.legend(fontsize=7, loc='upper right')
    for j in range(len(eps), len(ax)):
        ax[j].axis('off')
    fig.suptitle('Submitted rollouts (third pack): object error vs OUR reference per frame. Solid: position (cm, left axis, '
                 'clipped at 20); dotted: rotation (deg, right); shaded: reference speed (when the object is carried); '
                 'dashed: onset (> 2 cm for 10 frames)', fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.97]); fig.savefig(a.png, dpi=80)
