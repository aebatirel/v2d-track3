import numpy as np, sys
from PIL import Image, ImageDraw
import rs_lib as L
H=L.load_hulls(L.RACK_PACKED); G=L.Grid(H)
z0=np.load('../grid_base.npz'); M,PK=z0['M'],z0['PK']
ep=sys.argv[1]; pc=int(sys.argv[2])
R,_=L.rest_frames(ep); P=L.poses(ep); gh=L.load_hulls(L.GUEST[ep]['packed'])
RV=L.rest_volume(G,gh,P['rel'],R,PK); F=RV&~M
O=G.hull_occ(H[pc]); idx=np.argwhere(O); lo,hi=idx.min(0),idx.max(0)
ext=hi-lo; ax=int(np.argmax(ext)); print('piece',pc,'box mm',ext,'long axis',ax, 'F in piece', (O&F).sum())
tiles=[]
ks=np.linspace(lo[ax]+1,hi[ax]-1,8).astype(int)
for k in ks:
    sl=[slice(lo[0],hi[0]+1),slice(lo[1],hi[1]+1),slice(lo[2],hi[2]+1)]; sl[ax]=k; sl=tuple(sl)
    img=np.full(O[sl].shape+(3,),255,np.uint8)
    img[PK[sl]]=[200,200,255]; img[O[sl]]=[120,120,255]; img[M[sl]]=[20,20,20]; img[(RV&M)[sl]]=[255,150,0]; img[(F&O)[sl]]=[255,0,0]; img[(F&~O)[sl]]=[255,180,180]
    im=Image.fromarray(np.transpose(img,(1,0,2))[::-1]).resize((img.shape[0]*6,img.shape[1]*6),Image.NEAREST)
    ImageDraw.Draw(im).text((2,2),f'{k}',fill=(0,0,0)); tiles.append(im)
W=sum(t.size[0] for t in tiles)+8*len(tiles); Hh=max(t.size[1] for t in tiles)
canvas=Image.new('RGB',(W,Hh),(255,255,255)); x=0
for t in tiles: canvas.paste(t,(x,0)); x+=t.size[0]+8
canvas.save(f'../look_p{pc}_ep{ep}.png'); print(canvas.size)
