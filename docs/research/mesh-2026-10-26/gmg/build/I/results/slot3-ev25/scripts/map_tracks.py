"""Rigid per-board comparison of two eval-25 board tracks (ours = local evperc copy, ref = the packed reference's
perception track perc2/ep25/poses.npz of run 20261026-c25s42-feb0407), plus the check that the packed reference
parquet replays the ref track. GT-free: both inputs are our own perception outputs; no dataset parquet, mocap, scan
or alignment file is opened."""
import json, sys, hashlib
import numpy as np

ours_p, ref_p, wvo_p, pq_p, tf_p, out_p = sys.argv[1:7]
N = ['wooden_piece_1', 'wooden_piece_2']


def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def rot_angle(R):
    c = (np.trace(R, axis1=-2, axis2=-1) - 1) / 2
    return np.degrees(np.arccos(np.clip(c, -1, 1)))


def mean_rot(Rs):
    M = Rs.sum(0)
    U, _, Vt = np.linalg.svd(M)
    D = np.diag([1, 1, np.sign(np.linalg.det(U @ Vt))])
    return U @ D @ Vt


def name_rot(R):
    cands = {'I': np.eye(3), 'Rx180': np.diag([1, -1, -1.]), 'Ry180': np.diag([-1, 1, -1.]), 'Rz180': np.diag([-1, -1, 1.])}
    best = min(cands, key=lambda k: rot_angle(cands[k].T @ R))
    return best, float(rot_angle(cands[best].T @ R))


O = np.load(ours_p, allow_pickle=False)
Rf = np.load(ref_p, allow_pickle=False)
T = O['world_T_cam'].shape[0]
res = dict(inputs=dict(ours=dict(path=ours_p, sha256=sha(ours_p)), ref=dict(path=ref_p, sha256=sha(ref_p))), T=int(T))
wtc = np.abs(O['world_T_cam'] - Rf['world_T_cam']).max()
res['world_T_cam_maxabs_diff'] = float(wtc)
pairs = {}
for a in N:
    A = O[f'cam_T_{a}'].astype(np.float64)
    for b in N:
        B = Rf[f'cam_T_{b}'].astype(np.float64)
        dt = np.linalg.norm(A[:, :3, 3] - B[:, :3, 3], axis=1) * 1000
        # constant body offset X with B ~ A X  (X = A^-1 B per frame)
        X = np.einsum('tji,tjk->tik', A[:, :3, :3], B[:, :3, :3])
        Xm = mean_rot(X)
        spread = rot_angle(np.einsum('ji,tjk->tik', Xm, X))
        # constant body-frame translation offset: p = A^-1 (tB - tA)
        p = np.einsum('tji,tj->ti', A[:, :3, :3], B[:, :3, 3] - A[:, :3, 3])
        pm = np.median(p, 0)
        # residual after applying the constant rigid offset (A X -> B)
        Bh_t = A[:, :3, 3] + np.einsum('tij,j->ti', A[:, :3, :3], pm)
        Bh_R = np.einsum('tij,jk->tik', A[:, :3, :3], Xm)
        rt = np.linalg.norm(Bh_t - B[:, :3, 3], axis=1) * 1000
        rr = rot_angle(np.einsum('tji,tjk->tik', Bh_R, B[:, :3, :3]))
        nm, nd = name_rot(Xm)
        pairs[f'ours.{a}->ref.{b}'] = dict(
            centre_dist_mm=dict(median=float(np.median(dt)), p90=float(np.percentile(dt, 90)), max=float(dt.max()),
                                f0=float(dt[0]), flast=float(dt[-1])),
            rel_rot_raw_deg_median=float(np.median(rot_angle(X))),
            offset_rot=dict(nearest=nm, off_nearest_deg=nd, spread_deg_median=float(np.median(spread)),
                            spread_deg_p90=float(np.percentile(spread, 90)), matrix=np.round(Xm, 4).tolist()),
            offset_trans_mm=np.round(pm * 1000, 2).tolist(),
            resid_after_const_offset=dict(t_mm_median=float(np.median(rt)), t_mm_p90=float(np.percentile(rt, 90)),
                                          t_mm_max=float(rt.max()), R_deg_median=float(np.median(rr)),
                                          R_deg_p90=float(np.percentile(rr, 90)), R_deg_max=float(rr.max())))
res['pairs'] = pairs
# assignment: the permutation with the smaller summed median centre distance
s_id = pairs['ours.wooden_piece_1->ref.wooden_piece_1']['centre_dist_mm']['median'] + \
    pairs['ours.wooden_piece_2->ref.wooden_piece_2']['centre_dist_mm']['median']
s_sw = pairs['ours.wooden_piece_1->ref.wooden_piece_2']['centre_dist_mm']['median'] + \
    pairs['ours.wooden_piece_2->ref.wooden_piece_1']['centre_dist_mm']['median']
res['assignment_cost_mm'] = dict(identity=float(s_id), swapped=float(s_sw))
res['mapping'] = ({'wooden_piece_1': 'wooden_piece_1', 'wooden_piece_2': 'wooden_piece_2'} if s_id < s_sw else
                  {'wooden_piece_1': 'wooden_piece_2', 'wooden_piece_2': 'wooden_piece_1'})
# ref track -> packed parquet: object_body_position / wxyz (table frame) vs table_T_world world_T_cam cam_T_obj
import pyarrow.parquet as pq
t = pq.read_table(pq_p).to_pylist()[0]
tf = np.load(tf_p, allow_pickle=False)
TW = tf['T_table_from_world']
names = list(t['object_body_names'])
pos = np.asarray(t['object_body_position'], dtype=np.float64)
q = np.asarray(t['object_body_wxyz'], dtype=np.float64)
res['parquet'] = dict(path=pq_p, sha256=sha(pq_p), md5=hashlib.md5(open(pq_p, 'rb').read()).hexdigest(),
                      object_name=names, pos_shape=list(pos.shape), wxyz_shape=list(q.shape),
                      object_mesh_paths=t.get('object_mesh_paths'), object_urdf_paths=t.get('object_urdf_paths'))


def q2R(qq):
    w, x, y, z = qq[..., 0], qq[..., 1], qq[..., 2], qq[..., 3]
    return np.stack([np.stack([1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)], -1),
                     np.stack([2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)], -1),
                     np.stack([2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)], -1)], -2)


pp = {}
if pos.ndim == 3:  # (T, n_obj, 3) or (n_obj, T, 3)
    if pos.shape[0] == len(names) and pos.shape[1] != len(names):
        pos = pos.transpose(1, 0, 2); q = q.transpose(1, 0, 2)
    for k, nme in enumerate(names):
        P = pos[:, k]; Rq = q2R(q[:, k])
        for src, Z in (('ref', Rf), ('ours', O)):
            for b in N:
                W = np.einsum('ij,tjk,tkl->til', TW, Z['world_T_cam'], Z[f'cam_T_{b}'].astype(np.float64))
                d = W[:, :3, 3] - P
                # allow a constant translation (the per-object z snap) : residual about the median offset
                off = np.median(d, 0)
                r = np.linalg.norm(d - off, axis=1) * 1000
                ang = rot_angle(np.einsum('tji,tjk->tik', W[:, :3, :3], Rq))
                rr_ = np.asarray(t['object_root_position'], dtype=np.float64)
                rinfo = {}
                if rr_.shape == pos.shape or (rr_.ndim == 3):
                    R0 = rr_ if rr_.shape[:2] == (T, len(names)) else rr_.transpose(1, 0, 2)
                    d2 = W[:, :3, 3] - R0[:, k]; o2 = np.median(d2, 0); r2 = np.linalg.norm(d2 - o2, axis=1) * 1000
                    rinfo = dict(root_const_offset_mm=np.round(o2 * 1000, 2).tolist(), root_resid_mm_median=float(np.median(r2)),
                                 root_resid_mm_max=float(r2.max()))
                if src == 'ref' and b == nme:
                    dd = (P - W[:, :3, 3]) * 1000
                    rinfo.update(table_frame_dxy_absmax_mm=np.round(np.abs(dd[:, :2]).max(0), 3).tolist(),
                                 table_frame_dz_mm=dict(min=float(dd[:, 2].min()), median=float(np.median(dd[:, 2])),
                                                        max=float(dd[:, 2].max()), f0=float(dd[0, 2])))
                pp[f'parquet.{nme}<-{src}.{b}'] = dict(**rinfo, const_offset_mm=np.round(off * 1000, 2).tolist(),
                                                       resid_mm_median=float(np.median(r)), resid_mm_max=float(r.max()),
                                                       rot_deg_median=float(np.median(ang)), rot_deg_max=float(ang.max()))
res['parquet_vs_tracks'] = pp
res['world_vo'] = dict(path=wvo_p, sha256=sha(wvo_p))
json.dump(res, open(out_p, 'w'), indent=1)
print(json.dumps({k: v for k, v in res.items() if k not in ('pairs', 'parquet_vs_tracks')}, indent=1)[:3000])
for k, v in pairs.items():
    print(k, json.dumps(v['centre_dist_mm']), v['offset_rot']['nearest'], round(v['offset_rot']['off_nearest_deg'], 2),
          'spread', round(v['offset_rot']['spread_deg_median'], 2), 'resid', json.dumps(v['resid_after_const_offset']))
for k, v in pp.items():
    print(k, json.dumps(v))
