# GT-free [M]: profile of ep31 observed points (our frame) by z slices
import numpy as np
from scipy.spatial import cKDTree
S='/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad'
z=np.load(f'{S}/obs_all/ep31_mini_sweeper.npz'); p=z['pts'].astype(float); fr=z['frame']
# outlier removal: points with < 20 neighbours within 3 mm among a 200k subsample
rng=np.random.default_rng(0); sub=p[rng.choice(len(p),200000,replace=False)]
T=cKDTree(sub); cnt=np.array([len(x) for x in T.query_ball_point(p[::5],0.003)])
print('density p5/p50', np.percentile(cnt,[1,5,50]))
keep=np.ones(len(p),bool)
cnt_all=T.query_ball_point(p,0.003,return_length=True); keep=cnt_all>=8
print('kept', keep.mean())
p=p[keep]; np.save('ep31_clean.npy', p.astype(np.float32))
print('bbox cm', np.round(p.min(0)*100,2), np.round(p.max(0)*100,2))
for zc in np.arange(-6.5,8.6,0.5):
    s=p[np.abs(p[:,2]*100-zc)<0.25]
    if len(s)<50: print('z=%.1f n=%d'%(zc,len(s))); continue
    print('z=%5.1f n=%6d  y %6.2f..%6.2f (w %.2f)  x p2 %.2f p50 %.2f p98 %.2f'%(zc,len(s),*(np.percentile(s[:,1],[1,99])*100),np.ptp(np.percentile(s[:,1],[1,99]))*100,*(np.percentile(s[:,0],[2,50,98])*100)))
