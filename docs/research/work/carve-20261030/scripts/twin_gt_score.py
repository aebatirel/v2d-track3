"""PUBLIC TWINS ONLY, diagnostic after the settle test (2026-10-30): ADD (cm, mean vertex distance over our mesh) of the
reference pose and of the 2 s settled poses (default / carved hulls) against mocap GT at the same frame.
Relative ADD of the guest in the host frame (the reference world frame differs from the mocap frame: absolute ADD
was 13-32 cm for the reference itself). Usage: twin_gt_score.py GT.npz MESHDIR DEF.json CUT.json HOST GUEST"""
import json, sys
import numpy as np, trimesh
gt = np.load(sys.argv[1]); T = gt['T']; gnames = [str(x) for x in gt['names']]
d, c = json.load(open(sys.argv[3])), json.load(open(sys.argv[4]))
host, guest = sys.argv[5], sys.argv[6]          # relative ADD: the reference world frame is not the mocap frame
inv = np.linalg.inv; A = lambda x: np.asarray(x, float)
m = trimesh.load(f'{sys.argv[2]}/{guest}/{guest}.glb', force='mesh'); V = np.asarray(m.vertices)[::max(1, len(m.vertices) // 3000)]
out = {}
for F, fd in d['frames'].items():
    fc = c['frames'][F]; f = int(F); G = inv(T[f, gnames.index(host)]) @ T[f, gnames.index(guest)]
    add = lambda X: round(float(np.linalg.norm((V @ X[:3, :3].T + X[:3, 3]) - (V @ G[:3, :3].T + G[:3, 3]), axis=1).mean() * 100), 2)
    rel = lambda D: inv(A(D[host])) @ A(D[guest])
    out[F] = dict(rel_add_cm=dict(ref=add(rel(fd['T_ref'])), settle_def=add(rel(fd['T_end'])), settle_cut=add(rel(fc['T_end']))))
print(json.dumps(out))
