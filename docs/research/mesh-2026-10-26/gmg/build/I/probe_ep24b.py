"""Interlock probe 2 (dev, GT-free): entered region of each board in fractions of its own observed extent; insertion
direction (partner origin path in the target frame during intrusion frames); entry-side half after the insertion split
(XCarve R2 logic on swept partner samples). Inputs: dev bundle + dev hull candidates only."""
import json, sys, numpy as np, trimesh
sys.path.insert(0, '/home/user/v2d-track3/docs/research/mesh-2026-10-26')
from gmg import bundle as BU, contact as CT, geom
S = '/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad'
RUN = f'{S}/gmg/runs-dev/20261030-b5pool24-edba5b3'
b = BU.load_bundle(f'{RUN}/bundle/public/ep24')
out = {}
for t in b.objects:
    p = b.partners(t)[0]
    obs = b.obs(t); lo = np.asarray(obs['lo']); vox = float(obs['vox']); st = np.asarray(obs['state']); shape = st.shape
    cf = np.array(sorted(set(b.contact(t, p)['contact'])))
    X, N, fid, n_p = CT.partner_samples(b, t, p, cf)
    vi, ok = CT._vox_index(X, lo, vox, shape); lin = np.ravel_multi_index(tuple(vi[ok].T), shape); f_ok = fid[ok]
    G = np.stack(np.meshgrid(*[lo[k] + vox * (np.arange(shape[k]) + 0.5) for k in range(3)], indexing='ij'), -1).reshape(-1, 3)
    m = trimesh.load(f'{RUN}/cand/public/ep24/{t}/hull.glb', force='mesh'); ins = geom.inside(m, G)[0]
    # per-frame entered voxel sets inside the hull
    per = {}
    for f in cf:
        s = np.unique(lin[f_ok == f]); per[int(f)] = s[ins[s]]
    nf = np.array([len(per[int(f)]) for f in cf]); k = nf >= 10; fi = cf[k]
    tr = np.array([CT.rel(b.poses, t, p, f)[:3, 3] for f in fi])
    # insertion direction: PCA of the origin path during intrusion frames, signed from first to last
    d = np.linalg.svd(tr - tr.mean(0), full_matrices=False)[2][0]; sv = np.linalg.svd(tr - tr.mean(0), compute_uv=False)
    if (tr[-1] - tr[0]) @ d < 0: d = -d
    straight = float(sv[0] / sv.sum())
    P = np.asarray(obs['pts'])[::50]; c = P.mean(0); U = np.linalg.svd(P - c, full_matrices=False)[2]
    Ap = (P - c) @ U.T; lo_p, hi_p = np.percentile(Ap, 1, 0), np.percentile(Ap, 99, 0)
    cnt = np.zeros(st.size, int)
    for f in fi: cnt[per[int(f)]] += 1
    rec = dict(intrusion_frames=int(k.sum()), first_last=[int(fi[0]), int(fi[-1])], travel_mm=round(float((tr[-1] - tr[0]) @ d) * 1e3, 1),
               straightness=round(straight, 2), insert_dir_in_pca=np.round(U @ d, 3).tolist())
    for nmin in (10, 28):
        E = cnt >= nmin; C = G[E]; A = (C - c) @ U.T
        frac = lambda a: np.round((a - lo_p) / (hi_p - lo_p), 2).tolist()
        r = dict(cm3=round(E.sum() * vox ** 3 * 1e6, 2), frac_min=frac(A.min(0)), frac_max=frac(A.max(0)),
                 width_mm=np.round((A.max(0) - A.min(0)) * 1e3, 1).tolist(), observed_share=round(float((st.ravel()[E] == 2).mean()), 3))
        # insertion split: plane through the region's centroid normal to d; entry side = (x - c).d < 0 (where the partner came from)
        s = (C - C.mean(0)) @ d; ent = s < 0
        Ae = A[ent]
        r['entry_half'] = dict(cm3=round(ent.sum() * vox ** 3 * 1e6, 2), frac_min=frac(Ae.min(0)), frac_max=frac(Ae.max(0)))
        # persistence weighted: which side holds more frame-counts
        w = cnt[E]; r['frame_count_share_entry_side'] = round(float(w[ent].sum() / w.sum()), 3)
        rec[f'nmin{nmin}'] = r
    out[f'{t}<-{p}'] = rec
print(json.dumps(out, indent=1))
