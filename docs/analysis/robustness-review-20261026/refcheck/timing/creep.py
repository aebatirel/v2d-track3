"""refcheck/timing: motion in OUR object paths while the true (mocap) object rests (diagnostic; reads mocap).

Per canonical episode and object, for perc / ref (or stale): the largest displacement (cm, kit anchor) and rotation
(deg; swing of the axis for cups) of ours from its own start rest pose (median of the first 5 frames) over the frames
BEFORE the true physical onset, and from its own end rest pose (median of the last 5 frames) AFTER the true physical
offset; for static objects (mocap never moves 1 cm / 10 deg) over the whole episode. The same for mocap. Also the
first frame where ours leaves its start rest by > 1 cm, for spurious early motion.
Usage: python -I creep.py TIMING.json OUT.json
"""
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from tload import *                                                        # noqa: E402,F401,F403
import timing as TM                                                        # noqa: E402


def main():
    TJ = json.load(open(sys.argv[1])); out = {}
    for ep, e in sorted(canon().items()):
        R = TJ[str(ep)]; names, gt = load_gt(ep); T = len(gt[names[0]])
        src = {k: v for k, v in sources(ep, e, with_sim=False).items() if k in ('perc', 'ref', 'stale')}
        for s, n in enumerate(names):
            m = R['obj'][n]['mocap']; static = R['obj'][n]['static']
            on, off = (0, T - 1) if static else (m['on_phys'], m['off_phys'])
            row = dict(static=static, true_on=None if static else on, true_off=None if static else off)
            tracks = {'mocap': TM.Track(gt[n], host_anchor(n, s), TM.sym_axis_body(ep, s, n, 'mocap'))}
            for k, v in src.items():
                tracks[k] = TM.Track(v['poses'][n], v['anchor'][s], TM.sym_axis_body(ep, s, n, v['lib']))
            for k, tr in tracks.items():
                p0, r0 = tr.rest(np.arange(5)); pL, rL = tr.rest(np.arange(T - 5, T))
                d0 = np.linalg.norm(tr.P - p0, axis=1) * 100; a0 = tr.ang_to(r0)
                dL = np.linalg.norm(tr.P - pL, axis=1) * 100; aL = tr.ang_to(rL)
                x = {}
                if static:
                    x['whole_max_cm'] = round(float(d0.max()), 2); x['whole_max_deg'] = round(float(a0.max()), 1)
                    big = np.nonzero(d0 > 1.0)[0]
                    x['first_over_1cm'] = int(big[0]) if len(big) else None
                    x['frames_over_1cm'] = int((d0 > 1.0).sum())
                else:
                    pre = slice(0, max(1, on)); post = slice(min(T - 1, off + 1), T)
                    x['pre_onset_max_cm'] = round(float(d0[pre].max()), 2); x['pre_onset_max_deg'] = round(float(a0[pre].max()), 1)
                    x['pre_onset_frames_over_1cm'] = int((d0[pre] > 1.0).sum())
                    big = np.nonzero(d0[pre] > 1.0)[0]; x['pre_onset_first_over_1cm'] = int(big[0]) if len(big) else None
                    x['post_offset_max_cm'] = round(float(dL[post].max()), 2) if off + 1 < T else None
                    x['post_offset_max_deg'] = round(float(aL[post].max()), 1) if off + 1 < T else None
                    x['post_offset_frames_over_1cm'] = int((dL[post] > 1.0).sum()) if off + 1 < T else 0
                row[k] = x
            out[f'{ep}/{n}'] = row
            print(ep, n, row, flush=True)
    json.dump(out, open(sys.argv[2], 'w'), indent=1)


if __name__ == '__main__':
    main()
