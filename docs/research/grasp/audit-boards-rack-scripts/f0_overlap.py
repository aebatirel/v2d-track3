"""Frame-0 overlap of the sweeper with the rack in OUR reference (no GT): (a) sweeper surface samples inside the rack's
true mesh (signed distance), (b) inside the rack's CoACD hulls (Newton settings; stored npz), depth = distance to
the hull boundary."""
import sys, numpy as np, trimesh
from scipy.spatial import ConvexHull
from scipy.spatial.transform import Rotation as R
sys.path.insert(0, __file__.rsplit('/', 1)[0]); from refload import load_ref
d = load_ref(sys.argv[1]); lib = sys.argv[2]; hulls = np.load(sys.argv[3]); frames = [int(x) for x in sys.argv[4].split(',')]
ns = d['names']; si, ri = ns.index('mini_sweeper'), ns.index('plastic_dish_rack')
sw = trimesh.load(f'{lib}/mini_sweeper.glb', force='mesh'); rk = trimesh.load(f'{lib}/plastic_dish_rack.glb', force='mesh')
pts, _ = trimesh.sample.sample_surface(sw, 4000, seed=0)
H = [ConvexHull(hulls[k]) for k in hulls.files]
for t in frames:
    w = R.from_quat(d['OQ'][t, si]).apply(pts) + d['OP'][t, si]
    loc = R.from_quat(d['OQ'][t, ri]).inv().apply(w - d['OP'][t, ri])
    sd = trimesh.proximity.signed_distance(rk, loc)  # + inside
    depth = np.zeros(len(loc))
    for h in H:
        e = loc @ h.equations[:, :3].T + h.equations[:, 3]  # <=0 inside
        inside = (e <= 0).all(1); depth[inside] = np.maximum(depth[inside], -e[inside].max(1))
    low = w[:, 2].min()
    print(f'f{t}: sweeper samples inside rack MESH {np.mean(sd > 0.0005)*100:.1f}% max {sd.max()*1000:.1f} mm | inside rack HULLS {np.mean(depth > 0.0005)*100:.1f}% max {depth.max()*1000:.1f} mm p95 {np.percentile(depth[depth>0],95)*1000 if (depth>0).any() else 0:.1f} | sweeper lowest z {low:.4f}')
