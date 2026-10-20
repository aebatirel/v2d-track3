"""Verifier: re-run the stage C feature extractors on a few eps and compare with the stored npz (no writes to work/20)."""
import sys, numpy as np
sys.path.insert(0, '/Users/aebatirel/Documents/Code/v2d-research/work/20/scripts')
from c_lib import *
import c_detect, c_motion
for ep in map(int, sys.argv[1:]):
    g = gt_ref(ep); R, C = cam0(ep)
    M0, z = silhouette(g['name'], g['e']['pose'][0, g['j']], R, C)
    F = frames('public', ep, 'a', n_max=160)
    rows, box, _ = c_detect.features(F, M0)
    old = np.load(f'{OUT}/feat_v2_p{ep}.npz')['rows']
    n = min(len(rows), len(old))
    dtouch = np.abs(rows[:n, 1] - old[:n, 1]).max()
    mrows, r0 = c_motion.motion(F[:140], M0)
    mo = np.load(f'{OUT}/mot_t2_p{ep}.npz'); om = mo['rows']; m = min(len(mrows), len(om))
    dm = np.nanmax(np.abs(mrows[:m, 1:4] - om[:m, 1:4])); 
    np.savez(f'/Users/aebatirel/Documents/Code/v2d-research/work/20-verify/feat_p{ep}.npz', rows=rows, mrows=mrows, r0=r0, z=z)
    print(f'p{ep} z {z:.3f} vs stored {float(mo["z"]):.3f} | feat rows {len(rows)} vs {len(old)} max|dtouch| {dtouch} | mot rows {len(mrows)} vs {len(om)} max|dstep| {dm:.4f} r0 {r0:.1f} vs {float(mo["r0"]):.1f}', flush=True)
