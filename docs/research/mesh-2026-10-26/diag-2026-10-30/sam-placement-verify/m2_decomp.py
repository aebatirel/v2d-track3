"""M2/M3 [D]: independent Sim(3) decomposition of placed meshes vs the public scan, plus the sim3_fit objective J
(re-implemented from gen/sim3_fit.py) at our fit, at the scan-ideal placement and at the ideal placement expressed
in our points' frame (display alignment). Usage: m2_decomp.py OUT.jsonl model_dir [objs...] """
import sys, json, time, glob
import numpy as np
from vlib import *
from scipy.spatial import cKDTree

out, mdir = sys.argv[1], sys.argv[2]
objs = sys.argv[3:] or list(EPS)
SYM = kit_sym()


def J(X, O, keep_o=0.9, keep_m=0.7):
    do = cKDTree(X).query(O)[0]; dm = cKDTree(O).query(X)[0]
    return float(np.sort(do)[:int(keep_o * len(do))].mean() + np.sort(dm)[:int(keep_m * len(dm))].mean())


def add_err(T, q, kind, axis, c_scan):
    s, R, t = T
    p = ((q - t) @ R) / s                       # T^-1 q  (where our mesh puts the point the scan has at q)
    if kind is None:
        return float(np.linalg.norm(p - q, axis=1).mean())
    angs = np.radians(np.arange(0, 360, 1.0)) if kind == 'axial' else [0.0, math.pi]
    best = np.inf
    for a in angs:
        Sq = (q - c_scan) @ axis_rot(axis, a).T + c_scan
        best = min(best, float(np.linalg.norm(p - Sq, axis=1).mean()))
    return best


with open(out, 'a') as fo:
    for obj in objs:
        for seed in (42, 7):
            path = f'{mdir}/{obj}_{KTAG[obj]}_s{seed}.ply'
            if not os.path.exists(path):
                cand = glob.glob(f'{mdir}/*{obj}*s{seed}.ply')
                if not cand: continue
                path = cand[0]
            t0 = time.time()
            v, f = load(path); sv, sf = load_scan(obj)
            A = sample(v, f, 4000, 11); B = sample(sv, sf, 4000, 12)
            allr = multi_start(A, B, scale=True, return_all=True)
            tr, un, T = allr[0]
            # second-best start whose rotation differs by > 30 deg from the best
            alt = [r for r in allr[1:] if rot_angle(r[2][1] @ T[1].T) > 30]
            gap = (alt[0][0] - tr) * 1e3 if alt else None
            s, R, t = T
            kind = SYM.get(obj)
            cs = centroid(sv, sf)
            cpv, Vs, _ = pca_frame(sample(sv, sf, 20000, 13))
            axis = sym_axis(sample(sv, sf, 6000, 14), kind) if kind else None
            if kind == 'axial':
                a2 = R @ axis
                krot = math.degrees(math.acos(np.clip(abs(a2 @ axis) if False else a2 @ axis, -1, 1)))
            elif kind == 'half':
                krot = min(rot_angle(R), rot_angle(R @ axis_rot(axis, math.pi)))
            else:
                krot = rot_angle(R)
            cm = centroid(v, f)
            off = apply(T, cm[None])[0] - cm
            q = sample(sv, sf, 500, 0)
            add_sim = add_err(T, q, kind, axis, cs)
            # rigid-only version (scale error removed about the mesh centroid): kit normalises scale
            Tr = (1.0, R, apply(T, cm[None])[0] - R @ cm)
            add_rig = add_err(Tr, q, kind, axis, cs)
            # extents of the placed mesh after the best similarity, relative to the scan, along scan PCA axes
            Xm = apply(T, sample(v, f, 20000, 15))
            ext_m = np.ptp((Xm - cpv) @ Vs, 0); ext_s = np.ptp((sample(sv, sf, 20000, 16) - cpv) @ Vs, 0)
            rec = dict(obj=obj, seed=seed, path=path.split('/results/gen/')[-1], size_pct=round((1 / s - 1) * 100, 1),
                       rot_deg=round(rot_angle(R), 1), kit_rot_deg=round(krot, 1), trans_mm=round(float(np.linalg.norm(off)) * 1e3, 1),
                       off_LMS_mm=[round(float(x) * 1e3, 1) for x in off @ Vs], add_sim_mm=round(add_sim * 1e3, 1),
                       add_rigid_mm=round(add_rig * 1e3, 1), shape_trim_mm=round(tr * 1e3, 2), shape_mm=round(un * 1e3, 2),
                       alt_gap_mm=None if gap is None else round(gap, 3), ext_ratio_LMS=[round(float(x), 2) for x in ext_m / ext_s])
            # J at fit / ideal / ideal in our points' frame
            obsf = f'{SCR}/obs_all/ep{EPS[obj]}_{obj}.npz'
            if os.path.exists(obsf):
                P = np.load(obsf)['pts']; rng = np.random.default_rng(0)
                O = P[rng.choice(len(P), min(20000, len(P)), replace=False)]
                X = sample(v, f, 20000, 0)
                Xi = apply(T, X)
                rec['J_fit_mm'] = round(J(X, O) * 1e3, 2); rec['J_ideal_mm'] = round(J(Xi, O) * 1e3, 2)
                af = f'{SCR}/obs/ep{EPS[obj]}_{obj}_align.npz'
                if not os.path.exists(af): af = f'{SCR}/page/align/ep{EPS[obj]}_{obj}_align.npz'
                if os.path.exists(af):
                    al = np.load(af); Ra, ta = al['R'], al['t']
                    Xa = (Xi - ta) @ Ra                      # scan frame -> our points' frame
                    rec['J_ideal_al_mm'] = round(J(Xa, O) * 1e3, 2)
                    # decomposition of our placement relative to the scan expressed in OUR points' frame
                    Ta = (s, Ra.T @ R, Ra.T @ (t - ta))
                    offa = apply(Ta, cm[None])[0] - cm
                    rec['al_trans_mm'] = round(float(np.linalg.norm(offa)) * 1e3, 1)
                    rec['al_rot_deg'] = round(rot_angle(Ra.T @ R), 1)
            rec['secs'] = round(time.time() - t0, 1)
            print(json.dumps(rec), flush=True); fo.write(json.dumps(rec) + '\n'); fo.flush()
