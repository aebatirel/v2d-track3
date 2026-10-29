"""Cross-sections of a mesh in its PCA frame (COM origin) to measure handles, straps and loops.
Usage: slices.py MESH AXIS(0|1|2) POS_CM[,POS_CM...] [OUT_PNG]
Prints, per slice, each closed loop's bbox (cm) in the other two PCA axes, its area and whether it is a hole."""
import sys
import numpy as np
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

mesh, axis, poss = sys.argv[1], int(sys.argv[2]), [float(x) for x in sys.argv[3].split(',')]
out = sys.argv[4] if len(sys.argv) > 4 else None
m = trimesh.load(mesh, force='mesh')
com = m.center_mass if m.is_watertight else m.vertices.mean(0)
_, _, Vt = np.linalg.svd(m.vertices - m.vertices.mean(0), full_matrices=False)
# (no axis flip: same PCA axes as contact_plot.py)
T = np.eye(4); T[:3, :3] = Vt; T[:3, 3] = -Vt @ com
mp = m.copy(); mp.apply_transform(T)          # now in the PCA frame, COM at the origin
other = [i for i in range(3) if i != axis]
fig, axs = plt.subplots(1, len(poss), figsize=(4 * len(poss), 4)) if out else (None, None)
for j, p in enumerate(poss):
    n = np.zeros(3); n[axis] = 1.0
    sec = mp.section(plane_origin=n * p / 100, plane_normal=n)
    if sec is None:
        print(f'slice {p:+.1f} cm: empty'); continue
    print(f'slice pca{axis+1} = {p:+.1f} cm:')
    for d in sec.discrete:
        q = np.asarray(d)[:, other] * 100
        x, y = q[:, 0], q[:, 1]
        area = 0.5 * np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y)
        print(f'   loop bbox pca{other[0]+1} [{x.min():+.1f},{x.max():+.1f}] pca{other[1]+1} [{y.min():+.1f},{y.max():+.1f}]'
              f' size {np.ptp(x):.1f} x {np.ptp(y):.1f} cm, signed area {area:+.1f} cm2')
        if out:
            a = axs[j] if len(poss) > 1 else axs
            a.plot(x, y, '-k', lw=1)
    if out:
        a = axs[j] if len(poss) > 1 else axs
        a.set_aspect('equal'); a.grid(lw=0.3); a.set_title(f'pca{axis+1} = {p:+.1f} cm')
        a.set_xlabel(f'pca{other[0]+1} cm'); a.set_ylabel(f'pca{other[1]+1} cm')
if out:
    fig.tight_layout(); fig.savefig(out, dpi=65)
