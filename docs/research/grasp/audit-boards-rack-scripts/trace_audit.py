"""Zero-action trace audit: per object sim vs reference, lift, and hand-link proximity (no ground truth)."""
import sys, json, argparse, numpy as np, trimesh
from scipy.spatial.transform import Rotation as R
sys.path.insert(0, __file__.rsplit('/', 1)[0]); from refload import load_ref
p = argparse.ArgumentParser(); p.add_argument('ref'); p.add_argument('trace'); p.add_argument('lib'); p.add_argument('--every', type=int, default=5)
p.add_argument('--json'); p.add_argument('--near', type=float, default=0.02)
a = p.parse_args()
d = load_ref(a.ref); names = d['names']; T = d['T']
z = np.load(a.trace); L = [str(x) for x in z['labels']]; Q = z['q'].astype(float); n = min(len(Q), T)
meshes = {o: trimesh.load(f'{a.lib}/{o}.glb', force='mesh') for o in names}
pqs = {o: trimesh.proximity.ProximityQuery(meshes[o]) for o in names}
links = [i for i, l in enumerate(L) if '_sharpa_wave/' in l]
lname = [L[i].split('/')[-1] for i in links]
out = {}
for j, o in enumerate(names):
    oi = next(i for i, l in enumerate(L) if l == f'track3_{o}/object')
    sp, sq = Q[:n, oi, :3], Q[:n, oi, 3:7]
    rp, rq = d['OP'][:n, j], d['OQ'][:n, j]
    ep = 100 * np.linalg.norm(sp - rp, axis=1)
    er = np.degrees((R.from_quat(sq) * R.from_quat(rq).inv()).magnitude())
    slift = 100 * (sp[:, 2] - sp[0, 2]); rlift = 100 * (rp[:, 2] - rp[0, 2])
    sdisp = 100 * np.linalg.norm(sp - sp[0], axis=1); srot0 = np.degrees((R.from_quat(sq) * R.from_quat(sq[0]).inv()).magnitude())
    # hand proximity: link origins to the surface (unsigned) per frame
    W = Q[:n][:, links, :3]
    loc = np.einsum('tij,tkj->tki', R.from_quat(sq).inv().as_matrix(), W - sp[:, None])
    dist = np.abs(pqs[o].signed_distance(loc.reshape(-1, 3))).reshape(n, len(links))
    near = {}
    for s in ('left', 'right'):
        idx = [k for k, nm in enumerate(lname) if nm.startswith(s)]
        near[s] = [[lname[k][len(s) + 1:] for k in idx if dist[t, k] < a.near] for t in range(n)]
    out[o] = dict(err_cm=ep.tolist(), err_deg=er.tolist(), sim_lift=slift.tolist(), ref_lift=rlift.tolist(), sim_disp=sdisp.tolist(), sim_rot0=srot0.tolist(),
                  near=near, mind={s: [float(min(dist[t, k] for k, nm in enumerate(lname) if nm.startswith(s))) for t in range(n)] for s in ('left', 'right')})
    print(f'== {o}: max sim lift {slift.max():.1f} cm (ref {rlift.max():.1f}); frames err<3cm {np.mean(ep<3):.2f}; first frame err>3cm: {int(np.argmax(ep>3)) if (ep>3).any() else None}')
    for t in range(0, n, a.every):
        nl = {s: near[s][t] for s in near if near[s][t]}
        print(f'  f{t:3d} err {ep[t]:5.1f}cm {er[t]:5.1f}deg | sim lift {slift[t]:5.1f} ref lift {rlift[t]:5.1f} | sim disp {sdisp[t]:5.1f} rot {srot0[t]:5.1f} | minD L {100*out[o]["mind"]["left"][t]:5.1f} R {100*out[o]["mind"]["right"][t]:5.1f} | near {nl}')
if a.json:
    json.dump(out, open(a.json, 'w'))
