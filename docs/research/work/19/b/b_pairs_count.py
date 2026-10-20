# [E] narrowphase load proxy: per GT contact state, number of (A hull, B hull) pairs with overlapping world AABBs and
# number of pairs that actually interpenetrate (any sampled point of one hull inside the other, depth > 0).
import sys, numpy as np, pandas as pd
sys.path.insert(0,'/Users/aebatirel/Documents/Code/v2d-research/work/19/b')
from b_eval import hulls, CASES, CASES2, C, T, tr, P
from scipy.spatial import ConvexHull
def run(lab,d,cases):
    for ep,f,a,b in cases:
        ha,hb=hulls(d,a),hulls(d,b)
        df=C(('p',ep),lambda: pd.read_parquet(P+'/data/chunk-000/episode_%06d.parquet'%ep)); fi=f if f>=0 else len(df)-1
        pose={x['name']:x['pose'] for x in df['observation.objects'].iloc[fi]}; Ma,Mb=T(pose[a]),T(pose[b])
        A=[tr(Ma,v) for v in ha]; B=[tr(Mb,v) for v in hb]
        Al=np.array([v.min(0) for v in A]); Ah=np.array([v.max(0) for v in A]); Bl=np.array([v.min(0) for v in B]); Bh=np.array([v.max(0) for v in B])
        ov=np.all((Al[:,None,:]<=Bh[None,:,:])&(Bl[None,:,:]<=Ah[:,None,:]),-1); I,J=np.nonzero(ov); pen=0
        for i,j in zip(I,J):
            e=ConvexHull(B[j]).equations
            if ((A[i]@e[:,:3].T+e[:,3]).max(1)<0).any(): pen+=1; continue
            e=ConvexHull(A[i]).equations
            if ((B[j]@e[:,:3].T+e[:,3]).max(1)<0).any(): pen+=1
        print(f'{lab:8s} ep{ep} f{fi} {a} vs {b}: hulls {len(A)}x{len(B)} aabb_pairs {len(I)} penetrating_pairs(vertex test) {pen}',flush=True)
for a in sys.argv[1:]:
    lab,d=a.split('='); run(lab,d,CASES2)
