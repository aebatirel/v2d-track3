"""Where do official draws of one checkpoint part ways? (Prof. Inceoglu's good-vs-failed draw comparison, 31 Oct 2026.)
Reads per-draw evaluator rollouts (flash_chord_object_trajectories_v1 parquets) of one checkpoint and compares them
against our own reference (stored in the same parquet) and against each other. No ground truth is read.
ADD yardstick as pipeline/qa.py: 500 points on a 5 cm-radius sphere per object.
Usage: drawdiv.py DATA_ROOT ARM EP [ARM EP ...]  (DATA_ROOT/ARM/epN/r1..r10/episode_0000NN.parquet + qa_policy.json)
"""
import glob, json, os, sys
import numpy as np
import pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as R

rng = np.random.default_rng(0); P = rng.normal(size=(500, 3)); P = 0.05 * P / np.linalg.norm(P, axis=1, keepdims=True)


def load(f):
    t = pq.read_table(f).to_pydict()
    steps, oid = np.array(t['step']), np.array(t['object_id'])
    T, B = steps.max() + 1, oid.max() + 1
    names = [None] * B
    A = np.zeros((T, B, 7)); F = np.zeros((T, B, 7))
    for k in range(len(steps)):
        s, o = steps[k], oid[k]; names[o] = t['object_body_name'][k]
        A[s, o] = [t[f'achieved_position_{c}'][k] for c in 'xyz'] + [t[f'achieved_quaternion_{c}'][k] for c in 'xyzw']
        F[s, o] = [t[f'reference_position_{c}'][k] for c in 'xyz'] + [t[f'reference_quaternion_{c}'][k] for c in 'xyzw']
    return A, F, names


def add(X, Y):  # (T, B, 7) x2 -> (T, B) mean point distance, m
    T, B, _ = X.shape; out = np.zeros((T, B))
    for b in range(B):
        rx, ry = R.from_quat(X[:, b, 3:]), R.from_quat(Y[:, b, 3:])
        for t in range(T):
            out[t, b] = np.linalg.norm((rx[t].apply(P) + X[t, b, :3]) - (ry[t].apply(P) + Y[t, b, :3]), axis=1).mean()
    return out


def onset(e, thr=0.03, run=8):  # first frame an object stays > thr for >= run frames (as physics_solve/failures.py)
    T, B = e.shape; res = []
    for b in range(B):
        bad = e[:, b] > thr; f = None
        for t in range(T - run + 1):
            if bad[t:t + run].all(): f = t; break
        res.append(f)
    return res


def first_above(d, thr):
    i = np.flatnonzero(d > thr); return int(i[0]) if len(i) else None


root = sys.argv[1]; out = {}
for arm, ep in zip(sys.argv[2::2], sys.argv[3::2]):
    ds = sorted(glob.glob(f'{root}/{arm}/ep{ep}/r*'), key=lambda p: int(p.rsplit('r', 1)[1]))
    draws = []
    for d in ds:
        A, F, names = load(f'{d}/episode_0000{int(ep):02d}.parquet')
        q = json.load(open(f'{d}/qa_policy.json'))
        draws.append(dict(name=os.path.basename(d), A=A, F=F, svr=q['sim_vs_ref'], e=add(A, F)))
    F0 = draws[0]['F']; same_ref = all(np.allclose(x['F'], F0, atol=1e-6) for x in draws)
    svr = np.array([x['svr'] for x in draws]); order = np.argsort(svr)
    worst, best = draws[order[0]], draws[order[-1]]
    # where every pair of draws first differs (numerical), and first parts by 5 mm / 2 cm (any object)
    pair = {}
    for thr in (1e-5, 0.005, 0.02):
        fs = []
        for i in range(len(draws)):
            for j in range(i + 1, len(draws)):
                d = add(draws[i]['A'], draws[j]['A']).max(1); fs.append(first_above(d, thr))
        fs = [f for f in fs if f is not None]
        pair[f'{thr}'] = dict(n_pairs_split=len(fs), of=len(draws) * (len(draws) - 1) // 2,
                              min=min(fs) if fs else None, median=float(np.median(fs)) if fs else None,
                              max=max(fs) if fs else None)
    bw = add(best['A'], worst['A'])
    rec = dict(arm=arm, ep=int(ep), objects=names, frames=int(F0.shape[0]), same_reference=bool(same_ref),
               sim_vs_ref=dict(mean=round(float(svr.mean()), 4), sd=round(float(svr.std(ddof=1)), 4),
                               min=float(svr.min()), max=float(svr.max()), values=[float(v) for v in svr]),
               pairwise_first_split=pair,
               best_vs_worst=dict(best=best['name'], best_svr=best['svr'], worst=worst['name'], worst_svr=worst['svr'],
                                  first_diff_10um=first_above(bw.max(1), 1e-5), split_5mm=first_above(bw.max(1), 0.005),
                                  split_2cm=first_above(bw.max(1), 0.02),
                                  split_2cm_per_object={n: first_above(bw[:, b], 0.02) for b, n in enumerate(names)}),
               failure_onset_3cm_8f={x['name']: dict(zip(names, onset(x['e']))) for x in draws},
               mean_err_cm_by_object={x['name']: {n: round(float(x['e'][:, b].mean() * 100), 2) for b, n in enumerate(names)}
                                      for x in draws})
    # error-vs-reference curve of best and worst, every 10 frames (cm, max over objects)
    rec['best_worst_err_cm_every10'] = dict(frame=list(range(0, F0.shape[0], 10)),
                                            best=[round(float(best['e'][t].max() * 100), 1) for t in range(0, F0.shape[0], 10)],
                                            worst=[round(float(worst['e'][t].max() * 100), 1) for t in range(0, F0.shape[0], 10)])
    out[f'{arm}/ep{ep}'] = rec
print(json.dumps(out, indent=1))
