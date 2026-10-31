"""ORACLE ARM scoring (public; README §2), after inference: S11 on the Phase-1 P_s tracks with scan templates.
Tracks are in scan frames; they are taken to lib frames by X*_geom and scored with the X*_geom registration (= native
scan-frame scoring, Phase 1 frame invariance 0.0000). Ceiling: R_trk(P_s) - R*(P_s) (phase1 xstar_trk_Ps.json).
Geometric share: C_s (S11 body correction, scan frame) vs the oracle C_or,scan = X*_geom inv(X_trk) on 2000 scan surface
samples (cups: 3 points on the scan axis). Usage: python -I oracle_ps_score.py OUT_JSON"""
import json, os, sys, time
from concurrent.futures import ProcessPoolExecutor
import numpy as np, trimesh

REPO = '/home/user/v2d-track3'
S = '/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad'
sys.path.insert(0, f'{REPO}/tools')
import xstar_fit as XF  # noqa: E402
KIT = f'{S}/map/scoring/kit/v2d_submission_kit'; T3D = f'{S}/map/scoring/t3'
LD = f'{REPO}/docs/research/work/leak-decomp-20261030'
XG = json.load(open(f'{LD}/tierA/xstar_geom.json'))['objects']
TRK = json.load(open(f'{LD}/phase1/scores/xstar_trk_Ps.json'))['episodes']
W = f'{S}/offset/oracle/runs/Ps'
VARS = ['S2', 'V1', 'V2', 'V3']


def pts(n, H):
    m = trimesh.load(XF.scan_path(T3D, n), force='mesh')
    P = np.asarray(trimesh.sample.sample_surface(m, 2000, seed=5)[0], float)
    if H['order'] == 360:
        r = float(np.sqrt((H['points'] ** 2).sum(1).mean()))
        return H['anchor'] + np.outer([-1.0, 0.0, 1.0], H['axis']) * r
    return P


def disp(A, B, P):
    return float(np.linalg.norm((P @ A[:3, :3].T + A[:3, 3]) - (P @ B[:3, :3].T + B[:3, 3]), axis=1).mean() * 100)


def episode(ep):
    XF.kit(KIT); t0 = time.time()
    names, gt = XF.mocap(T3D, ep, None)
    H = [XF.host_geometry(T3D, n, s) for s, n in enumerate(names)]
    Xg = {n: np.asarray(XG[n]['X_scan_T_lib']) for n in names}
    REG = [XF.reg_of_X(Xg[n], H[s]['anchor']) for s, n in enumerate(names)]
    out = dict(names=names, ceiling=dict(star=TRK[str(ep)]['scores']['star']['AUC'], trk=TRK[str(ep)]['scores']['trk']['AUC']))
    for v in VARS:
        V = np.load(f'{W}/{v}/ep{ep}/poses_world_vo.npz'); N = len(V[names[0]])
        T = {n: V[n].astype(np.float64) @ Xg[n] for n in names}
        out[v] = dict(star=XF.score_track(names, T, {n: gt[n][:N] for n in names}, H, REG))
        if v != 'S2':
            js = json.load(open(f'{W}/{v}/ep{ep}/pose_opt.json'))['steps']['S11']['objects']
            out[v]['s11'] = {}
            for s, n in enumerate(names):
                o = js[n]; P = pts(n, H[s])
                Cor = Xg[n] @ np.linalg.inv(np.asarray(TRK[str(ep)]['objects'][n]['X_scan_T_lib']))
                C = np.asarray(o['C_body']) if o['applied'] else np.eye(4)
                d0, d1 = disp(Cor, np.eye(4), P), disp(Cor, C, P)
                out[v]['s11'][n] = dict(applied=bool(o['applied']), reason=o.get('reason'), d0=round(d0, 3), d1=round(d1, 3),
                                        dC=round(disp(C, np.eye(4), P), 3), recovered=round(1 - d1 / d0, 3) if d0 > 1e-6 else None)
    for v in VARS[1:]:
        out[v]['d_star'] = round(out[v]['star']['AUC'] - out['S2']['star']['AUC'], 4)
    print(f'ep{ep}: S2 * {out["S2"]["star"]["AUC"]:.4f} (input * {out["ceiling"]["star"]:.4f} trk {out["ceiling"]["trk"]:.4f}) '
          + ' '.join(f'{v} {out[v]["d_star"]:+.4f}' for v in VARS[1:]) + f' ({time.time() - t0:.0f} s)', flush=True)
    return ep, out


def main():
    if os.environ.get('SPLIT', 'public') != 'public':
        sys.exit('public only')
    res = {}
    with ProcessPoolExecutor(4) as ex:
        for ep, o in ex.map(episode, XF.PUBLIC):
            res[str(ep)] = o
    eps = sorted(res, key=int); no = [e for e in eps if e not in ('0', '23')]
    ceil = np.mean([res[e]['ceiling']['trk'] - res[e]['ceiling']['star'] for e in eps])
    ceil18 = np.mean([res[e]['ceiling']['trk'] - res[e]['ceiling']['star'] for e in no])
    summ = {}
    for v in VARS[1:]:
        d = np.array([res[e][v]['d_star'] for e in eps]); d18 = np.array([res[e][v]['d_star'] for e in no])
        g = np.array([x['recovered'] for e in eps for x in res[e][v]['s11'].values() if x['applied'] and x['d0'] >= 0.5])
        summ[v] = dict(mean_d_star=round(float(d.mean()), 4), mean_d_star_18=round(float(d18.mean()), 4),
                       better=int((d >= 0.0001).sum()), worse=int((d <= -0.0001).sum()), worst=round(float(d.min()), 4),
                       share_of_ceiling=round(float(d.mean() / ceil), 3), share_of_ceiling_18=round(float(d18.mean() / ceil18), 3),
                       geo_n=int(len(g)), geo_median_recovered=round(float(np.median(g)), 3) if len(g) else None,
                       geo_share_closer=round(float((g > 0).mean()), 3) if len(g) else None)
        print(v, summ[v])
    json.dump(dict(summary=summ, ceiling=round(float(ceil), 4), ceiling_18=round(float(ceil18), 4), episodes=res),
              open(sys.argv[1], 'w'), indent=1)


if __name__ == '__main__':
    main()
