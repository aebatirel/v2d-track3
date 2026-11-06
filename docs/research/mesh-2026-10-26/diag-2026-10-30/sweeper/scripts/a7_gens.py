# GT-free [M] stats of generator meshes as placed in our frame; [D] columns only from existing scores.jsonl (no new scoring)
import numpy as np, trimesh, json, glob, os
from scipy.spatial import cKDTree
S='/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad'
G=f'{S}/gen/mesh-20261029-gen-f3fbeb0/results/gen'
O=np.load(f'{S}/obs_all/ep31_mini_sweeper.npz')['pts'].astype(float)
O=O[np.random.default_rng(0).choice(len(O),40000,replace=False)]; TO=cKDTree(O)
cands={'library_v3':'/home/user/v2d-track3/meshes/library_v3/mini_sweeper.glb'}
for m in ['sam3d','trellis2','triposg','hy21']:
    for s in [42,7]: cands[f'{m}_k270_s{s}']=f'{G}/{m}_sim3/mini_sweeper_k270_s{s}.ply'
for s in [42,7]: cands[f'pixal_mv_s{s}']=f'{G}/pixal_mv/ep31_mini_sweeper_s{s}.ply'
sc=np.load('scan_samples.npz')['p']
def c2z_resid(P):
    # GT-free: C2 about the mesh's own long PCA axis through its centroid
    c=P.mean(0); w,V=np.linalg.eigh(np.cov((P-c).T)); a=V[:,-1]
    R=2*np.outer(a,a)-np.eye(3)
    sub=P[::3]; d=cKDTree(P).query((sub-c)@R.T+c)[0]; return d.mean()*1e3
rows=[]
for k,p in cands.items():
    m=trimesh.load(p,force='mesh')
    P=np.asarray(m.sample(60000,)); 
    do=cKDTree(P).query(O)[0]; dm=TO.query(P)[0]
    ext=np.ptp(P,0)*100
    r=dict(label=k, faces=len(m.faces), watertight=m.is_watertight, bodies=m.body_count, euler=int(m.euler_number),
           ext_xyz_cm=np.round(ext,2).tolist(), area_cm2=round(m.area*1e4,1),
           obs_to_mesh_p50=round(np.median(do)*1e3,2), obs_to_mesh_p90=round(np.percentile(do,90)*1e3,2),
           mesh_to_obs_p50=round(np.median(dm)*1e3,2), mesh_frac_gt10mm=round(float((dm>0.01).mean()),3),
           c2z_selfsym_mm=round(c2z_resid(P),2), centroid_cm=np.round(P.mean(0)*100,2).tolist())
    rows.append(r); print(r)
r=dict(label='SCAN [D] (in scan frame)', ext_xyz_cm=np.round(np.ptp(sc,0)*100,2).tolist(), c2z_selfsym_mm=round(c2z_resid(sc[::5]),2)); print(r); rows.append(r)
json.dump(rows,open('gen_stats.json','w'),indent=1)
