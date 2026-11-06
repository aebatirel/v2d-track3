"""Report-only: relative pose board 2 in board 1 (reference names) of our mapped track vs the packed reference track,
per frame and over the late frames 294-355 (the eval-25 assembled window named in the work log, 26 Oct T-a test).
Also the per-board difference of the mapped track vs the reference (cam frame). GT-free (both are our perception)."""
import json, sys
import numpy as np
mapped_p, ref_p, out_p = sys.argv[1:4]
M = np.load(mapped_p, allow_pickle=False); R = np.load(ref_p, allow_pickle=False)
N = ['wooden_piece_1', 'wooden_piece_2']


def ang(Rm):
    return np.degrees(np.arccos(np.clip((np.trace(Rm, axis1=-2, axis2=-1) - 1) / 2, -1, 1)))


def inv(T):
    Ti = np.zeros_like(T); Ti[..., :3, :3] = np.swapaxes(T[..., :3, :3], -1, -2)
    Ti[..., :3, 3] = -np.einsum('...ij,...j->...i', Ti[..., :3, :3], T[..., :3, 3]); Ti[..., 3, 3] = 1
    return Ti


out = dict(mapped=mapped_p, ref=ref_p)
T = len(M['world_T_cam'])
win = np.arange(294, min(356, T))
for o in N:
    A = M[f'cam_T_{o}'].astype(float); B = R[f'cam_T_{o}'].astype(float)
    dt = np.linalg.norm(A[:, :3, 3] - B[:, :3, 3], axis=1) * 1000
    da = ang(np.einsum('tji,tjk->tik', A[:, :3, :3], B[:, :3, :3]))
    out[o] = dict(all=dict(dt_mm_median=float(np.median(dt)), dt_mm_p90=float(np.percentile(dt, 90)),
                           dR_deg_median=float(np.median(da)), dR_deg_p90=float(np.percentile(da, 90))),
                  f294_355=dict(dt_mm_median=float(np.median(dt[win])), dt_mm_max=float(dt[win].max()),
                                dR_deg_median=float(np.median(da[win])), dR_deg_max=float(da[win].max())))
rel = lambda Z: np.einsum('tij,tjk->tik', inv(Z['cam_T_wooden_piece_1'].astype(float)), Z['cam_T_wooden_piece_2'].astype(float))
Rm, Rr = rel(M), rel(R)
d = np.einsum('tij,tjk->tik', inv(Rm), Rr)
dtr = (Rm[:, :3, 3] - Rr[:, :3, 3]) * 1000                     # in board-1 frame
out['rel_b2_in_b1'] = dict(
    f294_355=dict(dt_mm_median=float(np.median(np.linalg.norm(dtr[win], axis=1))),
                  dt_mm_max=float(np.linalg.norm(dtr[win], axis=1).max()),
                  dt_xyz_mm_median=np.round(np.median(dtr[win], 0), 2).tolist(),
                  dR_deg_median=float(np.median(ang(d[win, :3, :3]))), dR_deg_max=float(ang(d[win, :3, :3]).max())),
    note='board-1 frame of each track; difference mapped minus reference')
json.dump(out, open(out_p, 'w'), indent=1)
print(json.dumps(out, indent=1))
