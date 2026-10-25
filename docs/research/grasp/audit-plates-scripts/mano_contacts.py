"""Human contacts per frame and per contact slot on each object, from our reference parquet (our perception of the
human; no ground truth). Counts active contacts (normal length > 1e-3 and part id = object + 1), per-slot shares over
given frame ranges, and the contact points in the object frame (to see which face/edge and the thumb vs fingers sides).
Slots are labelled in mkref's probe order (tools/contact_slots.py; counts mode: T/I/M/R/P + t tip, D DP, M MCP/MP;
Pa palm). 2026-10-25: earlier versions used the mano_link_names column (MANO link order), which does not describe
mkref's slots (approach3-grasp-taxonomy.md §9)."""
import os, sys, json
import numpy as np, pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as R
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', 'tools'))
from contact_slots import slot_names, short  # noqa: E402
t = pq.read_table(sys.argv[1]); names = t.column('object_body_names')[0].as_py(); ln = [short(n) for n in slot_names(t)]
ab = lambda l: 'Pa' if l == 'palm' else l[0].upper() + {'tip': 't', 'DP': 'D', 'MP': 'M', 'MCP': 'M'}[l.split('_')[1]]  # noqa: E731
T = len(np.array(t.column('robot_left_wrist_position')[0].as_py(), float).reshape(-1, 3))
OP = np.array(t.column('object_body_position')[0].as_py(), float).reshape(T, len(names), 3)
OQ = np.array(t.column('object_body_wxyz')[0].as_py(), float).reshape(T, len(names), 4)[..., [1, 2, 3, 0]]
mode = sys.argv[2]
C = {}
for s in ('left', 'right'):
    n = np.array(t.column(f'mano_{s}_object_contact_normals')[0].as_py(), float).reshape(T, -1, 3)
    pid = np.array(t.column(f'mano_{s}_object_contact_part_ids')[0].as_py()).reshape(T, -1)
    P = np.array(t.column(f'mano_{s}_object_contact_positions')[0].as_py(), float).reshape(T, -1, 3)
    C[s] = (n, pid, P)
if mode == 'counts':
    f0, f1, st = map(int, sys.argv[3:6])
    print('frame | ' + ' | '.join(f'{s}->{o}' for s in C for o in names))
    for f in range(f0, f1, st):
        row = f'{f:4d}'
        for s in C:
            n, pid, P = C[s]
            for j, o in enumerate(names):
                act = (np.linalg.norm(n[f], axis=1) > 1e-3) & (pid[f] == j + 1)
                row += f' | {act.sum():2d} {"".join(ab(l) if a else "" for l, a in zip(ln, act))[:40]:40s}'
        print(row)
else:   # shares over ranges: side obj f0 f1
    s, o, f0, f1 = sys.argv[3], sys.argv[4], int(sys.argv[5]), int(sys.argv[6]); j = names.index(o); n, pid, P = C[s]
    act = (np.linalg.norm(n[f0:f1], axis=2) > 1e-3) & (pid[f0:f1] == j + 1)
    sh = {l: round(float(act[:, k].mean()), 2) for k, l in enumerate(ln)}
    print(json.dumps(dict(side=s, obj=o, frames=[f0, f1], share=sh, mean_active=round(float(act.sum(1).mean()), 2))))
    # contact points in the object frame, per slot (thumb vs fingers vs palm), with object-frame normal direction
    pts = {}
    for k, l in enumerate(ln):
        X = [R.from_quat(OQ[f0 + i, j]).inv().apply(P[f0 + i, k] - OP[f0 + i, j]) for i in range(f1 - f0) if act[i, k]]
        N = [R.from_quat(OQ[f0 + i, j]).inv().apply(n[f0 + i, k]) for i in range(f1 - f0) if act[i, k]]
        if X:
            pts[l] = dict(n=len(X), mean_obj_cm=[round(100 * x, 1) for x in np.mean(X, 0)], mean_normal_obj=[round(float(x), 2) for x in np.mean(N, 0) / max(1e-9, np.linalg.norm(np.mean(N, 0)))])
    print(json.dumps(pts, indent=0))
