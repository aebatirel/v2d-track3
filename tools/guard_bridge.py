"""Repair the perception jumps at TRACK_GUARD re-acquisitions (2026-11-01, perfect-following lane). GT-free.

Evidence (docs/analysis/perfect-following-20261101/README.md, [M]): perc2's TRACK_GUARD re-detects an object when its
tracked pose falls below the table and restarts the track from the re-acquired pose. On evals 14 (blue cup f46), 32 (f21,
f34) and 33 (f91) the reference then holds a one-frame teleport of 11-20 cm (eval 32: also a 150-degree flip of the cup's
axis) that no robot can follow; every H5p7 draw's error takes off there. Before the eval-14 / eval-32 re-acquisitions the
tracked cup drifts out of the perceived human hand (eval 14 f38-44: 8-16 cm from every fingertip; 0.3-1.6 cm right after).

Rule (fixed before any GPU result), per object with re-acquisition events:
  1. d(k) = distance of the object's surface (posed by the reference) to the nearest perceived fingertip of either hand
     (MANO joints 4, 8, 12, 16, 20), per frame;
  2. events of one object less than PAIR frames apart bound a segment the guard re-acquired twice: the span is the frames
     between them (r1 .. r2-1);
  3. otherwise the span is the run of frames just before the event (r-1, r-2, ...) with d > DRIFT_CM (the drift out of the
     hand), at most MAX_BACK frames; if d at r itself is >= DRIFT_CM, the event is not hand-consistent: nothing is rewritten;
  4. a span [s, e] is replaced by interpolation between the boundary frames s-1 and e+1 (linear position, slerp rotation);
  5. any jump left at an event (position > JUMP_CM or rotation > JUMP_DEG between consecutive frames) is spread over a ramp
     of RAMP frames ending at the event (the pre-event frames move toward the re-acquired pose).
Only object_body_position / object_body_wxyz and the root columns (= object 0, as contact_retarget.py writes them) change.
Usage: guard_bridge.py IN.parquet OUT.parquet --events blue_cup:46[,obj:frame ...] --mesh_dir meshes/library_v3 [--json J]
"""
import argparse, json, os
import numpy as np, pyarrow as pa, pyarrow.parquet as pq, trimesh
from scipy.spatial.transform import Rotation as Rot, Slerp

DRIFT_CM, PAIR, MAX_BACK, JUMP_CM, JUMP_DEG, RAMP = 3.0, 20, 30, 4.0, 30.0, 6
TIPS = [4, 8, 12, 16, 20]


def interp(P, Q, a, b, ks):
    """poses at frames ks between boundary frames a and b (P: positions, Q: Rotation per frame)."""
    s = Slerp([a, b], Rot.concatenate([Q[a], Q[b]]))
    w = (np.array(ks, float) - a) / (b - a)
    return P[a] + w[:, None] * (P[b] - P[a]), s(np.array(ks, float))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('inp'); ap.add_argument('out'); ap.add_argument('--events', required=True)
    ap.add_argument('--mesh_dir', required=True); ap.add_argument('--json', default=None)
    a = ap.parse_args()
    t = pq.read_table(a.inp); c = lambda k: t.column(k)[0].as_py()
    names = c('object_body_names'); B = len(names); T = len(np.array(c('robot_left_wrist_position')).reshape(-1, 3))
    OP = np.array(c('object_body_position'), float).reshape(T, B, 3)
    OQ = np.array(c('object_body_wxyz'), float).reshape(T, B, 4)
    J = {s: np.array(c(f'mano_{s}_joints'), float).reshape(T, 21, 3) for s in ('left', 'right')}
    evs = {}
    for x in a.events.split(','):
        if x: o, f = x.split(':'); evs.setdefault(o, []).append(int(f))
    report = []; changed = {}
    for o, fr in evs.items():
        j = names.index(o); fr = sorted(fr)
        pqm = trimesh.proximity.ProximityQuery(trimesh.load(os.path.join(a.mesh_dir, f'{o}.glb'), force='mesh'))
        P = OP[:, j].copy(); R = Rot.from_quat(OQ[:, j][:, [1, 2, 3, 0]])
        d = np.array([min(float(np.abs(pqm.signed_distance(R[k].inv().apply(J[s][k][TIPS] - P[k]))).min()) for s in J) * 100
                      for k in range(T)])
        spans = []; i = 0
        while i < len(fr):
            r = fr[i]
            if i + 1 < len(fr) and fr[i + 1] - r < PAIR:
                spans.append(dict(events=[r, fr[i + 1]], span=[r, fr[i + 1] - 1], why=f'two re-acquisitions {fr[i + 1] - r} frames apart'))
                i += 2; continue
            if d[r] >= DRIFT_CM:
                spans.append(dict(events=[r], span=None, why=f'not hand-consistent at the re-acquisition (d {d[r]:.1f} cm)')); i += 1; continue
            k = r - 1
            while k >= max(0, r - MAX_BACK) and d[k] > DRIFT_CM: k -= 1
            spans.append(dict(events=[r], span=[k + 1, r - 1] if k + 1 <= r - 1 else None, why='drift out of the hand before the re-acquisition'))
            i += 1
        for sp in spans:
            if sp['span']:
                s0, e0 = sp['span']; ks = list(range(s0, e0 + 1))
                if s0 - 1 < 0 or e0 + 1 >= T: sp['why'] += ' (no boundary frame: skipped)'; sp['span'] = None; continue
                newP, newR = interp(P, R, s0 - 1, e0 + 1, ks)
                sp['max_shift_cm'] = round(float(np.linalg.norm(newP - P[ks], axis=1).max() * 100), 1)
                P[ks] = newP; q = R.as_quat(); q[ks] = newR.as_quat(); R = Rot.from_quat(q)
            r = sp['events'][-1]                                       # ramp a remaining jump into the (last) event
            dp = float(np.linalg.norm(P[r] - P[r - 1]) * 100); dr = float(np.degrees((R[r] * R[r - 1].inv()).magnitude()))
            sp['jump_after_bridge'] = [round(dp, 1), round(dr, 1)]
            if dp > JUMP_CM or dr > JUMP_DEG:
                a0 = max(0, r - RAMP); ks = list(range(a0 + 1, r))
                newP, newR = interp(P, R, a0, r, ks)
                sp['ramp'] = [a0 + 1, r - 1]; P[ks] = newP; q = R.as_quat(); q[ks] = newR.as_quat(); R = Rot.from_quat(q)
            sp['d_cm_around'] = {int(k): round(float(d[k]), 1) for k in range(max(0, sp['events'][0] - 12), min(T, sp['events'][-1] + 4))}
        dpos = np.linalg.norm(P - OP[:, j], axis=1) * 100
        changed[o] = dict(frames=int((dpos > 1e-6).sum()), max_cm=round(float(dpos.max()), 1))
        OP[:, j] = P; OQ[:, j] = R.as_quat()[:, [3, 0, 1, 2]]
        report.append(dict(object=o, events=fr, spans=spans))
    out = t
    for col, v in (('object_body_position', OP), ('object_body_wxyz', OQ), ('object_root_position', OP[:, 0]),
                   ('object_root_axis_angle', Rot.from_quat(OQ[:, 0][:, [1, 2, 3, 0]]).as_rotvec())):
        i = out.column_names.index(col); old = np.array(t.column(col)[0].as_py(), float)
        out = out.set_column(i, col, pa.array([v.reshape(old.shape).astype(np.float64).tolist()], type=out.schema.field(col).type))
    pq.write_table(out, a.out)
    res = dict(inp=a.inp, out=a.out, events=a.events, params=dict(DRIFT_CM=DRIFT_CM, PAIR=PAIR, MAX_BACK=MAX_BACK,
               JUMP_CM=JUMP_CM, JUMP_DEG=JUMP_DEG, RAMP=RAMP), changed=changed, report=report)
    if a.json: json.dump(res, open(a.json, 'w'), indent=1)
    print(json.dumps(changed), [(s['events'], s['span'], s.get('ramp'), s.get('max_shift_cm'), s['jump_after_bridge'], s['why'][:50])
                                for r in report for s in r['spans']])


if __name__ == '__main__':
    main()
