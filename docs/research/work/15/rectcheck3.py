import cv2, json, numpy as np, itertools
exec(open('rectcheck.py').read().split("def run(")[0])
ca=C['cameras']['ego_cam_a']; Ta=np.array(ca['extrinsics_to_stereo_left'])
def KDa(rot):
    K=np.array(ca['intrinsic_matrix'],float); D=np.array(ca['distortion_coefficients'],float)
    if rot: K=K.copy(); K[0,2]=2028-1-K[0,2]; K[1,2]=1520-1-K[1,2]; D=D.copy(); D[2]*=-1; D[3]*=-1; D[8:12]*=-1
    return K,D
for ep in [3,20]:
    idx=[0,60,120,180]
    A=frames('evaluation','a',ep,idx); B=frames('evaluation','b',ep,idx)
    orb=cv2.ORB_create(5000); bf=cv2.BFMatcher(cv2.NORM_HAMMING,crossCheck=True); pa=[];pb=[]
    for i in idx:
        a=cv2.resize(A[i],(1014,760),interpolation=cv2.INTER_AREA)
        k1,d1=orb.detectAndCompute(a,None); k2,d2=orb.detectAndCompute(B[i],None)
        for mm in bf.match(d1,d2):
            p=np.array(k1[mm.queryIdx].pt)*2.0; q=k2[mm.trainIdx].pt; pa.append(p); pb.append(q)
    pa=np.array(pa); pb=np.array(pb); _,mk=cv2.findFundamentalMat(pa,pb,cv2.FM_RANSAC,2.0,0.999); mk=mk.ravel()>0; pa=pa[mk]; pb=pb[mk]
    # undistort to normalized coords first then RANSAC essential to keep inliers
    out=[]
    for rotK,inv in itertools.product([0,1],[0,1]):
        KA,DA=KDa(rotK); KB,DB=KD(cb,0)
        na=cv2.undistortPoints(pa.reshape(-1,1,2),KA,DA).reshape(-1,2); nb=cv2.undistortPoints(pb.reshape(-1,1,2),KB,DB).reshape(-1,2)
        Tm=np.linalg.inv(Ta) if inv else Ta; R=Tm[:3,:3]; t=Tm[:3,3]
        tx=np.array([[0,-t[2],t[1]],[t[2],0,-t[0]],[-t[1],t[0],0]]); Em=tx@R
        xa=np.c_[na,np.ones(len(na))]; xb=np.c_[nb,np.ones(len(nb))]
        l=(Em@xa.T).T; d=np.abs(np.sum(l*xb,1))/np.hypot(l[:,0],l[:,1])*565  # epipolar dist in b pixels
        out.append((np.median(d), f"ep{ep} rotK_a={rotK} inv={inv} n={len(d)} med_epi_px={np.median(d):.2f} frac<2px={np.mean(d<2):.2f}"))
    for s,l in sorted(out): print(l)
    # essential-matrix estimate vs calibration
    for rotK in [0,1]:
        KA,DA=KDa(rotK); KB,DB=KD(cb,0)
        na=cv2.undistortPoints(pa.reshape(-1,1,2),KA,DA).reshape(-1,2); nb=cv2.undistortPoints(pb.reshape(-1,1,2),KB,DB).reshape(-1,2)
        Em,mk=cv2.findEssentialMat(na,nb,np.eye(3),cv2.RANSAC,0.999,1.5/565)
        _,R,t,_=cv2.recoverPose(Em,na,nb,np.eye(3),mask=mk)
        Rg=Ta[:3,:3]; tg=Ta[:3,3]/np.linalg.norm(Ta[:3,3])
        ang=np.degrees(np.arccos(np.clip((np.trace(R.T@Rg)-1)/2,-1,1)))
        rv=cv2.Rodrigues(R@Rg.T)[0].ravel()
        print(f"  ep{ep} rotK={rotK} inl={int(mk.sum())} dR_deg={ang:.2f} dR_axis_deg={np.degrees(rv).round(2)} t_est={t.ravel().round(3)} t_cal={tg.round(3)}")
