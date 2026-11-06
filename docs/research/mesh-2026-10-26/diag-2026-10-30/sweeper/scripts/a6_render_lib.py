import sys; sys.path.insert(0,'scripts')
import numpy as np, trimesh, cv2
from rend import *
from scipy.spatial import cKDTree
S='/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad'
z=np.load('scan_samples.npz'); sp,sn,scol=z['p'],z['n'],z['c']
lib=trimesh.load('/home/user/v2d-track3/meshes/library_v3/mini_sweeper.glb', force='mesh')
lp,lfi=trimesh.sample.sample_surface(lib,400000,seed=1); ln=lib.face_normals[lfi]
o=np.load(f'{S}/obs_all/ep31_mini_sweeper.npz'); op=o['pts'].astype(float)
o18=np.load(f'{S}/obs_all/ep18_mini_sweeper.npz'); op18=o18['pts'].astype(float)
d18=np.load('obs_d.npz')['d18']; d31=np.load('obs_d.npz')['d31']
views=[('+x face (2 balls)',(0,0)),('-x face (1 ball)',(180,0)),('+y edge',(90,0)),('top',(0,89.9)),('oblique',(35,30))]
size=340; sc=size*0.85/0.17; cen=np.zeros(3)
rows=[]
for nm,v in views:
    R=look(v)
    A,mA=render_layer(sp,sn,scol,R,cen,sc,size)
    B,mB=render_layer(lp,ln,(235,80,60),R,cen,sc,size)
    G,mG=render_layer(sp,sn,(170,170,170),R,cen,sc,size)
    ov=overlay(G,mG,B,mB)
    # mismatch map: scan-only pixels blue, library-only red
    mm=np.full_like(A,255); mm[mA&mB]=(200,200,200); mm[mA&~mB]=(40,90,230); mm[mB&~mA]=(230,50,40)
    # obs ep31 points coloured by distance to library (green<5mm, orange<10, red>10)
    col=np.where(d31[:,None]<0.005,np.array([[40,160,60]]),np.where(d31[:,None]<0.01,np.array([[240,150,0]]),np.array([[220,0,0]])))
    P31,mP=render_layer(op,None,col.astype(float),R,cen,sc,size)
    pv=overlay(G,mG,P31,mP,alpha=0.25)
    col18=np.where(d18[:,None]<0.005,np.array([[40,160,60]]),np.where(d18[:,None]<0.01,np.array([[240,150,0]]),np.array([[220,0,0]])))
    P18,mP18=render_layer(op18,None,col18.astype(float),R,cen,sc,size)
    pv18=overlay(G,mG,P18,mP18,alpha=0.25)
    tiles=[label(A.copy() if True else A,'scan '+nm), label(np.where(mB[:,:,None],B,255).astype(np.uint8),'library_v3'), label(ov,'overlay scan(grey)+lib(red)'), label(mm,'blue=scan only, red=lib only'), label(pv,'ep31 obs pts on scan'), label(pv18,'ep18 obs pts on scan')]
    for t in tiles: scalebar(t,sc)
    A2=A.copy(); A2[~mA]=255; tiles[0]=label(A2,'scan '+nm); scalebar(tiles[0],sc)
    rows.append(np.concatenate(tiles,1))
out=np.concatenate(rows,0)
cv2.imwrite('fig1_scan_vs_library_v3_vs_obs.jpg', cv2.cvtColor(out,cv2.COLOR_RGB2BGR),[cv2.IMWRITE_JPEG_QUALITY,88])
print(out.shape)
