import numpy as np, sys
d=np.load('/Users/aebatirel/Documents/Code/v2d-research/work/19/b/FG/plastic_dish_rack.npz'); f,lo=d['f'],d['lo']; S=f<0
base=np.where(S.any((1,2)))[0].min()
for hx in [int(a) for a in sys.argv[1:]]:
    k=base+hx; sl=S[k]; print(f'--- height {hx} mm above base: rows=y (3 mm), cols=z (3 mm)')
    for j in range(0,sl.shape[0],3):
        print(''.join('#' if sl[j:j+3,kk:kk+3].any() else '.' for kk in range(0,sl.shape[1],3)))
