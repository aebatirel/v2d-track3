# Verify C2 independently: slot-0 pre-onset perturbation, noise floor, and the BIAS of window-averaged anchors vs GT f0.
import pandas as pd, numpy as np
from scipy.spatial.transform import Rotation as R
D='/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public/data/chunk-000/episode_%06d.parquet'
def mean_err(P, sl):
    # chordal mean of rotations + mean translation over window sl; error vs frame 0
    q=R.from_quat(P[sl][:,[4,5,6,3]]); m=q.mean(); t=P[sl,:3].mean(0)
    return np.linalg.norm(t-P[0,:3])*1000, np.degrees((R.from_quat(P[0,[4,5,6,3]]).inv()*m).magnitude())
rows=[]
for e in [0,2,11,12,13,18,21,22,23,24,26,27,31,39,40,41,42,43,44,45]:
    objs=pd.read_parquet(D%e)['observation.objects']
    P=np.array([[*o[0]['pose']] for o in objs]); nm=objs.iloc[0][0]['name']; n=len(P)
    d=np.linalg.norm(P[:,:3]-P[0,:3],axis=1)*1000
    q=R.from_quat(P[:,[4,5,6,3]]); a=np.degrees((q[0].inv()*q).magnitude())
    on=int(np.argmax(d>10)) if (d>10).any() else n
    pm=(d>1)|(a>1); pert=int(np.argmax(pm)) if pm.any() else n
    # step jitter in the first 10 frames (noise floor)
    jt=np.median(np.linalg.norm(np.diff(P[:11,:3],axis=0),axis=1))*1000
    ja=np.median(np.degrees((q[:10].inv()*q[1:11]).magnitude()))
    # pre-onset rotation excluding the last 5 frames before the onset (the lift transient)
    k=max(on-5,1); a5=a[:k].max(); d5=d[:k].max()
    e_on=mean_err(P,slice(0,on)); e_pre=mean_err(P,slice(0,max(pert,1)))
    e_half=mean_err(P,slice(0,max(on//2,1)))
    rows.append((e,nm,n,pert,on,a[:on].max(),d[:on].max(),a5,d5,jt,ja,*e_on,*e_pre,*e_half))
    print(f'ep{e:2d} {nm:17s} n{n:3d} pert f{pert:3d} on f{on:3d} | pre-on max {a[:on].max():4.1f}deg {d[:on].max():4.1f}mm '
          f'| excl last5 {a5:4.1f}deg {d5:4.1f}mm | jitter {jt:.2f}mm {ja:.2f}deg | MEAN[0,on) {e_on[0]:4.1f}mm {e_on[1]:4.2f}deg '
          f'| MEAN[0,pert) {e_pre[0]:4.1f}mm {e_pre[1]:4.2f}deg | MEAN[0,on/2) {e_half[0]:4.1f}mm {e_half[1]:4.2f}deg',flush=True)
A=np.array([r[2:] for r in rows],dtype=float)
mov=[i for i,r in enumerate(rows) if r[1]!='plastic_dish_rack']
print('pre-onset max rot: all range %.1f-%.1f median %.2f; movable range %.1f-%.1f median %.2f'%(A[:,3].min(),A[:,3].max(),np.median(A[:,3]),A[mov,3].min(),A[mov,3].max(),np.median(A[mov,3])))
print('excluding last 5 pre-onset frames: movable rot median %.2f range %.1f-%.1f'%(np.median(A[mov,5]),A[mov,5].min(),A[mov,5].max()))
print('MEAN[0,on) rot err movable: median %.2f max %.2f; >1deg in %d/%d'%(np.median(A[mov,10]),A[mov,10].max(),(A[mov,10]>1).sum(),len(mov)))
print('MEAN[0,pert) rot err movable: median %.2f max %.2f'%(np.median(A[mov,12]),A[mov,12].max()))
print('first pert frame: range f%d-f%d median %.0f'%(A[:,1].min(),A[:,1].max(),np.median(A[:,1])))
