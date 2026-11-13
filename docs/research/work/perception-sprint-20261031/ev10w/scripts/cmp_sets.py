"""Set comparison of two piece directories (order-free): each piece of A matched to the piece of B with the smallest
vertex-set Hausdorff distance; also whether the .obj bytes are equal for the matched pair."""
import sys, glob, json, numpy as np, trimesh, hashlib
from scipy.spatial import cKDTree
a, b = sys.argv[1:3]; out = {}
for n in ('blue_cup', 'beige_cup'):
    fa, fb = sorted(glob.glob(f'{a}/{n}/piece_*.obj')), sorted(glob.glob(f'{b}/{n}/piece_*.obj'))
    VA = [np.asarray(trimesh.load(x, process=False).vertices) for x in fa]; VB = [np.asarray(trimesh.load(y, process=False).vertices) for y in fb]
    H = lambda A, B: max(cKDTree(B).query(A)[0].max(), cKDTree(A).query(B)[0].max())
    best = []; same_bytes = 0; same_pos = 0
    for i, A in enumerate(VA):
        d = [H(A, B) for B in VB]; j = int(np.argmin(d)); best.append(d[j] * 1e3)
        same_bytes += open(fa[i], 'rb').read() == open(fb[j], 'rb').read(); same_pos += (i == j)
    out[n] = dict(count=[len(fa), len(fb)], max_matched_hausdorff_mm=float(max(best)), byte_equal_matched=int(same_bytes), same_index=int(same_pos))
print(json.dumps(out))
