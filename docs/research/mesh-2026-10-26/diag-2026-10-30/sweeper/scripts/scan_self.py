# [D] scan registered to itself (independent samples): basin margin = the best achievable flip margin (markers only)
import sys, numpy as np
sys.path.insert(0,'scripts'); sys.path.insert(0,'/home/user/v2d-track3/docs/research/mesh-2026-10-26/scripts')
import mesh_metric as MM
from margin import basins
ref = MM.reference('mini_sweeper')
for s in [19000057, 30000090, 11]:
    # candidate = scan with a different sampling seed: emulate by passing seed+7 for candidate sampling
    A=MM.auc; v,f=ref['v'],ref['f']
    cc,cr=A._surface_moments(v,f)
    rp=A._sample_mesh_surface(v,f,3000,s)-cc; cp=A._sample_mesh_surface(v,f,3000,s+7)-cc
    import math
    best={'ok':math.inf,'flip':math.inf}
    for st in A._initial_rotations(rp,cp,A._ALIGNMENT_STARTS):
        R,t,d=MM.icp_from(rp,cp,st); ang=MM.angle_deg(R)
        if ang<30: best['ok']=min(best['ok'],d)
        elif ang>150: best['flip']=min(best['flip'],d)
    print('scan-vs-scan seed',s,'ok %.3f flip %.3f margin %.3f mm'%(best['ok']*1e3,best['flip']*1e3,(best['flip']-best['ok'])*1e3))
