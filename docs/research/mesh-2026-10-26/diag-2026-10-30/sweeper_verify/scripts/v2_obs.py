# [M] Independent re-measure on OUR observed points (no scan): ep18 far share vs library_v3, blob location/motion; ep31/ep18 view coverage.
import numpy as np, trimesh, json
from scipy.spatial import cKDTree
S='/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad'
lib=trimesh.load('/home/user/v2d-track3/meshes/library_v3/mini_sweeper.glb', force='mesh')
# distance to the library SURFACE via dense sampling (2M pts ~ 0.1 mm spacing error) - different sampler from the other agent
rng=np.random.default_rng(123)
a=lib.area_faces; fi=rng.choice(len(a),1500000,p=a/a.sum()); r1,r2=rng.random(len(fi)),rng.random(len(fi)); s=np.sqrt(r1)[:,None]; T=lib.triangles[fi]
L=(1-s)*T[:,0]+s*(1-r2[:,None])*T[:,1]+s*r2[:,None]*T[:,2]; TL=cKDTree(L)
inside_lib=lambda q: lib.contains(q)
out={}
for ep in (18,31):
    z=np.load(f'{S}/obs_all/ep{ep}_mini_sweeper.npz', allow_pickle=True)
    p=z['pts'].astype(float); cam=z['cam'].astype(float); fr=z['frame']
    d=TL.query(p)[0]
    v=cam-p; v/=np.linalg.norm(v,axis=1,keepdims=True)
    # per-frame camera position in object frame (median of cam over its points)
    frames=np.unique(fr); camf=np.array([np.median(cam[fr==f],0) for f in frames])
    cdir=camf/np.linalg.norm(camf,axis=1,keepdims=True)
    rec=dict(n=len(p), n_frames=len(frames), far10=round(float((d>0.01).mean()),4), far20=round(float((d>0.02).mean()),4),
             p50_mm=round(float(np.median(d)*1e3),2), p90_mm=round(float(np.percentile(d,90)*1e3),2),
             pts_view_xpos=round(float((v[:,0]>0.3).mean()),3), pts_view_xneg=round(float((v[:,0]<-0.3).mean()),3), pts_view_zneg=round(float((v[:,2]<-0.3).mean()),3),
             frames_cam_xneg=int((cdir[:,0]<0).sum()), frames_cam_xneg_strong=int((cdir[:,0]<-0.3).sum()), min_cam_dir_x=round(float(cdir[:,0].min()),3),
             frames_cam_zneg=int((cdir[:,2]<-0.3).sum()))
    far=p[d>0.01]
    if len(far):
        rec['far_centroid_cm']=(far.mean(0)*100).round(2).tolist(); rec['far_p5_cm']=(np.percentile(far,5,0)*100).round(1).tolist(); rec['far_p95_cm']=(np.percentile(far,95,0)*100).round(1).tolist()
        # how many far points are inside the library volume (would be interior noise) vs outside
        sub=far[rng.choice(len(far),min(20000,len(far)),replace=False)]
        rec['far_inside_lib_frac']=round(float(inside_lib(sub).mean()),3)
    # points on -x side of the object (x < -1 cm) : are any observed at all?
    rec['frac_pts_x_lt_-1cm']=round(float((p[:,0]<-0.01).mean()),4)
    out[ep]=rec; print(ep,rec)
    if ep==18:
        P=np.load(f'{S}/data/sweep/ep18/poses.npz'); W=P['world_T_cam']; Cs=P['cam_T_mini_sweeper'].astype(float); Cd=P['cam_T_mini_dust_pan'].astype(float)
        Ws=np.einsum('fij,fjk->fik',W,Cs)
        pos=Ws[:,:3,3]
        rows=[]
        for f in frames:
            m=fr==f; q=p[m]; dq=d[m]; fq=q[dq>0.01]
            if len(fq)<50: rows.append((int(f),float((dq>0.01).mean()),np.nan,np.nan,np.nan,np.nan,np.nan,np.nan)); continue
            c_obj=fq.mean(0)
            c_w=Ws[f,:3,:3]@c_obj+Ws[f,:3,3]
            rows.append((int(f),float((dq>0.01).mean()),*c_obj,*c_w))
        rows=np.array(rows)
        bad=rows[:,1]>0.3
        mov=bad&(rows[:,0]>=44)&(rows[:,0]<=204); still=bad&(rows[:,0]>=296)
        def spread(x): return (np.nanstd(x,0)*100).round(2).tolist()
        rec['blob_frames_moving']=int(mov.sum()); rec['blob_frames_still']=int(still.sum())
        rec['blob_obj_centroid_moving_cm']=(np.nanmedian(rows[mov,2:5],0)*100).round(2).tolist(); rec['blob_obj_std_moving_cm']=spread(rows[mov,2:5])
        rec['blob_world_std_moving_cm']=spread(rows[mov,5:8])
        rec['blob_obj_centroid_still_cm']=(np.nanmedian(rows[still,2:5],0)*100).round(2).tolist(); rec['blob_obj_std_still_cm']=spread(rows[still,2:5])
        # sweeper world travel during the moving blob frames
        fm=rows[mov,0].astype(int); rec['sweeper_world_std_moving_cm']=spread(pos[fm])
        # world z of blob vs sweeper (is it above = a hand from above, or below = table?)
        wz_up=np.array([0,0,1.0])
        rec['blob_minus_sweeper_world_cm_median']=(np.nanmedian(rows[mov,5:8]-pos[fm],0)*100).round(2).tolist()
        # sweeper long-axis (obj z) direction in world for those frames
        ax=np.einsum('fij,j->fi',Ws[fm,:3,:3],np.array([0,0,1.0])); rec['obj_z_in_world_median']=np.median(ax,0).round(2).tolist()
        ay=np.einsum('fij,j->fi',Ws[fm,:3,:3],np.array([0,1.0,0])); rec['obj_y_in_world_median']=np.median(ay,0).round(2).tolist()
        # world-frame up guess: world z? report world positions range
        rec['sweeper_world_pos_range_cm']=(np.ptp(pos,0)*100).round(1).tolist()
        np.save(f'{S}/diag/sweeper_verify/ep18_blob_rows.npy',rows)
        print({k:rec[k] for k in rec if k.startswith(('blob','sweeper','obj_'))})
json.dump(out,open(f'{S}/diag/sweeper_verify/v2_obs.json','w'),indent=1)
