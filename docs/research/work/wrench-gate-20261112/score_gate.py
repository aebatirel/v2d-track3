#!/usr/bin/env python3
"""Pre-registered public test of the wrench-feasibility gate (pipeline/wrench_gate.py; note 29 idea 1).

Rule, as written before any data (docs/work-log.md, "2026-11-12 ~22:20 UTC ... PRE-REGISTRATION"):
  score per reference frame in held phases = relative NNLS residual of the task wrench in the contact wrench cone
  (inputs: our reference only); label per frame = the official evaluator rollout's object deviates > 2 cm from our
  reference (GT-free); 20 public episodes. Informative: pooled AUROC >= 0.75 and >= 8 episodes contribute positives.
  Falsified: AUROC < 0.65. Otherwise inconclusive. 95% CI by episode bootstrap, reported with the result.
Choices fixed here before any label was computed (README.md, "Analysis plan"):
  unit        one (object, frame) pair inside a held window of wrench_gate.py (object-event windows)
  label       |achieved - reference| object position > 0.02 m in the rollout row of environment_id = min, matched by
              reference_frame; a frame with no row or environment_valid False counts as positive (object lost)
  rollout     exactly one official evaluator rollout per episode, all 20 from one recipe; every rollout must replay its
              reference: max |reference_position - our object_body_position| < 1 mm, otherwise the test refuses to run
  AUROC       Mann-Whitney with mid-ranks (ties count 1/2); higher score = predicted deviation
  CI          2,000 episode-bootstrap resamples (seed 20261112), percentile 2.5 / 97.5; one-class resamples skipped
  secondary   per episode: share of held units with score > 0.5 vs mean sim-vs-reference error over the held units
              (and over all rollout frames); Spearman rho, descriptive only
Subcommands
  list OUT_DIR RUNS_TXT          save recursive HF tree listings of the store runs named in RUNS_TXT (one per line)
  inventory TREES_DIR OUT.json   which public episodes have official evaluator rollouts and references in the store
  score MANIFEST.json OUT.json   the test (refuses unless the manifest is complete and every rollout replays its ref)
  selftest                       synthetic checks of the statistics and of the gate's physics
Manifest: {"recipe": "...", "episodes": [{"ep": 0, "ref": PATH, "rollout": PATH, "assets": DIR|null,
           "store": {"ref": ..., "rollout": ...}}, ...]}
Run with the repo's pipeline/ importable (this script adds it to sys.path itself)."""
import argparse, json, os, re, subprocess, sys, tempfile
from collections import defaultdict

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', 'pipeline')))

PUBLIC = (0, 2, 11, 12, 13, 18, 21, 22, 23, 24, 26, 27, 31, 39, 40, 41, 42, 43, 44, 45)   # pipeline/run_public.sh
STORE = 'aebatirel/v2d-store'
LABEL_M, INFEASIBLE, ALIGN_M, NBOOT, SEED = 0.02, 0.5, 1e-3, 2000, 20261112
BAR_INFORMATIVE, BAR_FALSIFIED, MIN_POS_EPISODES = 0.75, 0.65, 8


# ------------------------------------------------------------------ statistics
def auroc(score, label):
    """Mann-Whitney AUROC with mid-ranks; None without both classes."""
    s = np.asarray(score, float); y = np.asarray(label, bool); n1, n0 = int(y.sum()), int((~y).sum())
    if n1 == 0 or n0 == 0:
        return None
    order = np.argsort(s, kind='mergesort'); r = np.empty(len(s)); ss = s[order]; i = 0
    while i < len(s):
        j = i
        while j + 1 < len(s) and ss[j + 1] == ss[i]:
            j += 1
        r[order[i:j + 1]] = 0.5 * (i + j) + 1; i = j + 1
    return float((r[y].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def episode_bootstrap(per_ep, nboot=NBOOT, seed=SEED):
    """per_ep: list of (scores, labels) per episode. Pooled AUROC over resampled episodes; percentile CI."""
    rng = np.random.default_rng(seed); vals, skipped = [], 0
    for _ in range(nboot):
        pick = rng.integers(0, len(per_ep), len(per_ep))
        a = auroc(np.concatenate([per_ep[k][0] for k in pick]), np.concatenate([per_ep[k][1] for k in pick]))
        if a is None:
            skipped += 1
        else:
            vals.append(a)
    v = np.asarray(vals)
    return dict(ci95=[round(float(np.percentile(v, 2.5)), 4), round(float(np.percentile(v, 97.5)), 4)] if len(v) else None,
                resamples=nboot, skipped_one_class=skipped, seed=seed)


def verdict(a, n_pos_eps):
    if a is None:
        return 'inconclusive (no AUROC: one class only)'
    if a < BAR_FALSIFIED:
        return 'falsified'
    if a >= BAR_INFORMATIVE and n_pos_eps >= MIN_POS_EPISODES:
        return 'informative'
    return 'inconclusive'


def spearman(x, y):
    from scipy.stats import spearmanr
    if len(x) < 3:
        return None
    r = spearmanr(x, y)
    return round(float(r.statistic if hasattr(r, 'statistic') else r[0]), 4)


# ------------------------------------------------------------------ labels from an official evaluator rollout
def rollout_errors(rollout, ref):
    """{object: {frame: error_m or None (missing / invalid)}} and the provenance check against our reference."""
    import pyarrow.parquet as pq
    from task_wrench import object_tracks
    d = pq.read_table(rollout).to_pydict(); env = np.array(d['environment_id']); keep = env == env.min()
    rf = np.array(d['reference_frame'])[keep]; nm = np.array(d['object_body_name'])[keep]
    val = np.array(d['environment_valid'])[keep].astype(bool)
    A = np.stack([np.array(d[f'achieved_position_{c}'])[keep] for c in 'xyz'], 1)
    B = np.stack([np.array(d[f'reference_position_{c}'])[keep] for c in 'xyz'], 1)
    names, P, _ = object_tracks(ref); out = {}; worst = 0.0
    for j, n in enumerate(names):
        sel = nm == n; fr = rf[sel]
        if not sel.any() or fr.max() >= len(P):
            return None, dict(ok=False, why=f'object {n} missing or frames beyond the reference')
        worst = max(worst, float(np.abs(B[sel] - P[fr, j]).max()))
        e = np.linalg.norm(A[sel] - B[sel], axis=1)
        out[n] = {int(f): (float(x) if v else None) for f, x, v in zip(fr, e, val[sel])}
    return out, dict(ok=worst < ALIGN_M, max_ref_diff_mm=round(worst * 1000, 4))


# ------------------------------------------------------------------ the test
def score(manifest, out_path):
    from wrench_gate import gate
    man = json.load(open(manifest)); eps = man['episodes']; got = sorted(e['ep'] for e in eps)
    missing = sorted(set(PUBLIC) - set(got)); extra = sorted(set(got) - set(PUBLIC))
    if missing or extra or len(got) != len(set(got)) or not man.get('recipe'):
        res = dict(status='blocked', why='manifest does not hold exactly the 20 public episodes under one recipe',
                   missing=missing, extra=extra)
        json.dump(res, open(out_path, 'w'), indent=1); print(json.dumps(res)); return 2
    per_ep, table, prov, lost = [], [], [], 0
    for e in sorted(eps, key=lambda x: x['ep']):
        g = gate(e['ref'], e.get('assets'))
        err, chk = rollout_errors(e['rollout'], e['ref'])
        prov.append(dict(ep=e['ep'], **chk, physics={n: o['physics_source'] for n, o in g['objects'].items()}))
        if not chk['ok']:
            continue
        s, y, ev = [], [], []
        for r in g['rows']:
            x = err[r['object']].get(r['frame'])
            s.append(r['score']); y.append(x is None or x > LABEL_M); ev.append(np.nan if x is None else x)
            lost += x is None
        s, y, ev = np.asarray(s), np.asarray(y, bool), np.asarray(ev)
        allerr = [x for o in err.values() for x in o.values() if x is not None]
        per_ep.append((s, y))
        table.append(dict(ep=e['ep'], held_units=int(len(s)), positives=int(y.sum()),
                          share_infeasible=round(float((s > INFEASIBLE).mean()), 4) if len(s) else None,
                          mean_err_held_cm=round(float(np.nanmean(ev)) * 100, 3) if len(s) and np.isfinite(ev).any() else None,
                          mean_err_all_cm=round(float(np.mean(allerr)) * 100, 3) if allerr else None,
                          auroc_within=None if auroc(s, y) is None else round(auroc(s, y), 4)))
    bad = [p for p in prov if not p['ok']]
    if bad:
        res = dict(status='blocked', why='a rollout does not replay its reference (provenance check)', provenance=prov)
        json.dump(res, open(out_path, 'w'), indent=1); print(json.dumps(res)); return 2
    S = np.concatenate([p[0] for p in per_ep]); Y = np.concatenate([p[1] for p in per_ep])
    a = auroc(S, Y); npos = sum(int(p[1].any()) for p in per_ep)
    sec = [r for r in table if r['share_infeasible'] is not None and r['mean_err_held_cm'] is not None]
    res = dict(status='run', recipe=man['recipe'], units=int(len(S)), positives=int(Y.sum()), lost_units=int(lost),
               auroc=None if a is None else round(a, 4), bootstrap=episode_bootstrap(per_ep),
               episodes_with_positives=npos, verdict=verdict(a, npos),
               secondary=dict(spearman_share_vs_err_held=spearman([r['share_infeasible'] for r in sec], [r['mean_err_held_cm'] for r in sec]),
                              spearman_share_vs_err_all=spearman([r['share_infeasible'] for r in sec], [r['mean_err_all_cm'] for r in sec]),
                              note='descriptive only'),
               per_episode=table, provenance=prov, manifest=os.path.abspath(manifest))
    json.dump(res, open(out_path, 'w'), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k not in ('per_episode', 'provenance')}, indent=1))
    return 0


# ------------------------------------------------------------------ store inventory
def list_store(out_dir, runs_txt):
    """Recursive tree listing of each run (HF API, paginated; auth comes from the network proxy)."""
    os.makedirs(out_dir, exist_ok=True)
    for run in [ln.strip() for ln in open(runs_txt) if ln.strip()]:
        url = f'https://huggingface.co/api/datasets/{STORE}/tree/main/{run}?recursive=true&limit=1000'; files = []
        while url:
            with tempfile.TemporaryDirectory() as td:
                subprocess.run(['curl', '-sS', '-D', f'{td}/h', '-o', f'{td}/b', url], check=False)
                head, body = open(f'{td}/h').read(), open(f'{td}/b').read()
            files += [(x['path'], x.get('size', 0)) for x in json.loads(body) if x['type'] == 'file']
            m = re.search(r'<([^>]+)>; rel="next"', head); url = m.group(1) if m else None
        json.dump(files, open(os.path.join(out_dir, run.replace('/', '_') + '.json'), 'w'))


def inventory(trees_dir, out_path):
    roll = defaultdict(set); group = defaultdict(set); refsets = defaultdict(set); nfiles = 0; runs = 0
    for fn in sorted(os.listdir(trees_dir)):
        files = json.load(open(os.path.join(trees_dir, fn))); runs += 1; nfiles += len(files)
        for p, _ in files:
            m = re.search(r'^runs/([^/]+)/results/([^/]+)/.*episode_(\d{6})\.parquet$', p)
            if m and int(m.group(3)) in PUBLIC:
                ep = int(m.group(3)); roll[ep].add(m.group(1)); group[f'{m.group(1)}/results/{m.group(2)}'].add(ep)
            m = re.search(r'^runs/([^/]+)/refs/([^/]+)/ep(\d+)[^/]*/processed/.*\.parquet$', p)
            if m and int(m.group(3)) in PUBLIC:
                refsets[f'{m.group(1)}/refs/{m.group(2)}'].add(int(m.group(3)))
    best = sorted(group.items(), key=lambda kv: -len(kv[1]))[:8]
    bestref = sorted(refsets.items(), key=lambda kv: -len(kv[1]))[:5]
    res = dict(store=STORE, runs_listed=runs, files_listed=nfiles,
               public_with_any_rollout=sorted(roll), public_without_any_rollout=sorted(set(PUBLIC) - set(roll)),
               rollout_runs_per_public_episode={str(k): sorted(v) for k, v in sorted(roll.items())},
               largest_rollout_groups=[dict(group=g, public_episodes=sorted(v), n=len(v)) for g, v in best],
               largest_reference_sets=[dict(set=g, public_episodes=sorted(v), n=len(v)) for g, v in bestref])
    json.dump(res, open(out_path, 'w'), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != 'rollout_runs_per_public_episode'}, indent=1))


# ------------------------------------------------------------------ self-test
def selftest():
    from scipy.spatial.transform import Rotation as Rot
    import wrench_gate as wg
    ok = True

    def check(name, got, want, tol=1e-6):
        nonlocal ok
        good = (got is None and want is None) or (got is not None and want is not None and abs(got - want) <= tol)
        ok &= bool(good); print(f"{'PASS' if good else 'FAIL'} {name}: {got} (want {want})")

    # statistics
    check('auroc perfect', auroc([0.1, 0.2, 0.8, 0.9], [0, 0, 1, 1]), 1.0)
    check('auroc reversed', auroc([0.9, 0.8, 0.2, 0.1], [0, 0, 1, 1]), 0.0)
    check('auroc all tied', auroc([0.0] * 6, [0, 1, 0, 1, 0, 1]), 0.5)
    check('auroc one class', auroc([0.1, 0.2], [0, 0]), None)
    rng = np.random.default_rng(1); s = rng.integers(0, 5, 300) / 4.0; y = rng.random(300) < 0.3 + 0.1 * s
    pos, neg = s[y], s[~y]; brute = ((pos[:, None] > neg[None]).sum() + 0.5 * (pos[:, None] == neg[None]).sum()) / (len(pos) * len(neg))
    check('auroc ties vs brute force', auroc(s, y), float(brute), 1e-12)
    eps = [(rng.random(50), rng.random(50) < 0.2) for _ in range(20)]
    b1, b2 = episode_bootstrap(eps, 200), episode_bootstrap(eps, 200)
    check('bootstrap reproducible', float(b1['ci95'][0] == b2['ci95'][0]), 1.0)
    for a, n, want in ((0.80, 9, 'informative'), (0.80, 7, 'inconclusive'), (0.64, 12, 'falsified'), (0.70, 12, 'inconclusive'),
                       (0.75, 8, 'informative'), (0.65, 3, 'inconclusive')):
        got = verdict(a, n); ok &= got == want; print(f"{'PASS' if got == want else 'FAIL'} verdict({a}, {n}) = {got}")
    # gate physics (rc = 0.1 m, mu = 1, m = 0.3 kg, static: demand = [0, 0, m g ; 0, 0, 0])
    W = np.array([0, 0, 0.3 * 9.81, 0, 0, 0]); c = np.zeros(3); rc = 0.1
    G = wg.generators([[0.03, 0, 0], [-0.03, 0, 0]], [[-1, 0, 0], [1, 0, 0]], c, rc)
    check('antipodal pinch holds the weight', wg.feasibility(W, G), 0.0, 1e-6)
    check('single side contact at the COM: 1/sqrt(2)', wg.feasibility(W, wg.generators([[0, 0, 0]], [[-1, 0, 0]], c, rc)),
          1 / np.sqrt(2), 1e-6)
    check('support from below at the COM', wg.feasibility(W, wg.generators([[0, 0, -0.05]], [[0, 0, 1]], c, rc)), 0.0, 1e-6)
    check('push from above only', wg.feasibility(W, wg.generators([[0, 0, 0.05]], [[0, 0, -1]], c, rc)), 1.0, 1e-9)
    check('no contacts', wg.feasibility(W, wg.generators([], [], c, rc)), 1.0)
    check('mu 0.1 pinch still holds (internal force)', wg.feasibility(W, wg.generators([[0.03, 0, 0], [-0.03, 0, 0]],
          [[-1, 0, 0], [1, 0, 0]], c, rc, mu=0.1)), 0.0, 1e-6)
    r = wg.cone_rays(np.array([0.3, -0.5, 0.81]), 1.0); n = np.array([0.3, -0.5, 0.81]) / np.linalg.norm([0.3, -0.5, 0.81])
    check('cone rays at 45 deg for mu 1', float(np.degrees(np.arccos(np.clip(r[:8] @ n, -1, 1))).max()), 45.0, 1e-6)
    # demand: constant linear acceleration and a spin about a non-principal axis (analytic omega x I omega)
    T, fps = 60, 20.0; tt = np.arange(T) / fps; acc = np.array([0.5, -0.2, 1.0]); w = np.array([0.0, 0.0, 2.0])
    P = 0.5 * tt[:, None] ** 2 * acc; Rr = Rot.from_rotvec(tt[:, None] * w)
    I = np.array([[2e-3, 4e-4, 0], [4e-4, 1e-3, 3e-4], [0, 3e-4, 5e-4]])
    Wd, _ = wg.demand_wrench(P, Rr.as_quat(), dict(mass=0.3, com=np.zeros(3), inertia=I), fps)
    k = T // 2; Iw = Rr[k].as_matrix() @ I @ Rr[k].as_matrix().T
    check('demand force m(a-g)', float(np.abs(Wd[k, :3] - 0.3 * (acc - np.array([0, 0, -9.81]))).max()), 0.0, 1e-6)
    check('demand torque w x I w', float(np.abs(Wd[k, 3:] - np.cross(w, Iw @ w)).max()), 0.0, 1e-4)
    print('SELFTEST', 'OK' if ok else 'FAILED')
    return 0 if ok else 1


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = p.add_subparsers(dest='cmd', required=True)
    x = sp.add_parser('list'); x.add_argument('out_dir'); x.add_argument('runs_txt')
    x = sp.add_parser('inventory'); x.add_argument('trees_dir'); x.add_argument('out')
    x = sp.add_parser('score'); x.add_argument('manifest'); x.add_argument('out')
    sp.add_parser('selftest')
    a = p.parse_args()
    if a.cmd == 'list':
        return list_store(a.out_dir, a.runs_txt)
    if a.cmd == 'inventory':
        return inventory(a.trees_dir, a.out)
    if a.cmd == 'score':
        return score(a.manifest, a.out)
    return selftest()


if __name__ == '__main__':
    sys.exit(main() or 0)
