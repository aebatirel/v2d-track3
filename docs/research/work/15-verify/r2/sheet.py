# Contact sheet of eval ego_cam_a frames (no rotation): python sheet.py ep start stop step [width] [crop x0 y0 x1 y1 as fractions]
import sys, subprocess, os, glob, numpy as np
from PIL import Image, ImageDraw
ep,a,b,s=map(int,sys.argv[1:5]); W=int(sys.argv[5]) if len(sys.argv)>5 else 500
crop=[float(x) for x in sys.argv[6:10]] if len(sys.argv)>9 else None
V='/Users/aebatirel/Documents/Code/v2d-research/data/track_3/'+os.environ.get('SPLIT','evaluation')+'/videos/chunk-000/observation.images.ego_cam_a/episode_%06d.mp4'%ep
tmp=f'tmp_{ep}'; os.makedirs(tmp,exist_ok=True); [os.remove(f) for f in glob.glob(tmp+'/*.png')]
sel=f"select='between(n\\,{a}\\,{b})*not(mod(n-{a}\\,{s}))'"
subprocess.run(['ffmpeg','-loglevel','error','-i',V,'-vf',sel,'-vsync','0',f'{tmp}/f_%04d.png'],check=True)
fs=sorted(glob.glob(tmp+'/*.png')); ims=[]
for i,f in enumerate(fs):
    im=Image.open(f)
    if crop: w,h=im.size; im=im.crop((int(crop[0]*w),int(crop[1]*h),int(crop[2]*w),int(crop[3]*h)))
    im=im.resize((W,int(W*im.size[1]/im.size[0]))); d=ImageDraw.Draw(im); d.rectangle((0,0,70,22),fill='black'); d.text((4,4),f'f{a+i*s}',fill='yellow'); ims.append(im)
c=int(os.environ.get("COLS",4)); r=(len(ims)+c-1)//c; w,h=ims[0].size; S=Image.new('RGB',(c*w,r*h))
for i,im in enumerate(ims): S.paste(im,((i%c)*w,(i//c)*h))
out=os.environ.get('SPLIT','evaluation')[0]+f'{ep}_{a}_{b}_{s}'+('c' if crop else '')+'.jpg'; S.save(out,quality=85); print(out,S.size)
