"""Object-only audit of official policy rollouts (episode parquets, kit reader): per rollout and object, the frame it
first leaves its rest (> 5 mm or > 3 deg from its simulated frame-0 pose), lift (z - z0) vs our reference's lift at the
reference's lifted frames, error to the reference over windows, frames within 3 cm. Our reference only, except the
registered AUC copied from score_registered (computed vs mocap after inference)."""
import sys, glob, json, os
import numpy as np
sys.path.insert(0, '/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/kit/v2d_submission_kit')
from v2dlb.submission_parquet import read_trajectory
from scipy.spatial.transform import Rotation as R
wins = [(0, 20), (20, 40), (40, 60), (60, 90), (90, 120), (120, 160), (160, 200), (200, 260), (260, 400)]
for path in sys.argv[1:]:
    tr = read_trajectory(path); reg = os.path.join(os.path.dirname(path), [f for f in os.listdir(os.path.dirname(path)) if f.startswith('score_registered')][0]) if any(f.startswith('score_registered') for f in os.listdir(os.path.dirname(path))) else None
    auc = None
    if reg:
        d = json.load(open(reg)); s_ = d.get('sim', {}); auc = (s_.get('AUC'), s_.get('per_obj_AUC'))
    print(f'== {path.split("runs/")[-1]}  registered AUC {auc}')
    for slot in np.unique(tr.object_slot):
        k = tr.object_slot == slot; fr = tr.frame_index[k]; o = np.argsort(fr); P = tr.pose_xyzw[k][o]; Q = tr.reference_xyzw[k][o]; name = tr.object_name[k][0]
        disp = 1000 * np.linalg.norm(P[:, :3] - P[0, :3], axis=1); turn = np.degrees((R.from_quat(P[:, 3:]) * R.from_quat(P[0, 3:]).inv()).magnitude())
        dep = int(np.argmax((disp > 5) | (turn > 3))) if ((disp > 5) | (turn > 3)).any() else None
        lift = 100 * (P[:, 2] - P[0, 2]); rlift = 100 * (Q[:, 2] - Q[0, 2]); err = 100 * np.linalg.norm(P[:, :3] - Q[:, :3], axis=1)
        rd = 100 * np.linalg.norm(Q[:, :3] - Q[0, :3], axis=1)
        rmv = int(np.argmax(rd > 1.0)) if (rd > 1).any() else None
        up = rlift > 2
        print(f'  {name:14s} leaves rest f{dep} (ref moves >1cm f{rmv}); max lift {lift.max():5.1f} cm (ref {rlift.max():4.1f}); '
              f'on ref-lifted frames ({up.sum()}): sim lifted>2cm {np.mean(lift[up] > 2) if up.any() else float("nan"):.2f}; within 3 cm {np.mean(err <= 3):.2f}; '
              f'first err>3cm f{int(np.argmax(err > 3)) if (err > 3).any() else None}, >10cm f{int(np.argmax(err > 10)) if (err > 10).any() else None}')
        print('     err cm per window ' + ' '.join(f'{a}-{b}:{err[a:min(b, len(err))].mean():4.1f}' for a, b in wins if a < len(err)))
        print('     lift sim/ref per window ' + ' '.join(f'{a}-{b}:{lift[a:min(b, len(err))].mean():4.1f}/{rlift[a:min(b, len(err))].mean():4.1f}' for a, b in wins if a < len(err)))
