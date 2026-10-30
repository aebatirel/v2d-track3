"""GT-FREE descriptive check (no mocap read): per object at frame 0, mask coverage of the predicted visible silhouette
(our library_v3 mesh at the refine-input P_r pose, other objects rendered as occluders), over the 20 public episodes.
Usage: python -I coverage_all.py OUT_JSON"""
import json, sys, numpy as np, trimesh
S = '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad'
LIB = '/home/user/v2d-track3/meshes/library_v3'
EPS = [0, 2, 11, 12, 13, 18, 21, 22, 23, 24, 26, 27, 31, 39, 40, 41, 42, 43, 44, 45]
SM = {}
def pts(n):
    if n not in SM:
        SM[n] = trimesh.sample.sample_surface(trimesh.load(f'{LIB}/{n}.glb', force='mesh'), 400000 if n == 'plastic_dish_rack' else 150000, seed=11)[0]
    return SM[n]
out = {}
for ep in EPS:
    R = f'{S}/refine/in/ep{ep}'; det = np.load(f'{R}/det_f0.npz', allow_pickle=True)
    names = [str(x) for x in det['names']]; K2 = np.diag([0.5, 0.5, 1.0]) @ det['K'].astype(float)
    Hh, Ww = int(det['mask_shape'][1]), int(det['mask_shape'][2])
    masks = np.unpackbits(det['masks'], axis=-1)[:, :, :Ww].astype(bool)
    V = np.load(f'{R}/poses_world_vo.npz'); W0 = np.load(f'{R}/poses.npz')['world_T_cam'][0].astype(float)
    zb = np.full((Hh, Ww), np.inf); lab = np.full((Hh, Ww), -1)
    for s, n in enumerate(names):
        T = np.linalg.inv(W0) @ V[n][0].astype(float); X = pts(n) @ T[:3, :3].T + T[:3, 3]; uv = X @ K2.T
        u = np.round(uv[:, 0] / uv[:, 2]).astype(int); v = np.round(uv[:, 1] / uv[:, 2]).astype(int); z = X[:, 2]
        for du in (0, 1):
            for dv in (0, 1):
                uu, vv = u + du, v + dv; ok = (uu >= 0) & (uu < Ww) & (vv >= 0) & (vv < Hh) & (z > 0)
                uu, vv, zz = uu[ok], vv[ok], z[ok]; o = np.argsort(-zz); uu, vv, zz = uu[o], vv[o], zz[o]
                up = zz < zb[vv, uu]; zb[vv[up], uu[up]] = zz[up]; lab[vv[up], uu[up]] = s
    e = {}
    for s, n in enumerate(names):
        c = int(det['chosen'][s]); pred = lab == s
        if c < 0:
            e[n] = None; continue
        m = masks[c]
        e[n] = dict(slot=s, mask_px=int(m.sum()), pred_px=int(pred.sum()), coverage=round(float((m & pred).sum() / max(1, pred.sum())), 3),
                    iou=round(float((m & pred).sum() / max(1, (m | pred).sum())), 3))
    out[ep] = e
    print(ep, {n: (v['coverage'], v['iou'], v['mask_px']) if v else None for n, v in e.items()}, flush=True)
json.dump(out, open(sys.argv[1], 'w'), indent=1)
