"""Public test of the GT-free frame-0 anchor rule F3 on all 20 public episodes (diagnostic scoring vs mocap):
frame 0 of every object := mean pose over the initial window in which the perceived object stays within 1 cm / 3 deg
of its frame-0 pose (window <= K frames). Arms: Phase-1 P_o, its repeat P_o2 (10 eps) and the refine-input P.
Scores: lib (X_kit, the leaderboard convention) and * (X*_geom)."""
import sys, json, os
import numpy as np
from scipy.spatial.transform import Rotation as Rot
from concurrent.futures import ProcessPoolExecutor
sys.path.insert(0, '/home/user/v2d-track3/tools')
import xstar_fit as XF
S = '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad'
LIB = '/home/user/v2d-track3/meshes/library_v3'; T3D = S + '/map/scoring/t3'; R = S + '/leak/p1/oracle_roots'
XG = json.load(open('/home/user/v2d-track3/docs/research/work/leak-decomp-20261030/tierA/xstar_geom.json'))['objects']
K = int(os.environ.get('K', 20))
def avg_pose(Ts):
    M = np.eye(4); M[:3, :3] = Rot.from_matrix(Ts[:, :3, :3]).mean().as_matrix(); M[:3, 3] = Ts[:, :3, 3].mean(0); return M
def smooth0(T):
    o = {}
    for n, Tn in T.items():
        Tn = Tn.copy(); p = Tn[:K, :3, 3]; r = np.degrees(Rot.from_matrix(np.einsum('ji,njk->nik', Tn[0, :3, :3], Tn[:K, :3, :3])).magnitude())
        ok = (np.linalg.norm(p - p[0], axis=1) * 100 < 1.0) & (r < 3.0); m = K if ok.all() else max(1, int(np.argmin(ok)))
        Tn[0] = avg_pose(Tn[:m]); o[n] = Tn
    return o
def run(ep):
    XF.kit(S + '/map/scoring/kit/v2d_submission_kit')
    names, gt = XF.mocap(T3D, ep); H = [XF.host_geometry(T3D, n, s) for s, n in enumerate(names)]
    X = {n: np.array(XG[n]['X_scan_T_lib']) for n in names}
    RID = [XF.reg_of_X(np.eye(4), h['anchor']) for h in H]
    RK = [XF.reg_of_X(XF.kit_X(f'{LIB}/{n}.glb', H[s], ep, s)[0], H[s]['anchor']) for s, n in enumerate(names)]
    out = {}
    for arm, path in (('Po', f'{R}/Po/ep{ep}/poses_world_vo.npz'), ('Po2', f'{R}/Po2/ep{ep}/poses_world_vo.npz'), ('Pr', f'{S}/refine/in/ep{ep}/poses_world_vo.npz')):
        if not os.path.exists(path): continue
        V = np.load(path); T = {n: V[n].astype(float)[:len(gt[n])] for n in names}
        for tag, TT in (('raw', T), ('f0s', smooth0(T))):
            out[f'{arm}_{tag}_lib'] = XF.score_track(names, TT, gt, H, RK)['AUC']
            out[f'{arm}_{tag}_star'] = XF.score_track(names, {n: TT[n] @ np.linalg.inv(X[n]) for n in names}, gt, H, RID)['AUC']
    return ep, out
if __name__ == '__main__':
    eps = XF.PUBLIC
    with ProcessPoolExecutor(3) as ex:
        res = dict(ex.map(run, eps))
    json.dump(res, open(f'{S}/leak/diag_ep0/out/f0smooth_all_K{K}.json', 'w'), indent=1)
    for ep in eps:
        r = res[ep]; print(ep, {k: round(v, 4) for k, v in r.items()})
    for arm in ('Po', 'Po2', 'Pr'):
        for conv in ('lib', 'star'):
            d = np.array([res[e][f'{arm}_f0s_{conv}'] - res[e][f'{arm}_raw_{conv}'] for e in eps if f'{arm}_raw_{conv}' in res[e]])
            print(f'{arm} {conv}: n={len(d)} mean d {d.mean():+.4f} min {d.min():+.4f} max {d.max():+.4f} pos {int((d > 0.0005).sum())} neg {int((d < -0.0005).sum())}')
    for conv in ('lib', 'star'):
        e2 = [e for e in eps if f'Po2_raw_{conv}' in res[e]]
        a = np.array([abs(res[e][f'Po_raw_{conv}'] - res[e][f'Po2_raw_{conv}']) for e in e2]); b = np.array([abs(res[e][f'Po_f0s_{conv}'] - res[e][f'Po2_f0s_{conv}']) for e in e2])
        print(f'repeat |Po-Po2| {conv}: raw mean {a.mean():.4f} max {a.max():.4f} -> f0s mean {b.mean():.4f} max {b.max():.4f}')
