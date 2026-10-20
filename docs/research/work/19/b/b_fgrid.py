# Save the W2 field grids (float32, + outside, metres) for fast inside/depth queries by trilinear interpolation.
import sys, numpy as np; sys.path.insert(0,'/Users/aebatirel/Documents/Code/v2d-research/work/19/b'); from b_field import *
for n in sys.argv[1:]:
    f,lo=w2_field(n,1e-3,3e-3); np.savez(f'FG/{n}.npz',f=(f-0.3e-3).astype(np.float32),lo=lo,h=1e-3); print(n,f.shape,flush=True)
