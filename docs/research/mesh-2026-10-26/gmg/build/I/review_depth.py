import sys, json, numpy as np, trimesh
sys.path.insert(0, '/home/user/v2d-track3/docs/research/mesh-2026-10-26')
from gmg import bundle as BU, contact as CT, geom
S = '/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad'
RUN = f'{S}/gmg/runs-dev/20261030-b5pool24-edba5b3'
b = BU.load_bundle(f'{RUN}/bundle/public/ep24')
for t in b.objects:
    p = b.partners(t)[0]
    obs = b.obs(t); lo = np.asarray(obs['lo']); vox = float(obs['vox']); shape = obs['state'].shape
    cf = np.array(sorted(set(b.contact(t, p)['contact'])))
    X, N, fid, n_p = CT.partner_samples(b, t, p, cf)
    print(t, 'partner samples', X.shape, 'n_p', n_p if np.isscalar(n_p) else np.shape(n_p))
    for kind in ('hull', 'shell_t5p36'):
        m = trimesh.load(f'{RUN}/cand/public/ep24/{t}/{kind}.glb', force='mesh')
        # oriented extents
        ext = m.bounding_box_oriented.primitive.extents
        ins = geom.inside(m, X)[0]
        d = np.zeros(len(X)); 
        if ins.any(): d[ins] = geom.Closest(m).query(X[ins])[0]
        # trimesh check of distance
        if ins.any():
            pq = trimesh.proximity.ProximityQuery(m); d2 = np.abs(pq.signed_distance(X[ins][:2000]))
        else: d2 = np.zeros(1)
        per = np.array([ins[fid == f].sum() for f in cf])
        print(' ', kind, 'OBB extents mm', np.round(np.sort(ext) * 1e3, 1), 'vol cm3', round(m.volume * 1e6, 1),
              'frames with >=3 samples inside', int((per >= 3).sum()), 'inside samples', int(ins.sum()),
              'depth p50/p99/max mm', np.round(np.percentile(d[ins], [50, 99, 100]) * 1e3, 1) if ins.any() else None,
              'trimesh depth p99/max', np.round(np.percentile(d2, [99, 100]) * 1e3, 1))
