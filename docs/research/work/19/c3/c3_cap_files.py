# Stage C3: real MuJoCo cap loss (as c3_capset.py) and hull-vertex counts for arbitrary hull files. usage: files...
import sys, numpy as np, mujoco
from scipy.spatial import ConvexHull
def cap(v, f):
    v32 = np.asarray(v, np.float32)
    xml = ('<mujoco><asset><mesh name="m" maxhullvert="64" vertex="' + ' '.join(repr(float(x)) for x in v32.ravel()) +
           '" face="' + ' '.join(str(int(i)) for i in np.asarray(f).ravel()) + '"/></asset><worldbody><geom type="mesh" mesh="m"/></worldbody></mujoco>')
    m = mujoco.MjModel.from_xml_string(xml); g = m.mesh_graph[m.mesh_graphadr[0]:]; k = g[0]
    return v32.astype(np.float64)[g[2 + k:2 + 2 * k]]
for fn in sys.argv[1:]:
    d = np.load(fn); loss = []; nv = []
    for i in range(int(d['n'])):
        v = d[f'v{i}']; h = ConvexHull(v)
        if h.volume < 1e-12: continue
        nv.append(len(h.vertices)); c = cap(v, d[f'f{i}'] if f'f{i}' in d else h.simplices); e = ConvexHull(c).equations
        loss.append(((v[h.vertices] @ e[:, :3].T + e[:, 3]).max(1)).max() * 1e3)
    loss, nv = np.array(loss), np.array(nv)
    print(f'{fn.split("work/19/")[-1]:42s} hulls {len(nv):4d} hull-verts median {int(np.median(nv)):3d} >64 {np.mean(nv > 64) * 100:3.0f} % | '
          f'cap loss median {np.median(loss):.2f} p90 {np.percentile(loss, 90):.2f} max {loss.max():.2f} mm', flush=True)
