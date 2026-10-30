"""Public test (CPU) of a GT-FREE static-hold rule on the 20 Phase-1 P_o tracks (and P_s where present).
Rule F1 (inference side, perception only): table plane from our frame-0 depth (det_rules.table_plane, as perc2's
TRACK_GUARD); per object, c(t) = our mesh's vertex centroid in world; if max_t |horizontal(c(t) - c(0))| < HMAX and
(non-axisymmetric objects only) max_t rot(R(t) R(0)^T) < RMAX, the object is declared static and every frame is set to
its frame-0 pose. Scoring (ORACLE, after inference): kit chain, * convention (X*_geom), vs public mocap.
Usage: python -I static_hold_test.py OUT_JSON
"""
import json, os, sys
import numpy as np, trimesh
from scipy.spatial.transform import Rotation as Rot

REPO = '/home/user/v2d-track3'
S = '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad'
sys.path.insert(0, f'{REPO}/tools'); sys.path.insert(0, f'{REPO}/pipeline')
import xstar_fit as XF  # noqa: E402
import det_rules  # noqa: E402

KIT = f'{S}/map/scoring/kit/v2d_submission_kit'; T3D = f'{S}/map/scoring/t3'
XG = json.load(open(f'{REPO}/docs/research/work/leak-decomp-20261030/tierA/xstar_geom.json'))['objects']
XF.kit(KIT)
LIB = f'{REPO}/meshes/library_v3'
SYMOBJ = {'beige_cup', 'blue_cup'}   # axisymmetric (our own knowledge of the roster; rotation test skipped)
EPS = XF.PUBLIC
ROOT = f'{S}/leak/p1/oracle_roots'


def plane(ep):  # GT-free: our frame-0 depth + rectified K (hands file)
    d = np.load(f'{S}/refine/in/ep{ep}/depth0.npy'); KR = np.load(f'{S}/refine/in/ep{ep}/hands_refined.npz')['KR']
    return det_rules.table_plane(d[::2, ::2].astype(np.float32), np.diag([0.5, 0.5, 1.0]) @ KR)


CENT = {}
def centroid(n):
    if n not in CENT:
        CENT[n] = np.asarray(trimesh.load(f'{LIB}/{n}.glb', force='mesh').vertices, float).mean(0)
    return CENT[n]


def stats(T, n, nrm):
    c = T[:, :3, :3] @ centroid(n) + T[:, :3, 3]; dc = c - c[0]
    v = dc @ nrm; h = np.linalg.norm(dc - v[:, None] * nrm, axis=1)
    r = np.degrees(Rot.from_matrix(np.einsum('nij,kj->nik', T[:, :3, :3], T[0, :3, :3])).magnitude())
    return dict(hmax_cm=float(h.max() * 100), vmax_cm=float(np.abs(v).max() * 100), rmax_deg=float(r.max()))


def score(names, track, gt, H, scan_frames=False):
    REG = [XF.reg_of_X(np.eye(4) if scan_frames else np.asarray(XG[n]['X_scan_T_lib']), H[s]['anchor']) for s, n in enumerate(names)]
    return XF.score_track(names, track, gt, H, REG)


def main():
    HMAX = [1.0, 1.5, 2.0, 3.0]; RMAX = 10.0
    out = {}
    for ep in EPS:
        names, gt = XF.mocap(T3D, ep, None)
        H = [XF.host_geometry(T3D, n, s) for s, n in enumerate(names)]
        pl = plane(ep); nrm = np.asarray(pl[0], float)
        arms = {'Po': (f'{ROOT}/Po/ep{ep}/poses_world_vo.npz', False)}
        if os.path.exists(f'{ROOT}/Ps_scan/ep{ep}/poses_world_vo.npz'):
            arms['Ps'] = (f'{ROOT}/Ps_scan/ep{ep}/poses_world_vo.npz', True)
        e = dict(names=names, plane=[np.round(nrm, 4).tolist(), round(float(pl[1]), 4)])
        # mocap motion per object (oracle, for labelling only)
        e['mocap_motion'] = {}
        for s, n in enumerate(names):
            M = gt[n]; a = M[:, :3, 3] + np.einsum('nij,j->ni', M[:, :3, :3], H[s]['anchor'])
            e['mocap_motion'][n] = round(float(np.linalg.norm(a - a[0], axis=1).max() * 100), 2)
        for arm, (path, scan) in arms.items():
            V = np.load(path); N = len(V[names[0]])
            T = {n: V[n].astype(np.float64) for n in names}
            g = {n: gt[n][:N] for n in names}
            # stats in OUR mesh frame: for scan-frame tracks convert to lib frames with X*_geom (centroid of our mesh)
            Tl = {n: (T[n] @ np.asarray(XG[n]['X_scan_T_lib'])) if scan else T[n] for n in names}
            st = {n: stats(Tl[n], n, nrm) for n in names}
            base = score(names, T, g, H, scan)
            ar = dict(stats={n: {k: round(v, 2) for k, v in st[n].items()} for n in names}, base=base, rules={})
            for hm in HMAX:
                frz = [n for n in names if st[n]['hmax_cm'] < hm and (n in SYMOBJ or st[n]['rmax_deg'] < RMAX)]
                if not frz:
                    ar['rules'][f'h{hm}'] = dict(frozen=[], AUC=base['AUC'], delta=0.0); continue
                T2 = {n: (np.repeat(T[n][:1], N, 0) if n in frz else T[n]) for n in names}
                sc = score(names, T2, g, H, scan)
                ar['rules'][f'h{hm}'] = dict(frozen=frz, AUC=sc['AUC'], per_obj=sc['per_obj_AUC'], delta=round(sc['AUC'] - base['AUC'], 4))
            # oracle upper bound: freeze objects static in mocap (< 1 cm)
            frz = [n for n in names if e['mocap_motion'][n] < 1.0]
            T2 = {n: (np.repeat(T[n][:1], N, 0) if n in frz else T[n]) for n in names}
            sc = score(names, T2, g, H, scan)
            ar['oracle_static_freeze'] = dict(frozen=frz, AUC=sc['AUC'], delta=round(sc['AUC'] - base['AUC'], 4))
            e[arm] = ar
            print(f'ep{ep} {arm} base {base["AUC"]:.4f} ' + ' '.join(f'{k}:{v["delta"]:+.4f}{v["frozen"]}' for k, v in ar['rules'].items())
                  + f' | oracle {ar["oracle_static_freeze"]["delta"]:+.4f}{frz} | stats ' +
                  ' '.join(f'{n}:h{st[n]["hmax_cm"]:.1f}/v{st[n]["vmax_cm"]:.1f}/r{st[n]["rmax_deg"]:.0f}(mocap {e["mocap_motion"][n]:.1f})' for n in names), flush=True)
        out[str(ep)] = e
    json.dump(out, open(sys.argv[1], 'w'), indent=1, default=float)


if __name__ == '__main__':
    main()
