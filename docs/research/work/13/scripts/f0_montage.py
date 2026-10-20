import cv2, numpy as np, subprocess
V='/Users/aebatirel/Documents/Code/v2d-research/data/track_3/evaluation/videos/chunk-000/observation.images.ego_cam_a/'
B={3:(1080,820,1560,1340),5:(1150,750,1500,1340),6:(1090,830,1490,1380),15:(770,1170,1560,1400),16:(790,1210,1560,1440),
   32:(1190,640,1570,1240),33:(970,720,1530,1200),35:(770,660,1380,1120)}
tiles=[]
for e,(x0,y0,x1,y1) in B.items():
    p=f'frames/stageA/e{e}_f0.png'
    subprocess.run(['ffmpeg','-v','error','-y','-i',V+f'episode_{e:06d}.mp4','-vframes','1',p],check=True)
    t=cv2.imread(p)[y0:y1,x0:x1]; s=400/max(t.shape[:2]); t=cv2.resize(t,None,fx=s,fy=s)
    c=np.zeros((400,400,3),np.uint8); c[:t.shape[0],:t.shape[1]]=t; cv2.putText(c,f'ep{e}',(5,30),0,1,(0,255,255),2); tiles.append(c)
cv2.imwrite('frames/stageA/f0_montage.jpg',np.vstack([np.hstack(tiles[:4]),np.hstack(tiles[4:])]))
