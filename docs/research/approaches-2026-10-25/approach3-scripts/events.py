"""Action-phase events per object (Johansson & Flanagan-style contact events), GT-free, plus a labelled diagnostic.

From OUR reference (inference side, no ground truth):
  onset     first frame the object leaves its frame-0 pose by > 1 cm or 8 deg (grasp_lock --onset_anchor rule)
  liftoff   first frame its origin is > 1.5 cm above its frame-0 height for 3 consecutive frames (z = table normal)
  settle    after liftoff, first frame of >= 5 frames with speed < 0.5 cm/frame and turn < 2 deg/frame (placed)
  hold_on / hold_off   first start / last end of the contact-label holds on that object (pipeline/hold_phases.py)
DIAGNOSTIC ONLY (--gt EPISODE.parquet, public episodes): the same three object events from the mocap poses
(observation.objects pose, world z up), printed next to ours as frame differences. Mocap is never an input to
anything else; the comparison only measures how sharp each GT-free event is.
Usage: python -I events.py REF.parquet [--gt EPISODE.parquet] [--json OUT]
"""
import argparse, json, os, sys
import numpy as np
from scipy.spatial.transform import Rotation as Rot
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_ref, hold_list  # noqa: E402


def object_events(P, R):
    """P (T,3) positions, R Rotation (T): onset, liftoff, settle frames (or None)."""
    T = len(P)
    d = np.linalg.norm(P - P[0], axis=1) * 100; a = np.degrees((R * R[0].inv()).magnitude())
    mv = np.nonzero((d > 1.0) | (a > 8.0))[0]; onset = int(mv[0]) if len(mv) else None
    up = (P[:, 2] - P[0, 2]) * 100 > 1.5
    lift = next((t for t in range(T - 2) if up[t:t + 3].all()), None)
    settle = None
    if lift is not None:
        v = np.r_[0, np.linalg.norm(np.diff(P, axis=0), axis=1) * 100]
        w = np.r_[0, np.degrees((R[1:] * R[:-1].inv()).magnitude())]
        still = (v < 0.5) & (w < 2.0)
        zr = (P[:, 2] - P[0, 2]) * 100
        # placed: first still run of >= 5 frames after the object came down >= 1 cm from its peak since liftoff
        for t in range(lift + 3, T - 4):
            if still[t:t + 5].all() and zr[t] < zr[lift:t + 1].max() - 1.0:
                settle = t; break
    return dict(onset=onset, liftoff=lift, settle=settle)


def gt_tracks(path, names):
    import pyarrow.parquet as pq
    t = pq.read_table(path).to_pylist(); out = {}
    for n in names:
        X = np.array([[o['pose'] for o in r['observation.objects'] if o['name'] == n][0] for r in t], float)
        out[n] = (X[:, :3], Rot.from_quat(X[:, [4, 5, 6, 3]]))   # [x y z qw qx qy qz] -> xyzw
    return out


def main():
    p = argparse.ArgumentParser(); p.add_argument('ref'); p.add_argument('--gt'); p.add_argument('--json'); a = p.parse_args()
    d = load_ref(a.ref); ph = hold_list(a.ref); res = {}
    G = gt_tracks(a.gt, d['names']) if a.gt else {}
    for j, n in enumerate(d['names']):
        e = object_events(d['OP'][:, j], d['OR'][j])
        hs = [x for x in ph if x['object'] == n]
        e['hold_on'] = min((x['start'] for x in hs), default=None); e['hold_off'] = max((x['end'] for x in hs), default=None)
        e['holds'] = [(x['hand'], x['start'], x['end']) for x in hs]
        if n in G:
            g = object_events(*G[n]); e['GT_DIAG'] = g
            e['diff_ref_minus_gt'] = {k: (None if e[k] is None or g[k] is None else e[k] - g[k]) for k in g}
            e['hold_on_minus_gt_onset'] = None if e['hold_on'] is None or g['onset'] is None else e['hold_on'] - g['onset']
            e['hold_on_minus_gt_liftoff'] = None if e['hold_on'] is None or g['liftoff'] is None else e['hold_on'] - g['liftoff']
            e['hold_off_minus_gt_settle'] = None if e['hold_off'] is None or g['settle'] is None else e['hold_off'] - g['settle']
        res[n] = e
        print(n, json.dumps(e))
    if a.json:
        json.dump(res, open(a.json, 'w'), indent=1)


if __name__ == '__main__':
    main()
