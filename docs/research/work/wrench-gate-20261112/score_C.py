#!/usr/bin/env python3
"""Test C of the wrench-feasibility gate (note 29 idea 1): zero-residual replay label.

Rule, as written before any label (docs/work-log.md, "2026-11-12 ~22:55 UTC — PRE-REGISTRATION, idea 1 test C"):
  gate      pipeline/wrench_gate.py frozen as committed in 61c0b6ad (checked here against git)
  data      the 19 public references runs/20261020-refsweep-ea14fdf/refs/perc2 (ep26 missing)
  label     FlashCHORD zero-residual replay of each reference on CPU (VOC 0, zero policy action, tools/trace_rollout.py
            zero, the recipe's controller settings); per (object, frame) in the gate's held windows, positive if the
            simulated object is > 2 cm from the reference; missing or non-finite rows count as positive
  verdict   informative: pooled AUROC >= 0.75 and >= 8 episodes contribute positives; falsified: AUROC < 0.65;
            otherwise inconclusive, and also inconclusive if under 10% or over 90% of held frames are positive.
            95% CI from 2,000 episode-bootstrap resamples, seed 20261112.
Inputs: a manifest {"episodes": [{"ep": 12, "ref": STORE_COPY.parquet, "trace": zero.npz, "store": path}], "assets": KIT}
  ref    the reference as downloaded from the store (the gate and the reference poses are read from it)
  trace  trace_rollout.py zero output: q (rows, bodies, 7) body poses [x y z qx qy qz qw], frame, labels
Outputs: results_C.json, labels_C.csv (episode, object, frame, label: exactly the gate's held-window rows).
Usage: score_C.py MANIFEST.json OUT_DIR"""
import csv, json, os, subprocess, sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'pipeline')); sys.path.insert(0, HERE)
from score_gate import auroc, episode_bootstrap, spearman, BAR_INFORMATIVE, BAR_FALSIFIED, MIN_POS_EPISODES  # noqa: E402
from task_wrench import object_tracks  # noqa: E402
from wrench_gate import gate, INFEASIBLE  # noqa: E402

LABEL_M, SHARE_LO, SHARE_HI, FROZEN = 0.02, 0.10, 0.90, '61c0b6ad'


def verdict_c(a, n_pos_eps, share):
    if a is None:
        return 'inconclusive (one class only)'
    if share < SHARE_LO or share > SHARE_HI:
        return f'inconclusive (positive share {share:.3f} outside [{SHARE_LO}, {SHARE_HI}])'
    if a < BAR_FALSIFIED:
        return 'falsified'
    if a >= BAR_INFORMATIVE and n_pos_eps >= MIN_POS_EPISODES:
        return 'informative'
    return 'inconclusive'


def body_index(labels, name):
    """Index of the simulated body of object `name`: the body label whose first path component is the name or ends in
    '_' + name (Newton labels a URDF body '<robot name>/<link>'; the kit URDFs are named 'track3_<object>')."""
    hits = [i for i, lb in enumerate(labels) if '/' in str(lb) and
            (str(lb).split('/')[0] == name or str(lb).split('/')[0].endswith('_' + name))]
    if len(hits) != 1:
        raise SystemExit(f'object {name}: {len(hits)} matching body labels in the trace ({hits})')
    return hits[0]


def sim_errors(ref, trace):
    """{object: (T,) distance sim vs reference per reference frame, NaN where the trace has no finite row}."""
    names, P, _ = object_tracks(ref); T = len(P)
    z = np.load(trace, allow_pickle=False); q, fr, labels = z['q'], z['frame'], [str(x) for x in z['labels']]
    out, info = {}, dict(trace_rows=int(len(fr)), frame_min=int(fr.min()), frame_max=int(fr.max()),
                         frames_unique=int(len(np.unique(fr))), frames_ref=int(T))
    for j, n in enumerate(names):
        b = body_index(labels, n); e = np.full(T, np.nan)
        for r, f in enumerate(fr):
            if 0 <= f < T and np.isfinite(q[r, b, :3]).all():
                e[f] = np.linalg.norm(q[r, b, :3] - P[f, j])          # last row wins if a frame repeats
        out[n] = e
        info[f'frame0_offset_mm_{n}'] = round(float(e[0] * 1000), 3) if np.isfinite(e[0]) else None
    return out, info


def main():
    man_path, out_dir = sys.argv[1], sys.argv[2]; man = json.load(open(man_path))
    diff = subprocess.run(['git', '-C', REPO, 'diff', '--quiet', FROZEN, '--', 'pipeline/wrench_gate.py']).returncode
    if diff != 0:
        raise SystemExit(f'pipeline/wrench_gate.py differs from the frozen {FROZEN}; refusing')
    per_ep, table, rows_csv, tinfo = [], [], [], {}
    for e in sorted(man['episodes'], key=lambda x: x['ep']):
        g = gate(e['ref'], man.get('assets')); err, info = sim_errors(e['ref'], e['trace']); tinfo[e['ep']] = info
        s = np.array([r['score'] for r in g['rows']]); ev = np.array([err[r['object']][r['frame']] for r in g['rows']])
        y = ~np.isfinite(ev) | (np.nan_to_num(ev, nan=np.inf) > LABEL_M)
        for r, lab in zip(g['rows'], y):
            rows_csv.append((f"ep{e['ep']}", r['object'], int(r['frame']), int(lab)))
        allerr = np.concatenate([v for v in err.values()])
        obj = np.array([r['object'] for r in g['rows']])
        per_ep.append((s, y))
        a_in = auroc(s, y)
        table.append(dict(ep=e['ep'], held_units=int(len(s)), positives=int(y.sum()),
                          positive_share=round(float(y.mean()), 4) if len(s) else None,
                          missing_or_nonfinite=int((~np.isfinite(ev)).sum()),
                          share_infeasible=round(float((s > INFEASIBLE).mean()), 4) if len(s) else None,
                          mean_err_held_cm=round(float(np.nanmean(ev)) * 100, 3) if np.isfinite(ev).any() else None,
                          mean_err_all_cm=round(float(np.nanmean(allerr)) * 100, 3) if np.isfinite(allerr).any() else None,
                          auroc_within=None if a_in is None else round(a_in, 4),
                          objects={n: dict(held=o['held_frames'], share_infeasible=o['share_infeasible'],
                                           positives=int(y[obj == n].sum()))
                                   for n, o in g['objects'].items() if o['held_frames']}))
    S = np.concatenate([p[0] for p in per_ep]); Y = np.concatenate([p[1] for p in per_ep])
    a = auroc(S, Y); npos = sum(int(p[1].any()) for p in per_ep); share = float(Y.mean())
    sec = [r for r in table if r['mean_err_held_cm'] is not None and r['held_units']]
    res = dict(test='C (zero-residual replay label)', units=int(len(S)), positives=int(Y.sum()), positive_share=round(share, 4),
               auroc=None if a is None else round(a, 4), bootstrap=episode_bootstrap(per_ep),
               episodes=len(per_ep), episodes_with_positives=npos, verdict=verdict_c(a, npos, share),
               bars=dict(informative=f'AUROC >= {BAR_INFORMATIVE} and >= {MIN_POS_EPISODES} positive episodes',
                         falsified=f'AUROC < {BAR_FALSIFIED}', share_rule=f'inconclusive if positive share < {SHARE_LO} or > {SHARE_HI}'),
               secondary=dict(spearman_share_infeasible_vs_mean_err_held=spearman([r['share_infeasible'] for r in sec], [r['mean_err_held_cm'] for r in sec]),
                              spearman_share_infeasible_vs_mean_err_all=spearman([r['share_infeasible'] for r in sec], [r['mean_err_all_cm'] for r in sec]),
                              note='descriptive only'),
               per_episode=table, trace_checks={str(k): v for k, v in tinfo.items()}, gate_frozen_at=FROZEN,
               manifest=os.path.abspath(man_path))
    os.makedirs(out_dir, exist_ok=True)
    json.dump(res, open(os.path.join(out_dir, 'results_C.json'), 'w'), indent=1)
    with open(os.path.join(out_dir, 'labels_C.csv'), 'w', newline='') as f:
        w = csv.writer(f); w.writerow(['episode', 'object', 'frame', 'label']); w.writerows(rows_csv)
    print(json.dumps({k: v for k, v in res.items() if k not in ('per_episode', 'trace_checks')}, indent=1))


if __name__ == '__main__':
    main()
