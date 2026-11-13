"""Selected frames of a store depth cache by HTTP range read (no full download).
Usage: python -I depth_frames.py SPLIT EP f0,f1,... OUT.npy  -> (k,H,W) float32 metres, 0 = invalid; prints header info."""
import sys, ast, json, time
import numpy as np
from huggingface_hub import HfFileSystem
split, ep, frames, out = sys.argv[1], int(sys.argv[2]), [int(x) for x in sys.argv[3].split(',')], sys.argv[4]
p = f'datasets/aebatirel/v2d-store/cache/depth/{split}/ep{ep}/depths_fs0.5.npy'
fs = HfFileSystem(); size = fs.info(p)['size']; t0 = time.time()
with fs.open(p, 'rb', block_size=1 << 20) as f:
    head = f.read(16); assert head[:6] == b'\x93NUMPY', head
    major = head[6]; pre = 10 if major == 1 else 12
    hl = int.from_bytes(head[8:10], 'little') if major == 1 else int.from_bytes(head[8:12], 'little')
    off = pre + hl; f.seek(0); hdr = f.read(off)
    d = ast.literal_eval(hdr[pre:].decode('latin1').strip())
    assert d['descr'] == '<f4' and not d['fortran_order'], d
    N, H, W = d['shape']; assert size == off + N * H * W * 4
    arr = []
    for k in frames:
        f.seek(off + k * H * W * 4); arr.append(np.frombuffer(f.read(H * W * 4), '<f4').reshape(H, W).copy())
np.save(out, np.stack(arr))
print(json.dumps(dict(split=split, ep=ep, shape=[N, H, W], header_len=off, bytes=size, frames=frames, secs=round(time.time() - t0, 1),
                      valid_frac=[round(float((a > 0).mean()), 4) for a in arr],
                      p5_p50_p95=[[round(float(x), 3) for x in np.percentile(a[a > 0], [5, 50, 95])] for a in arr])))
