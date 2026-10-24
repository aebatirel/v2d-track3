# DIAGNOSTIC with GROUND TRUTH (mocap; analysis after inference). Per-frame board state in ep24 / objects in ep31.
import sys, json, numpy as np, pyarrow.parquet as pq, trimesh
from scipy.spatial.transform import Rotation as R
pqf, every = sys.argv[1], int(sys.argv[2]); meshes = dict(a.split('=') for a in sys.argv[3:])
t = pq.read_table(pqf); rows = t.column('observation.objects').to_pylist(); T = len(rows)
names = [o['name'] for o in rows[0]]
P = {n: np.array([[o['pose'] for o in r if o['name']==n][0] for r in rows]) for n in names}
V = {}
for n in names:
    m = trimesh.load(meshes[n], force='mesh'); v = m.vertices
    if len(v) > 20000: v = v[np.random.default_rng(0).choice(len(v), 20000, replace=False)]
    V[n] = v
def world(n, f):
    p = P[n][f]; q = p[[4,5,6,3]]; return R.from_quat(q).apply(V[n]) + p[:3], R.from_quat(q)
low = {n: np.array([world(n,f)[0][:,2].min() for f in range(T)]) for n in names}
table = min(np.percentile(low[n], 5) for n in names)
print('frames', T, 'table z (5th pct of lowest point)', round(table,4))
out = {}
for n in names:
    rec = []
    for f in range(T):
        w, r = world(n, f)
        thin = r.apply([1,0,0]); tilt = np.degrees(np.arccos(abs(thin[2])))  # angle of the board plane normal from vertical
        rec.append(dict(f=f, x=P[n][f][0], y=P[n][f][1], z=P[n][f][2], low=w[:,2].min()-table, high=w[:,2].max()-table, tilt=tilt))
    out[n] = rec
for f in range(0, T, every):
    s = f'f{f:3d} '
    for n in names:
        r = out[n][f]; d = np.linalg.norm(P[n][f][:3]-P[n][0][:3])*100
        s += f'| {n[-7:]} disp {d:5.1f}cm low {r["low"]*100:5.1f} high {r["high"]*100:5.1f} tilt {r["tilt"]:5.1f} xy ({r["x"]*100:6.1f},{r["y"]*100:6.1f}) '
    print(s)
json.dump(out, open(sys.argv[0].replace('.py', f'_{T}.json'), 'w'))
