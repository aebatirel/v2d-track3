"""verify_timing: write time-shifted / control variants of OUR path as poses_world_vo-style npz (4x4 per object),
to be scored by the official pipeline/score_registered.py. My own interpolation code (27 Oct 2026, CPU).

  new(t) = old(t + s): s > 0 ADVANCES our path (undoes a lag). Positions: linear; rotations: slerp; clamped at the ends.
  variants: shift:<s>   time shift by s frames
            smooth:<a>  symmetric smoothing control: new(t) = old(t) * (1-2a) + a*old(t-1) + a*old(t+1) (positions;
                        rotations by chordal mean), i.e. the same kind of low-pass a fractional shift applies, but no shift
            freeze:<obj>:<f0>:<f1>  hold <obj> at the chordal-mean pose of frames f0..f1 for ALL frames
            fshift:<s>  band-limited (FFT, pure phase) shift: no smoothing
            fsmooth:<f> zero-phase filter with the magnitude response of linear interpolation at fraction f
            k0:<variant> any of the above, then frame 0 restored to the original (the kit aligns the scene ONCE at
                        frame 0, so this keeps the alignment identical to the unshifted path)
Usage: python -I vt_shift.py EP SOURCE(perc|ref|pre) VARIANT OUT.npz
"""
import sys, os
import numpy as np
from scipy.spatial.transform import Rotation as Rot, Slerp
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vt_load as L


def shift(M, s):
    T = len(M); t = np.clip(np.arange(T) + s, 0, T - 1)
    out = np.tile(np.eye(4), (T, 1, 1))
    for k in range(3):
        out[:, k, 3] = np.interp(t, np.arange(T), M[:, k, 3])
    out[:, :3, :3] = Slerp(np.arange(T), Rot.from_matrix(M[:, :3, :3]))(t).as_matrix()
    return out


def _fft_shift_1d(x, s, pad=64):
    """band-limited fractional shift new(t) = x(t + s): mirror-pad, multiply the spectrum by exp(i w s), crop.
    No magnitude change at any frequency (pure phase), unlike linear interpolation."""
    T = len(x); p = min(pad, T - 1)
    y = np.concatenate([x[p:0:-1], x, x[-2:-p - 2:-1]])
    N = len(y); w = 2 * np.pi * np.fft.rfftfreq(N)
    z = np.fft.irfft(np.fft.rfft(y) * np.exp(1j * w * s), n=N)
    return z[p:p + T]


def _fft_mag_1d(x, f, pad=64):
    """zero-phase filter with EXACTLY the magnitude response of linear interpolation at fraction f:
    |H(w)| = |(1-f) + f exp(i w)|. So linear shift(f) == fsmooth(f) o fshift(f) (up to edges)."""
    T = len(x); p = min(pad, T - 1)
    y = np.concatenate([x[p:0:-1], x, x[-2:-p - 2:-1]])
    N = len(y); w = 2 * np.pi * np.fft.rfftfreq(N)
    H = np.abs((1 - f) + f * np.exp(1j * w))
    return np.fft.irfft(np.fft.rfft(y) * H, n=N)[p:p + T]


def _apply_q(M, fn):
    T = len(M); out = np.tile(np.eye(4), (T, 1, 1))
    for k in range(3):
        out[:, k, 3] = fn(M[:, k, 3])
    q = Rot.from_matrix(M[:, :3, :3]).as_quat()
    for t in range(1, T):
        if q[t] @ q[t - 1] < 0:
            q[t] = -q[t]
    q2 = np.stack([fn(q[:, k]) for k in range(4)], 1)
    out[:, :3, :3] = Rot.from_quat(q2 / np.linalg.norm(q2, axis=1, keepdims=True)).as_matrix()
    return out


def fsmooth(M, f):
    return _apply_q(M, lambda x: _fft_mag_1d(x, f))


def fshift(M, s):
    """pure time shift (band-limited) of positions and of sign-continuous quaternion components (renormalised)."""
    T = len(M); out = np.tile(np.eye(4), (T, 1, 1))
    for k in range(3):
        out[:, k, 3] = _fft_shift_1d(M[:, k, 3], s)
    q = Rot.from_matrix(M[:, :3, :3]).as_quat()
    for t in range(1, T):
        if q[t] @ q[t - 1] < 0:
            q[t] = -q[t]
    q2 = np.stack([_fft_shift_1d(q[:, k], s) for k in range(4)], 1)
    out[:, :3, :3] = Rot.from_quat(q2 / np.linalg.norm(q2, axis=1, keepdims=True)).as_matrix()
    return out


def chordal_mean(Rs):
    U, _, Vt = np.linalg.svd(Rs.sum(0))
    D = np.diag([1, 1, np.sign(np.linalg.det(U @ Vt))])
    return U @ D @ Vt


def smooth(M, a):
    T = len(M); out = M.copy()
    idx = np.arange(T); lo = np.clip(idx - 1, 0, T - 1); hi = np.clip(idx + 1, 0, T - 1)
    out[:, :3, 3] = (1 - 2 * a) * M[:, :3, 3] + a * M[lo, :3, 3] + a * M[hi, :3, 3]
    for t in range(T):
        out[t, :3, :3] = chordal_mean(np.stack([(1 - 2 * a) * M[t, :3, :3], a * M[lo[t], :3, :3], a * M[hi[t], :3, :3]]))
    return out


def main():
    ep, src, var, outp = int(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
    e = L.canon()[ep]
    fin, pre = L.ref_paths(e)
    P = (L.load_npz(f"{L.STORE}/{e['perception_path']}") if src == 'perc'
         else L.load_refpq(fin) if src == 'ref' else L.load_refpq(pre))
    keep0 = var.startswith('k0:')                     # keep frame 0 as is -> the kit's frame-0 scene alignment is unchanged
    kind, *args = (var[3:] if keep0 else var).split(':')
    Q = {}
    for n, M in P.items():
        if kind == 'shift':
            Q[n] = shift(M, float(args[0]))
        elif kind == 'fshift':
            Q[n] = fshift(M, float(args[0]))
        elif kind == 'fsmooth':
            Q[n] = fsmooth(M, float(args[0]))
        elif kind == 'hold' and n == args[0]:          # hold <obj> at the mean pose of frames a..b for frames < until
            a, b, until = int(args[1]), int(args[2]), int(args[3]); Q[n] = M.copy()
            Q[n][:until, :3, :3] = chordal_mean(M[a:b + 1, :3, :3]); Q[n][:until, :3, 3] = M[a:b + 1, :3, 3].mean(0)
        elif kind == 'f0mean':                        # mechanism test: frame 0 := mean pose of frames 0..k-1, rest untouched
            k = int(args[0]); Q[n] = M.copy()
            Q[n][0, :3, :3] = chordal_mean(M[:k, :3, :3]); Q[n][0, :3, 3] = M[:k, :3, 3].mean(0)
        elif kind == 'f0from':                        # mechanism test: frame 0 := mean pose of frames a..b (b inclusive)
            a, b = int(args[0]), int(args[1]); Q[n] = M.copy()
            Q[n][0, :3, :3] = chordal_mean(M[a:b + 1, :3, :3]); Q[n][0, :3, 3] = M[a:b + 1, :3, 3].mean(0)
        elif kind == 'smooth':
            Q[n] = smooth(M, float(args[0]))
        elif kind == 'freeze' and n == args[0]:
            f0, f1 = int(args[1]), int(args[2])
            F = np.eye(4); F[:3, :3] = chordal_mean(M[f0:f1 + 1, :3, :3]); F[:3, 3] = M[f0:f1 + 1, :3, 3].mean(0)
            Q[n] = np.repeat(F[None], len(M), 0)
        else:
            Q[n] = M.copy()
    if keep0:
        for n in Q:
            Q[n][0] = P[n][0]
    np.savez(outp, **Q)
    print(outp, {n: Q[n].shape for n in Q}, 'max change cm', {n: round(float(np.abs(Q[n][:, :3, 3] - P[n][:, :3, 3]).max() * 100), 3) for n in Q})


if __name__ == '__main__':
    main()
