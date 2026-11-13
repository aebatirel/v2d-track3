# [M] observed points vs library_v3 (GT-free) and [D] vs scan; per-frame breakdown
import sys, json, numpy as np, trimesh
from scipy.spatial import cKDTree
S='/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad'
lib=trimesh.load('/home/user/v2d-track3/meshes/library_v3/mini_sweeper.glb', force='mesh')
L=np.asarray(lib.sample(400000)); TL=cKDTree(L)
sc=np.load('scan_samples.npz')['p']; TS=cKDTree(sc)
res={}
for ep in [18,31]:
    z=np.load(f'{S}/obs_all/ep{ep}_mini_sweeper.npz')
    p=z['pts'].astype(float); fr=z['frame']; cam=z['cam'].astype(float)
    d=TL.query(p)[0]
    print(f'ep{ep}: n={len(p)} frames={len(np.unique(fr))} range {fr.min()}..{fr.max()}')
    print('  dist to library_v3 mm p50 %.2f p75 %.2f p90 %.2f p95 %.2f; frac>10mm %.3f >20mm %.3f'%(*np.percentile(d,[50,75,90,95])*1e3, (d>0.01).mean(), (d>0.02).mean()))
    print('  centroid obs cm', np.round(p.mean(0)*100,2), ' library centroid', np.round(L.mean(0)*100,2), ' bbox obs cm', np.round(p.min(0)*100,1), np.round(p.max(0)*100,1))
    far=d>0.01
    if far.any():
        q=p[far]; print('  far (>10mm) points: n=%d centroid cm %s bbox %s..%s'%(far.sum(), np.round(q.mean(0)*100,2), np.round(q.min(0)*100,1), np.round(q.max(0)*100,1)))
    # per frame
    rows=[]
    for f in np.unique(fr):
        m=fr==f; dd=d[m]
        rows.append((int(f), int(m.sum()), float(np.median(dd)*1e3), float((dd>0.01).mean()), *(p[m].mean(0)*100)))
    rows=np.array(rows)
    np.save(f'obs_perframe_ep{ep}.npy', rows)
    bad=rows[:,3]>0.3
    print('  frames with >30%% points >10mm from library: %d of %d; their frame ids: %s'%(bad.sum(), len(rows), rows[bad,0].astype(int).tolist()[:80]))
    # camera directions (which side seen): cam centre direction in object frame
    cd=cam-p; cd/=np.linalg.norm(cd,axis=1,keepdims=True)
    print('  view-direction mean (obj frame)', np.round(cd.mean(0),2), ' frac seen from +x side %.2f, -x side %.2f, from below (z<-0.3) %.2f'%((cd[:,0]>0.3).mean(), (cd[:,0]<-0.3).mean(), (cd[:,2]<-0.3).mean()))
    res[ep]=dict(p=p, fr=fr, d=d, cam=cam)
np.savez_compressed('obs_d.npz', d18=res[18]['d'], d31=res[31]['d'])
