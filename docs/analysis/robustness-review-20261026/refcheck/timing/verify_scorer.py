"""refcheck/timing: write our reference object path (optionally time-shifted) as a poses_world_vo-style npz, so that
pipeline/score_registered.py (the kit's registered scoring) can score it, and print the in-process kit AUC
(refcheck/systematics kit_auc) for the same path. Used to check that the in-process scorer and the shift used in
cost.py reproduce the official functions. No ground truth is read except by the scorers.
Usage: python -I verify_scorer.py EP SHIFT_FRAMES OUT.npz
"""
import os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from tload import *                                                        # noqa: E402,F401,F403

ep, L, out = int(sys.argv[1]), float(sys.argv[2]), sys.argv[3]
e = canon()[ep]; fin, _, _ = ref_files(e)
names, gt = load_gt(ep)
ours = load_ref_parquet(fin)
b7 = {n: S.to7(ours[n]) for n in names}
sh = {n: (S.shift_path(b7[n], L) if L else b7[n]) for n in names}
np.savez(out, **{n: S.from7(sh[n]) for n in names})
H = [S.host_geometry(n, s) for s, n in enumerate(names)]
REG = [S.registration(ep, s, n, our_mesh_path(REF_LIB[ep], n)) for s, n in enumerate(names)]
auc, per, _, _ = S.kit_auc(ep, names, sh, gt, H, REG)
print('in-process kit AUC', auc, per, 'mesh lib', REF_LIB[ep])
