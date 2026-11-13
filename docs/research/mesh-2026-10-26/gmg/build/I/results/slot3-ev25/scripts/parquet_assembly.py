"""Report-only: relative pose board 2 in board 1 over f294-355 of (a) the packed reference parquet (object_body_position
/ wxyz, table frame: what the simulator replays), (b) the reference perception track perc2/ep25/poses.npz and (c) our
mapped track, all in the table frame (T_table_from_world world_T_cam cam_T_obj). GT-free (our own outputs).
usage: parquet_assembly.py PARQUET POSES_REF TABLE_FRAME POSES_MAPPED OUT.json"""
import json, sys
import numpy as np
import pyarrow.parquet as pq
pq_p, ref_p, tf_p, map_p, out_p = sys.argv[1:6]
t = pq.read_table(pq_p).to_pylist()[0]
names = list(t['object_body_names'])
P = np.asarray(t['object_body_position']); Q = np.asarray(t['object_body_wxyz'])
Rf = np.load(ref_p, allow_pickle=False); TW = np.load(tf_p, allow_pickle=False)['T_table_from_world']
M = np.load(map_p, allow_pickle=False)


def q2R(q):
    w, x, y, z = q[..., 0], q[..., 1], q[..., 2], q[..., 3]
    return np.stack([np.stack([1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)], -1),
                     np.stack([2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)], -1),
                     np.stack([2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)], -1)], -2)


def Tm(p, q):
    T = np.tile(np.eye(4), (len(p), 1, 1)); T[:, :3, :3] = q2R(q); T[:, :3, 3] = p
    return T


def inv(T):
    Ti = np.zeros_like(T); Ti[:, :3, :3] = np.swapaxes(T[:, :3, :3], 1, 2)
    Ti[:, :3, 3] = -np.einsum('tij,tj->ti', Ti[:, :3, :3], T[:, :3, 3]); Ti[:, 3, 3] = 1
    return Ti


win = np.arange(294, min(356, len(P)))
world = lambda Z, o: np.einsum('ij,tjk,tkl->til', TW, Z['world_T_cam'], Z['cam_T_' + o].astype(float))
par = {o: Tm(P[:, k], Q[:, k]) for k, o in enumerate(names)}
ref = {o: world(Rf, o) for o in names}; mp = {o: world(M, o) for o in names}
res = dict(window=[int(win[0]), int(win[-1])], board_1=names[0], board_2=names[1])
rp = np.einsum('tij,tjk->tik', inv(par[names[0]]), par[names[1]])
for name, A in (('ref_track', ref), ('mapped_track', mp)):
    ra = np.einsum('tij,tjk->tik', inv(A[names[0]]), A[names[1]])
    d = (ra[:, :3, 3] - rp[:, :3, 3]) * 1000
    dR = np.degrees(np.arccos(np.clip((np.trace(np.einsum('tji,tjk->tik', ra[:, :3, :3], rp[:, :3, :3]), axis1=1,
                                                axis2=2) - 1) / 2, -1, 1)))
    res[name + '_vs_parquet_rel_b2_in_b1'] = dict(
        dt_mm_median=float(np.median(np.linalg.norm(d[win], axis=1))), dt_mm_max=float(np.linalg.norm(d[win], axis=1).max()),
        dxyz_mm_median_in_b1_frame=np.round(np.median(d[win], 0), 2).tolist(), dR_deg_median=float(np.median(dR[win])),
        dR_deg_max=float(dR[win].max()))
for o in names:
    dz = (par[o][:, 2, 3] - ref[o][:, 2, 3]) * 1000
    res['parquet_minus_ref_table_z_mm_' + o] = dict(min=float(dz[win].min()), median=float(np.median(dz[win])),
                                                    max=float(dz[win].max()))
json.dump(res, open(out_p, 'w'), indent=1)
print(json.dumps(res, indent=1))
