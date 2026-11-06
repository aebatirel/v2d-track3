# [D] scan parts by colour + geometry, and near-symmetry of the scan
import sys; sys.path.insert(0,'scripts')
import numpy as np, cv2, json
from scipy.spatial import cKDTree
z=np.load('scan_samples.npz'); p,n,c=z['p'],z['n'],z['c']
hsv=cv2.cvtColor(c[None].astype(np.uint8),cv2.COLOR_RGB2HSV)[0].astype(float)  # H 0..180
H,Sat,V=hsv[:,0],hsv[:,1],hsv[:,2]
# heuristics, refined by geometry
lab=np.full(len(p),'other',object)
green=(H>=25)&(H<=45)&(Sat>120)&(V>80)
ball=(Sat<45)&(V>130)
dark=(V<55)
lab[green]='head'
lab[ball]='ball'
lab[dark&~green]='post'
zc=p[:,2]
# ring: above the head; bristles: below the head
headz=np.percentile(zc[green],[2,50,98])
rest=(lab=='other')
lab[rest&(zc>headz[1])]='ring'
lab[rest&(zc<=headz[1])]='bristle'
out={}
for k in ['ring','head','bristle','ball','post']:
    q=p[lab==k]
    if len(q)==0: continue
    out[k]=dict(frac_area=round(len(q)/len(p),3), lo_cm=np.round(q.min(0)*100,2).tolist(), hi_cm=np.round(q.max(0)*100,2).tolist(), ext_cm=np.round(np.ptp(q,0)*100,2).tolist())
    print(k, out[k])
np.save('scan_labels.npy', lab.astype('U8'))
# ring geometry: fit circle in y-z plane
q=p[lab=='ring']; yz=q[:,1:]; 
A=np.c_[2*yz, np.ones(len(yz))]; b=(yz**2).sum(1); sol=np.linalg.lstsq(A,b,rcond=None)[0]; cy,cz=sol[:2]; r=np.sqrt(sol[2]+cy**2+cz**2)
rr=np.linalg.norm(yz-[cy,cz],axis=1)
print('ring centre y,z cm', round(cy*100,2), round(cz*100,2), 'mean radius cm', round(r*100,2), 'radial min/max cm', np.round(np.percentile(rr,[1,99])*100,2), 'x thickness cm', np.round(np.percentile(q[:,0],[1,99])*100,2))
# head thickness in x
q=p[lab=='head']; print('head x p1/p99 cm', np.round(np.percentile(q[:,0],[1,99])*100,2), 'z', np.round(np.percentile(q[:,2],[1,99])*100,2), 'y', np.round(np.percentile(q[:,1],[1,99])*100,2))
q=p[lab=='bristle']; print('bristle x p1/p99 cm', np.round(np.percentile(q[:,0],[1,99])*100,2), 'z', np.round(np.percentile(q[:,2],[1,99])*100,2), 'y', np.round(np.percentile(q[:,1],[1,99])*100,2))
for zz in [-5.5,-4,-2.5,-1]:
    s=q[np.abs(q[:,2]*100-zz)<0.4]; print('  bristle slab z=%.1f cm: y %.2f..%.2f  x %.2f..%.2f cm'%(zz, *(np.percentile(s[:,1],[1,99])*100), *(np.percentile(s[:,0],[1,99])*100)))
# balls: cluster
q=p[lab=='ball']; 
from scipy.cluster.vq import kmeans2
from scipy.sparse.csgraph import connected_components
from scipy.sparse import coo_matrix
t=cKDTree(q); pairs=t.query_pairs(0.003,output_type='ndarray')
nc,cl=connected_components(coo_matrix((np.ones(len(pairs)),(pairs[:,0],pairs[:,1])),shape=(len(q),len(q))))
cnt=np.bincount(cl); big=np.argsort(-cnt)[:6]
balls=[]
for b in big:
    if cnt[b]<500: continue
    s=q[cl==b]
    # sphere fit
    A=np.c_[2*s, np.ones(len(s))]; bb=(s**2).sum(1); so=np.linalg.lstsq(A,bb,rcond=None)[0]; cen=so[:3]; rad=np.sqrt(so[3]+cen@cen)
    balls.append(dict(n=int(cnt[b]), centre_cm=np.round(cen*100,2).tolist(), radius_mm=round(rad*1000,1)))
    print('ball', balls[-1])
out['balls']=balls
# near-symmetry of scan: 180 deg about x, y, z through the area centroid; mirror planes
cen=p.mean(0); pc=p-cen
sub=pc[np.random.default_rng(0).choice(len(pc),60000,replace=False)]
T=cKDTree(pc)
def resid(M):
    d=T.query(sub@M.T)[0]; return 1000*d.mean(), 1000*np.percentile(d,90)
rots={'C2 about x':np.diag([1,-1,-1.]),'C2 about y':np.diag([-1,1,-1.]),'C2 about z (long axis)':np.diag([-1,-1,1.]),'mirror x (front/back)':np.diag([-1,1,1.]),'mirror y (left/right)':np.diag([1,-1,1.]),'identity (other sample)':np.eye(3)}
nb=lab!='ball'; nb&= lab!='post'
T2=cKDTree(pc[nb]); sub2=pc[nb][np.random.default_rng(1).choice(nb.sum(),60000,replace=False)]
sym={}
for k,M in rots.items():
    a=resid(M); d=T2.query(sub2@M.T)[0]; b=(1000*d.mean(),1000*np.percentile(d,90))
    sym[k]=dict(all_mean_mm=round(a[0],2), all_p90=round(a[1],2), no_markers_mean_mm=round(b[0],2), no_markers_p90=round(b[1],2))
    print('%-26s all: mean %.2f p90 %.2f mm | without balls+posts: mean %.2f p90 %.2f'%(k,*a,*b))
out['symmetry']=sym
json.dump(out,open('scan_parts.json','w'),indent=1)
