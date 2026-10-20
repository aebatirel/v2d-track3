# Union/per-hull depth (v_uniondepth2 metric) for a subset of the 21 states whose objects all exist in the given dirs.
# usage: b_ud_sub.py LABEL=dir[,dir2] ...
import sys, os, numpy as np, pandas as pd
argv=sys.argv[1:]; sys.argv=['x']
sys.path.insert(0,'/Users/aebatirel/Documents/Code/v2d-research/work/19-verify'); import v_uniondepth2 as U
for arg in argv:
    lab,d=arg.split('=',1)
    for ep,f,a,b in U.CASES:
        A,Bo=U.obj(d,a),U.obj(d,b)
        if A is None or Bo is None: continue
        df=pd.read_parquet(U.P%ep); fi=f if f>=0 else len(df)-1
        pose={x['name']:x['pose'] for x in df['observation.objects'].iloc[fi]}; Ma,Mb=U.T(pose[a]),U.T(pose[b])
        ab=Bo.depth(U.tr(np.linalg.inv(Mb)@Ma,A.S)); ba=A.depth(U.tr(np.linalg.inv(Ma)@Mb,Bo.S))
        print(f'{lab:6s} ep{ep:<2d} f{fi:<4d} {a:13s} vs {b:17s}: A-in-B per-hull {ab[0].max():4.1f} union {ab[1].max():4.1f} | B-in-A per-hull {ba[0].max():4.1f} union {ba[1].max():4.1f}',flush=True)
