# B25: union-depth table (both directions) from v_uniondepth2 outputs + W2 floors; cause split per state:
#   prep term = V2 - V1 (identical W2 geometry, voxel preprocessing on vs off); concavity term = V1 - floor.
import re, sys, numpy as np
rx=re.compile(r'^(\S+)\s+ep(\d+)\s+f(\d+)\s+(\S+)\s+vs\s+(\S+)\s*: A-in-B per-hull\s+([\d.]+) union\s+([\d.]+) \| B-in-A per-hull\s+([\d.]+) union\s+([\d.]+)')
fx=re.compile(r'^W2floor\s+ep(\d+)\s+f(\d+)\s+(\S+)\s+vs\s+(\S+)\s*: W2A-in-W2B max\s+([\d.]+).*W2B-in-W2A max\s+([\d.]+)')
D={}; order=[]
for fn in ['logs/uniondepth_V0V2.out','../../19-verify/uniondepth_V1.out','../../19-verify/uniondepth_S120.out']:
    for l in open(fn):
        m=rx.match(l)
        if not m: continue
        lab,ep,f,a,b=m.group(1),int(m.group(2)),int(m.group(3)),m.group(4),m.group(5); k=(ep,f,a,b)
        if k not in order: order.append(k)
        D[(lab,k)]=(float(m.group(7)),float(m.group(9)))
F={}
for fn in ['logs/eval_floors.out','logs/eval2_floors.out']:
    for l in open(fn):
        m=fx.match(l)
        if m: F[(int(m.group(1)),int(m.group(2)),m.group(3),m.group(4))]=(float(m.group(5)),float(m.group(6)))
print('| GT state | dir | floor | V0 | V2 | V1 | S120 | prep (V2-V1) | concavity (V1-floor) |'); print('|---|---|---|---|---|---|---|---|---|')
P={0:[],1:[]}; Cc={0:[],1:[]}; X={0:[],1:[]}
for k in order:
    ep,f,a,b=k; sa,sb=a.replace('white_pot_lid','lid').replace('white_pot','pot').replace('plastic_dish_rack','rack').replace('mini_sweeper','sweeper'),b.replace('white_pot_lid','lid').replace('white_pot','pot').replace('plastic_dish_rack','rack').replace('mini_sweeper','sweeper')
    for di,nm in ((0,f'{sa} in {sb}'),(1,f'{sb} in {sa}')):
        fl=F[k][di]; v=[D[(L,k)][di] for L in ('V0','V2','V1','S120')]
        P[di].append(v[1]-v[2]); Cc[di].append(v[2]-fl); X[di].append(v[3]-fl)
        print(f'| ep{ep} f{f} | {nm} | {fl:.1f} | {v[0]:.1f} | {v[1]:.1f} | {v[2]:.1f} | {v[3]:.1f} | {v[1]-v[2]:+.1f} | {v[2]-fl:+.1f} |')
for di in (0,1):
    p,c,x=map(np.array,(P[di],Cc[di],X[di]))
    print(f'dir {"A-in-B" if di==0 else "B-in-A"} n{len(p)}: prep median {np.median(p):+.1f} range {p.min():+.1f}..{p.max():+.1f} | concavity median {np.median(c):+.1f} range {c.min():+.1f}..{c.max():+.1f} | S120-floor median {np.median(x):+.1f} range {x.min():+.1f}..{x.max():+.1f}')
