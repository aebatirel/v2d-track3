import cv2, numpy as np, json, sys
ep, fr, box = sys.argv[1], int(sys.argv[2]), [int(v) for v in sys.argv[3].split(',')]  # x0,y0,x1,y1
img = cv2.imread(f'frames/stageA/e{ep}_f{fr}.png'); x0,y0,x1,y1 = box
cal = json.load(open('/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public/meta/camera_calibration.json'))['cameras']['ego_cam_a']
K = np.array(cal['intrinsic_matrix']); D = np.array(cal['distortion_coefficients'])
if len(sys.argv)>4:
    ex=[int(v) for v in sys.argv[4].split(",")]; img=img.copy(); img[ex[1]:ex[3],ex[0]:ex[2]]=(0,0,0)
sub = img[y0:y1, x0:x1]; hsv = cv2.cvtColor(sub, cv2.COLOR_BGR2HSV)
H,S,V = [hsv[...,i].astype(int) for i in range(3)]
wood = ((S>48)&(S<130)&(V>170)&(H<25)).astype(np.uint8)
wood = cv2.morphologyEx(wood, cv2.MORPH_OPEN, np.ones((5,5),np.uint8)); n,lab,st,_ = cv2.connectedComponentsWithStats(wood); k = 1+np.argmax(st[1:,4]); m = (lab==k).astype(np.uint8)
m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((7,7),np.uint8))
grey = ((S<45)&(V>110)&(V<235)).astype(np.uint8)   # marker spheres (grey, unsaturated)
n2,lab2,st2,cen2 = cv2.connectedComponentsWithStats(grey)
def und(pts):  # pixel -> normalized (raw-orientation K assumed)
    return cv2.undistortPoints(pts.reshape(-1,1,2).astype(np.float64), K, D).reshape(-1,2)
ys,xs = np.nonzero(m); P = und(np.c_[xs+x0, ys+y0])
c = P.mean(0); U,s,Vt = np.linalg.svd(P-c, full_matrices=False); a = (P-c)@Vt.T
L = a[:,0].max()-a[:,0].min(); W = a[:,1].max()-a[:,1].min()
print('axis min/max', a[:,0].min(), a[:,0].max())
print(f'spoon px area {m.sum()}  normalized length {L:.4f} width(max) {W:.4f}')
# width profile along axis
bins = np.linspace(a[:,0].min(), a[:,0].max(), 21)
prof = [np.ptp(a[(a[:,0]>=bins[i])&(a[:,0]<bins[i+1]),1]) if np.any((a[:,0]>=bins[i])&(a[:,0]<bins[i+1])) else 0 for i in range(20)]
for i in range(1,n2):
    if 150 < st2[i,4] < 3000:
        bw, bh = st2[i,2], st2[i,3]
        if 0.6 < bw/bh < 1.6:
            cx, cy = cen2[i]+[x0,y0]; e = und(np.array([[cx-bw/2,cy],[cx+bw/2,cy],[cx,cy-bh/2],[cx,cy+bh/2]]))
            d = 0.5*(np.linalg.norm(e[0]-e[1])+np.linalg.norm(e[2]-e[3]))
            pa = (und(np.array([[cx,cy]]))-c)@Vt.T
            print(f'blob at ({cx:.0f},{cy:.0f}) px {bw}x{bh} area {st2[i,4]} normdiam {d:.4f}  axis pos {pa[0,0]:+.4f},{pa[0,1]:+.4f}  -> L/d={L/d:.1f} W/d={W/d:.2f}  prof/d={np.round(np.array(prof)/d,2).tolist()}')
vis = sub.copy(); vis[m>0] = (0.5*vis[m>0] + [0,0,127]).astype(np.uint8); vis[grey>0]=(255,255,0)
cv2.imwrite(f'frames/stageA/e{ep}_f{fr}_size.jpg', vis)
