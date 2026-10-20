# Stage A: does the pinned CoACD 1.0.11 call pass a pre-decomposed convex piece through unchanged?
# Exact FlashCHORD call: run_coacd(threshold=0.05, max_convex_hull=-1, preprocess_mode="auto"); log level info to see preprocessing.
import sys, numpy as np, trimesh
sys.path.insert(0, '/Users/aebatirel/Documents/Code/v2d-research/work/15-verify/pylib11')
import coacd
from scipy.spatial import ConvexHull
coacd.set_log_level(sys.argv[2] if len(sys.argv) > 2 else 'error')
def run(name, v, f):
    v = np.ascontiguousarray(v, np.float64); f = np.ascontiguousarray(f, np.int64).reshape(-1, 3)
    parts = coacd.run_coacd(coacd.Mesh(v, f), threshold=0.05, max_convex_hull=-1, preprocess_mode='auto')
    H = ConvexHull(v); eq = H.equations  # outward planes of the input's own hull
    out = np.vstack([p[0] for p in parts])
    d_out = (out @ eq[:, :3].T + eq[:, 3]).max(axis=1)  # >0: outside input hull (inflation)
    nv = [len(ConvexHull(p[0]).vertices) for p in parts]
    print(f'{name:34s} inV={len(v):6d} manifold_in={trimesh.Trimesh(v,f,process=False).is_watertight!s:5s} hulls={len(parts):3d} '
          f'hullverts={nv[:6]} max_out_mm={1000*d_out.max():+.3f} min_mm={1000*d_out.min():+.3f}', flush=True)
case = sys.argv[1]
if case == 'box':
    m = trimesh.creation.box(extents=(0.12, 0.03, 0.2)); run('box welded 120x30x200mm', m.vertices, m.faces)
if case == 'cyl':
    m = trimesh.creation.cylinder(radius=0.05, height=0.1, sections=24); run('cylinder welded r50 h100 24seg', m.vertices, m.faces)
if case == 'cyl_soup':
    m = trimesh.creation.cylinder(radius=0.05, height=0.1, sections=24); v = m.vertices[m.faces].reshape(-1, 3); f = np.arange(len(v)).reshape(-1, 3)
    run('cylinder SOUP (unwelded) r50 h100', v, f)
if case == 'cyl_big':
    m = trimesh.creation.cylinder(radius=0.05, height=0.1, sections=96); run('cylinder welded 96seg (>64 hull v)', m.vertices, m.faces)
if case == 'plate_soup':
    m = trimesh.creation.box(extents=(0.3, 0.2, 0.003)); v = m.vertices[m.faces].reshape(-1, 3); f = np.arange(len(v)).reshape(-1, 3)
    run('thin plate 300x200x3 SOUP', v, f)
if case == 'plate':
    m = trimesh.creation.box(extents=(0.3, 0.2, 0.003)); run('thin plate 300x200x3 welded', m.vertices, m.faces)
