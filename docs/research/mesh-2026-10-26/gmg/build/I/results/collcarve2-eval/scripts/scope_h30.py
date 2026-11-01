"""Eval carve-scope check of the Eval-carves step (task condition (iii)): per eval pair, the H30 frames that pass the
pose precheck (no fail in (a) table, (b) float/support, (c) faithful overlap >= 1 cm3) AND where the PACKED colliders
block (packed-vs-packed overlap >= 1 cm3, or guest visual inside the receiver's packed pieces but outside its visual
>= 1 cm3). Such a frame is 'packed collider blocks a feasible pose'. From the evalcheck per-frame records only.
Usage: python -I scope_h30.py EVALCHECK_DIR OUT.json"""
import json, os, sys
import numpy as np
ev, outp = sys.argv[1], sys.argv[2]
OV = 1.0
res = {}
for ep in ['32', '33', '14', '16', '30', '15', '10', '1']:          # owner priority order
    fr = json.load(open(os.path.join(ev, 'per_frame', f'ep{ep}_frames.json')))
    R, P = fr['per_frame']['rows'], fr['per_frame']['pair']
    g = lambda k: np.array([p[k] for p in P], float)
    Vf, Vp, only = g('V_faithful'), g('V_packed'), g('V_gvis_in_rpk_only')
    r = {}
    for key in ('H30', 'H0', 'all'):
        sel = np.array([True if key == 'all' else x[key] for x in R])
        feas = sel & np.array([not x['fails'] for x in R])
        blk = feas & ((Vp >= OV) | (only >= OV))
        r[key] = dict(frames=int(sel.sum()), feasible=int(feas.sum()), feasible_and_packed_blocks=int(blk.sum()),
                      frames_list=[int(i) for i in np.nonzero(blk)[0]][:60],
                      max_V_packed_feasible_cm3=round(float(Vp[feas].max()), 3) if feas.any() else None,
                      max_V_rpk_only_feasible_cm3=round(float(only[feas].max()), 3) if feas.any() else None)
    res[ep] = r
    print(ep, {k: (v['frames'], v['feasible'], v['feasible_and_packed_blocks'], v['max_V_packed_feasible_cm3'],
                   v['max_V_rpk_only_feasible_cm3']) for k, v in r.items()})
json.dump(dict(_note=__doc__.split('Usage')[0].strip(), threshold_cm3=OV, episodes=res), open(outp, 'w'), indent=1)
