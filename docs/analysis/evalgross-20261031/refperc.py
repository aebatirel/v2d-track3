#!/usr/bin/env python3
"""Reference-stage shifts: per reference object with a > 3 cm distance from its feeding perception, the window
(frames > 2 cm), the vertical part of the shift, and the depth verdict inside the window (depth-bad share and
median signed residual, reference vs perception). Inference side only.
Usage: python3 refperc.py MANIFEST_EVAL.json DEPTH_ROOT OUT.json   (run with the embreex/rtree pylib on PYTHONPATH)"""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import screen  # noqa: E402

man = {(m['ep'], m['kind']): m for m in json.load(open(sys.argv[1]))}
root, outp = sys.argv[2], sys.argv[3]
res = []
for (ep, kind), m in sorted(man.items()):
    if kind != 'ref':
        continue
    n, d, A, tz = screen.load_plane(m)
    names, O = screen.load_ref(m['ref'], A)
    pn, PO = screen.load_perc(m['poses']); PO = PO[:, [pn.index(x) for x in names]]
    zr = np.load(f'{root}/ref/ep{ep}/audit.npz'); zp = np.load(f'{root}/perc/ep{ep}/audit.npz')
    for b, nm in enumerate(names):
        me = screen.Mesh(nm, f"{m['meshes']}/{nm}.glb")
        c = O[:, b, :3, :3] @ me.com + O[:, b, :3, 3]; pc = PO[:, b, :3, :3] @ me.com + PO[:, b, :3, 3]
        dp = np.linalg.norm(c - pc, axis=1) * 100
        if dp.max() < 3:
            continue
        w = dp > 2

        def bad(z):
            hid = z['hidden'][:, b].astype(bool); val = z['valid'][:, b].astype(bool)
            return hid | (val & ((np.nan_to_num(z['behind'][:, b]) > 0.2) | (np.nan_to_num(z['front'][:, b]) > 0.5)))
        br, bp = bad(zr), bad(zp); idx = np.where(w)[0]; dz = ((c - pc) @ n) * 100
        res.append(dict(ep=ep, obj=nm, T=len(dp), refperc_max=round(float(dp.max()), 1), argmax=int(dp.argmax()),
                        n_gt2=int(w.sum()), n_gt3=int((dp > 3).sum()), window=[int(idx.min()), int(idx.max())],
                        vertical_shift_cm_at_max=round(float(dz[dp.argmax()]), 1),
                        depth_bad_ref_in_window=round(float(br[w].mean()), 2), depth_bad_perc_in_window=round(float(bp[w].mean()), 2),
                        med_r_ref=round(float(np.nanmedian(zr['med_r_cm'][w, b])), 2),
                        med_r_perc=round(float(np.nanmedian(zp['med_r_cm'][w, b])), 2)))
        print(res[-1])
json.dump(res, open(outp, 'w'), indent=1)
