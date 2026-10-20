# Build the Stage B markdown matrix from eval logs (first + second set).
import re, collections
V=collections.OrderedDict([('W2floor','floor'),('V0','V0'),('V2','V2'),('V1','V1'),('S120','S120'),('S60r120','S60r120'),('S60','S60')])
files=['logs/eval_floors.out','logs/eval_pairs_V0.out','logs/eval_pairs_V2.out','logs/eval_pairs_V1.out','logs/eval_pairs_S120.out',
       'logs/eval_pairs_S60r120.out','logs/eval_pairs_S60.out','logs/eval2_floors.out','logs/eval2_pairs.out','logs/eval2_pairs_S60r120.out','logs/eval2_pairs_S60.out']
D=collections.OrderedDict(); short={'white_pot_lid':'lid','white_pot':'pot','mini_sweeper':'sweeper','plastic_dish_rack':'rack','blue_cup':'blue','beige_cup':'beige'}
for f in files:
    try: L=open(f).read().splitlines()
    except FileNotFoundError: continue
    for l in L:
        m=re.match(r'(\S+)\s+ep(\d+)\s+f(\d+)\s+(\S+)\s+vs\s+(\S+?)\s*:\s+\S+-in-\S+ max\s+([\d.]+)',l)
        if m and m.group(1) in V:
            k=f'ep{m.group(2)} f{m.group(3)} {short[m.group(4)]} in {short[m.group(5)]}'; D.setdefault(k,{})[m.group(1)]=m.group(6)
for k,r in D.items(): print('| '+k+' | '+' | '.join(r.get(v,'-') for v in V)+' |')
