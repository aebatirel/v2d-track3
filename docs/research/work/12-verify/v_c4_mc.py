"""C4 re-run of the MC (cam a only) with work/12/c/mc_spin.py's simulate/solve, outputs to work/12-verify.
Extra variants (not in the original): 'base_mk2' = solver uses scan marker centres perturbed by N(0, 2 mm) per axis
(fixed per trial; real marker/scan error), 'base_det67' = p_det 0.67 and 1.0 false blob (closer to the measured
real-frame recall 4/6 with false blobs). Run from a dir that has out/markers_raw.json and out/axes2.json.
Usage: v_c4_mc.py <object> <N> <cfg,cfg,...>"""
import numpy as np, json, sys, time
sys.path.insert(0, '/Users/aebatirel/Documents/Code/v2d-research/work/12/c')
import mc_spin as mc
name, N, cfgs = sys.argv[1], int(sys.argv[2]), sys.argv[3].split(',')
EXTRA = {'base_mk2': dict(mc.CFGS['base'], mkerr=0.002), 'base_mk1': dict(mc.CFGS['base'], mkerr=0.001), 'tight_mk2': dict(mc.CFGS['tight'], mkerr=0.002), 'base_det67': dict(mc.CFGS['base'], p_det=0.67, lfp=1.0)}
t0 = time.time(); Pw, M = mc.setup(name); T = mc.vis_table(Pw, M)
print(name, 'markers', len(M), 'setup %.0fs' % (time.time() - t0), flush=True)
out = {}
for cn in cfgs:
    cfg = mc.CFGS.get(cn) or EXTRA[cn]; rng = np.random.default_rng(12); E, nd = [], []
    rng2 = np.random.default_rng(99)
    for n in range(N):
        th, frames, t_est, g_est, D = mc.simulate(Pw, M, T, 'a', cfg, rng)
        Ms = M + rng2.normal(0, cfg.get('mkerr', 0.0), M.shape) if cfg.get('mkerr') else M
        est = mc.solve(Ms, T, 'a', frames, t_est, g_est, cfg, D)
        E.append((np.degrees(est - th) + 180) % 360 - 180); nd.append(frames[0]['ndet'])
    E = np.abs(np.array(E)); nd = np.array(nd)
    r = dict(n=N, med=float(np.median(E)), gt5=float((E > 5).mean()), gt30=float((E > 30).mean()),
             gt30_by_ndet={int(k): [int((nd == k).sum()), float((E[nd == k] > 30).mean())] for k in np.unique(nd)},
             big_err_hist=np.histogram(E[E > 30], bins=[30, 60, 100, 140, 181])[0].tolist())
    out[cn] = r
    print(name, 'a', cn, 'med %.2f >5 %.2f >30 %.3f | by ndet %s | hist %s | %.0fs' % (r['med'], r['gt5'], r['gt30'], r['gt30_by_ndet'], r['big_err_hist'], time.time() - t0), flush=True)
    json.dump(out, open(f'/Users/aebatirel/Documents/Code/v2d-research/work/12-verify/c4_mc_{name}_{sys.argv[3].replace(",","-")}.json', 'w'), indent=1)
