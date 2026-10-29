"""Official policy rollouts (kit reader) vs the body trace of the same policy: is the trace representative?
Per rollout and object: registered AUC (from score_registered, computed vs mocap after inference: diagnostic),
the frame the object leaves rest, max lift, the frame its lift first exceeds 2 cm, mean |rollout - trace| position."""
import sys, glob, json, os
import numpy as np
sys.path.insert(0, '/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/kit/v2d_submission_kit')
from v2dlb.submission_parquet import read_trajectory
from scipy.spatial.transform import Rotation as R
tr = np.load(sys.argv[1]); L = [str(x) for x in tr['labels']]; q = tr['q']
TO = {l.split('/')[0][len('track3_'):]: q[:, i] for i, l in enumerate(L) if l.endswith('/object')}
def summ(P):
    disp = 1000 * np.linalg.norm(P[:, :3] - P[0, :3], axis=1); turn = np.degrees((R.from_quat(P[:, 3:]) * R.from_quat(P[0, 3:]).inv()).magnitude())
    m = (disp > 5) | (turn > 3); lift = 100 * (P[:, 2] - P[0, 2])
    return (int(np.argmax(m)) if m.any() else None), round(float(lift.max()), 1), (int(np.argmax(lift > 2)) if (lift > 2).any() else None)
for name, P in TO.items():
    print(f'trace {name:14s} leaves rest / max lift cm / first lift>2cm: {summ(P)}')
for path in sys.argv[2:]:
    t = read_trajectory(path); d = os.path.dirname(path); auc = None
    for f in os.listdir(d):
        if f.startswith('score_registered'):
            j = json.load(open(os.path.join(d, f))); s_ = j.get('sim', j); auc = (s_.get('AUC'), s_.get('per_obj_AUC'))
    print('==', path.split('runs/')[-1], 'registered', auc)
    for slot in np.unique(t.object_slot):
        k = t.object_slot == slot; fr = t.frame_index[k]; o = np.argsort(fr); P = t.pose_xyzw[k][o]; name = t.object_name[k][0]
        n = min(len(P), len(TO[name])); e = 100 * np.linalg.norm(P[:n, :3] - TO[name][:n, :3], axis=1)
        print(f'  {name:14s} {summ(P)}  |rollout-trace| mean {e.mean():.1f} cm, p90 {np.percentile(e, 90):.1f} cm')
