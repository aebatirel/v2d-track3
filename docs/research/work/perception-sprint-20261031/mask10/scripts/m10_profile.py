"""GT-free profile of a nest (eval 10 or any episode): per frame, the outer (blue) cup's centroid height and horizontal
displacement from frame 0 along/on our frame-0 table plane (S12's plane, from pose_opt.json), the beige-minus-blue
height, and the lowest-vertex heights, for several refine outputs. Reads our perception outputs and our meshes only.
Usage: python -I m10_profile.py PLANE_POSE_OPT_JSON OUT_JSON label=DIR [label=DIR ...]"""
import json, sys
import numpy as np
sys.path.insert(0, '/home/user/v2d-track3/pipeline')
import refine

popt, out = sys.argv[1], sys.argv[2]
pl = json.load(open(refine.checked(popt)))['steps']['S12']['plane']
n, d = np.asarray(pl['n'], float), float(pl['d'])
objs = {k: refine.Obj(k, f'/home/user/v2d-track3/meshes/library_v3/{k}.glb') for k in ('blue_cup', 'beige_cup')}
res = {}
for arg in sys.argv[3:]:
    lab, dr = arg.split('=', 1)
    V = np.load(refine.checked(f'{dr}/poses_world_vo.npz'))
    c = {k: V[k][:, :3, :3] @ o.V.mean(0) + V[k][:, :3, 3] for k, o in objs.items()}
    lo = {k: np.array([(o.world(V[k][t]) @ n).min() + d for t in range(len(V[k]))]) for k, o in objs.items()}
    b = c['blue_cup'] - c['blue_cup'][0]
    v = b @ n
    h = np.linalg.norm(b - v[:, None] * n[None], axis=1)
    rel = (c['beige_cup'] - c['blue_cup']) @ n
    res[lab] = dict(blue_v_cm=np.round(v * 100, 2).tolist(), blue_h_cm=np.round(h * 100, 2).tolist(),
                    beige_minus_blue_cm=np.round(rel * 100, 2).tolist(), blue_bottom_cm=np.round(lo['blue_cup'] * 100, 2).tolist(),
                    beige_bottom_cm=np.round(lo['beige_cup'] * 100, 2).tolist())
json.dump(res, open(out, 'w'))
labs = list(res)
T = len(res[labs[0]]['blue_v_cm'])
print('frame | ' + ' | '.join(f'{l}: blue v, h, beige-blue' for l in labs))
for t in list(range(0, T, 5)) + [T - 1]:
    print(f'f{t:3d} | ' + ' | '.join(f'{res[l]["blue_v_cm"][t]:+5.2f} {res[l]["blue_h_cm"][t]:4.2f} {res[l]["beige_minus_blue_cm"][t]:+5.2f}' for l in labs))
