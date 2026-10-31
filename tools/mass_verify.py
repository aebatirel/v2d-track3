"""What the trained policies and the official evaluator of the masses transfer check actually load (2026-10-31;
ops/jobs/mass_check.sh, docs/research/work/masses-transfer-20261031/PREREG.md). Run after training, before the verdict.

For every arm, seed and episode: the chosen checkpoint (results/<arm>s<seed>_glock_public/ep<N>/best/policy.safetensors,
the file the NREP official evaluations used). Its saved training config (safetensors metadata
user.resolved_config_json; the official evaluator rebuilds the scene from it: evaluation/harness.py evaluate_checkpoint,
task.parquet) -> the reference parquet (a folder must hold exactly one .parquet, data/parquet.py resolve_parquet) ->
object_urdf_paths -> the URDF FlashCHORD imports (assets/registry.py resolve_asset_path: the stored path verbatim when the
file exists, else re-rooted; scene/objects.py add_urdf keeps the URDF inertials) -> its <mass>, COM and inertia.
Checks (any failure makes the run INVALID for the verdict):
  - masses: mass0 arms load 0.3 kg for every object, props arms the props' mass_kg; the COM equals the source's;
  - same reference: every arm's parquet has the source reference's fingerprint (all columns but the asset paths) and
    differs from it only in object_urdf_paths;
  - same training: per episode and seed the two arms' saved configs differ only in output_dir and task/reference.parquet,
    or in a value that is equal once each arm's name is replaced by a token (where the arm's files live:
    runs/mass1s42_glock vs runs/mass0s42_glock, refs/mass1_sf vs refs/mass0_sf); reset.seed is the seed;
    training.total_environment_steps is --steps (the key glock_public.sh sets);
  - the evaluated rollouts name the chosen checkpoint (when the evaluator writes it into its metrics file).
NOT failures (2026-10-31 build amendments, PREREG.md):
  - a cell without a chosen checkpoint (no best/summary.json or best/policy.safetensors: its training or its checkpoint
    choice failed) is listed in "missing" -> the verdict is INCOMPLETE (PREREG section 3), not INVALID;
  - evaluations cut by EVAL_TIMEOUT (eval_rc.txt 124, or 137 = killed 60 s after the cut) are counted per cell in
    "eval_timeouts" (chosen checkpoint's NREP rollouts and the checkpoint curve) and reported with the verdict.
Usage: mass_verify.py --eps "2 12" --seeds "42 43" --arms "mass0:none mass1:PROPS.json" --steps 70004736 --out V.json
       [--content /content] [--manifests "M2.json M12.json"]
"""
import argparse, glob, hashlib, json, os, struct, sys
import pyarrow.parquet as pq

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mass_arm import read_inertial, traj_fingerprint, md5   # noqa: E402

ALLOWED_DIFF = {'output_dir', 'task.parquet', 'reference.parquet'}
STEPS_KEY = 'training.total_environment_steps'          # glock_public.sh: training.total_environment_steps=$STEPS
TIMEOUT_RC = ('124', '137')                             # timeout(1) -k 60: 124 cut at EVAL_TIMEOUT, 137 killed 60 s later


def ck_config(path):
    """(metadata, resolved config) of a safetensors checkpoint, read from its header (no safetensors package needed)."""
    with open(path, 'rb') as f:
        n = struct.unpack('<Q', f.read(8))[0]; h = json.loads(f.read(n))
    m = h.get('__metadata__', {})
    return m, json.loads(m['user.resolved_config_json'])


def resolve_parquet(p):
    """flash_chord/data/parquet.py resolve_parquet: a file, or a folder holding exactly one .parquet (recursive)."""
    if os.path.isfile(p):
        return p
    fs = sorted(glob.glob(os.path.join(p, '**', '*.parquet'), recursive=True))
    if len(fs) != 1:
        raise ValueError(f'{len(fs)} .parquet files (FlashCHORD needs exactly one) in the reference folder {p}')
    return fs[0]


def resolve_asset(p):
    """flash_chord/assets/registry.py resolve_asset_path, first branch: the stored path when it is a file."""
    return (p, 'verbatim') if os.path.isfile(p) else (None, 'NOT A FILE: FlashCHORD would re-root it on /assets/')


def flat(d, p=''):
    out = {}
    for k, v in d.items():
        q = f'{p}.{k}' if p else k
        out.update(flat(v, q) if isinstance(v, dict) else {q: v})
    return out


def find(c, key):
    return {k: v for k, v in flat(c).items() if k.split('.')[-1] == key}


def norm(v, arm):
    """v with the arm's name replaced by a token, so that a value differing between the two arms only by where the arm's
    files live (refs/mass1_sf/... vs refs/mass0_sf/..., runs/mass1s42_glock vs runs/mass0s42_glock) compares equal."""
    if isinstance(v, str):
        return v.replace(arm, '<ARM>')
    if isinstance(v, list):
        return [norm(x, arm) for x in v]
    if isinstance(v, dict):
        return {k: norm(x, arm) for k, x in v.items()}
    return v


def pair_diff(c0, c1, a0, a1):
    """(keys whose values differ, those equal after arm-name normalisation, the rest not in ALLOWED_DIFF = failures)."""
    f0, f1 = flat(c0), flat(c1); NO = object()
    raw = sorted(x for x in set(f0) | set(f1) if f0.get(x, NO) != f1.get(x, NO))
    arm_only = [x for x in raw if x in f0 and x in f1 and norm(f0[x], a0) == norm(f1[x], a1)]
    bad = [x for x in raw if x not in ALLOWED_DIFF and x not in arm_only]
    return raw, arm_only, bad


def rc_counts(files):
    """{exit code: count} of the eval_rc.txt files the evaluation loops write when EVAL_TIMEOUT is set."""
    c = {}
    for f in files:
        try:
            r = open(f).read().strip() or '?'
        except OSError:
            r = '?'
        c[r] = c.get(r, 0) + 1
    return c


def eval_timeouts(O):
    """Evaluations of a cell cut by EVAL_TIMEOUT: the chosen checkpoint's rollouts (best/r*) and the curve
    (curve/policy_*[/r*]); *_runs = evaluation folders, *_without_rc = folders without eval_rc.txt (not recorded)."""
    out = {}
    for part, runs in (('best', glob.glob(f'{O}/best/r*/eval.log')),
                       ('curve', glob.glob(f'{O}/curve/policy_*/eval.log') + glob.glob(f'{O}/curve/policy_*/r*/eval.log'))):
        rc = rc_counts([os.path.join(os.path.dirname(f), 'eval_rc.txt') for f in runs
                        if os.path.exists(os.path.join(os.path.dirname(f), 'eval_rc.txt'))])
        out[part] = sum(rc.get(x, 0) for x in TIMEOUT_RC)
        out[f'{part}_runs'] = len(runs); out[f'{part}_rc'] = rc; out[f'{part}_without_rc'] = len(runs) - sum(rc.values())
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for x in ('--eps', '--seeds', '--arms', '--out'):
        ap.add_argument(x, required=True)
    ap.add_argument('--steps', type=int, required=True); ap.add_argument('--content', default='/content')
    ap.add_argument('--manifests', default='')
    a = ap.parse_args()
    C = a.content.rstrip('/'); fails, cells, cfgs, missing = [], {}, {}, []
    arms = [x.split(':', 1) for x in a.arms.split()]
    man = {}
    for f in a.manifests.split():
        if os.path.exists(f):
            d = json.load(open(f)); man[int(d['episode'])] = d
        else:
            fails.append(f'manifest {f} missing')
    for ep in [int(x) for x in a.eps.split()]:
        src = man.get(ep, {})
        for arm, props in arms:
            want = {n: float(v['physics']['mass_kg']) for n, v in json.load(open(props)).items() if isinstance(v, dict) and 'physics' in v} \
                if props != 'none' else None
            for s in a.seeds.split():
                key = f'ep{ep}/{arm}/s{s}'; row = cells[key] = {}
                O = f'{C}/results/{arm}s{s}_glock_public/ep{ep}'
                ck = f'{O}/best/policy.safetensors'
                row['eval_timeouts'] = eval_timeouts(O)
                if not (os.path.exists(f'{O}/best/summary.json') and os.path.exists(ck)):   # no chosen checkpoint (training
                    row['missing'] = True; missing.append(key); continue                     # failed): INCOMPLETE, not INVALID
                try:
                    summ = json.load(open(f'{O}/best/summary.json'))
                    row['checkpoint'] = summ.get('checkpoint')
                    if not os.path.exists(ck):
                        raise FileNotFoundError(ck)
                    if row['checkpoint'] and os.path.exists(row['checkpoint']) and md5(row['checkpoint']) != md5(ck):
                        fails.append(f'{key}: best/policy.safetensors is not the checkpoint the summary names')
                    meta, cfg = ck_config(ck); cfgs[key] = cfg
                    row['checkpoint_steps'] = meta.get('user.environment_steps'); row['curriculum_stage'] = meta.get('user.curriculum_stage')
                    task = cfg['task']['parquet']; row['task_parquet'] = task
                    rp = resolve_parquet(task); row['reference_file'] = rp; row['reference_md5'] = md5(rp)
                    t = pq.read_table(rp); fp = traj_fingerprint(t); row['traj_fingerprint'] = fp
                    if src and fp != src['traj_fingerprint']:
                        fails.append(f'{key}: reference fingerprint {fp} != source {src["traj_fingerprint"]} (not the same reference)')
                    names = t.column('object_body_names')[0].as_py(); loaded = {}
                    for n, u in zip(names, t.column('object_urdf_paths')[0].as_py()):
                        p, how = resolve_asset(u)
                        if p is None:
                            fails.append(f'{key}: {n}: {u} {how}'); continue
                        m, com, I = read_inertial(open(p).read())
                        loaded[n] = dict(urdf=p, resolved=how, mass=m, com=com, ixx=I.get('ixx'))
                        exp = want[n] if want else 0.3
                        if abs(m - exp) > 1e-9:
                            fails.append(f'{key}: {n} loads {m} kg from {p}, expected {exp}')
                        if src and com != src['source_urdfs'][n]['com']:
                            fails.append(f'{key}: {n} COM {com} differs from the source URDF {src["source_urdfs"][n]["com"]}')
                        if not os.path.realpath(p).startswith(os.path.realpath(f'{C}/refs/{arm}_sf/ep{ep}') + '/'):
                            fails.append(f'{key}: {n} URDF {p} is not in this arm\'s asset copy')
                    row['loaded_urdfs'] = loaded
                    row['reset_seed'] = cfg.get('reset', {}).get('seed')
                    if str(row['reset_seed']) != str(s):
                        fails.append(f'{key}: reset.seed {row["reset_seed"]} != {s}')
                    st = flat(cfg).get(STEPS_KEY); row['total_environment_steps'] = st      # other keys of that name are
                    row['other_total_environment_steps'] = {k: v for k, v in find(cfg, 'total_environment_steps').items()
                                                            if k != STEPS_KEY}                 # left to the pair check
                    if str(st) != str(a.steps):
                        fails.append(f'{key}: {STEPS_KEY} {st} != {a.steps}')
                    sha = hashlib.sha256(open(ck, 'rb').read()).hexdigest(); ev = 0   # the evaluator records checkpoint_sha256
                    for f in sorted(glob.glob(f'{O}/best/r*/episode_*.json')):
                        d = json.load(open(f)); ev += 1
                        if 'checkpoint_sha256' in d and d['checkpoint_sha256'] != sha:
                            fails.append(f'{key}: {f} evaluated checkpoint sha256 {d["checkpoint_sha256"][:12]} != chosen {sha[:12]}')
                    row['evaluations'] = ev; row['checkpoint_sha256'] = sha
                except Exception as e:
                    row['error'] = f'{type(e).__name__}: {str(e)[:200]}'; fails.append(f'{key}: {row["error"]}')
    # pairs: the two arms of one episode and seed train with identical settings except where their files live
    pairs, arm_named = {}, {}
    for ep in a.eps.split():
        for s in a.seeds.split():
            ks = [f'ep{ep}/{arm}/s{s}' for arm, _ in arms]
            if all(k in cfgs for k in ks):
                d, dn = {}, {}
                for k in ks[1:]:
                    d[k], dn[k], bad = pair_diff(cfgs[ks[0]], cfgs[k], ks[0].split('/')[1], k.split('/')[1])
                    if bad:
                        fails.append(f'{ks[0]} vs {k}: saved configs differ in {bad[:8]}')
                pairs[f'ep{ep}/s{s}'] = d; arm_named[f'ep{ep}/s{s}'] = dn
            elif not any(k in missing for k in ks):                 # a missing cell is INCOMPLETE (verdict), not a failure
                fails.append(f'ep{ep}/s{s}: not every arm has a chosen checkpoint')
    tmo = {k: c['eval_timeouts'] for k, c in cells.items()
           if c['eval_timeouts']['best'] or c['eval_timeouts']['curve'] or c['eval_timeouts']['best_without_rc']}
    out = dict(ok=not fails, failures=fails, missing=missing, allowed_config_differences=sorted(ALLOWED_DIFF),
               pair_config_differences=pairs, pair_config_equal_after_arm_name=arm_named, eval_timeouts=tmo,
               cells=cells, rule='docs/research/work/masses-transfer-20261031/PREREG.md')
    json.dump(out, open(a.out, 'w'), indent=1)
    loads = '; '.join(k + ' ' + ','.join(f'{n} {v["mass"]}' for n, v in c.get('loaded_urdfs', {}).items()) for k, c in cells.items())
    print(('VERIFIED' if out['ok'] else f'VERIFY FAILED ({len(fails)}): ' + ' | '.join(fails[:6]))
          + (f' :: MISSING cells (no chosen checkpoint; INCOMPLETE unless a failure above): {missing}' if missing else '')
          + ' :: eval timeouts: ' + ('; '.join(f'{k} best {v["best"]}/{v["best_runs"]} curve {v["curve"]}/{v["curve_runs"]}'
                                              + (f' ({v["best_without_rc"]} best runs without eval_rc.txt)' if v['best_without_rc'] else '')
                                              for k, v in tmo.items()) or 'none')
          + ' :: ' + loads)
    sys.exit(0 if out['ok'] else 1)


if __name__ == '__main__':
    main()
