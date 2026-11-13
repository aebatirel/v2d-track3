"""M7 [D]: kit-like static ADD (my re-implementation of _register_object_body + mesh_metric add_static, 3 seeds: the
first eval seed of the object is not used; seeds 11, 22, 33) for placed SAM meshes from several placement methods.
No CD-O, no selection. Usage: m7_kitlike.py OUT.jsonl label=dir ..."""
import sys, json
import numpy as np
from vlib import *
from m6_regdep import kit_like_register, add_static, SYM
out = sys.argv[1]
with open(out, 'a') as fo:
    for spec in sys.argv[2:]:
        lab, d = spec.split('=')
        for obj in EPS:
            sv, sf = load_scan(obj); kind = SYM.get(obj)
            axis = sym_axis(sample(sv, sf, 6000, 14), kind) if kind else None
            q = sample(sv, sf, 500, 0)
            for seed in (42, 7):
                p = f'{d}/{obj}_{KTAG[obj]}_s{seed}.ply'
                if not os.path.exists(p): continue
                v, f = load(p)
                adds, rots = [], []
                for s in (11, 22, 33):
                    da, R, rc = kit_like_register(v, f, sv, sf, s)
                    adds.append(add_static(da, R, q - rc, kind, axis) * 1e3)
                    rots.append(rot_angle(R) if kind != 'axial' else math.degrees(math.acos(np.clip((R @ axis) @ axis, -1, 1))))
                rec = dict(label=lab, obj=obj, seed=seed, add_mean=round(float(np.mean(adds)), 1), adds=[round(a, 1) for a in adds],
                           flips=int(sum(r > 90 for r in rots)))
                print(json.dumps(rec), flush=True); fo.write(json.dumps(rec) + '\n')
