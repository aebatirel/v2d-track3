"""Run CoACD exactly as FlashCHORD does (newton loader + flash_chord convex_decompose, own cache dir) for one object."""
import sys, os, numpy as np, time
from newton._src.utils.mesh import load_meshes_from_file
sys.path.insert(0, sys.argv[1])
from flash_chord.assets.mesh import convex_decompose
assets, cache, out, o = sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
ms = load_meshes_from_file(f'{assets}/mesh/{o}/{o}.glb', scale=np.ones(3), maxhullvert=64)
t0 = time.time()
for k, m in enumerate(ms):
    H = convex_decompose(np.asarray(m.vertices), np.asarray(m.indices).reshape(-1, 3), cache_dir=cache)
    np.savez(f'{out}/{o}_{k}.npz', n=np.int64(len(H)), **{f'v{i}': h.vertices for i, h in enumerate(H)}, **{f'f{i}': h.faces for i, h in enumerate(H)})
    print(o, k, len(H), 'hulls', round(time.time() - t0), 's', flush=True)
