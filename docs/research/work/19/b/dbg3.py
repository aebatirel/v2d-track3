import sys, numpy as np, trimesh, igl
sys.path.insert(0,'.'); from common import *
n=sys.argv[1]; m=scan_welded(n); d=np.load(sys.argv[2]); W=(d['v'],d['f'])
bodies=sorted(m.split(only_watertight=False),key=lambda t:-len(t.faces))
for b in bodies[:3]:
    q=b.sample(50000); dq=np.sqrt(igl.point_mesh_squared_distance(q,W[0],W[1])[0])*1e3
    sdq=igl.signed_distance(q,W[0],W[1])[0]*1e3
    print('body F',len(b.faces),'scan->W mm p50 %.2f p99 %.2f max %.2f >1mm %.2f%%'%(np.median(dq),np.percentile(dq,99),dq.max(),np.mean(dq>1)*100),
          ' far pts outside W: %.2f%% inside W: %.2f%%'%(np.mean(sdq>1)*100,np.mean(sdq<-1)*100))
    far=q[dq>1]
    if len(far): print('   far bbox mm',np.round(far.min(0)*1e3,1).tolist(),np.round(far.max(0)*1e3,1).tolist())
