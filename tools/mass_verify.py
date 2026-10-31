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
  - same training: per episode and seed the two arms' saved configs differ only in output_dir and task/reference.parquet;
    reset.seed is the seed; total_environment_steps equal in all arms;
  - the evaluated rollouts name the chosen checkpoint (when the evaluator writes it into its metrics file).
Usage: mass_verify.py --eps "2 12" --seeds "42 43" --arms "mass0:none mass1:PROPS.json" --steps 70004736 --out V.json
       [--content /content] [--manifests "M2.json M12.json"]
"""
import argparse, glob, hashlib, json, os, struct, sys
import pyarrow.parquet as pq

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mass_arm import read_inertial, traj_fingerprint, md5   # noqa: E402

ALLOWED_DIFF = {'output_dir', 'task.parquet', 'reference.parquet'}


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
        raise ValueError(f'reference folder {p} holds {len(fs)} .parquet files (FlashCHORD needs exactly one)')
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
    return [v for k, v in flat(c).items() if k.split('.')[-1] == key]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for x in ('--eps', '--seeds', '--arms', '--out'):
        ap.add_argument(x, required=True)
    ap.add_argument('--steps', type=int, required=True); ap.add_argument('--content', default='/content')
    ap.add_argument('--manifests', default='')
    a = ap.parse_args()
    C = a.content.rstrip('/'); fails, cells, cfgs = [], {}, {}
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
                    st = find(cfg, 'total_environment_steps'); row['total_environment_steps'] = st
                    if not st or any(int(x) != a.steps for x in st):
                        fails.append(f'{key}: total_environment_steps {st} != {a.steps}')
                    sha = hashlib.sha256(open(ck, 'rb').read()).hexdigest(); ev = 0   # the evaluator records checkpoint_sha256
                    for f in sorted(glob.glob(f'{O}/best/r*/episode_*.json')):
                        d = json.load(open(f)); ev += 1
                        if 'checkpoint_sha256' in d and d['checkpoint_sha256'] != sha:
                            fails.append(f'{key}: {f} evaluated checkpoint sha256 {d["checkpoint_sha256"][:12]} != chosen {sha[:12]}')
                    row['evaluations'] = ev; row['checkpoint_sha256'] = sha
                except Exception as e:
                    row['error'] = f'{type(e).__name__}: {str(e)[:200]}'; fails.append(f'{key}: {row["error"]}')
    # pairs: the two arms of one episode and seed train with identical settings except where their files live
    pairs = {}
    for ep in a.eps.split():
        for s in a.seeds.split():
            ks = [f'ep{ep}/{arm}/s{s}' for arm, _ in arms]
            if all(k in cfgs for k in ks):
                f0 = flat(cfgs[ks[0]]); d = {}
                for k in ks[1:]:
                    f1 = flat(cfgs[k])
                    d[k] = sorted(x for x in set(f0) | set(f1) if f0.get(x) != f1.get(x))
                    bad = [x for x in d[k] if x not in ALLOWED_DIFF]
                    if bad:
                        fails.append(f'{ks[0]} vs {k}: saved configs differ in {bad[:8]}')
                pairs[f'ep{ep}/s{s}'] = d
            else:
                fails.append(f'ep{ep}/s{s}: not every arm has a chosen checkpoint')
    out = dict(ok=not fails, failures=fails, allowed_config_differences=sorted(ALLOWED_DIFF), pair_config_differences=pairs,
               cells=cells, rule='docs/research/work/masses-transfer-20261031/PREREG.md')
    json.dump(out, open(a.out, 'w'), indent=1)
    loads = '; '.join(k + ' ' + ','.join(f'{n} {v["mass"]}' for n, v in c.get('loaded_urdfs', {}).items()) for k, c in cells.items())
    print(('VERIFIED' if out['ok'] else f'VERIFY FAILED ({len(fails)}): ' + ' | '.join(fails[:6])) + ' :: ' + loads)
    sys.exit(0 if out['ok'] else 1)


if __name__ == '__main__':
    main()
