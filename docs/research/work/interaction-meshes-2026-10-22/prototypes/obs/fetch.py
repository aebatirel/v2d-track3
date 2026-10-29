# Fetch every 2nd frame of our own public-episode depth cache (HF store) by HTTP range requests, store float16
# (0.5 mm step at 0.6 m) to save disk. Writes depth/ep<E>_s2.npy; poses/hands subsampled to match by sub_inputs.py.
import sys, subprocess, numpy as np, os
E = int(sys.argv[1]); N = int(sys.argv[2])
U = f'https://huggingface.co/datasets/aebatirel/v2d-store/resolve/main/cache/depth/public/ep{E}/depths_fs0.5.npy'
O = f'/tmp/claude-0/-home-user-v2d-track3/8c892c5e-fd7c-57aa-abef-68d2af098e4f/scratchpad/interact/obs/depth'; os.makedirs(O, exist_ok=True)
fr = list(range(0, N, 2)); FS = 1000 * 1600 * 4
out = np.lib.format.open_memmap(f'{O}/ep{E}_s2.npy.part', 'w+', np.float16, (len(fr), 1000, 1600))
for i, t in enumerate(fr):
    s = 128 + t * FS
    for k in range(4):
        b = subprocess.run(['curl', '-sS', '-L', '-r', f'{s}-{s + FS - 1}', U], capture_output=True).stdout
        if len(b) == FS:
            break
    assert len(b) == FS, (t, len(b))
    out[i] = np.frombuffer(b, np.float32).reshape(1000, 1600).astype(np.float16)
    if i % 20 == 0:
        print(E, i, len(fr), flush=True)
out.flush(); del out; os.rename(f'{O}/ep{E}_s2.npy.part', f'{O}/ep{E}_s2.npy'); print('done', E)
