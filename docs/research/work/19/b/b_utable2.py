# B30: compact union-depth table by contact type and direction (ranges over the states of that type), all variants.
import re, numpy as np
rx=re.compile(r'^(\S+)\s+ep(\d+)\s+f(\d+)\s+(\S+)\s+vs\s+(\S+)\s*: A-in-B per-hull\s+([\d.]+) union\s+([\d.]+) \| B-in-A per-hull\s+([\d.]+) union\s+([\d.]+)')
fx=re.compile(r'^W2floor\s+ep(\d+)\s+f(\d+)\s+(\S+)\s+vs\s+(\S+)\s*: W2A-in-W2B max\s+([\d.]+).*W2B-in-W2A max\s+([\d.]+)')
S={'white_pot_lid':'lid','white_pot':'pot','plastic_dish_rack':'rack','mini_sweeper':'sweeper','blue_cup':'blue','beige_cup':'beige'}
D={}; F={}; T={}
for fn in ['logs/uniondepth_V0V2.out','../../19-verify/uniondepth_V1.out','logs/uniondepth_C2all.out','../../19-verify/uniondepth_S120.out','logs/uniondepth_S60r120.out']:
    for l in open(fn):
        m=rx.match(l)
        if m: k=(m.group(2),m.group(3)); T[k]=(S[m.group(4)],S[m.group(5)]); D[(m.group(1),k)]=(float(m.group(7)),float(m.group(9)))
for fn in ['logs/eval_floors.out','logs/eval2_floors.out']:
    for l in open(fn):
        m=fx.match(l)
        if m: F[(m.group(1),m.group(2))]=(float(m.group(5)),float(m.group(6)))
labs=['floor','V0','V2','V1','C2all','S120','S60r120']
print('| contact (states) | '+' | '.join(labs)+' |'); print('|---'*(len(labs)+1)+'|')
groups={}
for k,(a,b) in T.items(): groups.setdefault((a,b),[]).append(k)
for (a,b),ks in groups.items():
    for di,nm in ((0,f'{a} in {b}'),(1,f'{b} in {a}')):
        cells=[]
        for L in labs:
            v=[F[k][di] if L=='floor' else D[(L,k)][di] for k in ks]
            cells.append(f'{min(v):.1f}-{max(v):.1f}' if len(v)>1 and min(v)!=max(v) else f'{v[0]:.1f}')
        print(f'| {nm} ({len(ks)}) | '+' | '.join(cells)+' |')
