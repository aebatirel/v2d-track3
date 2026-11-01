"""Repair (b) public gate (pre-registered in docs/work-log.md 20:31 UTC; set fixed 20:36 UTC): per public episode,
U = the stored support-filled pre-lock reference, F = pipeline/hold_filter.py (defaults) on it; both re-locked on CPU
(tools/cpu_glock_zero.sh with the run's GL_ARGS, no REPLAN / EVOLVE). M1: registered AUC of the object track vs mocap
(pipeline/score_registered.py, the episode's own meshes). M2: zero-action jittered sim_vs_ref of the re-locked
references (jitter_check --k 9 --seed 0; symmetric kit errors primary for cups, plain ADD reported).
Usage: S=<scratchpad> python -I gate_b.py OUT_DIR   (ground truth is read only by the M1 scoring, after the builds)"""
import concurrent.futures as cf, glob, importlib, json, os, shutil, subprocess, sys
import numpy as np, pyarrow as pa, pyarrow.parquet as pq

S = os.environ['S']; OUT = os.path.abspath(sys.argv[1]); R = '/home/user/v2d-track3'; os.makedirs(OUT, exist_ok=True)
GA = '--single_hand 1 --mcp_first 1 --close 10 --palm_clear -0.001 --wrap_where_held 1 --snap 1 --approach_cm 15'
SET = {2: ('runs/20261031-mass-2ed46ea', GA + ' --onset_anchor 1'), 12: ('runs/20261031-mass-2ed46ea', GA + ' --onset_anchor 1'),
       13: ('runs/20261030-orcB-38234d1', GA), 31: ('runs/20261030-orcB-38234d1', GA)}
ENV = dict(os.environ, FCD=f'{S}/src/video_to_data/robotic_grounding/flash_chord', PY=f'{S}/fcvenv/bin/python',
           SPY=f'{S}/venv/bin/python', KIT=f'{S}/kit/v2d_submission_kit', OMP_NUM_THREADS='1', EMB='sharpa_hands_mid', DEV='cpu')


def sh(cmd, log):
    with open(log, 'w') as f:
        return subprocess.run(cmd, shell=True, stdout=f, stderr=subprocess.STDOUT, env=ENV).returncode


def prep(ep):
    run, _ = SET[ep]; src = glob.glob(f'{S}/mirror/{run}/refs/sf/ep{ep}/processed/*/*/ref_sf.parquet')[0]
    root = f'{OUT}/ep{ep}/in'; hive = os.path.relpath(os.path.dirname(src), f'{S}/mirror/{run}/refs/sf/ep{ep}')
    os.makedirs(f'{root}/{hive}', exist_ok=True)
    for d in ('assets', 'reconstructed_stage'):
        shutil.copytree(f'{S}/mirror/{run}/refs/sf/ep{ep}/{d}', f'{root}/{d}', dirs_exist_ok=True)
    t = pq.read_table(src); i = t.column_names.index('object_urdf_paths'); old = t.column(i)[0].as_py()
    new = [f'{root}/assets/' + u.split('/assets/', 1)[1] for u in old]
    t = t.set_column(i, 'object_urdf_paths', pa.array([new], type=t.schema.field(i).type))
    U = f'{root}/{hive}/ref_in.parquet'; pq.write_table(t, U)
    F = f'{root}/{hive}/ref_hf.parquet'
    rc = sh(f'{S}/venv/bin/python -I {R}/pipeline/hold_filter.py {U} {F}', f'{OUT}/ep{ep}/hold_filter.log')
    return U, F, rc


def build(ep, arm, ref):
    _, ga = SET[ep]; d = f'{OUT}/ep{ep}/{arm}'
    rc = sh(f'bash {R}/tools/cpu_glock_zero.sh {ref} {d} "{ga}"', f'{OUT}/ep{ep}/{arm}_build.log')
    g = glob.glob(f'{d}/processed/*/*/ref_gl_ilc.parquet')
    if rc or not g:
        return None
    sh(f'cd {ENV["FCD"]} && {ENV["PY"]} {R}/tools/physics_solve/jitter_check.py {g[0]} --device cpu --k 9 --seed 0 '
       f'--json {d}/jitter.json --out {d}/jitter.npz', f'{d}/jitter.log')
    return g[0]


def main():
    refs = {ep: prep(ep) for ep in SET}
    json.dump({ep: [r[0], r[1], r[2]] for ep, r in refs.items()}, open(f'{OUT}/inputs.json', 'w'), indent=1)
    jobs = [(ep, arm, refs[ep][0 if arm == 'U' else 1]) for ep in SET for arm in ('U', 'F')]
    with cf.ThreadPoolExecutor(int(os.environ.get('PAR', '4'))) as ex:
        built = dict(zip([(e, a) for e, a, _ in jobs], ex.map(lambda j: build(*j), jobs)))
    json.dump({f'{e}{a}': v for (e, a), v in built.items()}, open(f'{OUT}/built.json', 'w'), indent=1)
    print('built', {f'{e}{a}': bool(v) for (e, a), v in built.items()}, flush=True)


if __name__ == '__main__':
    main()
