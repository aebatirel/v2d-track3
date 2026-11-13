import sys; sys.path.insert(0,'scripts')
import numpy as np, trimesh, cv2, json
from rend import *
S='/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad'
G=f'{S}/gen/mesh-20261029-gen-f3fbeb0/results/gen'
z=np.load('scan_samples.npz'); sp,sn,scol=z['p'],z['n'],z['c']
al=np.load(f'{S}/obs/ep31_mini_sweeper_align.npz'); Ra,ta=al['R'],al['t']
sp_our=(sp-ta)@Ra; sn_our=sn@Ra          # scan shown in OUR frame via the page's display alignment [D]
size=300; sc=size*0.85/0.20; cen=np.array([0,0,0.01])
views=[('+x face',(0,0)),('+y edge',(90,0)),('top',(0,89.9))]
def samp(path,n=250000):
    m=trimesh.load(path,force='mesh'); p,fi=trimesh.sample.sample_surface(m,n); return p,m.face_normals[fi]
def panel_set(name,path,col=(235,80,60), frame='our'):
    p,n=samp(path); tiles=[]
    for vn,v in views:
        R=look(v)
        Gs,mG=render_layer(sp_our,sn_our,(170,170,170),R,cen,sc,size)
        B,mB=render_layer(p,n,col,R,cen,sc,size)
        ov=overlay(Gs,mG,B,mB); label_=f"{name} | {vn}"
        tiles.append(scalebar(label(ov,label_,s=0.42),sc))
    return np.concatenate(tiles,0)
cols=[]
items=[('library_v3','/home/user/v2d-track3/meshes/library_v3/mini_sweeper.glb'),('M2 (GT-free fix)','meshes/M2_libsym_balls.glb'),
       ('SAM3D s7 (sim3)',f'{G}/sam3d_sim3/mini_sweeper_k270_s7.ply'),('SAM3D s42 (sim3)',f'{G}/sam3d_sim3/mini_sweeper_k270_s42.ply'),
       ('Pixal3D-MV s42 (posed)',f'{G}/pixal_mv/ep31_mini_sweeper_s42.ply'),('TRELLIS.2 s7 (sim3)',f'{G}/trellis2_sim3/mini_sweeper_k270_s7.ply'),
       ('Hunyuan2.1 s7 (sim3)',f'{G}/hy21_sim3/mini_sweeper_k270_s7.ply'),('TripoSG s7 (sim3)',f'{G}/triposg_sim3/mini_sweeper_k270_s7.ply')]
for k,p in items:
    cols.append(panel_set(k,p)); print(k, flush=True)
top=np.concatenate(cols[:4],1); bot=np.concatenate(cols[4:],1)
img=np.concatenate([top,bot],0)
cv2.imwrite('fig2_meshes_in_our_frame_vs_scan.jpg',cv2.cvtColor(img,cv2.COLOR_RGB2BGR),[cv2.IMWRITE_JPEG_QUALITY,85])
print(img.shape)
