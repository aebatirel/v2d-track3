# Aggregate logs/eval_pairs_*.out into a variant x case matrix of hullA-in-hullsB max depth (mm).
import sys, re, glob, collections
rows=collections.OrderedDict(); cols=[]
for f in sys.argv[1:]:
    for l in open(f):
        m=re.match(r'(\S+)\s+ep(\d+)\s+f(\d+)\s+(\S+)\s+vs\s+(\S+?)\s*:\s+\S+-in-\S+ max\s+([\d.]+)',l)
        if not m: continue
        lab,ep,fr,a,b,d=m.groups(); c=f'{ep}/{fr}'
        if c not in cols: cols.append(c)
        rows.setdefault(lab,{})[c]=float(d)
print('variant   '+' '.join(f'{c:>7s}' for c in cols))
for lab,r in rows.items(): print(f'{lab:9s} '+' '.join(f'{r[c]:7.1f}' if c in r else '      -' for c in cols))
