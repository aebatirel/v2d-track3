"""verify_timing: export a stored rollout's SIMULATED object path (world 0) to npz, optionally time-shifted, so the
official pipeline/score_registered.py can score it in npz mode (27 Oct 2026, CPU). Reader = the kit's own
v2dlb.submission_parquet.read_trajectory (pose_xyzw: x,y,z,qx,qy,qz,qw).
Usage: python -I vt_sim.py ROLLOUT.parquet EP VARIANT OUT.npz      (VARIANT: [k0:]shift:<s> | smooth:<a> | fshift:<s> | fsmooth:<f>)
"""
import sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vt_load as L
import vt_shift as VS
KIT = f'{L.RC}/kit/v2d_submission_kit'
sys.path.insert(0, KIT)
from v2dlb.submission_parquet import read_trajectory


def main():
    f, ep, var, outp = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
    names, _ = L.load_mocap(ep)
    tr = read_trajectory(f)
    w0 = tr.world_index == tr.world_index.min()
    frames = np.unique(tr.frame_index[w0])
    assert (frames == np.arange(len(frames))).all(), 'frames not 0..T-1'
    G = np.full((len(frames), len(names), 7), np.nan)
    for fr, s, q in zip(tr.frame_index[w0], tr.object_slot[w0], tr.pose_xyzw[w0]):
        G[fr, s] = q
    assert np.isfinite(G).all()
    keep0 = var.startswith('k0:')
    kind, *args = (var[3:] if keep0 else var).split(':')
    fn = {'shift': VS.shift, 'smooth': VS.smooth, 'fshift': VS.fshift, 'fsmooth': VS.fsmooth}[kind]
    Q = {}
    for s, n in enumerate(names):
        M = L.to44(G[:, s, :3], L.quat_wxyz_to_R(G[:, s, [6, 3, 4, 5]]))
        Q[n] = fn(M, float(args[0]))
        if keep0:
            Q[n][0] = M[0]
    np.savez(outp, **Q)
    print(outp, len(frames), names)


if __name__ == '__main__':
    main()
