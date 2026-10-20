import cv2, numpy as np, sys
img = cv2.imread('frames/stageA/e37_f0.png'); hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
P = {'bowl':(852,982),'handle':(1176,973),'lpalm':(385,1176),'rpalm':(1830,1150),'table':(1014,1298),'floor':(1500,400)}
vis = img.copy()
for k,(x,y) in P.items():
    r=12; h=hsv[y-r:y+r,x-r:x+r].reshape(-1,3); l=lab[y-r:y+r,x-r:x+r].reshape(-1,3)
    print(f"{k:7s} HSV med {np.median(h,0)} LAB med {np.median(l,0)}")
    cv2.rectangle(vis,(x-r,y-r),(x+r,y+r),(0,255,0),3); cv2.putText(vis,k,(x+15,y),0,1.2,(0,255,0),3)
cv2.imwrite('frames/stageA/e37_f0_probe.jpg', cv2.resize(vis,None,fx=0.5,fy=0.5))
