"""refcheck/timing, step 0: speed noise floors, used to choose the motion thresholds (diagnostic; reads mocap).

For every canonical episode and object: speed of the object's kit anchor (cm/s at the video rate 20.254 Hz) and rotation
rate (deg/s), Gaussian-smoothed (sigma 1 frame), in frames where the MOCAP object is at rest (within 2 mm and 1 deg of its
frame-0 or last-frame pose, 5 frames away from any motion). Reports the 50th / 95th / 99th percentiles for mocap,
perception (canonical poses_world_vo.npz) and the final reference.
Usage: python -I noise_floor.py OUT.json
"""
import json, os, sys
import numpy as np
from scipy.spatial.transform import Rotation as Rot

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from tload import *                                                        # noqa: E402,F401


def main():
    out = {}
    for ep, e in sorted(canon().items()):
        names, gt = load_gt(ep)
        srcs = sources(ep, e, with_sim=False)
        for s, n in enumerate(names):
            Pg, Rg = signals(gt[n], host_anchor(n, s))
            T = len(Pg)
            d0 = np.linalg.norm(Pg - Pg[0], axis=1); a0 = np.degrees((Rg * Rg[0].inv()).magnitude())
            dl = np.linalg.norm(Pg - Pg[-1], axis=1); al = np.degrees((Rg * Rg[-1].inv()).magnitude())
            rest = ((d0 < 0.002) & (a0 < 1.0)) | ((dl < 0.002) & (al < 1.0))
            mv = ~rest
            near = np.convolve(mv.astype(float), np.ones(11), 'same') > 0          # 5 frames from any motion
            rest = rest & ~near
            row = {'rest_frames': int(rest.sum()), 'T': T}
            if rest.sum() < 10:
                out[f'{ep}/{n}'] = row; continue
            for k, (M, anc) in [('mocap', (gt[n], host_anchor(n, s)))] + [(k, (v['poses'][n], v['anchor'][s])) for k, v in srcs.items()]:
                P, R = signals(M, anc)
                v, w = speed_cms(P), rate_degs(R)
                row[k] = dict(v_p50=round(float(np.percentile(v[rest], 50)), 2), v_p95=round(float(np.percentile(v[rest], 95)), 2),
                              v_p99=round(float(np.percentile(v[rest], 99)), 2), w_p50=round(float(np.percentile(w[rest], 50)), 2),
                              w_p95=round(float(np.percentile(w[rest], 95)), 2), w_p99=round(float(np.percentile(w[rest], 99)), 2))
            out[f'{ep}/{n}'] = row
            print(ep, n, row, flush=True)
    pooled = {}
    for k in ('mocap', 'perc', 'ref'):
        rows = [r[k] for r in out.values() if k in r]
        pooled[k] = {m: round(float(np.median([r[m] for r in rows])), 2) for m in rows[0]} if rows else None
        pooled[k + '_max'] = {m: round(float(np.max([r[m] for r in rows])), 2) for m in rows[0]} if rows else None
    out['_pooled_median_over_objects'] = pooled
    print(json.dumps(pooled, indent=1))
    json.dump(out, open(sys.argv[1], 'w'), indent=1)


if __name__ == '__main__':
    main()
