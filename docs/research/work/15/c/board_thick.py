# Stage C: board plate thickness (median per-cell top-bottom) and slot width (scan vs hull), rest pose of public ep 23
import sys, os, numpy as np, trimesh
sys.path.insert(0,os.path.dirname(__file__)); import coacd_fill as C
for n in ['wooden_piece_1','wooden_piece_2']:
    m=trimesh.load(f'{C.D}/mesh/{n}/{n}_collision.glb',force='mesh'); R=C.rest_R(n); s=m.sample(1500000)@R.T
    z=np.load(f'{C.H}/{n}.npz'); h=np.vstack([trimesh.Trimesh(z[f'v{i}'],z[f'f{i}']).sample(60000) for i in range(int(z['n']))])@R.T
    c=0.004; key=lambda p:(np.floor(p[:,0]/c).astype(int),np.floor(p[:,1]/c).astype(int))
    ix,iy=key(s); k=ix*100000+iy; o=np.argsort(k); ks,idx=np.unique(k[o],return_index=True)
    zz=np.split(s[o,2],idx[1:]); th=np.array([v.max()-v.min() for v in zz])
    print(n,'plate thickness median %.1f mm, p25 %.1f, p75 %.1f (cells %d; markers inflate upper tail)'%(np.median(th)*1e3,np.percentile(th,25)*1e3,np.percentile(th,75)*1e3,len(th)))
    # slot width: in the board plane, find long axis (y in rest map) rows; for each row count empty runs inside outline
    for name,P in (('scan',s),('hull',h)):
        cc=0.001; X=np.floor((P[:,0]-s[:,0].min())/cc).astype(int); Y=np.floor((P[:,1]-s[:,1].min())/cc).astype(int)
        nx=X.max()+1; ny=Y.max()+1; occ=np.zeros((ny+1,nx+1),bool); ok=(X>=0)&(Y>=0); occ[Y[ok],X[ok]]=True
        widths=[]
        for r in range(0,occ.shape[0],5):
            row=occ[r]; xs=np.where(row)[0]
            if len(xs)<10: continue
            inner=row[xs[0]:xs[-1]+1]; gaps=[]; g=0
            for v in inner:
                if not v: g+=1
                else:
                    if g>=4: gaps.append(g)
                    g=0
            if gaps: widths.append(max(gaps))
        print('   ',name,'rows with an interior gap>=4 mm: %d, median gap %.0f mm, max %.0f mm'%(len(widths),np.median(widths) if widths else 0,max(widths) if widths else 0))
