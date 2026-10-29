"""V4 (verify_systematics): write my own variants of our object paths as poses_world_vo-style npz files (4x4 per object)
for pipeline/score_registered.py (the official local scorer; the other agent used an in-process copy).
Variants:
  base        the path as stored (reference parquet / e2s parquet / perception npz)
  p05         advanced by +0.5 frame: positions by CUBIC spline (the other agent used linear), rotations by slerp
  p1, m1      integer shifts by +1 / -1 frame (no interpolation at all; edge frame repeated)
  tiltA       ORACLE (mocap): only the kit anchor object's frame-0 tilt removed, as a constant body-frame swing taking
              our anchor's up axis (relative to our table) to mocap's at frame 0; anchor point kept in place.
              (The other agent's 'tilt' removes a rest-averaged tilt of every object.)
Usage: python -I v4_make_npz.py OUTDIR"""
import os, sys
import numpy as np
from scipy.interpolate import CubicSpline
from scipy.spatial.transform import Rotation as R, Slerp
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vload import *  # noqa
import v2_scale_lag_tilt as V


def shift(M, tau):
    T = len(M); t = np.arange(T); tq = np.clip(t + tau, 0, T - 1)
    out = np.tile(np.eye(4), (T, 1, 1))
    if float(tau).is_integer():
        idx = np.clip(t + int(tau), 0, T - 1); return M[idx].copy()
    out[:, :3, 3] = CubicSpline(t, M[:, :3, 3], axis=0)(tq)
    out[:, :3, :3] = Slerp(t, R.from_matrix(M[:, :3, :3]))(tq).as_matrix()
    return out


def swing(u, v):
    """Minimal rotation matrix taking unit u to unit v."""
    u = u / np.linalg.norm(u); v = v / np.linalg.norm(v); c = np.cross(u, v); s = np.linalg.norm(c)
    if s < 1e-12:
        return np.eye(3)
    return R.from_rotvec(c / s * np.arctan2(s, np.dot(u, v))).as_matrix()


def tilt_anchor(ep, names, ours, gt, lib):
    fixed = [s for s, n in enumerate(names) if n not in V.SYMN]
    k = fixed[0] if fixed else 0; n = names[k]
    ca, B, sa, _ = V.reg(ep, k, n, lib)
    Rk = ours[n][0, :3, :3] @ B.T                         # kit convention: our table frame <- scan body
    z = np.array([0, 0, 1.0])
    u_o = Rk.T @ z; u_g = gt[n][0, :3, :3].T @ z          # up axes in the scan body frame
    S = swing(u_g, u_o)                                   # Rk S u_g = Rk u_o = z
    C = B.T @ S @ B                                       # same correction in our body frame
    M = ours[n].copy()
    Rn = M[:, :3, :3] @ C
    M[:, :3, 3] = M[:, :3, 3] + (M[:, :3, :3] - Rn) @ ca
    M[:, :3, :3] = Rn
    o = dict(ours); o[n] = M
    ang = float(np.degrees(np.arccos(np.clip(u_o @ u_g, -1, 1))))
    return o, n, ang


JOBS = {  # ep: list of (source, variant)
    21: [('ref', 'base'), ('ref', 'p05'), ('ref', 'tiltA'), ('pre', 'base'), ('perc', 'base')],
    26: [('ref', 'base'), ('ref', 'p05'), ('pre', 'base'), ('perc', 'base')],
    39: [('ref', 'base'), ('ref', 'p05'), ('ref', 'p1'), ('ref', 'm1')],
    24: [('ref', 'base'), ('ref', 'p05')],
    41: [('perc', 'base'), ('perc', 'p05')],
    22: [('perc', 'base'), ('perc', 'p05'), ('perc', 'tiltA')],
}

if __name__ == '__main__':
    od = sys.argv[1]; os.makedirs(od, exist_ok=True)
    for ep, jobs in JOBS.items():
        names, gt, _ = mocap(ep)
        d = ref_dir(ep); tfp = f'{d}/table_frame.npz' if d else f'{ST}/{V.STALE_TF.format(ep)}'
        Tt = np.load(tfp)['T_table_from_world']
        P = perc(ep)
        src = {'perc': ({n: np.einsum('ij,tjk->tik', Tt, P[n]) for n in names}, V.LIB_PERC[ep])}
        if d:
            src['ref'] = (refparq(ref_final(ep)), V.LIB_REF[ep]); src['pre'] = (refparq(f'{d}/e2s_reference.parquet'), V.LIB_REF[ep])
        for s, v in jobs:
            ours, lib = src[s]
            if v == 'base':
                o = ours
            elif v == 'p05':
                o = {n: shift(ours[n], 0.5) for n in names}
            elif v == 'p1':
                o = {n: shift(ours[n], 1.0) for n in names}
            elif v == 'm1':
                o = {n: shift(ours[n], -1.0) for n in names}
            elif v == 'tiltA':
                o, an, ang = tilt_anchor(ep, names, ours, gt, lib)
                print(f'ep{ep} {s} tiltA: anchor {an} frame-0 tilt removed {ang:.2f} deg')
            np.savez(f'{od}/ep{ep}_{s}_{v}.npz', **{n: o[n] for n in names})
            print(f'{od}/ep{ep}_{s}_{v}.npz', lib)
