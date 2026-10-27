"""V9 (verify_systematics): cost of mkref's per-object z snap = AUC(e2s pre-contact-retarget reference) minus
AUC(canonical perception mapped by the same table frame), both scored with the REFERENCE's mesh library (same mesh),
in-process (v6_inproc.auc, parity-checked against pipeline/score_registered.py). By construction (V1) pre = T_tab @ perc
+ object_z_shift, so the difference is the snap (plus start-overlap lift, zero here). Also contact retarget (ref - pre).
Usage: python -I v9_snap.py OUT.json"""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vload import *  # noqa
import v2_scale_lag_tilt as V
import v6_inproc as S

out = {}
for ep in sorted(CE):
    d = ref_dir(ep)
    if not d:
        continue
    names, gt, _ = mocap(ep)
    tf = np.load(f'{d}/table_frame.npz'); Tt = tf['T_table_from_world']; P = perc(ep); lib = V.LIB_REF[ep]
    pc = {n: np.einsum('ij,tjk->tik', Tt, P[n]) for n in names}
    pre = refparq(f'{d}/e2s_reference.parquet'); fin = refparq(ref_final(ep))
    a = {k: S.auc(ep, names, v, gt, lib) for k, v in (('perc', pc), ('pre', pre), ('ref', fin))}
    a['snap'] = round(a['pre'] - a['perc'], 4); a['contact_retarget'] = round(a['ref'] - a['pre'], 4)
    a['z_shift_mm'] = dict(zip([str(x) for x in tf['names']], np.round(tf['object_z_shift'] * 1000, 1).tolist())); a['lib'] = lib
    out[ep] = a
    print(ep, a, flush=True)
    json.dump(out, open(sys.argv[1], 'w'), indent=1)
print('snap mean', round(float(np.mean([v['snap'] for v in out.values()])), 4), 'contact retarget mean',
      round(float(np.mean([v['contact_retarget'] for v in out.values()])), 4))
