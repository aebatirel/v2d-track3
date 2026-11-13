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


EPS = 1e-5


def _bn_identity(w, layer, j):
    """Make unit j of a batch norm an identity map: (x - 0)/sqrt(1-eps+eps)*1 + 0."""
    w[f'batch_stats/{layer}/running_mean'][j] = 0
    w[f'batch_stats/{layer}/running_variance'][j] = 1 - EPS
    w[f'params/{layer}/unit_scale'][j] = 1
    w[f'params/{layer}/unit_bias'][j] = 0


def privatize_coordinate(w, j):
    """Turn residual-stream coordinate j into a private channel from block 0's contract unit j to the head.

    No input writes into it (embedding column j = 0), no block reads it (row j of both expand kernels = 0), the
    block-1 contract unit j writes nothing (column zero, identity norm -> relu(0) = 0), and the block-0 contract unit j
    becomes a wire: column zero (filled later by gate units), identity norm, so c0_j = relu(sum of gate writes).
    The head row j is cleared; controllers fill it with their output pattern. h2_j = h1_j = c0_j.
    """
    w = copy(w)
    w['params/embed/unit_kernel'][:, j] = 0
    for b in ('block_0', 'block_1'):
        w[f'params/{b}/expand/unit_kernel'][j, :] = 0
        w[f'params/{b}/contract/unit_kernel'][:, j] = 0
        _bn_identity(w, f'{b}/contract_norm', j)
    w[K_MEAN][j, :] = 0
    return w


def input_readout(w, i):
    """Direction u in the 256-wide h0 with h0.u ~= c * xnorm_i (least squares through the embedding kernel, a property
    of the weights only). Returns u and c = (E u)_i."""
    E = w['params/embed/unit_kernel'].astype(np.float64)
    e = np.zeros(E.shape[0]); e[i] = 1
    u = np.linalg.lstsq(E, e, rcond=None)[0]
    return u, float((E @ u)[i])


def input_affine(w, i):
    """xnorm_i = A*x_i + B (the input batch norm, frozen)."""
    mu = float(w['batch_stats/input_norm/running_mean'][i]); var = float(w['batch_stats/input_norm/running_variance'][i])
    s = float(w['params/input_norm/unit_scale'][i]); b = float(w['params/input_norm/unit_bias'][i])
    A = s / np.sqrt(var + EPS)
    return A, b - mu * A


def gate_unit_block0(w, k, terms, threshold, kappa, channel, weight=1.0):
    """Idle block-0 expand unit k computes  e = relu(kappa * (sum_i c_i * x_i - threshold))  from raw inputs x_i
    (terms = {input index: c_i}), read from h0 through least-squares readouts of the embedding, and writes
    weight * e into the private channel coordinate `channel` (block-0 contract unit, identity norm)."""
    w = copy(w)
    col = np.zeros(256); const = 0.0
    for i, ci in terms.items():
        u, c = input_readout(w, i)
        A, B = input_affine(w, i)
        # x_i = (h0.u / c - B) / A
        col += ci * u / (c * A); const += -ci * B / A
    w['params/block_0/expand/unit_kernel'][:, k] = (kappa * col).astype(np.float32)
    _bn_identity(w, 'block_0/expand_norm', k)
    w['params/block_0/expand_norm/unit_bias'][k] = np.float32(kappa * (const - threshold))
    w['params/block_0/contract/unit_kernel'][k, :] = 0
    w['params/block_0/contract/unit_kernel'][k, channel] = np.float32(weight)
    return w


def head_row(w, channel, pattern, rms_ref):
    """Head row of the private channel: output j moves by pattern[j] per unit of channel value at stream rms = rms_ref.
    z_j += gain_j * rms_scale_ch * W[ch, j] * h2_ch / rms."""
    w = copy(w)
    g = w[G_MEAN].astype(np.float64); rs = float(w['params/post_norm/rms_scale'][channel])
    for j, p in pattern.items():
        w[K_MEAN][channel, j] = np.float32(p * rms_ref / (g[j] * rs))
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
