"""Per-object attribution of the registration cost (refcheck/chain, 26 Oct 2026; evaluation only).

In a two-object scene the kit aligns the whole scene on object slot 0's frame-0 position (and on the first object
without a symmetry axis for the orientation), so the registration error of one object's mesh can cost AUC on the other.
For each flagged episode, score the perception path and the final reference with mixed candidate meshes: one object
with our mesh (library_v3 / v3x), the other with its public scan (a directory of symlinks). One process. Resumable.
Usage: python -I hyb_jobs.py
"""
import json, os, subprocess, time

SP = '/tmp/claude-0/-home-user-v2d-track3/12630086-0942-582d-80bb-a9806af3e32b/scratchpad/refcheck'
ST = f'{SP}/store'; W = f'{SP}/work/chain'; REPO = '/home/user/v2d-track3'; PY = f'{SP}/venv/bin/python'
C = {e['ep']: e for e in json.load(open(f'{SP}/work/canonical_refs.json'))['episodes']}
EPS = {11: ['blue_cup', 'beige_cup'], 12: ['blue_cup', 'plastic_dish_rack'], 21: ['blue_cup', 'water_pitcher'],
       31: ['mini_sweeper', 'plastic_dish_rack']}


def scan(n):
    q = f'{SP}/t3/mesh/{n}/{n}.glb'
    return q if os.path.exists(q) else f'{SP}/t3/mesh/{n}/{n}_visual.glb'


for ep, objs in EPS.items():
    lib = f'{REPO}/meshes/library_v3x' if ep == 11 else f'{REPO}/meshes/library_v3'
    for ours in objs:
        d = f'{W}/hyb/ep{ep}_{ours}_ours'
        os.makedirs(d, exist_ok=True)
        for n in objs:
            dst = f'{d}/{n}.glb'
            if not os.path.lexists(dst):
                os.symlink(f'{lib}/{n}.glb' if n == ours else scan(n), dst)
        for src_tag, src in (('perc', f"{ST}/{C[ep]['perception_path']}"), ('proc', f'{W}/npz/ep{ep}_proc.npz')):
            tag = f'hyb_ep{ep}_{src_tag}_{ours}_ours'
            if os.path.exists(f'{W}/scores/{tag}.json'):
                continue
            c = [PY, '-I', f'{REPO}/pipeline/score_registered.py', str(ep), src, '--meshes', d, '--t3', f'{SP}/t3',
                 '--kit', f'{SP}/kit/v2d_submission_kit', '--out', f'{W}/scores/{tag}.json']
            t0 = time.time(); env = dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
            with open(f'{W}/logs/{tag}.log', 'w') as f:
                r = subprocess.run(c, stdout=f, stderr=subprocess.STDOUT, env=env)
            with open(f'{W}/commands.log', 'a') as f:
                f.write(json.dumps(dict(tag=tag, rc=r.returncode, sec=round(time.time() - t0, 1), cmd=' '.join(c))) + '\n')
            print(tag, r.returncode, round(time.time() - t0, 1), flush=True)
