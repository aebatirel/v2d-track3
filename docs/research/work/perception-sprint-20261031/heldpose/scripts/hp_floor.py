"""ORACLE DIAGNOSTIC, POST HOC (public episodes only; not part of the pre-registered rule): why wrist x G fails or works.
For every S10 hold of the Po arm (pose_opt_aux.npz of the S10g run: S10_<obj>_side, S10_<obj>_P), after the kit's
conversion and scene alignment (* convention, as hp_score.per_frame), per hold frame:
  e_trk   tracker (S2 output) symmetry-aware ADD vs mocap;
  e_P     onset-G prediction P(t) = W(t) G (S10's own);
  e_Pst   oracle-G floor: P*(t) = A W(t) G*, G* = the ONE constant grasp per hold fitted to mocap (chordal mean rotation,
          mean translation of inv(A W(t)) M(t)); A = the kit's scene alignment. The best any constant-grasp lock on our
          palm frame can do; its error is palm-frame noise plus real in-hand motion.
  rel_spread_deg  median angle of inv(A W(t)) M(t) from its mean over the hold (mocap-relative grasp variation).
W(t) = heldpose.smooth_frames(heldpose.palm_frames(joints)) exactly as S10 computes it (GT-free inputs).
Usage: python -I hp_floor.py OUT_JSON
"""
import json, os, sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from scipy.spatial.transform import Rotation as Rot

REPO = '/home/user/v2d-track3'
S = '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad'
sys.path.insert(0, f'{REPO}/tools')
sys.path.insert(0, f'{REPO}/pipeline')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import xstar_fit as XF  # noqa: E402
import heldpose as HP  # noqa: E402
from hp_score import KIT, T3D, XG, W, CLASS, ARMS  # noqa: E402


def mat(x7):
    M = np.tile(np.eye(4), (len(x7), 1, 1))
    M[:, :3, :3] = Rot.from_quat(x7[:, 3:]).as_matrix()
    M[:, :3, 3] = x7[:, :3]
    return M


def x7(M):
    return np.concatenate([M[:, :3, 3], Rot.from_matrix(M[:, :3, :3]).as_quat()], 1)


def episode(ep, arm='Po'):
    XF.kit(KIT)
    T3 = XF.K['T3']
    names, gt = XF.mocap(T3D, ep, None)
    H = [XF.host_geometry(T3D, n, s) for s, n in enumerate(names)]
    REG = [XF.reg_of_X(np.asarray(XG[n]['X_scan_T_lib']), H[s]['anchor']) for s, n in enumerate(names)]
    V = np.load(f'{W}/runs/{arm}/S2/ep{ep}/poses_world_vo.npz')
    tr = {n: V[n].astype(np.float64) for n in names}
    N = len(tr[names[0]])
    ach0 = np.stack([XF.to7(tr[n]) for n in names], 1)[:, None].copy()
    ref = np.stack([XF.to7(gt[n][:N]) for n in names], 1)[:, None].copy()
    ach = ach0.copy()
    for s in range(len(names)):
        ach[:, :, s] = T3._convert_object_body(ach[:, :, s], *REG[s])
        ref[:, :, s, :3] += np.einsum('...ij,j->...i', T3._rotation_matrix(ref[:, :, s, 3:]), H[s]['anchor'])
    axes = [h['axis'] for h in H]
    al = T3._align_registered_scene(ach, ref, axes)
    # the scene alignment as one rigid transform A (from slot 0, frame 0: al = A o ach)
    Ma, Mb = mat(ach[:1, 0, 0]), mat(al[:1, 0, 0])
    A = Mb[0] @ np.linalg.inv(Ma[0])
    root = ARMS[arm]
    Hd = np.load(f'{root}/ep{ep}/hands_refined.npz')
    aux = np.load(f'{W}/runs/{arm}/S10g/ep{ep}/pose_opt_aux.npz')
    out = []
    for s, n in enumerate(names):
        side = aux[f'S10_{n}_side']
        P = aux[f'S10_{n}_P']
        vP = aux[f'S10_{n}_vP']
        if (side < 0).all():
            continue
        Mref = mat(ref[:, 0, s])
        e_trk = T3._symmetry_point_errors(al[:, :, s], ref[:, :, s], H[s]['points'], axes[s], H[s]['order'])[:, 0]
        # S10's prediction through the same conversion and alignment
        Pc = x7(np.where(np.isfinite(P), P, np.eye(4)[None]))[:, None]
        Pc = T3._convert_object_body(Pc, *REG[s])
        PcM = mat(Pc[:, 0])
        PalM = np.einsum('ij,tjk->tik', A, PcM)
        e_P = T3._symmetry_point_errors(x7(PalM)[:, None], ref[:, :, s], H[s]['points'], axes[s], H[s]['order'])[:, 0]
        r = np.r_[False, side >= 0, False].astype(np.int8)
        d = np.diff(r)
        for a, b in zip(np.nonzero(d == 1)[0], np.nonzero(d == -1)[0]):
            sd = 'left' if side[a] == 0 else 'right'
            J = Hd[f'joints_{sd}'].astype(float)
            Mm = Hd[f'measured_{sd}'].astype(bool)
            Wp = HP.smooth_frames(HP.palm_frames(J), Mm, 5, 20.0)
            fr = [t for t in range(max(a, 1), b) if Mm[t]]
            if len(fr) < 5:
                continue
            AW = np.einsum('ij,tjk->tik', A, Wp[fr])
            Gs = np.einsum('tij,tjk->tik', np.linalg.inv(AW), Mref[fr])
            Gst = np.eye(4)
            Gst[:3, :3] = Rot.from_matrix(Gs[:, :3, :3]).mean().as_matrix()
            Gst[:3, 3] = Gs[:, :3, 3].mean(0)
            Pst = np.einsum('tij,jk->tik', AW, Gst)
            e_Pst = T3._symmetry_point_errors(x7(Pst)[:, None], ref[fr, :, s], H[s]['points'], axes[s], H[s]['order'])[:, 0]
            spread = np.degrees((Rot.from_matrix(Gs[:, :3, :3]) * Rot.from_matrix(Gst[:3, :3]).inv()).magnitude())
            tspread = np.linalg.norm(Gs[:, :3, 3] - Gst[:3, 3], axis=1) * 100
            out.append(dict(ep=ep, obj=n, cls=CLASS.get(n, n), side=sd, a=int(a), b=int(b), n=len(fr),
                            e_trk_med=round(float(np.median(e_trk[fr]) * 100), 2),
                            e_P_med=round(float(np.median(e_P[fr]) * 100), 2),
                            e_Pst_med=round(float(np.median(e_Pst) * 100), 2),
                            Pst_better_than_trk=round(float((e_Pst < e_trk[fr]).mean()), 3),
                            rel_spread_deg_med=round(float(np.median(spread)), 1),
                            rel_spread_cm_med=round(float(np.median(tspread)), 2),
                            vP_med=round(float(np.nanmedian(vP[fr])), 3)))
    return out


def main():
    rows = []
    with ProcessPoolExecutor(4) as ex:
        for r in ex.map(episode, XF.PUBLIC):
            rows += r
    for x in rows:
        print(json.dumps(x))
    summ = {}
    for grp, members in (('thin', ('sweeper', 'dust pan')), ('cups', ('cups',)), ('pot/lid', ('pot/lid',)), ('all', None)):
        sel = [x for x in rows if members is None or x['cls'] in members]
        wsum = sum(x['n'] for x in sel)
        summ[grp] = dict(holds=len(sel), frames=wsum,
                         **{k: round(sum(x[k] * x['n'] for x in sel) / max(wsum, 1), 3)
                            for k in ('e_trk_med', 'e_P_med', 'e_Pst_med', 'Pst_better_than_trk', 'rel_spread_deg_med',
                                      'rel_spread_cm_med')})
    print(json.dumps(summ, indent=1))
    json.dump(dict(note='ORACLE, POST HOC diagnostic (Po arm): constant-grasp floor on our palm frame vs the tracker on '
                        'S10 holds; frame-weighted means of per-hold medians in the summary.', summary=summ, holds=rows),
              open(sys.argv[1], 'w'), indent=1)


if __name__ == '__main__':
    main()
