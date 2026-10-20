"""Are wooden_piece_1 and wooden_piece_2 the same shape (rigid or mirrored) in their canonical frames?"""
import os, numpy as np, trimesh
from scipy.spatial import cKDTree
from canon import sample_surface
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "t3", "public", "mesh")
def load(n):
    m = trimesh.load(f"{R}/{n}/{n}_visual.glb", force="mesh", process=False)
    return np.asarray(m.vertices, float), np.asarray(m.faces)
A = sample_surface(*load("wooden_piece_1"), 20000, 0)
B = sample_surface(*load("wooden_piece_2"), 20000, 1)
ta = cKDTree(A)
for sx in (1, -1):
    for sy in (1, -1):
        for sz in (1, -1):
            Bm = B * np.array([sx, sy, sz])
            d1 = ta.query(Bm)[0]; d2 = cKDTree(Bm).query(A)[0]
            kind = "rotation" if sx * sy * sz > 0 else "mirror"
            print(f"diag({sx:+d},{sy:+d},{sz:+d}) [{kind:8s}] chamfer_mm={500*(d1.mean()+d2.mean()):.2f}  p90_mm={1000*np.percentile(np.r_[d1,d2],90):.2f}")
