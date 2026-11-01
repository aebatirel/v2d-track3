"""B4 fix diagnostic (GT-free): frame-0 det proposals holding each object's projected origin vs the object's final
frame-0 owned points (v4 bundle). Inputs: det masks only, tracks, calib, v4 bundle points. No GT."""
import json, sys, numpy as np
sys.path.insert(0, '/home/user/v2d-track3/pipeline')
from recon_mesh import rectified_K
S = '/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad'
K = rectified_K(f'{S}/data/calib.json')
for ep in [int(x) for x in sys.argv[1:]]:
    B = f'{S}/gmg/runs/20261031-b4ext4-b61e8aa/bundle/public/ep{ep}'
    m = json.load(open(f'{B}/episode.json')); objs = m['objects']
    P = np.load(f'{S}/data/sweep/ep{ep}/poses.npz')
    d = np.load(f'{S}/data/store/ep{ep}/det_f0.npz')
    shp = tuple(int(x) for x in d['mask_shape'])
    M = np.unpackbits(d['masks'], axis=-1)[..., :shp[2]].astype(bool); sc = 1600 / shp[2]
    print(f'ep{ep}: {len(M)} proposals, half-res {M.shape[1:]}, scale {sc}')
    org = {}
    for o in objs:
        oc = P[f'cam_T_{o}'][0][:3, 3]
        org[o] = (int((K[1,1]*oc[1]/oc[2]+K[1,2])//sc), int((K[0,0]*oc[0]/oc[2]+K[0,2])//sc))
    for o in objs:
        z = np.load(f'{B}/{o}.npz'); sel = (z['frame'] == 0) & (z['own'] == 0)
        X = z['pts'][sel].astype(float); T = P[f'cam_T_{o}'][0].astype(float)
        C = X @ T[:3,:3].T + T[:3,3]
        u = (K[0,0]*C[:,0]/C[:,2]+K[0,2])//sc; v = (K[1,1]*C[:,1]/C[:,2]+K[1,2])//sc
        ok = (u>=0)&(u<M.shape[2])&(v>=0)&(v<M.shape[1])
        foot = np.zeros(M.shape[1:], bool); foot[v[ok].astype(int), u[ok].astype(int)] = True
        cand = np.nonzero(M[:, org[o][0], org[o][1]])[0] if 0<=org[o][0]<M.shape[1] and 0<=org[o][1]<M.shape[2] else []
        excl = [i for i in cand if not any(M[i, org[q][0], org[q][1]] for q in objs if q != o
                                           and 0<=org[q][0]<M.shape[1] and 0<=org[q][1]<M.shape[2])]
        print(f'  {o}: origin px {org[o]}, final frame-0 owned pts {sel.sum()}, footprint {foot.sum()} cells; '
              f'cand {list(cand)} excl {excl}; chosen {m["crop"][o].get("det_index")} iou {m["crop"][o].get("det_iou")}')
        for i in cand:
            a = int(M[i].sum()); inter = int((M[i] & foot).sum())
            print(f'     prop {i}: area {a}, inter {inter}, cover(foot) {inter/max(foot.sum(),1):.3f}, '
                  f'prec {inter/max(a,1):.3f}, iou {inter/max((M[i]|foot).sum(),1):.3f}, excl {i in excl}')
