import cv2, numpy as np
V='/Users/aebatirel/Documents/Code/v2d-research/data/track_3/%s/videos/chunk-000/observation.images.ego_cam_%s/episode_%06d.mp4'
def get(split,cam,ep,i):
    c=cv2.VideoCapture(V%(split,cam,ep)); c.set(cv2.CAP_PROP_POS_FRAMES,i); ok,f=c.read(); return f
t=[]
for split,ep,i in [('evaluation',30,0),('public',31,0),('evaluation',20,0),('public',21,0),('evaluation',20,4),('evaluation',20,8)]:
    f=get(split,'a',ep,i); f=cv2.resize(f,(640,480)); cv2.putText(f,f'{split[:4]} {ep} f{i}',(5,25),0,0.8,(0,0,255),2); t.append(f)
cv2.imwrite('f0_30_20.jpg',np.vstack([np.hstack(t[:2]),np.hstack(t[2:4]),np.hstack(t[4:])]))
