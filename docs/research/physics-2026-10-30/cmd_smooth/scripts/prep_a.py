"""Test A trees: GL (physS1 glockt, already remapped in dchk/pep<N>) and SOL (psolverl ref_ps), raw and smoothed."""
import glob, hashlib, json, os, shutil, subprocess, sys
import pyarrow as pa, pyarrow.parquet as pq
S = sys.argv[1]; C = f'{S}/cmds'; A = f'{S}/dchk/assets_pub'; out = {}
SOL = {2: 'refs/psolve2/ep2', 12: 'refs/psolve2/ep12', 18: 'refs/psolve/ep18', 24: 'refs/psolve/ep24'}
md5 = lambda p: hashlib.md5(open(p, 'rb').read()).hexdigest()  # noqa: E731
for ep in (2, 12, 18, 24):
    gl = glob.glob(f'{S}/dchk/pep{ep}/processed/*/*/ref.parquet')[0]; hive = os.path.relpath(os.path.dirname(gl), f'{S}/dchk/pep{ep}/processed')
    sb = f'{C}/store/runs/20261030-psolverl-04301a2/{SOL[ep]}'; sp = glob.glob(f'{sb}/processed/*/*/ref_ps.parquet')[0]
    for st, src, stage in (('GL', gl, f'{S}/dchk/pep{ep}/reconstructed_stage'), ('SOL', sp, f'{sb}/reconstructed_stage')):
        for v in ('raw', 'smooth'):
            d = f'{C}/{st}_{v}_ep{ep}'; os.makedirs(f'{d}/processed/{hive}', exist_ok=True)
            shutil.copytree(stage, f'{d}/reconstructed_stage', dirs_exist_ok=True); dst = f'{d}/processed/{hive}/ref.parquet'
            t = pq.read_table(src); new = [p.replace('/content/assets', A) for p in t.column('object_urdf_paths')[0].as_py()]
            assert all(os.path.exists(p) for p in new), new
            i = t.column_names.index('object_urdf_paths'); t = t.set_column(i, 'object_urdf_paths', pa.array([new], type=t.schema.field('object_urdf_paths').type))
            if v == 'raw':
                pq.write_table(t, dst)
            else:
                tmp = dst + '.in.parquet'; pq.write_table(t, tmp)
                subprocess.run([sys.executable, '/home/user/v2d-track3/tools/physics_solve/cmd_smooth.py', tmp, dst, '--json', f'{d}/smooth_stats.json'], check=True, capture_output=True)
                os.remove(tmp)
            out[f'{st}_{v}_ep{ep}'] = dict(src=src, src_md5=md5(src), tree=d, ref=dst)
json.dump(out, open(f'{C}/prep_a.json', 'w'), indent=1); print(len(out), 'trees')
