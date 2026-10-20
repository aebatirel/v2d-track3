"""Refit marker body positions from c/calib_obs_<ep>.npy with a Gaussian prior toward the scan catalogue (SIGP mm), because
depth along the (nearly parallel) viewing rays is weakly observed. -> c/calib_<ep>.json (overwrites calib17's unregularised fit).
usage: [SIGP=1.5] c/calfit.py ep"""
import sys, os, json, numpy as np
from scipy.optimize import least_squares
sys.path.insert(0, '/Users/aebatirel/Documents/Code/v2d-research/work/17')
import lib17 as L, det17lib as D
ep = int(sys.argv[1]); SIGP = float(os.environ.get('SIGP', 1.5)) / 1000
gt = L.load_gt(ep); RG = json.load(open(f'out/reg2_{ep}.json')); cams = {'a': RG['cams'], 'b': RG['cams_b'], 'c': RG['cams_c']}; DL = RG['delta']
FA = L.cam('a')[0][0, 0]; OBS = np.load(f'c/calib_obs_{ep}.npy'); out = {}
for j, n in enumerate(gt['names']):
    if n not in L.CAT: continue
    M = np.array([q['c'] for q in L.CAT[n]]); out[n] = []
    for k in range(len(M)):
        o = OBS[(OBS[:, 2] == j) & (OBS[:, 3] == k)] if len(OBS) else np.zeros((0, 9))
        if len(o) < 6: out[n].append(None); continue
        poses = [D.gt_interp(gt, j, oo[0] - 0.5 - (DL if oo[1] == 0 else 0)) for oo in o]
        P = [(np.array(cams['abc'[int(oo[1])]][int(oo[0])]['Rwc']), np.array(cams['abc'[int(oo[1])]][int(oo[0])]['C'])) for oo in o]
        def res(X, prior=True):
            r = []
            for oo, (Rj, tj), (R, C) in zip(o, poses, P):
                c = 'abc'[int(oo[1])]; uv, _ = L.project((X @ Rj.T + tj)[None], R, C, c, own=True); sc = FA / L.cam(c)[0][0, 0]
                r += [(uv[0, 0] - oo[4]) * sc / 2.0, (uv[0, 1] - oo[5]) * sc / 2.0]
            return np.r_[r, (X - M[k]) / SIGP] if prior else np.array(r)
        r0 = res(M[k], False).reshape(-1, 2) * 2; f = least_squares(res, M[k], loss='cauchy', f_scale=2.0); r1 = res(f.x, False).reshape(-1, 2) * 2
        # mean 2-D offset (obs - catalogue projection) per camera in a-eq px: the directly observed part
        dX = (f.x - M[k]) * 1000; ncam = [int(np.sum(o[:, 1] == ci)) for ci in range(3)]
        print(f'{n} k{k} ({L.CAT[n][k]["size"]}): n {len(o)} (a/b/c {ncam}), median res a-eq px {np.median(np.hypot(*r0.T)):.2f} -> {np.median(np.hypot(*r1.T)):.2f}; mean 2-D offset {np.round(-r0.mean(0), 1)} px; offset mm ({dX[0]:+.1f}, {dX[1]:+.1f}, {dX[2]:+.1f}) |{np.linalg.norm(dX):.1f}|', flush=True)
        out[n].append(dict(X=f.x.tolist(), n=len(o), ncam=ncam, off_mm=dX.tolist(), res_before=float(np.median(np.hypot(*r0.T))), res_after=float(np.median(np.hypot(*r1.T))), sigp_mm=SIGP * 1000))
json.dump(out, open(f'c/calib_{ep}.json', 'w'), indent=1); print('done')
