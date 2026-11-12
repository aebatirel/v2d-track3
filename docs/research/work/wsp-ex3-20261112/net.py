"""Numpy forward pass of exercise 3's actor with intermediate activations (same arithmetic as policy.py).

Observation layout (332, from simulation.py observation()):
  0:6 wrist pos (R,L) world | 6:14 wrist quat wxyz (R,L) | 14:28 arm q (R 7, L 7) | 28:42 arm qd
  42:56 arm ref target - q | 56:100 finger q normalised to [-1,1] (R 22, L 22) | 100:144 finger qd
  144:147 object pos world | 147:151 object quat | 151:158 R wrist cmd (pos err in wrist frame, rel quat)
  158:165 L wrist cmd | 165:209 finger ref target - q | 209:212 object pos err in object frame
  212:216 object rel quat | 216:274 raw action (previous) | 274:332 processed target (previous)
Actions (58): 0:7 R arm, 7:29 R fingers, 29:36 L arm, 36:58 L fingers.
"""
import numpy as np

BLOCKS = {
    'wrist_pos': slice(0, 6), 'wrist_quat': slice(6, 14), 'arm_q': slice(14, 28), 'arm_qd': slice(28, 42),
    'arm_cmd': slice(42, 56), 'finger_q': slice(56, 100), 'finger_qd': slice(100, 144), 'obj_pos': slice(144, 147),
    'obj_quat': slice(147, 151), 'Rwrist_cmd': slice(151, 158), 'Lwrist_cmd': slice(158, 165),
    'finger_cmd': slice(165, 209), 'obj_pos_err': slice(209, 212), 'obj_rot_err': slice(212, 216),
    'prev_raw': slice(216, 274), 'prev_target': slice(274, 332)}


def load(path):
    with np.load(path, allow_pickle=False) as d:
        return {k: d[k] for k in d.files}


def norm(w, x, name):
    return ((x - w['batch_stats/' + name + '/running_mean']) /
            np.sqrt(w['batch_stats/' + name + '/running_variance'] + np.float32(1e-5)) *
            w['params/' + name + '/unit_scale'] + w['params/' + name + '/unit_bias'])


def forward(w, obs, acts=False):
    x = np.asarray(obs, dtype=np.float32)
    A = {}
    A['in'] = norm(w, x, 'input_norm')
    h = A['in'] @ w['params/embed/unit_kernel']; A['h0'] = h
    for i in range(2):
        b = f'block_{i}'
        pre = norm(w, h @ w[f'params/{b}/expand/unit_kernel'], b + '/expand_norm'); A[f'e{i}pre'] = pre
        e = np.maximum(pre, 0); A[f'e{i}'] = e
        cpre = norm(w, e @ w[f'params/{b}/contract/unit_kernel'], b + '/contract_norm'); A[f'c{i}pre'] = cpre
        c = np.maximum(cpre, 0); A[f'c{i}'] = c
        h = c + h; A[f'h{i+1}'] = h
    rms = np.sqrt(np.mean(h * h, axis=-1, keepdims=True) + np.float32(1e-6)); A['rms'] = rms
    r = h / rms * w['params/post_norm/rms_scale']; A['r'] = r
    mean = (r @ w['params/mean/unit_kernel']) * w['params/mean/gain'] + w['params/mean_bias']; A['mean'] = mean
    out = np.tanh(mean).astype(np.float32)
    return (out, A) if acts else out
