"""V7 (verify_systematics): ORACLE (uses mocap) anchor-only frame-0 tilt removal on all public paths, in-process AUC
(v6_inproc.auc, parity-checked against pipeline/score_registered.py). Compares with the other agent's 'tilt' oracle
(a rest-averaged constant tilt removed from every object). The anchor is the kit's alignment object (first object
without a symmetry axis; else object 0, whose symmetry axis the kit uses). Usage: python -I v7_tilt_anchor.py OUT.json"""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vload import *  # noqa
import v2_scale_lag_tilt as V
import v6_inproc as S
from v4_make_npz import tilt_anchor

out = {}
for ep in sorted(CE):
    names, gt, _ = mocap(ep)
    d = ref_dir(ep); tfp = f'{d}/table_frame.npz' if d else f'{ST}/{V.STALE_TF.format(ep)}'
    Tt = np.load(tfp)['T_table_from_world']; P = perc(ep)
    srcs = {'perc': ({n: np.einsum('ij,tjk->tik', Tt, P[n]) for n in names}, V.LIB_PERC[ep])}
    if d:
        srcs['ref'] = (refparq(ref_final(ep)), V.LIB_REF[ep])
    out[ep] = {}
    for k, (ours, lib) in srcs.items():
        o, an, ang = tilt_anchor(ep, names, ours, gt, lib)
        b = S.auc(ep, names, ours, gt, lib); t = S.auc(ep, names, o, gt, lib)
        out[ep][k] = dict(anchor=an, tilt_removed_deg=round(ang, 2), base=b, tiltA=t, delta=round(t - b, 4))
    print(ep, out[ep], flush=True)
    json.dump(out, open(sys.argv[1], 'w'), indent=1)
for k in ('perc', 'ref'):
    v = [out[e][k]['delta'] for e in out if k in out[e] and e != 23]
    print(k, len(v), 'mean delta', round(float(np.mean(v)), 4), 'median', round(float(np.median(v)), 4), 'better', sum(x > 0 for x in v))
