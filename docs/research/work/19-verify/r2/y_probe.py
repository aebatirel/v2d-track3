# Run newton 1.2.0 add_urdf with FlashCHORD's flags + FlashCHORD's own _decompose_object_collision (source extracted
# verbatim from the pinned scene/objects.py) on the probe URDF; list shapes before/after. CPU only.
import os, sys, ast, numpy as np
W = '/Users/aebatirel/Documents/Code/v2d-research/work/19'
sys.path[:0] = [f'{W}/shim', '/Users/aebatirel/Documents/Code/v2d-research/work/15-verify/pylib11']
os.environ['FLASH_CHORD_CACHE_DIR'] = '/Users/aebatirel/Documents/Code/v2d-research/work/19-verify/r2/cache_probe'
import warp as wp; wp.config.log_level = wp.LOG_WARNING if hasattr(wp, 'LOG_WARNING') else None
import newton
src = open(f'{W}/src/src_flash_chord_scene_objects.py').read()
fn = next(n for n in ast.parse(src).body if isinstance(n, ast.FunctionDef) and n.name == '_decompose_object_collision')
g = {'np': np, 'newton': newton, 'ShapeSpan': object}; exec(compile(ast.Module([fn], []), 'objects.py', 'exec'), g)
class Span:  # minimal ShapeSpan stand-in (scene/collision.py ShapeSpan.ids())
    def __init__(s, a, b): s.a, s.b = a, b
    def ids(s): return range(s.a, s.b)
b = newton.ModelBuilder()
try:
    newton.solvers.SolverMuJoCo.register_custom_attributes(b); print('mujoco custom attrs registered')
except Exception as e: print('register_custom_attributes failed:', type(e).__name__, e)
b.add_urdf(source=sys.argv[1], floating=True, enable_self_collisions=False, collapse_fixed_joints=True, ignore_inertial_definitions=False)
col = int(newton.ShapeFlags.COLLIDE_SHAPES)
def dump(tag):
    print(f'--- {tag}: bodies={b.body_count} shapes={b.shape_count} mass={[round(float(m),3) for m in b.body_mass]}')
    for s in range(b.shape_count):
        src_ = b.shape_source[s]; nv = len(src_.vertices) if src_ is not None and hasattr(src_, 'vertices') else '-'
        mhv = getattr(src_, 'maxhullvert', '-') if src_ is not None else '-'
        print(f'  shape {s:2d} body={b.shape_body[s]} type={newton.GeoType(int(b.shape_type[s])).name:10s} collide={bool(int(b.shape_flags[s]) & col)!s:5s} '
              f'nverts={nv} maxhullvert={mhv} label={b.shape_label[s] if hasattr(b, "shape_label") else ""}')
dump('after add_urdf')
n = g['_decompose_object_collision'](b, Span(0, b.shape_count))
print('new hulls', n); dump('after FlashCHORD decomposition')
print('collision filter pairs', len(b.shape_collision_filter_pairs)); print('cache files', sorted(os.listdir('/Users/aebatirel/Documents/Code/v2d-research/work/19-verify/r2/cache_probe/convex')))
# inflation of the hulls made from the colour-split cube (centre (0,0.1,0), half 15 mm) and the 2-geometry GLB boxes
def out_of_box(v, c, h): return 1000 * (np.abs(v - np.asarray(c)) - h).max()
for s in range(b.shape_count):
    if int(b.shape_flags[s]) & col and int(b.shape_type[s]) == int(newton.GeoType.MESH):
        v = np.asarray(b.shape_source[s].vertices)
        c = v.mean(0)
        if abs(c[1] - 0.1) < 0.03: print(f'  hull {s}: cube-split hull, max outside cube = {out_of_box(v,(0,0.1,0),0.015):+.2f} mm')
        elif c[0] > 0.08: print(f'  hull {s}: glb box hull centre x={c[0]:.3f}, max outside its box = {min(out_of_box(v,(0.1,0,0),0.01), out_of_box(v,(0.15,0,0),0.01)):+.2f} mm')
