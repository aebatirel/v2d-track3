"""Timing stress (not a real episode): ep24 boards + two copies offset 15 cm in x, frames tiled to T=900, B=4."""
import glob, os, shutil, sys
import numpy as np, pyarrow as pa, pyarrow.parquet as pq
S = sys.argv[1]; src = glob.glob(f'{S}/phys/S0/base/ep24/processed/*/*/ref.parquet')[0]; sim0 = f'{S}/intrusion_test/real/sim/public/ep24/r0'
out = f'{S}/intrusion_test/stress'; sim = f'{out}/sim/r0'; shutil.rmtree(out, ignore_errors=True); os.makedirs(sim)
t = pq.read_table(src); names = t.column('object_body_names')[0].as_py()
P = np.array(t.column('object_body_position')[0].as_py()); Q = np.array(t.column('object_body_wxyz')[0].as_py())
idx = np.r_[np.arange(len(P)), np.arange(len(P))[::-1], np.arange(len(P)), np.arange(len(P))[::-1]][:900]
P, Q = P[idx], Q[idx]; P2 = P + [0.15, 0, 0]
names4 = names + [n + '_copy' for n in names]
pq.write_table(pa.table(dict(object_body_names=[names4], object_body_position=[np.concatenate([P, P2], 1).tolist()],
                             object_body_wxyz=[np.concatenate([Q, Q], 1).tolist()], fps=[20.0])),
               f'{out}/ref.parquet')
for n in names:
    for m in (n, n + '_copy'):
        os.makedirs(f'{sim}/{m}')
        for f in glob.glob(f'{sim0}/{n}/piece_*.obj'):
            shutil.copy(f, f'{sim}/{m}/')
print(out)
