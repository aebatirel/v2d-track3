"""(1) Rule F1 (static hold, HMAX 2 cm, RMAX 10 deg) on the 20 P_o tracks, scored in the LIB convention (library_v3 at the
kit's own registration X_kit: the leaderboard convention). (2) GT-free cup upright test on P_o cup episodes: at frame 0,
a cup whose bottom is within 2 cm of our table plane gets one body-frame correction that turns its axis (PCA of OUR
mesh) onto the plane normal (U1), optionally plus a base snap of our mesh's lowest vertex onto the plane (U2); scored *.
Scoring is ORACLE (public mocap), after inference. Usage: python -I f1_lib_and_upright.py OUT_JSON
"""
import json, sys
import numpy as np, trimesh
from scipy.spatial.transform import Rotation as Rot

sys.path.insert(0, '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/leak/diag_11/scripts')
import static_hold_test as SH  # noqa: E402
XF = SH.XF; XG = SH.XG

out = {'F1_lib': {}, 'upright': {}}
for ep in XF.PUBLIC:
    names, gt = XF.mocap(SH.T3D, ep, None)
    H = [XF.host_geometry(SH.T3D, n, s) for s, n in enumerate(names)]
    nrm = np.asarray(SH.plane(ep)[0], float)
    V = np.load(f'{SH.ROOT}/Po/ep{ep}/poses_world_vo.npz'); N = len(V[names[0]])
    T = {n: V[n].astype(np.float64) for n in names}; g = {n: gt[n][:N] for n in names}
    REG = [XF.kit_X(f'{SH.LIB}/{n}.glb', H[s], ep, s)[1] for s, n in enumerate(names)]
    base = XF.score_track(names, T, g, H, REG)
    st = {n: SH.stats(T[n], n, nrm) for n in names}
    frz = [n for n in names if st[n]['hmax_cm'] < 2.0 and (n in SH.SYMOBJ or st[n]['rmax_deg'] < 10.0)]
    T2 = {n: (np.repeat(T[n][:1], N, 0) if n in frz else T[n]) for n in names}
    sc = XF.score_track(names, T2, g, H, REG) if frz else base
    out['F1_lib'][ep] = dict(base=base['AUC'], F1=sc['AUC'], delta=round(sc['AUC'] - base['AUC'], 4), frozen=frz)
    print(f'F1 lib ep{ep} base {base["AUC"]:.4f} -> {sc["AUC"]:.4f} ({sc["AUC"] - base["AUC"]:+.4f}) {frz}', flush=True)
    cups = [n for n in names if n in SH.SYMOBJ]
    if not cups:
        continue
    d = np.load(f'{SH.S}/refine/in/ep{ep}/depth0.npy')  # noqa: F841 (plane already from it)
    c_plane = float(SH.plane(ep)[1])
    res = {'base_star': SH.score(names, T, g, H)['per_obj_AUC']}
    for var in ('U1', 'U2'):
        T3_ = dict(T); info = {}
        for n in cups:
            m = trimesh.load(f'{SH.LIB}/{n}.glb', force='mesh'); v = np.asarray(m.vertices, float); c = v.mean(0)
            w, U = np.linalg.eigh(np.cov((v - c).T)); k = int(np.argmax([abs(w[i] - np.mean(np.delete(w, i))) for i in range(3)])); a = U[:, k]
            M0 = T[n][0]; aw = M0[:3, :3] @ a
            if aw @ nrm < 0:
                aw = -aw
            tilt = float(np.degrees(np.arccos(np.clip(aw @ nrm, -1, 1))))
            vw = v @ M0[:3, :3].T + M0[:3, 3]; bottom = float((vw @ nrm + c_plane).min())
            if abs(bottom) > 0.02 or tilt > 15:
                info[n] = dict(skipped=True, tilt=round(tilt, 2), bottom_cm=round(bottom * 100, 2)); continue
            ax = np.cross(aw, nrm); s = np.linalg.norm(ax)
            Rc = Rot.from_rotvec(ax / s * np.arcsin(min(1.0, s))).as_matrix() if s > 1e-9 else np.eye(3)
            cw = M0[:3, :3] @ c + M0[:3, 3]
            M1 = np.eye(4); M1[:3, :3] = Rc @ M0[:3, :3]; M1[:3, 3] = Rc @ (M0[:3, 3] - cw) + cw
            if var == 'U2':
                vw1 = v @ M1[:3, :3].T + M1[:3, 3]; b1 = float((vw1 @ nrm + c_plane).min()); M1[:3, 3] -= b1 * nrm
            B = np.linalg.inv(M0) @ M1
            T3_[n] = T[n] @ B
            info[n] = dict(tilt=round(tilt, 2), bottom_cm=round(bottom * 100, 2))
        sc = SH.score(names, T3_, g, H)
        res[var] = dict(per_obj=sc['per_obj_AUC'], AUC=sc['AUC'], info=info)
    res['base_AUC'] = SH.score(names, T, g, H)['AUC']
    out['upright'][ep] = res
    print(f'upright ep{ep} base* {res["base_AUC"]:.4f} {res["base_star"]} | U1 {res["U1"]["AUC"]:.4f} {res["U1"]["per_obj"]} | U2 {res["U2"]["AUC"]:.4f} {res["U2"]["per_obj"]} | {res["U2"]["info"]}', flush=True)
json.dump(out, open(sys.argv[1], 'w'), indent=1, default=float)
