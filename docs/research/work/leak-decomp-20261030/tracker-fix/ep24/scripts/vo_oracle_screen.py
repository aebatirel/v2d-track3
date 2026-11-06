"""ORACLE SCREEN (public, 2-object episodes): how much of R* is lost to a common-mode (camera-like) translation error?
After the kit's chain and frame-0 alignment (* convention), m(t) = mean over objects of the anchor translation error vs
mocap, smoothed over 9 frames; all objects are shifted by -m(t) and re-scored. Upper bound of what a perfect
translation-only camera correction could recover (it also removes any common-mode tracker error).
Usage: python -I vo_oracle_screen.py OUT_JSON
"""
import json, sys, os
import numpy as np
REPO = '/home/user/v2d-track3'
S = '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad'
sys.path.insert(0, f'{REPO}/tools')
import xstar_fit as XF  # noqa: E402
KIT = f'{S}/map/scoring/kit/v2d_submission_kit'; T3D = f'{S}/map/scoring/t3'
XG = json.load(open(f'{REPO}/docs/research/work/leak-decomp-20261030/tierA/xstar_geom.json'))['objects']
XF.kit(KIT); T3 = XF.K['T3']
ROOT = f'{S}/leak/p1/oracle_roots'


def aligned(names, track, gt, H, REG):
    N = len(track[names[0]]); B = len(names)
    ach = np.stack([XF.to7(track[n]) for n in names], 1)[:, None].copy(); ref = np.stack([XF.to7(gt[n][:N]) for n in names], 1)[:, None].copy()
    for s in range(B):
        ach[:, :, s] = T3._convert_object_body(ach[:, :, s], *REG[s])
        ref[:, :, s, :3] += np.einsum('...ij,j->...i', T3._rotation_matrix(ref[:, :, s, 3:]), H[s]['anchor'])
    return T3._align_registered_scene(ach, ref, [h['axis'] for h in H]), ref


def auc(ach, ref, H):
    return float(T3._registered_pose_metric('add_auc', ach, ref, [h['points'] for h in H], [h['axis'] for h in H], [h['order'] for h in H]))


out = {}
for ep in XF.PUBLIC:
    names, gt = XF.mocap(T3D, ep, None)
    if len(names) < 2:
        continue
    H = [XF.host_geometry(T3D, n, s) for s, n in enumerate(names)]
    e = {}
    for arm, path, scan in (('Po', f'{ROOT}/Po/ep{ep}/poses_world_vo.npz', False), ('Ps', f'{ROOT}/Ps_scan/ep{ep}/poses_world_vo.npz', True)):
        V = np.load(path); T = {n: V[n].astype(np.float64) for n in names}
        REG = [XF.reg_of_X(np.eye(4) if scan else np.asarray(XG[n]['X_scan_T_lib']), H[s]['anchor']) for s, n in enumerate(names)]
        al, ref = aligned(names, T, gt, H, REG)
        d = al[:, 0, :, :3] - ref[:, 0, :, :3]           # (N, B, 3)
        m = d.mean(1)
        k = np.ones(9) / 9
        ms = np.stack([np.convolve(np.pad(m[:, j], 4, mode='edge'), k, 'valid') for j in range(3)], 1)
        al2 = al.copy(); al2[:, 0, :, :3] -= ms[:, None]
        diff = np.linalg.norm(d[:, 0] - d[:, 1], axis=1)
        e[arm] = dict(base=round(auc(al, ref, H), 4), common_removed=round(auc(al2, ref, H), 4),
                      common_cm_med=round(float(np.median(np.linalg.norm(ms, axis=1)) * 100), 2),
                      common_cm_p90=round(float(np.percentile(np.linalg.norm(ms, axis=1), 90) * 100), 2),
                      diff_cm_med=round(float(np.median(diff) * 100), 2))
    out[ep] = e
    print(ep, json.dumps(e), flush=True)
json.dump(out, open(sys.argv[1], 'w'), indent=1)
