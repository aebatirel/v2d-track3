"""CPU pack-eligibility test of the eval-20 b1 retrain (PREREG sections 2.5 and 8): is the recipe this job trains the PACKED
eval-20 recipe (every stored-config key equal to the packed checkpoint's except the reference paths, the output dir and the
seed keys, at stock 512 / 256), and does tools/no_oracle.py accept this run (packable) while still refusing what it refused?
Uses tools/e20b1.py's own config_diff (e10cs.config_diff, the function the box's `cells` step runs).
  1. the packed eval-20 checkpoint is the packed one (sha256 61dcd7a6...) and was trained by the grasp-lock learner:
     output_dir runs/glock/ep20-s42, glockt reference, 70,004,736 steps, seed 42, flash_sac;
  2. REAL packed eval-14 vs REAL packed eval-20 checkpoint (same run evb1420, same glock_public.sh call): the diff is only
     the paths and reference.num_frames (the recipe is per run, not per episode);
  3. [R] the D arm (pack 9b, code a1a7e25, the same glock_public.sh training path) reproduced evb1420's eval-14 config
     except the allowed keys (results/drG/verify.json); since a1a7e25 glock_public.sh changed only in PERC-guard lines;
  4. a stand-in of THIS job's seed-43 checkpoint (the packed one with only task / reference / output_dir / seeds rewritten to
     this job's names): diff inside ALLOWED, stock limits, and no_oracle accepts it;
  5. negative controls: njmax 1024 and an extra key are caught; no_oracle refuses the 1024 stand-in;
  6. no_oracle accepts this run's names (run id, folders, job, tool, PREREG folder, the piece folder) and still refuses the
     njmax diagnostic's names and an oracle run id.
Usage: python -I config_guard_test.py --repo R --packed CK20 --packed14 CK14 --dr_verify drG/verify.json --work DIR --out J"""
import argparse, json, os, struct, subprocess, sys

ap = argparse.ArgumentParser()
for k in ('repo', 'packed', 'packed14', 'dr_verify', 'work', 'out'):
    ap.add_argument('--' + k, required=True)
A = ap.parse_args(); os.makedirs(A.work, exist_ok=True)
sys.path.insert(0, os.path.join(A.repo, 'tools'))
import e10cs, e20b1                # noqa: E402
res = dict(checks=[]); fails = []


def need(ok, what, **kw):
    res['checks'].append(dict(ok=bool(ok), what=what, **kw)); print(('PASS ' if ok else 'FAIL ') + what, flush=True)
    if not ok:
        fails.append(what)


def rewrite(src, dst, fn):  # header-only edit of the stored resolved config (canonical JSON, as tools/e10nj.py cksim)
    with open(src, 'rb') as f:
        n = struct.unpack('<Q', f.read(8))[0]; raw = f.read(n); body = f.read()
    h = json.loads(raw); cfg = json.loads(h['__metadata__']['user.resolved_config_json']); fn(cfg)
    h['__metadata__']['user.resolved_config_json'] = json.dumps(cfg, sort_keys=True, separators=(',', ':'))
    hb = json.dumps(h, separators=(',', ':')).encode(); hb += b' ' * (-len(hb) % 8)
    open(dst, 'wb').write(struct.pack('<Q', len(hb)) + hb + body)


def guard(*w):
    r = subprocess.run([sys.executable, '-I', os.path.join(A.repo, 'tools', 'no_oracle.py'), *w], capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip()[-200:]


stock = {k: v for k, v in zip(e10cs.SIM_KEYS, (512, 256, 512, 256))}
m, c = e10cs.ck_config(A.packed); f = e10cs.flat(c); res['packed_sha256'] = e10cs.sha256(A.packed)
learner = dict(output_dir=f.get('output_dir'), task=f.get('task.parquet'), steps=m.get('user.environment_steps'), seed=f.get('reset.seed'),
               algorithm=m.get('user.algorithm'), keys=len(f))
res['packed_learner'] = learner
need(res['packed_sha256'] == e20b1.PACKED_SHA, f'packed checkpoint is the packed eval-20 one (sha256 {res["packed_sha256"][:12]})')
need(learner['output_dir'] == '/content/runs/glock/ep20-s42' and '/refs/glockt/ep20/' in learner['task'] and learner['steps'] == '70004736'
     and str(learner['seed']) == '42' and learner['algorithm'] == 'flash_sac',
     f'packed eval-20 = the grasp-lock learner, seed 42: {learner}')
d, bad, sim, _ = e10cs.config_diff(A.packed14, A.packed)
res['packed14_vs_packed20'] = dict(diff=d, outside_allowed=bad, sim=sim)
need(set(d) == {'output_dir', 'task.parquet', 'reference.parquet', 'reference.num_frames'} and sim == stock,
     f'REAL packed eval-14 vs eval-20 (same run evb1420): diff {d} (paths + the reference length only), sim {sim}')
dv = json.load(open(A.dr_verify))['episodes']['14']
res['dr_arm_ep14'] = {s: sorted(x['packed_config_diff']) for s, x in dv['cells'].items()}
need(dv['status'] == 'VERIFIED' and all(set(k) <= e10cs.ALLOWED for k in res['dr_arm_ep14'].values()),
     f'[R] the D arm\'s current-path eval-14 cells vs packed evb1420 eval 14: {res["dr_arm_ep14"]} (all allowed), status {dv["status"]}')
T = "'/content/refs/e20b1s43_glockt/ep20/processed/sequence_id=t3_ep020/robot_name=sharpa_wave'"


def ours(c):
    c['task']['parquet'] = T
    if isinstance(c.get('reference'), dict) and 'parquet' in c['reference']:
        c['reference']['parquet'] = T
    c['output_dir'] = '/content/runs/e20b1s43_glock/ep20-s43'
    c['reset']['seed'] = 43; c['env']['reset']['seed'] = 43; c['training']['seed'] = 43


st = os.path.join(A.work, 'standin_e20b1_s43', 'policy.safetensors'); os.makedirs(os.path.dirname(st), exist_ok=True); rewrite(A.packed, st, ours)
d, bad, sim, cfg = e10cs.config_diff(st, A.packed)
res['standin_vs_packed'] = dict(diff=d, outside_allowed=bad, sim=sim, task=cfg['task']['parquet'], output_dir=cfg['output_dir'])
need(not bad and sim == stock and set(d) == e10cs.ALLOWED, f'stand-in of this job\'s s43 checkpoint vs REAL packed: diff {d} (all allowed), sim {sim}')
rc, o = guard(st); need(rc == 0, f'no_oracle accepts the stand-in: rc {rc} {o}')


def nj(c):
    ours(c)
    for b in (c['sim'], c['env']['sim']):
        b['njmax'], b['nconmax'] = 1024, 512


def extra(c):
    ours(c); c['training']['mock_extra_setting'] = 1


for tag, fn in (('njmax1024', nj), ('extra_key', extra)):
    p = os.path.join(A.work, f'neg_{tag}', 'policy.safetensors'); os.makedirs(os.path.dirname(p), exist_ok=True); rewrite(A.packed, p, fn)
    d, bad, sim, _ = e10cs.config_diff(p, A.packed)
    res[f'negative_{tag}'] = dict(diff=d, outside_allowed=bad, sim=sim)
    need(bool(bad) and (tag != 'njmax1024' or sim != stock), f'negative control {tag}: caught (outside allowed {bad}, sim {sim})')
rc, o = guard(os.path.join(A.work, 'neg_njmax1024', 'policy.safetensors')); need(rc != 0, f'no_oracle refuses the 1024 stand-in (rc {rc})')
ok_words = ['20261101-e20b1-abc1234', 'runs/20261101-e20b1-abc1234/results/ev20_b1/summary.json', 'refs/e20b1s42_glockt/ep20',
            'runs/e20b1s43_glock/ep20-s43', 'results/e20b1s42_glock_public/ep20', 'results/ev20_b1', 'ops/jobs/ev20_b1.sh', 'tools/e20b1.py',
            'docs/research/work/eval20-b1-20261101', os.path.join(A.repo, 'meshes/carve/ev20b1'), '20:' + os.path.join(A.repo, 'meshes/carve/ev20b1')]
for w in ok_words:
    rc, o = guard(w); need(rc == 0, f'no_oracle accepts {w.replace(A.repo, "<R>")}')
for w in ('20261101-e10nj-451b82d', 'results/ev10_nj', 'refs/perc2e10njs43_glockt/ep10', '20261030-orcB-38234d1'):
    rc, o = guard(w); need(rc != 0, f'no_oracle still refuses {w}')
ckj = os.path.join(A.work, 'kit_checkpoints.json'); json.dump({'20': st}, open(ckj, 'w'))
rc, o = guard(ckj); need(rc == 0, 'no_oracle accepts a kit checkpoints JSON naming the stand-in')
res['ok'] = not fails; res['failures'] = fails
json.dump(res, open(A.out, 'w'), indent=1)
print('RESULT: ' + ('ALL CHECKS PASS' if not fails else f'{len(fails)} FAILED: {fails}') + f' ({len(res["checks"])} checks)')
sys.exit(0 if not fails else 1)
