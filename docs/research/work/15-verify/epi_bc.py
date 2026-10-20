# Independent check: epipolar error of b<->c SIFT matches under calibration hypotheses (no stereoRectify).
import cv2, json, numpy as np, sys
C=json.load(open('/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public/meta/camera_calibration.json'))
V='/Users/aebatirel/Documents/Code/v2d-research/data/track_3/%s/videos/chunk-000/observation.images.ego_cam_%s/episode_%06d.mp4'
def frames(split,cam,ep,idx):
    c=cv2.VideoCapture(V%(split,cam,ep)); out={}
    for i in idx:
        c.set(cv2.CAP_PROP_POS_FRAMES,i); ok,f=c.read(); out[i]=cv2.cvtColor(f,cv2.COLOR_BGR2GRAY)
    return out
W,H=1280,800
cam={k:C['cameras']['ego_cam_'+k] for k in 'bc'}
pair=[p for p in C['stereo_pairs'] if p['camera']=='ego'][0]; T=np.array(pair['left_to_right'])
F=np.diag([-1.,-1,1])
def KD(k,rot):
    K=np.array(cam[k]['intrinsic_matrix'],float); D=np.array(cam[k]['distortion_coefficients'],float)
    if rot: K=K.copy(); K[0,2]=W-1-K[0,2]; K[1,2]=H-1-K[1,2]; D=D.copy(); D[2]*=-1; D[3]*=-1
    return K,D
sift=cv2.SIFT_create(3000)
def matches(split,ep,idx):
    A=frames(split,'c',ep,idx); B=frames(split,'b',ep,idx); pc=[];pb=[]
    for i in idx:
        k1,d1=sift.detectAndCompute(A[i],None); k2,d2=sift.detectAndCompute(B[i],None)
        mm=cv2.BFMatcher().knnMatch(d1,d2,k=2)
        for m,n in mm:
            if m.distance<0.7*n.distance: pc.append(k1[m.queryIdx].pt); pb.append(k2[m.trainIdx].pt)
    return np.array(pc),np.array(pb)
def epi(pl,pr,KL,DL,KR,DR,R,t,fpx=565):
    nl=cv2.undistortPoints(pl.reshape(-1,1,2),KL,DL).reshape(-1,2); nr=cv2.undistortPoints(pr.reshape(-1,1,2),KR,DR).reshape(-1,2)
    tx=np.array([[0,-t[2],t[1]],[t[2],0,-t[0]],[-t[1],t[0],0]]); E=tx@R
    xl=np.c_[nl,np.ones(len(nl))]; xr=np.c_[nr,np.ones(len(nr))]
    l=(E@xl.T).T; d=np.abs(np.sum(l*xr,1))/np.hypot(l[:,0],l[:,1])*fpx
    # also check cheirality-ish: disparity sign in normalized x after rough rectification
    return d
for split,ep in [(a,int(b)) for a,b in (s.split(':') for s in sys.argv[1:])]:
    pc,pb=matches(split,ep,[0,50,100,150])
    _,mk=cv2.findFundamentalMat(pc,pb,cv2.FM_RANSAC,1.5,0.999); mk=mk.ravel()>0; pc,pb=pc[mk],pb[mk]
    R=T[:3,:3]; t=T[:3,3]; Ti=np.linalg.inv(T)
    hyp={'given(L=c)':(pc,pb,KD('c',0),KD('b',0),R,t),
         'swapped(L=b,T)':(pb,pc,KD('b',0),KD('c',0),R,t),
         'given_inverseT':(pc,pb,KD('c',0),KD('b',0),Ti[:3,:3],Ti[:3,3]),
         'rotK+conj(L=c)':(pc,pb,KD('c',1),KD('b',1),F@R@F,F@t),
         'rotK_only(L=c)':(pc,pb,KD('c',1),KD('b',1),R,t),
         'conj_only(L=c)':(pc,pb,KD('c',0),KD('b',0),F@R@F,F@t)}
    print(split,ep,'F-inliers',len(pc))
    for k,(pl,pr,(KL,DL),(KR,DR),RR,tt) in hyp.items():
        d=epi(pl,pr,KL,DL,KR,DR,RR,tt); print(f'  {k:16s} med={np.median(d):6.2f}px p90={np.percentile(d,90):6.2f} frac<1px={np.mean(d<1):.2f}')
    # disparity sign: x_c - x_b for matched points (left image x should be larger)
    print('  median x_c-x_b raw px', np.median(pc[:,0]-pb[:,0]).round(1), 'frac>0', np.mean(pc[:,0]-pb[:,0]>0).round(2))
