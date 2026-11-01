"""[D] Hypothesis tests (a) ill-posed / biased objective and (b) mesh->obs pulls unseen surfaces, for the SAM 3D fits.

T_fit   = the Sim(3) sim3_fit.py applied (recovered exactly from the vertex correspondence)
T_ideal = A o T_fit, A = the [D] Sim(3) that maps our placed mesh onto the scan (decomp_before.jsonl)
1. Path test: evaluate the GT-free objectives along the Sim(3) geodesic from T_ideal (lam = 0) to T_fit (lam = 1).
   If J_base decreases towards lam = 1, the objective itself prefers the wrong placement (bias, not an optimiser
   failure); if J_base(1) > J_base(0), the optimiser / starts failed.
2. Drift test: start the ICP AT the ideal placement and let it run (30 its) with each objective; report how far it
   walks away (scale, rotation, mean point displacement). A well-posed, unbiased objective stays put.
3. Scale slice: scale the ideal placement about its centroid by k, re-fit R, t (scale fixed), evaluate J.
Output: hyp.jsonl
"""
import json, sys
import numpy as np
from scipy.spatial.transform import Rotation as Rot, Slerp
sys.path.insert(0, '/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad/diag/sam-placement')
from common import *  # noqa
from fits import Known, objective, icp, N


def interp(T0, T1, lam):
    s = math.exp((1 - lam) * math.log(T0[0]) + lam * math.log(T1[0]))
    sl = Slerp([0, 1], Rot.from_matrix([T0[1], T1[1]]))
    R = sl([min(max(lam, 0), 1)]).as_matrix()[0] if 0 <= lam <= 1 else (Rot.from_matrix(T1[1] @ T0[1].T) ** lam * Rot.from_matrix(T0[1])).as_matrix()
    t = (1 - lam) * T0[2] + lam * T1[2]
    return (s, R, t)


def err(Tref, T, M):
    """placement error of T relative to Tref, on the raw samples M."""
    X = apply(T, M); Xr = apply(Tref, M)
    E = compose(Tref, inv(T))
    c = X.mean(0)
    return dict(size_pct=(T[0] / Tref[0] - 1) * 100, rot_deg=angle_deg(E[1]),
                mean_disp_mm=float(np.linalg.norm(X - Xr, axis=1).mean() * 1e3),
                centroid_mm=float(np.linalg.norm(Xr.mean(0) - c) * 1e3))


def main():
    dec = {}
    for l in open(f'{OUT}/decomp_before.jsonl'):
        r = json.loads(l)
        if r['model'] == 'sam3d':
            dec[(r['obj'], r['seed'])] = r
    fo = open(f'{OUT}/hyp.jsonl', 'w')
    for obj in OBJS:
        obs = load_obs(obj, n=N); O = obs['pts']; tO = cKDTree(O); known = Known(obs)
        for seed in (42, 7):
            if (obj, seed) not in dec:
                continue
            d = dec[(obj, seed)]
            rp, pp = gen_paths('sam3d', obj, seed)
            raw = load_mesh(rp); M, _ = surf(raw, N, seed=0)
            Tfit, _ = recover_T(raw, load_mesh(pp))
            A = (d['scale_A'], np.array(d['R']), np.array(d['t']))
            Tid = compose(A, Tfit)
            rec = dict(obj=obj, seed=seed)
            path = []
            for lam in (0, 0.25, 0.5, 0.75, 1.0):
                T = interp(Tid, Tfit, lam)
                X = apply(T, M)
                path.append(dict(lam=lam, j_base=objective(T, M, O, tO, 'base', known) * 1e3,
                                 j_vis=objective(T, M, O, tO, 'vis', known) * 1e3,
                                 known_frac=float(known(X).mean())))
            rec['path'] = path
            drift = {}
            for v in ('base', 'vis', 'obs_only'):
                Td = icp(Tid, M, O, tO, v, known)
                drift[v] = err(Tid, Td, M)
            Td = icp(Tid, M, O, tO, 'vis', known, fix_scale=Tid[0])
            drift['vis_fixscale'] = err(Tid, Td, M)
            rec['drift'] = drift
            sl = []
            for k in (0.8, 0.9, 1.0, 1.1, 1.2):
                Xc = apply(Tid, M).mean(0)
                Tk = compose((k, np.eye(3), Xc - k * Xc), Tid)
                Tk2 = icp(Tk, M, O, tO, 'base', known, iters=15, fix_scale=Tk[0])
                Tk3 = icp(Tk, M, O, tO, 'vis', known, iters=15, fix_scale=Tk[0])
                sl.append(dict(k=k, j_base=objective(Tk2, M, O, tO, 'base', known) * 1e3,
                               j_vis=objective(Tk3, M, O, tO, 'vis', known) * 1e3))
            rec['scale_slice'] = sl
            print(json.dumps(rec), flush=True)
            fo.write(json.dumps(rec) + '\n'); fo.flush()


if __name__ == '__main__':
    main()
