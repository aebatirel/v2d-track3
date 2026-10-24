"""Hand on plate pictures in the plate's PCA frame (axis1 = long axis, ring at negative axis1; axis3 = plate normal).
Usage: viz.py SRC OBJ HULLS GLB SIDE OUT.png F1,F2,... [--ref] [--title T]
Per frame: top view (axis1, axis2) and side view (axis1, axis3). Gray = object surface samples; colour = hand collision
samples of SIDE within 4 cm of the object (thumb red, index orange, middle green, ring blue, pinky purple, palm black);
big dots = samples within 5 mm of the object's collision pieces. Arrow = world up in the plate frame."""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, trimesh
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from scipy.spatial.transform import Rotation as R
from rlgrasp_lib import ObjGeom, hand_points, load_trace, load_ref, link_world, to_obj

p = argparse.ArgumentParser(); p.add_argument('src'); p.add_argument('obj'); p.add_argument('hulls'); p.add_argument('glb'); p.add_argument('side')
p.add_argument('out'); p.add_argument('frames'); p.add_argument('--ref', action='store_true'); p.add_argument('--title', default='')
a = p.parse_args()
G = ObjGeom(a.hulls, a.glb); src = load_ref(a.src) if a.ref else load_trace(a.src); hp = hand_points(a.side, n=300)
pts, _ = trimesh.sample.sample_surface_even(G.m, 6000, seed=0); OP = G.pca(pts)
COL = {'thumb': 'red', 'index': 'darkorange', 'middle': 'green', 'ring': 'blue', 'pinky': 'purple', 'hand': 'black'}
fr = [int(x) for x in a.frames.split(',')]
fig, axs = plt.subplots(2, len(fr), figsize=(4.2 * len(fr), 7.5), squeeze=False)
for j, f in enumerate(fr):
    op = src['obj'][a.obj][f]; up = G.W @ R.from_quat(op[3:7]).inv().apply([0, 0, 1.0])
    for row, (i, k) in enumerate([(0, 1), (0, 2)]):
        ax = axs[row, j]; ax.scatter(100 * OP[:, i], 100 * OP[:, k], s=0.3, c='0.75')
        for ln, P in hp.items():
            if ln not in src['links']:
                continue
            X = to_obj(op, link_world(src['links'][ln][f], P)); d = G.lb(X)[0]
            near = d < 0.04
            if not near.any():
                continue
            PX = G.pca(X[near]); fi = ln.split('_')[1]; c = COL.get(fi, 'gray')
            ax.scatter(100 * PX[:, i], 100 * PX[:, k], s=0.6, c=c, alpha=0.35)
            con = d[near] <= 0.005
            if con.any():
                ax.scatter(100 * PX[con, i], 100 * PX[con, k], s=7, c=c, edgecolors='k', linewidths=0.2)
        ax.set_aspect('equal'); ax.set_xlim(-13, 10); ax.set_ylim(-10, 9) if row == 0 else ax.set_ylim(-7, 7)
        ax.arrow(7, 5 if row == 0 else 4, 2.5 * up[i], 2.5 * up[k], head_width=0.5, color='k')
        ax.set_xlabel(f'axis{i + 1} (cm)'); ax.set_ylabel(f'axis{k + 1} (cm)')
        ax.set_title(f'f{f} {"top" if row == 0 else "side"} view' + (f' {a.title}' if a.title and row == 0 else ''), fontsize=9)
plt.tight_layout(); plt.savefig(a.out, dpi=70); print('wrote', a.out)
