import cv2, numpy as np, sys
V='/Users/aebatirel/Documents/Code/v2d-research/data/track_3/%s/videos/chunk-000/observation.images.ego_cam_%s/episode_%06d.mp4'
def get(split,cam,ep,i):
    c=cv2.VideoCapture(V%(split,cam,ep)); c.set(cv2.CAP_PROP_POS_FRAMES,i); ok,f=c.read(); return f
tiles=[]
for split,cam,ep,i in [('evaluation','a',1,0),('evaluation','a',1,150),('public','a',0,100),('evaluation','a',20,0),('evaluation','b',20,0),('evaluation','c',20,0)]:
    f=get(split,cam,ep,i); f=cv2.resize(f,(480,int(480*f.shape[0]/f.shape[1])))
    f=cv2.copyMakeBorder(f,0,360-f.shape[0],0,0,cv2.BORDER_CONSTANT)
    cv2.putText(f,f'{split[:4]} {cam} {ep} f{i} RAW',(5,20),0,0.6,(0,0,255),2); tiles.append(f)
g=np.vstack([np.hstack(tiles[:3]),np.hstack(tiles[3:])]); cv2.imwrite('raw_grid.jpg',g)
