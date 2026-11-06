"""ORACLE DIAGNOSTIC (public episodes only), after T1's pre-registered reading; POST HOC, adopts nothing.
Mechanism check for T1's small losses on episodes whose frozen object is the kit's alignment anchor (ep27 P_o * -0.0023):
the kit pins the whole scene on frame 0 (_align_registered_scene): the rotation from the first object without a symmetry
axis (the rack in ep12/13/26/27, the sweeper in ep31; cups only: slot 0's axis and the direction to slot 1), the
translation from slot 0's frame-0 position. In the S2 arm the anchor's frame 0 is the S2-advanced pose
O(0.545); with S6 before S2 a frozen anchor keeps the raw O(0). Counterfactual 'S2 then S6': the same frozen set (from the
S6,S2 run's pose_opt.json), frozen at the S2 output's frame-0 pose, so frame 0 equals the S2 arm's. Also prints the
unrounded Δ of the pre-registered comparison and the anchor's frame-0 shift between the arms.
Usage: python -I t1_order_diag.py OUT_JSON
"""
import json, sys

import numpy as np
from scipy.spatial.transform import Rotation as Rot

sys.path.insert(0, sys.argv[0].rsplit('/', 1)[0])
import t1_score as TS  # noqa: E402

XF = TS.XF


def auc_raw(names, track, gt, H, REG):   # score_track without the 4-decimal rounding
    T3 = XF.K['T3']; N = len(track[names[0]]); B = len(names)
    ach = np.stack([XF.to7(track[n]) for n in names], 1)[:, None].copy(); ref = np.stack([XF.to7(gt[n][:N]) for n in names], 1)[:, None].copy()
    for s in range(B):
        ach[:, :, s] = T3._convert_object_body(ach[:, :, s], *REG[s])
        ref[:, :, s, :3] += np.einsum('...ij,j->...i', T3._rotation_matrix(ref[:, :, s, 3:]), H[s]['anchor'])
    axes = [h['axis'] for h in H]; orders = [h['order'] for h in H]; pts = [h['points'] for h in H]
    ach = T3._align_registered_scene(ach, ref, axes)
    return float(T3._registered_pose_metric('add_auc', ach, ref, pts, axes, orders))


def main():
    XF.kit(TS.KIT)
    out = {}
    for ep in (11, 12, 13, 26, 27, 31):
        names, gt = XF.mocap(TS.T3D, ep, None)
        H = [XF.host_geometry(TS.T3D, n, s) for s, n in enumerate(names)]
        REG = {'lib': [XF.kit_X(f'{TS.LIB}/{n}.glb', H[s], ep, s)[1] for s, n in enumerate(names)],
               'star': [XF.reg_of_X(np.asarray(TS.XG[n]['X_scan_T_lib']), H[s]['anchor']) for s, n in enumerate(names)]}
        fixed = [n for s, n in enumerate(names) if not np.any(H[s]['axis'])]
        anchor = fixed[0] if fixed else names[0]          # rotation from it (cups only: slot 0 axis + slot 1 direction)
        e = dict(names=names, kit_rotation_anchor=anchor, kit_translation_anchor=names[0])
        for arm in TS.ARMS:
            frozen = json.load(open(f'{TS.W}/runs/{arm}/S6S2/ep{ep}/pose_opt.json'))['steps']['S6']['frozen']
            V2 = np.load(f'{TS.W}/runs/{arm}/S2/ep{ep}/poses_world_vo.npz'); V62 = np.load(f'{TS.W}/runs/{arm}/S6S2/ep{ep}/poses_world_vo.npz')
            N = len(V2[names[0]]); g = {n: gt[n][:N] for n in names}
            T2 = {n: V2[n].astype(np.float64) for n in names}; T62 = {n: V62[n].astype(np.float64) for n in names}
            Tcf = {n: (np.repeat(T2[n][:1], N, 0) if n in frozen else T2[n]) for n in names}
            r = dict(frozen=frozen)
            for c in ('lib', 'star'):
                a2, a62, acf = (auc_raw(names, T, g, H, REG[c]) for T in (T2, T62, Tcf))
                r[c] = dict(S2=round(a2, 6), S6S2=round(a62, 6), S2_then_S6=round(acf, 6),
                            delta_S6S2=round(a62 - a2, 6), delta_S2_then_S6=round(acf - a2, 6))
            A, B = T2[anchor][0], T62[anchor][0]
            r['anchor_f0_shift'] = dict(cm=round(float(np.linalg.norm(A[:3, 3] - B[:3, 3]) * 100), 4),
                                        deg=round(float(np.degrees(Rot.from_matrix(A[:3, :3] @ B[:3, :3].T).magnitude())), 4))
            e[arm] = r
            print(f'ep{ep} {arm} anchor {anchor} f0 shift {r["anchor_f0_shift"]} frozen {frozen} | ' + ' | '.join(
                f'{c}: S6,S2 {r[c]["delta_S6S2"]:+.5f}  S2 then S6 {r[c]["delta_S2_then_S6"]:+.5f}' for c in ('lib', 'star')), flush=True)
        out[str(ep)] = e
    json.dump(dict(note='ORACLE DIAGNOSTIC, post hoc (after the T1 reading); mechanism check only, adopts nothing.', episodes=out),
              open(sys.argv[1], 'w'), indent=1)


if __name__ == '__main__':
    main()
