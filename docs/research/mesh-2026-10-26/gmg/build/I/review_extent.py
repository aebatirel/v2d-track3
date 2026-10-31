import sys, json, numpy as np
sys.path.insert(0, '/home/user/v2d-track3/docs/research/mesh-2026-10-26')
from gmg import bundle as BU
S = '/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad'
RUN = f'{S}/gmg/runs-dev/20261030-b5pool24-edba5b3'
b = BU.load_bundle(f'{RUN}/bundle/public/ep24')
for t in b.objects:
    obs = b.obs(t); P = np.asarray(obs['pts'])[::50]; c = P.mean(0)
    U = np.linalg.svd(P - c, full_matrices=False)[2]; A = (P - c) @ U.T
    lo, hi = np.percentile(A, 1, 0), np.percentile(A, 99, 0)
    st = np.asarray(obs['state'])
    print(t, 'pca 1-99% extent mm', np.round((hi - lo) * 1e3, 1), 'n_obs_vox', int((st == 2).sum()), 'obs cm3', round((st==2).sum()*obs['vox']**3*1e6,1), 'own', np.unique(obs['own']))
