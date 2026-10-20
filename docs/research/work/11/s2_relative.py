from c11 import *
from collections import defaultdict
out = defaultdict(list)
for ep in PUBLIC:
    e = load_episode(ep); p = e['pose']; nm = e['names']
    if len(nm) < 2: continue
    for k, f in (("start", 0), ("end", len(p) - 1)):
        Ra, Rb = R_of(p[f, 0, 3:]), R_of(p[f, 1, 3:])
        d = Ra.T @ (p[f, 1, :3] - p[f, 0, :3])  # B in A's body frame
        Rrel = Ra.T @ Rb
        rv = Rot.from_matrix(Rrel).as_rotvec()
        # relative yaw about world vertical: yaw(B)-yaw(A)
        ya, _ = yaw_tilt(p[f, 0, 3:], nm[0]); yb, _ = yaw_tilt(p[f, 1, 3:], nm[1])
        dw = p[f, 1, :3] - p[f, 0, :3]
        out[(e['task'], k)].append((ep, nm, d, Rrel, wrap(yb - ya), dw))
for (task, k), L in out.items():
    print(f"== {task} {k}")
    for ep, nm, d, Rrel, dy, dw in L:
        print(f"  ep{ep:2d} {nm[1]} in {nm[0]} frame: d_body={np.round(d*100,1)} cm |d|={np.linalg.norm(d)*100:.1f}  world dxyz={np.round(dw*100,1)}  rel-yaw(B-A)={dy:7.1f}  dz={dw[2]*100:.1f}")
    if len(L) >= 2:
        for i in range(len(L)):
            for j in range(i + 1, len(L)):
                ang = np.degrees(Rot.from_matrix(L[i][3].T @ L[j][3]).magnitude())
                print(f"    pair ep{L[i][0]}-ep{L[j][0]}: rel-rot diff {ang:.1f} deg, rel-pos diff {np.linalg.norm(L[i][2]-L[j][2])*100:.1f} cm, horiz world dist diff {abs(np.linalg.norm(L[i][5][:2])-np.linalg.norm(L[j][5][:2]))*100:.1f} cm")
