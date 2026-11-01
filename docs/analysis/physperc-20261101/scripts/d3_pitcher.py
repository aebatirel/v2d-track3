import sys, json, numpy as np
S=sys.argv[1]; sys.path.insert(0,f'{S}/kit/v2d_submission_kit'); sys.path.insert(0,'/home/user/v2d-track3/docs/analysis/physperc-20261101/scripts')
from v2dlb import track3_pose as T3; from v2dlb.mesh_budget import budget_mesh; from v2dlb.object_mesh import _surface_moments
import physlib as PL
ang=lambda a,b: float(np.degrees(np.arccos(np.clip(np.dot(a,b)/np.linalg.norm(a)/np.linalg.norm(b),-1,1))))
D1=json.load(open('/home/user/v2d-track3/docs/analysis/physperc-20261101/diag/d1_tilt_9a.json'))
for mn in ['mesh9a']:
 for e,n in [(21,'water_pitcher'),(22,'water_pitcher'),(39,'mini_dust_pan'),(40,'mini_dust_pan'),(18,'mini_dust_pan'),(31,'mini_sweeper'),(41,'white_pot'),(24,'wooden_piece_1')]:
    D=D1[str(e)][n]; mp=f'{S}/{mn}/{n}.glb'
    sv,sf=PL.load_vf(PL.scan_path(S,n)); c,_=_surface_moments(sv,sf)
    ca,B=T3._register_object_body(budget_mesh(mp,4096,4096),(sv,sf),c,1_000_003*e+101*D['slot'])
    gt=np.array(D['g_true']); go=np.array(D['g_ours']); gb=B.T@go
    Nf,Af=PL.hull_facets.__wrapped__(mp,1e-4); k=int(np.argmax(Nf@gb))
    # lowest-points plane: hull vertices within band of the lowest point along gb, plane fit
    V=np.asarray(PL.mesh(mp).convex_hull.vertices); h=V@gb
    res=[]
    for band in (0.002,0.005,0.01):
        Q=V[h>=h.max()-band]
        if len(Q)>=3:
            w,U=np.linalg.eigh(np.cov((Q-Q.mean(0)).T)); nrm=U[:,0]*np.sign(U[:,0]@gb); res.append('band%dmm %5.2f (m%4.1f, n%d)'%(band*1000,ang(B@nrm,gt),ang(nrm,gb),len(Q)))
    print(e,n[:13].ljust(13),'now %5.2f stable %5.2f facet %5.2f (m%4.1f, %.1fcm2)'%(D['e_now'],D['e_prior'],ang(B@Nf[k],gt),ang(Nf[k],gb),Af[k]*1e4),' | '.join(res))
