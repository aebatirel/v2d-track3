import sys, numpy as np; sys.path.insert(0,'/Users/aebatirel/Documents/Code/v2d-research/work/19/b')
from common import *; from scipy.spatial import ConvexHull
for a in sys.argv[1:]:
    lab,d=a.split('=')
    for n in ['white_pot_lid','white_pot','mini_sweeper','plastic_dish_rack','blue_cup','beige_cup']:
        import os
        if not os.path.exists(f'{d}/{n}.npz'): continue
        dev=[]
        for v in load_hulls(f'{d}/{n}.npz'):
            c=cap_hull(v); e=ConvexHull(c).equations; full=v[ConvexHull(v).vertices]; dev.append(((full@e[:,:3].T+e[:,3]).max(1)).max()*1e3)
        print(f'{lab} {n:18s} cap64 loss mm: median {np.median(dev):.2f} p90 {np.percentile(dev,90):.2f} max {np.max(dev):.2f}',flush=True)
