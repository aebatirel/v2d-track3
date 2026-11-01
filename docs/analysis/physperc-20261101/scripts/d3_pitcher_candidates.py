import sys, json, numpy as np
S=sys.argv[1]; sys.path.insert(0,f'{S}/kit/v2d_submission_kit'); sys.path.insert(0,'/home/user/v2d-track3/docs/analysis/physperc-20261101/scripts')
from v2dlb import track3_pose as T3; from v2dlb.mesh_budget import budget_mesh; from v2dlb.object_mesh import _surface_moments
import physlib as PL
from scipy.spatial import cKDTree
ang=lambda a,b: float(np.degrees(np.arccos(np.clip(np.dot(a,b)/np.linalg.norm(a)/np.linalg.norm(b),-1,1))))
D1=json.load(open('/home/user/v2d-track3/docs/analysis/physperc-20261101/diag/d1_tilt_9a.json'))
v3=f'{S}/mesh9a/water_pitcher.glb'; pv=PL.surf_pts(v3)
for cand in [v3, f'{S}/pitch/water_pitcher_t3fit.glb', f'{S}/pitch/ep22_water_pitcher_g1_a2.glb']:
    pc=PL.surf_pts(cand); cd=(cKDTree(pc).query(pv)[0].mean()+cKDTree(pv).query(pc)[0].mean())/2
    print('==',cand.split('/')[-1],'chamfer to v3 (same frame?) %.1f mm'%(cd*1000), 'bounds', np.round(PL.mesh(cand).bounds*100,1).tolist(), 'watertight', PL.mesh(cand).is_watertight)
    for e in (21,22):
        D=D1[str(e)]['water_pitcher']
        sv,sf=PL.load_vf(PL.scan_path(S,'water_pitcher')); c,_=_surface_moments(sv,sf)
        ca,B=T3._register_object_body(budget_mesh(v3,4096,4096),(sv,sf),c,1_000_003*e+101*1)   # tracker template frame -> scan
        gt=np.array(D['g_true']); gb=B.T@np.array(D['g_ours'])
        sp=PL.stable_poses(cand); k,m=PL.nearest_stable(sp,gb)
        Nf,Af=PL.hull_facets.__wrapped__(cand,1e-4); kf=int(np.argmax(Nf@gb))
        print('  ep',e,'now %.2f'%D['e_now'],'| stable %.2f (match %.1f, p %.2f)'%(ang(B@sp['down'][k],gt),m,sp['prob'][k]),'| contact facet %.2f (match %.1f, %.1f cm2)'%(ang(B@Nf[kf],gt),ang(Nf[kf],gb),Af[kf]*1e4))
