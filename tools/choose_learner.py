"""One automatic, ground-truth-free choice per eval episode between learners trained on the same reference (2026-10-24).

Evidence (public twins, registered AUC vs mocap): the grasp-lock fine-tune wins on rigid graspable objects (ep27 0.96-0.97,
the eval spoon sim_vs_ref 0.97 where the standard FDR RL stays at 0.34-0.41), the standard FDR RL (250M) on two-handed
tool episodes (ep18 0.78 / 0.89 vs 0.22-0.41); ep12 goes either way by seed. The mean sim_vs_ref of repeated official
evaluations tracks the true score (27 public policies: corr 0.997; 2026-10-24 pairs ep12 / ep18: diff <= 0.03), so the
rule is: the candidate whose official rollouts track OUR reference best (mean over its repeats) is the episode's policy.
Every candidate is scored against the SAME yardstick: the reference_xyzw of a rollout whose reference keeps the
perceived object trajectory (the standard learner's; the grasp-lock reference equals it unless re-planned or settled,
measured max difference 0.0 m on ep12 / ep18), so a re-planned reference cannot score itself.
Only our own reference is read (no ground truth, no human per-episode decision).
Usage: choose_learner.py OUT EP --cand NAME:ROLLOUT_DIR:CHECKPOINT [--cand ...] [--yardstick ROLLOUT_DIR]
  ROLLOUT_DIR holds r*/episode_XXXXXX.parquet (official evaluations of CHECKPOINT); the yardstick defaults to the first
  candidate's rollouts. Writes OUT/ep<EP>/choice.json and OUT/ep<EP>/policy.safetensors (copy of the chosen checkpoint)
  and updates OUT/checkpoints.json (kit examples/run_policy_evaluation.py --checkpoints).
"""
import argparse, glob, importlib, json, os, shutil, sys

import numpy as np

KIT = os.environ.get('KIT', '/content/kit/v2d_submission_kit')


def grids(path):
    from v2dlb.submission_parquet import read_trajectory
    tr = read_trajectory(path); w0 = tr.world_index == tr.world_index.min()
    frames = np.unique(tr.frame_index[w0]); B = int(tr.object_slot.max()) + 1
    def g(P):
        G = np.full((len(frames), B, 7), np.nan)
        for f, s, q in zip(tr.frame_index[w0], tr.object_slot[w0], P[w0]):
            G[np.searchsorted(frames, f), s] = q
        return G
    return g(tr.pose_xyzw), g(tr.reference_xyzw)


def auc(A, a, r):  # as pipeline/qa.py: kit AUC on 500 points of a 5 cm sphere per object (no mesh)
    rng = np.random.default_rng(0); pts = rng.normal(size=(500, 3)); pts = 0.05 * pts / np.linalg.norm(pts, axis=1, keepdims=True)
    V = np.repeat(pts[None], a.shape[1], 0); a, r = a[:, None], r[:, None]
    return float(A._add_auc(A._object_add(A._warp_to_reference_start(a, r), r, V)))


def main():
    p = argparse.ArgumentParser(); p.add_argument('out'); p.add_argument('ep', type=int)
    p.add_argument('--cand', action='append', required=True); p.add_argument('--yardstick')
    a = p.parse_args()
    sys.path.insert(0, KIT); sys.path.insert(0, f'{KIT}/metric_code/track_3')
    A = importlib.import_module('AUC')
    E6 = f'episode_{a.ep:06d}.parquet'; cands = []
    for c in a.cand:
        name, d, ck = c.split(':', 2)
        cands.append(dict(name=name, dir=d, checkpoint=ck, rollouts=sorted(glob.glob(f'{d}/r*/{E6}'))))
    ys = a.yardstick or next((c['dir'] for c in cands if c['rollouts']), None)
    yr = sorted(glob.glob(f'{ys}/r*/{E6}')) if ys else []
    if not yr:
        raise SystemExit(f'no yardstick rollouts for ep{a.ep}')
    yard = grids(yr[0])[1]
    for c in cands:
        c['scores'] = []
        for r in c['rollouts']:
            sim, ref = grids(r)
            if sim.shape != yard.shape:
                c.setdefault('errors', []).append(f'{r}: shape {sim.shape} vs yardstick {yard.shape}'); continue
            c['scores'].append(round(auc(A, sim, yard), 4))
            c.setdefault('ref_offset_m', 0.0)
            c['ref_offset_m'] = round(max(c['ref_offset_m'], float(np.nanmax(np.linalg.norm(ref[..., :3] - yard[..., :3], axis=-1)))), 4)
        c['mean'] = round(float(np.mean(c['scores'])), 4) if c['scores'] else None
        c['ok'] = bool(c['scores']) and os.path.isfile(c['checkpoint'])
    ok = [c for c in cands if c['ok']]
    if not ok:
        raise SystemExit(f'no usable candidate for ep{a.ep}: {[(c["name"], c.get("errors"), c["checkpoint"]) for c in cands]}')
    best = max(ok, key=lambda c: c['mean'])
    o = os.path.join(a.out, f'ep{a.ep}'); os.makedirs(o, exist_ok=True)
    shutil.copy(best['checkpoint'], os.path.join(o, 'policy.safetensors'))
    json.dump(dict(ep=a.ep, chosen=best['name'], checkpoint=best['checkpoint'], yardstick=yr[0], rule='max mean sim_vs_ref',
                   candidates=[{k: c.get(k) for k in ('name', 'checkpoint', 'mean', 'scores', 'ref_offset_m', 'ok', 'errors')} for c in cands]),
              open(os.path.join(o, 'choice.json'), 'w'), indent=1)
    cj = os.path.join(a.out, 'checkpoints.json'); m = json.load(open(cj)) if os.path.exists(cj) else {}
    m[str(a.ep)] = os.path.abspath(os.path.join(o, 'policy.safetensors')); json.dump(m, open(cj, 'w'), indent=1, sort_keys=True)
    print(json.dumps(dict(ep=a.ep, chosen=best['name'], means={c['name']: c['mean'] for c in cands})))


if __name__ == '__main__':
    main()
