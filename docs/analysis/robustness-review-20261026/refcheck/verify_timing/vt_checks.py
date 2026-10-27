"""verify_timing: independent spot checks (27 Oct 2026, CPU). Own code; see VERIFY.md in ../timing.

  A. quaternion-order sanity (mocap w-first, reference wxyz) via conjugation-invariant rotation-from-rest angles
  B. false motion of resting objects: ep11 blue cup, ep24 board 2, ep31 sweeper, ep13 cup tail
  C. ep11 beige cup spin vs axis swing between f0 and f1
  D. mocap rest-noise floor
  E. physical onsets (my own walk-back rule) for the objects the other check quotes
Usage: python -I vt_checks.py OUT.json
"""
import sys, os, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vt_load as L
from vt_lag import principal_axis, rot_from_rest, cross

FPS = 1 / 0.04937264323234558


def ang(Ra, Rb):
    c = np.clip((np.trace(np.einsum('...ji,...jk->...ik', Ra, Rb), axis1=-2, axis2=-1) - 1) / 2, -1, 1)
    return np.degrees(np.arccos(c))


def speed(P):
    v = np.zeros(len(P)); v[1:-1] = np.linalg.norm(P[2:] - P[:-2], axis=1) / 2 * FPS * 100
    v[0], v[-1] = v[1], v[-2]
    return v


def rrate(R):
    w = np.zeros(len(R)); w[1:-1] = ang(R[2:], R[:-2]) / 2 * FPS
    w[0], w[-1] = w[1], w[-2]
    return w


def phys_onset(P, R, t1cm, vthr=1.0, wthr=10.0):
    v, w = speed(P), rrate(R)
    k = int(np.floor(t1cm))
    while k > 0 and (v[k - 1] >= vthr or w[k - 1] >= wthr):
        k -= 1
    return k


def phys_offset(P, R, vthr=1.0, wthr=10.0):
    """last frame where the object is moving (speed or rate above threshold), searched backwards from the end."""
    v, w = speed(P), rrate(R)
    mov = np.where((v >= vthr) | (w >= wthr))[0]
    return int(mov[-1]) if len(mov) else None


def main():
    C = L.canon(); out = {}
    # ---- A. quaternion order -------------------------------------------------------------------------------
    A = {}
    for ep, n in ((39, 'mini_dust_pan'), (12, 'blue_cup'), (24, 'wooden_piece_1'), (21, 'water_pitcher')):
        e = C[ep]; names, gt = L.load_mocap(ep)
        P = L.load_npz(f"{L.STORE}/{e['perception_path']}")
        fin, _ = L.ref_paths(e)
        ref = L.load_refpq(fin)
        Rg, Ro, Rr = gt[n][:, :3, :3], P[n][:, :3, :3], ref[n][:, :3, :3]
        a_gt = ang(Rg, Rg[:1]); a_o = ang(Ro, Ro[:1])
        # wrong order: treat parquet [qw,qx,qy,qz] as [qx,qy,qz,qw]
        import pyarrow.parquet as pq
        tab = pq.read_table(f'{L.T3}/ep{ep}.parquet', columns=['observation.objects']).to_pandas()
        Q = np.stack([np.asarray([o for o in r if str(o['name']) == n][0]['pose'], float) for r in tab['observation.objects']])
        Rw = L.quat_wxyz_to_R(Q[:, [6, 3, 4, 5]])          # misread: w taken from the last slot
        a_w = ang(Rw, Rw[:1])
        D = np.einsum('tij,tkj->tik', Rr, Ro)              # R_ref R_perc^T, should be constant
        A[f'ep{ep}:{n}'] = dict(
            corr_rot_from_f0_correct=round(float(np.corrcoef(a_gt, a_o)[0, 1]), 3),
            corr_rot_from_f0_misread=round(float(np.corrcoef(a_w, a_o)[0, 1]), 3),
            median_abs_diff_deg_correct=round(float(np.median(np.abs(a_gt - a_o))), 2),
            median_abs_diff_deg_misread=round(float(np.median(np.abs(a_w - a_o))), 2),
            ref_vs_perc_rot_spread_deg=round(float(ang(D, D[:1]).max()), 3),
            gt_upright_z_dot=round(float(np.median(Rg[:, 2, 2])), 3))
    out['A_quaternion'] = A
    # ---- B/E. false motion + onsets --------------------------------------------------------------------------
    B = {}
    for ep, n in ((11, 'blue_cup'), (11, 'beige_cup'), (24, 'wooden_piece_2'), (24, 'wooden_piece_1'), (31, 'mini_sweeper'),
                  (13, 'blue_cup'), (31, 'plastic_dish_rack'), (12, 'plastic_dish_rack')):
        e = C[ep]; names, gt = L.load_mocap(ep)
        cg = L.surf_centroid(L.scan_mesh(n)); Pg = L.point_path(gt[n], cg)
        dg = np.linalg.norm(Pg - Pg[:5].mean(0), axis=1)
        axg = principal_axis(L.scan_mesh(n)) if 'cup' in n else None
        t1 = cross(dg, 0.01)
        row = dict(gt_max_disp_from_start_cm=round(float(dg.max() * 100), 2),
                   gt_rot_from_start_max_deg=round(float(rot_from_rest(gt[n], axg).max()), 2),
                   gt_1cm_cross=None if t1 is None else round(t1, 2))
        if t1 is not None:
            row['gt_phys_onset'] = phys_onset(Pg, gt[n][:, :3, :3] if axg is None else gt[n][:, :3, :3], t1)
            row['gt_phys_offset_last_moving'] = phys_offset(Pg, gt[n][:, :3, :3])
        fin, _ = L.ref_paths(e)
        srcs = {'perc': (L.load_npz(f"{L.STORE}/{e['perception_path']}"), L.lib_of(e, 'perc'))}
        if fin:
            srcs['ref'] = (L.load_refpq(fin), L.lib_of(e, 'ref'))
        for s, (P, lib) in srcs.items():
            co = L.surf_centroid(L.our_mesh(lib, n)); Po = L.point_path(P[n], co)
            do = np.linalg.norm(Po - Po[:5].mean(0), axis=1)
            axo = principal_axis(L.our_mesh(lib, n)) if 'cup' in n else None
            ro = rot_from_rest(P[n], axo)
            first = cross(do, 0.01)
            d = dict(max_disp_cm=round(float(do.max() * 100), 2), argmax=int(do.argmax()),
                     first_1cm_3frames=None if first is None else round(first, 2),
                     frames_over_1cm=int((do > 0.01).sum()),
                     max_swing_or_rot_deg=round(float(ro.max()), 2))
            if t1 is not None:
                on = row['gt_phys_onset']
                d['before_true_onset'] = dict(max_disp_cm=round(float(do[:on].max() * 100), 2),
                                              frames_over_1cm=int((do[:on] > 0.01).sum()),
                                              max_rot_deg=round(float(ro[:on].max()), 2))
                off = row['gt_phys_offset_last_moving']
                # tail: displacement from OUR own end rest (median of last 10 frames) after the true offset
                Pend = np.median(Po[-10:], 0); de = np.linalg.norm(Po - Pend, axis=1)
                d['after_true_offset'] = dict(max_disp_from_own_end_rest_cm=round(float(de[off:].max() * 100), 2),
                                              frames_over_1cm=int((de[off:] > 0.01).sum()))
            row[s] = d
        B[f'ep{ep}:{n}'] = row
    out['B_false_motion'] = B
    # ---- C. ep11 beige cup spin vs swing f0->f1 -----------------------------------------------------------------
    e = C[11]
    Cc = {}
    for s, P, lib in (('perc', L.load_npz(f"{L.STORE}/{e['perception_path']}"), L.lib_of(e, 'perc')),
                      ('ref', L.load_refpq(L.ref_paths(e)[0]), L.lib_of(e, 'ref'))):
        for n in ('beige_cup', 'blue_cup'):
            R = P[n][:, :3, :3]; ax = principal_axis(L.our_mesh(lib, n))
            full = [round(float(ang(R[k + 1], R[k])), 2) for k in range(4)]
            swing = [round(float(np.degrees(np.arccos(np.clip((R[k + 1] @ ax) @ (R[k] @ ax), -1, 1)))), 2) for k in range(4)]
            full0 = [round(float(ang(R[k], R[0])), 2) for k in range(0, 40, 4)]
            Cc[f'{s}:{n}'] = dict(full_rot_step_f0_f4=full, swing_step_f0_f4=swing, full_rot_from_f0_every4=full0)
    _, gt = L.load_mocap(11)
    for n in ('beige_cup', 'blue_cup'):
        R = gt[n][:, :3, :3]; ax = principal_axis(L.scan_mesh(n))
        Cc[f'mocap:{n}'] = dict(full_rot_step_f0_f4=[round(float(ang(R[k + 1], R[k])), 2) for k in range(4)],
                                swing_step_f0_f4=[round(float(np.degrees(np.arccos(np.clip((R[k + 1] @ ax) @ (R[k] @ ax), -1, 1)))), 2) for k in range(4)])
    out['C_ep11_spin'] = Cc
    # ---- D. mocap rest noise floor ------------------------------------------------------------------------------
    sp, rr = [], []
    for ep in L.PUBLIC:
        names, gt = L.load_mocap(ep)
        for n in names:
            cg = L.surf_centroid(L.scan_mesh(n)); Pg = L.point_path(gt[n], cg)
            dg = np.linalg.norm(Pg - Pg[:5].mean(0), axis=1)
            v, w = speed(Pg), rrate(gt[n][:, :3, :3])
            rest = (v < 1.0) & (w < 10.0)
            # dilate the moving mask by 5 frames so rest = well away from motion
            mov = ~rest; k = np.convolve(mov.astype(float), np.ones(11), 'same') > 0
            rest = ~k
            if rest.sum() > 20:
                sp.append((ep, n, float(np.percentile(v[rest], 95)), float(np.percentile(w[rest], 95)), int(rest.sum())))
    S = np.array([x[2] for x in sp]); W = np.array([x[3] for x in sp])
    out['D_noise_floor_mocap_raw_central_diff'] = dict(n_objects=len(sp), speed_p95_cms_median=round(float(np.median(S)), 3),
                                                     speed_p95_cms_max=round(float(S.max()), 3),
                                                     rot_p95_degs_median=round(float(np.median(W)), 2),
                                                     rot_p95_degs_max=round(float(W.max()), 2),
                                                     per_object=[(a, b, round(c, 3), round(d, 2), f) for a, b, c, d, f in sp])
    json.dump(out, open(sys.argv[1], 'w'), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != 'D_noise_floor_mocap_raw_central_diff'}, indent=1))
    print({k: v for k, v in out['D_noise_floor_mocap_raw_central_diff'].items() if k != 'per_object'})


if __name__ == '__main__':
    main()
