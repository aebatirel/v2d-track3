import sys, numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
sys.path.insert(0, '.')
from lathe_lib import *
import trimesh
L = '/home/user/v2d-track3/meshes/'
items = [('blue_cup v3', L+'library_v3/blue_cup.glb', 2), ('beige_cup v3', L+'library_v3/beige_cup.glb', 2),
         ('beige_cup v3x', L+'library_v3x/beige_cup.glb', 2), ('white_pot v3', L+'library_v3/white_pot.glb', 0),
         ('white_pot_lid v3', L+'library_v3/white_pot_lid.glb', 0), ('water_pitcher v3', L+'library_v3/water_pitcher.glb', 2)]
if len(sys.argv) > 1:
    items = [tuple(a.split('=')[:2]) + (int(a.split('=')[2]),) for a in sys.argv[1:]]
fig, axs = plt.subplots(2, len(items), figsize=(4 * len(items), 8))
for j, (lab, p, ax_i) in enumerate(items):
    m = trimesh.load(p, force='mesh')
    for row, (u, w) in enumerate([(0, 1), (1, 0)]):
        e = np.eye(3)
        n = e[[k for k in range(3) if k != ax_i][w]]
        sec = m.section(plane_origin=m.centroid, plane_normal=n)
        a = axs[row, j]
        if sec is not None:
            for ent in sec.discrete:
                ids = [k for k in range(3) if k != ax_i]
                a.plot(ent[:, ids[u]] * 100, ent[:, ax_i] * 100, 'k-', lw=0.8)
        a.set_aspect('equal'); a.set_title(f'{lab}\nplane normal {np.round(n,0)}', fontsize=8); a.grid(alpha=.3)
        b = m.bodies if hasattr(m, 'bodies') else None
plt.tight_layout(); plt.savefig(sys.argv[0].replace('.py', '') + '_out.png' if len(sys.argv) == 1 else 'out/sec_custom.png', dpi=70)
for lab, p, ax_i in items:
    m = trimesh.load(p, force='mesh')
    print(lab, [(len(b.faces), round(abs(b.volume) * 1e6, 1)) for b in m.split(only_watertight=False)])
