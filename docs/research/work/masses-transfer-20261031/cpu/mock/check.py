"""Assertions on a finished masses-transfer mock (run_mock.sh with the JOBS.txt string). usage: check.py MR OUT.json
Proves, from what the stub FlashCHORD trainer and evaluator actually loaded (train_audit.log, eval_audit.log):
  C1 8 trainings: ep2 / ep12 x mass0 / mass1 x seeds 42 / 43, every one 70,004,736 steps, reset.seed = its seed;
  C2 per episode all 4 trainings read the SAME reference (fingerprint over every column but the asset paths), which for
     ep12 is the stored ev2 file (PREREG f7d8bb94...) and for ep2 the reference built on the box from the ev3 base
     (not E3's stored grasp-lock reference, also in the fake store); the arm parquets differ from the source only in
     object_urdf_paths;
  C3 the URDFs each training loaded: mass1 = props_masses_only.json, mass0 = 0.3 kg, each from its own arm folder;
  C4 every official evaluation (curve and best) loaded the URDFs of its checkpoint's arm, via the checkpoint's saved
     task.parquet (the stub evaluator reads the checkpoint's metadata, as evaluation/harness.py does);
  C5 the two arms of an episode and seed train with identical arguments and environment except output_dir / task.parquet;
  C6 the shared reference and its asset folder are untouched (md5 before = after); /content/assets stays 0.3 kg (no MA_ARGS);
  C7 store traffic: one upload (the job's single push); downloads = the pulls of the design only;
  C8 mass_verify.py VERIFIED, mass_verdict.py summary with 8 cells of n 10 and a verdict.
"""
import glob, json, os, re, sys
MR, OUT = sys.argv[1], sys.argv[2]
C = f'{MR}/content'
sys.path.insert(0, f'{C}/v2d-track3/tools')
import pyarrow.parquet as pq                                  # noqa: E402
from mass_arm import traj_fingerprint, md5, read_inertial    # noqa: E402

res, fails = {}, []


def ok(name, cond, detail=''):
    res[name] = dict(ok=bool(cond), detail=detail)
    if not cond:
        fails.append(f'{name}: {detail}')


props = json.load(open(f'{C}/v2d-track3/docs/research/physics-2026-10-30/props_masses_only.json'))
want = {n: v['physics']['mass_kg'] for n, v in props.items() if isinstance(v, dict) and 'physics' in v}
tr = [json.loads(x) for x in open(f'{MR}/train_audit.log')]; starts = [x for x in tr if 'task' in x]
ev = [json.loads(x) for x in open(f'{MR}/eval_audit.log')]


def arm_of(path):                                            # .../runs/mass1s43_glock/ep12-s43/... -> (mass1, 43, 12)
    m = re.search(r'/(mass[01])s(\d+)_glock[^/]*/ep(\d+)', path)
    return m.group(1), int(m.group(2)), int(m.group(3))


cells = {}
for x in starts:
    a, s, ep = arm_of(x['run']); cells[(ep, a, s)] = x
ok('C1_eight_trainings', sorted(cells) == sorted((e, a, s) for e in (2, 12) for a in ('mass0', 'mass1') for s in (42, 43))
   and len(starts) == 8, f'{len(starts)} trainings: {sorted(cells)}')
ok('C1_steps_seed', all(x['steps'] == 70004736 and int(x['seed']) == s for (e, a, s), x in cells.items()),
   str({f'ep{e}/{a}/s{s}': (x['steps'], x['seed']) for (e, a, s), x in cells.items()}))
stored12 = f7 = 'f7d8bb94a6087baa06e2f262e47118e9'
e3 = traj_fingerprint(pq.read_table(glob.glob(f'{MR}/store/runs/20261024-ev3-2c1e4dd/refs/glockt/ep2/processed/*/*/*.parquet')[0]))
for ep in (2, 12):
    fps = {x['fingerprint'] for (e, a, s), x in cells.items() if e == ep}
    src = glob.glob(f'{C}/refs/glockt/ep{ep}/processed/*/*/ref_gl_ilc.parquet')[0]; sfp = traj_fingerprint(pq.read_table(src))
    ok(f'C2_same_reference_ep{ep}', len(fps) == 1 and fps == {sfp}, f'training fingerprints {fps}, source {sfp}')
    if ep == 12:
        ok('C2_ep12_is_stored_ev2_reference', sfp == stored12, f'{sfp} vs PREREG {stored12}')
    else:
        ok('C2_ep2_built_here_not_E3', sfp != e3 and not os.path.exists(f'{C}/hfstore/runs/20261024-ev3-2c1e4dd/refs/glockt'),
           f'built {sfp}, E3 stored {e3}')
    t0 = pq.read_table(src)
    for (e, a, s), x in cells.items():
        if e != ep:
            continue
        t = pq.read_table(x['reference_file'])
        same = t.drop_columns(['object_urdf_paths']).equals(t0.drop_columns(['object_urdf_paths']))
        ok(f'C2_only_urdf_paths_differ_ep{e}_{a}_s{s}', same and t.column('object_urdf_paths')[0].as_py() != t0.column('object_urdf_paths')[0].as_py(),
           x['reference_file'].replace(MR, 'MR'))
for (e, a, s), x in cells.items():
    exp = {n: (want[n] if a == 'mass1' else 0.3) for n in x['loaded']}
    got = {n: v['mass'] for n, v in x['loaded'].items()}
    ok(f'C3_train_masses_ep{e}_{a}_s{s}', got == exp and all(f'/refs/{a}_sf/ep{e}/' in v['urdf'] for v in x['loaded'].values()),
       f'{got} from {sorted({os.path.dirname(v["urdf"]).replace(MR, "MR") for v in x["loaded"].values()})}')
bad = []
for x in ev:
    a, s, ep = arm_of(x['ck'])
    got = {n: v['mass'] for n, v in x['loaded'].items()}; exp = {n: (want[n] if a == 'mass1' else 0.3) for n in got}
    if got != exp or not all(f'/refs/{a}_sf/ep{ep}/' in v['urdf'] for v in x['loaded'].values()) or x['fingerprint'] != cells[(ep, a, s)]['fingerprint']:
        bad.append(x['ck'].replace(MR, 'MR'))
best = [x for x in ev if '/best/' in x['out']]
ok('C4_every_evaluation_loads_its_arm', not bad and len(ev) == 8 * (7 * 3 + 10) and len(best) == 80,
   f'{len(ev)} evaluations ({len(best)} of chosen checkpoints), {len(bad)} wrong: {bad[:3]}')
for ep in (2, 12):
    for s in (42, 43):
        x0, x1 = cells[(ep, 'mass0', s)], cells[(ep, 'mass1', s)]
        ok(f'C5_identical_settings_ep{ep}_s{s}', x0['args'] == x1['args'] and x0['env'] == x1['env'],
           f'args differ: {sorted(set(x0["args"]) ^ set(x1["args"]))}; env {x0["env"]} vs {x1["env"]}')
ok('C5_seeds_differ_only_in_seed', all(sorted(set(cells[(e, a, 42)]['args']) ^ set(cells[(e, a, 43)]['args'])) ==
                                       ['reset.seed=42', 'reset.seed=43'] for e in (2, 12) for a in ('mass0', 'mass1')), '')
# C6: the shared reference and its asset copy unchanged; /content/assets at the placeholder
st12 = glob.glob(f'{MR}/store/runs/20261024-ev2-2c1e4dd/refs/glockt/ep12/processed/*/*/ref_gl_ilc.parquet')[0]
ok('C6_shared_ep12_reference_untouched', md5(st12) == md5(glob.glob(f'{C}/refs/glockt/ep12/processed/*/*/ref_gl_ilc.parquet')[0]), '')
for ep, root in ((12, f'{MR}/store/runs/20261024-ev2-2c1e4dd/refs/sf/ep12/assets'), (2, None)):
    sf = f'{C}/refs/sf/ep{ep}/assets'
    m = {os.path.relpath(f, sf): md5(f) for f in glob.glob(f'{sf}/**/*', recursive=True) if os.path.isfile(f)}
    m0 = {os.path.relpath(f, f'{C}/refs/mass0_sf/ep{ep}/assets'): md5(f) for f in glob.glob(f'{C}/refs/mass0_sf/ep{ep}/assets/**/*', recursive=True) if os.path.isfile(f)}
    ok(f'C6_mass0_assets_byte_identical_to_shared_ep{ep}', m == m0, f'{len(m)} files')
    if root:
        mr = {os.path.relpath(f, root): md5(f) for f in glob.glob(f'{root}/**/*', recursive=True) if os.path.isfile(f)}
        ok(f'C6_shared_assets_untouched_ep{ep}', m == mr, '')
ok('C6_content_assets_placeholder', all(abs(read_inertial(open(f).read())[0] - 0.3) < 1e-12 for f in glob.glob(f'{C}/assets/urdf/*.urdf')),
   f'{len(glob.glob(f"{C}/assets/urdf/*.urdf"))} URDFs')
hf = open(f'{MR}/hf.log').read().splitlines()
ok('C7_one_push', sum(1 for x in hf if x.startswith('hf upload')) == 1, f'{sum(1 for x in hf if x.startswith("hf upload"))} uploads')
ok('C7_pulls', sorted(x.split()[x.split().index('--include') + 1] if '--include' in x else x.split()[3] for x in hf if x.startswith('hf download')) == sorted([
    'runs/20261024-ev3-2c1e4dd/refs/perc2mck/ep2/*', 'runs/20261024-ev2-2c1e4dd/refs/perc2mc/ep12/*', 'runs/20261024-ev2-2c1e4dd/refs/sf/ep12/*',
    'runs/20261024-ev2-2c1e4dd/refs/glockt/ep12/*', 'runs/20261024-ev2-2c1e4dd/results/glock_public/ep12/rest_check.json']), str(hf))
V = json.load(open(f'{C}/results/mass_check/verify.json')); Sm = json.load(open(f'{C}/results/mass_check/summary.json'))
ok('C8_verified', V['ok'], str(V['failures'][:3]))
ok('C8_summary', len([c for c in Sm['cells'].values() if c and c['auc'] and c['auc']['n'] == 10]) == 8 and Sm['verdict'] in ('ADOPT', 'NOT ADOPTED'),
   f"verdict {Sm['verdict']} (mock scores: not evidence)")
ok('C8_pair_config_diffs_allowed', all(set(d) <= {'output_dir', 'task.parquet', 'reference.parquet'} for p in V['pair_config_differences'].values()
                                       for d in p.values()), str(V['pair_config_differences']))
out = dict(ok=not fails, failures=fails, checks=res, trainings=len(starts), evaluations=len(ev), verdict_mock=Sm['verdict'],
           note='mock scores are synthetic (stub.py); they test the plumbing, not masses')
json.dump(out, open(OUT, 'w'), indent=1)
print(('ALL CHECKS PASS' if not fails else f'{len(fails)} FAILED: ' + ' | '.join(fails)) + f' ({len(res)} checks)')
sys.exit(0 if not fails else 1)
