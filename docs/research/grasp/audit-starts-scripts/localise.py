"""Copy a stored INPUT reference (refs/sf/epN ref_sf.parquet, the grasp-lock input) into a local tree with local URDF
paths; optional OBJ=URDF overrides. Usage: localise.py EP TREE [OBJ=URDF ...]"""
import sys, os, glob, shutil, pyarrow as pa, pyarrow.parquet as pq
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from common import *
ep, tree = int(sys.argv[1]), sys.argv[2]; over = dict(x.split('=') for x in sys.argv[3:])
src = glob.glob(f'{run_dir(ep)}/refs/sf/ep{ep}/processed/*/*/ref_sf.parquet')[0]
hive = os.path.relpath(os.path.dirname(src), os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(src)))))
os.makedirs(f'{tree}/{hive}', exist_ok=True)
if not os.path.isdir(f'{tree}/reconstructed_stage'):
    shutil.copytree(f'{run_dir(ep)}/refs/sf/ep{ep}/reconstructed_stage', f'{tree}/reconstructed_stage')
t = pq.read_table(src); names = t.column('object_body_names')[0].as_py()
u = [over.get(n, f'{run_dir(ep)}/refs/sf/ep{ep}/assets/urdf/{os.path.basename(p)}') for n, p in zip(names, t.column('object_urdf_paths')[0].as_py())]
for x in u:
    assert os.path.exists(x), x
t = t.set_column(t.column_names.index('object_urdf_paths'), 'object_urdf_paths', pa.array([u], type=t.schema.field('object_urdf_paths').type))
pq.write_table(t, f'{tree}/{hive}/ref_sf.parquet'); print(f'{tree}/{hive}/ref_sf.parquet')
