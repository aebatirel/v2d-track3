"""verify_timing: decisive quaternion-order test (27 Oct 2026). A resting cup's symmetry axis must be vertical in the
mocap world (z up). Angles between rest poses are blind to a fixed permutation of quaternion components, so this
test uses the absolute orientation instead. Usage: python -I vt_quat.py"""
import sys, os
import numpy as np, pyarrow.parquet as pq
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vt_load as L
from vt_lag import principal_axis
for ep, n in ((11, 'blue_cup'), (11, 'beige_cup'), (12, 'blue_cup'), (13, 'blue_cup'), (21, 'blue_cup'), (22, 'blue_cup')):
    tab = pq.read_table(f'{L.T3}/ep{ep}.parquet', columns=['observation.objects']).to_pandas()
    Q = np.stack([np.asarray([o for o in r if str(o['name']) == n][0]['pose'], float) for r in tab['observation.objects']])
    ax = principal_axis(L.scan_mesh(n))
    res = {}
    for lab, idx in (('w-first (correct)', [3, 4, 5, 6]), ('read as xyzw', [6, 3, 4, 5]), ('w last-swap', [4, 5, 6, 3])):
        R = L.quat_wxyz_to_R(Q[:5, idx])
        res[lab] = round(float(np.abs((R @ ax)[:, 2]).mean()), 3)
    print(ep, n, 'z height', round(float(Q[0, 2]), 3), '|axis . z| at rest:', res)
