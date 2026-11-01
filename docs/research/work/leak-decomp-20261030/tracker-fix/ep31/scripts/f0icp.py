"""ep31 frame 0, CPU proxy of fix F1 (anchor re-segmentation + re-registration).
GT-FREE part (inference side): our frame-0 depth (depth0.npy), our sweeper mask (det_f0.npz), our library_v3 meshes, our
P_o poses (lib frames). (a) mask coverage = |mask ∩ predicted visible silhouette| / |predicted visible silhouette|, with
the rack rendered at its tracked pose as occluder; (b) a completed mask = predicted silhouette (dilated 3 px) ∩ pixels
whose depth is within 2.5 cm of the predicted sweeper depth and not explained by the rendered rack (|d - rack| > 1 cm);
(c) point-to-plane ICP of our sweeper's visible surface to the back-projected depth, from the P_o pose, with
(i) our mask, (ii) the completed mask.
ORACLE part (after inference): the truth (mocap mapped by the P_s rack fit, as f0render.py), the f0 depth residual on
true-sweeper pixels inside / outside our mask, and the rotation error of every candidate pose; then the kit-chain AUC
(* and lib) of P_o with the sweeper's rest frames (f0 .. perceived onset-1) replaced by the ICP pose.
Usage: python -I f0icp.py SCRIPTS_DIR OUT_JSON
"""
import json, sys
import numpy as np, trimesh, cv2
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation as Rot
sys.path.insert(0, sys.argv[1]); import diag31 as D  # noqa: E402

XF = D.XF; T3 = D.T3
names, gt, N, tr = D.load_tracks()
H = [XF.host_geometry(D.T3D, n, s) for s, n in enumerate(names)]
sw, rk = names.index('mini_sweeper'), names.index('plastic_dish_rack')
det = np.load(f'{D.REF}/det_f0.npz', allow_pickle=True)
K2 = np.diag([0.5, 0.5, 1.0]) @ det['K'].astype(float)
masks = np.unpackbits(det['masks'], axis=-1)[:, :, :800].astype(bool)
msw = masks[det['chosen'][0]]
dep = np.load(f'{D.REF}/depth0.npy')[::2, ::2].astype(float); Hh, Ww = dep.shape
V = np.load(f'{D.RUN}/perc2/poses_world_vo.npz'); Plib = {n: V[n].astype(np.float64) for n in names}   # GT-free input
lib = {n: trimesh.load(f'{D.REPO}/meshes/library_v3/{n}.glb', force='mesh') for n in names}
scan = {n: trimesh.load(XF.scan_path(D.T3D, n), force='mesh') for n in names}
Xg = {n: np.asarray(D.XG[n]['X_scan_T_lib']) for n in names}


def samples(m, k, seed):
    p, fi = trimesh.sample.sample_surface(m, k, seed=seed); return p, m.face_normals[fi]


SL = {n: samples(lib[n], 400000 if n == names[rk] else 150000, 11) for n in names}
SS = {n: samples(scan[n], 400000 if n == names[rk] else 150000, 11) for n in names}


def render(objs):
    """objs: list of (slot, 4x4 pose, (pts, nrm)); returns depth z-buffer and slot labels"""
    zb = np.full((Hh, Ww), np.inf); lab = np.full((Hh, Ww), -1)
    for s, T, (P, _) in objs:
        X = P @ T[:3, :3].T + T[:3, 3]; uv = X @ K2.T
        u = np.round(uv[:, 0] / uv[:, 2]).astype(int); v = np.round(uv[:, 1] / uv[:, 2]).astype(int); z = X[:, 2]
        for du in (0, 1):
            for dv in (0, 1):
                uu, vv = u + du, v + dv; ok = (uu >= 0) & (uu < Ww) & (vv >= 0) & (vv < Hh) & (z > 0)
                uu, vv, zz = uu[ok], vv[ok], z[ok]; o = np.argsort(-zz); uu, vv, zz = uu[o], vv[o], zz[o]
                upd = zz < zb[vv, uu]; zb[vv[upd], uu[upd]] = zz[upd]; lab[vv[upd], uu[upd]] = s
    return zb, lab


def backproject(m):
    v, u = np.where(m); z = dep[v, u]; ok = z > 0; v, u, z = v[ok], u[ok], z[ok]
    x = (u - K2[0, 2]) * z / K2[0, 0]; y = (v - K2[1, 2]) * z / K2[1, 1]; return np.c_[x, y, z]


def icp(T0, cloud, model, iters=60, trim=0.8):
    """point-to-plane ICP; model = (pts, nrm) in body frame; only model points facing the camera are used"""
    T = T0.copy(); P, Nn = model
    for _ in range(iters):
        Xw = P @ T[:3, :3].T + T[:3, 3]; Nw = Nn @ T[:3, :3].T
        vis = (Xw * Nw).sum(1) < 0
        tree = cKDTree(Xw[vis]); d, i = tree.query(cloud)
        keep = d < np.quantile(d, trim); q = cloud[keep]; p = Xw[vis][i[keep]]; n = Nw[vis][i[keep]]
        A = np.c_[np.cross(p, n), n]; b = ((q - p) * n).sum(1)   # move the model p onto the cloud q
        x = np.linalg.lstsq(A, b, rcond=None)[0]
        dR = Rot.from_rotvec(x[:3]).as_matrix(); G = np.eye(4); G[:3, :3] = dR; G[:3, 3] = x[3:]
        T = G @ T
        if np.linalg.norm(x) < 1e-6:
            break
    return T


# ---------------- GT-free: predicted visible silhouette of the sweeper at the P_o pose, rack as occluder
zb, lab = render([(rk, Plib[names[rk]][0], SL[names[rk]]), (sw, Plib[names[sw]][0], SL[names[sw]])])
pred = lab == sw
zr, lr = render([(rk, Plib[names[rk]][0], SL[names[rk]])])
zs, ls = render([(sw, Plib[names[sw]][0], SL[names[sw]])])
coverage = float((msw & pred).sum() / max(1, pred.sum()))
dil = cv2.dilate(pred.astype(np.uint8), np.ones((7, 7), np.uint8)).astype(bool)
not_rack = ~np.isfinite(zr) | (np.abs(dep - zr) > 0.01)
near_sw = np.isfinite(zs) & (np.abs(dep - zs) < 0.025)
completed = (dil & near_sw & not_rack & (dep > 0)) | msw
out = dict(gtfree=dict(mask_px=int(msw.sum()), predicted_visible_px=int(pred.sum()), coverage=round(coverage, 3),
                       completed_px=int(completed.sum())))
# ---------------- ICP candidates (GT-free)
cand = {'Po': Plib[names[sw]][0]}
for k, m in (('icp_ourmask', msw), ('icp_completed', completed)):
    cand[k] = icp(Plib[names[sw]][0], backproject(m), SL[names[sw]])
# ---------------- ORACLE: truth in perception world (rack-only fit of P_s, as f0render.py)
pts = H[rk]['points'][::10] + H[rk]['anchor']
P = np.concatenate([pts @ tr['Ps'][names[rk]][i][:3, :3].T + tr['Ps'][names[rk]][i][:3, 3] for i in range(N)])
Q = np.concatenate([pts @ gt[names[rk]][i][:3, :3].T + gt[names[rk]][i][:3, 3] for i in range(N)])
mp, mq = P.mean(0), Q.mean(0); U, _, Vt = np.linalg.svd((P - mp).T @ (Q - mq))
Rm = Vt.T @ np.diag([1, 1, np.sign(np.linalg.det(Vt.T @ U.T))]) @ U.T; tm = mq - Rm @ mp
G = np.eye(4); G[:3, :3] = Rm.T; G[:3, 3] = -Rm.T @ tm
T_true_scan = G @ gt[names[sw]][0]
zt, lt = render([(rk, G @ gt[names[rk]][0], SS[names[rk]]), (sw, T_true_scan, SS[names[sw]])])
tv = lt == sw
res = {}
for k, m in (('true_vis_in_mask', tv & msw), ('true_vis_outside_mask', tv & ~msw), ('mask_not_true_sweeper', msw & ~tv)):
    mm = m & (dep > 0); dz = (dep - zt)[mm]
    res[k] = dict(n=int(mm.sum()), median_cm=round(float(np.median(dz) * 100), 2) if mm.any() else None,
                  within_1cm=round(float(np.mean(np.abs(dz) < 0.01)), 3) if mm.any() else None)
out['oracle_depth_vs_truth'] = res
out['oracle_completed_mask'] = dict(iou_with_true_visible=round(float((completed & tv).sum() / max(1, (completed | tv).sum())), 3),
                                    iou_ourmask_with_true_visible=round(float((msw & tv).sum() / max(1, (msw | tv).sum())), 3))
# rotation error of each candidate (scan frames: lib pose @ inv(Xg))
Xs = np.linalg.inv(Xg[names[sw]])
out['oracle_f0_error'] = {}
for k, T in cand.items():
    Ts = T @ Xs; E = Ts[:3, :3] @ T_true_scan[:3, :3].T
    a = Ts[:3, :3] @ H[sw]['anchor'] + Ts[:3, 3]; at = T_true_scan[:3, :3] @ H[sw]['anchor'] + T_true_scan[:3, 3]
    out['oracle_f0_error'][k] = dict(rot_deg=round(float(np.degrees(Rot.from_matrix(E).magnitude())), 2),
                                     anchor_cm=round(float(np.linalg.norm(a - at) * 100), 2))
# kit-chain AUC with the sweeper's rest frames (perceived onset, GT-free) replaced by each candidate (body-frame constant)
c = Plib[names[sw]][:, :3, 3]; R0 = Plib[names[sw]][0][:3, :3]
mv = (np.linalg.norm(c - c[0], axis=1) > 0.01) | (np.degrees(Rot.from_matrix(np.einsum('nij,kj->nik', Plib[names[sw]][:, :3, :3], R0)).magnitude()) > 5)
onset = int(np.argmax(mv)) if mv.any() else N
out['perceived_onset'] = onset
REG_star = [XF.reg_of_X(Xg[n], H[s]['anchor']) for s, n in enumerate(names)]
REG_lib = [XF.kit_X(f'{D.REPO}/meshes/library_v3/{n}.glb', H[s], D.EP, s)[1] for s, n in enumerate(names)]
out['auc'] = {}
for k, T in cand.items():
    B = np.linalg.inv(Plib[names[sw]][0]) @ T
    trk = {n: Plib[n].copy() for n in names}
    trk[names[sw]][:onset] = Plib[names[sw]][:onset] @ B
    a_s = XF.score_track(names, trk, gt, H, REG_star); a_l = XF.score_track(names, trk, gt, H, REG_lib)
    out['auc'][k] = dict(star=a_s, lib=a_l)
# oracle ceiling: rest frames := truth (lib frames)
T_true_lib = T_true_scan @ Xg[names[sw]]
trk = {n: Plib[n].copy() for n in names}; B = np.linalg.inv(Plib[names[sw]][0]) @ T_true_lib
trk[names[sw]][:onset] = Plib[names[sw]][:onset] @ B
out['auc']['ORACLE_rest_true'] = dict(star=XF.score_track(names, trk, gt, H, REG_star), lib=XF.score_track(names, trk, gt, H, REG_lib))
trk = {n: Plib[n].copy() for n in names}; trk[names[sw]][:1] = T_true_lib[None]
out['auc']['ORACLE_f0_only_true'] = dict(star=XF.score_track(names, trk, gt, H, REG_star), lib=XF.score_track(names, trk, gt, H, REG_lib))
json.dump(out, open(sys.argv[2], 'w'), indent=1)
print(json.dumps(out, indent=1))
cv2.imwrite(sys.argv[2].replace('.json', '_masks.png'),
            np.dstack([completed.astype(np.uint8) * 255, msw.astype(np.uint8) * 255, tv.astype(np.uint8) * 255]))
