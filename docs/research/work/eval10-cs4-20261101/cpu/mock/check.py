"""Assertions on one eval-10 cavity-safe retrain mock run (2026-11-01).
Usage: check.py MR EXPECT SET [--ovf N]
  EXPECT: SWAP-ELIGIBLE:INCLUDE | SWAP-ELIGIBLE:UNCLEAN | NO-SWAP:GATE | INVALID:CELLS | INVALID:<STOPPED substring> | REFUSED
Prints one line per check and the summary; exit 1 if any check fails."""
import glob, json, os, re, sys
MR, EXPECT, SET = sys.argv[1], sys.argv[2], sys.argv[3]
OVF = int(sys.argv[sys.argv.index('--ovf') + 1]) if '--ovf' in sys.argv else None
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', '..', '..'))
sys.path.insert(0, f'{REPO}/tools')
import e10cs                                                                  # noqa: E402  (the REAL pins, not the mock copy's)
RID = '20261101-e10cs-mocksha'; C = f'{MR}/content'; G = f'{C}/results/ev10_cs'; ST = f'{MR}/store/runs/{RID}'
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
tr = [x for x in jl(f'{MR}/train_audit.log') if 'run' in x and not x.get('injected_failure')]
ev = [x for x in jl(f'{MR}/eval_audit.log') if x.get('kind') == 'official' and not x.get('injected_failure')]
if EXPECT == 'REFUSED':
    ok('rc 1 (refused at the start)', rc == 'rc=1', rc)
    ok('the refusal names PIECESET', "PIECESET 'ev10cs6' must be ev10cs4 or ev10cs5" in job, job[-200:])
    ok('nothing pulled, trained, evaluated or pushed', not dl and not up and not tr and not ev, (len(dl), len(up), len(tr), len(ev)))
    print(json.dumps(dict(mr=MR, expect=EXPECT, checks=len(res), failed=bad))); print(f'{len(res) - len(bad)}/{len(res)} checks pass' + (f'; FAILED: {bad}' if bad else ''))
    sys.exit(1 if bad else 0)
summ = js(f'{G}/summary.json'); label = summ.get('label'); want, tag = EXPECT.split(':', 1)
stop_expected = want == 'INVALID' and tag != 'CELLS'
ok(f'label {want}', label == want, f'{label}; {(summ.get("why") or [])[:2]}')
ok('rc 1 (stopped)' if stop_expected else 'rc 0', rc == ('rc=1' if stop_expected else 'rc=0'), rc)
ok('RESULT line in the job log', 'ev10_cs RESULT: ' + str(label) in job)
ok('no store listing (single-file downloads only)', not [x for x in hf if x['kind'] == 'LISTING'], len(dl))
ok('every download is e10v\'s run or the packed side\'s H5p7 draws', all(x['path'].startswith(('runs/20261031-e10v-caf38fb/', 'runs/20261031-h5p7-1a7cdff/')) for x in dl),
   sorted({x['path'].split('/')[1] for x in dl}))
ok('exactly one store upload (the final push), holding summary.json', len(up) == 1 and os.path.exists(f'{ST}/results/ev10_cs/summary.json'), up)
ok('the push holds no e10v or njmax result folder (results/ev10_v4p, results/ev10_nj, perc2e10vs*, perc2e10nj*)',
   not [p for p in ('results/ev10_v4p', 'results/ev10_nj', 'results/perc2e10vs*', 'refs/perc2e10vs*', 'results/perc2e10nj*', 'refs/perc2e10nj*')
        if glob.glob(f'{ST}/{p}')])
ok('nothing written under the packed or e10v result names on this box', not [p for p in ('refs/glockt/ep10', 'refs/perc2mck/ep10', 'results/glock_public/ep10',
   'refs/glock/ep10', 'results/ev10_v4p') if os.path.exists(f'{C}/{p}')] and not glob.glob(f'{C}/refs/perc2e10vs*') and not glob.glob(f'{C}/results/perc2e10vs*'))
ok('hands_mp / hand_refine / perc2 / score_registered never ran', not os.path.exists(f'{MR}/UNEXPECTED.log'))
pcs = js(f'{G}/pieces.json')
if stop_expected:
    st = open(f'{G}/STOPPED').read() if os.path.exists(f'{G}/STOPPED') else ''
    ok(f'stopped for: {tag}', tag in st, st.strip())
    ok('piece check reported the edited file', 'md5 differs from MD5SUMS' in json.dumps(pcs) or 'MD5SUMS md5' in json.dumps(pcs), (pcs.get('failures') or [])[:2])
    ok('nothing pulled, trained or evaluated after the STOP', not dl and not tr and not ev, (len(dl), len(tr), len(ev)))
    print(json.dumps(dict(mr=MR, expect=EXPECT, label=label, checks=len(res), failed=bad))); print(f'{len(res) - len(bad)}/{len(res)} checks pass' + (f'; FAILED: {bad}' if bad else ''))
    sys.exit(1 if bad else 0)
ok(f'piece set {SET}: MD5SUMS md5 = the pinned one, check ok' + (', clause (a) vs ev10cs4 holds' if SET == 'ev10cs5' else ''),
   pcs.get('ok') and pcs.get('set') == SET and pcs.get('md5sums_md5') == e10cs.SETS[SET]['md5sums']
   and (SET != 'ev10cs5' or (pcs.get('clause_a') or {}).get('clause_a')), (pcs.get('md5sums_md5'), pcs.get('failures')))
ast = js(f'{G}/assets.json'); u = ast.get('urdfs') or {}
ok('assets: REAL make_assets.py build, URDF md5 = the set\'s pinned md5, 24 / 21 collisions (byte copies of the pieces)',
   ast.get('ok') and {n: v.get('urdf_md5') for n, v in u.items()} == e10cs.SETS[SET]['urdf']
   and (u.get('blue_cup') or {}).get('collisions') == 24 and (u.get('beige_cup') or {}).get('collisions') == 21, {n: (v.get('urdf_md5'), v.get('collisions')) for n, v in u.items()})
arms = js(f'{G}/arms.json')
ok('arms: V = e10v\'s arms.json (md5, fingerprint, base); seed copies 42 / 43 byte copies; V names the set\'s URDFs, not e10v\'s',
   arms.get('ok') and sorted(arms.get('seeds', {})) == ['42', '43'] and all(v['md5'] == arms['source_md5'] for v in arms['seeds'].values())
   and all(v.get('md5') == e10cs.SETS[SET]['urdf'][n] and v.get('md5_equals_e10v') is False for n, v in arms.get('urdfs', {}).items()), arms.get('failures'))
ok('no_oracle accepted the piece set and every e10v input', all('none oracle-derived' in (open(f'{G}/{f}').read() if os.path.exists(f'{G}/{f}') else '')
                                                                   for f in ('no_oracle_pieces.txt', 'no_oracle_inputs.txt')))
ok('two trainings: seeds 42 and 43, 70,004,736 steps, runs/perc2e10css<seed>_glock/ep10-s<seed>, on the seed copies',
   sorted((x['seed'], x['steps']) for x in tr) == [('42', 70004736), ('43', 70004736)]
   and all(x['run'].endswith(f'/runs/perc2e10css{x["seed"]}_glock/ep10-s{x["seed"]}') and f'/refs/perc2e10css{x["seed"]}_glockt/ep10' in x['task'] for x in tr),
   [(x['run'][-40:], x['seed']) for x in tr])
ok('the trainings loaded the set\'s URDFs (md5) at 0.3 kg', tr and all({n: v['md5'] for n, v in x['loaded'].items()} == e10cs.SETS[SET]['urdf']
                                                                       and all(v['mass'] == 0.3 for v in x['loaded'].values()) for x in tr))
ok('stock contact limits: no sim.* override on the command line, saved sim / env.sim 512 / 256',
   tr and all(not x.get('sim_cli') and x.get('saved_sim') == [512, 256, 512, 256] and not [a for a in x.get('argv', []) if a.startswith('sim.')] for x in tr),
   [(x.get('sim_cli'), x.get('saved_sim')) for x in tr])
ok('every CLI training key equals the packed gl10A2 config (no mismatch; >= 10 keys compared)',
   tr and all(not x['cli_vs_packed_mismatch'] and len(x['cli_keys_compared']) >= 10 for x in tr),
   [(x['cli_vs_packed_mismatch'], len(x['cli_keys_compared'])) for x in tr])
real = re.findall(r'TRAIN_ARGS \[([^\]]*)\]', open(f'{REPO}/docs/research/work/perception-sprint-20261031/ev10retrain/results/job.log', errors='replace').read())
mine = re.findall(r'TRAIN_ARGS \[([^\]]*)\]', job)
ok('TRAIN_ARGS = e10v\'s REAL job log line, byte for byte', bool(real) and bool(mine) and set(mine) == set(real), (set(mine), set(real)))
keys = [sorted(a.split('=', 1)[0] for a in x.get('argv', []) if '=' in a) for x in tr]          # argv = the trainer's arguments
ok('the training command line has exactly the template keys + TRAIN_ARGS keys (same template as e10v)', keys and all(k == keys[0] for k in keys)
   and set(keys[0]) == {'experiment', 'embodiment', 'task.parquet', 'task.motion_speed', 'reset.seed', 'logging.mode', 'output_dir',
                        'training.total_environment_steps', 'curriculum', 'objective.force_closure.enabled', 'objective.force_closure.weight',
                        'objective.contact_wrench_support.weight', 'objective.unintended_contact.weight'}, keys[:1])
ok('glock_public ran with REUSE_REF / REQUIRE_REUSE and never rebuilt a reference',
   job.count('REUSE_REF: training on this box\'s finished reference') == 2 and not jl(f'{MR}/ref_audit.log'), len(jl(f'{MR}/ref_audit.log')))
ok('collision pieces logged from the set\'s folder', f'collision pieces from {C}/v2d-track3/meshes/carve/{SET}' in job)
ov = js(f'{G}/overflow.json').get('groups', {})
if OVF is not None:
    ok(f'overflow: each training log has {OVF} nefc lines (the injected count), the summary reads the same',
       all(ov.get(f'train_s{s}', {}).get('counts', {}).get('nefc') == OVF for s in ('42', '43'))
       and all(summ.get('overflow', {}).get('per_seed', {}).get(s, {}).get('dropped') == OVF for s in ('42', '43')),
       {s: ov.get(f'train_s{s}', {}).get('counts', {}).get('nefc') for s in ('42', '43')})
    ok('overflow label ' + ('"pieces not clean in training"' if OVF > 1000 else 'absent'),
       ('pieces not clean in training' in summ.get('labels_attached', [])) == (OVF > 1000), summ.get('labels_attached'))
for s in ('42', '43'):
    lf = js(f'{G}/lift_s{s}.json')
    ok(f'lift s{s}: 7 checkpoints x 3 repeats, e10v controls read (r1 max 2.5 / 0.3 cm)', lf.get('n_checkpoints') == 7
       and all(len(r['repeats']) == 3 for r in lf.get('checkpoints', []))
       and {k: c.get('carried_lift_r1_max_cm') for k, c in lf.get('controls', {}).items()} == {'e10v_s42': 2.5, 'e10v_s43': 0.3}, lf.get('n_checkpoints'))
cells = js(f'{G}/cells.json').get('seeds', {})
if tag == 'CELLS':
    ok('cells: seed 43 INVALID (the extra config key), seed 42 VERIFIED', cells.get('43', {}).get('status') == 'INVALID'
       and any('mock_extra_setting' in f for f in cells.get('43', {}).get('failures', [])) and cells.get('42', {}).get('status') == 'VERIFIED',
       {s: (c['status'], c['failures'][:1]) for s, c in cells.items()})
    ok('no official draw (INVALID cell: no choice)', not ev, len(ev))
    ok('choice status INVALID', js(f'{G}/choice.json').get('status') == 'INVALID')
else:
    ok('cells: both VERIFIED; config diff vs the packed checkpoint within the allowed keys; stock limits; V md5',
       all(c['status'] == 'VERIFIED' and set(c['config_diff_vs_packed']) <= e10cs.ALLOWED and c['sim_limits'] == {k: v for k, v in zip(e10cs.SIM_KEYS, (512, 256, 512, 256))}
           for c in cells.values()) and len(cells) == 2, {s: (c['status'], c.get('config_diff_vs_packed'), c['failures'][:1]) for s, c in cells.items()})
    ch = js(f'{G}/choice.json'); gt = js(f'{G}/gate.json')
    st = {s: dict(n=c['n'], mean=c['mean'], sd=c['sd']) for s, c in cells.items()}
    ok('choice = pack 9b rule (e10v rule 2) on the cells', ch.get('chosen') == e10cs.rule2_e10v(st, ['42', '43']) and ch.get('status') == 'CHOSEN', ch.get('chosen'))
    gate_want = tag != 'GATE'
    ok(f'training-box gate {"met" if gate_want else "NOT met"} (bar {e10cs.GATE_V})', gt.get('met') is gate_want,
       {s: (r['mean'], r['above']) for s, r in gt.get('seeds', {}).items()})
    if gate_want:
        ok('10 official calls of the chosen checkpoint on the pristine worktree, at stock 512', len(ev) == 10
           and all(x['cwd'].endswith('v2d_clean/robotic_grounding/flash_chord') and x['stored_njmax'] == 512 and x['ck'] == ch['checkpoint'] for x in ev), len(ev))
        ok('no_oracle accepted the chosen checkpoint (packable)', 'none oracle-derived' in open(f'{G}/no_oracle_choice.txt').read())
    else:
        ok('no official draw (gate not met)', not ev and not glob.glob(f'{G}/conf/r*'), len(ev))
        ok('label reason: training-box gate not met', any('training-box gate not met' in w for w in summ.get('why', [])), summ.get('why'))
    cnt = {k: v.get('n_scored') for k, v in summ.get('counts', {}).items()}
    ok('scored: conf ' + ('10' if gate_want else '0') + ', packed 10, old 1, train42 10, train43 10', cnt == dict(conf=10 if gate_want else 0, old=1, packed=10, train42=10, train43=10), cnt)
    vr = js(f'{G}/verify.json')
    ok('verify ok, every own-reference check ok', vr.get('ok') and all(vr.get('own_ref_checks', {}).values()) and len(vr.get('own_ref_checks', {})) >= 31,
       (vr.get('failures'), len(vr.get('own_ref_checks', {}))))
    inc = summ.get('pack10_inclusion', {})
    if want == 'SWAP-ELIGIBLE':
        ok('pack-10 inclusion: gain >= 0.02 on V and P -> INCLUDE', inc.get('include_in_pack10') is True and all(v >= 0.02 for v in inc.get('gain', {}).values()), inc)
    else:
        ok('pack-10 inclusion: not included', inc.get('include_in_pack10') is False, inc.get('reading'))
pc = summ.get('pieces', {})
ok('summary records the piece set, its MD5SUMS md5 and the 50-line manifest; the URDF inertials used',
   pc.get('set') == SET and pc.get('md5sums_md5') == e10cs.SETS[SET]['md5sums'] and len(pc.get('manifest') or []) == 50
   and set(summ.get('urdf_inertials', {})) == {'blue_cup', 'beige_cup'} and all('com_mm' in v and 'inertia' in v for v in summ['urdf_inertials'].values()),
   (pc.get('set'), pc.get('md5sums_md5'), len(pc.get('manifest') or [])))
print(json.dumps(dict(mr=MR, expect=EXPECT, label=label, checks=len(res), failed=bad)))
print(f'{len(res) - len(bad)}/{len(res)} checks pass' + (f'; FAILED: {bad}' if bad else ''))
sys.exit(1 if bad else 0)
