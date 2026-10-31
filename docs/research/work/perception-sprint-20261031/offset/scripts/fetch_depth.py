"""Fetch a fixed grid of frames (48, evenly spaced, frame 0 included) of OUR stereo depth cache for one public episode
from the HF store by HTTP range reads (no full download), downsample to half resolution [::2, ::2] (the resolution of
det_f0 and the F1 test), store float16. GT-free input (our FoundationStereo depth). Usage: python -I fetch_depth.py OUT EP..."""
import json, os, sys, time, hashlib
import numpy as np
from huggingface_hub import HfFileSystem
out = sys.argv[1]; eps = [int(e) for e in sys.argv[2:]]
fs = HfFileSystem()
for ep in eps:
    d = f'{out}/ep{ep}'; os.makedirs(d, exist_ok=True)
    if os.path.exists(f'{d}/depth_grid.npz'):
        print('skip', ep); continue
    t0 = time.time(); p = f'datasets/aebatirel/v2d-store/cache/depth/public/ep{ep}/depths_fs0.5.npy'
    for attempt in range(6):
        try:
            f = fs.open(p, 'rb', block_size=1 << 22)
            hdr = f.read(128); assert hdr[:6] == b'\x93NUMPY'
            meta = eval(hdr[10:128].decode('latin1'))
            T, Hh, Ww = meta['shape']; assert meta['descr'] == '<f4' and hdr[6] == 1 and hdr[8] + 256 * hdr[9] == 118
            frames = np.unique(np.round(np.linspace(0, T - 1, 48)).astype(int))
            D = np.zeros((len(frames), Hh // 2, Ww // 2), np.float16); sha0 = None
            for k, i in enumerate(frames):
                f.seek(128 + i * Hh * Ww * 4); b = f.read(Hh * Ww * 4); assert len(b) == Hh * Ww * 4
                a = np.frombuffer(b, '<f4').reshape(Hh, Ww)
                if i == 0:
                    sha0 = hashlib.sha256(a.tobytes()).hexdigest()
                D[k] = a[::2, ::2].astype(np.float16)
            break
        except Exception as e:  # noqa: BLE001
            print('retry', ep, attempt, repr(e)[:200], flush=True); time.sleep(20 * (attempt + 1))
    else:
        sys.exit(f'ep{ep}: failed')
    np.savez(f'{d}/depth_grid.npz', frames=frames, depth=D, T=T)
    json.dump(dict(ep=ep, store_path=p, shape_full=[T, Hh, Ww], frames=frames.tolist(), frame0_sha256_full=sha0,
                   seconds=round(time.time() - t0, 1)), open(f'{d}/depth_grid.json', 'w'))
    print(ep, T, len(frames), round(time.time() - t0, 1), 's', flush=True)
