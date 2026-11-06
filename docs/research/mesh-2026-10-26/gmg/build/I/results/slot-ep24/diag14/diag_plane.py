"""GT-free diagnosis of the F-I4.1 'no_plane_pair' on the ep24 boards (scope-fix step, 31 Oct ~17:00 UTC).
Reads only our clean bundle (owned points, cameras, frames, sigma) and our pick meshes. No slot / physics outcome."""
import json, math, os, sys, time
sys.path.insert(0, '/home/user/v2d-track3/docs/research/mesh-2026-10-26')
import numpy as np
from gmg import guard, interlock as IL, structure as ST, platebody as PB
import trimesh

run, bundle, cands, out = sys.argv[1:5]
guard.set_run(run)
b = IL.load_bundle_any(bundle)
res = {}
for obj in b.objects:
    t0 = time.time()
    m = trimesh.load(os.path.join(cands, obj, 'shell_t5p36.glb'), force='mesh')
    m = trimesh.Trimesh(np.asarray(m.vertices), np.asarray(m.faces), process=True)
    P, Cm, fr, cnt = PB._near_points(b, obj, m)
    sigma = b.sigma(obj)
    K = ST.consts()
    r = dict(sigma_mm=round(sigma * 1e3, 3), points=cnt, band_mm=round(K['band'] * sigma * 1e3, 2))
    # thinnest axis of the near points (PCA) and of the pick
    c = P.mean(0)
    w, V = np.linalg.eigh(np.cov((P[::20] - c).T))
    n0 = V[:, 0]
    s = (P - c) @ n0
    view = np.einsum('ij,j->i', Cm - P, n0)        # > 0: camera on the +n0 side
    r['pca_eig_mm'] = np.round(np.sqrt(w) * 1e3, 2).tolist()
    r['pick_extents_mm'] = np.round(m.extents * 1e3, 2).tolist()
    Xm = (np.asarray(m.vertices) - c) @ n0
    r['pick_extent_along_n0_mm'] = round(float(Xm.max() - Xm.min()) * 1e3, 2)
    q = lambda x, p: float(np.percentile(x, p)) * 1e3
    r['s_pct_mm'] = {p: round(q(s, p), 2) for p in (1, 5, 25, 50, 75, 95, 99)}
    r['s_extent_1_99_mm'] = round(q(s, 99) - q(s, 1), 2)
    pos, neg = view > 0, view < 0
    r['seen_from_plus_share'] = round(float(pos.mean()), 4)
    r['s_plus_side_pct_mm'] = {p: round(q(s[pos], p), 2) for p in (5, 50, 95)} if pos.sum() > 100 else None
    r['s_minus_side_pct_mm'] = {p: round(q(s[neg], p), 2) for p in (5, 50, 95)} if neg.sum() > 100 else None
    # histogram along n0 (1 mm bins), by side
    edges = np.arange(np.floor(q(s, 0.5)) - 1, np.ceil(q(s, 99.5)) + 2, 1.0) * 1e-3
    hp, _ = np.histogram(s[pos], edges); hn, _ = np.histogram(s[neg], edges)
    r['hist_1mm'] = dict(edges_mm=np.round(edges * 1e3, 1).tolist(), plus=hp.tolist(), minus=hn.tolist())
    # per frame: which side the camera is on and the median s of that frame (track jitter along the normal)
    rows = []
    for f in np.unique(fr):
        k = fr == f
        if k.sum() < 200:
            continue
        sp = s[k & pos]; sn = s[k & neg]
        rows.append(dict(f=int(f), n=int(k.sum()), plus_share=round(float(pos[k].mean()), 3),
                         s_med_plus=None if len(sp) < 100 else round(float(np.median(sp)) * 1e3, 2),
                         s_med_minus=None if len(sn) < 100 else round(float(np.median(sn)) * 1e3, 2),
                         s_iqr=round((q(s[k], 75) - q(s[k], 25)), 2)))
    r['frames'] = rows
    sp_ = np.array([x['s_med_plus'] for x in rows if x['s_med_plus'] is not None])
    sn_ = np.array([x['s_med_minus'] for x in rows if x['s_med_minus'] is not None])
    r['per_frame_summary'] = dict(frames=len(rows), frames_plus=len(sp_), frames_minus=len(sn_),
                                  plus_med_of_med=None if len(sp_) == 0 else round(float(np.median(sp_)), 2),
                                  plus_mad=None if len(sp_) == 0 else round(float(np.median(np.abs(sp_ - np.median(sp_)))), 2),
                                  minus_med_of_med=None if len(sn_) == 0 else round(float(np.median(sn_)), 2),
                                  minus_mad=None if len(sn_) == 0 else round(float(np.median(np.abs(sn_ - np.median(sn_)))), 2),
                                  within_frame_iqr_med=round(float(np.median([x['s_iqr'] for x in rows])), 2))
    # the F-I4.1 plane step as run (band 3 sigma) and its planes
    obs = dict(pts=P, cam=Cm, own=np.zeros(len(P), np.uint8))
    Pd, Cd, _ = ST._points(obs, K, np.random.default_rng(0))
    planes, pairs, sinfo = ST._planes(Pd, Cd, sigma, K)
    def plsum(planes):
        out = []
        for p in planes:
            nn = np.asarray(p['n'])
            out.append(dict(n_pts=p['n_pts'], cos_n0=round(float(nn @ n0), 4), d_along_n0_mm=round(float((np.asarray(p['c']) - c) @ n0) * 1e3, 2),
                            rms_mm=p['rms_mm'], two_sided_share=p['two_sided_share'],
                            extent_mm=[round((e[1] - e[0]) * 1e3, 1) for e in p['extent_m']]))
        return out
    r['as_run'] = dict(n_down=int(len(Pd)), planes=plsum(planes), pairs=pairs)
    r['sec'] = round(time.time() - t0, 1)
    res[obj] = r
    print(obj, json.dumps({k: v for k, v in r.items() if k not in ('frames', 'hist_1mm')}), flush=True)
json.dump(res, open(out, 'w'), indent=1)
