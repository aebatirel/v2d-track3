"""Interlock design probe (dev, GT-free): where does the partner enter each board, in the board's own frame, along our
ep24 track? Persistence per voxel, state of entered voxels (OBSERVED/FREE/UNKNOWN), inside the HULL/SHELL candidates,
relative motion. Reads only the dev bundle (obs_all + our tracks) and the dev candidates. No scan, no mocap."""
import json, sys, numpy as np, trimesh
sys.path.insert(0, '/home/user/v2d-track3/docs/research/mesh-2026-10-26')
from gmg import bundle as BU, contact as CT, geom
S = '/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad'
RUN = f'{S}/gmg/runs-dev/' + (sys.argv[1] if len(sys.argv) > 1 else '20261030-b5pool24-edba5b3')
EP = sys.argv[2] if len(sys.argv) > 2 else '24'
b = BU.load_bundle(f'{RUN}/bundle/public/ep{EP}')
out = {}
for t in b.objects:
    for p in b.partners(t):
        obs = b.obs(t); lo = np.asarray(obs['lo']); vox = float(obs['vox']); st = np.asarray(obs['state'])
        shape = st.shape
        cf = sorted(set(b.contact(t, p)['contact']))
        X, N, fid, n_p = CT.partner_samples(b, t, p, cf)
        vi, ok = CT._vox_index(X, lo, vox, shape)
        lin = np.ravel_multi_index(tuple(vi[ok].T), shape); f_ok = fid[ok]
        # distinct frames per voxel
        key = np.unique(lin * 100000 + f_ok)
        cnt = np.bincount(key // 100000, minlength=st.size).reshape(shape)
        # candidate occupancy at voxel centres
        G = np.stack(np.meshgrid(*[lo[k] + vox * (np.arange(shape[k]) + 0.5) for k in range(3)], indexing='ij'), -1).reshape(-1, 3)
        rec = dict(contact_frames=len(cf), n_partner_samples=int(n_p))
        # PCA of owned points (board frame axes)
        P = np.asarray(obs['pts'])[::50]; c = P.mean(0); U = np.linalg.svd(P - c, full_matrices=False)[2]
        ext = np.percentile((P - c) @ U.T, [1, 99], axis=0)
        rec['own_extent_mm_p1_p99'] = np.round((ext[1] - ext[0]) * 1e3, 1).tolist()
        for kind in ['hull', 'shell_t5p36']:
            fn = f'{RUN}/cand/public/ep{EP}/{t}/{kind}.glb'
            try:
                m = trimesh.load(fn, force='mesh')
            except Exception as e:
                continue
            ins, _ = geom.inside(m, G)
            ins = ins.reshape(shape)
            for nmin_frac in (0.0, 0.1, 0.25, 0.5):
                nmin = max(1, int(np.ceil(nmin_frac * len(cf))))
                E = ins & (cnt >= nmin)
                sts = np.bincount(st[E], minlength=3)
                r = dict(n_vox=int(E.sum()), cm3=round(E.sum() * vox ** 3 * 1e6, 2),
                         state_unknown_free_observed=sts.tolist())
                if E.sum() >= 3:
                    C = G[E.ravel()]; A = (C - c) @ U.T
                    r['extent_mm_pca'] = np.round((A.max(0) - A.min(0)) * 1e3, 1).tolist()
                    r['centre_mm_pca'] = np.round(A.mean(0) * 1e3, 1).tolist()
                rec[f'{kind}_nmin{nmin}'] = r
        # relative motion of the partner origin in the target frame over contact frames
        tr = np.array([CT.rel(b.poses, t, p, f)[:3, 3] for f in cf])
        rec['partner_origin_range_mm'] = np.round((tr.max(0) - tr.min(0)) * 1e3, 1).tolist()
        # per frame intrusion count into the hull (time course)
        try:
            mh = trimesh.load(f'{RUN}/cand/public/ep{EP}/{t}/hull.glb', force='mesh')
            insh = ins_h = geom.inside(mh, G)[0].reshape(shape)
            per = []
            for f in cf:
                s = f_ok == f
                ii = np.unravel_index(lin[s], shape)
                per.append(int(np.unique(lin[s][insh[ii]]).size))
            per = np.array(per)
            rec['hull_entered_vox_per_frame'] = dict(p50=float(np.median(per)), p90=float(np.percentile(per, 90)),
                                                     max=int(per.max()), frames_ge10=int((per >= 10).sum()))
            # frames with intrusion: partner origin range during them
            k = per >= 10
            if k.sum() >= 2:
                rec['partner_origin_range_mm_intrusion_frames'] = np.round((tr[k].max(0) - tr[k].min(0)) * 1e3, 1).tolist()
                rec['intrusion_frames_first_last'] = [int(np.array(cf)[k][0]), int(np.array(cf)[k][-1])]
        except Exception as e:
            rec['err'] = str(e)
        out[f'{t}<-{p}'] = rec
print(json.dumps(out, indent=1))
