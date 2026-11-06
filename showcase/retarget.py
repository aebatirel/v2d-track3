"""Retarget a FlashCHORD Sharpa reference to another floating hand (multi-embodiment showcase, 2026-11-06).

Source: the Sharpa reference that NVIDIA's retargeter (plus our contact retargeting) made from the video. Its per-frame
Sharpa link positions (robot_<side>_frames) are clean, consistent hand keypoints in the 21-point MANO layout
(0 wrist; thumb 1-4; index 5-8; middle 9-12; ring 13-16; pinky 17-20). The raw perceived MANO joints are noisier
(median finger bones 1.5-2.5 cm on ep27), so they are not used here.
Fit (per frame, per hand; pinocchio FK, scipy least_squares, warm-started from the previous frame): free root pose of
the robot's palm link + finger joints within limits so that robot links match the source keypoints (weighted: tips
1.0, distal 0.5, middle 0.4, knuckles 0.6, palm 0.3), with a small temporal smoothness term. Output: a copy of the
source parquet with robot_<side>_wrist_position / _wrist_wxyz / _finger_joints / joint names / frames replaced and
robot_name set; objects, contacts and MANO fields are unchanged.
Usage (any python with pinocchio + pyarrow + scipy):
  retarget.py SRC_PROCESSED.parquet ROBOTS_DIR ROBOT OUT_TREE   -> OUT_TREE/processed/sequence_id=<seq>/robot_name=<robot>/ref.parquet
No ground truth is read.
"""
import json, os, shutil, sys, time

import numpy as np
import pinocchio as pin
import pyarrow as pa
import pyarrow.parquet as pq
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation as Rot

# source keypoints: 21-point MANO layout from Sharpa frame names (side prefix added at use)
SRC = {0: 'hand_C_MC', 1: 'thumb_CMC_FE', 2: 'thumb_MCP_FE', 3: 'thumb_IP', 4: 'thumb_tip_site',
       5: 'index_MCP_FE', 6: 'index_PIP', 7: 'index_DIP', 8: 'index_tip_site',
       9: 'middle_MCP_FE', 10: 'middle_PIP', 11: 'middle_DIP', 12: 'middle_tip_site',
       13: 'ring_MCP_FE', 14: 'ring_PIP', 15: 'ring_DIP', 16: 'ring_tip_site',
       17: 'pinky_MCP_FE', 18: 'pinky_PIP', 19: 'pinky_DIP', 20: 'pinky_tip_site'}
W_TIP, W_DP, W_MID, W_MCP, W_PALM = 1.0, 0.5, 0.4, 0.6, 0.3
# robot link (name after "<side>_") -> source keypoint (int, or list = mean), weight
TARGETS = {
    'shadow': [('thumb_fingertip', 4, W_TIP), ('thumb_DP', 3, W_DP), ('thmiddle', 2, W_MCP),
               ('index_fingertip', 8, W_TIP), ('index_DP', 7, W_DP), ('ffmiddle', 6, W_MID), ('ffproximal', 5, W_MCP),
               ('middle_fingertip', 12, W_TIP), ('middle_DP', 11, W_DP), ('mfmiddle', 10, W_MID), ('mfproximal', 9, W_MCP),
               ('ring_fingertip', 16, W_TIP), ('ring_DP', 15, W_DP), ('rfmiddle', 14, W_MID), ('rfproximal', 13, W_MCP),
               ('pinky_fingertip', 20, W_TIP), ('pinky_DP', 19, W_DP), ('lfmiddle', 18, W_MID), ('lfproximal', 17, W_MCP)],
    'allegro': [('thumb_fingertip', 4, W_TIP), ('thumb_DP', 3, W_DP), ('link_14.0', 2, W_MCP),
                ('index_fingertip', 8, W_TIP), ('index_DP', 7, W_DP), ('link_2.0', 6, W_MID), ('link_1.0', 5, W_MCP),
                ('middle_fingertip', 12, W_TIP), ('middle_DP', 11, W_DP), ('link_6.0', 10, W_MID), ('link_5.0', 9, W_MCP),
                ('ring_fingertip', 16, W_TIP), ('ring_DP', 15, W_DP), ('link_10.0', 14, W_MID), ('link_9.0', 13, W_MCP)],
    'leap': [('thumb_fingertip', 4, W_TIP), ('thumb_DP', 3, W_DP), ('thumb_dip', 2, W_MCP),
             ('index_fingertip', 8, W_TIP), ('index_DP', 7, W_DP), ('dip', 6, W_MID), ('pip', 5, W_MCP),
             ('middle_fingertip', 12, W_TIP), ('middle_DP', 11, W_DP), ('dip_2', 10, W_MID), ('pip_2', 9, W_MCP),
             ('ring_fingertip', 16, W_TIP), ('ring_DP', 15, W_DP), ('dip_3', 14, W_MID), ('pip_3', 13, W_MCP)],
    'inspire': [('thumb_fingertip', 4, W_TIP), ('thumb_DP', 3, W_DP), ('thumb_intermediate', 2, W_MCP),
                ('index_fingertip', 8, W_TIP), ('index_DP', 6, W_MID), ('index_proximal', 5, W_MCP),
                ('middle_fingertip', 12, W_TIP), ('middle_DP', 10, W_MID), ('middle_proximal', 9, W_MCP),
                ('ring_fingertip', 16, W_TIP), ('ring_DP', 14, W_MID), ('ring_proximal', 13, W_MCP),
                ('pinky_fingertip', 20, W_TIP), ('pinky_DP', 18, W_MID), ('pinky_proximal', 17, W_MCP)],
    'dex3': [('thumb_fingertip', 4, W_TIP), ('thumb_DP', 3, W_DP), ('hand_thumb_1_link', 2, W_MCP),
             ('index_fingertip', 8, W_TIP), ('index_DP', 6, W_MID), ('hand_index_0_link', 5, W_MCP),
             ('middle_fingertip', 12, W_TIP), ('middle_DP', 10, W_MID), ('hand_middle_0_link', 9, W_MCP),
             ('palm', 0, W_PALM)],
    'barrett': [('thumb_fingertip', 4, W_TIP), ('thumb_DP', 3, W_DP), ('finger_3_med_link', 2, W_MCP),
                ('index_fingertip', 8, W_TIP), ('index_DP', 7, W_DP), ('finger_1_med_liink', 5, W_MCP),
                ('middle_fingertip', [12, 16], W_TIP), ('middle_DP', [11, 15], W_DP), ('finger_2_med_link', [9, 13], W_MCP),
                ('palm', 0, W_PALM)],
    'dclaw': [('thumb_fingertip', 4, W_TIP), ('thumb_DP', 3, W_DP),
              ('index_fingertip', 8, W_TIP), ('index_DP', 7, W_DP),
              ('middle_fingertip', [12, 16], W_TIP), ('middle_DP', [11, 15], W_DP), ('palm', [0, 9], W_PALM)],
    'panda': [('thumb_fingertip', 4, W_TIP), ('thumb_DP', 3, W_DP),
              ('index_fingertip', [8, 12], W_TIP), ('index_DP', [7, 11], W_DP), ('palm', [0, 5, 9, 13], W_PALM)],
}
W_SMOOTH_P, W_SMOOTH_R, W_SMOOTH_Q = 0.3, 0.05, 0.02


class Hand:
    def __init__(self, urdf, side, robot):
        self.m = pin.buildModelFromUrdf(urdf, pin.JointModelFreeFlyer()); self.d = self.m.createData()
        self.side = side
        self.jnames = list(self.m.names)[2:]
        self.lo = self.m.lowerPositionLimit[7:].copy(); self.hi = self.m.upperPositionLimit[7:].copy()
        bad = ~np.isfinite(self.lo) | ~np.isfinite(self.hi) | (self.lo >= self.hi)
        self.lo[bad], self.hi[bad] = -3.14, 3.14
        self.targets = []
        for link, src, w in TARGETS[robot]:
            fid = self.m.getFrameId(f'{side}_{link}')
            if fid >= len(self.m.frames):
                raise KeyError(f'{robot} {side}: no frame {side}_{link}')
            self.targets.append((fid, [src] if isinstance(src, int) else list(src), w))
        self.nj = len(self.jnames)

    def q_of(self, p, R, qj):
        return np.concatenate([p, Rot.from_matrix(R).as_quat(), qj])  # pinocchio free flyer: xyz + qx qy qz qw

    def fk(self, q):
        pin.framesForwardKinematics(self.m, self.d, q)
        return np.array([self.d.oMf[fid].translation for fid, _, _ in self.targets])

    def solve(self, K, prev, iters):
        """K: (21, 3) source keypoints. prev: (p, R, qj) warm start. Returns (p, R, qj, rms error m)."""
        p0, R0, q0 = prev
        tgt = np.array([K[s].mean(0) for _, s, _ in self.targets]); w = np.array([w for _, _, w in self.targets])

        def res(x):
            p, r, qj = x[:3], x[3:6], x[6:]
            R = Rot.from_rotvec(r).as_matrix() @ R0
            e = (self.fk(self.q_of(p, R, qj)) - tgt) * w[:, None]
            return np.concatenate([e.ravel(), W_SMOOTH_P * (p - p0), W_SMOOTH_R * r, W_SMOOTH_Q * (qj - q0)])
        x0 = np.concatenate([p0, np.zeros(3), np.clip(q0, self.lo + 1e-6, self.hi - 1e-6)])
        lb = np.concatenate([np.full(6, -np.inf), self.lo]); ub = np.concatenate([np.full(6, np.inf), self.hi])
        sol = least_squares(res, x0, bounds=(lb, ub), max_nfev=iters, x_scale='jac')
        p, r, qj = sol.x[:3], sol.x[3:6], sol.x[6:]
        R = Rot.from_rotvec(r).as_matrix() @ R0
        err = np.linalg.norm(self.fk(self.q_of(p, R, qj)) - tgt, axis=1)
        return p, R, qj, err


def kabsch(A, B):
    """R, t minimising |R A + t - B| (rows are points)."""
    ca, cb = A.mean(0), B.mean(0); H = (A - ca).T @ (B - cb); U, _, Vt = np.linalg.svd(H)
    D = np.diag([1, 1, np.sign(np.linalg.det(Vt.T @ U.T))]); R = Vt.T @ D @ U.T
    return R, cb - R @ ca


def retarget_side(row, side, robot, urdf):
    h = Hand(urdf, side, robot)
    names = row[f'{side}_robot_frame_names']; F = np.asarray(row[f'robot_{side}_frames'], dtype=np.float64)
    idx = [names.index(f'{side}_{SRC[k]}') for k in range(21)]
    K = F[:, idx, :3]                                               # (T, 21, 3)
    T = K.shape[0]
    qn = np.clip(np.zeros(h.nj), h.lo, h.hi)                        # neutral pose -> initial root by Kabsch
    A = h.fk(h.q_of(np.zeros(3), np.eye(3), qn)); B = np.array([K[0][s].mean(0) for _, s, _ in h.targets])
    R, t = kabsch(A, B)
    prev = (t, R, qn)
    out_p, out_q, out_j, errs = np.zeros((T, 3)), np.zeros((T, 4)), np.zeros((T, h.nj)), np.zeros((T, len(h.targets)))
    for f in range(T):
        p, R, qj, e = h.solve(K[f], prev, 400 if f == 0 else 60)
        if f == 0:                                                  # settle the first frame twice
            p, R, qj, e = h.solve(K[f], (p, R, qj), 400)
        prev = (p, R, qj)
        out_p[f] = p; xyzw = Rot.from_matrix(R).as_quat(); out_q[f] = xyzw[[3, 0, 1, 2]]; out_j[f] = qj; errs[f] = e
    tip = np.array([i for i, (_, _, w) in enumerate(h.targets) if w == W_TIP])
    return dict(p=out_p, wxyz=out_q, q=out_j, names=h.jnames, err=errs, tip_err=errs[:, tip])


def main():
    src, robots_dir, robot, out_tree = sys.argv[1:5]
    t0 = time.time()
    tab = pq.ParquetFile(src).read(); row = tab.to_pylist()[0]       # hive columns (sequence_id, robot_name) live in the path
    seq = os.path.basename(os.path.dirname(os.path.dirname(os.path.abspath(src)))).split('=', 1)[1]
    rep = {}
    for side in ('left', 'right'):
        urdf = os.path.join(robots_dir, robot, f'{side}.urdf')
        r = retarget_side(row, side, robot, urdf)
        T = r['p'].shape[0]
        row[f'robot_{side}_wrist_position'] = r['p'].tolist()
        row[f'robot_{side}_wrist_wxyz'] = r['wxyz'].tolist()
        row[f'robot_{side}_finger_joints'] = r['q'].tolist()
        row[f'{side}_robot_finger_joint_names'] = r['names']
        row[f'{side}_robot_frame_names'] = [f'{side}_palm']
        row[f'{side}_robot_frame_task_names'] = [f'{side}_palm']
        row[f'robot_{side}_frames'] = np.concatenate([r['p'], r['wxyz']], 1)[:, None, :].tolist()
        row[f'robot_{side}_frame_task_errors'] = np.median(r['err'], 1, keepdims=True).tolist()
        row[f'robot_{side}_num_optimization_iterations'] = [0] * T
        rep[side] = dict(tip_err_cm_median=float(np.median(r['tip_err']) * 100), tip_err_cm_p95=float(np.percentile(r['tip_err'], 95) * 100),
                         all_err_cm_median=float(np.median(r['err']) * 100), joints=len(r['names']))
    d = os.path.join(out_tree, 'processed', f'sequence_id={seq}', f'robot_name={robot}')
    os.makedirs(d, exist_ok=True)
    changed = [n for n in tab.schema.names if n.startswith(('robot_left', 'robot_right', 'left_robot', 'right_robot'))]
    inferred = pa.Table.from_pylist([{n: row[n] for n in changed}]).schema
    schema = tab.schema
    for n in changed:
        schema = schema.set(schema.get_field_index(n), inferred.field(n))
    new = pa.Table.from_pylist([row], schema=schema)
    pq.write_table(new, os.path.join(d, 'ref.parquet'))
    stage = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(src))))), 'reconstructed_stage')
    if os.path.isdir(stage) and not os.path.exists(os.path.join(out_tree, 'reconstructed_stage')):
        shutil.copytree(stage, os.path.join(out_tree, 'reconstructed_stage'))
    rep['seconds'] = round(time.time() - t0, 1); rep['source'] = os.path.abspath(src)
    json.dump(rep, open(os.path.join(out_tree, f'retarget_{robot}.json'), 'w'), indent=1)
    print(robot, json.dumps(rep))


if __name__ == '__main__':
    main()
