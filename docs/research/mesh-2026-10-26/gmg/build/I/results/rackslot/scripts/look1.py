import numpy as np, sys
from PIL import Image, ImageDraw
import rs_lib as L
H=L.load_hulls(L.RACK_PACKED); G=L.Grid(H)
z0=np.load('../grid_base.npz'); M,PK=z0['M'],z0['PK']
ep=sys.argv[1]; axis=int(sys.argv[2]); off=int(sys.argv[3]) if len(sys.argv)>3 else 0
d=np.load(f'../rest_ep{ep}.npz'); F,RV=d['F'],d['RV']
k=np.argwhere(F); c=np.median(k,0).astype(int); c[axis]+=off
sl=[slice(None)]*3; sl[axis]=c[axis]; sl=tuple(sl)
img=np.full(M[sl].shape+(3,),255,np.uint8)
img[PK[sl]]=[150,150,255]; img[M[sl]]=[20,20,20]; img[RV[sl]&M[sl]]=[255,140,0]; img[F[sl]]=[255,0,0]
im=Image.fromarray(np.transpose(img,(1,0,2))[::-1]).resize((img.shape[0]*3,img.shape[1]*3),Image.NEAREST)
ImageDraw.Draw(im).text((5,5),f'ep{ep} axis{axis} idx{c[axis]} (mm from lo {np.round(G.lo*1000,1)})',fill=(0,0,0))
im.save(f'../look_ep{ep}_a{axis}_{off}.png'); print(im.size, c, 'F idx range', k.min(0), k.max(0))
