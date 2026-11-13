"""PREREG section 3.2 mkref depth rule (GT-free; eval 10): mkref's own fit_table / table_frame / snap (its defaults) on
the RAW stored track (the packed base reference's mkref input) with depth candidates D1 (det_f0 2x2 = depth0.npy) and
D2 (frame 0 of the 29 Oct eval cache), compared with the packed base reference's table_frame.npz (plane_n, plane_d).
Also the same on the V4p track (reported). Usage: python -I depth_rule.py REPO POSES_RAW POSES_V4P D1 D2 HANDS CALIB ASSETS PACKED_TF OUT"""
import sys, types, json
import numpy as np, trimesh
REPO, PRAW, PV, D1, D2, HANDS, CALIB, ASSETS, PTF, OUT = sys.argv[1:11]
sys.path.insert(0, f'{REPO}/pipeline'); import mkref as MK
a = types.SimpleNamespace(ring_in=10, ring_out=90, plane_thr=0.006, plane_iters=1000, support_tol=0.03, support_max=0.05,
                          support_fallback=1, snap='per_object', snap_max=0.02, table_z=0.60)
names = ['blue_cup', 'beige_cup']
vis = {n: trimesh.load(MK.visual_mesh_path(ASSETS, n), force='mesh') for n in names}
KR = MK.rectified_K(CALIB); KRh = np.asarray(np.load(HANDS)['KR'], float)
ptf = np.load(PTF); pn, pd_ = np.asarray(ptf['plane_n'], float), float(ptf['plane_d'])
def run(poses, dfile, frame0_of_3d):
    P = np.load(poses); W_C = P['world_T_cam'].astype(float); cam_T = {n: P[f'cam_T_{n}'].astype(float) for n in names}
    D = np.load(dfile, mmap_mode='r'); d0 = np.asarray(D[0] if D.ndim == 3 else D, np.float32)
    n, d, frac, npts, rms = MK.fit_table(d0, KR, W_C[0], {nm: cam_T[nm][0] for nm in names}, vis, a)
    ang = float(np.degrees(np.arccos(np.clip(abs(n @ pn), -1, 1))))
    OBJw = np.stack([W_C[0] @ cam_T[nm][0] for nm in names])
    cen = np.mean([OBJw[b, :3, :3] @ np.asarray(vis[nm].vertices).mean(0) + OBJw[b, :3, 3] for b, nm in enumerate(names)], 0)
    T_tab = MK.table_frame(n, d, W_C[0], cen, a.table_z)
    h = [float((np.asarray(vis[nm].vertices) @ (T_tab @ OBJw[b])[:3, :3].T + (T_tab @ OBJw[b])[:3, 3])[:, 2].min() - a.table_z) for b, nm in enumerate(names)]
    return dict(n=np.round(n, 6).tolist(), d=round(float(d), 6), inlier_frac=round(float(frac), 4), ring_points=int(npts), rms_mm=round(float(rms) * 1000, 3),
                angle_to_packed_deg=round(ang, 4), abs_dd_mm=round(abs(float(d) - pd_) * 1000, 3),
                bottoms_cm=dict(zip(names, np.round(np.array(h) * 100, 2).tolist())),
                T_table_from_world_diff_vs_packed=dict(rot_deg=round(float(np.degrees(np.arccos(np.clip((np.trace(T_tab[:3, :3] @ ptf['T_table_from_world'][:3, :3].T) - 1) / 2, -1, 1)))), 4),
                                                        trans_mm=round(float(np.linalg.norm(T_tab[:3, 3] - ptf['T_table_from_world'][:3, 3])) * 1000, 3)))
res = dict(packed=dict(n=np.round(pn, 6).tolist(), d=round(pd_, 6), source=PTF), KR_calib_vs_hands_max_abs=float(np.abs(KR - KRh).max()),
           raw={'D1': run(PRAW, D1, 0), 'D2': run(PRAW, D2, 0)}, v4p={'D1': run(PV, D1, 0), 'D2': run(PV, D2, 0)})
r = res['raw']
k = sorted(['D1', 'D2'], key=lambda x: (r[x]['angle_to_packed_deg'], r[x]['abs_dd_mm']))
if abs(r['D1']['angle_to_packed_deg'] - r['D2']['angle_to_packed_deg']) <= 0.05:
    k = sorted(['D1', 'D2'], key=lambda x: r[x]['abs_dd_mm'])
res['rule'] = 'PREREG 3.2: smaller angle between normals vs the packed table_frame.npz on the raw track; within 0.05 deg the smaller |dd|'
res['chosen'] = k[0]
json.dump(res, open(OUT, 'w'), indent=1); print(json.dumps(res, indent=1))
