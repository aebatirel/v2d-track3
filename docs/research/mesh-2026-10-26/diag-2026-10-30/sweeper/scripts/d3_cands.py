import sys; sys.path.insert(0,'scripts')
import numpy as np, trimesh, cv2
from rend import *
S='/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad'
z=np.load('scan_samples.npz'); sp,sn,scol=z['p'],z['n'],z['c']
al=np.load(f'{S}/obs/ep31_mini_sweeper_align.npz'); Ra,ta=al['R'],al['t']
sp=(sp-ta)@Ra; sn=sn@Ra
O=np.load('ep31_clean.npy').astype(float)
size=300; sc=size*0.85/0.17; cen=np.array([0,0,0.01])
views=[('+x face',(0,0)),('-x face',(180,0)),('+y edge',(90,0)),('top',(0,89.9))]
items=[('library_v3 (submitted)','/home/user/v2d-track3/meshes/library_v3/mini_sweeper.glb'),('M2: lib ∩ C2(lib) + 2 obs balls','meshes/M2_libsym_balls.glb'),('M2b: M2 + v3 resting base','meshes/M2b_libsym_balls_base.glb'),('P1: part program (ep31 obs)','meshes/P1_partprog.glb')]
rows=[]
for nm,pth in items:
    m=trimesh.load(pth,force='mesh'); p,fi=trimesh.sample.sample_surface(m,250000); n=m.face_normals[fi]
    tiles=[]
    for vn,v in views:
        R=look(v)
        G_,mG=render_layer(sp,sn,(170,170,170),R,cen,sc,size); B,mB=render_layer(p,n,(235,80,60),R,cen,sc,size)
        ov=overlay(G_,mG,B,mB); tiles.append(scalebar(label(ov,f'{nm.split(":")[0]} vs scan[D] | {vn}',s=0.4),sc))
    R=look((0,0)); B,mB=render_layer(p,n,(200,200,200),R,cen,sc,size)
    c=np.array([[30,120,230]]).repeat(len(O),0).astype(float); P_,mP=render_layer(O[::3],None,c,R,cen,sc,size)
    tiles.append(scalebar(label(overlay(B,mB,P_,mP,alpha=0.55),f'{nm.split(":")[0]} + ep31 obs (blue) [M]',s=0.4),sc))
    row=np.concatenate(tiles,1); hdr=np.full((22,row.shape[1],3),255,np.uint8); label(hdr,nm,(6,16),s=0.5); rows.append(np.concatenate([hdr,row],0))
img=np.concatenate(rows,0)
cv2.imwrite('fig5_candidates_vs_scan_and_obs.jpg',cv2.cvtColor(img,cv2.COLOR_RGB2BGR),[cv2.IMWRITE_JPEG_QUALITY,86]); print(img.shape)
