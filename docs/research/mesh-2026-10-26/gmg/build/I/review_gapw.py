import sys, json, numpy as np, trimesh
from scipy import ndimage
sys.path.insert(0, '/home/user/v2d-track3/docs/research/mesh-2026-10-26')
from gmg import bundle as BU, contact as CT, geom
S = '/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad'
RUN = f'{S}/gmg/runs-dev/20261030-b5pool24-edba5b3'
b = BU.load_bundle(f'{RUN}/bundle/public/ep24')
K = np.asarray(b.meta['K']); print('K fx', K[0][0], 'cx', K[0][2])
for t in b.objects:
    p = b.partners(t)[0]
    obs = b.obs(t); lo = np.asarray(obs['lo']); vox = float(obs['vox']); st = np.asarray(obs['state']); shape = st.shape
    cf = np.array(sorted(set(b.contact(t, p)['contact'])))
    X, N, fid, n_p = CT.partner_samples(b, t, p, cf)
    vi, ok = CT._vox_index(X, lo, vox, shape); lin = np.ravel_multi_index(tuple(vi[ok].T), shape); f_ok = fid[ok]
    G = np.stack(np.meshgrid(*[lo[k] + vox * (np.arange(shape[k]) + 0.5) for k in range(3)], indexing='ij'), -1).reshape(-1, 3)
    # camera range: mean distance of target points to their camera
    rng = np.linalg.norm(np.asarray(obs['pts']) - np.asarray(obs['cam']), axis=1) if np.asarray(obs['cam']).shape == np.asarray(obs['pts']).shape else None
    for kind in ('hull', 'shell_t5p36'):
        m = trimesh.load(f'{RUN}/cand/public/ep24/{t}/{kind}.glb', force='mesh'); ins = geom.inside(m, G)[0]
        per = {}; 
        for f in cf:
            s = np.unique(lin[f_ok == f]); per[int(f)] = s[ins[s]]
        eng = [f for f in cf if len(per[int(f)]) >= 3]; Nrun = len(eng)
        nmin = max(5, int(np.ceil(0.25 * Nrun)))
        cnt = np.zeros(G.shape[0], int)
        for f in eng: cnt[per[int(f)]] += 1
        E = (cnt >= nmin).reshape(shape)
        lab, n = ndimage.label(E, structure=np.ones((3, 3, 3)))
        sizes = ndimage.sum(E, lab, range(1, n + 1))
        w = 2 * ndimage.distance_transform_edt(np.pad(E, 1)).max() * vox
        # PCA extents of the region
        C = G[E.ravel()]; U = np.linalg.svd(C - C.mean(0), full_matrices=False)[2]; A = (C - C.mean(0)) @ U.T
        ext = np.percentile(A, 99, 0) - np.percentile(A, 1, 0)
        print(t, kind, 'Nrun', Nrun, 'nmin', nmin, 'cm3', round(E.sum() * vox ** 3 * 1e6, 2), 'components', n, 'largest', int(sizes.max()) if n else 0,
              'inscribed width mm', round(w * 1e3, 1), 'region PCA 1-99 extents mm', np.round(ext * 1e3, 1), 'observed share', round(float((st[E] == 2).mean()), 3))
    if rng is not None: print('  target median camera range m', round(float(np.median(rng)), 3))
