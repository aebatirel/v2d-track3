import sys, glob, importlib.util, numpy as np, trimesh
sys.path.insert(0, '/home/user/v2d-track3/pipeline')
from collision_decomp import SignedDistance
spec = importlib.util.spec_from_file_location('gap', sys.argv[1]); 
src = open(sys.argv[1]).read(); hm = src[src.index('def heightmap'):src.index('def analyse')]
spec2 = importlib.util.spec_from_file_location('intrusion', '/home/user/v2d-track3/tools/intrusion.py'); I = importlib.util.module_from_spec(spec2); spec2.loader.exec_module(I)
exec(hm)
UA = I.Union(sorted(glob.glob('/home/user/v2d-track3/meshes/carve/ev10/blue_cup/piece_*.obj')))
bB = trimesh.load('/home/user/v2d-track3/meshes/library_v3/blue_cup.glb', force='mesh', process=False); bB = trimesh.Trimesh(bB.vertices, bB.faces, process=True); sd = SignedDistance(bB)
for tag, ins, lo, hi in (('A', lambda X: UA.depth_lb(X) > 0, UA.alo, UA.ahi), ('B', lambda X: sd(X, 0.05) < 0, bB.bounds[0], bB.bounds[1])):
    xs, ys, H = heightmap(ins, lo, hi); gx, gy = np.meshgrid(xs, ys, indexing='ij'); r = np.hypot(gx - 0.0025, gy - 0.004)
    print(tag, ' '.join(f'r{a:.0f}:{np.nanmedian(H[(r >= a/1000) & (r < a/1000 + 0.003)])*1e3:.0f}/{np.isfinite(H[(r >= a/1000) & (r < a/1000 + 0.003)]).mean():.2f}' for a in range(0, 57, 3)))
