"""Official AUC (kit score() via work/11/sc11.py) of a PERFECT tracker whose only error is the slot-0 frame-0 anchor
being the mean pose over rows [0, end] (analysis only, public GT). AUC loss = 1 - AUC (perfect = 1)."""
import sys, os, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from c_lib import *
sys.path.insert(0, f'{ROOT}/work/11')
import sc11
from scipy.spatial.transform import Rotation as Rot
_C = {}


def auc_window(ep, end, sigma=0.0, seeds=1):
    """sigma > 0: add a base tracking error (per frame/object translation, random direction, |N(0, sigma)| m;
    slot-0 row 0 kept exact) so the anchor bias is scored on top of a realistic error level (mean over seeds)."""
    end = int(np.floor(end))
    if (ep, end, sigma) in _C: return _C[(ep, end, sigma)]
    g = gt_ref(ep); e = g['e']; j = g['j']
    order = [j] + [i for i in range(len(e['names'])) if i != j]
    ref = e['pose'][:, order].copy(); names = [e['names'][i] for i in order]
    # fill NaNs (not expected) by forward fill
    for b in range(ref.shape[1]):
        for t in range(1, ref.shape[0]):
            if not np.isfinite(ref[t, b]).all(): ref[t, b] = ref[t - 1, b]
    vals = []
    for sd in range(seeds):
        ach = ref.copy()
        if sigma > 0:
            rng = np.random.default_rng(1000 * ep + sd); T, B = ref.shape[:2]
            v = rng.normal(size=(T, B, 3)); v /= np.linalg.norm(v, axis=2, keepdims=True)
            ach[..., :3] += v * np.abs(rng.normal(0, sigma, size=(T, B, 1))); ach[0, 0, :3] = ref[0, 0, :3]
        vals.append(_score(ach, ref, names, ep, end))
    _C[(ep, end, sigma)] = float(np.mean(vals)); return _C[(ep, end, sigma)]


def _score(ach, ref, names, ep, end):
    if end >= 1:
        P = ref[:end + 1, 0]
        ach[0, 0, :3] = P[:, :3].mean(0); ach[0, 0, 3:] = Rot.from_quat(P[:, 3:]).mean().as_quat()
    return float(sc11.MET['AUC'].score(*sc11.frames(ach, ref, names, ep), 'id'))


if __name__ == '__main__':
    for ep in map(int, sys.argv[1:]):
        g = gt_ref(ep)
        for sg in (0.0, 0.03):
            print(ep, g['name'], sg, {k: round(auc_window(ep, v, sg, 4 if sg else 1), 4) for k, v in
                                  dict(f0=0, orc=g['pert'] - 1, f15=14, cm1=g['on'] - 1).items()}, flush=True)
