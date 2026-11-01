"""Assertions on one finished Masses v2 mock box (run_mock.sh with a JOBS.txt string). usage: check_v2.py MR STORE "EPS" RUN OUT.json
[--seeds "42 43"] [--expect_missing "ep13/mass1/s43 ..."]. From what the stub FlashCHORD trainer and evaluator loaded
(train_audit.log, eval_audit.log), the hf stub's log and the job's outputs:
  V1 trainings: EPS x mass0 / mass1 x seeds, every one 70,004,736 steps, reset.seed = its seed (minus injected failures);
  V2 per episode every training read ONE reference whose fingerprint is the REAL table's (PREREG) value, and the arm
     parquets differ from the source only in object_urdf_paths;
  V3 the URDFs each training loaded: mass1 = props_masses_only.json, mass0 = 0.3 kg, from the arm's own folder;
  V4 every official evaluation (curve 7 x 3, best 10) loaded its checkpoint's arm, via the checkpoint's saved task.parquet;
  V5 the two arms of an episode and seed have identical arguments and environment; seeds differ only in reset.seed;
  V6 the pulled reference and its asset folder are untouched; mass0 assets byte-identical to it; /content/assets at 0.3 kg;
  V7 store traffic: exactly one upload; 0 listings (--include); the downloads are exactly the table's pull + pull_optional
     files of EPS, once each, from the episode's source run (or the SRC_EP override);
  V8 mass_verify VERIFIED (or the injected missing cells listed as missing); summary rule_version v2, label PARTIAL (or
     INCOMPLETE with exactly the injected missing cells), n 10 per present cell.
"""
import argparse, glob, json, os, re, sys
ap = argparse.ArgumentParser()
ap.add_argument('MR'); ap.add_argument('STORE'); ap.add_argument('EPS'); ap.add_argument('RUN'); ap.add_argument('OUT')
ap.add_argument('--seeds', default='42 43'); ap.add_argument('--expect_missing', default=''); ap.add_argument('--src', default='')
a = ap.parse_args()
MR, C = a.MR, f'{a.MR}/content'; EPS = [int(x) for x in a.EPS.split()]; SEEDS = [int(x) for x in a.seeds.split()]
MISS = set(a.expect_missing.split()); SRC = dict(x.split('=') for x in a.src.split())     # --src "13=<run>"
sys.path.insert(0, f'{C}/v2d-track3/tools')
import pyarrow.parquet as pq                                  # noqa: E402
from mass_arm import traj_fingerprint, md5, read_inertial    # noqa: E402
REAL = json.load(open('/home/user/v2d-track3/docs/research/work/masses-v2-20261031/refs_v2.json'))
res, fails = {}, []


def ok(name, cond, detail=''):
    res[name] = dict(ok=bool(cond), detail=detail)
    if not cond:
        fails.append(f'{name}: {detail}')


props = json.load(open(f'{C}/v2d-track3/docs/research/physics-2026-10-30/props_masses_only.json'))
want = {n: v['physics']['mass_kg'] for n, v in props.items() if isinstance(v, dict) and 'physics' in v}
tr = [json.loads(x) for x in open(f'{MR}/train_audit.log')] if os.path.exists(f'{MR}/train_audit.log') else []
starts = [x for x in tr if 'task' in x]
ev = [json.loads(x) for x in open(f'{MR}/eval_audit.log')] if os.path.exists(f'{MR}/eval_audit.log') else []
fl = [json.loads(x) for x in open(f'{MR}/fail_audit.log')] if os.path.exists(f'{MR}/fail_audit.log') else []


def arm_of(path):
    m = re.search(r'/(mass[01])s(\d+)_glock[^/]*/ep(\d+)', path)
    return m.group(1), int(m.group(2)), int(m.group(3))


cells = {}
for x in starts:
    arm, s, ep = arm_of(x['run']); cells[(ep, arm, s)] = x
exp_cells = sorted((e, arm, s) for e in EPS for arm in ('mass0', 'mass1') for s in SEEDS)
failed = {arm_of(x['run'])[::-1][0:1] + arm_of(x['run'])[0:2] for x in fl}
ok('V1_trainings', sorted(set(cells) | failed) == exp_cells and not set(cells) & failed and len(starts) == len(exp_cells) - len(failed),
   f'{len(starts)} started and finished, injected failures {sorted(failed)}: {sorted(cells)}')
ok('V1_steps_seed', all(x['steps'] == 70004736 and int(x['seed']) == s for (e, arm, s), x in cells.items()), '')
for ep in EPS:
    fps = {x['fingerprint'] for (e, arm, s), x in cells.items() if e == ep}
    src = glob.glob(f'{C}/refs/glockt/ep{ep}/processed/*/*/ref_gl_ilc.parquet')[0]; sfp = traj_fingerprint(pq.read_table(src))
    ok(f'V2_one_reference_ep{ep}', fps == {sfp} == {REAL['episodes'][str(ep)]['glockt_fingerprint']},
       f'training fingerprints {fps}, pulled {sfp}, PREREG table {REAL["episodes"][str(ep)]["glockt_fingerprint"]}')
    t0 = pq.read_table(src)
    for (e, arm, s), x in cells.items():
        if e == ep:
            t = pq.read_table(x['reference_file'])
            ok(f'V2_only_urdf_paths_differ_ep{e}_{arm}_s{s}', t.drop_columns(['object_urdf_paths']).equals(t0.drop_columns(['object_urdf_paths']))
               and t.column('object_urdf_paths')[0].as_py() != t0.column('object_urdf_paths')[0].as_py(), '')
for (e, arm, s), x in cells.items():
    exp = {n: (want[n] if arm == 'mass1' else 0.3) for n in x['loaded']}; got = {n: v['mass'] for n, v in x['loaded'].items()}
    ok(f'V3_train_masses_ep{e}_{arm}_s{s}', got == exp and all(f'/refs/{arm}_sf/ep{e}/' in v['urdf'] for v in x['loaded'].values()), str(got))
bad = []
for x in ev:
    arm, s, ep = arm_of(x['ck']); got = {n: v['mass'] for n, v in x['loaded'].items()}; exp = {n: (want[n] if arm == 'mass1' else 0.3) for n in got}
    if got != exp or not all(f'/refs/{arm}_sf/ep{ep}/' in v['urdf'] for v in x['loaded'].values()) or x['fingerprint'] != cells[(ep, arm, s)]['fingerprint']:
        bad.append(x['ck'].replace(MR, 'MR'))
n_tr = len(cells); best = [x for x in ev if '/best/' in x['out']]
ok('V4_every_evaluation_loads_its_arm', not bad and len(ev) == n_tr * (7 * 3 + 10) and len(best) == 10 * n_tr,
   f'{len(ev)} evaluations ({len(best)} of chosen checkpoints) for {n_tr} finished trainings, {len(bad)} wrong')
for ep in EPS:
    for s in SEEDS:
        if (ep, 'mass0', s) in cells and (ep, 'mass1', s) in cells:
            x0, x1 = cells[(ep, 'mass0', s)], cells[(ep, 'mass1', s)]
            ok(f'V5_identical_settings_ep{ep}_s{s}', x0['args'] == x1['args'] and x0['env'] == x1['env'], str(sorted(set(x0['args']) ^ set(x1['args']))))
if len(SEEDS) == 2:
    ok('V5_seeds_differ_only_in_seed', all(sorted(set(cells[(e, arm, 42)]['args']) ^ set(cells[(e, arm, 43)]['args'])) == ['reset.seed=42', 'reset.seed=43']
                                           for e in EPS for arm in ('mass0', 'mass1') if (e, arm, 42) in cells and (e, arm, 43) in cells), '')
for ep in EPS:
    run = SRC.get(str(ep), REAL['episodes'][str(ep)]['source_run'])
    st = glob.glob(f'{a.STORE}/runs/{run}/refs/glockt/ep{ep}/processed/*/*/ref_gl_ilc.parquet')[0]
    ok(f'V6_pulled_reference_untouched_ep{ep}', md5(st) == md5(glob.glob(f'{C}/refs/glockt/ep{ep}/processed/*/*/ref_gl_ilc.parquet')[0]), '')
    sf = f'{C}/refs/sf/ep{ep}/assets'; sr = f'{a.STORE}/runs/{run}/refs/sf/ep{ep}/assets'
    m = {os.path.relpath(f, sf): md5(f) for f in glob.glob(f'{sf}/**/*', recursive=True) if os.path.isfile(f)}
    m0 = {os.path.relpath(f, f'{C}/refs/mass0_sf/ep{ep}/assets'): md5(f) for f in glob.glob(f'{C}/refs/mass0_sf/ep{ep}/assets/**/*', recursive=True) if os.path.isfile(f)}
    mr = {os.path.relpath(f, sr): md5(f) for f in glob.glob(f'{sr}/**/*', recursive=True) if os.path.isfile(f)}
    ok(f'V6_assets_ep{ep}', m == m0 == mr and len(m) == 4, f'{len(m)} files; mass0 copy identical {m == m0}; store identical {m == mr}')
ok('V6_content_assets_placeholder', all(abs(read_inertial(open(f).read())[0] - 0.3) < 1e-12 for f in glob.glob(f'{C}/assets/urdf/*.urdf')), '')
hf = open(f'{MR}/hf.log').read().splitlines()
dl = [x.split()[3] for x in hf if x.startswith('hf download') and '--include' not in x]
want_dl = sorted(f'runs/{SRC.get(str(e), REAL["episodes"][str(e)]["source_run"])}/{p}' for e in EPS
                 for p in REAL['episodes'][str(e)]['pull'] + REAL['episodes'][str(e)]['pull_optional'])
ok('V7_one_push', sum(1 for x in hf if x.startswith('hf upload')) == 1, f'{sum(1 for x in hf if x.startswith("hf upload"))} uploads')
ok('V7_no_listing', not any(x.startswith('LISTING') or '--include' in x for x in hf), f'{sum(1 for x in hf if x.startswith("LISTING"))} listings')
ok('V7_downloads_exactly_the_table', sorted(dl) == want_dl, f'{len(dl)} single-file downloads, {len(want_dl)} expected; extra {sorted(set(dl) - set(want_dl))[:3]} missing {sorted(set(want_dl) - set(dl))[:3]}')
V = json.load(open(f'{C}/results/mass_check/verify.json')); Sm = json.load(open(f'{C}/results/mass_check/summary.json'))
ok('V8_verify', V['ok'] and set(V.get('missing', [])) == MISS, f"ok {V['ok']}, missing {V.get('missing')}, failures {V['failures'][:2]}")
present = [k for k, c in Sm['cells'].items() if c and c['auc'] and c['auc']['n'] == 10]
ok('V8_summary_v2_partial', Sm.get('rule_version') == 'v2' and Sm['verdict'] == ('INCOMPLETE' if MISS else 'PARTIAL')
   and len(present) == len(exp_cells) - len(MISS), f"verdict {Sm['verdict']}, {len(present)} cells with n 10")
jl = open(f'{C}/job.log').read()
ok('V8_box_result_line', 'mass_check v2 BOX RESULT' in jl and 'mass_check RESULT' not in jl, '')
out = dict(ok=not fails, failures=fails, checks=res, trainings=len(starts), evaluations=len(ev), single_file_downloads=len(dl),
           listings=sum(1 for x in hf if x.startswith('LISTING')), uploads=sum(1 for x in hf if x.startswith('hf upload')),
           box_verdict=Sm['verdict'], note='mock scores are synthetic (stub_v2.py); they test the plumbing, not masses')
json.dump(out, open(a.OUT, 'w'), indent=1)
print(('ALL CHECKS PASS' if not fails else f'{len(fails)} FAILED: ' + ' | '.join(fails)) + f' ({len(res)} checks)')
sys.exit(0 if not fails else 1)
