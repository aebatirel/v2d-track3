# Stage C3: the REAL MuJoCo 3.8.1 maxhullvert=64 cap (as newton's SolverMuJoCo passes it) on stored CoACD hulls,
# replacing the greedy emulation of B7/B18 [E]. Per hull: compile a one-mesh model (vertex + face, maxhullvert 64),
# read the collision hull from mesh_graph (vert_globalid), and measure how far the uncapped hull's vertices lie
# outside the capped hull (mm). Hulls < 1e-12 m3 are skipped (they are screened out anyway, C20).
import sys, numpy as np, mujoco
sys.path.insert(0, '/Users/aebatirel/Documents/Code/v2d-research/work/19/b'); from common import load_hulls, cap_hull
from scipy.spatial import ConvexHull
def real_cap(v, f):
    xml = ('<mujoco><asset><mesh name="m" maxhullvert="64" vertex="' + ' '.join('%.9g' % x for x in v.ravel()) +
           '" face="' + ' '.join(str(int(i)) for i in f.ravel()) + '"/></asset><worldbody><geom type="mesh" mesh="m"/>'
           '</worldbody></mujoco>')
    m = mujoco.MjModel.from_xml_string(xml)
    va = m.mesh_vertadr[0]; nv = m.mesh_vertnum[0]; mv = m.mesh_vert[va:va + nv].astype(np.float64)
    ga = m.mesh_graphadr[0]; g = m.mesh_graph[ga:]; numvert = g[0]; gid = g[2 + numvert:2 + 2 * numvert]
    return mv, mv[gid]
W = '/Users/aebatirel/Documents/Code/v2d-research/work/19/b/'
for lab, d in [a.split('=') for a in sys.argv[1:]]:
    for n in ['white_pot_lid', 'white_pot', 'mini_sweeper', 'plastic_dish_rack', 'blue_cup', 'beige_cup']:
        import os
        if not os.path.exists(f'{W}{d}/{n}.npz'): continue
        z = np.load(f'{W}{d}/{n}.npz'); nh = int(z['n']) if 'n' in z else None
        hv = load_hulls(f'{W}{d}/{n}.npz'); real, emu, nvc, over = [], [], [], 0
        for i, v in enumerate(hv):
            try:
                h = ConvexHull(v)
                if h.volume < 1e-12: continue
            except Exception: continue
            f = h.simplices; mv, cv = real_cap(v, f); nvc.append(len(cv))
            full = mv[ConvexHull(mv).vertices]; e = ConvexHull(cv).equations
            real.append(((full @ e[:, :3].T + e[:, 3]).max(1)).max() * 1e3)
            if len(ConvexHull(v).vertices) > 64: over += 1
            c = cap_hull(v); e2 = ConvexHull(c).equations; full2 = v[ConvexHull(v).vertices]
            emu.append(((full2 @ e2[:, :3].T + e2[:, 3]).max(1)).max() * 1e3)
        real, emu = np.array(real), np.array(emu)
        print(f'{lab:5s} {n:18s} hulls {len(real):4d} (>64 v: {over:4d}; capped nvert max {max(nvc)}) | REAL loss mm median {np.median(real):.2f} p90 {np.percentile(real,90):.2f} max {real.max():.2f} | emu median {np.median(emu):.2f} p90 {np.percentile(emu,90):.2f} max {emu.max():.2f}', flush=True)
