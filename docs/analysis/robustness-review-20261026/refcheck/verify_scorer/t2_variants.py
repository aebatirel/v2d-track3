"""verify_scorer test 2: registration-seed offsets and host-scan resolutions with my own scorer (vs_core).
Usage: python -I t2_variants.py EP SOURCE LIB OUT.json VARIANT [VARIANT ...]
  SOURCE: a store-relative rollout dir (scores 'sim') or a store-relative poses_world_vo.npz (perception)
  VARIANT: name:off=K,faces=N,dec=fs|cluster,lag=D,slot_lib=S:LIB2  (all optional; lag D scores track[k] vs GT[k+D])
"""
import json, sys, time
sys.path.insert(0, '/home/user/v2d-track3/docs/analysis/robustness-review-20261026/refcheck/verify_scorer')
import numpy as np
from vs_core import *

ep, src, lib, out = int(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
names, G = load_gt(ep)
if src.endswith('.npz'):
    X = npz_track(f'{STORE}/{src}', names)
else:
    rn, X, ref, steps, rf, md = load_rollout(f'{STORE}/{src}/episode_{ep:06d}.parquet')
    assert rn == names
assert len(X) == len(G), (len(X), len(G))
HC, CC = {}, {}
res = dict(ep=ep, source=src, lib=lib, names=names, variants={})
for spec in sys.argv[5:]:
    vn, _, rest = spec.partition(':')
    cfg = dict(off=0, faces=0, dec='fs', lag=0, slot_lib='', npts=1000, anc='centroid')
    for kv in filter(None, rest.split(',')):
        k, v = kv.split('=')
        cfg[k] = type(cfg[k])(v)
    t0 = time.time()
    Hs, regs = [], []
    for s, n in enumerate(names):
        hk = (n, s, cfg['faces'], cfg['dec'], cfg['npts'], cfg['anc'])
        if hk not in HC:
            HC[hk] = host(n, s, n_points=cfg['npts'], faces=cfg['faces'], weld_dec=cfg['dec'], anchor_mode=cfg['anc'])
        L = lib
        if cfg['slot_lib'] and int(cfg['slot_lib'].split('/')[0]) == s:
            L = cfg['slot_lib'].split('/')[1]
        if (L, n) not in CC:
            CC[(L, n)] = budget(f'{LIB}/{L}/{n}.glb')
        Hs.append(HC[hk])
        regs.append(register(CC[(L, n)], HC[hk], 1_000_003 * ep + 101 * s + cfg['off']))
    d = cfg['lag']
    k = np.arange(max(0, -d), len(G) - max(0, d))
    r = my_score(X[k], G[k + d], Hs, regs)
    res['variants'][vn] = dict(cfg=cfg, host_faces=[len(h['mesh'][1]) for h in Hs],
                               reg_deg=[round(reg_angle(x[1]), 2) for x in regs],
                               tilt_deg=[round(float(np.degrees(np.arccos(np.clip((x[1] @ h['axis']) @ h['axis'], -1, 1)))), 2) if np.any(h['axis']) else None for x, h in zip(regs, Hs)],
                               reg_quat=[np.round(Rot.from_matrix(x[1]).as_quat(), 5).tolist() for x in regs],
                               AUC=round(r['AUC'], 4), per_obj=[round(x, 4) for x in r['per_obj']], SP=r['SP'], MP=r['MP'],
                               seconds=round(time.time() - t0, 1))
    print(vn, res['variants'][vn], flush=True)
    json.dump(res, open(out, 'w'), indent=1)
