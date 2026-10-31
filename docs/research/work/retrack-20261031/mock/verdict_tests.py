"""Fixture tests of rtk_verdict.py (2026-10-31), built from Phase 1's REAL P_o side (the 20 stored bundles, the stored
P_o tracks' cameras, R_Po.json) and a synthetic P_o' side (copies with the LIB_EP_DIR records; numbers made up).
usage: verdict_tests.py WORK PO_BUNDLES PO_POSES R_PO V3COPY_VALIDATION REPO      (WORK: a scratch folder, recreated)
Cases and the expected verdict (exit code of rtk_verdict.py):
  F0  every template a byte copy of library_v3, scores = P_o's               -> FAIL (no changed episode: all enter 0)
  F1  15 episodes with a new mesh (E0 scope), dR +0.02 on 13, -0.01 on 2, RPE -0.05 cm on the 13 -> PASS
  F2  F1 + one changed episode dR -0.04                                       -> FAIL (floor)
  F3  F1 with dR +0.015 on 13 -> mean +0.0088                                  -> FAIL (mean)
  F4  F1 with only 11 positive                                                 -> FAIL (count)
  F5  F1 with RPE +0.05 cm on the 13                                           -> FAIL (RPE)
  F6  F1 without ep45's P_o' score                                             -> INCOMPLETE (rerun [45])
  F7  F1 + ep12's P_o' depth frame-0 sha changed                               -> INVALID
  F8  F1 + ep2's P_o' camera moved 2 mm                                        -> INVALID
  F9  F1 + ep11's P_o' template md5 != VALIDATION.json                         -> INVALID
  F10 F1 + an unchanged episode (ep18) dR +0.05                                -> PASS (enters as 0) + control NOTE
  F11 F1 + a mesh without provenance tier                                      -> INVALID
  F12 F1 + ep13 scored with a mesh other than the tracked one                  -> INVALID
  F13 F1 with P_o' on a commit whose pipeline/perc2.py differs (fake sha)      -> INVALID"""
import copy, glob, hashlib, json, os, shutil, subprocess, sys
import numpy as np

W, POB, POP, RPO, V3, REPO = sys.argv[1:7]
V = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'rtk_verdict.py')
PY = sys.executable
E0 = {'white_pot', 'white_pot_lid', 'plastic_dish_rack', 'blue_cup'}
HEAD = subprocess.run(['git', '-C', REPO, 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
SPo = json.load(open(RPO))
Bpo = {int(p.split('/ep')[-1].split('/')[0]): p for p in glob.glob(f'{POB}/**/ep*/bundle.json', recursive=True)}
Ppo = {int(p.split('/ep')[-1].split('/')[0]): p for p in glob.glob(f'{POP}/**/ep*/perc2/poses.npz', recursive=True)}
assert len(Bpo) == 20 and len(Ppo) == 20, (len(Bpo), len(Ppo))


def build(case, commit=HEAD, v3copy=False, d_r=None, d_rpe=None, mutate=None):
    d = f'{W}/{case}'; shutil.rmtree(d, ignore_errors=True)
    os.makedirs(f'{d}/deliv'); os.makedirs(f'{d}/pop_b'); os.makedirs(f'{d}/pop_p')
    val = json.load(open(V3)); files = {}; pop = copy.deepcopy(SPo)
    for e, bp in Bpo.items():
        b = json.load(open(bp)); b['commit'] = commit; b['run_id'] = f'20261101-rtkA-{commit[:7]}'
        a = b['arms'] = {'perc2': b['arms']['perc2']}
        a['perc2']['lib_ep_dir'] = '/content/v2d-track3/meshes/rtk_e0b_public'; a['perc2']['templates_as_delivered'] = True
        for n, t in a['perc2']['templates'].items():
            rel = f'ep{e}/{n}.glb'
            if v3copy or n in E0:
                md = t['md5'] if v3copy else hashlib.md5(f'fixture {e} {n}'.encode()).hexdigest()
                files[rel] = dict(val['files'].get(rel, {}), md5=md, provenance_tier='STUB tier P1 (fixture)')
                t.update(md5=md, source='episode'); pop['episodes'][str(e)]['meshes'][n] = dict(md5=md, source='episode')
            else:
                t['source'] = 'library'
        os.makedirs(f'{d}/pop_b/ep{e}'); json.dump(b, open(f'{d}/pop_b/ep{e}/bundle.json', 'w'))
        os.makedirs(f'{d}/pop_p/ep{e}/perc2'); shutil.copyfile(Ppo[e], f'{d}/pop_p/ep{e}/perc2/poses.npz')
    val['files'] = files; json.dump(val, open(f'{d}/deliv/VALIDATION.json', 'w'))
    changed = sorted(e for e in Bpo if any(n in E0 for n in json.load(open(Bpo[e]))['objects'])) if not v3copy else []
    for i, e in enumerate(changed):
        s = pop['episodes'][str(e)]
        s['AUC'] = round(s['AUC'] + (d_r(i, e) if d_r else 0.0), 4); s['RPE_cm'] = round(s['RPE_cm'] + (d_rpe(i, e) if d_rpe else 0.0), 4)
    if mutate:
        mutate(d, pop)
    json.dump(pop, open(f'{d}/R_Pop.json', 'w'))
    return d, changed


def run(case, expect, **kw):
    d, ch = build(case, **kw)
    r = subprocess.run([PY, '-I', V, '--po', RPO, '--pop', f'{d}/R_Pop.json', '--po-bundles', POB, '--pop-bundles', f'{d}/pop_b',
                        '--po-poses', POP, '--pop-poses', f'{d}/pop_p', '--delivery', f'{d}/deliv', '--commit', kw.get('commit', HEAD),
                        '--repo', REPO, '--out', f'{d}/verdict.json'], capture_output=True, text=True)
    lines = r.stdout.splitlines()
    got = {0: 'PASS', 1: 'FAIL', 2: 'INCOMPLETE', 3: 'INVALID'}.get(r.returncode, f'rc {r.returncode}')
    ok = got == expect
    print(f'{case}: expected {expect}, got {got} {"ok" if ok else "MISMATCH"}; changed episodes {len(ch)}')
    for l in lines[1:]:
        if l.startswith(('  INVALID', '  INCOMPLETE', '  mean dR', '  NOTE')):
            print('   ', l.strip()[:230])
    if r.stderr.strip():
        print('    stderr:', r.stderr.strip()[-300:])
    return ok


def setp(e, key, val):
    def f(d, pop):
        pop['episodes'][str(e)][key] = val
    return f


plus = lambda i, e: 0.02 if i < 13 else -0.01
oks = [run('F0', 'FAIL', v3copy=True),
       run('F1', 'PASS', d_r=plus, d_rpe=lambda i, e: -0.05 if i < 13 else 0.0)]
base = dict(d_r=plus, d_rpe=lambda i, e: -0.05 if i < 13 else 0.0)
oks.append(run('F2', 'FAIL', d_r=lambda i, e: 0.02 if i < 13 else (-0.04 if i == 13 else -0.01), d_rpe=base['d_rpe']))
oks.append(run('F3', 'FAIL', d_r=lambda i, e: 0.015 if i < 13 else -0.01, d_rpe=base['d_rpe']))
oks.append(run('F4', 'FAIL', d_r=lambda i, e: 0.03 if i < 11 else -0.001, d_rpe=base['d_rpe']))
oks.append(run('F5', 'FAIL', d_r=plus, d_rpe=lambda i, e: 0.05 if i < 13 else 0.0))


def drop45(d, pop):
    pop['episodes'].pop('45')


oks.append(run('F6', 'INCOMPLETE', mutate=drop45, **base))


def depth12(d, pop):
    b = json.load(open(f'{d}/pop_b/ep12/bundle.json')); b['inputs']['depth']['frame0_sha256'] = '0' * 64
    json.dump(b, open(f'{d}/pop_b/ep12/bundle.json', 'w'))


oks.append(run('F7', 'INVALID', mutate=depth12, **base))


def cam2(d, pop):
    z = dict(np.load(f'{d}/pop_p/ep2/perc2/poses.npz')); z['world_T_cam'] = z['world_T_cam'].copy(); z['world_T_cam'][:, 0, 3] += 0.002
    np.savez(f'{d}/pop_p/ep2/perc2/poses.npz', **z)


oks.append(run('F8', 'INVALID', mutate=cam2, **base))


def tpl11(d, pop):
    b = json.load(open(f'{d}/pop_b/ep11/bundle.json')); b['arms']['perc2']['templates']['blue_cup']['md5'] = 'f' * 32
    json.dump(b, open(f'{d}/pop_b/ep11/bundle.json', 'w')); pop['episodes']['11']['meshes']['blue_cup']['md5'] = 'f' * 32


oks.append(run('F9', 'INVALID', mutate=tpl11, **base))
oks.append(run('F10', 'PASS', mutate=lambda d, pop: pop['episodes']['18'].update(AUC=round(pop['episodes']['18']['AUC'] + 0.05, 4)), **base))


def notier(d, pop):
    v = json.load(open(f'{d}/deliv/VALIDATION.json')); v['files']['ep2/white_pot.glb']['provenance_tier'] = None
    json.dump(v, open(f'{d}/deliv/VALIDATION.json', 'w'))


oks.append(run('F11', 'INVALID', mutate=notier, **base))
oks.append(run('F12', 'INVALID', mutate=lambda d, pop: pop['episodes']['13']['meshes']['blue_cup'].update(md5='1' * 32), **base))
oks.append(run('F13', 'INVALID', commit='1234567890abcdef1234567890abcdef12345678', **base))
print(f'verdict fixtures: {sum(oks)}/{len(oks)} as expected')
sys.exit(0 if all(oks) else 1)
