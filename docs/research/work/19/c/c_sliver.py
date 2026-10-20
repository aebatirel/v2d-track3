# Smallest hull volumes per hull set (MuJoCo rejects meshes whose volume < mjMINVAL=1e-15 m^3 unless inertia="shell").
import sys, glob, numpy as np
from scipy.spatial import ConvexHull
sys.path.insert(0,'/Users/aebatirel/Documents/Code/v2d-research/work/19/b'); from common import load_hulls
for p in sys.argv[1:]:
    for f in sorted(glob.glob(p+'/*.npz')):
        hv=load_hulls(f); vol=[]
        for v in hv:
            try: vol.append(ConvexHull(v).volume)
            except Exception: vol.append(0.0)
        vol=np.array(vol); k=np.argsort(vol)[:3]
        print(f'{f.split("work/19/")[-1]:45s} n {len(hv):5d} min vol m3 {vol[k[0]]:.2e} (idx {k.tolist()}, {[f"{x:.1e}" for x in vol[k]]}) n<1e-12: {(vol<1e-12).sum()} n<1e-15: {(vol<1e-15).sum()}')
