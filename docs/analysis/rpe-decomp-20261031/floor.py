"""ORACLE DIAGNOSTIC (public episodes only): the 'do-nothing' floor, i.e. every object held at its TRUE frame-0 pose
for the whole episode, scored with the kit metrics (alignment is then exact). It is the error of a benign failure
(nothing moved, nothing flung), to set beside the catastrophic rollout failures. Reads ground truth.
Usage: python -I floor.py RDLIB_DIR SCRATCH OUT_JSON"""
import json, sys
import numpy as np
sys.path.insert(0, sys.argv[1])
import rdlib as L
L.load_kit(f'{sys.argv[2]}/dl/kit/v2d_submission_kit'); t3 = f'{sys.argv[2]}/t3'; res = {}
for ep in L.PUBLIC:
    names = L.names_of(t3, ep)
    import pyarrow.parquet as pq
    T = pq.read_metadata(f'{t3}/ep{ep}.parquet').num_rows
    H = [L.host_geometry(t3, n, s) for s, n in enumerate(names)]
    G = L.ref_anchor(L.mocap7(t3, ep, names, T), H)
    m = L.metrics(np.repeat(G[:1], T, 0), G, H)
    res[str(ep)] = {k: round(m[k], 4) for k in ('AUC', 'MPPE', 'RPE')}
    print(ep, names, res[str(ep)], flush=True)
res['mean20'] = {k: round(float(np.mean([res[str(e)][k] for e in L.PUBLIC])), 4) for k in ('AUC', 'MPPE', 'RPE')}
print('mean20', res['mean20'])
json.dump(res, open(sys.argv[3], 'w'), indent=1)
