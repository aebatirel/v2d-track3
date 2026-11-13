import numpy as np, trimesh, cv2
S='/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad'
R=f'{S}/gmg/runs-dev/20261030-b5pool24-edba5b3/cand/public/ep24'
PX=3.0   # pixels per mm
def panel(B, A, a, b, lim):
    W=int(2*lim*PX)+20; img=np.full((W,W,3),255,np.uint8)
    for pts,col in ((B,(200,120,30)),(A,(20,120,240))):   # BGR: blue-ish points, orange mesh
        u=((pts[:,a]*1000+lim)*PX+10).astype(int); v=((lim-pts[:,b]*1000)*PX+10).astype(int)
        k=(u>=0)&(u<W)&(v>=0)&(v<W); img[v[k],u[k]]=col
    cv2.putText(img,f'axes {a}-{b}',(8,22),cv2.FONT_HERSHEY_SIMPLEX,0.6,(0,0,0),1)
    for t in range(-int(lim)//20*20, int(lim)+1, 20):                     # 2 cm ticks
        x=int((t+lim)*PX+10); cv2.line(img,(x,W-8),(x,W-1),(0,0,0),1)
    return img
rows=[]
for obj in ['wooden_piece_1','wooden_piece_2']:
    o=np.load(f'{S}/obs_all/ep24_{obj}.npz'); P=o['pts']
    P=P[np.random.default_rng(0).choice(len(P),min(len(P),60000),replace=False)]
    c=P.mean(0); U=np.linalg.svd(P-c,full_matrices=False)[2]
    for kind in ['shell_t5p36','hull']:
        m=trimesh.load(f'{R}/{obj}/{kind}.glb',force='mesh'); X,_=trimesh.sample.sample_surface(m,40000,seed=0)
        A=(X-c)@U.T; B=(P-c)@U.T
        lim=max(np.abs(A).max(),np.abs(B).max())*1000+5
        ims=[panel(B,A,a,b,lim) for a,b in [(0,1),(0,2),(1,2)]]
        h=max(i.shape[0] for i in ims); ims=[cv2.copyMakeBorder(i,0,h-i.shape[0],0,4,cv2.BORDER_CONSTANT,value=(255,255,255)) for i in ims]
        row=np.hstack(ims); ext=(m.bounds[1]-m.bounds[0])*100
        nb=len(m.split(only_watertight=False))
        head=np.full((34,row.shape[1],3),255,np.uint8)
        cv2.putText(head,f'{obj} {kind.split("_")[0].upper()}: {len(m.faces)} faces, watertight={m.is_watertight}, {nb} bodies, extent {ext[0]:.1f} x {ext[1]:.1f} x {ext[2]:.1f} cm',(6,24),cv2.FONT_HERSHEY_SIMPLEX,0.55,(0,0,0),1)
        rows.append(np.vstack([head,row]))
        print(obj,kind,len(m.faces),m.is_watertight,nb,np.round(ext,1))
w=max(r.shape[1] for r in rows); rows=[cv2.copyMakeBorder(r,0,8,0,w-r.shape[1],cv2.BORDER_CONSTANT,value=(255,255,255)) for r in rows]
top=np.full((40,w,3),255,np.uint8)
cv2.putText(top,'ep24 gmg dev candidates (orange) vs our observed depth points (blue), principal axes of our points; no scan',(6,26),cv2.FONT_HERSHEY_SIMPLEX,0.6,(0,0,0),1)
img=np.vstack([top]+rows); s=min(1.0,1400/img.shape[1]); img=cv2.resize(img,None,fx=s,fy=s,interpolation=cv2.INTER_AREA)
cv2.imwrite(f'{S}/look/ep24_candidates.png',img); print(img.shape)
