import cv2, json, numpy as np, itertools
exec(open('rectcheck.py').read().split("def run(")[0])
def collect(split,ep,idx):
    A=frames(split,'c',ep,idx); B=frames(split,'b',ep,idx)
    orb=cv2.ORB_create(4000); bf=cv2.BFMatcher(cv2.NORM_HAMMING,crossCheck=True); pc=[];pb=[]
    for i in idx:
        k1,d1=orb.detectAndCompute(A[i],None); k2,d2=orb.detectAndCompute(B[i],None)
        for mm in bf.match(d1,d2):
            p=k1[mm.queryIdx].pt; q=k2[mm.trainIdx].pt
            if abs(p[1]-q[1])<40 and abs(p[0]-q[0])<200: pc.append(p); pb.append(q)
    pc=np.array(pc,float); pb=np.array(pb,float)
    Fm,mask=cv2.findFundamentalMat(pc,pb,cv2.FM_RANSAC,1.0,0.999); mask=mask.ravel()>0
    return pc[mask],pb[mask]
for split,ep in [('evaluation',3),('evaluation',20)]:
    pc,pb=collect(split,ep,[0,60,120,180]); print(split,ep,'inliers',len(pc))
    out=[]
    for leftcam,inv,rotK,conj,nodist in itertools.product('cb',[0,1],[0,1],[0,1],[0,1]):
        Tm=np.linalg.inv(T) if inv else T
        R=Tm[:3,:3]; t=Tm[:3,3]
        if conj: R=F@R@F; t=F@t
        (KL,DL),(KR,DR)=(KD(cc,rotK),KD(cb,rotK)) if leftcam=='c' else (KD(cb,rotK),KD(cc,rotK))
        if nodist: DL=DL*0; DR=DR*0
        pL,pR=(pc,pb) if leftcam=='c' else (pb,pc)
        try:
            R1,R2,P1,P2,Q,_,_=cv2.stereoRectify(KL,DL,KR,DR,(W,H),R,t.reshape(3,1),alpha=0)
        except cv2.error: continue
        uL=cv2.undistortPoints(pL.reshape(-1,1,2),KL,DL,R=R1,P=P1).reshape(-1,2); uR=cv2.undistortPoints(pR.reshape(-1,1,2),KR,DR,R=R2,P=P2).reshape(-1,2)
        dy=uL[:,1]-uR[:,1]; dx=uL[:,0]-uR[:,0]
        out.append((np.median(np.abs(dy)), f"left={leftcam} inv={inv} rotK={rotK} conj={conj} nodist={nodist} med|dy|={np.median(np.abs(dy)):.3f} p90={np.percentile(np.abs(dy),90):.2f} med_dx={np.median(dx):.1f} frac_dx>0={np.mean(dx>0):.2f}"))
    for s,l in sorted(out)[:6]: print('  ',l)
