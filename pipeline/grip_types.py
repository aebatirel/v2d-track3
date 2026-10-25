"""Grip-type candidates for one hold, as grasp_lock templates (2026-10-25, owner: "try all the possible grip types and
pick the best or most stable; the best can be decided on how the piece moves and how it is released";
docs/research/approaches-2026-10-25/approach3-grasp-taxonomy.md §11). Built from OUR mesh (the object's collision
pieces in the FlashCHORD scene) and the Sharpa hand's own Newton FK, in the style of pipeline/wrap_grasp.py; no
classifier, no ground truth. The portfolio driver simulates each candidate and keeps the human copy unless a type wins
clearly (tools/grip_portfolio.sh).

Hand frame (wrap_grasp.py): +z along the fingers, y across the knuckles, +x the palm side (fingers curl towards +x).

Types (flat objects: boards, plates):
  clamp_long   parallel extension (GRASP #22, biomechanics report §11.3 "B4") at the long edge nearest the human hand:
               palm up (x = the board's up normal), fingers point inward (z) and lie flat under the board with its edge
               EDGE_IN cm past the knuckles, thumb pad on the top face THUMB_IN cm in. (The Sharpa thumb tip reaches
               z <= ~15 cm in the hand frame while the fingertips sit at 19-20 cm, measured with Newton FK: the thumb
               cannot oppose the fingertips, only the proximal phalanges, so the board goes deep into the hand);
  clamp_short  the same at the nearest short end;
  platform     the same placement with the thumb left open (a support grip, no opposition).
Placement: the hand starts LOW cm below the board and rises along its normal until a finger link touches the hulls
(the hands pass through the table in this simulator). Thumb: a grid over its joints, scored by how close its touching
point is to the target on the top face. Squeeze: per digit, the joint direction J^T n_in that pushes its contact point
into the object (n_in = -grad SDF), scaled to SQUEEZE rad on that digit's largest joint, so the thumb on top presses down
and the pads below press up (a plain flexion squeeze would lift a palm-up thumb off the top face).
Usage (FlashCHORD python, from the flash_chord dir, FC set):
  python grip_types.py REF.parquet OUT_DIR --object wooden_piece_1 --side left --frame 12 [--types clamp_long,clamp_short,platform]
Writes OUT_DIR/<type>.json ({"templates": {object: {...}}}, the format of tools/extract_grasp_templates.py plus
finger_joints_squeezed) and OUT_DIR/report.json."""
import argparse, itertools, json, os, sys

import numpy as np
import pyarrow.parquet as pq
from scipy.spatial.transform import Rotation as Rot

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import contact_retarget as cr  # noqa: E402

EDGE_IN, THUMB_IN, LOW, SQUEEZE, EDGE_MARGIN = 0.01, 0.03, 0.08, 0.25, 0.04
DIGITS = ('thumb', 'index', 'middle', 'ring', 'pinky')


def main():
    p = argparse.ArgumentParser(); p.add_argument('ref'); p.add_argument('out')
    p.add_argument('--object', required=True); p.add_argument('--side', required=True, choices=['left', 'right'])
    p.add_argument('--frame', type=int, required=True); p.add_argument('--types', default='clamp_long,clamp_short,platform')
    p.add_argument('--squeeze', type=float, default=SQUEEZE)
    a = p.parse_args(); fc = os.environ.get('FC', os.getcwd()); os.makedirs(a.out, exist_ok=True)
    st, env = cr.build_scene(os.path.abspath(a.ref), fc); m = st.scene.model; fk = cr.FK(m)
    t = pq.read_table(a.ref); qref = np.asarray(st.scene.robot_reference.joint_q, float).copy(); T = len(qref)
    names = t.column('object_body_names')[0].as_py(); j = names.index(a.object); g = a.frame; side = a.side; o = cr.SIDES[side]
    OP = np.array(t.column('object_body_position')[0].as_py(), float).reshape(T, len(names), 3)[g, j]
    ORg = Rot.from_quat(np.array(t.column('object_body_wxyz')[0].as_py(), float).reshape(T, len(names), 4)[g, j][[1, 2, 3, 0]])
    blabels = list(getattr(m, 'body_label', None) or getattr(m, 'body_key', []))
    body = next(i for i, l in enumerate(blabels) if l.startswith(f'track3_{a.object}/'))
    sdf = cr.HullSDF(m, body); V = np.vstack(sdf.pieces)
    fj = t.column(f'{side}_robot_finger_joint_names')[0].as_py()
    jl = list(getattr(m, 'joint_label', None) or getattr(m, 'joint_key', [])); jidx = {l: i for i, l in enumerate(jl)}
    dstart = m.joint_qd_start.numpy(); lo_l, hi_l = m.joint_limit_lower.numpy(), m.joint_limit_upper.numpy()
    lo = np.array([lo_l[dstart[jidx[f'{side}_sharpa_wave/{n}']]] for n in fj]); hi = np.array([hi_l[dstart[jidx[f'{side}_sharpa_wave/{n}']]] for n in fj])
    bodies, pb, pl = cr.hand_geometry(m, side)
    link = {d: np.isin(pb, [bodies[k] for k in bodies if k.startswith(f'{side}_{d}_') and k.split('_')[-1] in ('MC', 'PP', 'MP', 'DP')]) for d in DIGITS}
    dp = {d: pb == bodies[f'{side}_{d}_DP'] for d in DIGITS}
    jd = {d: np.array([i for i, n in enumerate(fj) if f'_{d}_' in n]) for d in DIGITS}
    to_obj = lambda X: ORg.inv().apply(X - OP)                    # noqa: E731
    wrist_obj = to_obj(qref[g, o:o + 3])

    def pose(R_ow, p_ow, qf):                                      # full joint vector with this hand at (R, p) in the object frame
        q = qref[g].copy(); q[o:o + 3] = ORg.apply(p_ow) + OP; q[o + 3:o + 7] = (ORg * R_ow).as_quat(); q[o + 7:o + 29] = qf
        return q

    def pts(q, sel):
        return to_obj(cr.world_points(fk(q), pb[sel], pl[sel]))

    # the board's frame from our mesh: n = its thinnest axis (up at frame g), u long, v short; slab extents by percentiles
    c0 = V.mean(0); _, _, Vt = np.linalg.svd(V - c0, full_matrices=False); u, v, n = Vt
    if ORg.apply(n)[2] < 0:
        n = -n
    ext = {k: np.percentile((V - c0) @ ax, [1, 99]) for k, ax in (('u', u), ('v', v), ('n', n))}
    # finger geometry in the hand frame (wrist at the origin, identity): fingertip reach along z, finger-group centre in y
    q0 = qref[g].copy(); q0[o:o + 3] = 0.0; q0[o + 3:o + 7] = [0, 0, 0, 1.0]; qopen = np.clip(np.zeros(22), lo, hi)
    q0[o + 7:o + 29] = qopen; H = cr.world_points(fk(q0), pb, pl)
    mid = dp['index'] | dp['middle'] | dp['ring']; y_mid = float(H[mid, 1].mean())
    pp = np.isin(pb, [bodies[f'{side}_{d}_PP'] for d in ('index', 'middle', 'ring')]); z_kn = float(np.median(H[pp, 2]) - 0.5 * np.ptp(H[pp, 2]))
    report = dict(object=a.object, side=side, frame=g, board_axes=dict(u=u.round(3).tolist(), v=v.round(3).tolist(), n=n.round(3).tolist()),
                  extents_cm={k: (100 * np.asarray(e)).round(1).tolist() for k, e in ext.items()}, z_knuckle_cm=round(100 * z_kn, 1), types={})
    for typ in a.types.split(','):
        ax, tax = (v, u) if typ in ('clamp_long', 'platform') else (u, v)
        key = 'v' if ax is v else 'u'; tkey = 'u' if key == 'v' else 'v'
        s = 1.0 if (wrist_obj - c0) @ ax >= 0 else -1.0             # the edge nearest the human wrist
        e0 = c0 + ax * (ext[key][1] if s > 0 else ext[key][0]); d = -s * ax
        gt = float(np.clip((wrist_obj - c0) @ tax, ext[tkey][0] + EDGE_MARGIN, ext[tkey][1] - EDGE_MARGIN))
        e = e0 + tax * (gt - (e0 - c0) @ tax)
        x, z = n, d; y = np.cross(z, x); R_ow = Rot.from_matrix(np.stack([x, y, z], 1))
        base = e - d * (z_kn + EDGE_IN) - R_ow.apply([0, y_mid, 0])   # the edge EDGE_IN past the knuckles
        fingers = link['index'] | link['middle'] | link['ring'] | link['pinky']
        h_hit = None
        for h in np.arange(-LOW, 0.04, 0.001):                     # rise along n until a finger link touches
            if sdf(pts(pose(R_ow, base + n * h, qopen), fingers)).min() <= 0.001:
                h_hit = float(h); break
        if h_hit is None:
            report['types'][typ] = dict(ok=False, why='no finger contact while rising'); continue
        p_ow = base + n * h_hit; qf = qopen.copy()
        info = dict(edge_cm=(100 * e).round(1).tolist(), inward=d.round(3).tolist(), rise_cm=round(100 * h_hit, 1))
        if typ != 'platform':                                      # thumb onto the top face, opposite the fingers
            target = e + d * THUMB_IN
            th = [int(jd['thumb'][[n.endswith(k) for n in np.array(fj)[jd['thumb']]].index(True)]) for k in ('CMC_FE', 'CMC_AA', 'MCP_FE', 'IP')]
            grids = [np.linspace(lo[i], hi[i], c) for i, c in zip(th, (8, 3, 6, 4))]
            best = (np.inf, None, None)
            for combo in itertools.product(*grids):
                qq = qf.copy(); qq[th] = combo
                P = pts(pose(R_ow, p_ow, qq), link['thumb']); sd = sdf(P); k = int(np.argmin(sd))
                if sd[k] < -0.004:                                 # inside the board
                    continue
                c = P[k]; top = (c - c0) @ n > 0
                score = (np.linalg.norm((c - target) - n * ((c - target) @ n)) + 5 * max(0.0, sd[k] - 0.002) + (0 if top else 1.0))
                if score < best[0]:
                    best = (score, combo, dict(gap_mm=round(1000 * float(sd[k]), 1), top=bool(top),
                                               in_cm=round(100 * float((c - e) @ d), 1), off_cm=round(100 * float(np.linalg.norm((c - target) - n * ((c - target) @ n))), 1)))
            if best[1] is None:
                report['types'][typ] = dict(info, ok=False, why='no thumb pose outside the board'); continue
            qf[th] = best[1]; info['thumb'] = best[2]
        # squeeze: per digit, J^T n_in at its touching point, scaled to SQUEEZE rad on the digit's largest joint
        q_c = pose(R_ow, p_ow, qf); qs = qf.copy(); contacts = {}
        for dg in DIGITS:
            if typ == 'platform' and dg == 'thumb':
                continue
            P = pts(q_c, link[dg]); sd = sdf(P); k = int(np.argmin(sd))
            if sd[k] > 0.004:
                continue
            nin = -sdf.grad(P[k:k + 1])[0]; idx = jd[dg]; Jt = np.zeros(len(idx))
            sel = np.nonzero(link[dg])[0][k]
            for ii, ji in enumerate(idx):                          # finite-difference Jacobian of that sample point
                qq = qf.copy(); qq[ji] += 1e-3
                Pk = to_obj(cr.world_points(fk(pose(R_ow, p_ow, qq)), pb[[sel]], pl[[sel]]))[0]
                Jt[ii] = (Pk - P[k]) @ nin / 1e-3
            if np.abs(Jt).max() > 1e-6:
                qs[idx] = qf[idx] + a.squeeze * Jt / np.abs(Jt).max()
            contacts[dg] = round(1000 * float(sd[k]), 1)
        qs = np.clip(qs, lo, hi); info['contacts_gap_mm'] = contacts
        if typ != 'platform' and 'thumb' not in contacts:
            report['types'][typ] = dict(info, ok=False, why='thumb not touching'); continue
        tpl = {a.object: dict(side=side, frame=g, type=typ, wrist_pos_obj=[round(float(x_), 6) for x_ in p_ow],
                              wrist_quat_obj_xyzw=[round(float(x_), 6) for x_ in R_ow.as_quat()], finger_joint_names=list(fj),
                              finger_joints=[round(float(x_), 5) for x_ in qf], finger_joints_squeezed=[round(float(x_), 5) for x_ in qs])}
        json.dump(dict(source=f'grip_types.py {typ} on {os.path.basename(a.ref)} f{g}', templates=tpl), open(f'{a.out}/{typ}.json', 'w'), indent=1)
        report['types'][typ] = dict(info, ok=True); print(typ, json.dumps(info), flush=True)
    json.dump(report, open(f'{a.out}/report.json', 'w'), indent=1); print(json.dumps(report['types']), flush=True)


if __name__ == '__main__':
    import warp as wp
    with wp.ScopedDevice('cpu'):
        main()
