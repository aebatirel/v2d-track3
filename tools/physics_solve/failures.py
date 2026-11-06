"""Failure finder for the solver<->RL loop (2026-10-31, docs/research/physics-2026-10-30/physics-solver.md section 6.1).

Reads a rollout trace (tools/trace_rollout.py npz: the trained policy played like the official evaluator, `policy` mode,
or a zero-action replay) and OUR reference parquet (perceived object poses; no ground truth). Per object and frame it
computes the kit's ADD distance (500 points on a 5 cm sphere, as pipeline/qa.py). A FAILURE of an object is the first
frame from which its ADD stays above --thr (default 3 cm, the AUC's 3 cm level) for at least --hold frames (default 8,
0.4 s), at a frame where the reference moves the object or a hand is near it (a static object that is never touched and
drifts by < thr is ignored by construction). A failure becomes a SOLVER WINDOW
  start = onset - --back (default 10 frames, 0.5 s: the policy's own state before it went wrong, read from the trace's
          STATE=1 record), end = min(T - 1, onset + --span) (default 60 frames, 3 s);
windows of different objects that overlap are merged (earliest start, latest end). Windows are ranked by onset (the
earliest failure first: later frames follow from it) and at most --max windows are returned.
Output JSON: per object (onset, ADD at onset, frames within thr, recovered?), the trace's per-object share of frames
within 3 cm, and the windows [{start, end, onset, objects}]. `--min_start` keeps windows after a frame (e.g. after
the previous round's windows); `--exclude` drops windows that start inside given [a,b] ranges.
Usage: failures.py REF.parquet TRACE.npz OUT.json [--thr 0.03 --hold 8 --back 10 --span 60 --max 2]
"""
import argparse, json, os, sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import solve as S  # noqa: E402


def main():
    p = argparse.ArgumentParser(); p.add_argument('ref'); p.add_argument('trace'); p.add_argument('out')
    p.add_argument('--thr', type=float, default=0.03); p.add_argument('--hold', type=int, default=8)
    p.add_argument('--back', type=int, default=10); p.add_argument('--span', type=int, default=60)
    p.add_argument('--max', type=int, default=2); p.add_argument('--min_start', type=int, default=1)
    a = p.parse_args()
    ref = S.Ref(a.ref); T, B = ref.T, len(ref.names)
    d = np.load(a.trace); L = [str(x) for x in d['labels']]; fr = [int(x) for x in d['frame']]
    n = next((i for i in range(1, len(fr)) if fr[i] <= fr[i - 1]), len(fr))     # one episode (the viewer resets at the end)
    rows = {fr[i]: i for i in range(n)}
    ob = [next(i for i, l in enumerate(L) if l.startswith(f'track3_{nm}/')) for nm in ref.names]
    pts = S.sphere_points(500)
    frames = [f for f in range(T) if f in rows]
    add = np.full((T, B), np.nan)
    for f in frames:
        add[f] = S.add_dist(d['q'][rows[f]][ob].astype(np.float64), ref.OP[f], ref.OQ[f], pts)
    travel = np.linalg.norm(ref.OP - ref.OP[:1], axis=-1)                         # (T, B) reference displacement
    near = np.zeros((T, B), bool)
    for s in ('right', 'left'):
        dist = np.linalg.norm(ref.frames[s][:, :, None] - ref.OP[:, None], axis=-1).min(1) - ref.radius[None]
        near |= dist < 0.10
    active = (travel > 0.02) | near                                               # the reference manipulates it
    objs, cands = {}, []
    for j, nm in enumerate(ref.names):
        above = np.nan_to_num(add[:, j], nan=0.0) > a.thr
        onset = None
        for f in range(T - a.hold + 1):
            if above[f] and above[f:f + a.hold].all() and active[max(0, f - a.back):f + 1, j].any():
                onset = f; break
        rec = onset is not None and not above[onset:].all() and bool((~above[onset + a.hold:]).any())
        objs[nm] = dict(onset=onset, add_cm_at_onset=None if onset is None else round(100 * float(add[onset, j]), 1),
                        within_3cm=round(float(np.mean(np.nan_to_num(add[frames, j], nan=1.0) < 0.03)), 3),
                        recovered_later=bool(rec))
        if onset is not None:
            st = max(a.min_start, onset - a.back)
            if st in rows:
                cands.append(dict(start=st, end=min(T - 1, onset + a.span), onset=onset, objects=[nm]))
    cands.sort(key=lambda w: w['onset']); wins = []
    for w in cands:                                                               # merge overlapping windows
        if wins and w['start'] <= wins[-1]['end']:
            wins[-1]['end'] = max(wins[-1]['end'], w['end']); wins[-1]['objects'] += w['objects']
        else:
            wins.append(w)
    out = dict(ref=os.path.abspath(a.ref), trace=os.path.abspath(a.trace), frames=len(frames), args=vars(a), objects=objs,
               windows=wins[:a.max], dropped_windows=wins[a.max:])
    json.dump(out, open(a.out, 'w'), indent=1)
    print(json.dumps(dict(objects=objs, windows=out['windows'])))


if __name__ == '__main__':
    main()
