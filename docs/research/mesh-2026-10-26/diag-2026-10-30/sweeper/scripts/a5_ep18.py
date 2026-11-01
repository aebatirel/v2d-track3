# [M] what are the far points in ep18? per-frame ICP to library (bad track?), dust pan proximity, world motion (held?)
import numpy as np, trimesh, json
from scipy.spatial import cKDTree
S='/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad'
lib=trimesh.load('/home/user/v2d-track3/meshes/library_v3/mini_sweeper.glb', force='mesh'); L=np.asarray(lib.sample(200000)); TL=cKDTree(L)
dp=trimesh.load('/home/user/v2d-track3/meshes/library_v3/mini_dust_pan.glb', force='mesh'); D=np.asarray(dp.sample(200000)); TD=cKDTree(D)
P=np.load(f'{S}/data/sweep/ep18/poses.npz')
z=np.load(f'{S}/obs_all/ep18_mini_sweeper.npz'); p=z['pts'].astype(float); fr=z['frame']
W=P['world_T_cam']; Cs=P['cam_T_mini_sweeper']; Cd=P['cam_T_mini_dust_pan']
# world pose of sweeper per frame
Ws=np.einsum('fij,fjk->fik', W, Cs); Wd=np.einsum('fij,fjk->fik', W, Cd)
pos=Ws[:,:3,3]; spd=np.r_[0,np.linalg.norm(np.diff(pos,axis=0),axis=1)]*1000
def kab(a,b):
    ca,cb=a.mean(0),b.mean(0); U,_,Vt=np.linalg.svd((a-ca).T@(b-cb)); R=Vt.T@U.T
    if np.linalg.det(R)<0: Vt[-1]*=-1; R=Vt.T@U.T
    return R, cb-R@ca
rows=[]
for f in np.unique(fr):
    q=p[fr==f]
    if len(q)<200: continue
    d0=TL.query(q)[0]
    # far points -> dust pan frame
    far=q[d0>0.01]
    dd=np.nan
    if len(far)>20:
        # obj(sweeper)->cam->dustpan: x_dp = inv(Cd) Cs x
        T=np.linalg.inv(Cd[f])@Cs[f]
        fd=far@T[:3,:3].T+T[:3,3]; dd=float(np.median(TD.query(fd)[0])*1e3)
    # per-frame trimmed ICP to library
    R=np.eye(3); t=np.zeros(3); x=q.copy()
    for it in range(30):
        dist,idx=TL.query(x); k=dist<np.percentile(dist,70)
        r,tt=kab(x[k],L[idx[k]]); x=x@r.T+tt; R=r@R; t=r@t+tt
    d1=TL.query(x)[0]
    ang=np.degrees(np.arccos(np.clip((np.trace(R)-1)/2,-1,1)))
    rows.append(dict(f=int(f), n=len(q), far_frac=round(float((d0>0.01).mean()),3), med0=round(float(np.median(d0)*1e3),2), med_icp=round(float(np.median(d1)*1e3),2), far_icp=round(float((d1>0.01).mean()),3), icp_deg=round(float(ang),1), icp_mm=round(float(np.linalg.norm(t)*1e3),1), far_to_dustpan_mm=None if np.isnan(dd) else round(dd,1), speed_mm=round(float(spd[f]),1), far_centroid_cm=None if len(far)<20 else np.round(far.mean(0)*100,1).tolist()))
json.dump(rows, open('ep18_perframe.json','w'))
import collections
for r in rows[::6]: print(r)
bad=[r for r in rows if r['far_frac']>0.3]; good=[r for r in rows if r['far_frac']<0.05]
print('bad frames', len(bad), 'median far_frac after per-frame ICP', np.median([r['far_icp'] for r in bad]), 'median far-to-dustpan mm', np.nanmedian([r['far_to_dustpan_mm'] or np.nan for r in bad]), 'median speed mm/frame', np.median([r['speed_mm'] for r in bad]))
print('good frames', len(good), 'median speed', np.median([r['speed_mm'] for r in good]))
# world displacement of the sweeper over the episode
print('sweeper world pos range cm', np.round(np.ptp(pos,0)*100,1), 'dust pan world range cm', np.round(np.ptp(Wd[:,:3,3],0)*100,1))
seg=np.r_[0,44,100,160,202,250,296,330,352]
for a,b in zip(seg[:-1],seg[1:]): print('frames %d-%d sweeper moved %.1f cm, dust pan moved %.1f cm'%(a,b, np.linalg.norm(pos[b]-pos[a])*100, np.linalg.norm(Wd[b,:3,3]-Wd[a,:3,3])*100))
