#!/usr/bin/env python3
"""Tests for tools/no_oracle.py ALLOW_CKPT (pack 11, 1 Nov 2026): exactly ONE checkpoint is accepted by content, and
everything else the guard refused before is still refused. Usage: allow_ckpt_test.py DL_DIR WORK_DIR > out.json
DL_DIR = a download root holding runs/20261101-e10nj-451b82d/results/... (ck512, conf512 r1, the 1024 checkpoint,
conf1024 r1) and runs/20261101-e10cs-50c2d90/results/ev10_cs/conf/r1 (pack 10's eval-10 rollout, a normal input)."""
import json, os, shutil, struct, subprocess, sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), *(['..'] * 6)))   # scripts → cpu → eval10 → work → research → docs → repo
assert os.path.isfile(os.path.join(REPO, 'tools', 'no_oracle.py')), REPO
NO = os.path.join(REPO, 'tools', 'no_oracle.py')
dl, work = sys.argv[1], sys.argv[2]
os.makedirs(work, exist_ok=True)
N = f'{dl}/runs/20261101-e10nj-451b82d/results'
C = f'{dl}/runs/20261101-e10cs-50c2d90/results/ev10_cs/conf/r1/ep10'
ck512 = f'{N}/ev10_nj/ck512/policy.safetensors'
ck1024 = f'{N}/perc2e10njs43_glock_public/ep10/best/policy.safetensors'
c512p, c512j = f'{N}/ev10_nj/conf512/r1/ep10/episode_000010.parquet', f'{N}/ev10_nj/conf512/r1/ep10/episode_000010.json'
c1024p, c1024j = f'{N}/ev10_nj/conf1024/r1/ep10/episode_000010.parquet', f'{N}/ev10_nj/conf1024/r1/ep10/episode_000010.json'

# neutral-name copies (a renamed file must be judged by content)
neu = os.path.join(work, 'neutral'); os.makedirs(neu, exist_ok=True)
n1024 = shutil.copy2(ck1024, os.path.join(neu, 'policy_a.safetensors'))
n512 = shutil.copy2(ck512, os.path.join(neu, 'policy_b.safetensors'))
n1024j = shutil.copy2(c1024j, os.path.join(neu, 'episode_a.json'))
# a tampered json: the allowed rollout's json with another checkpoint named
tj = os.path.join(neu, 'episode_tampered.json')
d = json.load(open(c512j)); d['checkpoint_sha256'] = '3c75ca1debb558d7c6a6266efbdc1973c2514dba9d76b90493abf1a5f83b7537'
json.dump(d, open(tj, 'w'))
# a json that claims the allowed sha but sits on a neutral path (accepted: the exception is by content, as specified)
cj = os.path.join(neu, 'episode_claims_allowed.json')
d = json.load(open(c1024j)); d['checkpoint_sha256'] = 'aaa077ebae863650c926d13550d368704889d445bcfc96ef9e4773f17c04d55f'
json.dump(d, open(cj, 'w'))

cases = [  # (name, inputs, expected exit code: 0 accepted, 1 refused)
    ('ck512 (allowed sha) as is', [ck512], 0),
    ('ck512 neutral-name copy', [n512], 0),
    ('conf512 r1 rollout parquet', [c512p], 0),
    ('conf512 r1 rollout json', [c512j], 0),
    ('conf512 r1 parquet + json together', [c512p, c512j], 0),
    ('pack 10 eval-10 rollout (normal input)', [f'{C}/episode_000010.parquet', f'{C}/episode_000010.json'], 0),
    ('1024 checkpoint as is', [ck1024], 1),
    ('1024 checkpoint neutral-name copy (non-stock limits by content)', [n1024], 1),
    ('conf1024 r1 rollout parquet', [c1024p], 1),
    ('conf1024 r1 rollout json', [c1024j], 1),
    ('conf1024 json neutral-name copy (its content names e10nj paths)', [n1024j], 1),
    ('allowed json tampered to name the 1024 checkpoint', [tj], 1),
    ('run id word', ['20261101-e10nj-451b82d'], 1),
    ('result folder word', ['results/ev10_nj/conf1024'], 1),
    ('reference path word of the diagnostic', ['/workspace/refs/perc2e10njs43_glockt/ep10/processed/x.parquet'], 1),
    ('the whole e10nj results dir (contains the 1024 checkpoint)', [N], 1),
    ('allowed + a refused input together', [c512p, c1024p], 1),
]
rows, ok = [], True
for name, inputs, want in cases:
    r = subprocess.run([sys.executable, '-I', NO, *inputs], capture_output=True, text=True)
    good = r.returncode == want
    ok &= good
    rows.append(dict(case=name, want='accepted' if want == 0 else 'refused', got='accepted' if r.returncode == 0 else 'refused',
                     ok=good, out=(r.stdout + r.stderr).strip().replace(dl, '<DL>').replace(work, '<WORK>')[:300]))
info = dict(note='claims_allowed: a json whose content names the allowed sha is accepted by design (the exception is by '
                 'content); pack_swap_rollouts additionally requires the parquet metadata and the json to name the same '
                 'checkpoint and the --expect-checkpoint sha, so a mislabelled json cannot enter a pack alone',
            claims_allowed=subprocess.run([sys.executable, '-I', NO, cj], capture_output=True, text=True).returncode)
print(json.dumps(dict(ok=ok, n=len(rows), passed=sum(r['ok'] for r in rows), cases=rows, info=info), indent=1))
sys.exit(0 if ok else 1)
