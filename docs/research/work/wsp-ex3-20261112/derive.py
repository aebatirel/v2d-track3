"""Derive data-based directions from recorded traces (difference of means) and store them in directions.npz.

Usage: python -I derive.py ACTOR_NPZ TRACE_NPZ OUT_NPZ NAME LAYER FAIL_LO FAIL_HI NORM_LO NORM_HI
  LAYER is one of the activation names of net.forward (e.g. r, h1, h2).
  d = mean(LAYER | frames FAIL_LO..FAIL_HI) - mean(LAYER | frames NORM_LO..NORM_HI-1), stored unit-normalised,
  together with the mean projection of the normal frames (ref level). Frames are the observation frames of the trace.
Appends to OUT_NPZ if it exists.
"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import net

actor, trace, out, name, layer = sys.argv[1:6]
flo, fhi, nlo, nhi = map(int, sys.argv[6:10])
w = net.load(actor); t = np.load(trace)
obs, fr = t['obs'], t['frames'][:len(t['obs'])]
_, A = net.forward(w, obs, acts=True)
X = A[layer]
F = (fr >= flo) & (fr <= fhi); N = (fr >= nlo) & (fr < nhi)
d = X[F].mean(0) - X[N].mean(0); dn = d / np.linalg.norm(d)
ref = float((X[N] @ dn).mean())
store = dict(np.load(out)) if os.path.exists(out) else {}
store[name] = dn.astype(np.float64); store[name + '__ref'] = np.float64(ref)
store[name + '__info'] = np.array(f'{layer}: mean(frames {flo}-{fhi}) - mean(frames {nlo}-{nhi-1}) of {os.path.basename(trace)}; '
                                  f'|d|={np.linalg.norm(d):.3f}; normal-frame mean projection {ref:.3f}')
np.savez(out, **store)
print(name, str(store[name + '__info']))
