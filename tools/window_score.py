"""Hold-window sim_vs_ref of recorded rollouts (2026-10-25, pre-registered test T2 in docs/work-log.md): the kit's ADD
AUC (pipeline/qa.py's metric: kit functions, 500 points on a 5 cm sphere, warped to the reference start over the whole
episode), restricted per object to the union of its hold windows [hold_from - PRE, end + POST] taken from ONE grasp-lock
report, so every arm is scored on the same frames; the mean over the objects that have a window. The full-episode
sim_vs_ref is printed too. Our reference only (no ground truth).
Usage: window_score.py REF.parquet GRASP_LOCK.json TRACE.npz[:label] ... [--pre 6] [--post 20]   (KIT env as qa.py)"""
import argparse, json, os, sys
import numpy as np, pyarrow.parquet as pq
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/../pipeline')
import qa  # noqa: E402
sys.path.insert(0, qa.KIT); sys.path.insert(0, f'{qa.KIT}/metric_code/track_3')
import importlib  # noqa: E402
A = importlib.import_module('AUC')
p = argparse.ArgumentParser(); p.add_argument('ref'); p.add_argument('gl'); p.add_argument('traces', nargs='+')
p.add_argument('--pre', type=int, default=6); p.add_argument('--post', type=int, default=20); a = p.parse_args()
t = pq.read_table(a.ref); names = t.column('object_body_names')[0].as_py(); B = len(names)
T = len(np.array(t.column('robot_left_wrist_position')[0].as_py(), float).reshape(-1, 3))
OP = np.array(t.column('object_body_position')[0].as_py(), float).reshape(T, B, 3)
OQ = np.array(t.column('object_body_wxyz')[0].as_py(), float).reshape(T, B, 4)[..., [1, 2, 3, 0]]
ref = np.concatenate([OP, OQ], 2)
rng = np.random.default_rng(0); pts = rng.normal(size=(500, 3)); pts = 0.05 * pts / np.linalg.norm(pts, axis=1, keepdims=True); V = np.repeat(pts[None], B, 0)
win = np.zeros((T, B), bool)
for x in json.load(open(a.gl))['phases']:
    j = names.index(x['object']); win[max(0, int(x['hold_from']) - a.pre):min(T, int(x['end']) + a.post + 1), j] = True
objs = [j for j in range(B) if win[:, j].any()]
print('windows', {names[j]: [int(np.nonzero(win[:, j])[0][0]), int(np.nonzero(win[:, j])[0][-1]), int(win[:, j].sum())] for j in objs})
for spec in a.traces:
    path, _, lab = spec.partition(':'); d = np.load(path); L = [str(x) for x in d['labels']]; q = d['q'][:T].astype(float)
    ids = [next(i for i, l in enumerate(L) if l.startswith(f'track3_{n}/')) for n in names]
    n = min(len(q), T); sim = q[:n, ids, :7][:, None]; r = ref[:n, None]
    add = A._object_add(A._warp_to_reference_start(sim, r), r, V)                     # (n, 1, B)
    full = float(A._add_auc(add))
    per = {names[j]: float(A._add_auc(add[win[:n, j]][:, :, [j]])) for j in objs}
    print(json.dumps(dict(trace=lab or path, window_sim_vs_ref=round(float(np.mean(list(per.values()))), 4),
                          per_object={k: round(v, 4) for k, v in per.items()}, full_sim_vs_ref=round(full, 4))))
