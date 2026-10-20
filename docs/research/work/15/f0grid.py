import cv2, sys
from PIL import Image, ImageDraw
EV='/Users/aebatirel/Documents/Code/v2d-research/data/track_3/evaluation/videos/chunk-000/observation.images.ego_cam_a/episode_%06d.mp4'
eps=[int(x) for x in sys.argv[2].split(',')]; fr=int(sys.argv[3]); W=480; cols=4
ims=[]
for e in eps:
    c=cv2.VideoCapture(EV%e)
    for i in range(fr+1): ok,f=c.read()
    f=cv2.resize(f,(W,int(f.shape[0]*W/f.shape[1])),interpolation=cv2.INTER_AREA); ims.append((e,f[:,:,::-1]))
h=ims[0][1].shape[0]; rows=(len(ims)+cols-1)//cols
cv=Image.new('RGB',(cols*W,rows*h)); d=ImageDraw.Draw(cv)
for j,(e,f) in enumerate(ims):
    x,y=(j%cols)*W,(j//cols)*h; cv.paste(Image.fromarray(f),(x,y)); d.rectangle([x,y,x+90,y+16],fill=(0,0,0)); d.text((x+3,y+2),f'ep{e} f{fr}',fill=(255,255,0))
cv.save(sys.argv[1])
