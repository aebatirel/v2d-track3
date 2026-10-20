"""Real-image check (PUBLIC ep 11, cam a): automatic blob detection inside each cup's region + the Monte Carlo
spin solver (mc_spin.solve), scored against GT. Evaluation-only use of GT: camera pose (PnP on GT-placed scan
markers, pnp_check.py), visibility of GT markers, the cup region (projected GT box = stand-in for a tracker mask)
and the centre/tilt prior (GT + noise = stand-in for a body tracker). Spin itself is never given to the solver.
Usage: real_ep11.py <frame> [png]  (frame image read from the MP4 with OpenCV)."""
import numpy as np, json, sys, cv2, pandas as pd
W12 = '/Users/aebatirel/Documents/Code/v2d-research/work/12'
sys.path.insert(0, W12); sys.path.insert(0, W12 + '/c')
import mc_spin as mc
from pnp_check import variant, T_of, world_markers, solve as pnp_solve
from detect2d import detect
from scipy.ndimage import minimum_filter

VID = '/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public/videos/chunk-000/observation.images.ego_cam_a/episode_000011.mp4'
K, D = variant(False)
NAMES = ['blue_cup', 'beige_cup']

def frame(i):
    cap = cv2.VideoCapture(VID); cap.set(cv2.CAP_PROP_POS_FRAMES, i); ok, im = cap.read(); return im

def gt(i):
    df = pd.read_parquet('/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public/data/chunk-000/episode_000011.parquet')
    return {o['name']: T_of(o['pose']) for o in df.iloc[i]['observation.objects']}

def cam_from_gt(im, G, rv0=None, tv0=None):
    """Evaluation-only camera: frame 0 from the stored 6-point solve; later frames by re-associating auto blobs."""
    X, lab, _ = world_markers(11, 0, NAMES) if rv0 is None else (None, None, None)
    if rv0 is None:
        uv = np.array([[795, 988], [1044, 1022], [950, 1290], [1260, 1059], [1479, 984], [1273, 888]], float)
        err, (perm, rv, tv, e) = pnp_solve(uv, X, K, D); return rv, tv, err
    return rv0, tv0, None

def upright_gauge(name, T, Pw_c0R0):
    c0, R0 = Pw_c0R0
    C = T[:3, :3] @ c0 + T[:3, 3]
    Q = T[:3, :3] @ R0.T
    th = np.arctan2(Q[1, 0], Q[0, 0])
    g = mc.Rr.from_matrix(Q @ mc.Rz(th).T).as_rotvec()[:2]
    return C, th, g

def setup2(name, n=80000):
    g_, tex = mc.load(name); P, _, _ = mc.sample(g_, tex, n, seed=3)
    up = np.array(mc.AX[name]['gt_up'], float); up /= np.linalg.norm(up)
    R0 = mc.Rr.align_vectors([[0, 0, 1.]], [up])[0].as_matrix(); c0 = P.mean(0)
    return P, (c0, R0), (P - c0) @ R0.T, (mc.good_markers(name) - c0) @ R0.T

if __name__ == '__main__':
    fi = int(sys.argv[1]); im = frame(fi); G = gt(fi)
    rv, tv, err = cam_from_gt(im, G); Rc = cv2.Rodrigues(rv)[0]; tc = tv.ravel(); Ccam = -Rc.T @ tc
    print('frame', fi, 'eval camera reproj %.2f px' % err)
    S = {n: setup2(n) for n in NAMES}
    # z-buffer of both GT-placed scans (distorted image coords, quarter res) for GT marker visibility
    sub = 2; Hs, Ws = im.shape[0] // sub, im.shape[1] // sub; zb = np.full((Hs, Ws), np.inf)
    for n in NAMES:
        P = S[n][0] @ G[n][:3, :3].T + G[n][:3, 3]
        uv = cv2.projectPoints(np.ascontiguousarray(P, float), rv, tv, K, D)[0].reshape(-1, 2) / sub; z = (P @ Rc.T + tc)[:, 2]
        ui, vi = uv[:, 0].astype(int), uv[:, 1].astype(int); ok = (ui >= 0) & (ui < Ws) & (vi >= 0) & (vi < Hs)
        np.minimum.at(zb, (vi[ok], ui[ok]), z[ok])
    zb = minimum_filter(zb, 3)
    rng = np.random.default_rng(0); res = {}
    for n in NAMES:
        P, cR, Pu, Mu = S[n]; T = mc.vis_table(Pu, Mu)
        Pw = P @ G[n][:3, :3].T + G[n][:3, 3]
        box = cv2.projectPoints(np.ascontiguousarray(Pw[::50], float), rv, tv, K, D)[0].reshape(-1, 2); lo, hi = box.min(0), box.max(0)
        ext = hi - lo; lo, hi = (lo - 0.15 * ext).astype(int), (hi + 0.15 * ext).astype(int)
        # GT markers and visibility
        mk = mc.good_markers(n) @ G[n][:3, :3].T + G[n][:3, 3]
        uvm = cv2.projectPoints(np.ascontiguousarray(mk, float), rv, tv, K, D)[0].reshape(-1, 2); zm = (mk @ Rc.T + tc)[:, 2]
        vis = np.array([zm[k] - 0.0075 <= zb[int(uvm[k, 1] / sub), int(uvm[k, 0] / sub)] + 0.006 for k in range(len(mk))])
        # automatic blobs inside the region, size-gated by the expected sphere diameter
        Z = float((G[n][:3, 3] @ Rc.T + tc)[2]); dexp = K[0, 0] * 0.0146 / Z
        blobs = [b for b in detect(im, rmin=int(0.3 * dexp), rmax=int(0.8 * dexp), roi=(max(lo[0], 0), max(lo[1], 0), hi[0], hi[1]))]
        bu = np.array([[b['x'], b['y']] for b in blobs]) if blobs else np.zeros((0, 2))
        if 'comb' in sys.argv:   # add top-5 Hough candidates by hand-made score (includes false blobs)
            from detect_hough import detect_h
            hb = detect_h(im, dexp, (max(lo[0], 0), max(lo[1], 0), hi[0], hi[1]), smooth_max=1e9, acc=14)
            g = cv2.GaussianBlur(cv2.cvtColor(im, cv2.COLOR_BGR2GRAY).astype(np.float32), (0, 0), 2.0)
            gx, gy = cv2.Sobel(g, cv2.CV_32F, 1, 0), cv2.Sobel(g, cv2.CV_32F, 0, 1); sc = []
            for q in hb:
                yy, xx = np.mgrid[-30:31, -30:31]; dd = np.hypot(xx, yy); X = (xx + int(q['x'])).clip(0, im.shape[1] - 1); Y = (yy + int(q['y'])).clip(0, im.shape[0] - 1)
                inn = dd <= 0.6 * q['r']; ring = (dd > 0.85 * q['r']) & (dd < 1.15 * q['r']); ang = np.arctan2(yy, xx)
                edge = np.abs(gx[Y, X] * np.cos(ang) + gy[Y, X] * np.sin(ang))[ring].mean()
                sc.append(edge / (1 + g[Y, X][inn].std()) / (1 + q['sat'] / 20))
            for k in np.argsort(sc)[::-1][:5]:
                u = np.array([hb[k]['x'], hb[k]['y']])
                if len(bu) == 0 or np.linalg.norm(bu - u, axis=1).min() > 10: bu = np.vstack([bu, u])
        if "nofalse" in sys.argv and len(bu): bu = bu[np.linalg.norm(bu[:, None] - uvm[None], axis=-1).min(1) < 10]   # verifier oracle: drop false blobs
        dm = np.linalg.norm(uvm[vis][:, None] - bu[None], axis=-1) if len(bu) and vis.any() else np.zeros((vis.sum(), len(bu)))
        tp = int((dm.min(1) < 10).sum()) if dm.size else 0; fp = int((dm.min(0) >= 10).sum()) if dm.size else len(bu)
        print(n, 'Z %.2f m, expected sphere %.0f px; GT markers visible %d/%d; auto blobs %d -> matched %d, false %d' % (Z, dexp, vis.sum(), len(mk), len(bu), tp, fp))
        # solver in the upright gauge
        C, th_gt, g_gt = upright_gauge(n, G[n], cR)
        pos = Ccam - C; az = np.degrees(np.arctan2(pos[1], pos[0])); el = np.degrees(np.arcsin(pos[2] / np.linalg.norm(pos)))
        if 'add3' in sys.argv and n == 'beige_cup':   # oracle recall test: add the missed silhouette spheres (by-eye positions)
            for u in ([1276, 888], [1479, 986]):
                if len(bu) == 0 or np.linalg.norm(bu - np.array(u, float), axis=1).min() > 10: bu = np.vstack([bu, np.array(u, float)])
            print('   add3: beige detections now', len(bu))
        und = cv2.undistortPoints(bu.reshape(-1, 1, 2), K, D, P=K).reshape(-1, 2) if len(bu) else bu
        fr = dict(Rcw=Rc, pos=pos, az=az, el=el, uv=und)
        E = []
        for cfgname in ('base', 'tight', 'base_wm0', 'tight_wm0'):
            cfg = mc.CFGS[cfgname]; e = []
            for t in range(40):
                t_est = rng.normal(0, cfg['st'], 3); g_est = g_gt + rng.normal(0, np.radians(cfg['sg']), 2)
                est = mc.solve(Mu, T, 'a', [fr], t_est, g_est, cfg, np.linalg.norm(pos))
                e.append((np.degrees(est - th_gt) + 180) % 360 - 180)
            e = np.array(e); E.append(e)
            print('   %s prior: spin err median %.2f deg, |err|>30: %d/40, values(sample) %s' % (cfgname, np.median(np.abs(e)), (np.abs(e) > 30).sum(), np.round(e[:8], 1)))
        res[n] = dict(blobs_uv=bu.tolist(), gt_uv=uvm.tolist(), vis_list=vis.tolist(), th_gt=float(np.degrees(th_gt)), vis=int(vis.sum()), n_mk=len(mk), blobs=len(bu), tp=tp, fp=fp, az=az, el=el, Z=Z,
                      err_base=E[0].tolist(), err_tight=E[1].tolist(), err_base_wm0=E[2].tolist(), err_tight_wm0=E[3].tolist())
        if len(sys.argv) > 2:
            for k in range(len(mk)):
                cv2.circle(im, tuple(int(x) for x in uvm[k]), 18, (0, 255, 0) if vis[k] else (0, 0, 255), 2)
            for b in bu: cv2.circle(im, tuple(int(x) for x in b), 6, (255, 0, 255), 2)
            cv2.rectangle(im, tuple(int(x) for x in lo), tuple(int(x) for x in hi), (255, 255, 0), 2)
    json.dump(res, open(f'/Users/aebatirel/Documents/Code/v2d-research/work/12-verify/dump_real_ep11_f{fi:03d}' + ('_nofalse' if 'nofalse' in sys.argv else '') + ('_comb' if 'comb' in sys.argv else '') + ('_add3' if 'add3' in sys.argv else '') + '.json', 'w'))
    if len(sys.argv) > 2: cv2.imwrite(f'/Users/aebatirel/Documents/Code/v2d-research/work/12-verify/dump_real_ep11_f{fi:03d}.jpg', cv2.resize(im, None, fx=0.5, fy=0.5))
