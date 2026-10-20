# Where does the S120 pot hull union leave W2-solid pixels uncovered in the 30 mm slice? (diagnostic for c_cavity)
import sys, numpy as np
sys.path.insert(0,'/Users/aebatirel/Documents/Code/v2d-research/work/19/c'); sys.argv=['x','white_pot']
import importlib.util
spec=importlib.util.spec_from_file_location('cc','/Users/aebatirel/Documents/Code/v2d-research/work/19/c/c_cavity.py')
src=open(spec.origin).read().replace('\nmain()\n','\n'); cc={}; exec(src,cc)
from common import load_hulls
d=np.load(cc['FG']+'/white_pot.npz'); f,lo,h=d['f'],d['lo'],float(d['h'])
X=[lo[i]+h*np.arange(f.shape[i]) for i in range(3)]
for lab,hd in [('S120','b/V4_120'),('S60','b/V4_60'),('V1','b/V1')]:
    H=cc['hull_eqs'](load_hulls(f'{hd}/white_pot.npz'))
    for xmm in np.arange(-15,40,1.0):
        k=int(np.argmin(np.abs(X[0]*1e3-xmm)))
        G=np.stack(np.meshgrid([X[0][k]],X[1],X[2],indexing='ij'),-1).reshape(-1,3)
        w=(f[k]<0).reshape(-1); o=cc['occ'](G,H,pad=float(sys.argv[1]) if False else 2e-6); unc=w&~o
        if unc.sum(): 
            P=G[unc]*1e3; print(lab,f'x={X[0][k]*1e3:.1f}mm uncovered W2 pixels {unc.sum()} e.g. y,z mm', np.round(P[:4,1:],1).tolist())
