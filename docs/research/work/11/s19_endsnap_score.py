"""Stage B2b (part 2): official-score value of snapping a mover's final static segment to the twin's relative end
placement (LOO), vs a constant vision error on that segment. Cases: lid->pot (eps 0, 2; lid spin kept from 'vision':
only translation + swing about the lid axis are snapped), plank piece_2 -> piece_1 (eps 23, 24; full 6-DoF snap).
Vision error: constant over the segment, translation |dt| = s cm (random direction), rotation |dR| = a deg (random axis);
mean over 8 seeds. Perfect tracking elsewhere. Research only."""
from sc11 import *
import json
rest = json.load(open('s8_rest.json'))
CASES = [("Pot_with_lid", 0, 2, "white_pot_lid", "white_pot", True), ("Pot_with_lid", 2, 0, "white_pot_lid", "white_pot", True),
         ("Planter_Stand", 23, 24, "wooden_piece_2", "wooden_piece_1", False),
         ("Planter_Stand", 24, 23, "wooden_piece_2", "wooden_piece_1", False)]
LEVELS = [(0.5, 2), (1, 5), (2, 10), (3, 15)]


def seg(ep, nm, T, rc=None, e=None):
    """final run of frames where the mover's pose in the receiver frame stays within 0.5 cm / 3 deg of its final value
    (GT-based 'placed' segmentation; in practice this state would come from vision)."""
    e = e or load_episode(ep); p = e['pose']; j, k = e['names'].index(nm), e['names'].index(rc)
    Rr = Rot.from_quat(p[:, k, 3:]); relR = Rr.inv() * Rot.from_quat(p[:, j, 3:]); relt = Rr.inv().apply(p[:, j, :3] - p[:, k, :3])
    ok = (np.linalg.norm(relt - relt[-1], axis=1) < 0.005) & (np.degrees((relR[-1].inv() * relR).magnitude()) < 3)
    f0 = T - 1
    while f0 > 0 and ok[f0 - 1]: f0 -= 1
    return (f0, T - 1)


def twist(Rm, u):
    """twist (rotation about body axis u) of a rotation given as Rot."""
    rv = Rm.as_quat(); v = rv[:3]; proj = (v @ u) * u
    q = np.r_[proj, rv[3]]; n = np.linalg.norm(q)
    return Rot.from_quat(q / n) if n > 1e-12 else Rot.identity()


out = {}
for task, ep, tw, mv, rc, keep_spin in CASES:
    e, t = load_episode(ep), load_episode(tw); p, nm = e['pose'], e['names']; T = len(p)
    j, k = nm.index(mv), nm.index(rc); f0, f1 = seg(ep, mv, T, rc, e)
    # twin relative end pose (receiver frame) at the twin's final-segment median
    Tt = len(t['pose']); g0, g1 = seg(tw, mv, Tt, rc, t); gm = (g0 + g1) // 2
    jt, kt = t['names'].index(mv), t['names'].index(rc)
    Rr_t = Rot.from_quat(t['pose'][gm, kt, 3:]); rel_R = Rr_t.inv() * Rot.from_quat(t['pose'][gm, jt, 3:])
    rel_t = Rr_t.inv().apply(t['pose'][gm, jt, :3] - t['pose'][gm, kt, :3])
    u = np.array(UP[mv], float)
    idx = np.arange(f0, f1 + 1)
    r = dict(task=task, ep=ep, twin=tw, seg=[int(f0), int(f1), T], frac=round(len(idx) / T, 3))

    def snapped(vis_dR):
        o = p.copy()
        for f in idx:
            Rr = Rot.from_quat(p[f, k, 3:]); M = Rot.from_quat(p[f, j, 3:])
            P = Rr * rel_R; pos = p[f, k, :3] + Rr.apply(rel_t)
            if keep_spin:   # replace the prior's twist about the lid axis by truth's twist composed with vision twist
                D = M.inv() * P; sw = D * twist(D, u).inv(); P = M * sw * twist(vis_dR, u)
            o[f, j, 3:] = P.as_quat(); o[f, j, :3] = pos
        return o

    def vision(dt, dR):
        o = p.copy()
        o[idx, j, :3] += dt
        o[idx, j, 3:] = (Rot.from_quat(p[idx, j, 3:]) * dR).as_quat()
        return o
    res_t = []; f = (f0 + f1) // 2
    Rr = Rot.from_quat(p[f, k, 3:]); r['prior_dt_cm'] = round(float(np.linalg.norm(p[f, k, :3] + Rr.apply(rel_t) - p[f, j, :3]) * 100), 2)
    r['prior_drot_deg'] = round(float(np.degrees(((Rr * rel_R).inv() * Rot.from_quat(p[f, j, 3:])).magnitude())), 1)
    for s, a in LEVELS:
        V, S = [], []
        for sd in range(8):
            rng = np.random.default_rng(sd)
            d = rng.normal(size=3); d *= s / 100 / np.linalg.norm(d)
            ax = rng.normal(size=3); ax /= np.linalg.norm(ax); dR = Rot.from_rotvec(np.radians(a) * ax)
            V.append(score_all(vision(d, dR), p, nm, ep)); S.append(score_all(snapped(dR), p, nm, ep))
        r[f"vision_{s}cm_{a}deg"] = mean_metrics(V); r[f"snap_{s}cm_{a}deg"] = mean_metrics(S)
    out[f"{ep}"] = r
    print(json.dumps(r)); json.dump(out, open('s19_endsnap_score.json', 'w'), indent=1)
