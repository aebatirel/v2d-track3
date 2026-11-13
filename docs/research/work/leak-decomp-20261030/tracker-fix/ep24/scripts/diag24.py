"""ORACLE DIAGNOSTIC (public ep24 only): per-frame error of the Phase-1 tracks vs mocap, in the * convention.
Reads ground truth (mocap, scans). Nothing here feeds eval inference.
Usage: python -I diag24.py OUT_JSON
"""
import json, os, sys
import numpy as np
from scipy.spatial.transform import Rotation as Rot
from scipy.spatial import cKDTree

REPO = '/home/user/v2d-track3'
S = '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad'
sys.path.insert(0, f'{REPO}/tools')
import xstar_fit as XF  # noqa: E402

EP = 24
KIT = f'{S}/map/scoring/kit/v2d_submission_kit'; T3D = f'{S}/map/scoring/t3'
RUN = f'{S}/leak/p1/runs/20261030-orcP1c-87fc869/results/leak_p1/ep24'
REF = f'{S}/refine/in/ep24'
XG = json.load(open(f'{REPO}/docs/research/work/leak-decomp-20261030/tierA/xstar_geom.json'))['objects']
XF.kit(KIT); T3 = XF.K['T3']
THR = np.arange(0.01, 0.10, 0.01); TW = np.r_[0.5, np.ones(7), 0.5] / 8
Z = np.array([0, 0, 1.0])


def auc_of(e):  # per-frame ADD (m) -> kit AUC
    return float(np.mean((e[:, None] < THR[None]).astype(float) @ TW)) if len(e) else float('nan')


def load_tracks():
    names, gt = XF.mocap(T3D, EP, None)
    N = len(gt[names[0]])
    out = {}
    lib2scan = lambda V: {n: V[n].astype(np.float64) @ np.linalg.inv(np.asarray(XG[n]['X_scan_T_lib'])) for n in names}
    out['Po'] = lib2scan(np.load(f'{RUN}/perc2/poses_world_vo.npz'))
    out['Po2'] = lib2scan(np.load(f'{RUN}/perc2rep/poses_world_vo.npz'))
    out['Pr'] = lib2scan(np.load(f'{REF}/poses_world_vo.npz'))
    Vs = np.load(f'{RUN}/perc2scan/poses_world_vo.npz')
    out['Ps'] = {n: Vs[n].astype(np.float64) for n in names}
    return names, gt, N, out


def chain(names, track, gt, H, align=True):
    N = len(track[names[0]]); B = len(names)
    ach = np.stack([XF.to7(track[n]) for n in names], 1)[:, None].copy()
    ref = np.stack([XF.to7(gt[n][:N]) for n in names], 1)[:, None].copy()
    for s in range(B):
        ca, Rb = XF.reg_of_X(np.eye(4), H[s]['anchor'])
        ach[:, :, s] = T3._convert_object_body(ach[:, :, s], ca, Rb)
        ref[:, :, s, :3] += np.einsum('...ij,j->...i', T3._rotation_matrix(ref[:, :, s, 3:]), H[s]['anchor'])
    axes = [h['axis'] for h in H]
    al = T3._align_registered_scene(ach, ref, axes)
    # world alignment (anchor slot 0 full pose, boards have no symmetry axis)
    qa = ach[0, 0, 0, 3:]; qr = ref[0, 0, 0, 3:]
    q = T3._quaternion_multiply(qr, qa * [-1, -1, -1, 1]); R = T3._rotation_matrix(q)
    off = ref[0, 0, 0, :3] - R @ ach[0, 0, 0, :3]
    return al, ref, ach, (R, off)


def rot_err_deg(qa, qr):
    Ra = Rot.from_quat(qa); Rr = Rot.from_quat(qr)
    return np.degrees((Ra.inv() * Rr).magnitude())


def per_frame(al, ref, H, names):
    res = {}
    for s, n in enumerate(names):
        add = T3._symmetry_point_errors(al[:, :, s], ref[:, :, s], H[s]['points'], H[s]['axis'], H[s]['order'])[:, 0]
        dt = al[:, 0, s, :3] - ref[:, 0, s, :3]
        rot = rot_err_deg(al[:, 0, s, 3:], ref[:, 0, s, 3:])
        # rotation error axis in the BODY frame of the reference (which body axis the error is about)
        Ra = Rot.from_quat(al[:, 0, s, 3:]); Rr = Rot.from_quat(ref[:, 0, s, 3:])
        rv_body = (Rr.inv() * Ra).as_rotvec()  # body-frame error rotation
        res[n] = dict(add=add, dt=dt, rot=rot, rv_body=rv_body)
    return res


def best_world(ach, ref, names, H):
    """One rigid world transform fitted over ALL frames on the host points of every object (oracle diagnostic):
    separates the kit's frame-0 scene pin from tracking error."""
    P, Q = [], []
    for s in range(len(names)):
        pts = H[s]['points'][::20]
        Ra = T3._rotation_matrix(ach[:, 0, s, 3:]); Rr = T3._rotation_matrix(ref[:, 0, s, 3:])
        P.append((np.einsum('nij,vj->nvi', Ra, pts) + ach[:, 0, s, None, :3]).reshape(-1, 3))
        Q.append((np.einsum('nij,vj->nvi', Rr, pts) + ref[:, 0, s, None, :3]).reshape(-1, 3))
    P = np.concatenate(P); Q = np.concatenate(Q)
    mp, mq = P.mean(0), Q.mean(0); U, _, Vt = np.linalg.svd((P - mp).T @ (Q - mq))
    D = np.diag([1, 1, np.sign(np.linalg.det(Vt.T @ U.T))])
    R = Vt.T @ D @ U.T; t = mq - R @ mp
    out = ach.copy(); out[..., :3] = ach[..., :3] @ R.T + t
    out[..., 3:] = T3._quaternion_multiply(Rot.from_matrix(R).as_quat(), ach[..., 3:])
    return out, (R, t)


def pca_axes(pts):
    w, U = np.linalg.eigh(np.cov(pts.T))
    return U[:, ::-1], np.sqrt(w[::-1])  # columns: long, mid, short(normal)


def main():
    names, gt, N, tr = load_tracks()
    H = [XF.host_geometry(T3D, n, s) for s, n in enumerate(names)]
    R = {'names': names, 'N': N}
    ax = {n: pca_axes(H[s]['points']) for s, n in enumerate(names)}
    R['pca_sd_cm'] = {n: np.round(ax[n][1] * 100, 2).tolist() for n in names}
    # mocap anchor positions, phases
    refpos = {}
    for s, n in enumerate(names):
        M = gt[n]; refpos[n] = M[:, :3, 3] + np.einsum('nij,j->ni', M[:, :3, :3], H[s]['anchor'])
    fps = 20.0
    phases = {}
    for s, n in enumerate(names):
        p = refpos[n]; v = np.r_[0, np.linalg.norm(np.diff(p, axis=0), axis=1)] * fps * 100
        Rm = gt[n][:, :3, :3]
        w = np.r_[0, np.degrees(Rot.from_matrix(Rm[1:] @ np.transpose(Rm[:-1], (0, 2, 1))).magnitude())] * fps
        disp = np.linalg.norm(p - p[0], axis=1) * 100
        nrm = Rm @ ax[n][0][:, 2]  # board normal in world
        tilt_from_up = np.degrees(np.arccos(np.clip(np.abs(nrm @ Z), -1, 1)))  # 0 = lying flat, 90 = on edge
        rot_from_f0 = np.degrees(Rot.from_matrix(Rm @ Rm[0].T).magnitude())
        phases[n] = dict(speed_cm_s=v, rot_rate_deg_s=w, disp_from_f0_cm=disp, height_cm=p @ Z * 100,
                         normal_tilt_deg=tilt_from_up, rot_from_f0_deg=rot_from_f0)
    # contact between the boards in mocap: min distance between scan surface samples
    pts = {}
    for s, n in enumerate(names):
        v, f = H[s]['mesh']; pts[n] = XF.K['sample'](v, f, 3000, 11)
    gap = np.zeros(N)
    for i in range(N):
        A = (gt[names[0]][i, :3, :3] @ pts[names[0]].T).T + gt[names[0]][i, :3, 3]
        B = (gt[names[1]][i, :3, :3] @ pts[names[1]].T).T + gt[names[1]][i, :3, 3]
        gap[i] = cKDTree(B).query(A, k=1)[0].min() * 100
    cdist = np.linalg.norm(refpos[names[0]] - refpos[names[1]], axis=1) * 100
    nrm0 = gt[names[0]][:, :3, :3] @ ax[names[0]][0][:, 2]; nrm1 = gt[names[1]][:, :3, :3] @ ax[names[1]][0][:, 2]
    rel_ang = np.degrees(np.arccos(np.clip(np.abs((nrm0 * nrm1).sum(-1)), -1, 1)))
    R['contact'] = dict(gap_cm=np.round(gap, 2).tolist(), centre_dist_cm=np.round(cdist, 2).tolist(), normal_angle_deg=np.round(rel_ang, 1).tolist())
    # tracks through the kit chain
    h = np.load(f'{REF}/hands_refined.npz', allow_pickle=True)
    res_all = {}
    for arm, T in tr.items():
        al, ref, ach, (Ra_, off) = chain(names, T, gt, H)
        pf = per_frame(al, ref, H, names)
        bw, (Rb, tb) = best_world(ach, ref, names, H); pfb = per_frame(bw, ref, H, names)
        # rotation between the kit's pin and the best world transform: the pin's injected error
        dR = Ra_ @ Rb.T; pin_deg = float(np.degrees(Rot.from_matrix(dR).magnitude()))
        pin_axis = Rot.from_matrix(dR).as_rotvec(); pin_axis = pin_axis / (np.linalg.norm(pin_axis) + 1e-12)
        res_all[arm] = dict(pf=pf, pfb=pfb, align=(Ra_, off), best=(Rb, tb), al=al, ref=ref, ach=ach, bw=bw,
                            pin_deg=pin_deg, pin_axis=pin_axis)
    # flips and swaps (kit-aligned and best-world): ADD of the track vs mocap with 180 deg about each body PCA axis,
    # and the cross-identity centre distance
    flips = {}
    for arm in ('Po', 'Ps'):
        flips[arm] = {}
        for view in ('pf', 'pfb'):
            A = res_all[arm]['al'] if view == 'pf' else res_all[arm]['bw']; ref = res_all[arm]['ref']
            for s, n in enumerate(names):
                P0 = H[s]['points']
                Rr = T3._rotation_matrix(ref[:, 0, s, 3:]); Ra = T3._rotation_matrix(A[:, 0, s, 3:])
                tgt = np.einsum('nij,vj->nvi', Rr, P0) + ref[:, 0, s, None, :3]
                d = {}
                for k, lab in enumerate(('long', 'mid', 'normal')):
                    F = Rot.from_rotvec(np.pi * ax[n][0][:, k]).as_matrix()
                    mv = np.einsum('nij,vj->nvi', Ra, P0 @ F.T) + A[:, 0, s, None, :3]
                    d[lab] = np.linalg.norm(mv - tgt, axis=-1).mean(-1)
                mv = np.einsum('nij,vj->nvi', Ra, P0) + A[:, 0, s, None, :3]
                d['none'] = np.linalg.norm(mv - tgt, axis=-1).mean(-1)
                # cross identity: track of n vs mocap of the other board (centre distance)
                o = 1 - s
                d['centre_self'] = np.linalg.norm(A[:, 0, s, :3] - ref[:, 0, s, :3], axis=-1)
                d['centre_other'] = np.linalg.norm(A[:, 0, s, :3] - ref[:, 0, o, :3], axis=-1)
                flips[arm][f'{view}_{n}'] = {k: np.round(v * 100, 2) for k, v in d.items()}
    # hands (perception world) -> mocap world via the best-world fit of P_s (display/proxy only)
    Rb, tb = res_all['Ps']['best']
    hand = {}
    for side in ('left', 'right'):
        J = h[f'joints_{side}'].astype(np.float64); valid = h[f'valid_{side}']
        Jm = J @ Rb.T + tb
        for s, n in enumerate(names):
            # distance to the board surface (mocap pose), not its centre: boards are 23 cm long
            P = np.einsum('nij,vj->nvi', gt[n][:, :3, :3], pts[n][::10]) + gt[n][:, None, :3, 3]
            dm = np.array([cKDTree(P[i]).query(Jm[i], k=1)[0].min() for i in range(N)]) * 100
            dm[~valid] = np.nan
            hand.setdefault(n, {})[side] = dm
    for n in names:
        hand[n]['min'] = np.fmin(hand[n]['left'], hand[n]['right'])
    # mocap phase segmentation (moving if speed > 3 cm/s or rot rate > 15 deg/s, smoothed over 5 frames)
    seg = {}; moving = {}
    for n in names:
        mv = (np.convolve(phases[n]['speed_cm_s'], np.ones(5) / 5, 'same') > 3) | (np.convolve(phases[n]['rot_rate_deg_s'], np.ones(5) / 5, 'same') > 15)
        moving[n] = mv
        segs = []; st = 0
        for i in range(1, N + 1):
            if i == N or mv[i] != mv[st]:
                segs.append([int(st), int(i - 1), 'moving' if mv[st] else 'rest']); st = i
        seg[n] = segs
    R['segments_mocap'] = seg

    def seg_stats(e, idx):
        idx = np.asarray(idx, int)
        if len(idx) == 0:
            return None
        return dict(n=int(len(idx)), add_med_cm=round(float(np.median(e[idx]) * 100), 2), add_max_cm=round(float(e[idx].max() * 100), 2), auc=round(auc_of(e[idx]), 4))
    summ = {}
    for arm, r in res_all.items():
        summ[arm] = dict(pin_vs_bestworld_deg=round(r['pin_deg'], 2), pin_axis_world=np.round(r['pin_axis'], 3).tolist())
        for n in names:
            e = r['pf'][n]['add']; eb = r['pfb'][n]['add']
            summ[arm][n] = dict(auc=round(auc_of(e), 4), auc_bestworld=round(auc_of(eb), 4),
                                add_f0_cm=round(float(e[0] * 100), 2), add_med_cm=round(float(np.median(e) * 100), 2),
                                add_max_cm=round(float(e.max() * 100), 2), rot_f0_deg=round(float(r['pf'][n]['rot'][0]), 2),
                                rot_med_deg=round(float(np.median(r['pf'][n]['rot'])), 2), rot_max_deg=round(float(r['pf'][n]['rot'].max()), 1),
                                bw_add_med_cm=round(float(np.median(eb) * 100), 2), bw_add_max_cm=round(float(eb.max() * 100), 2),
                                bw_rot_med_deg=round(float(np.median(r['pfb'][n]['rot'])), 2), bw_rot_max_deg=round(float(r['pfb'][n]['rot'].max()), 1),
                                bw_add_f0_cm=round(float(eb[0] * 100), 2), bw_rot_f0_deg=round(float(r['pfb'][n]['rot'][0]), 2),
                                bw_rv_body_f0_deg=np.round(np.degrees(r['pfb'][n]['rv_body'][0]), 2).tolist())
        summ[arm]['episode_auc'] = round(float(np.mean([summ[arm][n]['auc'] for n in names])), 4)
        summ[arm]['episode_auc_bestworld'] = round(float(np.mean([summ[arm][n]['auc_bestworld'] for n in names])), 4)
    R['summary'] = summ
    # split by phase
    split = {}
    contact = gap < 0.5
    for arm, r in res_all.items():
        split[arm] = {}
        for n in names:
            mv = moving[n]; hn = np.nan_to_num(hand[n]['min'], nan=99) < 5
            first_mv = int(np.where(mv)[0][0]) if mv.any() else N
            for view in ('pf', 'pfb'):
                e = r[view][n]['add']
                split[arm][f'{view}_{n}'] = {k: seg_stats(e, np.where(m)[0]) for k, m in dict(
                    before_first_move=np.arange(N) < first_mv, rest_hand_far=(~mv) & (~hn), rest_hand_near=(~mv) & hn,
                    moving=mv, boards_in_contact=contact, boards_apart=~contact).items()}
    R['split'] = split
    # per-frame rows
    rows = []
    for i in range(N):
        row = dict(f=i, gap=round(float(gap[i]), 2), cdist=round(float(cdist[i]), 1), nang=round(float(rel_ang[i]), 1))
        for n in names:
            ph = phases[n]
            row[n] = dict(speed=round(float(ph['speed_cm_s'][i]), 1), disp=round(float(ph['disp_from_f0_cm'][i]), 1),
                          tilt=round(float(ph['normal_tilt_deg'][i]), 1), rotf0=round(float(ph['rot_from_f0_deg'][i]), 1),
                          hz=round(float(ph['height_cm'][i] - ph['height_cm'][0]), 1), mv=bool(moving[n][i]),
                          hand=None if np.isnan(hand[n]['min'][i]) else round(float(hand[n]['min'][i]), 1))
            for arm in res_all:
                pf = res_all[arm]['pf'][n]; pb = res_all[arm]['pfb'][n]
                row[n][arm] = dict(add=round(float(pf['add'][i] * 100), 2), t=round(float(np.linalg.norm(pf['dt'][i]) * 100), 2),
                                   rot=round(float(pf['rot'][i]), 1), bw_add=round(float(pb['add'][i] * 100), 2),
                                   bw_t=round(float(np.linalg.norm(pb['dt'][i]) * 100), 2), bw_rot=round(float(pb['rot'][i]), 1))
            for arm in flips:
                fl = flips[arm]
                row[n][arm + '_flip'] = {k: float(fl[f'pfb_{n}'][k][i]) for k in ('none', 'long', 'mid', 'normal', 'centre_self', 'centre_other')}
        rows.append(row)
    R['frames'] = rows
    # flip / swap summary: frames where a 180 deg flip or the other identity fits better
    fs = {}
    for arm in flips:
        for key, d in flips[arm].items():
            best_alt = np.minimum.reduce([d['long'], d['mid'], d['normal']])
            fs[f'{arm}_{key}'] = dict(frames_flip_better=int((best_alt < d['none']).sum()),
                                      frames_other_identity_closer=int((d['centre_other'] < d['centre_self']).sum()),
                                      none_med=float(np.median(d['none'])), long_med=float(np.median(d['long'])),
                                      mid_med=float(np.median(d['mid'])), normal_med=float(np.median(d['normal'])))
    R['flip_swap'] = fs
    json.dump(R, open(sys.argv[1], 'w'), indent=1, default=lambda o: o.tolist() if hasattr(o, 'tolist') else str(o))
    print(json.dumps(dict(summary=summ, segments=seg, flip_swap=fs, pca=R['pca_sd_cm']), indent=1))
    np.savez(sys.argv[1].replace('.json', '_arrays.npz'),
             **{f'{arm}_{v}_{k}_{n}': res_all[arm][v][n][k] for arm in res_all for v in ('pf', 'pfb') for k in ('add', 'dt', 'rot', 'rv_body') for n in names},
             **{f'{arm}_al': res_all[arm]['al'] for arm in res_all}, **{f'{arm}_bw': res_all[arm]['bw'] for arm in res_all},
             **{f'{arm}_ach': res_all[arm]['ach'] for arm in res_all}, ref=res_all['Ps']['ref'],
             **{f'{arm}_Rkit': res_all[arm]['align'][0] for arm in res_all}, **{f'{arm}_tkit': res_all[arm]['align'][1] for arm in res_all},
             **{f'{arm}_Rbw': res_all[arm]['best'][0] for arm in res_all}, **{f'{arm}_tbw': res_all[arm]['best'][1] for arm in res_all},
             gap=gap, cdist=cdist, rel_ang=rel_ang, **{f'hand_{n}': hand[n]['min'] for n in names},
             **{f'mv_{n}': moving[n] for n in names})


if __name__ == '__main__':
    main()
