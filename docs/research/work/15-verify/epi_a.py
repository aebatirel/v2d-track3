# colour a vs mono b/c: epipolar error for ego_cam_a extrinsics_to_stereo_left hypotheses
import cv2, json, numpy as np, sys
exec(open('epi_bc.py').read().split('for split,ep in')[0])
ca=C['cameras']['ego_cam_a']; Ta=np.array(ca['extrinsics_to_stereo_left'])
Ka=np.array(ca['intrinsic_matrix'],float); Da=np.array(ca['distortion_coefficients'],float)
def fa(split,ep,idx):
    c=cv2.VideoCapture(V%(split,'a',ep)); out={}
    for i in idx:
        c.set(cv2.CAP_PROP_POS_FRAMES,i); ok,f=c.read(); out[i]=cv2.resize(cv2.cvtColor(f,cv2.COLOR_BGR2GRAY),(1014,760),interpolation=cv2.INTER_AREA)
    return out
split,ep=sys.argv[1],int(sys.argv[2]); idx=[int(x) for x in __import__("os").environ.get("IDX","0,50,100,150").split(",")]
A=fa(split,ep,idx)
for mono in sys.argv[3:]:
    B=frames(split,mono,ep,idx); pa=[];pb=[]
    for i in idx:
        k1,d1=sift.detectAndCompute(A[i],None); k2,d2=sift.detectAndCompute(B[i],None)
        for m,n in cv2.BFMatcher().knnMatch(d1,d2,k=2):
            if m.distance<0.7*n.distance: pa.append(np.array(k1[m.queryIdx].pt)*2); pb.append(k2[m.trainIdx].pt)
    pa=np.array(pa); pb=np.array(pb); _,mk=cv2.findFundamentalMat(pa,pb,cv2.FM_RANSAC,2.0,0.999); mk=mk.ravel()>0; pa,pb=pa[mk],pb[mk]
    Km,Dm=KD(mono,0)
    for inv in [0,1]:
        Tm=np.linalg.inv(Ta) if inv else Ta
        d=epi(pa,pb,Ka,Da,Km,Dm,Tm[:3,:3],Tm[:3,3])
        print(f'{split} {ep} a->{mono} inv={inv} n={len(d)} med={np.median(d):.2f}px p90={np.percentile(d,90):.2f}')
    # composite: a->c->b using pair T (if mono b, compose a->c then c->b)
    if mono=='b':
        Tc=T@Ta; d=epi(pa,pb,Ka,Da,Km,Dm,Tc[:3,:3],Tc[:3,3]); print(f'  a->c(Ta) then c->b(T): med={np.median(d):.2f}')
    print('  median x_a(scaled to mono f) - x_mono:', np.median(pa[:,0]*565/1150 - pb[:,0]).round(1))
