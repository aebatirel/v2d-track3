"""G2/G3 inputs (G2 copy, unchanged): 40000-point random subsamples (numpy default_rng(0), no replacement) of OUR observed points
(obs_points.py output, scratchpad obs_all/ep<E>_<obj>.npz, GT-free) for the box's Sim(3) fits, as obs_sub.tar was for the
29 Oct probe (sim3_fit.py subsamples again to 20000). Only the 'pts' array is kept.
Usage: obs_sub.py OBS_ALL_DIR OUT_DIR ep41_white_pot ep43_white_pot ...
"""
import os, sys
import numpy as np

src, out = sys.argv[1:3]
os.makedirs(out, exist_ok=True)
for name in sys.argv[3:]:
    P = np.load(os.path.join(src, name + '.npz'))['pts']
    i = np.random.default_rng(0).choice(len(P), min(40000, len(P)), replace=False)
    np.savez(os.path.join(out, name + '.npz'), pts=P[np.sort(i)])
    print(name, len(P), '->', len(i))
