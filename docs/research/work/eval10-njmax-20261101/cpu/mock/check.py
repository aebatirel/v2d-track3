"""Assertions on one eval-10 njmax diagnostic mock run (2026-11-01).
Usage: check.py MR EXPECT [--ovf N]   EXPECT: SUPPORTED | FALSIFIED | INCONCLUSIVE | PARTIAL | INCOMPLETE | INVALID[:<STOPPED substring>]
Prints one line per check and the summary; exit 1 if any check fails."""
import glob, json, os, re, sys
MR, EXPECT = sys.argv[1], sys.argv[2]
OVF = int(sys.argv[sys.argv.index('--ovf') + 1]) if '--ovf' in sys.argv else None
RID = '20261101-e10nj-mocksha'; C = f'{MR}/content'; G = f'{C}/results/ev10_nj'; ST = f'{MR}/store/runs/{RID}'
O = f'{C}/results/perc2e10njs43_glock_public/ep10'; RUN = f'{C}/runs/perc2e10njs43_glock/ep10-s43'
res, bad = [], []


def ok(name, cond, info=''):
    res.append(dict(check=name, ok=bool(cond), info=str(info)[:300])); print(('ok   ' if cond else 'FAIL ') + name + (f'  [{info}]' if info != '' else ''))
    if not cond:
        bad.append(name)


def jl(f):
    return [json.loads(x) for x in open(f)] if os.path.exists(f) else []


def js(f):
    return json.load(open(f)) if os.path.exists(f) else {}


rc = open(f'{MR}/rc.txt').read().strip(); job = open(f'{C}/job.log', errors='replace').read()
hf = jl(f'{MR}/hf.log'); dl = [x for x in hf if x['kind'] == 'file']; up = [x for x in hf if x['kind'] == 'upload']
summ = js(f'{G}/summary.json'); label = summ.get('label'); stop_expected = EXPECT.startswith('INVALID:')
ok(f'label {EXPECT.split(":")[0]}', label == EXPECT.split(':')[0], f'{label}; {(summ.get("invalid_reasons") or [])[:2]}')
ok('rc 1 (stopped)' if stop_expected else 'rc 0', rc == ('rc=1' if stop_expected else 'rc=0'), rc)
if stop_expected:
    st = open(f'{G}/STOPPED').read() if os.path.exists(f'{G}/STOPPED') else ''
    ok(f'stopped for: {EXPECT.split(":", 1)[1]}', EXPECT.split(':', 1)[1] in st, st.strip())
ok('RESULT line in the job log', 'ev10_nj RESULT: ' + str(label) in job)
ok('no store listing (single-file downloads only)', not [x for x in hf if x['kind'] == 'LISTING'], len(dl))
miss = [x['path'] for x in dl if x.get('result') != 'ok']
ok('every download succeeded', not miss, miss[:4])
ok('every download is e10v\'s run (runs/20261031-e10v-caf38fb)', all(x['path'].startswith('runs/20261031-e10v-caf38fb/') for x in dl),
   sorted({x['path'].split('/')[1] for x in dl}))
ok('exactly one store upload (the final push)', len(up) == 1, up)
ok('the push is this run\'s and holds summary.json', os.path.exists(f'{ST}/results/ev10_nj/summary.json'))
ok('the push holds no e10v result folder of this box (results/ev10_v4p, perc2e10vs*)',
   not glob.glob(f'{ST}/results/ev10_v4p') and not glob.glob(f'{ST}/results/perc2e10vs*') and not glob.glob(f'{ST}/refs/perc2e10vs*'))
ok('hands_mp / hand_refine / perc2 / score_registered never ran', not os.path.exists(f'{MR}/UNEXPECTED.log'), jl(f'{MR}/UNEXPECTED.log')[:2])
ok('nothing under the packed names refs/glockt/ep10, refs/perc2mck/ep10, results/glock_public/ep10, refs/glock/ep10',
   not [p for p in ('refs/glockt/ep10', 'refs/perc2mck/ep10', 'results/glock_public/ep10', 'refs/glock/ep10') if os.path.exists(f'{C}/{p}')])
ok('no e10v folder written on this box (perc2e10vs*, results/ev10_v4p): e10v is read only',
   not glob.glob(f'{C}/refs/perc2e10vs*') and not glob.glob(f'{C}/results/perc2e10vs*') and not os.path.exists(f'{C}/results/ev10_v4p'))
arms = js(f'{G}/arms.json')
ok('arms: V = e10v\'s arms.json (md5, fingerprint, base, URDF inertials), seed copy refs/perc2e10njs43_glockt', arms.get('ok')
   and arms.get('seeds', {}).get('43', {}).get('md5') == arms.get('e10v_arms', {}).get('source_md5'), arms.get('failures'))
ok('no_oracle accepted every e10v input', 'none oracle-derived' in open(f'{G}/no_oracle_inputs.txt').read() if os.path.exists(f'{G}/no_oracle_inputs.txt') else False)
tr = [x for x in jl(f'{MR}/train_audit.log') if 'run' in x and not x.get('injected_failure')]
ok('exactly one training: seed 43, 70,004,736 steps, output runs/perc2e10njs43_glock/ep10-s43, on the seed copy',
   len(tr) == 1 and tr[0]['seed'] == '43' and tr[0]['steps'] == 70004736 and tr[0]['run'] == RUN and '/refs/perc2e10njs43_glockt/ep10' in tr[0]['task'],
   [(x['run'], x['seed'], x['steps']) for x in tr])
if tr:
    ok('the training got sim.njmax=1024 sim.nconmax=512 and saved them in sim and env.sim', tr[0].get('sim_cli') == {'sim.njmax': '1024', 'sim.nconmax': '512'}
       and tr[0].get('saved_sim') == [1024, 512, 1024, 512], (tr[0].get('sim_cli'), tr[0].get('saved_sim')))
    ok('every other CLI training key equals the packed gl10A2 config (mismatches = the two sim keys only)',
       sorted(tr[0]['cli_vs_packed_mismatch']) == ['sim.nconmax', 'sim.njmax'] and len(tr[0]['cli_keys_compared']) >= 10,
       (tr[0]['cli_vs_packed_mismatch'], len(tr[0]['cli_keys_compared'])))
m = re.search(r'TRAIN_ARGS \[([^\]]*)\]', job)
ok('TRAIN_ARGS = the FDR overrides, then the two sim overrides', bool(m) and m.group(1).startswith('curriculum=tracking_250m_mixed_reset_v2d')
   and m.group(1).endswith('sim.njmax=1024 sim.nconmax=512'), m.group(1) if m else None)
ok('glock_public ran with REUSE_REF / REQUIRE_REUSE and never rebuilt a reference',
   'REUSE_REF: training on this box\'s finished reference' in job and not jl(f'{MR}/ref_audit.log'), len(jl(f'{MR}/ref_audit.log')))
ov = js(f'{G}/overflow.json').get('groups', {})
if OVF is not None:
    ok(f'overflow: train.log nefc lines = {OVF} (the injected count)', ov.get('train', {}).get('counts', {}).get('nefc') == OVF, ov.get('train', {}).get('counts'))
    ok('overflow: the label clause O reads the same', summ.get('clauses', {}).get('O', {}).get('value') == OVF)
lf = js(f'{G}/lift.json')
ok('lift: 7 curve checkpoints x 3 repeats read, e10v controls read (r1 max 2.5 / 0.3 cm)', lf.get('n_checkpoints') == 7
   and all(len(r['repeats']) == 3 for r in lf.get('checkpoints', []))
   and {k: c.get('carried_lift_r1_max_cm') for k, c in lf.get('controls', {}).items()} == {'e10v_s42': 2.5, 'e10v_s43': 0.3},
   (lf.get('n_checkpoints'), {k: c.get('carried_lift_r1_max_cm') for k, c in lf.get('controls', {}).items()}))
if not stop_expected or os.path.exists(f'{G}/identity.json'):
    idn = js(f'{G}/identity.json')
    ok('identity vs e10v s43: config diff = paths + the four sim limits', set(idn.get('config_diff', [])) == {'output_dir', 'task.parquet', 'reference.parquet',
       'sim.njmax', 'sim.nconmax', 'env.sim.njmax', 'env.sim.nconmax'} if idn.get('ok') else EXPECT.startswith('INVALID'), idn.get('config_diff'))
if not stop_expected:
    ck = js(f'{G}/ck512.json')
    ok('512 copy: header-only (buffer identical, config diff = the four limits, 512/256)', ck.get('ok') and ck.get('buffer_identical')
       and ck.get('dst_sim') == {'sim.njmax': 512, 'sim.nconmax': 256, 'env.sim.njmax': 512, 'env.sim.nconmax': 256}, ck.get('failures'))
    sc = js(f'{G}/solver_check.json').get('checkpoints', {})
    ok('REAL FlashCHORD evaluator config chain (pin, CPU): ck1024 -> [1024, 512], ck512 -> [512, 256]',
       sc.get('ck1024', {}).get('env_config_sim') == [1024, 512] and sc.get('ck512', {}).get('env_config_sim') == [512, 256],
       {k: v.get('env_config_sim', v.get('error')) for k, v in sc.items()})
    gd = js(f'{G}/guard.json')
    ok('pack guard: no_oracle refused both checkpoints as is, as neutral byte copies and via a kit JSON', gd.get('ok') and len(gd.get('cases', [])) == 6,
       [(c['how'], c['refused']) for c in gd.get('cases', [])])
    ev = [x for x in jl(f'{MR}/eval_audit.log') if x.get('kind') == 'official' and not x.get('injected_failure')]
    c1 = [x for x in ev if x['ck'].endswith('perc2e10njs43_glock_public/ep10/best/policy.safetensors')]
    c5 = [x for x in ev if x['ck'].endswith('results/ev10_nj/ck512/policy.safetensors')]
    ok('10 official calls of the 1024 checkpoint, each rebuilt at njmax 1024 from its stored config', len(c1) == 10 and all(x['stored_njmax'] == 1024 for x in c1), len(c1))
    ok('10 official calls of the 512 copy, each rebuilt at njmax 512 from the copy\'s stored config', len(c5) == 10 and all(x['stored_njmax'] == 512 for x in c5), len(c5))
    ok('official draws ran on the pristine worktree (cwd, runtime root)', all(x['cwd'].endswith('v2d_clean/robotic_grounding/flash_chord') for x in ev) and len(ev) == 20)
    tb = [x for x in jl(f'{MR}/eval_audit.log') if x.get('kind') == 'train_box']
    ok('curve + training-box evaluations: 7 x 3 + 10, all of 1024 checkpoints', len(tb) == 31 and all(x['stored_njmax'] == 1024 for x in tb), len(tb))
    st = summ.get('sets', {})
    ok('scored: conf1024 10, conf512 10, train1024 10, e10v control 10 (all own-reference checks ok)',
       [((st.get(k) or {}).get('V') or {}).get('n') for k in ('conf1024', 'conf512', 'train1024', 'e10v_conf_control')] == [10, 10, 10, 10],
       [((st.get(k) or {}).get('V') or {}).get('n') for k in ('conf1024', 'conf512', 'train1024', 'e10v_conf_control')])
    ok('512 readout VALID', summ.get('readout_512', {}).get('status') == 'VALID', summ.get('readout_512', {}).get('problems'))
else:
    ok('no official draw after a STOP', not [x for x in jl(f'{MR}/eval_audit.log') if x.get('kind') == 'official'])
print(json.dumps(dict(mr=MR, expect=EXPECT, label=label, checks=len(res), failed=bad)))
print(f'{len(res) - len(bad)}/{len(res)} checks pass' + (f'; FAILED: {bad}' if bad else ''))
sys.exit(1 if bad else 0)
