# Stage C end-to-end loader check: newton 1.2.0 add_urdf with FlashCHORD's flags + FlashCHORD's own
# _decompose_object_collision (verbatim from the pinned scene/objects.py, as in a_probe.py) on a split asset URDF.
# Reports shapes before/after, hulls per collision mesh, mass, wall time, and compares with stage B's direct calls.
# usage: c_e2e.py <urdf> <stageB_hull_dir_or_->   (env FLASH_CHORD_CACHE_DIR set by caller)
import os, sys, ast, time, glob, numpy as np
W = '/Users/aebatirel/Documents/Code/v2d-research/work/19'
sys.path[:0] = [f'{W}/shim', '/Users/aebatirel/Documents/Code/v2d-research/work/15-verify/pylib11']
import warp as wp
import newton
src = open(f'{W}/src/src_flash_chord_scene_objects.py').read()
fn = next(n for n in ast.parse(src).body if isinstance(n, ast.FunctionDef) and n.name == '_decompose_object_collision')
g = {'np': np, 'newton': newton, 'ShapeSpan': object}; exec(compile(ast.Module([fn], []), 'objects.py', 'exec'), g)
class Span:
    def __init__(s, a, b): s.a, s.b = a, b
    def ids(s): return range(s.a, s.b)
b = newton.ModelBuilder()
newton.solvers.SolverMuJoCo.register_custom_attributes(b)
t0 = time.time()
b.add_urdf(source=sys.argv[1], floating=True, enable_self_collisions=False, collapse_fixed_joints=True, ignore_inertial_definitions=False)
col = int(newton.ShapeFlags.COLLIDE_SHAPES)
n0 = b.shape_count
srcs = [(s, len(b.shape_source[s].vertices)) for s in range(n0) if int(b.shape_flags[s]) & col and int(b.shape_type[s]) == int(newton.GeoType.MESH)]
print(f'add_urdf {time.time()-t0:.1f}s: bodies={b.body_count} shapes={n0} colliding mesh shapes={len(srcs)} '
      f'verts={[v for _, v in srcs]} mass={[round(float(m), 4) for m in b.body_mass]}', flush=True)
t1 = time.time(); n = g['_decompose_object_collision'](b, Span(0, n0)); dt = time.time() - t1
hv = [np.asarray(b.shape_source[s].vertices) for s in range(n0, b.shape_count)]
print(f'decomposition {dt:.1f}s: new hulls {n}; colliding shapes now {sum(1 for s in range(b.shape_count) if int(b.shape_flags[s]) & col)}; '
      f'filter pairs {len(b.shape_collision_filter_pairs)}; mass {[round(float(m), 4) for m in b.body_mass]}', flush=True)
nv = [len(v) for v in hv]
print(f'hull vertex counts: median {int(np.median(nv))} max {max(nv)} >64: {sum(x > 64 for x in nv)}', flush=True)
if len(sys.argv) > 2 and sys.argv[2] != '-':
    ref = sorted(glob.glob(f'{sys.argv[2]}/*.npz')); tot = 0
    for p in ref:
        d = np.load(p); tot += int(d['n'])
    print(f'stage B direct calls on the same parts (float64 arrays): {tot} hulls in {len(ref)} files', flush=True)
    allv = np.vstack(hv); bv = np.vstack([np.load(p)[f'v{i}'] for p in ref for i in range(int(np.load(p)['n']))])
    print(f'bbox of hull union: e2e {allv.min(0).round(4)}..{allv.max(0).round(4)} | stage B {bv.min(0).round(4)}..{bv.max(0).round(4)}', flush=True)
np.savez(f'{os.environ["FLASH_CHORD_CACHE_DIR"]}/../e2e_hulls_{os.path.basename(sys.argv[1])}.npz', n=len(hv), **{f'v{i}': v for i, v in enumerate(hv)})
