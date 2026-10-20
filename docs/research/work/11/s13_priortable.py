"""Eval -> public-twin prior table. For each eval episode: twins (s10), slot-0 symmetry, and candidate yaw priors for
the slot-0 object computed from the twins: (abs) world yaw, (rel) yaw minus co-object yaw, (brg) yaw minus bearing
slot0->co-object (world-free AND co-object-frame-free). Spread = circular rms over twins; 'pairdiff' = |difference|
between the two twins (a LOO error proxy). Research only; uses public GT only."""
from c11 import *
import json
tw = {r['ev']: r for r in json.load(open('s10_twins.json'))}
SYM = {"beige_cup": 0, "blue_cup": 0, "white_pot_lid": 0, "mini_sweeper": 2, "wooden_piece_1": 2, "wooden_piece_2": 2,
       "plastic_dish_rack": 2, "white_pot": 1, "water_pitcher": 1, "mini_dust_pan": 1, "wooden_spoon": -1}
pub = {ep: load_episode(ep) for ep in PUBLIC}
def circ(v):
    v = np.asarray(v, float); m = np.degrees(np.angle(np.exp(1j * np.radians(v)).mean()))
    return float(m), float(np.sqrt(np.mean(wrap(v - m) ** 2)))
def qty(ep, a, b):
    e = pub[ep]; p = e['pose'][0]; nm = e['names']; ia = nm.index(a)
    ya, ta = yaw_tilt(p[ia, 3:], a); out = dict(abs=float(ya))
    if b is not None:
        ib = nm.index(b); yb, _ = yaw_tilt(p[ib, 3:], b); d = p[ib, :2] - p[ia, :2]
        out.update(rel=float(wrap(ya - yb)), brg=float(wrap(ya - np.degrees(np.arctan2(d[1], d[0])))), dist=float(np.linalg.norm(d)))
    return out
take = {ep: NOTES[ep] for ep in PUBLIC}
rows = []
for ev, r in sorted(tw.items()):
    objs = r['objs']; a = objs[0]; b = objs[1] if len(objs) > 1 else None
    row = dict(ev=ev, task=r['task'], twins=r['twins'], takes=[take[t] for t in r['twins']], slot0=a, sym0=SYM[a],
               slot1=b, sym1=SYM.get(b), order_same=bool(r['same_slot_order']))
    if r['twins'] and b is not None:
        Q = [qty(t, a, b) for t in r['twins']]
        for k in ('abs', 'rel', 'brg'):
            m, s = circ([q[k] for q in Q]); row[k] = dict(vals=[round(q[k], 1) for q in Q], mean=round(m, 1), rms=round(s, 1),
                pairdiff=round(abs(float(wrap(Q[0][k] - Q[1][k]))), 1) if len(Q) > 1 else None)
        row['dist_cm'] = [round(q['dist'] * 100, 1) for q in Q]
        # same for slot-1 if it is symmetric (lid, cups, 2-fold)
        if SYM[b] in (0, 2):
            Q1 = [qty(t, b, a) for t in r['twins']]
            for k in ('rel', 'brg'):
                m, s = circ([q[k] for q in Q1]); row['slot1_' + k] = dict(vals=[round(q[k], 1) for q in Q1], mean=round(m, 1), rms=round(s, 1))
    elif r['twins']:
        Q = [qty(t, a, None) for t in r['twins']]; m, s = circ([q['abs'] for q in Q])
        row['abs'] = dict(vals=[round(q['abs'], 1) for q in Q], mean=round(m, 1), rms=round(s, 1))
    rows.append(row)
    print(ev, r['task'][:22], 'twins', r['twins'], row['takes'], 'slot0', a, 'sym', SYM[a], 'same-order', row['order_same'],
          {k: row[k] for k in ('abs', 'rel', 'brg', 'dist_cm', 'slot1_rel', 'slot1_brg') if k in row})
json.dump(rows, open('s13_priortable.json', 'w'), indent=1)
