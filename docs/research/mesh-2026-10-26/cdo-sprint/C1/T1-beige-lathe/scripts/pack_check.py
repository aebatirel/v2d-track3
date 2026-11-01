"""Which beige-cup mesh is packed for evals 8 and 10 (no scoring): compare the submitted CD-O vertex rows with the
kit packer's budget_mesh of library_v3 and library_v3x. Usage: pack_check.py KIT CDO_PARQUET REPO"""
import sys
import numpy as np, pyarrow.parquet as pq
from scipy.spatial import cKDTree
kit, cdo_pq, repo = sys.argv[1:4]
sys.path.insert(0, kit)
from v2dlb.mesh_budget import budget_mesh
t = pq.read_table(cdo_pq).to_pandas()
lib = {n: np.asarray(budget_mesh(f'{repo}/meshes/{n}/beige_cup.glb', 4096, 4096)[0], float) for n in ('library_v3', 'library_v3x')}
for ep in (8, 10):
    for k in (0, 1):
        pre = f't3m_{ep:06d}_beige_cup_{k}_'
        r = t[t.row_id.str.startswith(pre)]
        X = r[['x', 'y', 'z']].to_numpy(float)
        out = []
        for n, V in lib.items():
            d1 = cKDTree(V).query(X)[0]; d2 = cKDTree(X).query(V)[0]
            out.append(f'{n}: max {1e3 * max(d1.max(), d2.max()):.3f} mm, n {len(V)}')
        print(f'eval {ep} beige rows _{k}: n {len(X)};', '; '.join(out))
