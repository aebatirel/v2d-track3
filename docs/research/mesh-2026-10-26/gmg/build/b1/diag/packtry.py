"""Dev diagnostic (B1): packing strategies for a high-genus marching-cubes HULL. No GT."""
import sys, numpy as np, trimesh, fast_simplification, time
m = trimesh.load(sys.argv[1], process=True)
print('in', len(m.faces), m.is_watertight, m.euler_number)
V0, F0 = np.asarray(m.vertices, np.float64), np.asarray(m.faces, np.int64)
def rep(tag, s, t):
    print(f'{tag:28s} faces {len(s.faces):5d} wt {s.is_watertight} euler {s.euler_number} area {s.area / m.area - 1:+.4f} vol {s.volume / m.volume - 1 if s.is_watertight else float("nan"):+.4f} ({time.time()-t:.1f}s)')
# 1. repeated agg 1
t = time.time(); v, f = V0, F0
for i in range(8):
    v, f = fast_simplification.simplify(v, f, target_count=4000, agg=1)
    s = trimesh.Trimesh(v, f, process=True); v, f = np.asarray(s.vertices), np.asarray(s.faces)
    if len(f) <= 4000: break
rep(f'agg1 x{i+1}', s, t)
# 2. Taubin smoothing then agg 3 / 7
for it in (5, 10, 20):
    t = time.time(); sm = m.copy(); trimesh.smoothing.filter_taubin(sm, iterations=it)
    for agg in (3, 7):
        v, f = fast_simplification.simplify(np.asarray(sm.vertices), np.asarray(sm.faces), target_count=4000, agg=agg)
        rep(f'taubin{it} agg{agg}', trimesh.Trimesh(v, f, process=True), t)
# 3. step-wise agg 3 (halve each time)
t = time.time(); v, f = V0, F0; n = len(F0)
while n > 4000:
    n = max(4000, n // 2)
    v, f = fast_simplification.simplify(v, f, target_count=n, agg=3)
    s = trimesh.Trimesh(v, f, process=True); v, f = np.asarray(s.vertices), np.asarray(s.faces); n = len(f)
rep('agg3 halving', s, t)
try:
    import pymeshlab; print('pymeshlab', pymeshlab.__version__)
except Exception as e: print('no pymeshlab', e)
try:
    import open3d; print('open3d', open3d.__version__)
except Exception as e: print('no open3d', e)
