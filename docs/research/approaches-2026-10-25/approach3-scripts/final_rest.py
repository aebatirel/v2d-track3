"""Final placement (start of the object's last rest) from OUR reference vs the last contact-label hold end; the same
event from mocap as a labelled diagnostic (public episodes only). Final rest = 1 + the last frame where the object
moves > 0.5 cm/frame or turns > 2 deg/frame (after 3-frame smoothing). Usage: final_rest.py REF.parquet GT.parquet [swap]
(swap: the twin boards are named the other way round in our ep24 reference; mocap names are swapped for the pairing)."""
import os, sys
import numpy as np
from scipy.ndimage import uniform_filter1d
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_ref, hold_list  # noqa: E402
from events import gt_tracks  # noqa: E402


def final_rest(P, R):
    v = uniform_filter1d(np.r_[0, np.linalg.norm(np.diff(P, axis=0), axis=1) * 100], 3)
    w = uniform_filter1d(np.r_[0, np.degrees((R[1:] * R[:-1].inv()).magnitude())], 3)
    mv = np.nonzero((v > 0.5) | (w > 2.0))[0]
    return int(mv[-1]) + 1 if len(mv) else None


d = load_ref(sys.argv[1]); ph = hold_list(sys.argv[1]); names = list(d['names'])
gnames = names[::-1] if len(sys.argv) > 3 else names
G = gt_tracks(sys.argv[2], set(names))
for j, n in enumerate(names):
    hs = [x['end'] for x in ph if x['object'] == n]
    fr_ref = final_rest(d['OP'][:, j], d['OR'][j]); fr_gt = final_rest(*G[gnames[j]])
    ho = max(hs) if hs else None
    print(n, 'final rest ref', fr_ref, 'GT', fr_gt, '| last hold end', ho,
          '| ref-GT', None if fr_ref is None or fr_gt is None else fr_ref - fr_gt,
          '| hold_end-GT', None if ho is None or fr_gt is None else ho - fr_gt)
