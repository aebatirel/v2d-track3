"""Synthetic B0 fixtures (tools/e11g_verify.py b0): from a rebuilt tracks folder (C/ep11, T/ep11) write perturbed copies.
  numeric_C        C's blue cup moved 0.005 mm on f50-59            -> NUMERIC (go)
  differs_C        C's blue cup moved 1 mm                          -> MISMATCH (C has no DIFFERS band)
  differs_T        T's blue cup moved 3 mm                          -> DIFFERS (go, flagged)
  mismatch_T_is_C  T replaced by C's track                          -> MISMATCH
  mismatch_T_6mm   T's blue cup moved 6 mm                          -> MISMATCH
  camera_changed   C's world_T_cam changed by 1e-9 m on one frame   -> MISMATCH (world_T_cam must be byte-identical)
Usage: python b0_fixtures.py TRACKS_DIR OUT_DIR"""
import os, sys
import numpy as np
src, out = sys.argv[1:3]


def mk(name, fC=None, fT=None):
    d = f'{out}/{name}'
    for t, f in (('C', fC), ('T', fT)):
        os.makedirs(f'{d}/{t}/ep11', exist_ok=True); z = dict(np.load(f'{src}/{t}/ep11/poses.npz'))
        if f:
            z = f(z, t)
        np.savez(f'{d}/{t}/ep11/poses.npz', **z)


def nudge(mm):
    def f(z, t):
        z = dict(z); k = 'cam_T_blue_cup'; a = z[k].astype(np.float64); a[50:60, 0, 3] += mm / 1000; z[k] = a.astype(np.float32); return z
    return f


def swapT(z, t):
    return dict(np.load(f'{src}/C/ep11/poses.npz'))


def cam(z, t):
    z = dict(z); w = z['world_T_cam'].copy(); w[5, 0, 3] += 1e-9; z['world_T_cam'] = w; return z


mk('numeric_C', fC=nudge(0.005)); mk('differs_C', fC=nudge(1.0)); mk('differs_T', fT=nudge(3.0)); mk('mismatch_T_is_C', fT=swapT)
mk('mismatch_T_6mm', fT=nudge(6.0)); mk('camera_changed', fC=cam)
