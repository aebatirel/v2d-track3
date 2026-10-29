"""Zero-action start timeline (no ground truth): per frame, each object's displacement from its simulated frame-0
pose and its error to our reference, the nearest hand collision point to the object's collision hulls (per hand),
penetration of each hand into the hulls, object-object hull penetration, lowest hull point vs the table.
Usage: start_timeline.py EP TRACE(zero|zero_r1) REFKIND(ref_gl_ilc|ref_gl_r1_ilc) F_END [EVERY]"""
import sys, os, json, numpy as np, trimesh
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from common import *

ep, tr, refkind, fend = int(sys.argv[1]), sys.argv[2], sys.argv[3], int(sys.argv[4])
every = int(sys.argv[5]) if len(sys.argv) > 5 else 1
d = load_ref(ref_path(ep, refkind)); names = d['names']
Q, L, F = load_trace(tr if tr.endswith('.npz') else f'{run_dir(ep)}/results/glock_public/ep{ep}/{tr}.npz'); tr = os.path.basename(tr).replace('.npz', '')
n = min(len(Q), fend + 1)
HP = {s: hand_points(s, 60) for s in ('left', 'right')}
HB = {s: {b: L.index(f'{s}_sharpa_wave/{b}') for b in HP[s] if f'{s}_sharpa_wave/{b}' in L} for s in HP}
H = {o: Hulls(hull_path(o)) for o in names}
# hull surface samples (object frame) for object-object overlap and lowest point
HS = {}
for o in names:
    pts = [trimesh.sample.sample_surface(h, max(20, int(4000 * h.area / sum(x.area for x in H[o].H))), seed=k)[0] for k, h in enumerate(H[o].H)]
    HS[o] = np.concatenate(pts + [h.vertices for h in H[o].H])
oi = {o: obj_index(L, o) for o in names}
rows = []
for t in range(n):
    row = dict(f=t)
    for j, o in enumerate(names):
        p, q = Q[t, oi[o], :3], Q[t, oi[o], 3:7]
        row[o] = dict(disp_mm=1000 * np.linalg.norm(p - Q[0, oi[o], :3]), rot_deg=float(rot_deg(q, Q[0, oi[o], 3:7])),
                      err_cm=100 * np.linalg.norm(p - d['OP'][min(t, d['T'] - 1), j]), err_deg=float(rot_deg(q, d['OQ'][min(t, d['T'] - 1), j])),
                      z_low_mm=1000 * (local_to_world(HS[o], p, q)[:, 2].min() - 0.6))
        for s in HP:
            P = np.concatenate([local_to_world(HP[s][b], Q[t, i, :3], Q[t, i, 3:7]) for b, i in HB[s].items()])
            dep, out = H[o].depth(world_to_local(P, p, q))
            row[o][f'{s}_gap_mm'] = 1000 * out.min(); row[o][f'{s}_pen_mm'] = 1000 * dep.max(); row[o][f'{s}_npen'] = int((dep > 0.0005).sum())
        for o2 in names:
            if o2 == o:
                continue
            p2, q2 = Q[t, oi[o2], :3], Q[t, oi[o2], 3:7]
            dep, out = H[o2].depth(world_to_local(local_to_world(HS[o], p, q), p2, q2))
            row[o][f'in_{o2}_mm'] = 1000 * dep.max(); row[o][f'in_{o2}_frac'] = float((dep > 0.0005).mean()); row[o][f'gap_{o2}_mm'] = 1000 * out.min()
    rows.append(row)
json.dump(rows, open(f'{W}/out/timeline_ep{ep}_{tr}.json', 'w'))
for row in rows[::every]:
    s = f"f{row['f']:3d}"
    for o in names:
        r = row[o]; o2 = [x for x in names if x != o][0]
        s += (f" | {o[:10]} d{r['disp_mm']:6.1f}mm {r['rot_deg']:5.1f}deg e{r['err_cm']:5.1f}cm/{r['err_deg']:5.1f} zlow{r['z_low_mm']:+5.1f}"
              f" L{r['left_gap_mm']:6.0f}/{r['left_pen_mm']:4.1f} R{r['right_gap_mm']:6.0f}/{r['right_pen_mm']:4.1f} in{o2[:5]} {r[f'in_{o2}_mm']:4.1f}mm({100*r[f'in_{o2}_frac']:.1f}%)")
    print(s)
