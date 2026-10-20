# Stage C3: write the MuJoCo-capped version of a hull set (what SolverMuJoCo actually collides). For each hull:
# float32 vertices (as newton stores them) + CoACD faces -> one-mesh MuJoCo 3.8.1 model with maxhullvert 64 ->
# collider = vertices listed in mesh_graph (vert_globalid). MuJoCo re-frames the mesh, so the vertex order is checked
# (pairwise distances of the processed vertices must match the input ones) before mapping back to the input frame.
# usage: c3_capset.py OUTDIR SRC1[,SRC2]   (object resolved in the first source dir that has it, like y_ud.py)
import sys, os, numpy as np, mujoco
from scipy.spatial import ConvexHull
out, srcs = sys.argv[1], sys.argv[2].split(','); os.makedirs(out, exist_ok=True)
NAMES = ['white_pot_lid', 'white_pot', 'mini_sweeper', 'plastic_dish_rack', 'blue_cup', 'beige_cup']
def cap(v, f):
    v32 = np.asarray(v, np.float32)
    xml = ('<mujoco><asset><mesh name="m" maxhullvert="64" vertex="' + ' '.join(repr(float(x)) for x in v32.ravel()) +
           '" face="' + ' '.join(str(int(i)) for i in np.asarray(f).ravel()) + '"/></asset><worldbody><geom type="mesh" mesh="m"/>'
           '</worldbody></mujoco>')
    m = mujoco.MjModel.from_xml_string(xml)
    nv = m.mesh_vertnum[0]; mv = m.mesh_vert[m.mesh_vertadr[0]:][:nv].astype(np.float64)
    g = m.mesh_graph[m.mesh_graphadr[0]:]; k = g[0]; gid = g[2 + k:2 + 2 * k]
    w = v32.astype(np.float64)
    assert nv == len(w), (nv, len(w))
    i = np.arange(min(nv, 50)); j = (i * 7 + 3) % nv
    assert np.allclose(np.linalg.norm(mv[i] - mv[j], axis=1), np.linalg.norm(w[i] - w[j], axis=1), atol=2e-6)
    return w[gid]
for n in NAMES:
    src = next((s for s in srcs if os.path.exists(f'{s}/{n}.npz')), None)
    if src is None: continue
    d = np.load(f'{src}/{n}.npz'); hs = []; loss = []; skipped = 0
    for i in range(int(d['n'])):
        v = d[f'v{i}']
        try: h = ConvexHull(v)
        except Exception: skipped += 1; continue
        if h.volume < 1e-12: skipped += 1; continue
        f = d[f'f{i}'] if f'f{i}' in d else h.simplices
        c = cap(v, f); hs.append(c); e = ConvexHull(c).equations
        loss.append(((v[h.vertices] @ e[:, :3].T + e[:, 3]).max(1)).max() * 1e3)
    np.savez(f'{out}/{n}.npz', n=len(hs), **{f'v{i}': c for i, c in enumerate(hs)})
    loss = np.array(loss)
    print(f'{out.split("/")[-1]:8s} {n:18s} from {src.split("work/")[-1]:24s} hulls {len(hs):5d} (skipped {skipped}) '
          f'cap loss mm median {np.median(loss):.2f} p90 {np.percentile(loss, 90):.2f} max {loss.max():.2f}', flush=True)
