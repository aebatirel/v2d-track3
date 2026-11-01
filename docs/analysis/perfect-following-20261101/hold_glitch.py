"""GT-free scan for perception glitches inside holds (1 Nov 2026): for every hold phase of a reference (pipeline/hold_phases.py),
the object pose in the holding hand's robot-wrist frame (the reference's robot_<side>_wrist track, which follows the human
hand). A held object should be near-rigid in that frame; frames where it moves faster than V_REL (cm/s) or turns faster than
W_REL (deg/s) relative to the hand are flagged, with the windows. Usage: hold_glitch.py STORE OUT_JSON"""
import json, os, sys
import numpy as np, pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as Rot
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.abspath(f'{HERE}/../../..'); sys.path.insert(0, f'{REPO}/pipeline')
from hold_phases import hold_phases
V_REL, W_REL = 40.0, 250.0
ST, OUT = sys.argv[1:3]
P = json.load(open(f'{REPO}/docs/analysis/perfect-following-20261101/preflight.json'))
res = {}
for ep, e in P.items():
    path = f"{ST}/{e['sf_path'] or e['ref_path']}"; t = pq.read_table(path); c = lambda k: t.column(k)[0].as_py()
    names = c('object_body_names'); fps = float(c('fps')); T = len(np.array(c('robot_left_wrist_position')).reshape(-1, 3))
    OP = np.array(c('object_body_position')).reshape(T, len(names), 3); OQ = np.array(c('object_body_wxyz')).reshape(T, len(names), 4)[..., [1, 2, 3, 0]]
    out = []
    for p in hold_phases(path)[0]['phases']:
        s, j = p['hand'], names.index(p['object']); a, b = p['start'], min(p['end'], T)
        W = np.array(c(f'robot_{s}_wrist_position')).reshape(T, 3); WQ = np.array(c(f'robot_{s}_wrist_wxyz')).reshape(T, 4)[:, [1, 2, 3, 0]]
        rw = Rot.from_quat(WQ[a:b]); rel_p = rw.inv().apply(OP[a:b, j] - W[a:b]); rel_r = rw.inv() * Rot.from_quat(OQ[a:b, j])
        v = np.linalg.norm(np.diff(rel_p, axis=0), axis=1) * fps * 100; w = np.degrees((rel_r[1:] * rel_r[:-1].inv()).magnitude()) * fps
        bad = (v > V_REL) | (w > W_REL); fr = (np.nonzero(bad)[0] + a + 1).tolist()
        out.append(dict(hand=s, object=p['object'], start=a, end=b, v_rel_p95=round(float(np.percentile(v, 95)), 1), v_rel_max=round(float(v.max()), 1),
                        w_rel_p95=round(float(np.percentile(w, 95)), 1), w_rel_max=round(float(w.max()), 1), flagged=len(fr), frames=fr[:40],
                        rel_spread_cm=round(float(np.linalg.norm(rel_p - np.median(rel_p, 0), axis=1).max() * 100), 1)))
    res[ep] = out
    print(ep, [(o['hand'][0], o['object'][:8], o['start'], o['end'], o['v_rel_max'], o['w_rel_max'], o['flagged'], o['rel_spread_cm']) for o in out])
json.dump(res, open(OUT, 'w'), indent=1)
