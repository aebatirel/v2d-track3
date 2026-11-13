"""Interlock probe 3 (dev, GT-free): for every ordered pair (target <- partner) of a dev run, the partner's observed
samples moved into the target frame at contact frames; voxels inside each target candidate (hull, shell) entered in
>= nmin frames; their depth-state mix; the narrowest width of the entered region; the depth of entry below the
candidate surface; and the partner's relative motion during intrusion frames (travel, straightness)."""
import json, sys, numpy as np, trimesh
from scipy import ndimage
sys.path.insert(0, '/home/user/v2d-track3/docs/research/mesh-2026-10-26')
from gmg import bundle as BU, contact as CT, geom
S = '/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad'
RUN, EP = f'{S}/gmg/runs-dev/{sys.argv[1]}', sys.argv[2]
b = BU.load_bundle(f'{RUN}/bundle/public/ep{EP}')
out = {}
for t in b.objects:
    for p in b.partners(t):
        obs = b.obs(t); lo = np.asarray(obs['lo']); vox = float(obs['vox']); st = np.asarray(obs['state']).ravel(); shape = obs['state'].shape
        cf = np.array(sorted(set(b.contact(t, p)['contact'])))
        if not len(cf): continue
        X, N, fid, n_p = CT.partner_samples(b, t, p, cf)
        vi, ok = CT._vox_index(X, lo, vox, shape); lin = np.ravel_multi_index(tuple(vi[ok].T), shape); f_ok = fid[ok]
        G = np.stack(np.meshgrid(*[lo[k] + vox * (np.arange(shape[k]) + 0.5) for k in range(3)], indexing='ij'), -1).reshape(-1, 3)
        rec = dict(contact_frames=int(len(cf)), band_mm=round(b.band(t, p) * 1e3, 2))
        for kind in ('hull', 'shell_t5p36'):
            try: m = trimesh.load(f'{RUN}/cand/public/ep{EP}/{t}/{kind}.glb', force='mesh')
            except Exception: continue
            ins = geom.inside(m, G)[0]
            # depth of each voxel centre below the candidate surface (positive inside)
            dist = np.zeros(len(G)); dist[ins] = geom.Closest(m).query(G[ins])[0]
            cnt = np.zeros(len(G), int); per = []
            for f in cf:
                s = np.unique(lin[f_ok == f]); s = s[ins[s] & (dist[s] > b.band(t, p))]; cnt[s] += 1; per.append(len(s))
            per = np.array(per); k = per >= 3
            r = dict(frames_with_deep_entry=int(k.sum()))
            if k.sum() >= 2:
                fi = cf[k]; tr = np.array([CT.rel(b.poses, t, p, f)[:3, 3] for f in fi]); sv = np.linalg.svd(tr - tr.mean(0), compute_uv=False)
                r.update(travel_mm=round(float(np.linalg.norm(tr.max(0) - tr.min(0))) * 1e3, 1), straightness=round(float(sv[0] / max(sv.sum(), 1e-12)), 2),
                         first_last=[int(fi[0]), int(fi[-1])])
            for frac in (0.1, 0.25, 0.5):
                nmin = max(2, int(np.ceil(frac * len(cf)))); E = cnt >= nmin
                if E.sum() == 0: r[f'n{nmin}'] = dict(cm3=0.0); continue
                Eg = E.reshape(shape)
                # narrowest width: 2 x max distance-to-outside inside the region (voxels)
                w = 2 * ndimage.distance_transform_edt(np.pad(Eg, 1)).max() * vox
                r[f'n{nmin}'] = dict(cm3=round(E.sum() * vox ** 3 * 1e6, 2), unknown_free_observed=np.bincount(st[E], minlength=3).tolist(),
                                     max_thickness_mm=round(w * 1e3, 1), depth_mm_p50_max=[round(float(np.median(dist[E])) * 1e3, 1), round(float(dist[E].max()) * 1e3, 1)])
            rec[kind] = r
        out[f'{t}<-{p}'] = rec
print(json.dumps(out, indent=1))
