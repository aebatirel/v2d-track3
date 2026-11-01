import numpy as np, json
from scipy.ndimage import maximum_filter
from scipy.optimize import least_squares
p=np.load('ep31_clean.npy').astype(float)
band=p[(p[:,2]>-0.03)&(p[:,2]<0.03)&(np.abs(p[:,1])<0.05)]
face_x=0.0079
g=0.002; y0,z0=-0.05,-0.03
iy=((band[:,1]-y0)/g).astype(int); iz=((band[:,2]-z0)/g).astype(int)
H=np.full((50,30),-1.0)
np.maximum.at(H,(iy,iz),np.percentile(band[:,0],0)*0+band[:,0])
for row in range(0,50,2):
    print('y=%5.1f '%((y0+row*g)*100)+''.join(' ' if H[row,c]<-0.5 else ('#' if H[row,c]>0.017 else ('+' if H[row,c]>0.013 else ('.' if H[row,c]>0.009 else '_'))) for c in range(30)))
print('cols: z from -3 to 3 cm, 2 mm/col; # x>1.7cm, + x>1.3, . x>0.9')
mx=maximum_filter(H,size=7); pk=np.argwhere((H==mx)&(H>0.014))
balls=[]
for a,b in pk:
    yc,zc=y0+(a+0.5)*g,z0+(b+0.5)*g
    s=band[np.hypot(band[:,1]-yc,band[:,2]-zc)<0.009]; s=s[s[:,0]>face_x+0.003]
    for R in [0.007]:
        f=lambda q: np.linalg.norm(s-np.r_[q[0],q[1],q[2]],axis=1)-R
        q=least_squares(f,[H[a,b]-R,yc,zc],loss='soft_l1',f_scale=0.001).x
    def g2(q): return np.linalg.norm(s-q[:3],axis=1)-q[3]
    q2=least_squares(g2,np.r_[q,0.007],bounds=([-1,-1,-1,0.005],[1,1,1,0.011]),loss='soft_l1',f_scale=0.001).x
    balls.append(dict(apex_x_cm=round(H[a,b]*100,2), centre_r7_cm=np.round(q*100,2).tolist(), free_fit_centre_cm=np.round(q2[:3]*100,2).tolist(), free_radius_mm=round(q2[3]*1000,1), n=len(s)))
    print(balls[-1])
json.dump(dict(face_x_cm=face_x*100, balls=balls), open('balls_obs.json','w'), indent=1)
