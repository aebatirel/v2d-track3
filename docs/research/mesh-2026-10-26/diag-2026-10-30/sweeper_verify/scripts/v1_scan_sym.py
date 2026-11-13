# [D] Independent re-measure: scan self-symmetry under 180 deg turns about its PCA axes; extents (W/L) of scan and meshes.
import numpy as np, trimesh, sys, json
from scipy.spatial import cKDTree
S='/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad'
def load(p):
    m=trimesh.load(p, force='mesh'); return m
def samp(m,n,seed):
    rng=np.random.default_rng(seed)
    a=m.area_faces; fi=rng.choice(len(a),n,p=a/a.sum()); r1,r2=rng.random(n),rng.random(n)
    s=np.sqrt(r1)[:,None]; T=m.triangles[fi]
    return (1-s)*T[:,0]+s*(1-r2[:,None])*T[:,1]+s*r2[:,None]*T[:,2]
def pca(P):
    c=P.mean(0); w,V=np.linalg.eigh(np.cov((P-c).T)); return c,V[:,::-1],w[::-1]
def kab(A,B):
    ca,cb=A.mean(0),B.mean(0); U,_,Vt=np.linalg.svd((A-ca).T@(B-cb)); R=Vt.T@U.T
    if np.linalg.det(R)<0: Vt[-1]*=-1; R=Vt.T@U.T
    return R,cb-R@ca
def rot(ax,ang):
    ax=ax/np.linalg.norm(ax); K=np.array([[0,-ax[2],ax[1]],[ax[2],0,-ax[0]],[-ax[1],ax[0],0]])
    return np.eye(3)+np.sin(ang)*K+(1-np.cos(ang))*K@K
def icp(A,B,R,t,it=50):   # move A onto B, plain (untrimmed) point-to-point
    T=cKDTree(B)
    for _ in range(it):
        X=A@R.T+t; d,i=T.query(X); r,tt=kab(X,B[i]); R=r@R; t=r@t+tt
    X=A@R.T+t; d1=T.query(X)[0]; d2=cKDTree(X).query(B)[0]
    return R,t,d1,d2
scan=load(f'{S}/loc/t3/mesh/mini_sweeper/mini_sweeper_visual.glb')
A=samp(scan,60000,1); B=samp(scan,60000,2)
c,V,w=pca(A)
loc=(A-c)@V; ext=np.ptp(loc,0)
out=dict(scan_extents_cm=(ext*100).round(2).tolist(), scan_WL=float(ext[1]/ext[0]), scan_TL=float(ext[2]/ext[0]), long_axis=V[:,0].round(3).tolist())
print(out)
for k,name in enumerate(['long','mid','short']):
    R0=rot(V[:,k],np.pi); t0=c-R0@c
    R,t,d1,d2=icp(A,B,R0,t0)
    ang=np.degrees(np.arccos(np.clip((np.trace(R)-1)/2,-1,1)))
    out[f'C2_{name}']=dict(mean_one_way_mm=round(d1.mean()*1e3,3), sym_mean_mm=round(0.5*(d1.mean()+d2.mean())*1e3,3), p90_mm=round(np.percentile(d1,90)*1e3,2), final_angle=round(float(ang),1))
    print(name, out[f'C2_{name}'])
# floor: identity between two independent samples
d=cKDTree(B).query(A)[0]; out['floor_mean_mm']=round(d.mean()*1e3,3); print('floor', out['floor_mean_mm'])
# extents of other meshes (intrinsic PCA)
G=f'{S}/gen/mesh-20261029-gen-f3fbeb0/results/gen'
meshes={'library_v3':'/home/user/v2d-track3/meshes/library_v3/mini_sweeper.glb',
 'sam3d_s7':f'{G}/sam3d/mini_sweeper_k270_s7.ply','sam3d_s42':f'{G}/sam3d/mini_sweeper_k270_s42.ply',
 'sam3d_sim3_s7':f'{G}/sam3d_sim3/mini_sweeper_k270_s7.ply','sam3d_sim3_s42':f'{G}/sam3d_sim3/mini_sweeper_k270_s42.ply',
 'pixal_mv_s7':f'{G}/pixal_mv/ep31_mini_sweeper_s7.ply','pixal_mv_s42':f'{G}/pixal_mv/ep31_mini_sweeper_s42.ply',
 'hy21_sim3_s7':f'{G}/hy21_sim3/mini_sweeper_k270_s7.ply','trellis2_sim3_s7':f'{G}/trellis2_sim3/mini_sweeper_k270_s7.ply','triposg_sim3_s7':f'{G}/triposg_sim3/mini_sweeper_k270_s7.ply',
 'P1':f'{S}/diag/sweeper/meshes/P1_partprog.glb','M2':f'{S}/diag/sweeper/meshes/M2_libsym_balls.glb'}
Llib=None
for k,p in meshes.items():
    try: m=load(p)
    except Exception as e: print(k,'fail',e); continue
    P=samp(m,40000,3); cc,VV,_=pca(P); e=np.ptp((P-cc)@VV,0)
    rec=dict(extents_cm=(e*100).round(2).tolist(), WL=round(float(e[1]/e[0]),3), TL=round(float(e[2]/e[0]),3), long_axis=VV[:,0].round(3).tolist(), centroid_cm=(cc*100).round(2).tolist())
    if k=='library_v3': Llib=VV[:,0]
    rec['long_axis_deg_from_library']=round(float(np.degrees(np.arccos(abs(VV[:,0]@Llib)))),1)
    # axis-aligned extents in OUR frame (x,y,z)
    rec['frame_extents_cm']=(np.ptp(P,0)*100).round(2).tolist()
    out[k]=rec; print(k,rec)
json.dump(out,open(f'{S}/diag/sweeper_verify/v1_scan_sym.json','w'),indent=1)
