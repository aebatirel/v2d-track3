import numpy as np, trimesh, json
S='/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad'
G=f'{S}/gen/mesh-20261029-gen-f3fbeb0/results/gen'
c={'library_v3':'/home/user/v2d-track3/meshes/library_v3/mini_sweeper.glb'}
for m in ['sam3d','trellis2','triposg','hy21']:
    for s in [42,7]: c[f'{m}_s{s}']=f'{G}/{m}_sim3/mini_sweeper_k270_s{s}.ply'
for s in [42,7]: c[f'pixal_mv_s{s}']=f'{G}/pixal_mv/ep31_mini_sweeper_s{s}.ply'
sc=np.load('scan_samples.npz')['p']
def pc(P):
    c0=P.mean(0); w,V=np.linalg.eigh(np.cov((P-c0).T)); V=V[:,::-1]; Q=(P-c0)@V
    ext=np.ptp(Q,0); return ext, V
es,Vs=pc(sc[::4])
print('%-16s %-22s %-24s %s'%('mesh','PCA extents cm (L,W,T)','normalised to scan L', 'angle of long/thin axis vs our z/x (deg)'))
print('%-16s %-22s'%('SCAN[D]', np.round(es*100,2)))
for k,p in c.items():
    m=trimesh.load(p,force='mesh'); P=np.asarray(m.sample(80000))
    e,V=pc(P)
    a_long=np.degrees(np.arccos(abs(V[:,0]@[0,0,1]))); a_thin=np.degrees(np.arccos(abs(V[:,2]@[1,0,0])))
    print('%-16s %-22s %-24s long %.1f thin %.1f   W/L %.2f T/L %.2f (scan %.2f %.2f)'%(k, np.round(e*100,2), np.round(e/e[0]*es[0]*100,2), a_long, a_thin, e[1]/e[0], e[2]/e[0], es[1]/es[0], es[2]/es[0]))
