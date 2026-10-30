"""(c) What SAM 3D's own layout would have given: the saved layout scale (gen_log) vs the [D] ideal metric scale, and
which raw canonical axis ends up on each scan PCA axis under the ideal placement (is SAM's canonical frame upright?)."""
import json, sys
import numpy as np
sys.path.insert(0, '/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad/diag/sam-placement')
from common import *  # noqa
log = {}
for l in open(f'{GEN}/sam3d/gen_log.jsonl'):
    r = json.loads(l)
    if r.get('ok'):
        log[(r['tag'], r['seed'])] = r
out = []
for l in open(f'{OUT}/decomp_before.jsonl'):
    d = json.loads(l)
    if d['model'] != 'sam3d':
        continue
    obj, seed = d['obj'], d['seed']
    rp, pp = gen_paths('sam3d', obj, seed)
    raw = load_mesh(rp)
    Tfit, _ = recover_T(raw, load_mesh(pp))
    A = (d['scale_A'], np.array(d['R']), np.array(d['t']))
    Tid = compose(A, Tfit)
    g = log[(f'{obj}_{TAG[obj]}', seed)]
    lay = g['scale'][0][0] if g.get('scale') else None
    V = np.array(d['scan_pca'])
    M = np.abs(V.T @ Tid[1])           # rows: scan long/mid/short, cols: raw x/y/z
    amap = ['xyz'[int(np.argmax(M[i]))] + f'({M[i].max():.2f})' for i in range(3)]
    rec = dict(obj=obj, seed=seed, s_ideal=Tid[0], s_fit=Tfit[0], layout_scale=lay,
               layout_over_ideal=(lay / Tid[0]) if lay else None, raw_axis_on_scan_LMS=amap,
               raw_extent=g['extent'])
    out.append(rec)
    print(json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in rec.items()}))
json.dump(out, open(f'{OUT}/layout_check.json', 'w'), indent=1)
