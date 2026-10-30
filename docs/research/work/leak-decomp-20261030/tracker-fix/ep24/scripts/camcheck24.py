"""ORACLE DIAGNOSTIC (public ep24): is the error common-mode (camera / VO) or per object (tracker)?
(1) relative pose board1->board2 in the camera frame (VO-free) vs mocap;
(2) the camera trajectory implied by each board's camera-frame track and its mocap pose vs our VO world_T_cam.
Reads mocap and scans. Usage: python -I camcheck24.py OUT_JSON
"""
import json, sys
import numpy as np
from scipy.spatial.transform import Rotation as Rot

REPO = '/home/user/v2d-track3'
S = '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad'
sys.path.insert(0, f'{REPO}/tools')
import xstar_fit as XF  # noqa: E402

EP = int(sys.argv[2]) if len(sys.argv) > 2 else 24
RUNS = {24: '20261030-orcP1c-87fc869'}
KIT = f'{S}/map/scoring/kit/v2d_submission_kit'; T3D = f'{S}/map/scoring/t3'
RUN = f'{S}/leak/p1/runs/{RUNS[EP]}/results/leak_p1/ep{EP}'
XG = json.load(open(f'{REPO}/docs/research/work/leak-decomp-20261030/tierA/xstar_geom.json'))['objects']
XF.kit(KIT)


def fit_rigid(P, Q):
    mp, mq = P.mean(0), Q.mean(0); U, _, Vt = np.linalg.svd((P - mp).T @ (Q - mq))
    D = np.diag([1, 1, np.sign(np.linalg.det(Vt.T @ U.T))]); R = Vt.T @ D @ U.T
    M = np.eye(4); M[:3, :3] = R; M[:3, 3] = mq - R @ mp
    return M


def main():
    names, gt = XF.mocap(T3D, EP, None)
    H = [XF.host_geometry(T3D, n, s) for s, n in enumerate(names)]
    P = np.load(f'{RUN}/perc2/poses.npz'); WC = P['world_T_cam'].astype(np.float64); N = len(WC)
    Vs = np.load(f'{RUN}/perc2scan/poses_world_vo.npz')
    arms = {}
    arms['Po'] = {n: P[f'cam_T_{n}'].astype(np.float64) @ np.linalg.inv(np.asarray(XG[n]['X_scan_T_lib'])) for n in names}
    arms['Ps'] = {n: np.linalg.inv(WC) @ Vs[n].astype(np.float64) for n in names}
    out = {}
    pts = {n: H[s]['points'] for s, n in enumerate(names)}
    for arm, C in arms.items():
        o = {}
        # (1) relative pose, VO-free: board 2 in board 1's frame
        a, b = names
        rel_a = np.linalg.inv(C[a]) @ C[b]; rel_r = np.linalg.inv(gt[a]) @ gt[b]
        X_a = np.einsum('nij,vj->nvi', rel_a[:, :3, :3], pts[b]) + rel_a[:, None, :3, 3]
        X_r = np.einsum('nij,vj->nvi', rel_r[:, :3, :3], pts[b]) + rel_r[:, None, :3, 3]
        o['rel_add_cm'] = np.linalg.norm(X_a - X_r, axis=-1).mean(-1) * 100
        # (2) implied camera from each board: W_imp_k(t) = G M_k(t) inv(C_k(t)); G maps mocap world -> perception world,
        # fitted on frames 0-7 (both boards at rest, untouched) from both boards' points
        Pp, Qq = [], []
        for n in names:
            for t in range(8):
                Pp.append(pts[n] @ gt[n][t, :3, :3].T + gt[n][t, :3, 3])
                W = WC[t] @ C[n][t]; Qq.append(pts[n] @ W[:3, :3].T + W[:3, 3])
        G = fit_rigid(np.concatenate(Pp), np.concatenate(Qq))
        Ginv = np.linalg.inv(G)
        for n in names:
            Wimp = G @ gt[n] @ np.linalg.inv(C[n])
            # camera error expressed as the world displacement of a point 50 cm in front of the camera, and rotation
            pc = np.array([0, 0, 0.5, 1.0])
            d = (np.einsum('nij,j->ni', WC, pc) - np.einsum('nij,j->ni', Wimp, pc))[:, :3]
            d_mocap = d @ G[:3, :3]  # in mocap world axes (z up)
            rot = np.degrees(Rot.from_matrix(np.einsum('nji,njk->nik', Wimp[:, :3, :3], WC[:, :3, :3])).magnitude())
            o[f'cam_err_cm_{n}'] = d_mocap * 100
            o[f'cam_rot_deg_{n}'] = rot
        o['G'] = G
        out[arm] = o
    # print a compact table
    a, b = names
    print('f | Po rel_add | Po cam err from b1 (x y z) |  from b2 (x y z) | rot b1 b2 || Ps rel_add | Ps from b1 | from b2')
    for t in list(range(0, 60, 3)) + list(range(60, N, 10)):
        r = []
        for arm in ('Po', 'Ps'):
            o = out[arm]
            r.append(f"{o['rel_add_cm'][t]:5.2f} | {np.array2string(np.round(o[f'cam_err_cm_{a}'][t], 2), precision=2)} | {np.array2string(np.round(o[f'cam_err_cm_{b}'][t], 2), precision=2)} | {o[f'cam_rot_deg_{a}'][t]:4.1f} {o[f'cam_rot_deg_{b}'][t]:4.1f}")
        print(t, ' || '.join(r))
    summ = {}
    for arm in out:
        o = out[arm]
        e1 = o[f'cam_err_cm_{a}']; e2 = o[f'cam_err_cm_{b}']
        summ[arm] = dict(
            rel_add_med_cm=round(float(np.median(o['rel_add_cm'])), 2), rel_add_p90_cm=round(float(np.percentile(o['rel_add_cm'], 90)), 2),
            cam_err_b2_f0_30_med=np.round(np.median(e2[:30], 0), 2).tolist(), cam_err_b2_f50_110_med=np.round(np.median(e2[50:110], 0), 2).tolist(),
            cam_err_b1_f50_110_med=np.round(np.median(e1[50:110], 0), 2).tolist(), cam_err_b1_f135_274_med=np.round(np.median(e1[135:], 0), 2).tolist(),
            cam_err_b2_f220_274_med=np.round(np.median(e2[220:], 0), 2).tolist(),
            b1_minus_b2_f0_110_med_norm_cm=round(float(np.median(np.linalg.norm(e1[:110] - e2[:110], axis=1))), 2),
            b1_minus_b2_f135_274_med_norm_cm=round(float(np.median(np.linalg.norm(e1[135:] - e2[135:], axis=1))), 2))
    print(json.dumps(summ, indent=1))
    json.dump(dict(summary=summ, per_frame={arm: {k: (v.tolist() if hasattr(v, 'tolist') else v) for k, v in out[arm].items()} for arm in out}),
              open(sys.argv[1], 'w'), indent=0)


if __name__ == '__main__':
    main()
