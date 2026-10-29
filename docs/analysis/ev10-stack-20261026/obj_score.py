import os, sys, importlib, numpy as np, pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as R
sys.path.insert(0, 'pipeline'); import qa
sys.path.insert(0, qa.KIT); sys.path.insert(0, f'{qa.KIT}/metric_code/track_3'); AU = importlib.import_module('AUC')
t = pq.read_table(sys.argv[1]); names = t.column('object_body_names')[0].as_py(); B = len(names)
T = len(np.array(t.column('robot_left_wrist_position')[0].as_py(), float).reshape(-1, 3))
OP = np.array(t.column('object_body_position')[0].as_py(), float).reshape(T, B, 3); OQ = np.array(t.column('object_body_wxyz')[0].as_py(), float).reshape(T, B, 4)[..., [1, 2, 3, 0]]
ref = np.concatenate([OP, OQ], 2); rng = np.random.default_rng(0); pts = rng.normal(size=(500, 3)); pts = 0.05 * pts / np.linalg.norm(pts, axis=1, keepdims=True)
for spec in sys.argv[2:]:
    path, _, lab = spec.partition(':'); d = np.load(path); L = [str(x) for x in d['labels']]; q = d['q'][:T].astype(float)
    out = []
    for j, n in enumerate(names):
        i = next(k for k, l in enumerate(L) if l.startswith(f'track3_{n}/')); s = q[:, i, :7]
        a_, r_ = s[:, None][:, None], ref[:, j:j+1][:, None]; a_ = AU._warp_to_reference_start(a_, r_); sc = float(AU._add_auc(AU._object_add(a_, r_, pts[None])))
        rot = np.degrees((R.from_quat(s[:, 3:7]) * R.from_quat(ref[:, j, 3:7]).inv()).magnitude())
        pe = np.linalg.norm(s[:, :3] - ref[:, j, :3], axis=1) * 100
        out.append(f'{n}: auc {sc:.3f}, pos mean {pe.mean():.1f} cm, rot mean {rot.mean():.0f} deg (f100-160 {rot[100:].mean():.0f} deg)')
    print(f'{lab}: ' + ' | '.join(out))
