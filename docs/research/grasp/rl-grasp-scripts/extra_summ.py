"""Window summary of extra.py output for one object and hand: per link, share of frames near (within 2 cm), share in the
ring hole, dominant world side (above / below / side-on) and median lowest point relative to the table top (mm)."""
import sys, json
from collections import Counter, defaultdict
import numpy as np
path, obj, side, wins = sys.argv[1], sys.argv[2], sys.argv[3][0].upper(), sys.argv[4]
R = [json.loads(l) for l in open(path)]
for w in wins.split(','):
    f0, f1 = (int(x) for x in w.split('-')); rs = [r for r in R if f0 <= r['f'] < f1]; n = len(rs)
    if not n:
        continue
    acc = defaultdict(list)
    for r in rs:
        for k, v in r['obj'][obj]['links'].items():
            if k.startswith(side + ':'):
                acc[k.split(':')[1]].append(v)
    nz = np.median([r['obj'][obj]['nz'] for r in rs])
    parts = []
    for ln in sorted(acc, key=lambda k: -len(acc[k])):
        v = acc[ln]; near = len(v) / n
        if near < 0.3:
            continue
        hole = np.mean([x['in_hole'] >= 3 for x in v]) * near; sd = Counter(x['side'] for x in v).most_common(1)[0]
        z = np.median([x['zmin_mm'] for x in v])
        parts.append(f"{ln.replace('hand_C_MC','palm')}: near {near:.2f} hole {hole:.2f} {sd[0]}({sd[1] / len(v):.2f}) zmin {z:+.0f}mm")
    print(f'{w} (n {n}, plate normal z {nz:+.2f}):\n   ' + '\n   '.join(parts))
