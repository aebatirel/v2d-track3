"""Frame-level diagnosis jobs of refcheck/chain (diag.py) for the flagged links. One process (run_jobs.py may use the
other scorer slot). Resumable. Usage: python -I diag_jobs.py [--only PREFIX]"""
import json, os, subprocess, sys, time

SP = '/tmp/claude-0/-home-user-v2d-track3/12630086-0942-582d-80bb-a9806af3e32b/scratchpad/refcheck'
ST = f'{SP}/store'; W = f'{SP}/work/chain'; REPO = '/home/user/v2d-track3'; PY = f'{SP}/venv/bin/python'
HERE = os.path.dirname(os.path.abspath(__file__))
C = {e['ep']: e for e in json.load(open(f'{SP}/work/canonical_refs.json'))['episodes']}
V3, V3X = f'{REPO}/meshes/library_v3', f'{REPO}/meshes/library_v3x'


def lib(ep):
    return V3X if ep == 11 else V3


def perc(ep):
    return f"{ST}/{C[ep]['perception_path']}"


J = []   # (tag, ep, A, B, meshes, meshes_b)
for ep in (2, 11, 12, 18, 21, 26, 31):
    J.append((f'mkref_ep{ep}_lib', ep, perc(ep), f'{W}/npz/ep{ep}_e2s.npz', lib(ep), None))
for ep in (2, 26, 31, 18):
    J.append((f'cr_ep{ep}_lib', ep, f'{W}/npz/ep{ep}_e2s.npz', f'{W}/npz/ep{ep}_proc.npz', lib(ep), None))
for ep in (2, 11, 12, 21, 26):
    J.append((f'mkref_ep{ep}_scan', ep, perc(ep), f'{W}/npz/ep{ep}_e2s.npz', None, None))
for ep in (11, 12, 21, 31, 26, 27):    # registration cost: same perception path, scans (A) vs our meshes (B)
    J.append((f'reg_ep{ep}_perc', ep, perc(ep), perc(ep), None, lib(ep)))

only = sys.argv[sys.argv.index('--only') + 1] if '--only' in sys.argv else ''
os.makedirs(f'{W}/diag', exist_ok=True)
for tag, ep, A, B, m, mb in J:
    if not tag.startswith(only) or os.path.exists(f'{W}/diag/{tag}.json'):
        continue
    c = [PY, '-I', f'{HERE}/diag.py', str(ep), A, B, '--t3', f'{SP}/t3', '--kit', f'{SP}/kit/v2d_submission_kit',
         '--out', f'{W}/diag/{tag}.json', '--pf', f'{W}/diag/{tag}.npz'] + (['--meshes', m] if m else []) + (['--meshes_b', mb] if mb else [])
    t0 = time.time()
    env = dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
    with open(f'{W}/logs/diag_{tag}.log', 'w') as f:
        r = subprocess.run(c, stdout=f, stderr=subprocess.STDOUT, env=env)
    with open(f'{W}/commands.log', 'a') as f:
        f.write(json.dumps(dict(tag='diag_' + tag, rc=r.returncode, sec=round(time.time() - t0, 1), cmd=' '.join(c))) + '\n')
    print(tag, r.returncode, round(time.time() - t0, 1), flush=True)
