import re, collections
L={'white_pot_lid':189.7,'white_pot':358.0,'mini_sweeper':144.0,'plastic_dish_rack':510.2,'blue_cup':172.3,'beige_cup':169.9}
R=collections.defaultdict(dict)
for f in ['logs/eval_obj_V0V1.out','logs/eval_obj_V2.out','logs/eval_obj_split.out']:
    for l in open(f):
        m=re.match(r'(\S+)\s+(\S+)\s+hulls\s+(\d+).*hull-vs-scan mm p95\s+[\d.]+ p99\s+([\d.]+) max\s+([\d.]+) \| hull-vs-W2 p99\s+([\d.]+) max\s+([\d.]+)',l)
        if m: R[m.group(2)][m.group(1)]=f'{m.group(3)} / {m.group(6)} / {m.group(7)}'
for n,l in L.items():
    print(f'| {n} | {l:.0f} | {0.025*l:.1f} | '+' | '.join(R[n].get(v,'-') for v in ['V0','V2','V1','S120','S60'])+' |')
