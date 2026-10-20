"""Monte Carlo: achievable spin (yaw about the rest-up axis) from mocap-marker blobs, per object and camera.
Synthetic only (scan geometry + scan marker centres); no video, no GT trajectories.
Model: upright object at rest, camera at distance D, elevation 25-60 deg, random azimuth/spin.
Visibility: z-buffer of scan surface samples (self-occlusion incl. markers standing proud).
Detections: visible markers kept w.p. p_det, one extra visible marker dropped w.p. p_occ (hand),
Gaussian pixel noise, Poisson false blobs in the object's box. Prior: centre (sigma_t) and tilt (sigma_tilt)
from body/silhouette/table cues; spin unknown. Solver: coarse spin grid with gated robust cost + visibility-
aware missing-marker term, then joint refinement (spin, centre, tilt) of the 6 best minima with re-matching.
Usage: mc_spin.py <object> <ntrials> -> c/out/mc_<object>.json"""
import numpy as np, json, sys, time
from scipy.optimize import least_squares
from scipy.ndimage import minimum_filter
from scipy.spatial.transform import Rotation as Rr
W12 = '/Users/aebatirel/Documents/Code/v2d-research/work/12'
sys.path.insert(0, W12)
from meshlib import load, sample
from selfsim import good_markers

AX = json.load(open(f'{W12}/out/axes2.json'))
CAL = json.load(open('/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public/meta/camera_calibration.json'))['cameras']
CAMS = {c: (np.array(CAL[f'ego_cam_{c}']['intrinsic_matrix']), CAL[f'ego_cam_{c}']['resolution']) for c in 'ab'}
EL_GRID = np.arange(15, 80, 5); AZ_STEP = 2; VIS_FRAC = 0.25

def Rz(th):
    c, s = np.cos(th), np.sin(th); return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.]])

def setup(name, n=150000):
    g, tex = load(name); P, _, _ = sample(g, tex, n, seed=3)
    up = np.array(AX[name]['gt_up'], float); up /= np.linalg.norm(up)
    R0 = Rr.align_vectors([[0, 0, 1.]], [up])[0].as_matrix()
    c0 = P.mean(0)
    return (P - c0) @ R0.T, (good_markers(name) - c0) @ R0.T

def camera(az, el, D):
    az, el = np.radians(az), np.radians(el)
    pos = D * np.array([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)])
    f = -pos / D; r = np.cross(f, [0, 0, 1.]); r /= np.linalg.norm(r); d = np.cross(f, r)
    return np.stack([r, d, f]), pos

def project(X, Rcw, pos, K):
    Xc = (X - pos) @ Rcw.T
    return np.stack([K[0, 0] * Xc[..., 0] / Xc[..., 2] + K[0, 2], K[1, 1] * Xc[..., 1] / Xc[..., 2] + K[1, 2]], -1), Xc[..., 2]

def vis_table(Pw, M, D=0.55, sub=2):
    K = CAMS['a'][0].copy(); K[:2] /= sub; Wd, Ht = CAMS['a'][1][0] // sub, CAMS['a'][1][1] // sub
    T = np.zeros((360 // AZ_STEP, len(EL_GRID), len(M)), bool)
    for j, el in enumerate(EL_GRID):
        for i, az in enumerate(range(0, 360, AZ_STEP)):
            Rcw, pos = camera(az, el, D)
            uv, z = project(Pw, Rcw, pos, K); ui, vi = uv[:, 0].astype(int), uv[:, 1].astype(int)
            ok = (ui >= 0) & (ui < Wd) & (vi >= 0) & (vi < Ht)
            zb = np.full((Ht, Wd), np.inf); np.minimum.at(zb, (vi[ok], ui[ok]), z[ok]); zb = minimum_filter(zb, 3)
            um, zm = project(M, Rcw, pos, K)
            for k in range(len(M)):
                # sphere counts as visible if >= VIS_FRAC of its projected disk is not covered by nearer surface
                rp = max(1, int(round(K[0, 0] * 0.0073 / zm[k]))); x0, y0 = int(um[k, 0]), int(um[k, 1])
                yy, xx = np.mgrid[-rp:rp + 1, -rp:rp + 1]; m = xx ** 2 + yy ** 2 <= rp ** 2
                xs, ys = x0 + xx[m], y0 + yy[m]; ok = (xs >= 0) & (xs < Wd) & (ys >= 0) & (ys < Ht)
                if not ok.any(): continue
                free = zb[ys[ok], xs[ok]] >= zm[k] - 0.0073 - 0.004
                T[i, j, k] = free.mean() >= VIS_FRAC
    return T

def vis_lookup(T, phi_deg, el_deg):
    i = (np.round(np.asarray(phi_deg) / AZ_STEP).astype(int)) % T.shape[0]
    j = np.clip(np.round((el_deg - EL_GRID[0]) / 5).astype(int), 0, len(EL_GRID) - 1)
    return T[i, j]

def pose_pts(M, th, t, g):
    R = Rr.from_rotvec([g[0], g[1], 0.]).as_matrix() @ Rz(th); return M @ R.T + t

def simulate(Pw, M, T, cam, cfg, rng):
    K, (Wd, Ht) = CAMS[cam]
    th = rng.uniform(0, 2 * np.pi); az0 = rng.uniform(0, 360); el0 = rng.uniform(25, 60); D = rng.uniform(*cfg['D'])
    frames = []
    for k in range(cfg['nf']):
        az = az0 + (rng.uniform(-8, 8) if k else 0); el = el0 + (rng.uniform(-3, 3) if k else 0)
        Rcw, pos = camera(az, el, D)
        vis = vis_lookup(T, az - np.degrees(th), el)
        idx = [i for i in np.flatnonzero(vis) if rng.random() < cfg['p_det']]
        if idx and rng.random() < cfg['p_occ']: idx.pop(rng.integers(len(idx)))
        uv, _ = project(pose_pts(M[idx], th, np.zeros(3), np.zeros(2)), Rcw, pos, K) if idx else (np.zeros((0, 2)), None)
        uv = uv + rng.normal(0, cfg['spx'], uv.shape)
        box, _ = project(pose_pts(Pw[::200], th, np.zeros(3), np.zeros(2)), Rcw, pos, K)
        lo, hi = box.min(0), box.max(0); ext = hi - lo; lo, hi = lo - 0.1 * ext, hi + 0.1 * ext
        nfp = rng.poisson(cfg['lfp']); fp = lo + rng.random((nfp, 2)) * (hi - lo)
        uv = np.vstack([uv, fp]); uv = uv[(uv[:, 0] >= 0) & (uv[:, 0] < Wd) & (uv[:, 1] >= 0) & (uv[:, 1] < Ht)]
        frames.append(dict(Rcw=Rcw, pos=pos, az=az, el=el, uv=uv, nvis=int(vis.sum()), ndet=len(idx)))
    t_est = rng.normal(0, cfg['st'], 3); g_est = rng.normal(0, np.radians(cfg['sg']), 2)
    return th, frames, t_est, g_est, D

def solve(M, T, cam, frames, t_est, g_est, cfg, D):
    K = CAMS[cam][0]; spx = cfg['spx_assumed']; tau = max(3 * spx, 5.0)
    gate = 3 * K[0, 0] * cfg['st'] / D + 8
    ths = np.radians(np.arange(0, 360, 2.))
    cost = np.zeros(len(ths))
    for fr in frames:
        X = np.stack([pose_pts(M, th, t_est, g_est) for th in ths])          # n, m, 3
        uv, _ = project(X, fr['Rcw'], fr['pos'], K)                          # n, m, 2
        vis = vis_lookup(T, fr['az'] - np.degrees(ths), fr['el'])           # n, m
        if len(fr['uv']) == 0:
            cost += cfg['wm'] * vis.sum(1); continue
        d = np.linalg.norm(uv[:, :, None, :] - fr['uv'][None, None], axis=-1)  # n, m, k
        d = np.where(vis[:, :, None], d, np.inf)
        dmin_det = np.minimum(d.min(1) / gate, 1) ** 2                       # n, k
        dmin_mk = np.minimum(d.min(2) / gate, 1) ** 2                        # n, m
        cost += dmin_det.sum(1) + cfg['wm'] * np.where(vis, dmin_mk, 0).sum(1)
    # local minima on the circle
    lm = np.flatnonzero((cost <= np.roll(cost, 1)) & (cost <= np.roll(cost, -1)))
    cand = lm[np.argsort(cost[lm])][:6]
    best = None
    for c in cand:
        p = np.r_[ths[c], t_est, g_est]
        for gref in (gate, gate / 2, 2 * tau, tau):
            match = []
            for fi, fr in enumerate(frames):
                if len(fr['uv']) == 0: continue
                vis = vis_lookup(T, fr['az'] - np.degrees(p[0]), fr['el']); mi = np.flatnonzero(vis)
                if len(mi) == 0: continue
                uv, _ = project(pose_pts(M[mi], p[0], p[1:4], p[4:6]), fr['Rcw'], fr['pos'], K)
                d = np.linalg.norm(uv[:, None] - fr['uv'][None], axis=-1)
                for k in range(len(fr['uv'])):
                    j = d[:, k].argmin()
                    if d[j, k] < gref: match.append((fi, mi[j], k))
            if not match: break
            def res(q):
                r = []
                for fi, j, k in match:
                    fr = frames[fi]; u, _ = project(pose_pts(M[j:j + 1], q[0], q[1:4], q[4:6]), fr['Rcw'], fr['pos'], K)
                    r += list((u[0] - fr['uv'][k]) / spx)
                r += list((q[1:4] - t_est) / cfg['st']) + list((q[4:6] - g_est) / np.radians(cfg['sg']))
                return np.array(r)
            p = least_squares(res, p, loss='soft_l1', f_scale=tau / spx, max_nfev=60).x
        # final score: truncated reprojection + unmatched detections + missing predicted markers + prior
        S = float(np.sum(((p[1:4] - t_est) / cfg['st']) ** 2) + np.sum(((p[4:6] - g_est) / np.radians(cfg['sg'])) ** 2))
        for fr in frames:
            vis = vis_lookup(T, fr['az'] - np.degrees(p[0]), fr['el']); mi = np.flatnonzero(vis)
            if len(mi) == 0:
                S += 0; continue
            uv, _ = project(pose_pts(M[mi], p[0], p[1:4], p[4:6]), fr['Rcw'], fr['pos'], K)
            if len(fr['uv']) == 0:
                S += cfg['wm'] * len(mi) * (tau / spx) ** 2; continue
            d = np.linalg.norm(uv[:, None] - fr['uv'][None], axis=-1) / spx
            S += np.minimum(d.min(0), tau / spx).__pow__(2).sum() + cfg['wm'] * np.minimum(d.min(1), tau / spx).__pow__(2).sum()
        if best is None or S < best[0]: best = (S, p[0])
    return best[1] if best else ths[cost.argmin()]

CFGS = {
    'base':  dict(D=(0.42, 0.70), nf=1, p_det=0.9, p_occ=0.3, lfp=0.5, spx=1.5, spx_assumed=1.5, st=0.005, sg=2.0, wm=0.5),
    'tight': dict(D=(0.42, 0.70), nf=1, p_det=0.9, p_occ=0.3, lfp=0.5, spx=1.5, spx_assumed=1.5, st=0.002, sg=1.0, wm=0.5),
    'harsh': dict(D=(0.42, 0.70), nf=1, p_det=0.75, p_occ=0.5, lfp=1.5, spx=3.0, spx_assumed=3.0, st=0.005, sg=2.0, wm=0.5),
    'base_wm0': dict(D=(0.42, 0.70), nf=1, p_det=0.9, p_occ=0.3, lfp=0.5, spx=1.5, spx_assumed=1.5, st=0.005, sg=2.0, wm=0.0),
    'tight_wm0': dict(D=(0.42, 0.70), nf=1, p_det=0.9, p_occ=0.3, lfp=0.5, spx=1.5, spx_assumed=1.5, st=0.002, sg=1.0, wm=0.0),
    'multi5': dict(D=(0.42, 0.70), nf=5, p_det=0.9, p_occ=0.3, lfp=0.5, spx=1.5, spx_assumed=1.5, st=0.005, sg=2.0, wm=0.5),
}

if __name__ == '__main__':
    name, N = sys.argv[1], int(sys.argv[2]); cfgs = sys.argv[3].split(',') if len(sys.argv) > 3 else list(CFGS)
    t0 = time.time(); Pw, M = setup(name); T = vis_table(Pw, M)
    print(name, 'markers', len(M), 'vis-table mean visible %.2f (el 25-60)' % T[:, 2:10].sum(-1).mean(), 'setup %.0fs' % (time.time() - t0), flush=True)
    out = {}
    for cam in 'ab':
        for cn in cfgs:
            cfg = CFGS[cn]; rng = np.random.default_rng(12); E, nd = [], []
            for n in range(N):
                th, frames, t_est, g_est, D = simulate(Pw, M, T, cam, cfg, rng)
                est = solve(M, T, cam, frames, t_est, g_est, cfg, D)
                E.append((np.degrees(est - th) + 180) % 360 - 180); nd.append(frames[0]['ndet'])
            E = np.abs(np.array(E)); nd = np.array(nd)
            r = dict(n=N, med=float(np.median(E)), p90=float(np.percentile(E, 90)), gt5=float((E > 5).mean()),
                     gt15=float((E > 15).mean()), gt30=float((E > 30).mean()),
                     det0=float((nd == 0).mean()), det1=float((nd == 1).mean()), det2p=float((nd >= 2).mean()),
                     gt30_by_ndet={int(k): [int((nd == k).sum()), float((E[nd == k] > 30).mean())] for k in np.unique(nd)},
                     big_err_hist=np.histogram(E[E > 30], bins=[30, 60, 100, 140, 181])[0].tolist())
            out[f'{cam}/{cn}'] = r
            print(name, cam, cn, 'med %.2f p90 %.1f >5 %.2f >15 %.2f >30 %.2f | ndet0 %.2f 1 %.2f 2+ %.2f | >30 by ndet %s | %.0fs' % (
                r['med'], r['p90'], r['gt5'], r['gt15'], r['gt30'], r['det0'], r['det1'], r['det2p'], r['gt30_by_ndet'], time.time() - t0), flush=True)
            json.dump(out, open(f'{W12}/c/out/mc_{name}.json', 'w'), indent=1)
