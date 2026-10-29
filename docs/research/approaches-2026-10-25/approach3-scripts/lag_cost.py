"""What does waiting for an event cost under the time-indexed score? (GT-free: our reference against itself.)
For each object, the reference track is delayed by K frames from an event frame E (pose(t) = ref(max(E, t - K)) for
t >= E) - the robot "waits K frames to confirm" the event before it continues - and scored against the undelayed
reference with the kit's ADD-AUC definition re-implemented here (thresholds 1..9 cm step 1 cm, trapezoid on [0, 1],
500 points on a 5 cm sphere as pipeline/qa.py; per object, mean over objects). Events: liftoff (the lift waits for a
secure grasp), onset (the first motion waits for closure) and settle (the release waits for touchdown: the object is
at rest, so a late release does not move it; reported as a check). Only the delayed object is changed; the episode
AUC loss is reported (1 - AUC, other objects perfect). Two delay models: 'persist' (the object stays K frames late for
the rest of the episode, an upper bound) and 'catchup' (it waits K frames, then catches up at 1.5x over 2K frames).
Usage: python -I lag_cost.py OUT.json TAG=REF.parquet ...
"""
import json, os, sys
import numpy as np
from scipy.spatial.transform import Rotation as Rot, Slerp
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_ref  # noqa: E402
from events import object_events  # noqa: E402

TH = np.arange(0.01, 0.10, 0.01)
rng = np.random.default_rng(0); PTS = rng.normal(size=(500, 3)); PTS = 0.05 * PTS / np.linalg.norm(PTS, axis=1, keepdims=True)


def auc_obj(Pa, Ra, Pr, Rr):
    A = np.stack([Ra[t].apply(PTS) + Pa[t] for t in range(len(Pa))]); B = np.stack([Rr[t].apply(PTS) + Pr[t] for t in range(len(Pr))])
    add = np.linalg.norm(A - B, axis=2).mean(1)
    return float(np.trapezoid([np.mean(add < t) for t in TH], x=np.linspace(0, 1, TH.size)))


def main(out, specs):
    res = []
    for sp in specs:
        tag, path = sp.split('=', 1); d = load_ref(path); B = len(d['names'])
        for j, n in enumerate(d['names']):
            P, R = d['OP'][:, j], d['OR'][j]; ev = object_events(P, R); T = len(P)
            row = dict(tag=tag, object=n, events=ev)
            for name in ('onset', 'liftoff', 'settle'):
                E = ev[name]
                if E is None:
                    continue
                for K in (1, 2, 3, 5):
                    for mode, C in (('persist', None), ('catchup', 2 * K)):
                        u = np.array([float(t) if t < E else (float(max(E, t - K)) if C is None else
                                      float(E) if t < E + K else min(float(t), E + (t - E - K) * (K + C) / C)) for t in range(T)])
                        i0 = np.floor(u).astype(int); i1 = np.minimum(i0 + 1, T - 1); w = (u - i0)[:, None]
                        Pa = (1 - w) * P[i0] + w * P[i1]
                        Ra = Rot.from_quat([Slerp([0, 1], Rot.from_quat([R[a_].as_quat(), R[b_].as_quat()]))([float(w_[0])]).as_quat()[0]
                                            for a_, b_, w_ in zip(i0, i1, w)])
                        a = auc_obj(Pa, Ra, P, R)
                        row[f'{name}_K{K}_{mode}_episode_loss'] = round((1 - a) / B, 4)
            res.append(row); print(json.dumps(row), flush=True)
    json.dump(res, open(out, 'w'), indent=1)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2:])
