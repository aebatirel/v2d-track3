import numpy as np, trimesh, cv2, glob, os
S='/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad'
G=f'{S}/gen/mesh-20261029-gen-f3fbeb0/results/gen'
files=[f'{G}/sam3d/wooden_piece_1_k27_s42.ply',f'{G}/sam3d/wooden_piece_1_k27_s7.ply',f'{G}/sam3d/wooden_piece_2_k6_s42.ply',f'{G}/sam3d/wooden_piece_2_k6_s7.ply',
       f'{G}/pixal_mv/ep23_wooden_piece_1_s42_gen.ply',f'{G}/pixal_mv/ep23_wooden_piece_2_s42_gen.ply']
rows=[]
for f in files:
    m=trimesh.load(f,force='mesh'); X,_=trimesh.sample.sample_surface(m,80000,seed=0)
    c=X.mean(0); U=np.linalg.svd(X-c,full_matrices=False)[2]; A=(X-c)@U.T
    A=A/np.abs(A).max()*200   # normalised, 200 px half-size
    ims=[]
    for a,b in [(0,1),(0,2),(1,2)]:
        W=420; img=np.full((W,W,3),255,np.uint8)
        # depth-shade along the third axis for the face-on view
        o=[x for x in (0,1,2) if x not in (a,b)][0]
        z=A[:,o]; sh=((z-z.min())/(np.ptp(z)+1e-9)*180).astype(np.uint8)
        u=(A[:,a]+W/2).astype(int); v=(W/2-A[:,b]).astype(int)
        k=(u>=0)&(u<W)&(v>=0)&(v<W)
        img[v[k],u[k]]=np.stack([sh[k],sh[k],sh[k]],1)
        ims.append(img)
    row=np.hstack(ims); head=np.full((30,row.shape[1],3),255,np.uint8)
    cv2.putText(head,os.path.basename(os.path.dirname(f))+'/'+os.path.basename(f)+f'  faces {len(m.faces)}',(6,22),cv2.FONT_HERSHEY_SIMPLEX,0.55,(0,0,0),1)
    rows.append(np.vstack([head,row]))
img=np.vstack(rows); cv2.imwrite(f'{S}/look/sam_boards.png',img); print(img.shape)
