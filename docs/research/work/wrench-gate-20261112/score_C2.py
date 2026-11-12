#!/usr/bin/env python3
"""Test C2 of the wrench-feasibility gate (note 29 ideas 1 and 3): grasp-locked replay label.

Rule (docs/work-log.md, "2026-11-13 ~00:50 UTC — owner: okay go crazy … PRE-REGISTRATION of tests C2, G-A and G-B"):
  gate      unchanged: pipeline/wrench_gate.py frozen at 61c0b6ad, on the 19 ORIGINAL refsweep perc2 references
  label     per (object, frame) in the gate's held windows: the grasp-locked physics replay of that reference
            (tools/cpu_glock_zero.sh chain: grasp_lock.py default args -> wrist_ilc.py kp 400, 4 iterations ->
            zero-action replay with sharpa_hands_mid, CPU); positive if the simulated object is > 2 cm from the
            REPLAYED reference's object pose; missing or non-finite counts as positive
  failures  episodes where grasp lock or ILC fails are excluded and reported; more than 5 of 19 -> inconclusive
  verdict   as test C: informative = pooled AUROC >= 0.75 and >= 8 episodes with positives; falsified = AUROC < 0.65;
            otherwise inconclusive, and inconclusive if under 10% or over 90% of held frames are positive.
            95% CI from 2,000 episode-bootstrap resamples, seed 20261112.
Manifest: {"assets": KIT, "episodes": [{"ep", "ref" (original), "replayed_ref" (ref_gl_ilc.parquet), "trace" (zero.npz),
           "status" (OK | GL_FAIL | ILC_FAIL | ZERO_FAIL), "store"}]}
Outputs: results_C2.json, labels_C2.csv (episode, object, frame, label; the gate rows of the included episodes).
Usage: score_C2.py MANIFEST.json OUT_DIR"""
import csv, json, os, subprocess, sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'pipeline')); sys.path.insert(0, HERE)
from score_gate import auroc, episode_bootstrap, spearman  # noqa: E402
from score_C import sim_errors, verdict_c, FROZEN, LABEL_M  # noqa: E402
from task_wrench import object_tracks  # noqa: E402
from wrench_gate import gate, INFEASIBLE  # noqa: E402

MAX_FAILED = 5


def object_change(orig, replayed):
    """Largest change of the object trajectory made by grasp lock + ILC (position mm, rotation deg)."""
    from scipy.spatial.transform import Rotation as Rot
    n0, P0, Q0 = object_tracks(orig); n1, P1, Q1 = object_tracks(replayed)
    if n0 != n1 or P0.shape != P1.shape:
        return dict(same_objects_and_frames=False)
    rot = max(float(np.degrees((Rot.from_quat(Q0[:, j]) * Rot.from_quat(Q1[:, j]).inv()).magnitude()).max()) for j in range(len(n0)))
    return dict(same_objects_and_frames=True, max_pos_change_mm=round(float(np.abs(P1 - P0).max()) * 1000, 4),
                max_rot_change_deg=round(rot, 4))


def main():
    man_path, out_dir = sys.argv[1], sys.argv[2]; man = json.load(open(man_path))
    if subprocess.run(['git', '-C', REPO, 'diff', '--quiet', FROZEN, '--', 'pipeline/wrench_gate.py']).returncode != 0:
        raise SystemExit(f'pipeline/wrench_gate.py differs from the frozen {FROZEN}; refusing')
    eps = sorted(man['episodes'], key=lambda x: x['ep'])
    failed = [dict(ep=e['ep'], status=e['status']) for e in eps if e['status'] in ('GL_FAIL', 'ILC_FAIL')]
    per_ep, table, rows_csv, checks = [], [], [], {}
    for e in eps:
        if e['status'] in ('GL_FAIL', 'ILC_FAIL'):
            continue
        g = gate(e['ref'], man.get('assets'))
        chg = object_change(e['ref'], e['replayed_ref'])
        if os.path.exists(e['trace']):
            err, info = sim_errors(e['replayed_ref'], e['trace'])      # vs the REPLAYED reference's object pose
        else:                                                          # final replay missing: every row positive
            names = object_tracks(e['ref'])[0]; T = len(object_tracks(e['ref'])[1])
            err, info = {n: np.full(T, np.nan) for n in names}, dict(trace='missing')
        checks[str(e['ep'])] = dict(status=e['status'], object_trajectory_change=chg, **info)
        s = np.array([r['score'] for r in g['rows']]); ev = np.array([err[r['object']][r['frame']] for r in g['rows']])
        y = ~np.isfinite(ev) | (np.nan_to_num(ev, nan=np.inf) > LABEL_M); obj = np.array([r['object'] for r in g['rows']])
        rows_csv += [(f"ep{e['ep']}", r['object'], int(r['frame']), int(lab)) for r, lab in zip(g['rows'], y)]
        allerr = np.concatenate(list(err.values())); a_in = auroc(s, y); per_ep.append((s, y))
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
    verdict = (f'inconclusive ({len(failed)} of {len(eps)} episodes failed grasp lock or ILC, more than {MAX_FAILED})'
               if len(failed) > MAX_FAILED else verdict_c(a, npos, share))
    sec = [r for r in table if r['mean_err_held_cm'] is not None and r['held_units']]
    res = dict(test='C2 (grasp-locked replay label)', episodes_total=len(eps), episodes_failed=failed,
               episodes_scored=len(per_ep), units=int(len(S)), positives=int(Y.sum()), positive_share=round(share, 4),
               auroc=None if a is None else round(a, 4), bootstrap=episode_bootstrap(per_ep),
               episodes_with_positives=npos, verdict=verdict,
               secondary=dict(spearman_share_infeasible_vs_mean_err_held=spearman([r['share_infeasible'] for r in sec], [r['mean_err_held_cm'] for r in sec]),
                              spearman_share_infeasible_vs_mean_err_all=spearman([r['share_infeasible'] for r in sec], [r['mean_err_all_cm'] for r in sec]),
                              note='descriptive only'),
               per_episode=table, checks=checks, gate_frozen_at=FROZEN)
    os.makedirs(out_dir, exist_ok=True)
    json.dump(res, open(os.path.join(out_dir, 'results_C2.json'), 'w'), indent=1)
    with open(os.path.join(out_dir, 'labels_C2.csv'), 'w', newline='') as f:
        w = csv.writer(f); w.writerow(['episode', 'object', 'frame', 'label']); w.writerows(rows_csv)
    print(json.dumps({k: v for k, v in res.items() if k not in ('per_episode', 'checks')}, indent=1))


if __name__ == '__main__':
    main()
