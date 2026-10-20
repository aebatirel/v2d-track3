"""Candidate-generation recall: for z-visible markers, best DoG candidate rank within match radius. usage: candrec.py ep step"""
import sys, json, time, numpy as np, cv2
import lib17 as L, det17lib as D, seg17
ep, step = int(sys.argv[1]), int(sys.argv[2]); SH = -0.5
gt = L.load_gt(ep); RG = json.load(open(f'out/reg2_{ep}.json')); z = np.load(f'out/census_{ep}.npz'); seg = seg17.segments(gt)[0]
cams = {'a': RG['cams'], 'b': RG['cams_b'], 'c': RG['cams_c']}; T = len(cams['a']); N = len(gt['names'])
vids = {c: L.Video(ep, c) for c in 'abc'}; ranks = []; ncand = {c: [] for c in 'abc'}; t0 = time.time()
for t in range(0, T, step):
    for ci, c in enumerate('abc'):
        G = cv2.cvtColor(vids[c].get(t), cv2.COLOR_BGR2GRAY); Cd = D.dog_candidates(G, c); ncand[c].append(len(Cd))
        R, C = np.array(cams[c][t]['Rwc']), np.array(cams[c][t]['C']); tau = t + SH - (RG['delta'] if c == 'a' else 0)
        for j in range(N):
            uv, zz, rp = D.project_markers(gt, j, tau, R, C, c)
            for k in range(len(uv)):
                if not z['VIS'][t, ci, j, k]: continue
                rad = max(0.5 * rp[k], 3.0 if c == 'a' else 2.0)
                d = np.hypot(Cd[:, 0] - uv[k, 0], Cd[:, 1] - uv[k, 1]); ok = (d < rad) & (Cd[:, 2] > 0.5 * rp[k]) & (Cd[:, 2] < 2.0 * rp[k])
                ii = np.flatnonzero(ok); ranks.append((ci, seg[t, j], rp[k], ii[0] if len(ii) else -1, Cd[ii[0], 4] if len(ii) else 0))
print(f'{time.time()-t0:.0f}s; candidates per image med', {c: int(np.median(v)) for c, v in ncand.items()})
A = np.array(ranks)
for ci, c in enumerate('abc'):
    for s in range(3):
        m = (A[:, 0] == ci) & (A[:, 1] == s)
        if not m.any(): continue
        rk = A[m, 3]; print(f'cam {c} seg {s} n {m.sum():4d} found(any) {np.mean(rk>=0):.2f} top100 {np.mean((rk>=0)&(rk<100)):.2f} top300 {np.mean((rk>=0)&(rk<300)):.2f} top1000 {np.mean((rk>=0)&(rk<1000)):.2f}; pol+ {np.mean(A[m,4]>0):.2f} pol- {np.mean(A[m,4]<0):.2f}')
