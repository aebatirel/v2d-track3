"""Find FlashCHORD's cached CoACD hulls for our sim assets: load each mesh exactly as newton's URDF importer does,
compute FlashCHORD's cache key, copy the hulls to OUT/<object>.npz (v_i in the object-local frame)."""
import sys, os, shutil, numpy as np
from newton._src.utils.mesh import load_meshes_from_file
sys.path.insert(0, sys.argv[1])  # flash_chord src
from flash_chord.assets.mesh import _cache_key
assets, cache, out = sys.argv[2], sys.argv[3], sys.argv[4]
os.makedirs(out, exist_ok=True)
params = dict(threshold=0.05, max_convex_hull=-1, preprocess_mode='auto')
for o in sys.argv[5:]:
    p = f'{assets}/mesh/{o}/{o}.glb'
    ms = load_meshes_from_file(p, scale=np.ones(3), maxhullvert=64)
    for k, m in enumerate(ms):
        v = np.asarray(m.vertices); f = np.asarray(m.indices).reshape(-1, 3)
        key = _cache_key(v, f, params)
        hit = os.path.exists(f'{cache}/{key}.npz')
        print(o, k, v.shape, f.shape, key, 'HIT' if hit else 'miss', flush=True)
        if hit:
            shutil.copy(f'{cache}/{key}.npz', f'{out}/{o}_{k}.npz')
