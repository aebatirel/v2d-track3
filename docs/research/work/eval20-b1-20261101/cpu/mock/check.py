"""Assertions on one eval-20 b1 retrain mock run (2026-11-01; after eval10-cs4-20261101/cpu/mock/check.py).
Usage: check.py MR EXPECT [--ovf N]
  EXPECT: SWAP-ELIGIBLE:INCLUDE | SWAP-ELIGIBLE:UNCLEAN | NO-SWAP:GATE | INVALID:CELLS | INVALID:<STOPPED substring> | REFUSED
Prints one line per check and the summary; exit 1 if any check fails."""
import glob, hashlib, json, os, re, sys
MR, EXPECT = sys.argv[1], sys.argv[2]
OVF = int(sys.argv[sys.argv.index('--ovf') + 1]) if '--ovf' in sys.argv else None
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', '..', '..'))
W = os.path.join(REPO, 'docs/research/work/eval20-b1-20261101')
sys.path.insert(0, f'{REPO}/tools')
import e10cs, e20b1                                                          # noqa: E402  (the REAL pins, not the mock copy's)
RID = os.environ.get('MOCK_RUN_ID', '20261101-e20b1-mocksha'); C = f'{MR}/content'; G = f'{C}/results/ev20_b1'; ST = f'{MR}/store/runs/{RID}'
SRC = 'runs/20261025-evb1420-ee7ba8e'; res, bad = [], []
md5 = lambda f: hashlib.md5(open(f, 'rb').read()).hexdigest() if os.path.isfile(f) else None
rd = lambda f: open(f, errors='replace').read() if os.path.isfile(f) else ''


def ok(name, cond, info=''):
    res.append(dict(check=name, ok=bool(cond), info=str(info)[:300])); print(('ok   ' if cond else 'FAIL ') + name + (f'  [{info}]' if info != '' else ''))
    if not cond:
        bad.append(name)


def jl(f):
    return [json.loads(x) for x in open(f)] if os.path.exists(f) else []


def js(f):
    return json.load(open(f)) if os.path.exists(f) else {}


def done():
    print(json.dumps(dict(mr=MR, expect=EXPECT, checks=len(res), failed=bad)))
    print(f'{len(res) - len(bad)}/{len(res)} checks pass' + (f'; FAILED: {bad}' if bad else '')); sys.exit(1 if bad else 0)


rc = open(f'{MR}/rc.txt').read().strip(); job = open(f'{C}/job.log', errors='replace').read()
hf = jl(f'{MR}/hf.log'); dl = [x for x in hf if x['kind'] == 'file']; up = [x for x in hf if x['kind'] == 'upload']
tr = [x for x in jl(f'{MR}/train_audit.log') if 'run' in x and not x.get('injected_failure')]
ev = [x for x in jl(f'{MR}/eval_audit.log') if x.get('kind') == 'official' and not x.get('injected_failure')]
if EXPECT == 'REFUSED':
    ok('rc 1 (refused at the start)', rc == 'rc=1', rc)
    ok('the refusal names the run id rule', "must contain -e20b1-" in job, job[-200:])
    ok('nothing pulled, trained, evaluated or pushed', not dl and not up and not tr and not ev, (len(dl), len(up), len(tr), len(ev)))
    done()
summ = js(f'{G}/summary.json'); label = summ.get('label'); want, tag = EXPECT.split(':', 1)
stop_expected = want == 'INVALID' and tag != 'CELLS'
ok(f'label {want}', label == want, f'{label}; {(summ.get("why") or [])[:2]}')
ok('rc 1 (stopped)' if stop_expected else 'rc 0', rc == ('rc=1' if stop_expected else 'rc=0'), rc)
ok('RESULT line in the job log', 'ev20_b1 RESULT: ' + str(label) in job)
ok('no store listing (single-file downloads only)', not [x for x in hf if x['kind'] == 'LISTING'], len(dl))
ok('every download is the packed run\'s, the H5p7 draws or pack 6\'s eval-20 rollout',
   all(x['path'].startswith((SRC + '/', 'runs/20261031-h5p7-1a7cdff/', 'runs/20261026-pack6-5203d42/')) for x in dl), sorted({x['path'].split('/')[1] for x in dl}))
ok('exactly one store upload (the final push), into this run id, holding summary.json',
   len(up) == 1 and up[0]['dst'] == f'runs/{RID}' and os.path.exists(f'{ST}/results/ev20_b1/summary.json'), up)
ok('hands_mp / hand_refine / perc2 / score_registered never ran', not os.path.exists(f'{MR}/UNEXPECTED.log'))
pcs = js(f'{G}/pieces.json')
if stop_expected:
    st = rd(f'{G}/STOPPED')
    ok(f'stopped for: {tag}', tag in st, st.strip())
    ok('piece check reported the edited file', 'md5 differs from MD5SUMS' in json.dumps(pcs), (pcs.get('failures') or [])[:2])
    ok('nothing pulled, trained or evaluated after the STOP', not dl and not tr and not ev, (len(dl), len(tr), len(ev)))
    done()
ok('piece set ev20b1: MD5SUMS / FROZEN.md md5 = the pinned ones, 41 pieces', pcs.get('ok') and pcs.get('md5sums_md5') == e20b1.PIECES['md5sums']
   and pcs.get('frozen_md5') == e20b1.PIECES['frozen'] and pcs.get('pieces') == 41, (pcs.get('md5sums_md5'), pcs.get('failures')))
inp = js(f'{G}/inputs.json')
ok('inputs: the packed P (fingerprint), stage, packed asset copy (pitcher 6772f954 9 collisions, cup 31cd001d, glbs) and checkpoint sha256',
   inp.get('ok') and inp.get('traj_fingerprint') == e20b1.REF_FP and {n: v.get('md5') for n, v in inp.get('assets', {}).items()} == e20b1.URDF_PACKED
   and inp.get('packed_ck_sha256') == e20b1.PACKED_SHA, inp.get('failures'))
ast = js(f'{G}/assets.json'); u = ast.get('urdfs') or {}
ok('carve (REAL placement_carve.py assets): only the pitcher URDF changed (-> 77b395a5, 41 collisions), 41 col_NN byte copies added, '
   'visual + inertial unchanged, blue cup untouched',
   ast.get('ok') and ast.get('changed') == ['urdf/water_pitcher_rigid.urdf'] and ast.get('added') == 41 and not ast.get('removed')
   and {n: v.get('md5') for n, v in u.items()} == e20b1.URDF_B1 and u['water_pitcher']['collisions'] == 41 and u['blue_cup']['collisions'] == 1
   and all(v['inertial_equal'] and v['visual_equal'] for v in u.values()), (ast.get('changed'), ast.get('failures')))
ok('the carve ran on refs/sf/ep20/assets (the mesh lane\'s command)', 'carved' in rd(f'{G}/carve.txt') and
   re.search(r'placement_carve\.py assets \$A \$PIECES_DIR ', rd(f'{C}/v2d-track3/ops/jobs/ev20_b1.sh')) is not None)
ok('on the box: refs/sf/ep20/assets is the b1 copy; the pristine packed copy is kept in e20b1_in',
   md5(f'{C}/refs/sf/ep20/assets/urdf/water_pitcher_rigid.urdf') == e20b1.URDF_B1['water_pitcher']
   and md5(f'{C}/e20b1_in/sf_packed_assets/urdf/water_pitcher_rigid.urdf') == e20b1.URDF_PACKED['water_pitcher'])
ok('the push holds the b1 asset copy under this run id and not the pristine copy; the packed run\'s store files are unchanged',
   md5(f'{ST}/refs/sf/ep20/assets/urdf/water_pitcher_rigid.urdf') == e20b1.URDF_B1['water_pitcher'] and not glob.glob(f'{ST}/e20b1_in*')
   and md5(f'{MR}/store/{SRC}/refs/sf/ep20/assets/urdf/water_pitcher_rigid.urdf') == e20b1.URDF_PACKED['water_pitcher'])
arms = js(f'{G}/arms.json')
ok('arms: seed copies 42 / 43 are byte copies of P; P names the b1 URDFs at 0.3 kg', arms.get('ok') and sorted(arms.get('seeds', {})) == ['42', '43']
   and all(v['md5'] == arms['source_md5'] for v in arms['seeds'].values()) and arms.get('traj_fingerprint') == e20b1.REF_FP
   and {n: v.get('md5') for n, v in arms.get('urdfs', {}).items()} == e20b1.URDF_B1, arms.get('failures'))
ok('no_oracle accepted the piece set and every input', all('none oracle-derived' in rd(f'{G}/{f}')
                                                           for f in ('no_oracle_pieces.txt', 'no_oracle_inputs.txt')))
ok('two trainings: seeds 42 and 43, 70,004,736 steps, runs/e20b1s<seed>_glock/ep20-s<seed>, on the seed copies',
   sorted((x['seed'], x['steps']) for x in tr) == [('42', 70004736), ('43', 70004736)]
   and all(x['run'].endswith(f'/runs/e20b1s{x["seed"]}_glock/ep20-s{x["seed"]}') and f'/refs/e20b1s{x["seed"]}_glockt/ep20' in x['task'] for x in tr),
   [(x['run'][-30:], x['seed']) for x in tr])
ok('the trainings loaded the b1 URDFs (md5) at 0.3 kg, from refs/sf/ep20/assets', tr and all(
   {n: v['md5'] for n, v in x['loaded'].items()} == e20b1.URDF_B1 and all(v['mass'] == 0.3 and '/refs/sf/ep20/assets/urdf/' in v['urdf'] for v in x['loaded'].values())
   for x in tr))
ok('stock contact limits: no sim.* override, saved sim / env.sim 512 / 256',
   tr and all(not x.get('sim_cli') and x.get('saved_sim') == [512, 256, 512, 256] and not [a for a in x.get('argv', []) if a.startswith('sim.')] for x in tr))
ok('every CLI training key equals the REAL packed eval-20 config (no mismatch; >= 10 keys compared)',
   tr and all(not x['cli_vs_packed_mismatch'] and len(x['cli_keys_compared']) >= 10 for x in tr),
   [(x['cli_vs_packed_mismatch'], len(x['cli_keys_compared'])) for x in tr])
real = re.findall(r'TRAIN_ARGS \[([^\]]*)\]', open(f'{W}/cpu/out/evb1420_job_log_lines.txt').read())
mine = re.findall(r'patched FlashCHORD \(FDR rewards\)[^\n]*TRAIN_ARGS \[([^\]]*)\]', job)
ok('TRAIN_ARGS = the packed run evb1420\'s REAL job-log line, byte for byte', bool(real) and bool(mine) and set(mine) == set(real), (set(mine), set(real)))
keys = [sorted(a.split('=', 1)[0] for a in x.get('argv', []) if '=' in a) for x in tr]
ok('the training command has exactly the glock_public.sh template keys + TRAIN_ARGS keys', keys and all(k == keys[0] for k in keys)
   and set(keys[0]) == {'experiment', 'embodiment', 'task.parquet', 'task.motion_speed', 'reset.seed', 'logging.mode', 'output_dir',
                        'training.total_environment_steps', 'curriculum', 'objective.force_closure.enabled', 'objective.force_closure.weight',
                        'objective.contact_wrench_support.weight', 'objective.unintended_contact.weight'}, keys[:1])
ok('glock_public ran with REUSE_REF / REQUIRE_REUSE, SF 0, and never rebuilt a reference', job.count('REUSE_REF: training on this box\'s finished reference') == 2
   and not jl(f'{MR}/ref_audit.log') and job.count(', SF 0, REPLAN 1, EVOLVE 0') == 2, len(jl(f'{MR}/ref_audit.log')))
ok('no make_assets --pieces anywhere (PIECES unset: no "collision pieces from" line)', 'collision pieces from' not in job)
ov = js(f'{G}/overflow.json').get('groups', {})
if OVF is not None:
    ok(f'overflow: each training log has {OVF} nefc lines (the injected count), the summary reads the same',
       all(ov.get(f'train_s{s}', {}).get('counts', {}).get('nefc') == OVF for s in ('42', '43'))
       and all(summ.get('overflow', {}).get('per_seed', {}).get(s, {}).get('dropped') == OVF for s in ('42', '43')),
       {s: ov.get(f'train_s{s}', {}).get('counts', {}).get('nefc') for s in ('42', '43')})
    ok('overflow label ' + ('"pieces not clean in training"' if OVF > 1000 else 'absent'),
       ('pieces not clean in training' in summ.get('labels_attached', [])) == (OVF > 1000), summ.get('labels_attached'))
ok('the b1 zero-action rest check ran and is reported (not gating)', os.path.exists(f'{G}/rest_check_b1.json') and 'rest check of P on the b1 copy' in job
   and 'b1' in (summ.get('rest_check') or {}))
cells = js(f'{G}/cells.json').get('seeds', {})
if tag == 'CELLS':
    ok('cells: seed 43 INVALID (the extra config key), seed 42 VERIFIED', cells.get('43', {}).get('status') == 'INVALID'
       and any('mock_extra_setting' in f for f in cells.get('43', {}).get('failures', [])) and cells.get('42', {}).get('status') == 'VERIFIED',
       {s: (c['status'], c['failures'][:1]) for s, c in cells.items()})
    ok('no official draw (INVALID cell: no choice)', not ev, len(ev))
    ok('choice status INVALID', js(f'{G}/choice.json').get('status') == 'INVALID')
else:
    stock = {k: v for k, v in zip(e10cs.SIM_KEYS, (512, 256, 512, 256))}
    ok('cells: both VERIFIED; config diff vs the packed checkpoint within the allowed keys; stock limits; P md5; b1 URDFs; stage',
       len(cells) == 2 and all(c['status'] == 'VERIFIED' and set(c['config_diff_vs_packed']) <= e10cs.ALLOWED and c['sim_limits'] == stock
                               and list(c['support_stage'].values()) == [e20b1.STAGE_MD5] for c in cells.values()),
       {s: (c['status'], c.get('config_diff_vs_packed'), c['failures'][:1]) for s, c in cells.items()})
    ch = js(f'{G}/choice.json'); gt = js(f'{G}/gate.json')
    st = {s: dict(n=c['n'], mean=c['mean'], sd=c['sd']) for s, c in cells.items()}
    ok('choice = pack 9b rule (e10v rule 2) on the cells', ch.get('chosen') == e10cs.rule2_e10v(st, ['42', '43']) and ch.get('status') == 'CHOSEN', ch.get('chosen'))
    gate_want = tag != 'GATE'
    ok(f'training-box gate {"met" if gate_want else "NOT met"} (bar {e20b1.GATE_P})', gt.get('met') is gate_want and gt.get('bar') == 0.8933,
       {s: (r['mean'], r['above']) for s, r in gt.get('seeds', {}).items()})
    if gate_want:
        ok('10 official calls of the chosen checkpoint on the pristine worktree, at stock 512', len(ev) == 10
           and all(x['cwd'].endswith('v2d_clean/robotic_grounding/flash_chord') and x['stored_njmax'] == 512 and x['ck'] == ch['checkpoint'] for x in ev), len(ev))
        ok('no_oracle accepted the chosen checkpoint (packable)', 'none oracle-derived' in rd(f'{G}/no_oracle_choice.txt'))
    else:
        ok('no official draw (gate not met)', not ev and not glob.glob(f'{G}/conf/r*'), len(ev))
        ok('label reason: training-box gate not met', any('training-box gate not met' in w for w in summ.get('why', [])), summ.get('why'))
    cnt = {k: v.get('n_scored') for k, v in summ.get('counts', {}).items()}
    ok('scored: conf ' + ('10' if gate_want else '0') + ', packed 10, old 1, train42 10, train43 10',
       cnt == dict(conf=10 if gate_want else 0, old=1, packed=10, train42=10, train43=10), cnt)
    pk = (summ.get('sides') or {}).get('packed') or {}
    ok('packed side = the REAL H5p7 draws vs P: mean 0.8933 (raw 0.89335), 0 fails, median RPE 1.67 cm (as the CPU score of the same files)',
       abs(((pk.get('sim_vs_ref') or {}).get('mean') or 0) - 0.89335) <= 1e-4 and pk.get('fails') == 0 and abs(((pk.get('RPE') or {}).get('median') or 0) - 1.67) < 0.01,
       ((pk.get('sim_vs_ref') or {}).get('mean'), pk.get('fails'), (pk.get('RPE') or {}).get('median')))
    vr = js(f'{G}/verify.json')
    ok('verify ok, every own-reference check ok', vr.get('ok') and all(vr.get('own_ref_checks', {}).values()) and len(vr.get('own_ref_checks', {})) >= 31,
       (vr.get('failures'), len(vr.get('own_ref_checks', {}))))
    inc = summ.get('pack10_inclusion', {})
    if want == 'SWAP-ELIGIBLE':
        ok('swap rule: a / b / c / s all hold', all(v['holds'] for v in summ.get('clauses', {}).values()) and len(summ.get('clauses', {})) == 4, summ.get('clauses'))
        ok('pack-10 inclusion: gain >= 0.02 vs P -> INCLUDE', inc.get('include_in_pack10') is True and inc.get('gain') >= 0.02, inc)
    else:
        ok('pack-10 inclusion: not included', inc.get('include_in_pack10') is False, inc.get('reading'))
pc = summ.get('pieces', {})
ok('summary records the piece set, its MD5SUMS md5 and the 41-line manifest; the URDFs used', pc.get('set') == 'ev20b1'
   and pc.get('md5sums_md5') == e20b1.PIECES['md5sums'] and len(pc.get('manifest') or []) == 41
   and (summ.get('urdfs') or {}).get('water_pitcher', {}).get('md5') == e20b1.URDF_B1['water_pitcher'], (pc.get('set'), len(pc.get('manifest') or [])))
done()
