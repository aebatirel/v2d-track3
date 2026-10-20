import pandas as pd, numpy as np, sys
P='/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public/data/chunk-000/episode_%06d.parquet'
for e in [0,2,11,12,13,18,21,22,23,24,26,27,31,39,40,41,42,43,44,45]:
    df=pd.read_parquet(P%e); objs=df['observation.objects']
    names=[o['name'] for o in objs.iloc[0]]
    out=[]
    for k,n in enumerate(names):
        P0=np.array([o[k]['pose'] for o in objs]); V=np.array([o[k]['visible'] for o in objs])
        p=P0[:,:3]; z0=p[0,2]; zmin=np.min(p[V,2]); zend=p[-1,2]
        d=np.linalg.norm(p-p[0],axis=1)
        on1=int(np.argmax(d>0.01)) if (d>0.01).any() else -1
        on05=int(np.argmax(d>0.005)) if (d>0.005).any() else -1
        out.append(f"{k}:{n} z0={z0:.3f} zend={zend:.3f} zmin={zmin:.3f} vis0={V[0]} nvis={V.sum()}/{len(V)} on5mm={on05} on1cm={on1}")
    print(e, len(df), ' | '.join(out))
