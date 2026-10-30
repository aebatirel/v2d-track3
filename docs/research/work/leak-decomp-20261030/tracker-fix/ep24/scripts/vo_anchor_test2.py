"""Public test (CPU), version 2, of a GT-FREE camera (VO) correction from untouched resting objects, gated to the VO's own
keyframe switches ("keyframe-step anchor", rule K). v1 (vo_anchor_test.py) was falsified on ep2 (a lid sliding slowly
with no hand detected near it was read as a camera error: -0.087) and showed that sub-mm corrections churn the score
on threshold-clustered episodes (ep0 lid +-0.02 for 0.5 mm).
Rule K (inference side; reads only our tracks, world_T_cam, our VO keyframe list vo.json, hands_refined, our meshes):
  - our world centroid x_k(t) of each object (our mesh), hand distance d_k(t) (nearest valid hand joint to our mesh
    surface at our pose);
  - anchor windows: from frame 0 while untouched (d_k >= D_H), and later rest windows that start after REST_MIN
    untouched frames with apparent step < V_REST per frame, then continue while untouched; an anchor in contact
    (< 1 cm) with a non-anchored object is dropped (window ends);
  - camera translation correction c(t): only within KW frames of a VO keyframe switch, the mean residual
    r = ref_k - (x_k(t) + c) of the anchors (they must agree within 0.5 cm if >= 2) is absorbed, c += r, when
    DEAD < |r| <= JUMP; |r| > JUMP ends those windows (real motion); away from keyframe switches the anchors' reference
    follows them (ref_k = x_k(t) + c: their drift is object/tracker motion, not camera);
  - every object's world pose is translated by c(t).
Scoring (ORACLE, after inference): kit chain vs public mocap, * (X*_geom) and lib (X_kit).
Usage: python -I vo_anchor_test2.py OUT_JSON [eps]
"""
import json, os, sys
import numpy as np, trimesh
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
GRID = [(0.03, 5, 2), (0.03, 5, 1), (0.03, 8, 2), (0.05, 5, 2), (0.05, 8, 2)]   # first = primary
D_H = 0.05; REST_MIN = 8; V_REST = 0.0015; KW = int(os.environ.get('KW', 2)); DEAD = 0.002; JUMP = 0.015; AGREE = 0.005


def lib_pts(n, k=200):
    return trimesh.sample.sample_surface(trimesh.load(f'{LIB}/{n}.glb', force='mesh'), k, seed=3)[0]


_GEOM = {}


def geom(T, P, J, Jv, names):
    key = id(T)
    if key in _GEOM:
        return _GEOM[key]
    N = len(T[names[0]])
    X = {n: np.einsum('nij,vj->nvi', T[n][:, :3, :3], P[n]) + T[n][:, None, :3, 3] for n in names}
    dh = {}
    for n in names:
        d = np.full(N, np.inf)
        for i in range(N):
            if Jv[i].any():
                d[i] = cKDTree(X[n][i]).query(J[i][Jv[i]], k=1)[0].min()
        dh[n] = d
    cen = {n: X[n].mean(1) for n in names}
    gap = {}
    for a in names:
        for b in names:
            if a < b:
                g = np.array([cKDTree(X[b][i]).query(X[a][i], k=1)[0].min() for i in range(N)])
                gap[(a, b)] = gap[(b, a)] = g
    _GEOM[key] = (dh, cen, gap)
    return _GEOM[key]


def windows(T, P, J, Jv, names, relay=True):
    N = len(T[names[0]])
    dh, cen, gap = geom(T, P, J, Jv, names)
    spd = {n: np.r_[0, np.linalg.norm(np.diff(cen[n], axis=0), axis=1)] for n in names}
    cand = {}
    for n in names:
        ok = dh[n] >= D_H
        first = int(np.argmax(~ok)) if (~ok).any() else N
        st = np.arange(N) < first
        if relay:
            run = 0; inside = False
            for i in range(N):
                if not ok[i]:
                    inside = False; run = 0; continue
                if inside:
                    st[i] = True; continue
                run = run + 1 if spd[n][i] < V_REST else 0
                if run >= REST_MIN:
                    st[i - REST_MIN + 1:i + 1] = True; inside = True
        cand[n] = st
    return cand, cen, dh, gap


def correct(names, cand, cen, gap, kfs):
    N = len(cen[names[0]])
    near = np.zeros(N, bool)
    for k in kfs[1:]:
        near[max(0, k - KW):min(N, k + KW + 1)] = True
    c = np.zeros(3); C = np.zeros((N, 3)); ref = {n: None for n in names}; banned = set(); log = []
    for i in range(N):
        act = []
        for n in names:
            if not cand[n][i]:
                ref[n] = None; banned.discard(n); continue
            if n in banned:
                continue
            if any(gap[(n, o)][i] < 0.01 and not cand[o][i] for o in names if o != n):
                ref[n] = None; banned.add(n); continue
            xc = cen[n][i] + c
            if ref[n] is None:
                ref[n] = np.mean([cen[n][j] + c for j in range(i, min(N, i + 3))], 0)
            act.append(n)
        if act and near[i]:
            rs = np.array([ref[n] - (cen[n][i] + c) for n in act])
            r = rs.mean(0)
            agree = len(act) < 2 or np.linalg.norm(rs - r, axis=1).max() < AGREE
            if np.linalg.norm(r) > JUMP or not agree:
                banned.update(act); log.append((i, 'ban', act, np.round(r * 100, 2).tolist()))
            elif np.linalg.norm(r) > DEAD:
                c = c + r; log.append((i, 'absorb', act, np.round(r * 100, 2).tolist()))
        for n in act:
            if not near[i] and n not in banned:
                ref[n] = cen[n][i] + c          # away from keyframe switches: drift is the object's, not the camera's
        C[i] = c
    return C, log


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
        arms = {'Po': (f'{ROOT}/Po/ep{ep}/poses_world_vo.npz', False, f'{S}/refine/in/ep{ep}/vo.json'),
                'Pr': (f'{S}/refine/in/ep{ep}/poses_world_vo.npz', False, f'{S}/refine/in/ep{ep}/vo.json')}
        if os.path.exists(f'{ROOT}/Ps_scan/ep{ep}/poses_world_vo.npz'):
            arms['Ps'] = (f'{ROOT}/Ps_scan/ep{ep}/poses_world_vo.npz', True, f'{S}/refine/in/ep{ep}/vo.json')
        e = {}
        for arm, (path, scan, vo) in arms.items():
            V = np.load(path); N = len(V[names[0]])
            kfs = json.load(open(vo))['keyframes']
            T = {n: V[n].astype(np.float64) for n in names}
            P = {n: (H[s]['points'][::5] + H[s]['anchor']) if scan else lib_pts(n) for s, n in enumerate(names)}
            g = {n: gt[n][:N] for n in names}
            sc = lambda TT: dict(star=XF.score_track(names, TT, g, H, REGn if scan else REGs)['AUC'],
                                 lib=None if scan else XF.score_track(names, TT, g, H, REGl)['AUC'])
            r = dict(base=sc(T), keyframes=len(kfs))
            cache = {b'zero': r['base']}
            global D_H, REST_MIN, KW
            for dh_, rm_, kw_ in GRID:
                D_H, REST_MIN, KW = dh_, rm_, kw_
                cand, cen, dh, gap = windows(T, P, J[:N], Jv[:N], names, True)
                C, log = correct(names, cand, cen, gap, kfs)
                T2 = {n: T[n].copy() for n in names}
                for n in names:
                    T2[n][:, :3, 3] += C
                mag = np.linalg.norm(C, axis=1) * 100
                key = b'zero' if not np.any(C) else np.round(C, 6).tobytes()
                if key not in cache:
                    cache[key] = sc(T2)
                r[f'K_h{int(dh_ * 100)}_r{rm_}_w{kw_}'] = dict(**cache[key], anchored_frames={n: int(cand[n].sum()) for n in names},
                                                 corr_cm_max=round(float(mag.max()), 2), corr_cm_end=round(float(mag[-1]), 2),
                                                 n_absorb=sum(1 for x in log if x[1] == 'absorb'), n_ban=sum(1 for x in log if x[1] == 'ban'),
                                                 log=[[x[0], x[1], x[2], x[3]] for x in log][:60])
            e[arm] = r
            print(ep, arm, json.dumps({k: (v if k in ('base', 'keyframes') else {kk: vv for kk, vv in v.items() if kk != 'log'}) for k, v in r.items()}), flush=True)
        out[str(ep)] = e
    json.dump(dict(note='GT-free keyframe-gated anchor VO correction (rule K); scored vs public mocap (oracle diagnostic)',
                   params=dict(D_H=D_H, REST_MIN=REST_MIN, V_REST=V_REST, KW=KW, DEAD=DEAD, JUMP=JUMP, AGREE=AGREE), episodes=out),
              open(sys.argv[1], 'w'), indent=1)
    keys = [f'K_h{int(h * 100)}_r{r}_w{w}' for h, r, w in GRID]
    for arm in ('Po', 'Pr', 'Ps'):
        for key in keys:
            for conv in ('star', 'lib'):
                d = [out[k][arm][key][conv] - out[k][arm]['base'][conv] for k in out if arm in out[k] and out[k][arm]['base'][conv] is not None]
                if d:
                    d = np.array(d)
                    print(f'{arm} {key} {conv}: n={len(d)} mean {d.mean():+.4f} min {d.min():+.4f} max {d.max():+.4f} pos {(d > 0.0005).sum()} neg {(d < -0.0005).sum()}')


if __name__ == '__main__':
    main()
