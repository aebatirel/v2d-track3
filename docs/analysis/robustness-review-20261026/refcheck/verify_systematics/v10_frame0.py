"""V10 (verify_systematics): is our frame-0 pose worse than the frames after it? (Explains why part of the +0.5-frame
gain disappears when frame 0 is kept: the kit aligns the whole scene on frame 0.) No ground truth in the variants:
  f0=f1     frame 0 of every object replaced by frame 1
  f0=med3   frame 0 replaced by the chordal mean of frames 0..2 (rotation) and their median position
Scored in-process (v6_inproc.auc). Usage: python -I v10_frame0.py OUT.json"""
import json, os, sys
import numpy as np
from scipy.spatial.transform import Rotation as R
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vload import *  # noqa
import v2_scale_lag_tilt as V
import v6_inproc as S

out = {}
for ep in sorted(CE):
    if ep == 23:
        continue
    names, gt, _ = mocap(ep)
    d = ref_dir(ep); tfp = f'{d}/table_frame.npz' if d else f'{ST}/{V.STALE_TF.format(ep)}'
    Tt = np.load(tfp)['T_table_from_world']; P = perc(ep)
    srcs = {'perc': ({n: np.einsum('ij,tjk->tik', Tt, P[n]) for n in names}, V.LIB_PERC[ep])}
    if d:
        srcs['ref'] = (refparq(ref_final(ep)), V.LIB_REF[ep])
    out[ep] = {}
    for k, (ours, lib) in srcs.items():
        o1 = {n: ours[n].copy() for n in names}; o3 = {n: ours[n].copy() for n in names}
        for n in names:
            o1[n][0] = ours[n][1]
            o3[n][0, :3, 3] = np.median(ours[n][:3, :3, 3], 0)
            o3[n][0, :3, :3] = R.from_matrix(ours[n][:3, :3, :3]).mean().as_matrix()
        b = S.auc(ep, names, ours, gt, lib)
        out[ep][k] = {'0': b, 'f0=f1': S.auc(ep, names, o1, gt, lib), 'f0=med3': S.auc(ep, names, o3, gt, lib)}
    print(ep, out[ep], flush=True)
    json.dump(out, open(sys.argv[1], 'w'), indent=1)
for k in ('perc', 'ref'):
    rows = [v[k] for v in out.values() if k in v]
    print(k, len(rows), {L: (round(float(np.mean([r[L] - r['0'] for r in rows])), 4), sum(r[L] > r['0'] for r in rows)) for L in ('f0=f1', 'f0=med3')})
