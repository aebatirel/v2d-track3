"""Which intrinsics/extrinsics convention fits the stored (upright) ego mono frames? Measure post-rectification |dy|."""
import cv2, json, numpy as np, sys
C=json.load(open('/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public/meta/camera_calibration.json'))
E='/Users/aebatirel/Documents/Code/v2d-research/data/track_3/%s/videos/chunk-000/observation.images.ego_cam_%s/episode_%06d.mp4'
def frames(split,cam,ep,idx):
    c=cv2.VideoCapture(E%(split,cam,ep)); out={}; i=0
    while i<=max(idx):
        ok,f=c.read()
        if not ok: break
        if i in idx: out[i]=cv2.cvtColor(f,cv2.COLOR_BGR2GRAY)
        i+=1
    return out
cb,cc=C['cameras']['ego_cam_b'],C['cameras']['ego_cam_c']
pair=[p for p in C['stereo_pairs'] if p['camera']=='ego'][0]
W,H=1280,800
def KD(cam,rot):
    K=np.array(cam['intrinsic_matrix'],float); D=np.array(cam['distortion_coefficients'],float)
    if rot:
        K=K.copy(); K[0,2]=W-1-K[0,2]; K[1,2]=H-1-K[1,2]
        D=D.copy(); D[2]*=-1; D[3]*=-1; D[8:12]*=-1  # tangential + thin prism flip under 180 deg
    return K,D
F=np.diag([-1,-1,1.0])
T=np.array(pair['left_to_right'])  # as given: left=c, right=b
def run(split,ep,idx):
    A=frames(split,'c',ep,idx); B=frames(split,'b',ep,idx)
    orb=cv2.ORB_create(4000); bf=cv2.BFMatcher(cv2.NORM_HAMMING,crossCheck=True)
    ptsL=[];ptsR=[]
    for i in idx:
        k1,d1=orb.detectAndCompute(A[i],None); k2,d2=orb.detectAndCompute(B[i],None)
        m=bf.match(d1,d2)
        for mm in m:
            p=k1[mm.queryIdx].pt; q=k2[mm.trainIdx].pt
            if abs(p[1]-q[1])<40 and -5<p[0]-q[0]<200: ptsL.append(p); ptsR.append(q)
    pL=np.array(ptsL,float).reshape(-1,1,2); pR=np.array(ptsR,float).reshape(-1,1,2)
    res={}
    for name,rotK,conj in [('as_given',0,0),('rotK_only',1,0),('rotK_conjRt',1,1),('conjRt_only',0,1)]:
        KL,DL=KD(cc,rotK); KR,DR=KD(cb,rotK)
        R=T[:3,:3]; t=T[:3,3]
        if conj: R=F@R@F; t=F@t
        R1,R2,P1,P2,Q,_,_=cv2.stereoRectify(KL,DL,KR,DR,(W,H),R,t.reshape(3,1),alpha=0)
        uL=cv2.undistortPoints(pL,KL,DL,R=R1,P=P1).reshape(-1,2); uR=cv2.undistortPoints(pR,KR,DR,R=R2,P=P2).reshape(-1,2)
        dy=uL[:,1]-uR[:,1]; dx=uL[:,0]-uR[:,0]
        good=np.abs(dy)<20
        res[name]=(np.median(np.abs(dy[good])), np.mean(good), np.median(dx[good]), P2[0,3]/P2[0,0])
    print(split,ep,'n',len(pL), {k:tuple(round(float(x),3) for x in v) for k,v in res.items()})
for split,ep in [('evaluation',3),('evaluation',20),('evaluation',35)]:
    run(split,ep,[0,60,120,180])
