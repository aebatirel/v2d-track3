"""Stage B2b (part 1): final-placement priors. For each (task, mover, receiver) pair with >=2 public eps, the mover's pose
in the receiver's body frame over its final static segment (median frame), and the twin-to-twin (LOO) difference:
translation (cm), full rotation (deg), rotation ignoring spin about the mover's symmetry axis (deg). Single-object tasks
use the mover's own START pose as 'receiver' (end-relative-to-start) and the world (end yaw). GT only. Research only."""
from c11 import *
import json
rest = json.load(open('s8_rest.json'))
PAIRS = [("Cup_In_Dish_Rack", [12, 13], "blue_cup", "plastic_dish_rack"),
         ("Pan_In_Dishrack", [26, 27], "white_pot", "plastic_dish_rack"),
         ("Pot_with_lid", [0, 2], "white_pot_lid", "white_pot"),
         ("Water_Can_Blue_Cup", [21, 22], "water_pitcher", "blue_cup"),
         ("Water_Can_Blue_Cup", [21, 22], "blue_cup", "water_pitcher"),
         ("Planter_Stand", [23, 24], "wooden_piece_1", "wooden_piece_2"),
         ("Planter_Stand", [23, 24], "wooden_piece_2", "wooden_piece_1"),
         ("Pan_Solo", [41, 42, 43, 44, 45], "white_pot", "START"),
         ("Dustpan_Solo", [39, 40], "mini_dust_pan", "START"),
         ("Cup_Stack", [11], "beige_cup", "blue_cup"), ("Brush_Dishrack", [31], "mini_sweeper", "plastic_dish_rack"),
         ("Dust_Brush", [18], "mini_sweeper", "mini_dust_pan")]
SYMC = {"blue_cup", "beige_cup", "white_pot_lid"}


def last_static(ep, nm, T):
    L = [r for r in rest.get(nm, []) if r['ep'] == ep]
    L = sorted(L, key=lambda r: r['f1'])
    if L and L[-1]['f1'] >= T - 5:
        return (L[-1]['f0'], L[-1]['f1'])
    return (T - 1, T - 1)   # not static at the end -> use the final frame (flag: seg = (T-1, T-1))


def rel(e, mv, rc, f):
    p = e['pose']; j = e['names'].index(mv)
    if rc == "START":
        Rr, tr = R_of(p[0, j, 3:]), p[0, j, :3]
    else:
        k = e['names'].index(rc); Rr, tr = R_of(p[f, k, 3:]), p[f, k, :3]
    Rm, tm = R_of(p[f, j, 3:]), p[f, j, :3]
    return Rr.T @ Rm, Rr.T @ (tm - tr)


out = []
for task, eps, mv, rc in PAIRS:
    R = {}
    for ep in eps:
        e = load_episode(ep); T = len(e['pose']); f0, f1 = last_static(ep, mv, T); fm = (f0 + f1) // 2
        Rrel, trel = rel(e, mv, rc, fm)
        yaw_end, tilt_end = yaw_tilt(e['pose'][fm, e['names'].index(mv), 3:], mv)
        R[ep] = dict(Rrel=Rrel, trel=trel, seg=(int(f0), int(f1)), T=T, yaw=float(yaw_end), tilt=float(tilt_end))
    row = dict(task=task, mover=mv, receiver=rc, eps=eps,
               seg={ep: R[ep]['seg'] + (R[ep]['T'],) for ep in eps},
               trel_cm={ep: [round(float(x) * 100, 1) for x in R[ep]['trel']] for ep in eps},
               end_world_yaw={ep: round(R[ep]['yaw'], 1) for ep in eps}, end_tilt={ep: round(R[ep]['tilt'], 1) for ep in eps})
    if len(eps) >= 2:
        dt, dr, dra = [], [], []
        for i in range(len(eps)):
            for k in range(i + 1, len(eps)):
                a, b = R[eps[i]], R[eps[k]]
                dt.append(float(np.linalg.norm(a['trel'] - b['trel']) * 100))
                D = a['Rrel'].T @ b['Rrel']; dr.append(float(np.degrees(Rot.from_matrix(D).magnitude())))
                u = np.array(UP[mv], float)   # symmetry axis (body); angle between mapped axes ignores spin
                dra.append(float(np.degrees(np.arccos(np.clip((a['Rrel'] @ u) @ (b['Rrel'] @ u), -1, 1)))))
        row.update(pair_dt_cm=[round(x, 1) for x in dt], pair_drot_deg=[round(x, 1) for x in dr],
                   pair_daxis_deg=[round(x, 1) for x in dra])
    out.append(row); print(json.dumps(row))
json.dump(out, open('s18_endplace.json', 'w'), indent=1)
