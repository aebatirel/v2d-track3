"""ORACLE DIAGNOSTIC (public ep11 only): per-frame error of the Phase-1 tracks vs mocap, in the * convention.
Reads ground truth (mocap, scans). Nothing here feeds eval inference.
Usage: python -I diag11.py OUT_JSON
"""
import json, os, sys
import numpy as np
from scipy.spatial.transform import Rotation as Rot

REPO = '/home/user/v2d-track3'
S = '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad'
sys.path.insert(0, f'{REPO}/tools')
import xstar_fit as XF  # noqa: E402

EP = 11
KIT = f'{S}/map/scoring/kit/v2d_submission_kit'; T3D = f'{S}/map/scoring/t3'
RUN = f'{S}/leak/p1/runs/20261030-orcP1b-87fc869/results/leak_p1/ep11'
REF = f'{S}/refine/in/ep11'
XG = json.load(open(f'{REPO}/docs/research/work/leak-decomp-20261030/tierA/xstar_geom.json'))['objects']
XF.kit(KIT); T3 = XF.K['T3']
THR = np.arange(0.01, 0.10, 0.01); TW = np.r_[0.5, np.ones(7), 0.5] / 8


def auc_of(e):  # per-frame ADD (m) -> kit AUC
    return float(np.mean((e[:, None] < THR[None]).astype(float) @ TW)) if len(e) else float('nan')


def load_tracks():
    names, gt = XF.mocap(T3D, EP, None)
    N = len(gt[names[0]])
    out = {}
    V = np.load(f'{RUN}/perc2/poses_world_vo.npz')
    out['Po'] = {n: V[n].astype(np.float64) @ np.linalg.inv(np.asarray(XG[n]['X_scan_T_lib'])) for n in names}
    if os.path.exists(f'{RUN}/perc2rep/poses_world_vo.npz'):
        V2 = np.load(f'{RUN}/perc2rep/poses_world_vo.npz')
        out['Po2'] = {n: V2[n].astype(np.float64) @ np.linalg.inv(np.asarray(XG[n]['X_scan_T_lib'])) for n in names}
    Vs = np.load(f'{RUN}/perc2scan/poses_world_vo.npz')
    out['Ps'] = {n: Vs[n].astype(np.float64) for n in names}
    return names, gt, N, out


def chain(names, track, gt, H):
    """Kit chain with identity registration (track already in scan frames). Returns aligned achieved, ref (N,1,B,7),
    and the alignment (R, off) mapping perception world -> mocap world for anchor points."""
    N = len(track[names[0]]); B = len(names)
    ach = np.stack([XF.to7(track[n]) for n in names], 1)[:, None].copy()
    ref = np.stack([XF.to7(gt[n][:N]) for n in names], 1)[:, None].copy()
    for s in range(B):
        ca, Rb = XF.reg_of_X(np.eye(4), H[s]['anchor'])
        ach[:, :, s] = T3._convert_object_body(ach[:, :, s], ca, Rb)
        ref[:, :, s, :3] += np.einsum('...ij,j->...i', T3._rotation_matrix(ref[:, :, s, 3:]), H[s]['anchor'])
    axes = [h['axis'] for h in H]
    al = T3._align_registered_scene(ach, ref, axes)
    # recover the world alignment from frame 0 (positions): p_al = R p + off
    ar = T3._rotation_matrix(ref[0, 0, 0, 3:]) @ axes[0]; aa = T3._rotation_matrix(ach[0, 0, 0, 3:]) @ axes[0]
    dr = ref[0, 0, 1, :3] - ref[0, 0, 0, :3]; da = ach[0, 0, 1, :3] - ach[0, 0, 0, :3]
    R = T3._axis_basis(ar, dr) @ T3._axis_basis(aa, da).T; off = ref[0, 0, 0, :3] - R @ ach[0, 0, 0, :3]
    return al, ref, ach, (R, off)


def per_frame(al, ref, H, names):
    res = {}
    for s, n in enumerate(names):
        add = T3._symmetry_point_errors(al[:, :, s], ref[:, :, s], H[s]['points'], H[s]['axis'], H[s]['order'])[:, 0]
        dt = al[:, 0, s, :3] - ref[:, 0, s, :3]
        Ra = T3._rotation_matrix(al[:, 0, s, 3:]); Rr = T3._rotation_matrix(ref[:, 0, s, 3:])
        ax = H[s]['axis']; aa = Ra @ ax; arr = Rr @ ax
        tilt = np.degrees(np.arctan2(np.linalg.norm(np.cross(aa, arr), axis=-1), np.clip((aa * arr).sum(-1), -1, 1)))
        res[n] = dict(add=add, dt=dt, tilt=tilt, axis_ach=aa, axis_ref=arr)
    return res


def reanchor(al, ref):
    """Per-object frame-0 re-anchor (A5-style): left-multiply each object's aligned track by G = ref0 inv(ach0)."""
    out = al.copy(); N, W, B, _ = al.shape
    for s in range(B):
        Ma = np.repeat(np.eye(4)[None], N, 0); Ma[:, :3, :3] = T3._rotation_matrix(al[:, 0, s, 3:]); Ma[:, :3, 3] = al[:, 0, s, :3]
        M0 = np.eye(4); M0[:3, :3] = T3._rotation_matrix(ref[0, 0, s, 3:]); M0[:3, 3] = ref[0, 0, s, :3]
        G = M0 @ np.linalg.inv(Ma[0]); Mn = G[None] @ Ma
        out[:, 0, s, :3] = Mn[:, :3, 3]; out[:, 0, s, 3:] = Rot.from_matrix(Mn[:, :3, :3]).as_quat()
    return out


def best_world(ach, ref, names, H):
    """One rigid world transform fitted over ALL frames (anchor + 2 axis points per object), oracle diagnostic:
    separates frame-0 scene-alignment error from tracking error."""
    P, Q = [], []
    for s in range(len(names)):
        ax = H[s]['axis']; r = 0.05
        Ra = T3._rotation_matrix(ach[:, 0, s, 3:]); Rr = T3._rotation_matrix(ref[:, 0, s, 3:])
        for k in (-r, 0, r):
            P.append(ach[:, 0, s, :3] + k * (Ra @ ax)); Q.append(ref[:, 0, s, :3] + k * (Rr @ ax))
    P = np.concatenate(P); Q = np.concatenate(Q)
    mp, mq = P.mean(0), Q.mean(0); U, _, Vt = np.linalg.svd((P - mp).T @ (Q - mq)); D = np.diag([1, 1, np.sign(np.linalg.det(Vt.T @ U.T))])
    R = Vt.T @ D @ U.T; t = mq - R @ mp
    out = ach.copy(); out[..., :3] = ach[..., :3] @ R.T + t
    q = Rot.from_matrix(R).as_quat()
    out[..., 3:] = T3._quaternion_multiply(q, ach[..., 3:])
    return out


def main():
    names, gt, N, tr = load_tracks()
    H = [XF.host_geometry(T3D, n, s) for s, n in enumerate(names)]
    R = {'names': names, 'N': N}
    # world up from mocap: blue cup axis while at rest at frame 0 (sign: + world z)
    up = T3._rotation_matrix(XF.to7(gt[names[0]][:1])[:, 3:])[0] @ H[0]['axis']
    R['mocap_up_from_blue_axis_f0'] = np.round(up, 4).tolist()
    Z = np.array([0, 0, 1.0])
    # mocap phases: anchor positions in mocap world
    refpos = {}
    for s, n in enumerate(names):
        M = gt[n]; refpos[n] = M[:, :3, 3] + np.einsum('nij,j->ni', M[:, :3, :3], H[s]['anchor'])
    fps = 20.254
    phases = {}
    for s, n in enumerate(names):
        p = refpos[n]; v = np.r_[0, np.linalg.norm(np.diff(p, axis=0), axis=1)] * fps * 100  # cm/s
        Ra = gt[n][:, :3, :3] @ H[s]['axis']
        w = np.r_[0, np.degrees(np.arccos(np.clip((Ra[1:] * Ra[:-1]).sum(-1), -1, 1)))] * fps
        disp = np.linalg.norm(p - p[0], axis=1) * 100
        phases[n] = dict(speed_cm_s=v, tilt_rate_deg_s=w, disp_from_f0_cm=disp, height_cm=(p @ Z) * 100,
                         tilt_vs_up_deg=np.degrees(np.arccos(np.clip(np.abs(Ra @ up), -1, 1))))
    # nesting geometry in mocap world: beige anchor relative to blue anchor, in blue's axis frame
    bl, be = names.index('blue_cup'), names.index('beige_cup')
    Rbl = gt['blue_cup'][:, :3, :3] @ H[bl]['axis']
    d = refpos['beige_cup'] - refpos['blue_cup']; ax_off = (d * Rbl).sum(-1); rad = np.linalg.norm(d - ax_off[:, None] * Rbl, axis=1)
    nest = dict(axial_cm=ax_off * 100, radial_cm=rad * 100, dist_cm=np.linalg.norm(d, axis=1) * 100)
    # hands (perception world = rectified-left camera at frame 0) -> mocap world via the P_o kit alignment
    h = np.load(f'{REF}/hands_refined.npz', allow_pickle=True)
    res_all = {}
    for arm, T in tr.items():
        al, ref, ach, (Ra_, off) = chain(names, T, gt, H)
        pf = per_frame(al, ref, H, names)
        ra = reanchor(al, ref); pfr = per_frame(ra, ref, H, names)
        bw = best_world(ach, ref, names, H); pfb = per_frame(bw, ref, H, names)
        res_all[arm] = dict(pf=pf, pfr=pfr, pfb=pfb, align=(Ra_, off), al=al, ref=ref)
    # hand distance (GT-free proxy uses perceived P_s anchor in perception world; also report mocap-mapped)
    Ra_, off = res_all['Ps']['align']
    hand = {}
    for side in ('left', 'right'):
        J = h[f'joints_{side}'].astype(np.float64); valid = h[f'valid_{side}']
        Jm = J @ Ra_.T + off
        for s, n in enumerate(names):
            dm = np.linalg.norm(Jm - refpos[n][:, None], axis=-1).min(-1) * 100
            dm[~valid] = np.nan
            hand.setdefault(n, {})[side] = dm
    for n in names:
        hand[n]['min'] = np.fmin(hand[n]['left'], hand[n]['right'])
    # summaries
    def seg_stats(e, idx):
        idx = np.asarray(idx, int)
        if len(idx) == 0:
            return None
        return dict(n=int(len(idx)), add_med_cm=round(float(np.median(e[idx]) * 100), 2), add_max_cm=round(float(e[idx].max() * 100), 2), auc=round(auc_of(e[idx]), 4))
    summ = {}
    for arm, r in res_all.items():
        summ[arm] = {}
        for n in names:
            e = r['pf'][n]['add']; er = r['pfr'][n]['add']; eb = r['pfb'][n]['add']
            summ[arm][n] = dict(auc=round(auc_of(e), 4), auc_reanchor_f0=round(auc_of(er), 4), auc_bestworld=round(auc_of(eb), 4),
                                add_f0_cm=round(float(e[0] * 100), 2), add_med_cm=round(float(np.median(e) * 100), 2),
                                add_max_cm=round(float(e.max() * 100), 2), tilt_f0_deg=round(float(r['pf'][n]['tilt'][0]), 2),
                                dt_f0_cm=np.round(r['pf'][n]['dt'][0] * 100, 2).tolist())
        summ[arm]['episode_auc'] = round(float(np.mean([summ[arm][n]['auc'] for n in names])), 4)
        summ[arm]['episode_auc_reanchor'] = round(float(np.mean([summ[arm][n]['auc_reanchor_f0'] for n in names])), 4)
        summ[arm]['episode_auc_bestworld'] = round(float(np.mean([summ[arm][n]['auc_bestworld'] for n in names])), 4)
    R['summary'] = summ
    # per-frame table
    rows = []
    for i in range(N):
        row = dict(f=i)
        for n in names:
            ph = phases[n]
            row[n] = dict(speed=round(float(ph['speed_cm_s'][i]), 1), disp=round(float(ph['disp_from_f0_cm'][i]), 1),
                          tilt_up=round(float(ph['tilt_vs_up_deg'][i]), 1),
                          hand_cm=None if np.isnan(hand[n]['min'][i]) else round(float(hand[n]['min'][i]), 1))
            for arm in res_all:
                pf = res_all[arm]['pf'][n]
                row[n][arm] = dict(add=round(float(pf['add'][i] * 100), 2), t=round(float(np.linalg.norm(pf['dt'][i]) * 100), 2),
                                   dz=round(float(pf['dt'][i] @ Z * 100), 2), tilt=round(float(pf['tilt'][i]), 1),
                                   add_re=round(float(res_all[arm]['pfr'][n]['add'][i] * 100), 2),
                                   add_bw=round(float(res_all[arm]['pfb'][n]['add'][i] * 100), 2))
        row['nest'] = dict(axial=round(float(nest['axial_cm'][i]), 2), radial=round(float(nest['radial_cm'][i]), 2))
        rows.append(row)
    R['frames'] = rows
    # phase segmentation on mocap (moving if speed > 3 cm/s or tilt rate > 15 deg/s, smoothed over 5 frames)
    seg = {}
    for n in names:
        mv = (np.convolve(phases[n]['speed_cm_s'], np.ones(5) / 5, 'same') > 3) | (np.convolve(phases[n]['tilt_rate_deg_s'], np.ones(5) / 5, 'same') > 15)
        segs = []; st = 0
        for i in range(1, N + 1):
            if i == N or mv[i] != mv[st]:
                segs.append([int(st), int(i - 1), 'moving' if mv[st] else 'rest']); st = i
        seg[n] = segs
    R['segments_mocap'] = seg
    # phase-split stats
    nested = (np.abs(nest['radial_cm']) < 3.0) & (nest['axial_cm'] < 12)
    R['nested_frames'] = [int(i) for i in np.where(nested)[0]]
    split = {}
    for arm, r in res_all.items():
        split[arm] = {}
        for n in names:
            mv = np.zeros(N, bool)
            for a, b, k in seg[n]:
                if k == 'moving':
                    mv[a:b + 1] = True
            hn = np.nan_to_num(hand[n]['min'], nan=99) < 8
            e = r['pf'][n]['add']
            split[arm][n] = {k: seg_stats(e, np.where(m)[0]) for k, m in dict(
                rest_hand_far=(~mv) & (~hn), rest_hand_near=(~mv) & hn, moving=mv, nested=nested, not_nested=~nested,
                before_first_move=np.arange(N) < (np.where(mv)[0][0] if mv.any() else N)).items()}
    R['split'] = split
    R['nest_summary'] = dict(first_nested=int(np.where(nested)[0][0]) if nested.any() else None,
                             axial_cm_nested_med=round(float(np.median(nest['axial_cm'][nested])), 2) if nested.any() else None)
    json.dump(R, open(sys.argv[1], 'w'), indent=1, default=lambda o: o.tolist() if hasattr(o, 'tolist') else str(o))
    print(json.dumps(dict(summary=summ, segments=seg, nest=R['nest_summary'], up=R['mocap_up_from_blue_axis_f0']), indent=1))
    np.savez(sys.argv[1].replace('.json', '_arrays.npz'), **{f'{arm}_{k}_{n}': res_all[arm][k][n]['add'] for arm in res_all for k in ('pf', 'pfr', 'pfb') for n in names},
             **{f'{arm}_al': res_all[arm]['al'] for arm in res_all}, ref=res_all['Ps']['ref'],
             **{f'{arm}_R': res_all[arm]['align'][0] for arm in res_all}, **{f'{arm}_off': res_all[arm]['align'][1] for arm in res_all},
             nest_axial=nest['axial_cm'], nest_radial=nest['radial_cm'], **{f'hand_{n}': hand[n]['min'] for n in names})


if __name__ == '__main__':
    main()
