"""DIAGNOSTIC (2026-11-12, note 27 §9): FlashSAC actor checkpoints in numpy, for weight-space analysis and hand edits.
No simulator, no JAX, no ground truth.

Names follow jax's sorted-key flattening of the actor (FlashCHORD training/flash_sac/network.py, residual head with
unit_gain); checked here only by shapes and value ranges, and the numpy forward is NOT yet checked against JAX.
  python tools/actor_np.py census CKPT.safetensors [...]   idle-unit estimate per layer from the batch-norm statistics
"""
import json, math, struct, sys

import numpy as np

NAMES = ["block_0/contract/unit_kernel","block_0/contract_norm/unit_bias","block_0/contract_norm/unit_scale","block_0/expand/unit_kernel","block_0/expand_norm/unit_bias","block_0/expand_norm/unit_scale",
"block_1/contract/unit_kernel","block_1/contract_norm/unit_bias","block_1/contract_norm/unit_scale","block_1/expand/unit_kernel","block_1/expand_norm/unit_bias","block_1/expand_norm/unit_scale",
"embed/unit_kernel","input_norm/unit_bias","input_norm/unit_scale","log_std/gain","log_std/unit_kernel","log_std_bias","mean/gain","mean/unit_kernel","mean_bias","post_norm/rms_scale",
"bs/block_0/contract_norm/mean","bs/block_0/contract_norm/var","bs/block_0/expand_norm/mean","bs/block_0/expand_norm/var","bs/block_1/contract_norm/mean","bs/block_1/contract_norm/var","bs/block_1/expand_norm/mean","bs/block_1/expand_norm/var","bs/input_norm/mean","bs/input_norm/var"]
def load(p):
    f = open(p, 'rb'); n = struct.unpack('<Q', f.read(8))[0]; h = json.loads(f.read(n)); buf = f.read(); meta = h.pop('__metadata__', {})
    W = {}
    for k, v in h.items():
        a, b = v['data_offsets']; W[NAMES[int(k.split('.')[1])]] = np.frombuffer(buf[a:b], dtype=np.float32).reshape(v['shape'])
    return W, meta
def bn(x, W, name, eps=1e-5):
    return (x - W[f'bs/{name}/mean']) / np.sqrt(W[f'bs/{name}/var'] + eps) * W[f'{name}/unit_scale'] + W[f'{name}/unit_bias']
def actor_mean(obs, W, return_acts=False):
    """Deterministic actor mean (residual head, unit_gain), eval mode (running BN stats). obs: (B, 722)."""
    acts = {}
    h = bn(obs, W, 'input_norm') @ W['embed/unit_kernel']
    for b in ('block_0', 'block_1'):
        e = np.maximum(bn(h @ W[f'{b}/expand/unit_kernel'], W, f'{b}/expand_norm'), 0); acts[f'{b}/expand'] = e
        c = np.maximum(bn(e @ W[f'{b}/contract/unit_kernel'], W, f'{b}/contract_norm'), 0); acts[f'{b}/contract'] = c
        h = c + h
    r = h / np.sqrt(np.mean(h * h, -1, keepdims=True) + 1e-6) * W['post_norm/rms_scale']
    mean = (r @ W['mean/unit_kernel']) * W['mean/gain'] + W['mean_bias']
    return (mean, acts) if return_acts else mean


def p_active(W, layer):
    """P(unit > 0 after BN+ReLU) if the normalised input is N(0, 1): Phi(bias / |scale|). A rough, input-free estimate."""
    z = W[f'{layer}/unit_bias'] / np.maximum(np.abs(W[f'{layer}/unit_scale']), 1e-9)
    return 0.5 * (1 + np.vectorize(math.erf)(z / math.sqrt(2)))


if __name__ == '__main__' and len(sys.argv) > 2 and sys.argv[1] == 'census':
    for p in sys.argv[2:]:
        W, _ = load(p)
        cols = []
        for b in ('block_0', 'block_1'):
            for lay in ('expand', 'contract'):
                pa = p_active(W, f'{b}/{lay}_norm')
                cols.append(f'{b}.{lay} {int((pa < 0.01).sum())}/{pa.size} idle, median P(active) {np.median(pa):.3f}')
        print(p, '|', ' | '.join(cols))
