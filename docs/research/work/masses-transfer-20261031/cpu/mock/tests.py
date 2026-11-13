"""Negative and unit tests for the masses transfer check (CPU). usage: tests.py MR OUT.json   (MR = a finished mock)
  T1 mass_verify.py FAILS when an arm loads the wrong mass (mass1's blue cup URDF set back to 0.3 kg; restored after);
  T2 mass_verify.py FAILS when an arm's reference folder holds a second .parquet (FlashCHORD refuses it; restored after);
  T3 mass_verify.py FAILS when an arm's reference is not the source reference (one wrist sample changed; restored after);
  T4 mass_verdict.verdict(): ADOPT / NOT ADOPTED (gain short on one episode) / NOT ADOPTED (one seed drops 0.06 while the
     seed mean passes) / boundary (+0.03 exactly, -0.05 exactly: passes) / INCOMPLETE (7 rollouts) / INVALID;
  T5 mass_arm.set_mass() on make_assets.py's placeholder URDFs gives make_assets.py --physics props_masses_only.json's
     masses, COMs and inertias (library_v3, every object): the arm copy is what MA_ARGS would have built;
  T6 mass_arm.py refuses a source reference whose URDF is not the 0.3 kg placeholder;
  T7 mass_verify.py FAILS when the two arms' saved training configs differ in a setting (a reward weight) (restored).
Review fixes of 2026-10-31 (external review of 4e019af + our F1; "before_fix" = the same fixture on the 4e019af tools):
  T8  one missing cell (no chosen checkpoint) -> verify OK with the cell in "missing" -> verdict INCOMPLETE (was INVALID);
  T9  a whole dropped episode (no ep2 results, no ep2 manifest, as mass_check.sh then passes) -> INCOMPLETE;
  T10 a missing cell AND a wrong mass in another cell -> INVALID (the missing cell is listed beside it);
  T11 a NaN value and an all-NaN column in the reference -> mass_arm.py builds the arm copies (was: refused, Table.equals);
  T12 saved-config keys that embed the arm name (a run dir, a task path, a list of asset dirs) -> VERIFIED (was INVALID);
      the same key differing by more than the arm name -> INVALID;
  T13 an injected eval timeout (best rollout rc 124, curve repeat rc 137) -> counted in verify.json eval_timeouts and
      printed right after the verdict label, per cell and per arm; without timeouts nothing is flagged;
  T14 glock_public.sh REQUIRE_REUSE=1 exits (rc 1, nothing trained or rebuilt) when an arm copy misses rest_check.json,
      and when REUSE_REF is not 1.
"""
import glob, hashlib, json, math, os, shutil, struct, subprocess, sys, tempfile
import pyarrow as pa, pyarrow.parquet as pq
MR, OUT = sys.argv[1], sys.argv[2]
C = f'{MR}/content'; TOOLS = f'{C}/v2d-track3/tools'; PY = sys.executable
sys.path.insert(0, TOOLS)
import mass_arm, mass_verdict                                   # noqa: E402
PROPS = f'{C}/v2d-track3/docs/research/physics-2026-10-30/props_masses_only.json'
MANS = f'{C}/results/mass_check/arms_ep2.json {C}/results/mass_check/arms_ep12.json'
REPO = subprocess.run(['/usr/bin/git', '-C', os.path.dirname(os.path.abspath(__file__)), 'rev-parse', '--show-toplevel'],
                      capture_output=True, text=True).stdout.strip()
OLD = '4e019af'                                                 # the commit the external review read (before the fixes)
OLDT = tempfile.mkdtemp()                                       # its mass tools, /content mapped as setup.sh maps it
for n in ('mass_arm.py', 'mass_verify.py', 'mass_verdict.py'):
    r = subprocess.run(['/usr/bin/git', '-C', REPO, 'show', f'{OLD}:tools/{n}'], capture_output=True, text=True)
    open(f'{OLDT}/{n}', 'w').write(r.stdout.replace('/content', f'{C}'))
res = {}


def verify2(tools=TOOLS, man=MANS, out=None):
    out = out or f'{MR}/tests_verify.json'
    r = subprocess.run([PY, '-I', f'{tools}/mass_verify.py', '--content', C, '--eps', '2 12', '--seeds', '42 43', '--arms',
                        f'mass0:none mass1:{PROPS}', '--steps', '70004736', '--manifests', man, '--out', out],
                       capture_output=True, text=True)
    return r.returncode, json.load(open(out)), r.stdout.strip()


def verify():
    rc, V, _ = verify2()
    return rc, V['failures']


def verdict_cli(tools=TOOLS, man=MANS, vjson=None):
    """verify then mass_verdict.py as mass_check.sh runs them -> (verify rc, verify.json, summary.json, verdict line)."""
    vjson = vjson or f'{MR}/tests_verify.json'; rc, V, _ = verify2(tools, man, vjson); out = f'{MR}/tests_summary.json'
    r = subprocess.run([PY, '-I', f'{tools}/mass_verdict.py', '--content', C, '--eps', '2 12', '--seeds', '42 43', '--control',
                        'mass0', '--treatment', 'mass1', '--verify', vjson, '--manifests', man, '--out', out],
                       capture_output=True, text=True)
    return rc, V, json.load(open(out)), r.stdout.strip()


def short(line):
    return line.replace(MR, 'MR')[:400]


rc, f = verify(); res['T0_baseline_verified'] = dict(ok=rc == 0 and not f, detail=f[:2])
u = glob.glob(f'{C}/refs/mass1_sf/ep12/assets/urdf/blue_cup_rigid.urdf')[0]; keep = open(u).read()
open(u, 'w').write(mass_arm.set_mass(keep, 0.3, 'tamper test'))
rc, f = verify(); open(u, 'w').write(keep)
res['T1_wrong_mass_detected'] = dict(ok=rc != 0 and any('blue_cup loads 0.3' in x for x in f), detail=[x.replace(MR, 'MR') for x in f[:3]])
d = os.path.dirname(glob.glob(f'{C}/refs/mass1s43_glockt/ep2/processed/*/*/ref_gl_ilc.parquet')[0]); extra = f'{d}/extra.parquet'
shutil.copy(f'{d}/ref_gl_ilc.parquet', extra); rc, f = verify(); os.remove(extra)
res['T2_second_parquet_detected'] = dict(ok=rc != 0 and any('2 .parquet files' in x for x in f), detail=[x.replace(MR, 'MR') for x in f[:2]])
p = glob.glob(f'{C}/refs/mass0s42_glockt/ep12/processed/*/*/ref_gl_ilc.parquet')[0]; tmp = p + '.keep'; shutil.copy(p, tmp)
t = pq.read_table(p); w = t.column("robot_left_wrist_position")[0].as_py(); w[0] = [w[0][0] + 0.001] + list(w[0][1:]) if isinstance(w[0], list) else w[0] + 0.001
t = t.set_column(t.column_names.index('robot_left_wrist_position'), 'robot_left_wrist_position',
                 pa.array([w], type=t.schema.field('robot_left_wrist_position').type)); pq.write_table(t, p)
rc, f = verify(); shutil.move(tmp, p)
res['T3_other_reference_detected'] = dict(ok=rc != 0 and any('not the same reference' in x for x in f), detail=[x.replace(MR, 'MR') for x in f[:2]])
import struct                                                                             # noqa: E402
ck = f'{C}/results/mass1s42_glock_public/ep2/best/policy.safetensors'; keep = ck + '.keep'; shutil.copy(ck, keep)
with open(ck, 'rb') as fh:
    nh = struct.unpack('<Q', fh.read(8))[0]; hd = json.loads(fh.read(nh))
cf = json.loads(hd['__metadata__']['user.resolved_config_json']); cf['objective']['force_closure']['weight'] = '7'
hd['__metadata__']['user.resolved_config_json'] = json.dumps(cf); b = json.dumps(hd).encode(); b += b' ' * (-len(b) % 8)
open(ck, 'wb').write(struct.pack('<Q', len(b)) + b); rc, f = verify(); shutil.move(keep, ck)
res['T7_other_training_setting_detected'] = dict(ok=rc != 0 and any('objective.force_closure.weight' in x for x in f), detail=f[:2])

# ---- review fixes (2026-10-31) ----
rc, V, S, line = verdict_cli()                                  # T13a: the untouched mock: no timeout, none flagged
res['T13a_no_timeout_nothing_flagged'] = dict(
    ok=rc == 0 and V['eval_timeouts'] == {} and 'EVAL TIMEOUTS' not in line and 'NOT RECORDED' not in line
    and all(c['eval_timeouts']['best_rc'] == {'0': 10} and c['eval_timeouts']['curve_rc'] == {'0': 21} for c in V['cells'].values()),
    detail=dict(verdict=short(line), cell=V['cells']['ep2/mass1/s42']['eval_timeouts']))
B = f'{C}/results/mass1s43_glock_public/ep12/best'; shutil.move(B, B + '.t')     # T8: one cell lost
rc, V, S, line = verdict_cli(); orc, oV, oS, oline = verdict_cli(OLDT, vjson=f'{MR}/tests_verify_old.json'); shutil.move(B + '.t', B)
res['T8_missing_cell_incomplete'] = dict(
    ok=rc == 0 and V['ok'] and V['missing'] == ['ep12/mass1/s43'] and not V['failures'] and S['verdict'] == 'INCOMPLETE',
    detail=dict(verify_rc=rc, missing=V['missing'], verdict=short(line),
                before_fix=dict(verify_rc=orc, failures=[short(x) for x in oV['failures'][:2]], verdict=oS['verdict'])))
moved = [f'{C}/results/{a}s{s}_glock_public/ep2' for a in ('mass0', 'mass1') for s in ('42', '43')]   # T9: ep2 dropped
for d in moved:
    shutil.move(d, d + '.t')
m12 = f'{C}/results/mass_check/arms_ep12.json'
rc, V, S, line = verdict_cli(man=m12); orc, oV, oS, oline = verdict_cli(OLDT, man=m12, vjson=f'{MR}/tests_verify_old.json')
for d in moved:
    shutil.move(d + '.t', d)
res['T9_dropped_episode_incomplete'] = dict(
    ok=rc == 0 and V['ok'] and sorted(V['missing']) == sorted(f'ep2/{a}/s{s}' for a in ('mass0', 'mass1') for s in ('42', '43'))
    and S['verdict'] == 'INCOMPLETE',
    detail=dict(verify_rc=rc, missing=V['missing'], verdict=short(line), before_fix=dict(verify_rc=orc, verdict=oS['verdict'])))
B = f'{C}/results/mass0s42_glock_public/ep2/best'; shutil.move(B, B + '.t')      # T10: lost cell + wrong mass elsewhere
u = glob.glob(f'{C}/refs/mass1_sf/ep12/assets/urdf/blue_cup_rigid.urdf')[0]; keep = open(u).read()
open(u, 'w').write(mass_arm.set_mass(keep, 0.3, 'tamper test'))
rc, V, S, line = verdict_cli(); open(u, 'w').write(keep); shutil.move(B + '.t', B)
res['T10_missing_plus_wrong_mass_invalid'] = dict(
    ok=rc != 0 and not V['ok'] and V['missing'] == ['ep2/mass0/s42'] and any('blue_cup loads 0.3' in x for x in V['failures'])
    and not any('ep2/s42' in x for x in V['failures']) and S['verdict'] == 'INVALID' and any('also missing' in x for x in S['reasons']),
    detail=dict(verify_rc=rc, missing=V['missing'], failures=[short(x) for x in V['failures'][:2]], verdict=short(line)))


def ck_rewrite(ck, cfg):
    """the checkpoint with its saved config (safetensors header metadata) replaced; returns its new sha256."""
    with open(ck, 'rb') as fh:
        nh = struct.unpack('<Q', fh.read(8))[0]; hd = json.loads(fh.read(nh)); rest = fh.read()
    hd['__metadata__']['user.resolved_config_json'] = json.dumps(cfg); b = json.dumps(hd).encode(); b += b' ' * (-len(b) % 8)
    open(ck, 'wb').write(struct.pack('<Q', len(b)) + b + rest)
    return hashlib.sha256(open(ck, 'rb').read()).hexdigest()


def with_arm_keys(extra_suffix=''):
    """T12 fixture: both arms of ep2/s42 get saved-config keys that embed the arm's name, written consistently (the
    summary's checkpoint, best/policy.safetensors and the rollouts' checkpoint_sha256); arm mass1's run dir gets
    extra_suffix. Returns a restore function."""
    saved = []
    for a in ('mass0', 'mass1'):
        O = f'{C}/results/{a}s42_glock_public/ep2'; ckn = json.load(open(f'{O}/best/summary.json'))['checkpoint']
        bk = tempfile.mkdtemp(); shutil.copytree(f'{O}/best', f'{bk}/best'); shutil.copy(ckn, f'{bk}/ckn'); saved.append((O, ckn, bk))
        cfg = json.loads(mass_arm_ck_meta(ckn)['user.resolved_config_json'])
        cfg.setdefault('logging', {})['run_dir'] = cfg['output_dir'] + '/logs' + (extra_suffix if a == 'mass1' else '')
        cfg.setdefault('env', {})['task'] = dict(parquet=cfg['task']['parquet'])
        cfg.setdefault('scene', {})['asset_dirs'] = [f'{C}/refs/{a}_sf/ep2/assets', f'{C}/assets']
        sha = ck_rewrite(ckn, cfg); shutil.copy(ckn, f'{O}/best/policy.safetensors')
        for f in glob.glob(f'{O}/best/r*/episode_*.json'):
            d = json.load(open(f)); d['checkpoint_sha256'] = sha; json.dump(d, open(f, 'w'))

    def restore():
        for O, ckn, bk in saved:
            shutil.rmtree(f'{O}/best'); shutil.copytree(f'{bk}/best', f'{O}/best'); shutil.copy(f'{bk}/ckn', ckn); shutil.rmtree(bk)
    return restore


def mass_arm_ck_meta(ck):
    with open(ck, 'rb') as fh:
        nh = struct.unpack('<Q', fh.read(8))[0]; return json.loads(fh.read(nh))['__metadata__']


restore = with_arm_keys()                                                         # T12
rc, V, so = verify2(); orc, oV, oso = verify2(OLDT, out=f'{MR}/tests_verify_old.json'); restore()
eq = V['pair_config_equal_after_arm_name'].get('ep2/s42', {}).get('ep2/mass1/s42', [])
restore = with_arm_keys('2'); rc2, V2, _ = verify2(); restore()
res['T12_arm_named_config_keys_verified'] = dict(
    ok=rc == 0 and V['ok'] and {'logging.run_dir', 'env.task.parquet', 'scene.asset_dirs'} <= set(eq)
    and orc != 0 and rc2 != 0 and any("'logging.run_dir'" in x for x in V2['failures']) and not any('env.task' in x for x in V2['failures']),
    detail=dict(verify_rc=rc, equal_after_arm_name=eq, before_fix=dict(verify_rc=orc, failures=[short(x) for x in oV['failures'][:2]]),
                differs_by_more_than_arm=dict(verify_rc=rc2, failures=[short(x) for x in V2['failures'][:2]])))
O = f'{C}/results/mass1s42_glock_public/ep2'; bk = tempfile.mkdtemp()           # T13: injected eval timeouts
shutil.copytree(f'{O}/best', f'{bk}/best'); shutil.copytree(f'{O}/curve', f'{bk}/curve')
open(f'{O}/best/r3/eval_rc.txt', 'w').write('124\n')
for f in ('qa_policy.json', 'score_registered_ep2.json'):
    os.remove(f'{O}/best/r3/{f}')
sm = json.load(open(f'{O}/best/summary.json'))                                    # as evalrep's summary then has it
sm['rollouts'] = [x if x['rollout'] != 'r3' else dict(rollout='r3', error='[Errno 2] No such file or directory: qa_policy.json')
                  for x in sm['rollouts']]; sm['n'] -= 1; json.dump(sm, open(f'{O}/best/summary.json', 'w'))
open(f'{O}/curve/policy_9998336/r2/eval_rc.txt', 'w').write('137\n')
rc, V, S, line = verdict_cli()
for d in ('best', 'curve'):
    shutil.rmtree(f'{O}/{d}'); shutil.copytree(f'{bk}/{d}', f'{O}/{d}')
shutil.rmtree(bk)
t = V['eval_timeouts'].get('ep2/mass1/s42', {})
res['T13_injected_eval_timeout_reported'] = dict(
    ok=rc == 0 and list(V['eval_timeouts']) == ['ep2/mass1/s42'] and t.get('best') == 1 and t.get('curve') == 1
    and t.get('best_rc') == {'0': 9, '124': 1} and t.get('curve_rc') == {'0': 20, '137': 1}
    and line.startswith(S['verdict'] + ' [EVAL TIMEOUTS in 1 cell(s): ep2/mass1/s42 best 1/10 curve 1/21; per arm best/curve mass0 0/0, mass1 1/1]')
    and S['cells']['ep2/mass1/s42']['n_rollouts'] == 10 and S['cells']['ep2/mass1/s42']['auc']['n'] == 9
    and list(S['eval_timeouts']['cells_cut']) == ['ep2/mass1/s42'],
    detail=dict(verify_eval_timeouts=V['eval_timeouts'], verdict=short(line), per_arm=S['eval_timeouts']['per_arm']))
# T14: glock_public.sh REQUIRE_REUSE=1 refuses an arm copy that is not a finished reference (nothing rebuilt or trained)
rcf = f'{C}/results/mass1s42_glock_public/ep2/rest_check.json'; shutil.move(rcf, rcf + '.t')
n_audit = {k: (sum(1 for _ in open(f'{MR}/{k}.log')) if os.path.exists(f'{MR}/{k}.log') else 0) for k in ('train_audit', 'ref_audit', 'eval_audit')}
runs_before = sorted(os.listdir(f'{C}/runs'))


def gp(env, J):
    return subprocess.run(['bash', '-c', f'. {MR}/env.sh; cd {C}/v2d-track3 && {env} J={J} SEED=42 '
                           f'PAIRS="2:local:mck:mass0s42 2:local:mck:mass1s42" bash ops/jobs/glock_public.sh'],
                          capture_output=True, text=True, env={k: v for k, v in os.environ.items() if k in ('HOME', 'PATH', 'LANG')})


r1 = gp('REUSE_REF=1 REQUIRE_REUSE=1', f'{MR}/t14a.log'); r2 = gp('REUSE_REF=0 REQUIRE_REUSE=1', f'{MR}/t14b.log')
shutil.move(rcf + '.t', rcf)
n_after = {k: (sum(1 for _ in open(f'{MR}/{k}.log')) if os.path.exists(f'{MR}/{k}.log') else 0) for k in n_audit}
l1, l2 = open(f'{MR}/t14a.log').read(), open(f'{MR}/t14b.log').read()
res['T14_require_reuse_exits'] = dict(
    ok=r1.returncode == 1 and 'REQUIRE_REUSE: pair 2:local:mck:mass1s42 has no finished reference' in l1
    and r2.returncode == 1 and 'REQUIRE_REUSE=1 needs REUSE_REF=1' in l2 and n_after == n_audit and sorted(os.listdir(f'{C}/runs')) == runs_before
    and 'make_assets' not in l1 + l2,
    detail=dict(rc=(r1.returncode, r2.returncode), log=[short(x[x.find('glock_public: REQ'):]) for x in (l1, l2)], audits=n_after))
rc, f = verify(); res['T0_restored_verified'] = dict(ok=rc == 0 and not f, detail=f[:2])


def cells(vals, n=10):  # vals[(ep, arm, seed)] = mean -> rows as mass_verdict builds them
    return {k: dict(auc=dict(n=n, mean=v, sd=0.02, min=v - 0.03, max=v + 0.03)) for k, v in vals.items()}


def V(d, n=10, ok=True):
    return mass_verdict.verdict(cells(d, n), [2, 12], ['42', '43'], 'mass0', 'mass1', ok, 8)[0]


base = {(2, 'mass0', '42'): 0.70, (2, 'mass0', '43'): 0.72, (12, 'mass0', '42'): 0.88, (12, 'mass0', '43'): 0.86}
adopt = {**base, **{(2, 'mass1', '42'): 0.75, (2, 'mass1', '43'): 0.76, (12, 'mass1', '42'): 0.92, (12, 'mass1', '43'): 0.90}}
short = {**adopt, **{(12, 'mass1', '42'): 0.90, (12, 'mass1', '43'): 0.88}}                 # ep12 +0.02
drop = {**adopt, **{(2, 'mass1', '42'): 0.64, (2, 'mass1', '43'): 0.88}}                    # ep2 mean +0.05, seed 42 -0.06
edge = {(2, 'mass0', '42'): 0.5, (2, 'mass0', '43'): 0.5, (2, 'mass1', '42'): 0.53, (2, 'mass1', '43'): 0.53,   # ep2 +0.03
        (12, 'mass0', '42'): 0.5, (12, 'mass0', '43'): 0.5, (12, 'mass1', '42'): 0.45, (12, 'mass1', '43'): 0.67}  # seed 42 -0.05
got = dict(adopt=V(adopt), short=V(short), drop=V(drop), edge=V(edge), incomplete=V(adopt, n=7), invalid=V(adopt, ok=False))
want = dict(adopt='ADOPT', short='NOT ADOPTED', drop='NOT ADOPTED', edge='ADOPT', incomplete='INCOMPLETE', invalid='INVALID')
res['T4_verdict_rule'] = dict(ok=got == want, detail=dict(got=got, want=want))
# T5: arm copy == make_assets --physics
tmpd = tempfile.mkdtemp(); lib = f'{C}/v2d-track3/meshes/library_v3'; ma = f'{C}/v2d-track3/pipeline/make_assets.py'
subprocess.run([PY, '-I', ma, lib, f'{tmpd}/a0'], check=True, capture_output=True)
subprocess.run([PY, '-I', ma, lib, f'{tmpd}/a1', '--physics', PROPS], check=True, capture_output=True)
P = json.load(open(PROPS)); worst = {}
for f in sorted(glob.glob(f'{tmpd}/a0/urdf/*.urdf')):
    n = os.path.basename(f)[:-len('_rigid.urdf')]
    mine = mass_arm.read_inertial(mass_arm.set_mass(open(f).read(), P[n]['physics']['mass_kg'], 'test'))
    ref = mass_arm.read_inertial(open(f'{tmpd}/a1/urdf/{n}_rigid.urdf').read())
    worst[n] = dict(mass=(mine[0], ref[0]), com_equal=mine[1] == ref[1],
                    inertia_rel_err=max(abs(mine[2][k] - ref[2][k]) / max(abs(ref[2][k]), 1e-12) for k in ref[2]))
res['T5_equals_make_assets_physics'] = dict(ok=all(v['mass'][0] == v['mass'][1] and v['com_equal'] and v['inertia_rel_err'] < 1e-6
                                                   for v in worst.values()) and len(worst) == 11, detail=worst)
# T6: refuse a non-placeholder source
src = glob.glob(f'{C}/refs/sf/ep12/assets/urdf/blue_cup_rigid.urdf')[0]; keep = open(src).read()
open(src, 'w').write(mass_arm.set_mass(keep, 0.5, 'tamper test'))
r = subprocess.run([PY, '-I', f'{TOOLS}/mass_arm.py', '--content', C, '--ep', '12', '--base', 'mc', '--arms', 'zz0:none',
                    '--seeds', '99', '--out', f'{tmpd}/m.json'], capture_output=True, text=True)
open(src, 'w').write(keep)
res['T6_non_placeholder_source_refused'] = dict(ok=r.returncode != 0 and 'not the 0.3 kg placeholder' in r.stderr,
                                                detail=r.stderr.strip().replace(MR, 'MR')[-200:])


def nan_content():
    """a content root whose ep12 grasp-lock reference has a NaN in a wrist sample and an all-NaN extra column (the URDFs
    stay the mock's refs/sf/ep12 ones); base reference link and rest_check.json as mass_check.sh leaves them."""
    tc = tempfile.mkdtemp(); src = glob.glob(f'{C}/refs/glockt/ep12/processed/*/*/ref_gl_ilc.parquet')[0]
    hive = os.path.relpath(os.path.dirname(src), f'{C}/refs/glockt/ep12'); os.makedirs(f'{tc}/refs/glockt/ep12/{hive}')
    t = pq.read_table(src); w = t.column('robot_left_wrist_position')[0].as_py()
    w[0] = [float('nan')] + list(w[0][1:]) if isinstance(w[0], list) else float('nan')
    t = t.set_column(t.column_names.index('robot_left_wrist_position'), 'robot_left_wrist_position',
                     pa.array([w], type=t.schema.field('robot_left_wrist_position').type))
    t = t.append_column('mock_nan_column', pa.array([float('nan')], pa.float64()))
    pq.write_table(t, f'{tc}/refs/glockt/ep12/{hive}/ref_gl_ilc.parquet')
    os.makedirs(f'{tc}/refs/perc2mc'); os.symlink(f'{C}/refs/perc2mc/ep12', f'{tc}/refs/perc2mc/ep12')
    os.makedirs(f'{tc}/results/glock_public/ep12'); shutil.copy(f'{C}/results/glock_public/ep12/rest_check.json', f'{tc}/results/glock_public/ep12/')
    return tc, t


def run_arm(tools, tc):
    return subprocess.run([PY, '-I', f'{tools}/mass_arm.py', '--content', tc, '--ep', '12', '--base', 'mc', '--arms',
                           f'mass0:none mass1:{PROPS}', '--seeds', '42', '--out', f'{tc}/m.json'], capture_output=True, text=True)


tc, tn = nan_content(); r = run_arm(TOOLS, tc); man = json.load(open(f'{tc}/m.json')) if r.returncode == 0 else {}   # T11
cp = [pq.read_table(v['seeds']['42']['parquet']) for v in man.get('arms', {}).values()]
tco, _ = nan_content(); ro = run_arm(OLDT, tco)
res['T11_nan_reference_not_dropped'] = dict(
    ok=r.returncode == 0 and len(cp) == 2 and all(math.isnan(x.column('mock_nan_column')[0].as_py()) for x in cp)
    and all(v['seeds']['42']['traj_fingerprint'] == man['traj_fingerprint'] for v in man['arms'].values())
    and not tn.equals(tn) and ro.returncode != 0 and 'differs from the source' in ro.stderr,
    detail=dict(rc=r.returncode, arm_masses={a: {n: o['mass'] for n, o in v['objects'].items()} for a, v in man.get('arms', {}).items()},
                table_equals_itself=tn.equals(tn), before_fix=dict(rc=ro.returncode, stderr=ro.stderr.strip().replace(tco, 'TC')[-160:])))
shutil.rmtree(tc); shutil.rmtree(tco)
shutil.rmtree(tmpd); shutil.rmtree(OLDT)
fails = [k for k, v in res.items() if not v['ok']]
json.dump(dict(ok=not fails, failures=fails, tests=res), open(OUT, 'w'), indent=1, default=str)
print(('ALL TESTS PASS' if not fails else f'FAILED: {fails}') + f' ({len(res)} tests)')
sys.exit(0 if not fails else 1)
