"""Job list and runner for refcheck/chain (26 Oct 2026; CPU, at most 2 scorer processes; evaluation only).

Scores, with pipeline/score_registered.py (the kit's registered scoring, public scan standing in for the hidden one),
every link of the chain perception -> mkref (e2s_reference.parquet) -> contact retarget (processed parquet) ->
evaluator reference columns (+ the rollout itself), each with our submitted meshes (library_v3; v3x for ep11 whose
run tracked the v5 beige cup) and with the public scans (no --meshes). Also re-scores the 20-episode perception sweep
(base arm) and the 8-episode track-guard arm, and the stale 20 Oct refsweep perception/reference pairs (public-scan
templates, so scored with the scans only). Resumable: a job whose output JSON exists is skipped.
Usage: python -I run_jobs.py [--dry] [--only PREFIX] [--workers 2]
"""
import argparse, glob, json, os, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor

SP = '/tmp/claude-0/-home-user-v2d-track3/12630086-0942-582d-80bb-a9806af3e32b/scratchpad/refcheck'
ST = f'{SP}/store'
W = f'{SP}/work/chain'
REPO = '/home/user/v2d-track3'
PY = f'{SP}/venv/bin/python'
SCORER = f'{REPO}/pipeline/score_registered.py'
HERE = os.path.dirname(os.path.abspath(__file__))
PUBLIC = [0, 2, 11, 12, 13, 18, 21, 22, 23, 24, 26, 27, 31, 39, 40, 41, 42, 43, 44, 45]
GUARD = [0, 11, 12, 18, 21, 23, 24, 31]


def lib_for(ep, canonical):
    return f'{REPO}/meshes/library_v3x' if (canonical and ep == 11) else f'{REPO}/meshes/library_v3'


def ref_npz(parquet, tag):
    out = f'{W}/npz/{tag}.npz'
    if not os.path.exists(out):
        subprocess.run([PY, '-I', f'{HERE}/ref2npz.py', parquet, out], check=True)
    return out


def jobs():
    J = []   # (tag, ep, source, meshes)
    C = json.load(open(f'{SP}/work/canonical_refs.json'))['episodes']
    for e in C:
        ep = e['ep']; lib = lib_for(ep, True)
        if not e['ref_path']:
            continue
        J += [(f'can_ep{ep}_perc_lib', ep, f"{ST}/{e['perception_path']}", lib),
              (f'can_ep{ep}_perc_scan', ep, f"{ST}/{e['perception_path']}", None)]
        e2s = f"{ST}/{e['ref_pre_contact_retarget']}"
        if os.path.exists(e2s):
            n = ref_npz(e2s, f'ep{ep}_e2s')
            J += [(f'can_ep{ep}_e2s_lib', ep, n, lib), (f'can_ep{ep}_e2s_scan', ep, n, None)]
        n = ref_npz(f"{ST}/{e['ref_parquet']}", f'ep{ep}_proc')
        J += [(f'can_ep{ep}_proc_lib', ep, n, lib)]
        r1 = f"{ST}/{e['results_dir']}/r1"
        J += [(f'can_ep{ep}_res_lib', ep, r1, lib), (f'can_ep{ep}_res_scan', ep, r1, None)]
    for ep in PUBLIC:
        p = f'{ST}/runs/20261025-sweep-a894083/results/sweep/base/ep{ep}/poses_world_vo.npz'
        J += [(f'sweep_ep{ep}_lib', ep, p, lib_for(ep, False)), (f'sweep_ep{ep}_scan', ep, p, None)]
    for ep in GUARD:
        p = f'{ST}/runs/20261025-guard-fe3f407/results/sweep/guard/ep{ep}/poses_world_vo.npz'
        J += [(f'guard_ep{ep}_lib', ep, p, lib_for(ep, False)), (f'guard_ep{ep}_scan', ep, p, None)]
    for e in C:
        if e['ref_path']:
            continue
        ep = e['ep']; rd = f"{ST}/{e['stale_reference']}"
        pq_ = sorted(glob.glob(f'{rd}/processed/*/*/*.parquet'))[0]
        n = ref_npz(pq_, f'ep{ep}_stale')
        J += [(f'stale_ep{ep}_perc_scan', ep, f'{ST}/runs/20261020-refsweep-ea14fdf/perc2/ep{ep}/poses_world_vo.npz', None),
              (f'stale_ep{ep}_ref_scan', ep, n, None)]
    return J


def cmd(tag, ep, src, meshes):
    c = [PY, '-I', SCORER, str(ep), src, '--t3', f'{SP}/t3', '--kit', f'{SP}/kit/v2d_submission_kit',
         '--out', f'{W}/scores/{tag}.json', '--per_frame', f'{W}/pf/{tag}.npz']
    return c + (['--meshes', meshes] if meshes else [])


def run(j):
    tag = j[0]
    if os.path.exists(f'{W}/scores/{tag}.json'):
        return tag, 'skip', 0
    c = cmd(*j); t0 = time.time()
    env = dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
    with open(f'{W}/logs/{tag}.log', 'w') as f:
        r = subprocess.run(c, stdout=f, stderr=subprocess.STDOUT, env=env)
    dt = time.time() - t0
    with open(f'{W}/commands.log', 'a') as f:
        f.write(json.dumps(dict(tag=tag, rc=r.returncode, sec=round(dt, 1), cmd=' '.join(c))) + '\n')
    return tag, r.returncode, dt


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--dry', action='store_true'); p.add_argument('--only', default='')
    p.add_argument('--workers', type=int, default=2); a = p.parse_args()
    for d in ('scores', 'pf', 'logs', 'npz'):
        os.makedirs(f'{W}/{d}', exist_ok=True)
    J = [j for j in jobs() if j[0].startswith(a.only)]
    print(len(J), 'jobs', flush=True)
    if a.dry:
        for j in J:
            print(' '.join(cmd(*j)))
        sys.exit()
    with ThreadPoolExecutor(a.workers) as ex:
        for tag, rc, dt in ex.map(run, J):
            print(tag, rc, round(dt, 1), flush=True)
