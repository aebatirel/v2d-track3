"""Assertions on one ep11-gate mock run. Usage: check.py MR EXPECT [RUN_ID] [--rerun CELLS]
EXPECT: PASS | FAIL | INCOMPLETE | INVALID (a verdict run, rc 0) or STOP:<substring of the STOPPED reason> (rc 1).
Prints one line per check and a JSON summary; exit 1 if any check fails."""
import glob, json, os, sys
MR, EXPECT = sys.argv[1], sys.argv[2]
RID = sys.argv[3] if len(sys.argv) > 3 and not sys.argv[3].startswith('--') else '20261031-e11g-mocksha'
RERUN = sys.argv[sys.argv.index('--rerun') + 1].split() if '--rerun' in sys.argv else None
C = f'{MR}/content'; G = f'{C}/results/ep11_gate'; ST = f'{MR}/store/runs/{RID}'
GL = '--single_hand 1 --mcp_first 1 --close 10 --palm_clear -0.001 --wrap_where_held 1 --snap 1 --approach_cm 15'.split()
EXP_MD5 = dict(C='b32ab808e560f8a3ebbec3658701066c', T='25801979433d7265bfd5aef2ca868dcc')
res, bad = [], []


def ok(name, cond, info=''):
    res.append(dict(check=name, ok=bool(cond), info=str(info)[:300])); print(('ok   ' if cond else 'FAIL ') + name + (f'  [{info}]' if info else ''))
    if not cond:
        bad.append(name)


def jl(f):
    return [json.loads(x) for x in open(f)] if os.path.exists(f) else []


rc = open(f'{MR}/rc.txt').read().strip()
hf = jl(f'{MR}/hf.log'); dl = [x for x in hf if x['kind'] == 'file']; up = [x for x in hf if x['kind'] == 'upload']
ok('no store listing (single-file downloads only)', not [x for x in hf if x['kind'] == 'LISTING'], len(dl))
ok('every download succeeded', all(x.get('result') == 'ok' for x in dl), [x['path'] for x in dl if x.get('result') != 'ok'])
ok('exactly one store upload (the final push)', len(up) == 1, up)
ok('hands_mp / hand_refine / perc2 never ran', not os.path.exists(f'{MR}/UNEXPECTED.log'))
if EXPECT.startswith('STOP'):
    why = EXPECT.split(':', 1)[1] if ':' in EXPECT else ''
    ok('rc 1 (stopped)', rc == 'rc=1', rc)
    st = open(f'{G}/STOPPED').read() if os.path.exists(f'{G}/STOPPED') else ''
    ok(f'stopped for: {why}', why in st, st.strip())
    ok('no reference built', not glob.glob(f'{C}/refs/perc2e11*'), glob.glob(f'{C}/refs/perc2e11*')[:3])
    ok('no training', not os.path.exists(f'{MR}/train_audit.log'))
    ok('push holds the stop reason', os.path.exists(f'{ST}/results/ep11_gate/STOPPED'))
else:
    ok('rc 0', rc == 'rc=0', rc)
    S = json.load(open(f'{G}/summary.json')); V = json.load(open(f'{G}/verify.json'))
    ok(f'verdict {EXPECT}', S['verdict'] == EXPECT, f"{S['verdict']}: {S['reasons']}")
    ok('verdict pushed to the store', os.path.exists(f'{ST}/results/ep11_gate/summary.json'))
    ok('no depth cache in the push', not glob.glob(f'{ST}/**/depths_*', recursive=True))
    tr = jl(f'{MR}/train_audit.log'); starts = [x for x in tr if 'task' in x]; dones = {x['done']: x['t'] for x in tr if 'done' in x}
    ev = jl(f'{MR}/eval_audit.log'); sc = jl(f'{MR}/score_audit.log')
    cells = [(a, s) for s in ('42', '43') for a in ('e11c', 'e11t')]
    want = [tuple(c.split(':')) for c in RERUN] if RERUN else cells
    want = [(a, s) for a, s in want]
    for a, s in want:
        x = [y for y in starts if f'perc2{a}s{s}_glock/' in y['run']]
        inj = [y for y in tr if y.get('injected_failure') and f'perc2{a}s{s}_glock/' in y['run']]
        if inj:
            ok(f'{a}/s{s}: injected training failure (missing cell)', not x, len(inj)); continue
        ok(f'{a}/s{s}: trained once', len(x) == 1, len(x))
        if not x:
            continue
        x = x[0]
        ok(f'{a}/s{s}: trained on its own copy', f'/refs/perc2{a}s{s}_glockt/ep11' in x['task'], x['task'])
        ok(f'{a}/s{s}: seed, steps', x['seed'] == s and x['steps'] == 70004736, (x['seed'], x['steps']))
        ok(f'{a}/s{s}: 0.3 kg URDFs under /content/assets', all(v['mass'] == 0.3 and '/content/assets/urdf/' in v['urdf'] for v in x['loaded'].values()))
        ok(f'{a}/s{s}: reference holds the blue cup as its arm says', (x['lift_cm'] < 1.0) == (a == 'e11t'), x['lift_cm'])
        e = [y for y in ev if f'perc2{a}s{s}_glock_public/' in y['out']]
        ok(f'{a}/s{s}: 10 best + 21 curve evaluations, each on the checkpoint\'s own task', len(e) == 31 and all(f'perc2{a}s{s}_glockt' in y['task'] for y in e), len(e))
        t_done = dones.get(x['run'])
        s_cell = [y for y in sc if f'perc2{a}s{s}_glock_public/' in y['dir']]
        ok(f'{a}/s{s}: mocap scoring only after its training finished', t_done and all(y['t'] >= t_done for y in s_cell), len(s_cell))
    for s in ('42', '43'):
        xs = [y for y in starts if f's{s}_glock/' in y['run']]
        if len(xs) == 2:
            ok(f's{s}: both arms same args and URDF files', xs[0]['args'] == xs[1]['args'] and
               {n: v['md5'] for n, v in xs[0]['loaded'].items()} == {n: v['md5'] for n, v in xs[1]['loaded'].items()})
    if not RERUN and len(starts) == 4:
        s42 = [y for y in starts if 's42_glock/' in y['run']]; s43 = [y for y in starts if 's43_glock/' in y['run']]
        ok('wave order: both s42 trainings done before any s43 training starts', max(dones[y['run']] for y in s42) <= min(y['t'] for y in s43))
    if not RERUN:
        mk = jl(f'{MR}/mkref_audit.log')
        ok('mkref ran once per arm', len(mk) == 2, len(mk))
        for m in mk:
            t = 'C' if '/tracks/C/' in m['poses'] else 'T' if '/tracks/T/' in m['poses'] else '?'
            ok(f'mkref {t}: rebuilt track (md5), depth cache, stored hands, --wrist_cost 3.0, /content/assets, public',
               m['poses_md5'] == EXP_MD5.get(t) and m['depth'].endswith('hfstore/cache/depth/public/ep11/depths_fs0.5.npy')
               and m['hands_md5'] == 'd9c391deaf73509b6c52e3b743580272' and '--wrist_cost' in m['argv']
               and m['argv'][m['argv'].index('--wrist_cost') + 1] == '3.0' and m['assets'].endswith('/content/assets') and m['split'] == 'public', m['poses_md5'])
        ra = jl(f'{MR}/ref_audit.log')
        cr = [x for x in ra if x['stage'] == 'contact_retarget.py']; gl = [x for x in ra if x['stage'] == 'grasp_lock.py']
        ok('contact retargeting --rest_settle 1, once per arm', len(cr) == 2 and all(x['args'] == ['--rest_settle', '1'] for x in cr), [x['args'] for x in cr])
        ok('grasp lock: GL_ARGS exact, kp 400, only in the reference stages (2 arms x (plan + re-plan))',
           len(gl) == 4 and all(x['args'][:len(GL)] == GL and x['env']['GL_WRIST_KP'] == '400' for x in gl), len(gl))
        pip = open(f'{MR}/pip.log').read()
        ok('pinned venvs', 'e11g_vr install -q numpy==2.5.4 scipy==1.18.1 trimesh==5.2.0 rtree==1.4.1' in pip
           and 'e11g_vp install -q numpy==2.4.6 scipy==1.18.0 trimesh==4.12.2 mujoco==3.8.1' in pip)
        b0 = json.load(open(f'{G}/b0.json'))
        ok('B0 IDENTICAL on both arms', all(b0['arms'][a]['band'] == 'IDENTICAL' for a in ('e11c', 'e11t')), {a: b0['arms'][a]['band'] for a in b0['arms']})
        rf = open(f'{G}/rerun_files.txt').read().split()
        ok('every re-run file is in the push', rf and all(os.path.exists(f'{ST}/{f}') for f in rf), len(rf))
        ok('downloads: 5 inputs + the depth cache', len(dl) == 6, len(dl))
    ok('verify identity: e2s own < other on both arms', all(V['identity'][a].get('e2s_ok') for a in ('e11c', 'e11t')) if V.get('identity') else False,
       {a: V['identity'][a].get('e2s_vs_tracks_cm') for a in ('e11c', 'e11t')} if V.get('identity') else None)
json.dump(dict(mr=os.path.basename(MR), expect=EXPECT, rc=rc, n_checks=len(res), failed=bad), sys.stdout); print()
sys.exit(1 if bad else 0)
