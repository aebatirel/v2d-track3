"""V1: is the canonical reference built from the canonical perception (pre = T_tab @ perc + z shift)? Frame counts.
Usage: python -I v1_consistency.py OUT.json"""
import json, sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vload import *  # noqa

out = {}
for ep in sorted(CE):
    names, gt, fidx = mocap(ep)
    P = perc(ep)
    row = dict(mocap_rows=len(fidx), frame_index_0_to_T=bool((fidx == np.arange(len(fidx))).all()),
               perc_frames={n: len(P[n]) for n in names})
    d = ref_dir(ep)
    if d:
        tf = np.load(f'{d}/table_frame.npz'); Tt = tf['T_table_from_world']; sh = tf['object_z_shift']
        pre = refparq(f'{d}/e2s_reference.parquet'); fin = refparq(ref_final(ep))
        row['pre_frames'] = {n: len(pre[n]) for n in names}; row['final_frames'] = {n: len(fin[n]) for n in names}
        row['object_z_shift_mm'] = dict(zip([str(x) for x in tf['names']], np.round(sh * 1000, 1).tolist()))
        cmp = {}
        for b, n in enumerate(names):
            Mp = np.einsum('ij,tjk->tik', Tt, P[n]); Mp[:, 2, 3] += sh[list(tf['names']).index(n)]
            dp = np.linalg.norm(Mp[:, :3, 3] - pre[n][:, :3, 3], axis=1) * 1000
            dr = np.degrees(np.arccos(np.clip((np.einsum('tij,tij->t', Mp[:, :3, :3], pre[n][:, :3, :3]) - 1) / 2, -1, 1)))
            df_ = np.linalg.norm(fin[n][:, :3, 3] - pre[n][:, :3, 3], axis=1) * 1000
            dfr = np.degrees(np.arccos(np.clip((np.einsum('tij,tij->t', fin[n][:, :3, :3], pre[n][:, :3, :3]) - 1) / 2, -1, 1)))
            cmp[n] = dict(pre_vs_perc_pos_mm_max=round(float(dp.max()), 3), pre_vs_perc_rot_deg_max=round(float(dr.max()), 3),
                          final_vs_pre_pos_mm=[round(float(np.median(df_)), 2), round(float(df_.max()), 2)],
                          final_vs_pre_rot_deg=[round(float(np.median(dfr)), 2), round(float(dfr.max()), 2)])
        row['compare'] = cmp
    out[ep] = row
    print(ep, json.dumps(row), flush=True)
json.dump(out, open(sys.argv[1], 'w'), indent=1)
