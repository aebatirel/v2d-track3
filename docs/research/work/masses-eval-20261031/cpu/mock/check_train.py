"""Assertions on the training boxes of a finished run_all.sh mock (MS/done_{G1,G2,G4,S1a,S1b}). usage: check_train.py MS OUT.json
From what the stub FlashCHORD trainer and evaluator actually loaded (train_audit.log, eval_audit.log), per episode:
  T1 every training read the PACKED policy's reference: its fingerprint is the real one of packed_refs.json (the repo
     copy, not the mock's) and the source file's; grasp lock: the training parquet differs from the source only in
     object_urdf_paths; std: the training parquet is byte-identical (md5) to the pulled refs/perc2mck file;
  T2 trainings loaded the props masses for every object, grasp lock from refs/mass1_sf/ep<N>/, std from /content/assets;
  T3 every official evaluation on the box (curve, NREP rollouts, std main + sweep) loaded its checkpoint's reference and
     the props masses (through the checkpoint's saved config);
  T4 steps 70,004,736 / 250,003,456, reset.seed = the seed, both seeds' arguments differ only in reset.seed; eval 33 trains
     with the CURR_SCALE 0.4 thresholds of its packed checkpoint (rcB), every other episode with the default ones;
  T5 the pulled references and asset folders are byte-unchanged after the box; on grasp-lock boxes /content/assets stays
     at 0.3 kg; on the std boxes /content/assets carries the props masses and ev01's 53 / 107 pieces;
  T6 store traffic per box: exactly one upload; the downloads are the table's pulls, result files and recipe checkpoint;
  T7 no reference stage ran on an eval episode (no grasp_lock / ILC / evolve / support_fill / rollout / rest_check);
  T8 mass_eval_verify: every episode VERIFIED, packed-config differences only in allowed keys, a rule-2 candidate and
     confirmation strings.
"""
import glob, json, os, re, struct, sys
MS, OUT = sys.argv[1], sys.argv[2]
REPO = '/home/user/v2d-track3'
sys.path.insert(0, f'{REPO}/tools')
import pyarrow.parquet as pq                                   # noqa: E402
from mass_arm import traj_fingerprint, md5, read_inertial     # noqa: E402
REAL = json.load(open(f'{REPO}/docs/research/work/masses-eval-20261031/packed_refs.json'))['episodes']
props = {n: v['physics']['mass_kg'] for n, v in json.load(open(f'{REPO}/docs/research/physics-2026-10-30/props_masses_only.json')).items()
         if isinstance(v, dict) and 'physics' in v}
BOXES = dict(G1=('glock', [20, 8], [42, 43], '20261101-mevG1-mocksha'), G2=('glock', [33, 15], [42, 43], '20261101-mevG2-mocksha'),
             G4=('glock', [10], [42], '20261101-mevG4-mocksha'), S1a=('std', [1], [42], '20261101-mevS1s42-mocksha'),
             S1b=('std', [1], [43], '20261101-mevS1s43-mocksha'))
res, fails = {}, []


def ok(name, cond, detail=''):
    res[name] = dict(ok=bool(cond), detail=str(detail)[:600])
    if not cond:
        fails.append(f'{name}: {str(detail)[:300]}')


def ckcfg(p):
    with open(p, 'rb') as f:
        n = struct.unpack('<Q', f.read(8))[0]
        return json.loads(json.loads(f.read(n))['__metadata__']['user.resolved_config_json'])


DEF = [19660800, 34406400, 49152000, 63897600, 78643200, 93388800, 108134400, 122880000, 137625600, 200007680, 250003456]
RCB = ckcfg(f'{MS}/store/runs/20261029-rcB-34bf6ae/results/glock_public/ep33/best/policy.safetensors')['curriculum']['thresholds']
for box, (mode, eps, seeds, rid) in BOXES.items():
    B = f'{MS}/done_{box}'; C = f'{B}/content'; CR = f'{MS}/box/content'   # CR: the path the box ran at (the audits hold it)
    fx = lambda p: p.replace(f'{MS}/box/', f'{B}/')
    rd = lambda n: [json.loads(x) for x in open(f'{B}/{n}.log')] if os.path.exists(f'{B}/{n}.log') else []
    tr = [x for x in rd('train_audit') if 'task' in x]; ev = rd('eval_audit')
    for e in eps:
        T = REAL[str(e)]
        if mode == 'glock':
            src = glob.glob(f'{C}/refs/glockt/ep{e}/processed/*/*/ref_gl_ilc.parquet')[0]
            runs = {s: [x for x in tr if f'/runs/mass1s{s}_glock/ep{e}-s{s}' in x['run']] for s in seeds}
        else:
            src = glob.glob(f'{C}/refs/perc2mck/ep{e}/processed/*/*/*.parquet')[0]
            runs = {s: [x for x in tr if f'/runs/perc2mcks/ep{e}-s{s}' in x['run']] for s in seeds}
        t0 = pq.read_table(src)
        ok(f'{box}_ep{e}_T1_one_training_per_seed', all(len(v) == 1 for v in runs.values()), {s: len(v) for s, v in runs.items()})
        for s, v in runs.items():
            if not v:
                continue
            x = v[0]; t = pq.read_table(fx(x['reference_file']))
            if mode == 'glock':
                same = t.drop_columns(['object_urdf_paths']).equals(t0.drop_columns(['object_urdf_paths']))
                ok(f'{box}_ep{e}_s{s}_T1_packed_reference', x['fingerprint'] == T['traj_fingerprint'] == traj_fingerprint(t0) and same
                   and t.column('object_urdf_paths')[0].as_py() != t0.column('object_urdf_paths')[0].as_py(),
                   f"{x['fingerprint']} vs real {T['traj_fingerprint']}")
            else:
                ok(f'{box}_ep{e}_s{s}_T1_packed_reference', x['fingerprint'] == T['traj_fingerprint'] and md5(fx(x['reference_file'])) == md5(src),
                   f"{x['fingerprint']} vs real {T['traj_fingerprint']}, md5 {md5(fx(x['reference_file']))} vs pulled {md5(src)}")
            root = f'{CR}/refs/mass1_sf/ep{e}/' if mode == 'glock' else f'{CR}/assets/'
            got = {n: u['mass'] for n, u in x['loaded'].items()}
            ok(f'{box}_ep{e}_s{s}_T2_train_masses', got == {n: props[n] for n in got} and all(u['urdf'].startswith(root) for u in x['loaded'].values()),
               f'{got} from {sorted({os.path.dirname(u["urdf"]).replace(MS, "MS") for u in x["loaded"].values()})}')
            ok(f'{box}_ep{e}_s{s}_T4_steps_seed', x['steps'] == T['steps'] and int(x['seed']) == s, (x['steps'], x['seed']))
            cfg = ckcfg(sorted(glob.glob(f'{fx(x["run"])}/policy_*.safetensors'))[-1])
            want = RCB if e == 33 else DEF
            ok(f'{box}_ep{e}_s{s}_T4_curriculum', cfg['curriculum']['thresholds'] == want and cfg['training']['curriculum']['thresholds'] == want,
               cfg['curriculum']['thresholds'])
            mine = [y for y in ev if (f'/runs/mass1s{s}_glock/ep{e}-s{s}/' if mode == 'glock' else f'/runs/perc2mcks/ep{e}-s{s}/') in y['ck']
                    or (mode == 'glock' and f'/mass1s{s}_glock_public/ep{e}/' in y['ck'])]
            bad = [y['out'] for y in mine if y['fingerprint'] != T['traj_fingerprint'] or
                   {n: u['mass'] for n, u in y['loaded'].items()} != {n: props[n] for n in y['loaded']} or
                   not all(u['urdf'].startswith(root) for u in y['loaded'].values())]
            nbest = len([y for y in mine if re.search(r'/best/r\d+/|/mcks-s\d+/r\d+/', y['out'])])
            ok(f'{box}_ep{e}_s{s}_T3_evaluations', mine and not bad and nbest == 10, f'{len(mine)} evaluations ({nbest} NREP), {len(bad)} wrong')
        if len(seeds) == 2 and all(runs.values()):
            a0, a1 = runs[seeds[0]][0]['args'], runs[seeds[1]][0]['args']
            ok(f'{box}_ep{e}_T4_seeds_differ_only_in_seed', sorted(set(a0) ^ set(a1)) == sorted(f'reset.seed={s}' for s in seeds), sorted(set(a0) ^ set(a1)))
        # T5 untouched sources
        if mode == 'glock':
            st = glob.glob(f'{MS}/store/runs/{T["source_run"]}/refs/glockt/ep{e}/processed/*/*/ref_gl_ilc.parquet')[0]
            ok(f'{box}_ep{e}_T5_reference_untouched', md5(st) == md5(src))
            sroot = f'{C}/refs/sf/ep{e}/assets' if not T['shared_assets'] else None
            if sroot:
                a = {os.path.relpath(f, sroot): md5(f) for f in glob.glob(f'{sroot}/**/*', recursive=True) if os.path.isfile(f)}
                b0 = f'{MS}/store/runs/{T["source_run"]}/refs/sf/ep{e}/assets'
                b = {os.path.relpath(f, b0): md5(f) for f in glob.glob(f'{b0}/**/*', recursive=True) if os.path.isfile(f)}
                ok(f'{box}_ep{e}_T5_asset_copy_untouched', a == b and all(abs(read_inertial(open(f'{sroot}/{k}').read())[0] - 0.3) < 1e-12
                                                                          for k in a if k.endswith('.urdf')), f'{len(a)} files')
        else:
            st = glob.glob(f'{MS}/store/runs/{T["source_run"]}/refs/perc2mck/ep{e}/processed/*/*/*.parquet')[0]
            ok(f'{box}_ep{e}_T5_reference_untouched', md5(st) == md5(src))
    U = glob.glob(f'{C}/assets/urdf/*.urdf')
    if mode == 'glock':
        ok(f'{box}_T5_content_assets_placeholder', U and all(abs(read_inertial(open(f).read())[0] - 0.3) < 1e-12 for f in U), f'{len(U)} URDFs')
    else:
        m = {os.path.basename(f)[:-11]: read_inertial(open(f).read())[0] for f in U}
        cols = {n: open(f'{C}/assets/urdf/{n}_rigid.urdf').read().count('<collision>') for n in ('white_pot', 'white_pot_lid')}
        ok(f'{box}_T5_content_assets_masses_and_pieces', m == {n: props[n] for n in m} and cols == dict(white_pot=53, white_pot_lid=107), (m, cols))
    hf = open(f'{B}/hf.log').read().splitlines()
    ups = [x for x in hf if x.startswith('hf upload')]
    dl = sorted(x.split('--include ')[1].split()[0] if '--include' in x else x.split()[3] for x in hf if x.startswith('hf download'))
    want = sorted([f'runs/{REAL[str(e)]["source_run"]}/{s}/*' for e in eps for s in REAL[str(e)]['pull']]
                  + [f for e in eps for f in REAL[str(e)]['result_files']] + [REAL[str(e)]['recipe_checkpoint'] for e in eps])
    ok(f'{box}_T6_one_push', len(ups) == 1 and f'runs/{rid}' in ups[0], len(ups))
    ok(f'{box}_T6_pulls_exactly_the_table', dl == want, f'{dl} vs {want}')
    ok(f'{box}_T7_no_reference_stage', not os.path.exists(f'{B}/forbidden_audit.log'),
       open(f'{B}/forbidden_audit.log').read()[:300] if os.path.exists(f'{B}/forbidden_audit.log') else '')
    V = json.load(open(f'{C}/results/mass_eval/verify.json')); S = json.load(open(f'{C}/results/mass_eval/summary.json'))
    ok(f'{box}_T8_verified', V['ok'] and all(V['episodes'][str(e)]['status'] == 'VERIFIED' for e in eps),
       {e: (x['status'], x['failures'][:2]) for e, x in V['episodes'].items()})
    allowed = {'output_dir', 'task.parquet', 'reference.parquet', 'reset.seed', 'env.reset.seed', 'training.seed'}
    diffs = {f'ep{e}/s{s}': sorted(c.get('packed_config_diff', {'<missing>': 0})) for e, x in V['episodes'].items() for s, c in x['cells'].items()}
    ok(f'{box}_T8_packed_config_diff_allowed_only', all(set(d) <= allowed for d in diffs.values()), diffs)
    ok(f'{box}_T8_candidates', all(S['episodes'][str(e)].get('pick_extra') for e in eps) and S['confirmation']['MASS_EPS'].split() == [str(e) for e in eps],
       S['confirmation'])
out = dict(ok=not fails, failures=fails, checks=res, note='mock scores are synthetic (stub.py): plumbing, not masses')
json.dump(out, open(OUT, 'w'), indent=1)
print(('ALL TRAINING CHECKS PASS' if not fails else f'{len(fails)} FAILED: ' + ' | '.join(fails[:8])) + f' ({len(res)} checks)')
sys.exit(0 if not fails else 1)
