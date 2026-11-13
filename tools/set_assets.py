"""Copy a reference parquet with its object asset paths pointed at another asset tree (2026-10-30, physics study).
make_assets.py writes OUT/urdf/<obj>_rigid.urdf and OUT/mesh/<obj>/<obj>.glb; a reference names the asset root of the
box that built it (/content/assets). Usage: set_assets.py IN_PARQUET OUT_PARQUET ASSETS_DIR"""
import os, sys
import pyarrow as pa, pyarrow.parquet as pq

src, dst, assets = sys.argv[1], sys.argv[2], os.path.abspath(sys.argv[3])
t = pq.read_table(src)
names = t.column('object_body_names')[0].as_py()
new = {'object_urdf_paths': [f'{assets}/urdf/{n}_rigid.urdf' for n in names],
       'object_mesh_paths': [f'{assets}/mesh/{n}/{n}.glb' for n in names]}
for k, v in new.items():
    if k in t.column_names:
        for p in v:
            assert os.path.exists(p), p
        t = t.set_column(t.column_names.index(k), k, pa.array([v], type=t.schema.field(k).type))
os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
pq.write_table(t, dst)
print('assets ->', assets, {k: v for k, v in new.items() if k in t.column_names})
