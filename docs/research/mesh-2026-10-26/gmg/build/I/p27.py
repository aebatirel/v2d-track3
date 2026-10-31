"""P27a-c (PREREG F-I1.12) on a BI2 ep24 output folder (dev process on the clean bundle; GT-free).

  GMG_MODE=dev GMG_RUN=RUN python p27.py OUT_DIR BUNDLE_DIR CAND_DIR obj=cid,obj=cid
P27a entry-side share of the frame counts (sum of n_v over the carve side / over the component) >= 0.6 on both boards;
P27b (a, c) offset along the board's long axis <= 10 mm (centroid of the motion component vs the placed SAM 3D notch
component that overlaps it most); P27c >= 50 % of the motion component OBSERVED (falsified if < 20 %).
"""
import json
import os
import sys

import numpy as np
import trimesh
from scipy import ndimage

sys.path.insert(0, '/home/user/v2d-track3/docs/research/mesh-2026-10-26')
from gmg import guard, interlock as IL  # noqa: E402


def main():
    out_dir, bdir, cdir, picks = sys.argv[1:5]
    guard.set_run(os.environ['GMG_RUN'])
    picks = dict(kv.split('=') for kv in picks.split(','))
    b = IL.load_bundle_any(bdir)
    res = {}
    for obj, cid in picks.items():
        z = dict(np.load(os.path.join(out_dir, f'voxels_{obj}.npz')))
        g = IL.Grid(z['lo'], float(z['vox']), z['shape'])
        keys = sorted([k for k in z if k.startswith('comp') and k.endswith('_lin')], key=lambda k: -len(z[k]))
        if not keys:
            continue
        k = keys[0]
        lin, nv, reg = z[k], z[k.replace('_lin', '_nv')], z[k.replace('_lin', '_region')]
        share = float(nv[np.isin(lin, reg)].sum() / max(nv.sum(), 1))
        st = np.asarray(b.obs(obj)['state']).ravel()
        obs_share = float((st[lin] == 2).mean())
        m = trimesh.load(os.path.join(cdir, obj, f'{cid}.glb'), force='mesh')
        X = trimesh.sample.sample_surface(m, 30000, seed=0)[0]
        c = X.mean(0); U = np.linalg.svd(X - c, full_matrices=False)[2]
        CR = g.centres(lin)
        r = dict(component_voxels=int(len(lin)), carve_side_voxels=int(len(reg)), P27a_entry_share=round(share, 3),
                 P27c_observed_share=round(obs_share, 3))
        if 'gen_C_a' in z:
            ca = z['gen_C_a'].astype(bool)
            lab, n = ndimage.label(ca.reshape(g.shape), structure=np.ones((3, 3, 3)))
            lab = lab.ravel()
            if n:
                best = max(range(1, n + 1), key=lambda i: (np.isin(np.nonzero(lab == i)[0], lin).sum(), (lab == i).sum()))
                CA = g.centres(np.nonzero(lab == best)[0])
                dL = float(((CR.mean(0) - CA.mean(0)) @ U[0]))
                r.update(P27b_along_long_axis_mm=round(dL * 1e3, 1),
                         a_c_centroid_mm=round(float(np.linalg.norm(CR.mean(0) - CA.mean(0))) * 1e3, 1),
                         a_component_voxels=int((lab == best).sum()),
                         a_extent_long_mm=round(float(np.ptp((CA - c) @ U[0]) + g.vox) * 1e3, 1),
                         c_extent_long_mm=round(float(np.ptp((CR - c) @ U[0]) + g.vox) * 1e3, 1))
        res[obj] = r
    res['P27a_pass'] = all(v['P27a_entry_share'] >= 0.6 for v in res.values() if isinstance(v, dict) and
                           'P27a_entry_share' in v)
    res['P27b_pass'] = all(abs(v.get('P27b_along_long_axis_mm', 1e9)) <= 10 for v in res.values()
                           if isinstance(v, dict) and 'component_voxels' in v)
    res['P27c'] = {o: ('pass' if v['P27c_observed_share'] >= 0.5 else 'falsified' if v['P27c_observed_share'] < 0.2
                       else 'neither') for o, v in res.items() if isinstance(v, dict) and 'P27c_observed_share' in v}
    print(json.dumps(res, indent=1))


if __name__ == '__main__':
    main()
