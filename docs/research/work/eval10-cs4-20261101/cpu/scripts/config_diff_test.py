"""CPU config diff (PREREG section 3.2 / orchestrator condition 1): is the recipe this job trains pack-eligible, i.e. does every
stored-config key equal the PACKED eval-10 checkpoint's (run 20261026-gl10A2-5e0e100, sha256 76a12265...) except the
reference paths, the output dir and the seed keys, at stock 512 / 256? Uses tools/e10cs.py's own config_diff (the function the
box's `cells` step runs), the same flattened stored-config diff as tools/e10nj.py identity.
  1. REAL e10v seed-43 checkpoint (sha256 bcc51063..., trained by the recipe lines ev10_cs.sh copies verbatim, through the same
     glock_public.sh template and TRAIN_ARGS; static_checks.txt, mock check 'TRAIN_ARGS = e10v's REAL job log line') vs the REAL
     packed checkpoint: the diff must lie inside ALLOWED; sim / env.sim limits 512 / 256.
  2. Stand-in of THIS job's seed-43 checkpoint: e10v's real one with only its stored task.parquet / reference.parquet /
     output_dir rewritten to this job's names (refs/perc2e10css43_glockt/ep10, runs/perc2e10css43_glock/ep10-s43): the
     collision pieces do not enter the config (they reach training through the reference's URDF paths, /content/assets).
     Same diff, same limits; and no_oracle accepts it (packable).
  3. Negative controls: the stand-in with njmax 1024 / nconmax 512 (tools/e10nj.py cksim) and with one extra key must FAIL.
Usage: python config_diff_test.py --repo R --packed CK --e10v CK43 --work DIR --out J"""
import argparse, json, os, struct, subprocess, sys

ap = argparse.ArgumentParser()
for k in ('repo', 'packed', 'e10v', 'work', 'out'):
    ap.add_argument('--' + k, required=True)
A = ap.parse_args(); os.makedirs(A.work, exist_ok=True)
sys.path.insert(0, os.path.join(A.repo, 'tools'))
import e10cs                       # noqa: E402
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


stock = {k: v for k, v in zip(e10cs.SIM_KEYS, (512, 256, 512, 256))}
res['packed_sha256'] = e10cs.sha256(A.packed); res['e10v_sha256'] = e10cs.sha256(A.e10v)
need(res['packed_sha256'] == e10cs.PACKED_SHA, f'packed checkpoint is the packed eval-10 one (sha256 {res["packed_sha256"][:12]})')
diff, bad, sim, cfg = e10cs.config_diff(A.e10v, A.packed)
res['e10v_vs_packed'] = dict(diff=diff, outside_allowed=bad, sim=sim, keys=len(e10cs.flat(cfg)))
need(not bad and sim == stock, f'REAL e10v s43 vs REAL packed: {len(e10cs.flat(cfg))}-key config, diff {diff} (all allowed), sim {sim}')


def ours(c):
    t = "'/content/refs/perc2e10css43_glockt/ep10/processed/sequence_id=t3_ep010/robot_name=sharpa_wave'"
    c['task']['parquet'] = t
    if isinstance(c.get('reference'), dict) and 'parquet' in c['reference']:
        c['reference']['parquet'] = t
    c['output_dir'] = '/content/runs/perc2e10css43_glock/ep10-s43'


st = os.path.join(A.work, 'standin_e10cs_s43', 'policy.safetensors'); os.makedirs(os.path.dirname(st), exist_ok=True); rewrite(A.e10v, st, ours)
diff, bad, sim, cfg = e10cs.config_diff(st, A.packed)
res['standin_vs_packed'] = dict(diff=diff, outside_allowed=bad, sim=sim, task=cfg['task']['parquet'], output_dir=cfg['output_dir'])
need(not bad and sim == stock and 'perc2e10css43' in cfg['task']['parquet'],
     f'stand-in of this job\'s s43 checkpoint vs REAL packed: diff {diff} (all allowed), sim {sim}')
r = subprocess.run([sys.executable, '-I', os.path.join(A.repo, 'tools', 'no_oracle.py'), st], capture_output=True, text=True)
need(r.returncode == 0, f'no_oracle accepts the stand-in (stock limits, perc2e10css names): rc {r.returncode} {(r.stdout + r.stderr).strip()[-160:]}')


def nj(c):
    ours(c)
    for b in (c['sim'], c['env']['sim']):
        b['njmax'], b['nconmax'] = 1024, 512


def extra(c):
    ours(c); c['training']['mock_extra_setting'] = 1


for tag, fn, want in (('njmax1024', nj, 'sim limits'), ('extra_key', extra, 'training.mock_extra_setting')):
    p = os.path.join(A.work, f'neg_{tag}', 'policy.safetensors'); os.makedirs(os.path.dirname(p), exist_ok=True); rewrite(A.e10v, p, fn)
    diff, bad, sim, _ = e10cs.config_diff(p, A.packed)
    caught = bool(bad) and (want != 'sim limits' or sim != stock)
    res[f'negative_{tag}'] = dict(diff=diff, outside_allowed=bad, sim=sim)
    need(caught, f'negative control {tag}: caught (outside allowed {bad}, sim {sim})')
r = subprocess.run([sys.executable, '-I', os.path.join(A.repo, 'tools', 'no_oracle.py'), os.path.join(A.work, 'neg_njmax1024', 'policy.safetensors')],
                   capture_output=True, text=True)
need(r.returncode != 0, 'no_oracle still refuses a non-stock-limit checkpoint under this job\'s names')
res['ok'] = not fails; res['failures'] = fails
json.dump(res, open(A.out, 'w'), indent=1)
print('RESULT: ' + ('ALL CHECKS PASS' if not fails else f'{len(fails)} FAILED: {fails}'))
sys.exit(0 if not fails else 1)
