"""Cheap CPU test of the mapping check's untested hypothesis H-freeze, on the objects it names (ep11 blue cup,
ep12 rack, ep31 rack): replace the object's REFERENCE path by a constant pose and rescore R (reference vs mocap)
and S (the stored sims against the frozen reference). T does not change (same sims).
Variants: f0 = frame-0 pose held; med = median position + frame-0 orientation.
Caveat: the objects are chosen with knowledge of the truth (they rest in the mocap); a GT-free trigger
(no hand contact in the reference) is not implemented here. Diagnostic only."""
import collections, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import myscore as M

rows = [json.loads(l) for l in open(f'{M.SP}/work/verify_mapping/all.jsonl')]
rows = [r for r in rows if 'error' not in r and r['lib'] != 'scan']
out = {}
for ep, obj in ((11, 'blue_cup'), (12, 'plastic_dish_rack'), (31, 'plastic_dish_rack')):
    names = M.gt(ep)[0]; b = names.index(obj)
    groups = collections.defaultdict(list)
    for r in rows:
        if r['ep'] == ep:
            groups[(r['ref_digest'], r['lib'])].append(r)
    for (rd, lib), g in groups.items():
        g = sorted(g, key=lambda r: -r['S'])[:12]
        fr, sim0, ref, _, _ = M.read_rollout(f"{M.SP}/store/{g[0]['path']}", names)
        res = dict(n=len(g), R=M.registered(ep, lib, ref, fr), S_mean=round(float(np.mean([r['S'] for r in g])), 4))
        for v in ('f0', 'med'):
            rf = ref.copy()
            if v == 'f0':
                rf[:, b] = ref[0, b]
            else:
                rf[:, b, :3] = np.median(ref[:, b, :3], axis=0); rf[:, b, 3:] = ref[0, b, 3:]
            Rf = M.registered(ep, lib, rf, fr)
            Sf = []
            for r in g:
                _, sim, _, _, _ = M.read_rollout(f"{M.SP}/store/{r['path']}", names)
                Sf.append(M.sim_vs_ref(sim, rf, per_object=True))
            res[v] = dict(R=Rf[0], R_obj=Rf[1][obj], S_mean=round(float(np.mean([s[0] for s in Sf])), 4),
                          S_obj_mean=round(float(np.mean([s[1][b] for s in Sf])), 4))
        res['R_obj_orig'] = res['R'][1][obj]; res['S_obj_orig'] = round(float(np.mean([r['S_obj'][obj] for r in g])), 4)
        res['T_mean'] = round(float(np.mean([r['T'] for r in g])), 4)
        out[f'ep{ep} {obj} {rd[:6]} {lib}'] = res
        print(ep, obj, rd[:6], lib, json.dumps(res), flush=True)
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'freeze_test.json'), 'w'), indent=1)
