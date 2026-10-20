# Heuristic uprightness check: vertical centroid of wood-coloured (table) pixels and of bright floor pixels at f0/f30.
import cv2, numpy as np, glob, os
for path in sorted(glob.glob('/Users/aebatirel/Documents/Code/v2d-research/data/track_3/*/videos/chunk-000/observation.images.ego_cam_a/*.mp4')):
    c=cv2.VideoCapture(path); r=[]
    for i in (0,30):
        c.set(cv2.CAP_PROP_POS_FRAMES,i); ok,f=c.read()
        if not ok: continue
        f=cv2.resize(f,(507,380)); h=cv2.cvtColor(f,cv2.COLOR_BGR2HSV)
        wood=(h[...,0]>=5)&(h[...,0]<=20)&(h[...,1]>120)&(h[...,2]>60)
        ys=np.nonzero(wood)[0]; r.append(ys.mean()/380 if len(ys) else np.nan)
    print(path.split('/')[-4][:4], os.path.basename(path)[8:14], 'wood centroid y/H:', ' '.join('%.2f'%x for x in r))
