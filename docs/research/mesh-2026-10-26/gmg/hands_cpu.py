"""Hands on the CPU (module M1 of SPEC section 7; build step B4).

  run_hands(split, ep, video_a, depth, calib, poses, out) -> path of hands.npz
  segments(hands_npz_path, world_T_cam, hand_r, arm_r, arm_len) -> per frame (A, B, radius) in camera coordinates
  venv_python() -> path of the MediaPipe interpreter

MediaPipe Hands (pipeline/hands_mp.py: cam_a colour video + our FoundationStereo depth + VO world_T_cam; no ground
truth read) runs in its own Python 3.12 virtual environment (mediapipe 0.10.14 has no Python 3.13 wheel), as a child
process. The guard checks every input before the child starts (roles video, depth, calib, tracks); the child is not
guarded in-process, so the strace audit of the production run covers its opens. Outputs go to OUT inside the run
folder (role own) and are registered with guard.register_output, so the run's provenance ledger lists them.

The venv: env GMG_MP_PYTHON, default <DATA>/mpvenv/bin/python (created with
  uv venv --python /usr/bin/python3.12 <DATA>/mpvenv
  uv pip install --python <DATA>/mpvenv/bin/python mediapipe==0.10.14 opencv-python-headless numpy scipy).
hands_mp.py runs with its own defaults (a_offset 1, legacy API, greedy linker): the settings of the existing sweep.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time

import numpy as np

from gmg import guard

# MediaPipe hand joints -> bones (pipeline/recon_mesh.BONES, copied so this module does not import the pipeline)
BONES = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8), (5, 9), (9, 10), (10, 11), (11, 12),
         (9, 13), (13, 14), (14, 15), (15, 16), (13, 17), (0, 17), (17, 18), (18, 19), (19, 20)]


def venv_python():
    return os.environ.get('GMG_MP_PYTHON', os.path.join(guard.CFG['data'], 'mpvenv', 'bin', 'python'))


def hands_mp_script():
    return os.path.join(guard.CFG['repo'], 'pipeline', 'hands_mp.py')


def run_hands(split, ep, video_a, depth, calib, poses, out, log=None):
    """Run pipeline/hands_mp.py for one episode in the MediaPipe venv. Returns the realpath of OUT/hands.npz."""
    if split not in ('public', 'eval'):
        raise ValueError(split)
    vid = guard.open_input(video_a, 'video')
    dep = guard.open_input(depth, 'depth')
    cal = guard.open_input(calib, 'calib')
    pos = guard.open_input(poses, 'tracks')
    if os.path.basename(cal) != 'calib.json':
        raise ValueError(f'hands_mp.py reads <t3>/calib.json; calib is {cal}')
    run = guard.run_dir()
    out = os.path.realpath(out)
    if not run or not (out + '/').startswith(run + '/'):
        raise guard.GuardError(f'hands_cpu: output {out} is not inside the run folder {run}')
    os.makedirs(out, exist_ok=True)
    py = venv_python()
    cmd = [py, '-I', hands_mp_script(), '--ep', str(int(ep)), '--split', split, '--t3', os.path.dirname(cal),
           '--depth', dep, '--poses', pos, '--video_a', vid, '--out', out]
    t0 = time.time()
    env = {k: v for k, v in os.environ.items() if k in ('PATH', 'HOME', 'LANG', 'LC_ALL', 'TMPDIR')}
    env.update(OMP_NUM_THREADS=os.environ.get('OMP_NUM_THREADS', '2'), PYTHONDONTWRITEBYTECODE='1')
    res = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=out)
    if log:
        with open(log, 'a') as f:
            f.write(res.stdout[-20000:])
            f.write(res.stderr[-20000:])
    if res.returncode != 0:
        raise RuntimeError(f'hands_mp.py ep{ep} failed ({res.returncode}): {res.stderr[-2000:]}')
    paths = []
    for name in ('hands.npz', 'hands_log.json', 'hands_overlay.jpg'):
        p = os.path.join(out, name)
        if os.path.exists(p):
            paths.append(guard.register_output(p))
    guard.constant('hands_mp_a_offset', 1, 'generic:hands_mp.py default (stereo frame k pairs with cam_a frame k+1)')
    info = dict(sec=round(time.time() - t0, 1), cmd=[os.path.basename(c) if i == 0 else c for i, c in enumerate(cmd)])
    with open(os.path.join(out, 'hands_run.json'), 'w') as f:
        json.dump(info, f)
    return os.path.join(out, 'hands.npz')


def segments(hands_path, W_C, hand_r, arm_r, arm_len, role='own'):
    """Per frame t: (A (m,3), B (m,3), r (m,)) capsule segments in the camera coordinates of frame t: the 21 hand
    bones (radius hand_r) and a forearm segment of length arm_len from the wrist away from the middle-finger knuckle
    (radius arm_r), as pipeline/recon_mesh.hand_segments (obs_points.py)."""
    H = guard.load_npz(hands_path, role, keys=['joints_left', 'joints_right', 'valid_left', 'valid_right'])
    H = {k: np.asarray(H[k]) for k in ('joints_left', 'joints_right', 'valid_left', 'valid_right')}
    out = []
    for t in range(len(W_C)):
        C_W = np.linalg.inv(W_C[t])
        A, B, r = [], [], []
        for side in ('left', 'right'):
            if t >= len(H[f'valid_{side}']) or not H[f'valid_{side}'][t]:
                continue
            J = H[f'joints_{side}'][t].astype(np.float64) @ C_W[:3, :3].T + C_W[:3, 3]
            if not np.all(np.isfinite(J)):
                continue
            for i, j in BONES:
                A.append(J[i]); B.append(J[j]); r.append(hand_r)
            d = J[0] - J[9]
            d /= max(np.linalg.norm(d), 1e-9)
            A.append(J[0]); B.append(J[0] + arm_len * d); r.append(arm_r)
        out.append((np.array(A).reshape(-1, 3), np.array(B).reshape(-1, 3), np.array(r)))
    return out


if __name__ == '__main__':
    print(venv_python(), hands_mp_script(), file=sys.stderr)
