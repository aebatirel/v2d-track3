import sys; sys.path.insert(0,'scripts')
import numpy as np, cv2, json, trimesh
from rend import *
S='/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad'
rows=json.load(open('ep18_perframe.json'))
W,H=900,260; img=np.full((H,W,3),255,np.uint8)
f=np.array([r['f'] for r in rows]); ff=np.array([r['far_frac'] for r in rows]); sp=np.array([r['speed_mm'] for r in rows]); icp=np.array([r['icp_mm'] for r in rows])
x=lambda fr: int(40+fr/352*(W-60))
cv2.line(img,(40,H-30),(W-20,H-30),(0,0,0),1); cv2.line(img,(40,20),(40,H-30),(0,0,0),1)
for i in range(len(f)-1):
    cv2.line(img,(x(f[i]),int(H-30-ff[i]*200)),(x(f[i+1]),int(H-30-ff[i+1]*200)),(220,0,0),2)
    cv2.line(img,(x(f[i]),int(H-30-min(sp[i],25)/25*200)),(x(f[i+1]),int(H-30-min(sp[i+1],25)/25*200)),(0,120,220),1)
    cv2.line(img,(x(f[i]),int(H-30-min(icp[i],100)/100*200)),(x(f[i+1]),int(H-30-min(icp[i+1],100)/100*200)),(0,160,0),1)
label(img,'ep18 per frame: red = share of sweeper points >10 mm from library_v3 (0..1); blue = sweeper speed (0..25 mm/frame); green = per-frame ICP shift (0..100 mm)',(45,15),s=0.38)
for t in range(0,353,50): label(img,str(t),(x(t)-8,H-12),s=0.4)
label(img,'frame',(W-60,H-12),s=0.4)
o=np.load(f'{S}/obs_all/ep18_mini_sweeper.npz'); p=o['pts'].astype(float); d=np.load('obs_d.npz')['d18']
z=np.load('scan_samples.npz'); spp,snn=z['p'],z['n']
sel=np.random.default_rng(0).choice(len(p),300000,replace=False); p=p[sel]; d=d[sel]
col=np.where(d[:,None]<0.01,np.array([[40,160,60]]),np.array([[220,0,0]])).astype(float)
L=trimesh.load('/home/user/v2d-track3/meshes/library_v3/mini_sweeper.glb',force='mesh'); lp,fi=trimesh.sample.sample_surface(L,200000); ln=L.face_normals[fi]
tiles=[]
for vn,v in [('+x',(0,0)),('top',(0,89.9)),('oblique',(35,30))]:
    R=look(v); size=300; sc=size*0.8/0.20; cen=np.array([0,0.01,0.015])
    G_,mG=render_layer(lp,ln,(180,180,180),R,cen,sc,size); P_,mP=render_layer(p,None,col,R,cen,sc,size)
    ov=overlay(G_,mG,P_,mP,alpha=0.3); tiles.append(scalebar(label(ov,f'ep18 obs on library_v3 ({vn}); red >10 mm',s=0.4),sc))
img2=np.concatenate(tiles,1)
pad=np.full((img2.shape[0],W-img2.shape[1],3),255,np.uint8) if img2.shape[1]<W else None
img2=np.concatenate([img2,pad],1) if pad is not None else img2[:, :W]
out=np.concatenate([img,img2],0)
cv2.imwrite('fig4_ep18_contamination.jpg',cv2.cvtColor(out,cv2.COLOR_RGB2BGR),[cv2.IMWRITE_JPEG_QUALITY,88])
