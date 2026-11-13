"""Assertions on the D-arm training boxes of a finished run_all.sh mock (MS/done_{G,S25a,S25b,S30a,S30b}).
usage: check_train.py MS OUT.json. From what the stub FlashCHORD trainer / evaluators actually loaded (train_audit,
eval_audit), the patch calls (patch_audit), the training logs, the store log (hf.log) and the pushed run, per box:
  T1 one training per episode and seed, on the BYTE copy of the packed reference (md5 = the store's packed reference;
     fingerprint = the real packed_refs.json one), under refs/drs<seed>_glockt (grasp lock) / refs/perc2mckdr (std);
  T2 every training loaded the 0.3 kg placeholder for every object, grasp lock from the packed asset copy
     refs/sf/ep<N>/assets (byte-unchanged), std from /content/assets (= a fresh make_assets build with the table's pieces:
     eval 25 one <collision> per ev25 piece);
  T3 training env: FC_DR_RESET=1.5,0.015,0.01, FC_DR_SEED=<seed>; FC_DR_SKIP_IMMEDIATE=1 for 25 / 30 only; std also
     FC_IMMEDIATE_FIRST_FRAME 0.25; grasp lock: NO FC_DR_* in any evaluation process (TRAIN_ENV reaches the training only);
  T4 each training log holds the installed hook's line (seed, 2 objects; the skip tail for 25 / 30 only) and nothing else
     with "v2d FC_DR_RESET";
  T5 the DR patch ran after the box's other FlashCHORD patches (glock: VOC, FDR; std: patch_flashchord.py, FDR, VOC) in
     every invocation, on the real stand-in tree (reset.py tagged once), and the installed v2d_dr.py is what the repo
     patch writes;
  T6 steps 70,004,736 / 250,003,456, reset.seed = the seed; eval 33 with the rcB (CURR_SCALE 0.4) thresholds;
  T7 store traffic: exactly one upload, 0 listings, downloads = the table's pull_files + result files + recipe checkpoint;
  T8 nothing a pack pulls by default was written: no refs/mass1*, results/mass_eval, results/glock_public/ep<N>/best,
     refs/perc2mcks, results/hard_ab/ep<N>/mcks-s*; the pulled refs/glockt/ep<N> and refs/perc2mck/ep<N> are unchanged;
  T9 dr_eval_verify: every episode VERIFIED, packed-config differences only in allowed keys, a candidate with strings,
     D line ok per cell, hook md5 = expected, no other training logs;
  T10 the pushed run holds every candidate's checkpoint and D reference copy.
"""
import glob, hashlib, json, os, re, struct, sys
MS, OUT = sys.argv[1], sys.argv[2]
REPO = '/home/user/v2d-track3'
sys.path.insert(0, f'{REPO}/tools')
import pyarrow.parquet as pq                                   # noqa: E402
from mass_arm import traj_fingerprint, md5, read_inertial     # noqa: E402
REAL = json.load(open(f'{REPO}/docs/research/work/masses-eval-20261031/packed_refs.json'))['episodes']
MOCKT = json.load(open(f'{MS}/tmpl/content/v2d-track3/docs/research/work/masses-eval-20261031/packed_refs.json'))['episodes']
BOXES = dict(G=('glock', [14, 16, 33], [42, 43], '20261101-drG-mocksha'), S25a=('std', [25], [42], '20261101-drS25s42-mocksha'),
             S25b=('std', [25], [43], '20261101-drS25s43-mocksha'), S30a=('std', [30], [42], '20261101-drS30s42-mocksha'),
             S30b=('std', [30], [43], '20261101-drS30s43-mocksha'))
LINE = ('v2d FC_DR_RESET: sampled resets perturbed by +-1.5 mm, +-0.015 rad (rotation vector per axis), fingers +-0.01 rad; '
        '2 objects, 44 finger joints, 4096 worlds, seed {s}')
TAIL = '; skip immediate starts (FC_DR_SKIP_IMMEDIATE: deployment-exact starts not perturbed)'
res, fails = {}, []


def ok(name, cond, detail=''):
    res[name] = dict(ok=bool(cond), detail=str(detail)[:600])
    if not cond:
        fails.append(f'{name}: {str(detail)[:300]}')


def ckcfg(p):
    with open(p, 'rb') as f:
        n = struct.unpack('<Q', f.read(8))[0]
        return json.loads(json.loads(f.read(n))['__metadata__']['user.resolved_config_json'])


def tree(root):
    return {os.path.relpath(f, root): md5(f) for f in sorted(glob.glob(f'{root}/**/*', recursive=True)) if os.path.isfile(f)}


DEF = [19660800, 34406400, 49152000, 63897600, 78643200, 93388800, 108134400, 122880000, 137625600, 200007680, 250003456]
RCB = ckcfg(f'{MS}/store/runs/20261029-rcB-34bf6ae/results/glock_public/ep33/best/policy.safetensors')['curriculum']['thresholds']
for box, (mode, eps, seeds, rid) in BOXES.items():
    B = f'{MS}/done_{box}'; C = f'{B}/content'; CR = f'{MS}/box/content'
    fx = lambda p: p.replace(f'{MS}/box/', f'{B}/')
    rd = lambda n: [json.loads(x) for x in open(f'{B}/{n}.log')] if os.path.exists(f'{B}/{n}.log') else []
    tr = [x for x in rd('train_audit') if 'task' in x]; ev = rd('eval_audit'); pa = rd('patch_audit')
    for e in eps:
        T, TM = REAL[str(e)], MOCKT[str(e)]
        runs = {s: [x for x in tr if (f'/runs/drs{s}_glock/ep{e}-s{s}' if mode == 'glock' else f'/runs/perc2mckdr/ep{e}-s{s}') in x['run']] for s in seeds}
        ok(f'{box}_ep{e}_T1_one_training_per_seed', all(len(v) == 1 for v in runs.values()), {s: len(v) for s, v in runs.items()})
        store_ref = f'{MS}/store/runs/{T["source_run"]}/' + (f'refs/glockt/ep{e}' if mode == 'glock' else f'refs/perc2mck/ep{e}')
        sref = glob.glob(f'{store_ref}/processed/*/*/*.parquet')[0]
        for s, v in runs.items():
            if not v:
                continue
            x = v[0]; rf = fx(x['reference_file'])
            want_dir = f'{CR}/refs/drs{s}_glockt/ep{e}/' if mode == 'glock' else f'{CR}/refs/perc2mckdr/ep{e}/'
            ok(f'{box}_ep{e}_s{s}_T1_byte_copy_of_packed', md5(rf) == md5(sref) == TM['md5'] and x['fingerprint'] == T['traj_fingerprint']
               and x['reference_file'].startswith(want_dir), f"{x['reference_file']} md5 {md5(rf)} store {md5(sref)} fp {x['fingerprint']}")
            root = f'{CR}/refs/sf/ep{e}/assets/' if mode == 'glock' else f'{CR}/assets/'
            ok(f'{box}_ep{e}_s{s}_T2_train_masses_0.3', all(abs(u['mass'] - 0.3) < 1e-9 and u['urdf'].startswith(root) for u in x['loaded'].values()),
               {n: (u['mass'], u['urdf'].replace(MS, 'MS')) for n, u in x['loaded'].items()})
            env = x.get('env', {})
            want = {'FC_DR_RESET': '1.5,0.015,0.01', 'FC_DR_SEED': str(s), 'FC_DR_SKIP_IMMEDIATE': '1' if mode == 'std' else None}
            ok(f'{box}_ep{e}_s{s}_T3_training_env', all(env.get(k) == w for k, w in want.items())
               and (env.get('FC_IMMEDIATE_FIRST_FRAME') == '0.25') == (mode == 'std'), env)
            log = f'{C}/runs/' + (f'drs{s}_glock/ep{e}-s{s}' if mode == 'glock' else f'perc2mckdr/ep{e}-s{s}') + '/train.log'
            lines = [l_.strip() for l_ in open(log) if 'v2d FC_DR_RESET' in l_] if os.path.exists(log) else []
            exp = LINE.format(s=s) + (TAIL if mode == 'std' else '')
            ok(f'{box}_ep{e}_s{s}_T4_dr_line', lines and all(l_ == exp for l_ in lines), lines[:2])
            cfg = ckcfg(fx(sorted(glob.glob(fx(x['run']) + '/policy_*.safetensors'))[0]))
            th = cfg['curriculum']['thresholds'] if cfg['curriculum']['thresholds'] == cfg['training']['curriculum']['thresholds'] else 'DIFFERS'
            ok(f'{box}_ep{e}_s{s}_T6_steps_seed', x['steps'] == T['steps'] and x['seed'] == s
               and (mode == 'std' or th == (RCB if e == 33 else DEF)), (x['steps'], x['seed'], (th or [])[:3]))
        evs = [y for y in ev if (f'/drs' in y['ck'] if mode == 'glock' else '/perc2mckdr/' in y['ck']) and f'/ep{e}' in y['ck']]
        ok(f'{box}_ep{e}_T2_evals_0.3', evs and all(abs(u['mass'] - 0.3) < 1e-9 for y in evs for u in y['loaded'].values()), len(evs))
        if mode == 'glock':
            ok(f'{box}_ep{e}_T3_no_DR_env_in_evaluations', evs and all(not y.get('env') for y in evs),
               sorted({json.dumps(y.get('env')) for y in evs}))
            ok(f'{box}_ep{e}_T2_asset_copy_unchanged', tree(f'{C}/refs/sf/ep{e}/assets') == tree(f'{MS}/store/runs/{T["source_run"]}/refs/sf/ep{e}/assets'))
        else:
            ok(f'{box}_ep{e}_T3_std_evaluations_env_reported', True, sorted({json.dumps(y.get('env')) for y in evs}))
            if T.get('pieces'):
                k = {n: len(glob.glob(f'{REPO}/{T["pieces"]}/{n}/piece_*.obj')) for n in T['objects']}
                got = {n: len(re.findall('<collision>', open(f'{C}/assets/urdf/{n}_rigid.urdf').read())) for n in T['objects']}
                ok(f'{box}_ep{e}_T2_pieces', all(got[n] == k[n] for n in k if k[n]), (got, k))
            ok(f'{box}_ep{e}_T2_assets_eq_twin', tree(f'{C}/assets') == tree(f'{C}/results/dr_eval/assets_03'))
        ok(f'{box}_ep{e}_T8_pulled_refs_unchanged', md5(glob.glob(f'{C}/' + (f'refs/glockt/ep{e}' if mode == 'glock' else f'refs/perc2mck/ep{e}')
                                                                 + '/processed/*/*/*.parquet')[0]) == md5(sref))
    # T5 patch order per invocation
    names = [x['patch'] for x in pa]
    groups, cur = [], []
    for n in names:
        cur.append(n)
        if n == 'patch_flashchord_dr.py':
            groups.append(cur); cur = []
    want = ['patch_flashchord_voc.py', 'patch_flashchord_fdr.py', 'patch_flashchord_dr.py'] if mode == 'glock' else \
        ['patch_flashchord.py', 'patch_flashchord_fdr.py', 'patch_flashchord_voc.py', 'patch_flashchord_dr.py']
    ok(f'{box}_T5_dr_patch_last', groups and all(g == want for g in groups) and not cur and len(groups) == len(seeds) if mode == 'glock' else
       groups and all(g == want for g in groups) and not cur, names)
    L = f'{C}/v2d/robotic_grounding/flash_chord/src/flash_chord/lifecycle'
    ok(f'{box}_T5_tree_tagged_once', open(f'{L}/reset.py').read().count('# v2d patch: FC_DR_RESET') == 1)
    hf = [l_.split() for l_ in open(f'{B}/hf.log')]
    ups = [x for x in hf if x[1] == 'upload']; lst = [x for x in hf if '--include' in x]; dls = [x for x in hf if x[1] == 'download' and '--include' not in x]
    want_dl = set()
    for e in eps:
        T = REAL[str(e)]; want_dl |= set(T['pull_files']) | set(T['result_files']) | {T['recipe_checkpoint']}
    got_dl = {x[3] for x in dls}
    ok(f'{box}_T7_store', len(ups) == 1 and not lst and got_dl <= want_dl and set(f for f in want_dl if not f.endswith(('.txt', '.jpg', '_log.json'))) <= got_dl,
       (len(ups), len(lst), len(got_dl), sorted(want_dl - got_dl)[:4]))
    bad = [p for p in glob.glob(f'{C}/refs/mass1*') + glob.glob(f'{C}/results/mass_eval') + glob.glob(f'{C}/results/glock_public/ep*/best')
           + glob.glob(f'{C}/refs/perc2mcks') + glob.glob(f'{C}/results/hard_ab/ep*/mcks-s*')]
    ok(f'{box}_T8_no_default_folders', not bad, [p.replace(MS, 'MS') for p in bad])
    V = json.load(open(f'{C}/results/dr_eval/verify.json')); S = json.load(open(f'{C}/results/dr_eval/summary.json'))
    ok(f'{box}_T9_verified', V['ok'] and all(x['status'] == 'VERIFIED' for x in V['episodes'].values())
       and V['hook']['installed_md5'] == V['hook']['expected_md5'] and not V['other_training_logs'],
       {e: (x['status'], x['failures'][:2]) for e, x in V['episodes'].items()})
    for e, x in V['episodes'].items():
        for s, c in x['cells'].items():
            ok(f'{box}_ep{e}_s{s}_T9_config_diff_allowed', set(c.get('packed_config_diff', {})) <= {'output_dir', 'task.parquet', 'reference.parquet',
                                                                                                  'reset.seed', 'env.reset.seed', 'training.seed'},
               sorted(c.get('packed_config_diff', {})))
    ok(f'{box}_T9_candidates', all(S['episodes'][str(e)].get('pick_extra') and S['episodes'][str(e)].get('candidate_sha256') for e in eps),
       {e: S['episodes'][str(e)].get('pick_extra') for e in eps})
    P = f'{MS}/store/runs/{rid}'
    for e in eps:
        ent = S['episodes'][str(e)]; ck = ent['pick_extra'].split(':ck=')[1]
        ok(f'{box}_ep{e}_T10_pushed', os.path.isfile(f'{P}/{ck}') and glob.glob(f'{P}/{ent["runs_extra"].split("@")[1]}/processed/*/*/*.parquet')
           and hashlib.sha256(open(f'{P}/{ck}', 'rb').read()).hexdigest() == ent['candidate_sha256'], ck)
json.dump(dict(n=len(res), passed=sum(v['ok'] for v in res.values()), failures=fails, checks=res), open(OUT, 'w'), indent=1)
print(f'check_train: {sum(v["ok"] for v in res.values())} / {len(res)} pass' + ('' if not fails else ' :: FAIL ' + ' | '.join(fails[:8])))
