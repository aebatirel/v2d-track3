"""Automatic eval -> public twin mapping: object multiset match, constrained by episode-index bracketing
(public task_index is monotone in episode_index), plus frame counts from the global 'index' gaps."""
from c11 import *
import json
SYM = {"beige_cup": "continuous", "blue_cup": "continuous", "white_pot_lid": "continuous",
       "mini_sweeper": "2-fold", "wooden_piece_1": "2-fold", "wooden_piece_2": "2-fold",
       "plastic_dish_rack": "near-2-fold (15 mm)", "white_pot": "asymmetric", "water_pitcher": "asymmetric",
       "mini_dust_pan": "asymmetric", "wooden_spoon": "mirror (roll sign)"}
pub = {ep: load_episode(ep) for ep in PUBLIC}
nfr = {int(l.split()[0]): int(l.split()[1]) for l in open('eval_nframes.txt')}
ti = {ep: pub[ep]['task_index'] for ep in PUBLIC}
rows = []
for ev, objs in sorted(EVAL.items()):
    lo = max([p for p in PUBLIC if p < ev], default=None); hi = min([p for p in PUBLIC if p > ev], default=None)
    trange = (ti[lo] if lo is not None else 0, ti[hi] if hi is not None else 99)
    cands = [p for p in PUBLIC if sorted(pub[p]['names']) == sorted(objs) and trange[0] <= ti[p] <= trange[1]]
    task = pub[cands[0]]['task'] if cands else f"unknown (task_index {trange[0]}..{trange[1]}, not in public)"
    slot_same = [p for p in cands if pub[p]['names'] == objs]
    rows.append(dict(ev=ev, objs=objs, n=nfr.get(ev), bracket=(lo, hi), task=task, twins=cands, same_slot_order=slot_same,
                     slot0=objs[0], sym0=SYM[objs[0]], sym1=SYM[objs[1]] if len(objs) > 1 else None))
    print(f"ev{ev:2d} n={nfr.get(ev)} {objs} bracket={lo}-{hi} ti {trange} -> {task}; twins {cands} same-order {slot_same}; slot0 {objs[0]} [{SYM[objs[0]]}]")
json.dump(rows, open('s10_twins.json', 'w'), indent=1)
# global-index gaps: frames of non-public episodes between public ones
print()
for a, b in zip(PUBLIC[:-1], PUBLIC[1:]):
    if b - a > 1:
        gap = pub[b]['index'][0] - pub[a]['index'][-1] - 1
        between = list(range(a + 1, b)); ev = [x for x in between if x in EVAL]; miss = [x for x in between if x not in EVAL]
        print(f"gap {a}->{b}: {gap} frames; eval {ev} sum {sum(nfr[x] for x in ev)}; withheld {miss} -> {gap - sum(nfr[x] for x in ev)} frames")
