"""Hand-built weight edits for exercise 3's actor. Every edit keeps all array shapes.

Each function takes the weight dict (copied) plus explicit numbers and returns the edited dict. Data-derived
directions are computed by derive.py from recorded traces and stored in directions.npz; the derivation of each is
documented there and in README.md. No gradients, no optimisation, no rollout-score search.
"""
import numpy as np

K_MEAN = 'params/mean/unit_kernel'
B_MEAN = 'params/mean_bias'
G_MEAN = 'params/mean/gain'


def copy(w):
    return {k: v.copy() for k, v in w.items()}


def project_out_of_readout(w, outputs, d, ref_level):
    """Remove direction d (unit vector in the RMS-normalised stream r) from the readout of the given outputs.

    For output j: W[:, j] <- W[:, j] - (W[:, j].d) d, and the bias absorbs the old contribution at r.d = ref_level,
    so the output is unchanged wherever r.d == ref_level and no longer depends on r.d elsewhere.
    """
    w = copy(w)
    W, b, g = w[K_MEAN], w[B_MEAN], w[G_MEAN]
    d = np.asarray(d, np.float64); d = d / np.linalg.norm(d)
    for j in outputs:
        c = float(W[:, j].astype(np.float64) @ d)
        W[:, j] = (W[:, j] - c * d).astype(np.float32)
        b[j] = np.float32(b[j] + g[j] * c * ref_level)
    return w


def diff(w0, w1):
    """Count changed entries and Frobenius norm of the change per array."""
    out = {}
    for k in w0:
        dlt = w1[k].astype(np.float64) - w0[k].astype(np.float64)
        n = int((dlt != 0).sum())
        if n:
            out[k] = dict(changed=n, zeroed=int(((w1[k] == 0) & (w0[k] != 0)).sum()), fro=float(np.linalg.norm(dlt)))
    return out


def save(w, path):
    np.savez(path, **w)
