"""DIAGNOSTIC (post hoc, report only, never delivered; written 23:50 UTC 31 Oct after the n1 smoke; needs dbg_wall.pkl from
fi517_diag_n1_inputs.py in the cwd): n1's carve with the trim options disabled for wall pieces,
and the residual guest-in-host overlap at T_rest for the rule's carve and the diagnostic one."""
import os, sys, pickle, math, json
os.environ.setdefault('GMG_MODE', 'dev')
sys.path.insert(0, '/home/user/v2d-track3/docs/research/mesh-2026-10-26'); sys.path.insert(0, '/home/user/v2d-track3/docs/research/mesh-2026-10-26/gmg/tests')
import numpy as np
from gmg import cavpieces as CP, collcarve as CC, simphys as PH
import test_collcarve2 as T2
d = pickle.load(open('dbg_wall.pkl', 'rb'))
Kf, Kfull, carved, default = d['Kf'], d['Kfull'], d['carved'], d['default']
host = T2.T1.cup()
P = CP.Profile2(host, *T2.AXIS, 0.001)
b = T2.T1.episode(host, T2.T1.cup(rb=T2.RB_G), lambda f: np.eye(4), 4, [], jitter=False)
ev = CP.IL if False else None
lay = CP.build_layout(P, 12, 'b1', {})
forced = CP.carved_heights(P, lay, Kf); lay2 = CP.forced_layout(P, lay, forced)
orig = CP._options2
def no_trim(prof, p, Q, wk):
    o = orig(prof, p, Q, wk)
    return [x for x in o if not (p['kind'] == 'wall' and x[0].startswith('trim'))] or o
CP._options2 = no_trim
lay3, rep = CP.carve2(P, lay2, Kf)
CP._options2 = orig
hl = CP.layout_hulls(P, lay3)
wi = CC.wall_integrity(default, hl, Kf, K_full=Kfull)
tp = CC.topology_1mm(default, hl)
T_rest = np.array(d['comps'][0]['T_rest'])
guest = T2.routes(b, dict(B=T2.T1.cup(rb=T2.RB_G)), dict(B=T2.AXIS))['B']['hulls']
Xg, cell = PH.guest_samples(guest)
ov = lambda H: PH.overlap(PH.eqs(H), Xg @ T_rest[:3, :3].T + T_rest[:3, 3], cell)
out = dict(rule_carve=dict(options=d['carve']['lathe']['options'], wall=d['caps']['wall'], overlap_at_rest_cm3=round(ov(carved), 3)),
           widen_only_diag=dict(options=rep['options'], removed=rep['removed_pieces'], wall=wi, topology=tp, overlap_at_rest_cm3=round(ov(hl), 3)),
           default_overlap_at_rest_cm3=round(ov(default), 3), K_fragments=len(Kf), R_voxels=d['comps'][0].get('R_voxels'),
           note='DIAGNOSTIC (post hoc, report only, never delivered)')
print(json.dumps(out, indent=1, default=str)[:3000])
json.dump(out, open('dbg_wall3.json', 'w'), indent=1, default=str)
# S (16 copies, the F-I5.5 setup) on the rule's carve and on the widen-only diagnostic carve at the n1 S frames
bb, M = T2.nest_case()
gB = T2.routes(bb, dict(B=M['B']), dict(B=T2.AXIS))['B']['hulls']
gp = CP.exact_props(gB, 0.3)
tb = (np.asarray(bb.meta['table']['n']), float(bb.meta['table']['d']))
rows = {}
for f in (81, 62):
    Wr = CC._world(bb, 'A', f); Wg = CC._world(bb, 'B', f)
    for name, H in (('rule_carve', carved), ('widen_only_diag', hl)):
        r = CC.sink_test2(H, gB, Wr, Wg, tb, gp, copies=16)
        rows[f'{name}@{f}'] = {k: v for k, v in r.items() if k != 'per_copy'}
        print(name, f, rows[f'{name}@{f}'])
out['S_diag'] = rows
json.dump(out, open('dbg_wall3.json', 'w'), indent=1, default=str)
