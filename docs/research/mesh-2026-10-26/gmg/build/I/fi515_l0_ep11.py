"""PREREG F-I5.15 (5) / INTERLOCK 21.13.6 L0 (P90; report only, decides nothing, for the pose lanes): per ep11 cup,
the 99th-percentile height above our table of its OWNED v6 points (own == 0, exclusive ownership) over the hands-off
static frames of the assembled stretch, and the difference between the two cups.

Heights use the bundle's table plane in the object frame at each frame (Bundle.table_in_obj: height = n . x + d). The
frames are passed in (--frames a-b,c-d: the hands-off static segments that the T-I16 round-2 run of ep11 reports).
GT-free: the v6 bundle only (no scan, mocap, parquet pose or *_align).

  GMG_MODE=dev python docs/research/mesh-2026-10-26/gmg/build/I/fi515_l0_ep11.py --run <run> --bundle <v6>/ep11 \
      --frames 118-136 --out <json>
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MR = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
if MR not in sys.path:
    sys.path.insert(0, MR)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', required=True); ap.add_argument('--bundle', required=True)
    ap.add_argument('--frames', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--src', default='', help='where the frames come from (recorded)')
    a = ap.parse_args()
    import numpy as np
    from gmg import guard
    guard.set_run(a.run)
    from gmg import interlock as IL
    b = IL.load_bundle_any(a.bundle)
    F = []
    for part in a.frames.split(','):
        lo, hi = (int(x) for x in part.split('-'))
        F += list(range(lo, hi + 1))
    out = dict(rule='PREREG F-I5.15 (5), INTERLOCK 21.13.6 L0 (P90; report only)', frames=a.frames, frames_src=a.src,
               objects={})
    for o in b.objects:
        obs = b.obs(o)
        P = np.asarray(obs['pts'], np.float64); fr = np.asarray(obs['frame']); own = np.asarray(obs['own'])
        H, per = [], {}
        for f in sorted(set(F) & set(fr.tolist())):
            pl = b.table_in_obj(o, f)
            if pl is None:
                continue
            m = (fr == f) & (own == 0)
            if not m.any():
                continue
            h = P[m] @ pl[0] + pl[1]
            H.append(h)
            per[int(f)] = dict(n=int(m.sum()), p99_mm=round(float(np.percentile(h, 99)) * 1e3, 2),
                               p1_mm=round(float(np.percentile(h, 1)) * 1e3, 2))
        if not H:
            out['objects'][o] = dict(n=0)
            continue
        H = np.concatenate(H)
        out['objects'][o] = dict(n=int(len(H)), frames_with_points=len(per), p99_mm=round(float(np.percentile(H, 99)) * 1e3, 2),
                                 p50_mm=round(float(np.percentile(H, 50)) * 1e3, 2),
                                 p1_mm=round(float(np.percentile(H, 1)) * 1e3, 2), per_frame=per)
    v = [out['objects'][o].get('p99_mm') for o in b.objects]
    if all(x is not None for x in v):
        d = abs(v[0] - v[1])
        out['rim_difference_mm'] = round(d, 2)
        out['P90'] = 'holds (>= 5 mm: a nest the tracks miss)' if d >= 5.0 else 'falsified (within 5 mm)'
    with open(a.out, 'w') as fh:
        json.dump(out, fh, indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != 'objects'}),
          {o: {k: w for k, w in r.items() if k != 'per_frame'} for o, r in out['objects'].items()})


if __name__ == '__main__':
    main()
