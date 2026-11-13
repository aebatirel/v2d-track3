import sys; sys.path.insert(0,'scripts')
import numpy as np, trimesh, cv2
from rend import *
S='/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad'
sc=trimesh.load(f'{S}/loc/t3/mesh/mini_sweeper/mini_sweeper_visual.glb', force='mesh')
p,n,c=sample_mesh(sc, 600000)
np.savez('scan_samples.npz', p=p, n=n, c=c)
views=[('+x',(0,0)),('-x',(180,0)),('+y',(90,0)),('-y',(-90,0)),('+z top',(0,89.9)),('-z bottom',(0,-89.9)),('obl',(35,30)),('obl2',(215,30))]
tiles=[]
for nm,v in views:
    R=look(v); im,info=render([dict(p=p,n=n,c=c)],R,size=360, center=np.zeros(3), scale=360*0.85/0.16)
    label(im,'scan '+nm); scalebar(im, info['scale']); tiles.append(im)
row1=np.concatenate(tiles[:4],1); row2=np.concatenate(tiles[4:],1)
cv2.imwrite('scan_views.jpg', cv2.cvtColor(np.concatenate([row1,row2],0), cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 90])
