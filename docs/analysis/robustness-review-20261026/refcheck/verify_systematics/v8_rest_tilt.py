"""V8 (verify_systematics): object tilt at rest vs mocap (my rest blocks from v5), and the kit-aligned vertical error of
the alignment anchor at rest (ep21/ep22 pitcher claim). Light CPU. Usage: python -I v8_rest_tilt.py OUT.json"""
import json, os, sys
import numpy as np
from scipy.spatial.transform import Rotation as R
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vload import *  # noqa
import v2_scale_lag_tilt as V
from v5_rest_height import blocks
from v2dlb import track3_pose as K

z = np.array([0, 0, 1.0])
out = {}; allt = []; between = []
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
        regs = [V.reg(ep, s, n, lib) for s, n in enumerate(names)]
        row = {}; ups = []
        for s, n in enumerate(names):
            g = gt[n]; pg = g[:, :3, :3] @ regs[s][2] + g[:, :3, 3]
            sp = np.r_[0, np.linalg.norm(np.diff(pg, axis=0), axis=1)] * 1000
            ang = np.r_[0, np.degrees(R.from_matrix(np.einsum('tji,tjk->tik', g[1:, :3, :3], g[:-1, :3, :3])).magnitude())]
            bl = blocks((sp < 1.0) & (ang < 0.5))
            if not bl:
                continue
            fr = np.unique(np.r_[bl[0], bl[-1]])
            Ro = np.einsum('tij,kj->tik', ours[n][fr, :3, :3], regs[s][1])        # our table frame <- scan body
            Rg = g[fr, :3, :3]
            uo = np.einsum('tji,j->ti', Ro, z); ug = np.einsum('tji,j->ti', Rg, z)
            t = np.degrees(np.arccos(np.clip((uo * ug).sum(1), -1, 1)))
            iu = np.einsum('tij,tkj,k->ti', Rg, Ro, z); iu = iu.mean(0); iu /= np.linalg.norm(iu); ups.append(iu)
            row[n] = dict(frames=int(len(fr)), tilt_deg_median=round(float(np.median(t)), 2))
            if k == 'ref' or not d:
                allt.append(float(np.median(t)))
        if len(ups) == 2:
            row['between_objects_deg'] = round(float(np.degrees(np.arccos(np.clip(ups[0] @ ups[1], -1, 1)))), 2)
            if k == 'ref' or not d:
                between.append(row['between_objects_deg'])
        out[ep][k] = row
    # kit-aligned vertical error of every object at its rest blocks (main source)
    k = 'ref' if d else 'perc'; ours, lib = srcs[k]
    regs = [V.reg(ep, s, n, lib) for s, n in enumerate(names)]
    from v6_inproc import host
    H = [host(n, s) for s, n in enumerate(names)]
    a = np.stack([np.c_[ours[n][:, :3, 3], R.from_matrix(ours[n][:, :3, :3]).as_quat()] for n in names], 1)[:, None].copy()
    r = np.stack([np.c_[gt[n][:, :3, 3], R.from_matrix(gt[n][:, :3, :3]).as_quat()] for n in names], 1)[:, None].copy()
    for s in range(len(names)):
        a[:, :, s] = K._convert_object_body(a[:, :, s], regs[s][0], regs[s][1])
        r[:, :, s, :3] += np.einsum('...ij,j->...i', K._rotation_matrix(r[:, :, s, 3:]), H[s]['anchor'])
    al = K._align_registered_scene(a, r, [h['axis'] for h in H])
    ve = {}
    for s, n in enumerate(names):
        dz = (al[:, 0, s, 2] - r[:, 0, s, 2]) * 1000
        ve[n] = dict(frame0_mm=round(float(dz[0]), 1), first20_median_mm=round(float(np.median(dz[:20])), 1),
                     last20_median_mm=round(float(np.median(dz[-20:])), 1))
    out[ep]['kit_aligned_vertical_error_' + k] = ve
    print(ep, json.dumps(out[ep]), flush=True)
out['_summary'] = dict(rest_tilt_median=float(np.median(allt)), rest_tilt_iqr=np.percentile(allt, [25, 75]).tolist(), n=len(allt),
                       between_objects_median=float(np.median(between)), n_between=len(between))
print(out['_summary'])
json.dump(out, open(sys.argv[1], 'w'), indent=1)
