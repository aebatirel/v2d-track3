"""Public 20-episode CPU test of rule F0-ICP (PREREG_f0icp.md). The rule itself is GT-free (depth0, det_f0 masks, our
library_v3 meshes, our tracks); scoring vs public mocap happens after it (ORACLE).
Usage: python -I f0icp_all.py ARM OUT_JSON   (ARM = Pr: refine/in tracks; Po: Phase-1 P_o tracks with the refine masks)
"""
import json, sys, time
import numpy as np, trimesh
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation as Rot

REPO = '/home/user/v2d-track3'
S = '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad'
sys.path.insert(0, f'{REPO}/tools')
import xstar_fit as XF  # noqa: E402
KIT = f'{S}/map/scoring/kit/v2d_submission_kit'; T3D = f'{S}/map/scoring/t3'
XF.kit(KIT)
XG = json.load(open(f'{REPO}/docs/research/work/leak-decomp-20261030/tierA/xstar_geom.json'))['objects']
LIB = f'{REPO}/meshes/library_v3'
ARM = sys.argv[1]
MESH = {}


def model(n):
    if n not in MESH:
        m = trimesh.load(f'{LIB}/{n}.glb', force='mesh'); k = 400000 if n == 'plastic_dish_rack' else 150000
        p, fi = trimesh.sample.sample_surface(m, k, seed=11); MESH[n] = (p, m.face_normals[fi])
    return MESH[n]


def icp(T0, cloud, mdl, iters=60, trim=0.8):
    T = T0.copy(); P, Nn = mdl; res0 = None
    for it in range(iters):
        Xw = P @ T[:3, :3].T + T[:3, 3]; Nw = Nn @ T[:3, :3].T
        vis = (Xw * Nw).sum(1) < 0
        if vis.sum() < 100:
            return T, None, None
        tree = cKDTree(Xw[vis]); d, i = tree.query(cloud)
        keep = d < np.quantile(d, trim); q = cloud[keep]; p = Xw[vis][i[keep]]; n = Nw[vis][i[keep]]
        r = np.abs(((q - p) * n).sum(1)).mean()
        if res0 is None:
            res0 = r
        A = np.c_[np.cross(p, n), n]; b = ((q - p) * n).sum(1)
        x = np.linalg.lstsq(A, b, rcond=None)[0]
        G = np.eye(4); G[:3, :3] = Rot.from_rotvec(x[:3]).as_matrix(); G[:3, 3] = x[3:]; T = G @ T
        if np.linalg.norm(x) < 1e-6:
            break
    # final residual
    Xw = P @ T[:3, :3].T + T[:3, 3]; Nw = Nn @ T[:3, :3].T; vis = (Xw * Nw).sum(1) < 0
    d, i = cKDTree(Xw[vis]).query(cloud); keep = d < np.quantile(d, trim)
    r1 = np.abs(((cloud[keep] - Xw[vis][i[keep]]) * Nw[vis][i[keep]]).sum(1)).mean()
    return T, res0, r1


def main():
    out = {}
    for ep in XF.PUBLIC:
        t0 = time.time()
        names, gt = XF.mocap(T3D, ep, None)
        H = [XF.host_geometry(T3D, n, s) for s, n in enumerate(names)]
        R = f'{S}/refine/in/ep{ep}'
        det = np.load(f'{R}/det_f0.npz', allow_pickle=True)
        dn = [str(x) for x in det['names']]
        K2 = np.diag([0.5, 0.5, 1.0]) @ det['K'].astype(float)
        masks = np.unpackbits(det['masks'], axis=-1)[:, :, :int(det['mask_shape'][2])].astype(bool)
        dep = np.load(f'{R}/depth0.npy')[::2, ::2].astype(float)
        if ARM == 'Pr':
            V = np.load(f'{R}/poses_world_vo.npz'); W0 = np.load(f'{R}/poses.npz')['world_T_cam'][0].astype(float)
        else:
            V = np.load(f'{S}/leak/p1/oracle_roots/Po/ep{ep}/poses_world_vo.npz'); W0 = np.load(f'{S}/leak/p1/oracle_roots/Po/ep{ep}/poses.npz')['world_T_cam'][0].astype(float)
        T = {n: V[n].astype(np.float64) for n in names}; N = len(T[names[0]]); g = {n: gt[n][:N] for n in names}
        REG_l = [XF.kit_X(f'{LIB}/{n}.glb', H[s], ep, s)[1] for s, n in enumerate(names)]
        REG_s = [XF.reg_of_X(np.asarray(XG[n]['X_scan_T_lib']), H[s]['anchor']) for s, n in enumerate(names)]
        base = dict(lib=XF.score_track(names, T, g, H, REG_l), star=XF.score_track(names, T, g, H, REG_s))
        e = dict(names=names, base=base, objects={})
        corr = {}
        for s, n in enumerate(names):
            info = {}
            if n not in dn or int(det['chosen'][dn.index(n)]) < 0:
                info['skip'] = 'no mask'; e['objects'][n] = info; continue
            m = masks[int(det['chosen'][dn.index(n)])] & (dep > 0)
            v, u = np.where(m); z = dep[v, u]
            cloud = np.c_[(u - K2[0, 2]) * z / K2[0, 0], (v - K2[1, 2]) * z / K2[1, 1], z]
            info['points'] = int(len(cloud))
            if len(cloud) < 200:
                info['skip'] = 'few points'; e['objects'][n] = info; continue
            Tc0 = np.linalg.inv(W0) @ T[n][0]            # world -> camera f0 (depth frame)
            Ti, r0, r1 = icp(Tc0, cloud, model(n))
            if r0 is None:
                info['skip'] = 'icp failed'; e['objects'][n] = info; continue
            dR = np.degrees(Rot.from_matrix(Ti[:3, :3] @ Tc0[:3, :3].T).magnitude())
            c = model(n)[0].mean(0); dt = np.linalg.norm((Ti[:3, :3] @ c + Ti[:3, 3]) - (Tc0[:3, :3] @ c + Tc0[:3, 3]))
            info.update(rot_change_deg=round(float(dR), 2), shift_cm=round(float(dt * 100), 2), res0_mm=round(float(r0 * 1000), 2), res1_mm=round(float(r1 * 1000), 2))
            ok = dR <= 15 and dt <= 0.03 and r1 < r0
            info['accepted'] = bool(ok)
            if ok:
                Tw = W0 @ Ti; corr[n] = np.linalg.inv(T[n][0]) @ Tw
            # perceived onset
            cc = T[n][:, :3, :3] @ c + T[n][:, :3, 3]
            mv = (np.linalg.norm(cc - cc[0], axis=1) > 0.01) | (np.degrees(Rot.from_matrix(np.einsum('nij,kj->nik', T[n][:, :3, :3], T[n][0, :3, :3])).magnitude()) > 5)
            info['onset'] = int(np.argmax(mv)) if mv.any() else N
            e['objects'][n] = info
        cache = {(): base}
        for var, objs in (('A_slot0', names[:1]), ('B_all', names)):
            T2 = {n: T[n].copy() for n in names}
            app = tuple(n for n in objs if n in corr)
            for n in app:
                on = e['objects'][n]['onset']; T2[n][:on] = T[n][:on] @ corr[n]
            if app not in cache:   # identical inputs give identical scores: score each distinct correction set once
                cache[app] = dict(lib=XF.score_track(names, T2, g, H, REG_l), star=XF.score_track(names, T2, g, H, REG_s))
            e[var] = dict(applied=list(app), lib=cache[app]['lib'], star=cache[app]['star'])
            e[var]['d_lib'] = round(e[var]['lib']['AUC'] - base['lib']['AUC'], 4); e[var]['d_star'] = round(e[var]['star']['AUC'] - base['star']['AUC'], 4)
        out[str(ep)] = e
        print(f'ep{ep} base lib {base["lib"]["AUC"]:.4f} * {base["star"]["AUC"]:.4f} | A {e["A_slot0"]["d_lib"]:+.4f}/{e["A_slot0"]["d_star"]:+.4f} '
              f'B {e["B_all"]["d_lib"]:+.4f}/{e["B_all"]["d_star"]:+.4f} | ' + ' '.join(f'{n}:{v.get("rot_change_deg", "-")}deg/{v.get("shift_cm", "-")}cm/{"acc" if v.get("accepted") else v.get("skip", "rej")}' for n, v in e['objects'].items())
              + f' ({time.time() - t0:.0f}s)', flush=True)
    for var in ('A_slot0', 'B_all'):
        for conv in ('d_lib', 'd_star'):
            d = np.array([out[k][var][conv] for k in out]); dn31 = np.array([out[k][var][conv] for k in out if k != '31'])
            print(f'{var} {conv}: mean {d.mean():+.4f} (w/o ep31 {dn31.mean():+.4f}) nonneg {int((d > -0.0005).sum())}/20 '
                  f'min {d.min():+.4f} max {d.max():+.4f} ep31 {out["31"][var][conv]:+.4f}')
    json.dump(out, open(sys.argv[2], 'w'), indent=1, default=float)


if __name__ == '__main__':
    main()
