"""Local CPU copies of the 5 packed D-eval references (md5-checked) with object_urdf_paths remapped from the box roots
to local asset copies (URDF mesh paths are relative). Our perception references only; no ground truth."""
import hashlib, json, os, shutil, sys
import pyarrow as pa, pyarrow.parquet as pq
S, ST = sys.argv[1], sys.argv[2]                      # dchk dir, store download dir
E = {14: ('20261025-evb1420-ee7ba8e', 'refs/glockt/ep14', 'refs/sf/ep14/assets', '10d5f3ba6b7368ed30dad9d0c9c30df1'),
     16: ('20261024-pack-31ef267', 'refs/glockt/ep16', 'refs/sf/ep16/assets', 'f7e2ea9260106425be6163553aac5af9'),
     33: ('20261026-fr3233s43-6a8a0e2', 'refs/glockt/ep33', 'refs/sf/ep33/assets', '2a7173ab1d4248433bd049bc43f6878a'),
     25: ('20261026-c25s42-feb0407', 'refs/perc2mck/ep25', None, '71ac95f3764170f29f02fa657e7c057c'),
     30: ('20261025-std30-ee7ba8e', 'refs/perc2mck/ep30', None, 'dd464c96184e84400e62ffcfa17a6ac4')}
out = {}
for ep, (run, sub, asub, md5) in E.items():
    base = f'{ST}/runs/{run}/{sub}'
    src = [os.path.join(dp, f) for dp, _, fs in os.walk(f'{base}/processed') for f in fs if f.endswith('.parquet')][0]
    m = hashlib.md5(open(src, 'rb').read()).hexdigest(); assert m == md5, (ep, m, md5)
    hive = os.path.relpath(os.path.dirname(src), f'{base}/processed')
    dst_dir = f'{S}/ep{ep}/processed/{hive}'; os.makedirs(dst_dir, exist_ok=True)
    shutil.copytree(f'{base}/reconstructed_stage', f'{S}/ep{ep}/reconstructed_stage', dirs_exist_ok=True)
    t = pq.read_table(src); paths = t.column('object_urdf_paths')[0].as_py()
    local = f'{ST}/runs/{run}/{asub}' if asub else f'{S}/assets_std'
    new = [p.replace(f'/content/{asub}', local) if asub else p.replace('/content/assets', local) for p in paths]
    assert all(os.path.exists(p) for p in new), new
    i = t.column_names.index('object_urdf_paths')
    t = t.set_column(i, 'object_urdf_paths', pa.array([new], type=t.schema.field('object_urdf_paths').type))
    dst = f'{dst_dir}/ref.parquet'; pq.write_table(t, dst)
    out[ep] = dict(run=run, ref=f'{run}/{src.split(run + "/")[1]}', md5=m, local=dst, urdfs=new, emb='sharpa_hands_mid' if asub else 'default')
json.dump(out, open(f'{S}/prep.json', 'w'), indent=1); print(json.dumps({k: (v['md5'][:8], v['emb']) for k, v in out.items()}))
