# GT-free [M]: marker balls from ep31 observed points (protrusions on the +x face of the head)
import numpy as np, json
from scipy.spatial import cKDTree
from scipy.sparse.csgraph import connected_components
from scipy.sparse import coo_matrix
from scipy.optimize import least_squares
p=np.load('ep31_clean.npy').astype(float)
# head face plane: points of the head band (z -1.5..2.0) excluding protrusions; robust plane x = a + b*y + c*z on the 60th pct of x
band=p[(p[:,2]>-0.015)&(p[:,2]<0.02)]
face_x=np.percentile(band[:,0],60)
cand=band[band[:,0]>face_x+0.006]
print('head band n', len(band), 'face x ~ %.2f cm'%(face_x*100), 'protruding pts', len(cand))
t=cKDTree(cand); pr=t.query_pairs(0.003,output_type='ndarray')
nc,cl=connected_components(coo_matrix((np.ones(len(pr)),(pr[:,0],pr[:,1])),shape=(len(cand),)*2))
cnt=np.bincount(cl); order=np.argsort(-cnt)
balls=[]
for b in order[:5]:
    s=cand[cl==b]
    if len(s)<300: continue
    def res(q): return np.linalg.norm(s-q[:3],axis=1)-q[3]
    q0=np.r_[s.mean(0)-[0.004,0,0],0.007]
    r=least_squares(res,q0,loss='soft_l1',f_scale=0.001).x
    balls.append(dict(n=int(len(s)), centre_cm=np.round(r[:3]*100,2).tolist(), radius_mm=round(r[3]*1000,1), rms_mm=round(float(np.sqrt(np.mean(res(r)**2))*1000),2)))
    print(balls[-1])
json.dump(dict(face_x_cm=round(face_x*100,2), balls=balls), open('balls_obs.json','w'), indent=1)
