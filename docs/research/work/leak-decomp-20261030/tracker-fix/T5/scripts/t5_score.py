"""T5 scoring (ORACLE: reads public mocap; run only after vo_t5.py has written its cameras). Public ep24 only.

For each camera W' (RUNS/<run>/W_<variant>.npy, world_T_cam) the object tracks are recomposed, nothing else changes:
  P_o (eval-like arm, library_v3 meshes): world pose = W'[t] @ cam_T_obj[t] from the Phase-1 perc2 poses.npz;
  P_s (scan-template arm, secondary): W'[t] @ inv(W_base[t]) @ (its stored world pose) (all Phase-1 arms share one camera).
Scores (tools/xstar_fit.py score_track, the kit's chain): * = X*_geom registration (P_o), lib = the kit's own registration
of our mesh (X_kit, the leaderboard convention), P_s * = scan frames. Common-mode error as
../ep24/scripts/vo_oracle_screen.py (after the kit's frame-0 alignment, * convention: mean over objects of the anchor
translation error vs mocap, smoothed over 9 frames; median and p90 over frames, plus per phase) and the AUC with it removed.
Usage: python -I t5_score.py RUNS OUT_JSON run:variant[,run:variant...]
"""
import json, sys
import numpy as np

REPO = '/home/user/v2d-track3'
S = '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad'
sys.path.insert(0, f'{REPO}/tools')
import xstar_fit as XF  # noqa: E402

KIT = f'{S}/map/scoring/kit/v2d_submission_kit'; T3D = f'{S}/map/scoring/t3'; LIB = f'{REPO}/meshes/library_v3'
XG = json.load(open(f'{REPO}/docs/research/work/leak-decomp-20261030/tierA/xstar_geom.json'))['objects']
P1 = f'{S}/leak/p1/runs/20261030-orcP1c-87fc869/results/leak_p1/ep24'
EP = 24
PHASES = dict(A=(0, 33), B=(33, 52), C=(52, 111), D=(111, 164), E=(164, 220), F=(220, 275))
XF.kit(KIT); T3 = XF.K['T3']


def aligned(names, track, gt, H, REG):  # as vo_oracle_screen.py
    N = len(track[names[0]])
    ach = np.stack([XF.to7(track[n]) for n in names], 1)[:, None].copy(); ref = np.stack([XF.to7(gt[n][:N]) for n in names], 1)[:, None].copy()
    for s in range(len(names)):
        ach[:, :, s] = T3._convert_object_body(ach[:, :, s], *REG[s])
        ref[:, :, s, :3] += np.einsum('...ij,j->...i', T3._rotation_matrix(ref[:, :, s, 3:]), H[s]['anchor'])
    return T3._align_registered_scene(ach, ref, [h['axis'] for h in H]), ref


def auc(ach, ref, H):
    return float(T3._registered_pose_metric('add_auc', ach, ref, [h['points'] for h in H], [h['axis'] for h in H], [h['order'] for h in H]))


def common(names, track, gt, H, REG):
    al, ref = aligned(names, track, gt, H, REG)
    d = al[:, 0, :, :3] - ref[:, 0, :, :3]
    m = d.mean(1); k = np.ones(9) / 9
    ms = np.stack([np.convolve(np.pad(m[:, j], 4, mode='edge'), k, 'valid') for j in range(3)], 1)
    al2 = al.copy(); al2[:, 0, :, :3] -= ms[:, None]
    nm = np.linalg.norm(ms, axis=1) * 100
    per_obj = {n: round(float(np.median(np.linalg.norm(d[:, s], axis=1)) * 100), 2) for s, n in enumerate(names)}
    return dict(common_cm_med=round(float(np.median(nm)), 2), common_cm_p90=round(float(np.percentile(nm, 90)), 2),
                common_cm_phase={p: round(float(np.median(nm[a:b])), 2) for p, (a, b) in PHASES.items()},
                common_cm_end=round(float(nm[-1]), 2), common_vec_cm_f100=np.round(ms[100] * 100, 2).tolist(),
                anchor_err_cm_med=per_obj, diff_cm_med=round(float(np.median(np.linalg.norm(d[:, 0] - d[:, 1], axis=1)) * 100), 2),
                auc_common_removed=round(auc(al2, ref, H), 4))


def main():
    runs, out, specs = sys.argv[1], sys.argv[2], sys.argv[3].split(',')
    names, gt = XF.mocap(T3D, EP, None)
    H = [XF.host_geometry(T3D, n, s) for s, n in enumerate(names)]
    REGs = [XF.reg_of_X(np.asarray(XG[n]['X_scan_T_lib']), H[s]['anchor']) for s, n in enumerate(names)]
    REGl = [XF.kit_X(f'{LIB}/{n}.glb', H[s], EP, s)[1] for s, n in enumerate(names)]
    REGn = [XF.reg_of_X(np.eye(4), H[s]['anchor']) for s in range(len(names))]
    P = np.load(f'{P1}/perc2/poses.npz'); Wb = P['world_T_cam'].astype(float)
    camT = {n: P[f'cam_T_{n}'].astype(float) for n in names}
    Vs = np.load(f'{P1}/perc2scan/poses_world_vo.npz'); Ts = {n: Vs[n].astype(float) for n in names}
    Vo = np.load(f'{P1}/perc2/poses_world_vo.npz')
    chk = max(float(np.abs(np.einsum('tij,tjk->tik', Wb, camT[n]) - Vo[n]).max()) for n in names)
    res = dict(note='ORACLE scoring vs public mocap, after inference (T5 first stage, ep24)', objects=names,
               recompose_check_maxdiff_base=chk, runs={})
    for sp in specs:
        run, v = sp.split(':')
        W = np.load(f'{runs}/{run}/W_{v}.npy').astype(float)
        To = {n: np.einsum('tij,tjk->tik', W, camT[n]) for n in names}
        C = np.einsum('tij,tjk->tik', W, np.linalg.inv(Wb))
        Tps = {n: np.einsum('tij,tjk->tik', C, Ts[n]) for n in names}
        so, sl, ss = XF.score_track(names, To, gt, H, REGs), XF.score_track(names, To, gt, H, REGl), XF.score_track(names, Tps, gt, H, REGn)
        r = dict(Po_star=so['AUC'], Po_lib=sl['AUC'], Po_star_per_obj=so['per_obj_AUC'], Po_lib_per_obj=sl['per_obj_AUC'],
                 Ps_star=ss['AUC'], Po_common=common(names, To, gt, H, REGs), Ps_common=common(names, Tps, gt, H, REGn))
        res['runs'][sp] = r
        c = r['Po_common']
        print(f'{sp:28s} P_o * {r["Po_star"]:.4f} lib {r["Po_lib"]:.4f} (b1 {so["per_obj_AUC"][names[0]]:.3f}, b2 '
              f'{so["per_obj_AUC"][names[1]]:.3f}) | common med {c["common_cm_med"]:.2f} p90 {c["common_cm_p90"]:.2f} cm, phases '
              f'{c["common_cm_phase"]}, removed {c["auc_common_removed"]:.4f} | P_s * {r["Ps_star"]:.4f} common '
              f'{r["Ps_common"]["common_cm_med"]:.2f}', flush=True)
    json.dump(res, open(out, 'w'), indent=1)


if __name__ == '__main__':
    main()
