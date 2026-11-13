"""ORACLE DIAGNOSTIC (public ep31, frame 0): does the perceived (tilted) sweeper pose explain our own f0 inputs (mask, depth)
better or worse than the true pose? Point-splat render (z-buffer) of the scan meshes in the rectified half-res camera of
det_f0.npz; mocap is mapped into the perception world by a rigid fit of the P_s RACK track to the mocap rack over all
frames (the rack is static and tracked to 0.4 cm; the sweeper does not enter this mapping).
Also: rack depth quality (is the rack's observed depth poor?) and sweeper/rack interpenetration at f0.
Usage: python -I f0render.py SCRIPTS_DIR OUT_JSON
"""
import json, sys
import numpy as np, trimesh
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation as Rot
sys.path.insert(0, sys.argv[1]); import diag31 as D  # noqa: E402

XF = D.XF; T3 = D.T3; S = D.S
names, gt, N, tr = D.load_tracks()
H = [XF.host_geometry(D.T3D, n, s) for s, n in enumerate(names)]
det = np.load(f'{D.REF}/det_f0.npz', allow_pickle=True)
K = det['K'].astype(float) @ np.eye(3); K2 = np.diag([0.5, 0.5, 1.0]) @ K
masks = np.unpackbits(det['masks'], axis=-1)[:, :, :800].astype(bool)
msw = masks[det['chosen'][0]]; mrk = masks[det['chosen'][1]]
dep = np.load(f'{D.REF}/depth0.npy')[::2, ::2].astype(float)  # rectified full-res -> half res (same as det)
Hh, Ww = dep.shape


def fit_rigid(P, Q):
    mp, mq = P.mean(0), Q.mean(0); U, _, Vt = np.linalg.svd((P - mp).T @ (Q - mq))
    Dg = np.diag([1, 1, np.sign(np.linalg.det(Vt.T @ U.T))]); R = Vt.T @ Dg @ U.T; return R, mq - R @ mp


# mapping perception -> mocap from the P_s rack only (all frames, 100 points)
rk = names.index('plastic_dish_rack'); sw = names.index('mini_sweeper')
pts = H[rk]['points'][::10] + H[rk]['anchor']
P = np.concatenate([pts @ tr['Ps'][names[rk]][i][:3, :3].T + tr['Ps'][names[rk]][i][:3, 3] for i in range(N)])
Q = np.concatenate([pts @ gt[names[rk]][i][:3, :3].T + gt[names[rk]][i][:3, 3] for i in range(N)])
Rm, tm = fit_rigid(P, Q)
res = np.linalg.norm(P @ Rm.T + tm - Q, axis=1)
G = np.eye(4); G[:3, :3] = Rm.T; G[:3, 3] = -Rm.T @ tm   # mocap -> perception
out = dict(map_fit_resid_cm=dict(median=round(float(np.median(res) * 100), 3), p95=round(float(np.percentile(res, 95) * 100), 3)))

mesh = {n: trimesh.load(XF.scan_path(D.T3D, n), force='mesh') for n in names}
spl = {n: trimesh.sample.sample_surface(mesh[n], 400000 if n == names[rk] else 120000, seed=11)[0] for n in names}


def render(poses):
    """z-buffer of point splats; returns depth map and label map (-1 none, s slot)"""
    zb = np.full((Hh, Ww), np.inf); lab = np.full((Hh, Ww), -1)
    for s, n in enumerate(names):
        T = poses[n]; X = spl[n] @ T[:3, :3].T + T[:3, 3]
        uv = X @ K2.T; u = np.round(uv[:, 0] / uv[:, 2]).astype(int); v = np.round(uv[:, 1] / uv[:, 2]).astype(int); z = X[:, 2]
        ok = (u >= 0) & (u < Ww) & (v >= 0) & (v < Hh) & (z > 0)
        for du in (0, 1):   # 2x2 splat to close holes at half res
            for dv in (0, 1):
                uu, vv, zz = u[ok] + du, v[ok] + dv, z[ok]
                k = (uu < Ww) & (vv < Hh); uu, vv, zz = uu[k], vv[k], zz[k]
                order = np.argsort(-zz)  # far first, near overwrite
                cur = zb[vv[order], uu[order]]
                upd = zz[order] < cur
                zb[vv[order][upd], uu[order][upd]] = zz[order][upd]; lab[vv[order][upd], uu[order][upd]] = s
    return zb, lab


def iou(a, b):
    return float((a & b).sum() / max(1, (a | b).sum()))


truth = {n: G @ gt[n][0] for n in names}
cases = {'truth': truth,
         'Ps': {n: tr['Ps'][n][0] for n in names},
         'Po_scanframe': {n: tr['Po'][n][0] for n in names},
         'truth_sweeper+Ps_rack': {names[sw]: truth[names[sw]], names[rk]: tr['Ps'][names[rk]][0]},
         'Ps_sweeper+truth_rack': {names[sw]: tr['Ps'][names[sw]][0], names[rk]: truth[names[rk]]}}
valid = dep > 0
out['mask_px'] = dict(sweeper=int(msw.sum()), rack=int(mrk.sum()))
out['cases'] = {}
for k, poses in cases.items():
    zb, lab = render(poses)
    sil_sw_vis = lab == sw; sil_rk_vis = lab == rk
    # full (unoccluded) sweeper silhouette
    zs, ls = render({names[sw]: poses[names[sw]], names[rk]: np.eye(4) @ np.diag([1, 1, 1, 1]) @ np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, -10], [0, 0, 0, 1]])})
    sil_sw_full = ls == sw
    r = dict(sweeper_visible_px=int(sil_sw_vis.sum()), sweeper_full_px=int(sil_sw_full.sum()),
             sweeper_visible_frac=round(float(sil_sw_vis.sum() / max(1, sil_sw_full.sum())), 3),
             iou_mask_sweeper_visible=round(iou(sil_sw_vis, msw), 3), iou_mask_rack_visible=round(iou(sil_rk_vis, mrk), 3))
    for nm, sil in (('sweeper', sil_sw_vis), ('rack', sil_rk_vis)):
        m = sil & valid
        dz = (dep - zb)[m]
        r[f'{nm}_depth_resid_cm'] = dict(n=int(m.sum()), valid_frac=round(float(m.sum() / max(1, sil.sum())), 3),
                                         median=round(float(np.median(dz) * 100), 2), mad=round(float(np.median(np.abs(dz)) * 100), 2),
                                         frac_within_1cm=round(float(np.mean(np.abs(dz) < 0.01)), 3))
    # residual on OUR sweeper mask pixels (what the tracker was given): observed depth vs the rendered sweeper depth (unoccluded)
    m = msw & valid & sil_sw_full
    dz = (dep - zs)[m]
    r['on_sweeper_mask_depth_vs_rendered_sweeper_cm'] = dict(n=int(m.sum()), cover=round(float(m.sum() / max(1, (msw & valid).sum())), 3),
                                                             median=round(float(np.median(dz) * 100), 2) if m.any() else None,
                                                             mad=round(float(np.median(np.abs(dz)) * 100), 2) if m.any() else None)
    out['cases'][k] = r
    np.save(f'{sys.argv[2].replace(".json", "")}_{k}_lab.npy', lab.astype(np.int8))
# what the sweeper mask actually contains (truth render labels inside the sweeper mask)
zb, lab = render(truth)
inmask = lab[msw]
out['sweeper_mask_content_by_truth_render'] = dict(sweeper=round(float(np.mean(inmask == sw)), 3), rack=round(float(np.mean(inmask == rk)), 3),
                                                    background=round(float(np.mean(inmask == -1)), 3))
inmask = lab[mrk]
out['rack_mask_content_by_truth_render'] = dict(sweeper=round(float(np.mean(inmask == sw)), 3), rack=round(float(np.mean(inmask == rk)), 3),
                                                 background=round(float(np.mean(inmask == -1)), 3))
# observed depth inside the sweeper mask vs truth sweeper depth and truth rack depth
m = msw & valid
lab_sw = lab == sw
out['sweeper_mask_depth'] = dict(valid_frac=round(float(m.sum() / max(1, msw.sum())), 3))
# interpenetration at f0: sweeper scan samples inside the rack scan (winding / contains) for truth, P_s, P_o
rm = mesh[names[rk]]
spts = trimesh.sample.sample_surface(mesh[names[sw]], 4000, seed=5)[0]
pen = {}
for k in ('truth', 'Ps', 'Po_scanframe'):
    Ts, Tr = cases[k][names[sw]], cases[k][names[rk]]
    M = np.linalg.inv(Tr) @ Ts; q = spts @ M[:3, :3].T + M[:3, 3]
    inside = rm.contains(q) if rm.is_watertight else None
    tree = cKDTree(trimesh.sample.sample_surface(rm, 300000, seed=6)[0])
    dmin = tree.query(q)[0]
    pen[k] = dict(watertight=bool(rm.is_watertight), frac_inside=None if inside is None else round(float(inside.mean()), 4),
                  max_depth_mm=None if inside is None or not inside.any() else round(float(dmin[inside].max() * 1000), 1),
                  min_gap_mm=round(float(dmin.min() * 1000), 2))
out['penetration_f0'] = pen
# sweeper's lowest point vs the table plane (ours, from depth0) for truth/P_s/P_o; plane from det_rules like perc2's guard
sys.path.insert(0, f'{D.REPO}/pipeline'); import det_rules  # noqa: E402
hz = np.load(f'{D.REF}/hands_refined.npz', allow_pickle=True)
d0 = np.load(f'{D.REF}/depth0.npy')
pl = det_rules.table_plane(d0[::2, ::2].astype(np.float32), np.diag([0.5, 0.5, 1.0]) @ hz['KR'])
nrm, c0 = np.asarray(pl[0], float), float(pl[1])
out['table_plane'] = [np.round(nrm, 4).tolist(), round(c0, 4)]
vs = np.asarray(mesh[names[sw]].vertices)
tab = {}
for k in ('truth', 'Ps', 'Po_scanframe'):
    T = cases[k][names[sw]]; X = vs @ T[:3, :3].T + T[:3, 3]; h = X @ nrm + c0
    up = -nrm if np.median(h) < 0 else nrm
    hh = X @ up + (c0 if up is nrm else -c0)
    ax = T[:3, :3] @ np.array([0, 0, 1.0])
    tab[k] = dict(lowest_above_plane_cm=round(float(hh.min() * 100), 2), p2_cm=round(float(np.percentile(hh, 2) * 100), 2),
                  body_z_tilt_vs_plane_normal_deg=round(float(np.degrees(np.arccos(abs(ax @ nrm)))), 2))
out['sweeper_vs_our_table'] = tab
json.dump(out, open(sys.argv[2], 'w'), indent=1)
print(json.dumps(out, indent=1))
