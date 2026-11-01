"""ORACLE DIAGNOSTIC ep0: counterfactual scores of GT-free post-processing rules on P_s / P_o (scored vs mocap)."""
import sys, json, os
import numpy as np
from scipy.spatial.transform import Rotation as Rot
sys.path.insert(0, '/home/user/v2d-track3/tools')
import xstar_fit as XF
S = '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad'
KIT = S + '/map/scoring/kit/v2d_submission_kit'; T3D = S + '/map/scoring/t3'; LIB = '/home/user/v2d-track3/meshes/library_v3'
EP = 0
XF.kit(KIT); T3 = XF.K['T3']
names, gt = XF.mocap(T3D, EP); N = len(gt[names[0]])
H = [XF.host_geometry(T3D, n, s) for s, n in enumerate(names)]
XG = json.load(open('/home/user/v2d-track3/docs/research/work/leak-decomp-20261030/tierA/xstar_geom.json'))['objects']
X = {n: np.array(XG[n]['X_scan_T_lib']) for n in names}
R = S + '/leak/p1/oracle_roots'
Ps = {n: np.load(f'{R}/Ps_scan/ep0/poses_world_vo.npz')[n].astype(float) for n in names}
Po_lib = {n: np.load(f'{R}/Po/ep0/poses_world_vo.npz')[n].astype(float) for n in names}
Pr_lib = {n: np.load(f'{S}/refine/in/ep0/poses_world_vo.npz')[n].astype(float) for n in names}
star = lambda T: {n: T[n] @ np.linalg.inv(X[n]) for n in names}
REG_ID = [XF.reg_of_X(np.eye(4), h['anchor']) for h in H]
Xk = [XF.kit_X(f'{LIB}/{n}.glb', H[s], EP, s)[0] for s, n in enumerate(names)]
REG_KIT = [XF.reg_of_X(Xk[s], H[s]['anchor']) for s in range(len(names))]
sc = lambda T: XF.score_track(names, T, gt, H, REG_ID)
sc_lib = lambda T: XF.score_track(names, T, gt, H, REG_KIT)
out = {}
# 1. P_s pot error at f0: rotation axis in the pot body frame vs the pot's principal axes; also in world vs vertical
G = np.load(f'{S}/leak/diag_ep0/out/perframe.npz')['G']
A = G @ Ps['white_pot'][0]; B = gt['white_pot'][0]
E = np.linalg.inv(B) @ A                       # body-frame error
rv = Rot.from_matrix(E[:3, :3]).as_rotvec(); ang = np.degrees(np.linalg.norm(rv)); ax = rv / np.linalg.norm(rv)
v, f = XF.load_vf(XF.scan_path(T3D, 'white_pot')); P = v - v.mean(0); w, U = np.linalg.eigh(np.cov(P.T))
up_world = np.array([0, 0, 1.0])
ax_world = B[:3, :3] @ ax
out['Ps_pot_f0_error'] = dict(angle_deg=round(ang, 1), axis_body=np.round(ax, 3).tolist(), pot_pca_axes_body=np.round(U.T, 3).tolist(),
                              pca_var=np.round(w, 5).tolist(), axis_world=np.round(ax_world, 3).tolist(),
                              angle_axis_to_world_z_deg=round(float(np.degrees(np.arccos(abs(ax_world @ up_world)))), 1),
                              shift_cm=round(float(np.linalg.norm(A[:3, 3] - B[:3, 3]) * 100), 2))
# where is the mocap world up? check pot's mocap z-axis spread
out['mocap_pot_body_z_in_world_f0'] = np.round(B[:3, 2], 3).tolist()
# 2. scores as is
out['as_is'] = {'Ps*': sc(Ps), 'Po*': sc(star(Po_lib)), 'Pr*': sc(star(Pr_lib)), 'Po_lib': sc_lib(Po_lib), 'Pr_lib': sc_lib(Pr_lib)}
# 3. GT-free static backfill rule on P_s: guard re-acquired the pot at f64 (perception log); the track over [0,64)
#    is near-static in perception world -> replace [0,64) by the re-acquired world pose at f64
def motion(T, a, b):
    p = T[a:b, :3, 3]; r = Rot.from_matrix(np.einsum('ji,njk->nik', T[a, :3, :3], T[a:b, :3, :3])).magnitude()
    return float(np.linalg.norm(p - p[0], axis=1).max() * 100), float(np.degrees(r.max()))
k = 64
out['Ps_pot_track_motion_f0_63'] = dict(zip(('max_shift_cm', 'max_rot_deg'), np.round(motion(Ps['white_pot'], 0, k), 2)))
jump = np.linalg.inv(Ps['white_pot'][k - 1]) @ Ps['white_pot'][k]
out['Ps_pot_jump_f63_f64'] = dict(shift_cm=round(float(np.linalg.norm(Ps['white_pot'][k, :3, 3] - Ps['white_pot'][k - 1, :3, 3]) * 100), 2),
                                  rot_deg=round(float(np.degrees(Rot.from_matrix(jump[:3, :3]).magnitude())), 1))
for kk in (64, 70):
    Pb = {n: Ps[n].copy() for n in names}; Pb['white_pot'][:kk] = Ps['white_pot'][kk]
    out[f'Ps*_backfill_hold_f{kk}'] = sc(Pb)
# oracle: G-aligned score (each object independent of slot 0's frame-0 pose) -- replace the kit scene alignment by G
def score_G(T):
    ach = np.stack([XF.to7(G @ T[n]) for n in names], 1)[:, None].copy(); ref = np.stack([XF.to7(gt[n]) for n in names], 1)[:, None].copy()
    for s in range(len(names)):
        ach[:, :, s] = T3._convert_object_body(ach[:, :, s], H[s]['anchor'], np.eye(3))
        ref[:, :, s, :3] += np.einsum('...ij,j->...i', T3._rotation_matrix(ref[:, :, s, 3:]), H[s]['anchor'])
    axes = [h['axis'] for h in H]; orders = [h['order'] for h in H]; pts = [h['points'] for h in H]
    return {n: round(float(T3._registered_pose_metric('add_auc', ach[:, :, s:s+1], ref[:, :, s:s+1], pts[s:s+1], axes[s:s+1], orders[s:s+1])), 4) for s, n in enumerate(names)}
out['G_aligned_oracle'] = {'Ps*': score_G(Ps), 'Po*': score_G(star(Po_lib)), 'Pr*': score_G(star(Pr_lib))}
# 4. P_o / Pr: frame-0 anchor smoothing (GT-free): replace frame 0 of each object by the mean pose over the first K frames
#    in which the perceived object moved < 1 cm / 3 deg from frame 0 (and K <= 30)
def avg_pose(Ts):
    q = Rot.from_matrix(Ts[:, :3, :3]).mean().as_matrix(); M = np.eye(4); M[:3, :3] = q; M[:3, 3] = Ts[:, :3, 3].mean(0); return M
def smooth0(T, K=30, tcm=1.0, rdeg=3.0):
    o = {}
    for n in names:
        Tn = T[n].copy(); p = Tn[:K, :3, 3]; r = np.degrees(Rot.from_matrix(np.einsum('ji,njk->nik', Tn[0, :3, :3], Tn[:K, :3, :3])).magnitude())
        ok = (np.linalg.norm(p - p[0], axis=1) * 100 < tcm) & (r < rdeg); m = int(np.argmin(ok)) if not ok.all() else K
        Tn[0] = avg_pose(Tn[:m]); o[n] = Tn
    return o
for K in (10, 20, 30):
    out[f'f0_smooth_K{K}'] = {'Po*': sc(star(smooth0(Po_lib, K))), 'Pr*': sc(star(smooth0(Pr_lib, K))),
                              'Po_lib': sc_lib(smooth0(Po_lib, K)), 'Pr_lib': sc_lib(smooth0(Pr_lib, K))}
# 5. sensitivity: P_o vs Pr pot frame-0 difference
d0 = np.linalg.inv(Pr_lib['white_pot'][0]) @ Po_lib['white_pot'][0]
out['Po_vs_Pr_pot_f0'] = dict(shift_cm=round(float(np.linalg.norm(Po_lib['white_pot'][0, :3, 3] - Pr_lib['white_pot'][0, :3, 3]) * 100), 3),
                              rot_deg=round(float(np.degrees(Rot.from_matrix(d0[:3, :3]).magnitude())), 3))
json.dump(out, open(f'{S}/leak/diag_ep0/out/counterfactuals.json', 'w'), indent=1)
print(json.dumps(out, indent=1))
