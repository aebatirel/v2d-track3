"""Public test (CPU) of a GT-FREE camera (VO) correction from untouched objects ("anchor hold").
Rule (inference side; reads only our tracks, our camera world_T_cam, our hands_refined joints and our meshes):
  - per object k and frame t: our world pose W_k(t) = world_T_cam(t) cam_T_k(t); hand distance d_k(t) = min distance
    from any valid hand joint to our mesh's surface points at W_k(t);
  - anchor windows: (A) the initial window [0, first touch): no hand within D_H; (B) also later rest windows that start
    after REST_MIN untouched frames with apparent speed < V_REST per frame; a window ends at a touch, at a new contact
    (< 1 cm) with a non-anchored object, or when the object's apparent world drift from its window-start pose exceeds
    MAXDRIFT (a real motion, not a camera error);
  - camera correction C(t): rigid (RT) or translation-only (T) fit that maps every anchored object's current world points
    back onto its window-start points (window start = mean of the first 3 window frames, in the corrected world);
    no anchor -> hold the last C; 5-frame running median; all objects' world poses become C(t) W_k(t).
Scoring (ORACLE, after inference): kit chain vs public mocap, * (X*_geom) and lib (X_kit).
Usage: python -I vo_anchor_test.py OUT_JSON [eps]
"""
import json, os, sys
import numpy as np, trimesh
from scipy.spatial.transform import Rotation as Rot
from scipy.spatial import cKDTree

REPO = '/home/user/v2d-track3'
S = '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad'
sys.path.insert(0, f'{REPO}/tools')
import xstar_fit as XF  # noqa: E402

KIT = f'{S}/map/scoring/kit/v2d_submission_kit'; T3D = f'{S}/map/scoring/t3'
XG = json.load(open(f'{REPO}/docs/research/work/leak-decomp-20261030/tierA/xstar_geom.json'))['objects']
XF.kit(KIT)
LIB = f'{REPO}/meshes/library_v3'
ROOT = f'{S}/leak/p1/oracle_roots'
D_H = float(os.environ.get('D_H', 0.05)); MAXDRIFT = float(os.environ.get('MAXDRIFT', 0.05)); MAXROT = 5.0
REST_MIN = 8; V_REST = 0.005


def lib_pts(n, k=300):
    m = trimesh.load(f'{LIB}/{n}.glb', force='mesh')
    return trimesh.sample.sample_surface(m, k, seed=3)[0]


def windows(T, P, J, Jv, names, relay):
    """GT-free anchor windows. T: world poses (uncorrected), P: body points, J: (N,42,3) hand joints, Jv: (N,42) valid."""
    N = len(T[names[0]])
    X = {n: np.einsum('nij,vj->nvi', T[n][:, :3, :3], P[n]) + T[n][:, None, :3, 3] for n in names}
    dh = {}
    for n in names:
        d = np.full(N, np.inf)
        for i in range(N):
            if Jv[i].any():
                d[i] = cKDTree(X[n][i]).query(J[i][Jv[i]], k=1)[0].min()
        dh[n] = d
    touched = {n: dh[n] < D_H for n in names}
    cen = {n: X[n].mean(1) for n in names}
    spd = {n: np.r_[0, np.linalg.norm(np.diff(cen[n], axis=0), axis=1)] for n in names}
    gap = {}
    for a in names:
        for b in names:
            if a < b:
                g = np.array([cKDTree(X[b][i]).query(X[a][i], k=1)[0].min() for i in range(N)])
                gap[(a, b)] = gap[(b, a)] = g
    cand = {}
    for n in names:
        ok = ~touched[n]
        first = int(np.argmax(~ok)) if (~ok).any() else N
        init = np.arange(N) < first                                   # (A) untouched since frame 0
        if relay:                                                      # (B) + later rest windows
            # a window starts after REST_MIN untouched frames with apparent speed < V_REST (start = the first of
            # them) and then continues while the object stays untouched, whatever its apparent speed (a camera
            # jump must not end the window; the guard in correct() catches real motion)
            run = 0; st = np.zeros(N, bool); inside = False
            for i in range(N):
                if not ok[i]:
                    inside = False; run = 0; continue
                if inside:
                    st[i] = True; continue
                run = run + 1 if spd[n][i] < V_REST else 0
                if run >= REST_MIN:
                    st[i - REST_MIN + 1:i + 1] = True; inside = True
            cand[n] = init | st
        else:
            cand[n] = init
    return cand, dh, gap


def correct(T, P, names, cand, gap, mode):
    N = len(T[names[0]])
    C = np.repeat(np.eye(4)[None], N, 0)
    start = {n: None for n in names}; refp = {n: None for n in names}; banned = set()
    active_log = []
    last = np.eye(4)
    Craw = []
    for i in range(N):
        act = []
        for n in names:
            if not cand[n][i]:
                start[n] = None; banned.discard(n); continue
            if n in banned:
                continue
            # contact with a non-anchored object ends the window (new contact only)
            if any(gap[(n, o)][i] < 0.01 and not cand[o][i] and gap[(n, o)][0] >= 0.01 for o in names if o != n):
                start[n] = None; banned.add(n); continue
            Xi = T[n][i, :3, :3] @ P[n].T + T[n][i, :3, 3:4]
            if start[n] is None:
                start[n] = i
                # window-start points in the corrected world (current held correction)
                Xs = [last[:3, :3] @ (T[n][j, :3, :3] @ P[n].T + T[n][j, :3, 3:4]) + last[:3, 3:4] for j in range(i, min(N, i + 3))]
                refp[n] = np.mean(Xs, 0)
            act.append((n, Xi.T, refp[n].T))
        if act:
            A = np.concatenate([a[1] for a in act]); B = np.concatenate([a[2] for a in act])
            if mode == 'T':
                M = np.eye(4); M[:3, 3] = (B - A).mean(0)
            else:
                ma, mb = A.mean(0), B.mean(0); U, _, Vt = np.linalg.svd((A - ma).T @ (B - mb))
                Dg = np.diag([1, 1, np.sign(np.linalg.det(Vt.T @ U.T))]); R = Vt.T @ Dg @ U.T
                M = np.eye(4); M[:3, :3] = R; M[:3, 3] = mb - R @ ma
            # guard: a one-frame step > 1.5 cm, a total > MAXDRIFT or a turn > MAXROT is a real motion (or a
            # tracking glitch) of the anchor, not a camera error -> end those windows, keep the last correction
            if np.linalg.norm(M[:3, 3] - last[:3, 3]) > 0.015 or np.linalg.norm(M[:3, 3]) > MAXDRIFT or \
                    np.degrees(Rot.from_matrix(M[:3, :3]).magnitude()) > MAXROT:
                banned.update(a[0] for a in act); act = []
                M = last
            last = M
        Craw.append(last.copy()); active_log.append([a[0] for a in act])
    Craw = np.stack(Craw)
    # 5-frame running median of translation and rotation vector
    tr = Craw[:, :3, 3]; rv = Rot.from_matrix(Craw[:, :3, :3]).as_rotvec()
    for i in range(N):
        lo, hi = max(0, i - 2), min(N, i + 3)
        C[i, :3, 3] = np.median(tr[lo:hi], 0); C[i, :3, :3] = Rot.from_rotvec(np.median(rv[lo:hi], 0)).as_matrix()
    return C, active_log


def main():
    eps = [int(x) for x in sys.argv[2].split(',')] if len(sys.argv) > 2 else XF.PUBLIC
    out = {}
    for ep in eps:
        names, gt = XF.mocap(T3D, ep, None)
        H = [XF.host_geometry(T3D, n, s) for s, n in enumerate(names)]
        REGs = [XF.reg_of_X(np.asarray(XG[n]['X_scan_T_lib']), H[s]['anchor']) for s, n in enumerate(names)]
        REGl = [XF.kit_X(f'{LIB}/{n}.glb', H[s], ep, s)[1] for s, n in enumerate(names)]
        REGn = [XF.reg_of_X(np.eye(4), H[s]['anchor']) for s in range(len(names))]
        hz = np.load(f'{S}/refine/in/ep{ep}/hands_refined.npz', allow_pickle=True)
        J = np.concatenate([hz['joints_left'], hz['joints_right']], 1).astype(np.float64)
        Jv = np.concatenate([np.repeat(hz['valid_left'][:, None], 21, 1), np.repeat(hz['valid_right'][:, None], 21, 1)], 1) & np.isfinite(J).all(-1)
        arms = {'Po': (f'{ROOT}/Po/ep{ep}/poses_world_vo.npz', False), 'Pr': (f'{S}/refine/in/ep{ep}/poses_world_vo.npz', False)}
        if os.path.exists(f'{ROOT}/Ps_scan/ep{ep}/poses_world_vo.npz'):
            arms['Ps'] = (f'{ROOT}/Ps_scan/ep{ep}/poses_world_vo.npz', True)
        e = {}
        for arm, (path, scan) in arms.items():
            V = np.load(path); N = len(V[names[0]])
            T = {n: V[n].astype(np.float64) for n in names}
            P = {n: (H[s]['points'][::3] + H[s]['anchor']) if scan else lib_pts(n) for s, n in enumerate(names)}
            g = {n: gt[n][:N] for n in names}
            sc = lambda TT: dict(star=XF.score_track(names, TT, g, H, REGn if scan else REGs)['AUC'],
                                 lib=None if scan else XF.score_track(names, TT, g, H, REGl)['AUC'])
            r = dict(base=sc(T))
            for relay in (False, True):
                cand, dh, gap = windows(T, P, J[:N], Jv[:N], names, relay)
                for mode in ('T', 'RT'):
                    cd = {n: cand[n].copy() for n in names}
                    C, act = correct(T, P, names, cd, gap, mode)
                    T2 = {n: np.einsum('nij,njk->nik', C, T[n]) for n in names}
                    key = ('B' if relay else 'A') + '_' + mode
                    mag = np.linalg.norm(C[:, :3, 3], axis=1) * 100
                    r[key] = dict(**sc(T2), anchored_frames={n: int(cand[n].sum()) for n in names},
                                  corr_cm_max=round(float(mag.max()), 2), corr_cm_end=round(float(mag[-1]), 2),
                                  corr_deg_max=round(float(np.degrees(Rot.from_matrix(C[:, :3, :3]).magnitude()).max()), 2))
            e[arm] = r
            print(ep, arm, json.dumps(r), flush=True)
        out[str(ep)] = e
    json.dump(dict(note='GT-free anchor-hold VO correction; scored vs public mocap (oracle diagnostic)', D_H=D_H, MAXDRIFT=MAXDRIFT, episodes=out),
              open(sys.argv[1], 'w'), indent=1)
    # summary
    for arm in ('Po', 'Pr', 'Ps'):
        for key in ('A_T', 'A_RT', 'B_T', 'B_RT'):
            for conv in ('star', 'lib'):
                d = [out[k][arm][key][conv] - out[k][arm]['base'][conv] for k in out if arm in out[k] and out[k][arm]['base'][conv] is not None]
                if d:
                    d = np.array(d)
                    print(f'{arm} {key} {conv}: n={len(d)} mean {d.mean():+.4f} min {d.min():+.4f} max {d.max():+.4f} pos {(d > 0.0005).sum()} neg {(d < -0.0005).sum()}')


if __name__ == '__main__':
    main()
