"""Room map: drift-free camera relocalisation for the ego stereo pair (note 18 rewritten, GT-free).

Reads NO ground truth: only public/eval VIDEOS and the factory calibration. Never reads the episode parquets.
The map is built from PUBLIC video frames only; eval frames never enter a map. For public validation, a fold map
excludes the test episodes' frames entirely (leave-episodes-out), as at eval time.

Differences from note 18 (docs/research/notes/18-room-map.md), all GT-free:
- only the ego b/c pair (perc2 uses c/b only; cam_a and its lag are not needed);
- no mocap registration (gravity/height/heading): consumers keep their own frame-0 world and use only relative
  map motion, world_T_cam(t) = world_T_cam(0) . map_T_cam(0)^-1 . map_T_cam(t);
- relocalisation at every frame (STRIDE, default 1) instead of keyframes + VO bridge; a GT-free temporal gate replaces
  single-frame glitches by interpolation of trusted neighbours (see `track`).

Steps (WORK = a work dir, T3 = dataset root laid out by pipeline/fetch_data.sh):
  python roommap.py extract  --t3 T3 --work WORK [--step 30]       public b/c frames, undistorted pinhole + masks
  python roommap.py features --work WORK                            SIFT (first_octave -1, 6000) into WORK/db.db
  python roommap.py match    --work WORK [--partners 12]            pairs: within-episode, frame-0s, random cross-ep
  python roommap.py map      --work WORK --name NAME [--exclude 12,13] [--threads 4]
                                                                    incremental SfM, b/c fixed rig (metric)
  python roommap.py reloc    --t3 T3 --work WORK --name NAME --split eval|public --ep N --out F.npz [--stride 1]
                                                                    per-frame rig PnP against the map (+ gate)
Output of reloc (npz): frames, map_T_c (N,4,4; NaN where failed), inliers, gate flags, map_T_c_gated (filled),
plus rect_T_c (perc2's rectified-left rotation), so map_T_rect = map_T_c @ inv(rect_T_c).
"""
import argparse, json, os, sys, time, random
import numpy as np, cv2

W_, H_, F_ = 1280, 800, 420.0                       # undistorted pinhole for b/c (note 18 A1)
KP = np.array([[F_, 0, W_ / 2], [0, F_, H_ / 2], [0, 0, 1]])
t_all = time.time()


def log(*a):
    print(f'[{time.time() - t_all:7.1f}s]', *a, flush=True)


def calib(t3):
    C = json.load(open(f'{t3}/calib.json')); cam = C['cameras']
    sp = [p for p in C['stereo_pairs'] if p['camera'] == 'ego'][0]
    K = lambda n: np.array(cam[n]['intrinsic_matrix'], float)
    D = lambda n: np.array(cam[n]['distortion_coefficients'], float)
    E = np.array(sp['left_to_right'], float)           # x_b = R x_c + T  (perc2: left = c, right = b)
    return K('ego_cam_c'), D('ego_cam_c'), K('ego_cam_b'), D('ego_cam_b'), E


def undist_maps(t3):
    Kc, dc, Kb, db, E = calib(t3)
    mc = cv2.initUndistortRectifyMap(Kc, dc, None, KP, (W_, H_), cv2.CV_32FC1)
    mb = cv2.initUndistortRectifyMap(Kb, db, None, KP, (W_, H_), cv2.CV_32FC1)
    return mc, mb, E


def rect_T_c(t3):
    """perc2's rectified-left frame: x_rect = R1 x_c (same stereoRectify call as pipeline/perc2.py)."""
    Kc, dc, Kb, db, E = calib(t3)
    R1 = cv2.stereoRectify(Kc, dc, Kb, db, (1280, 800), E[:3, :3].copy(), E[:3, 3].reshape(3, 1).copy(), alpha=0,
                           newImageSize=(1600, 1000), flags=cv2.CALIB_ZERO_DISPARITY)[0]
    M = np.eye(4); M[:3, :3] = R1; return M


def mask_img():
    """note 18 A1 b/c mask: exclude normalised y > 0.30 within |x| < 0.9, or y > 0.55 (table, hands, objects)."""
    x = (np.arange(W_) - W_ / 2) / (W_ / 2); y = (np.arange(H_) - H_ / 2) / (H_ / 2)
    X, Y = np.meshgrid(x, y)
    bad = ((Y > 0.30) & (np.abs(X) < 0.9)) | (Y > 0.55)
    return np.where(bad, 0, 255).astype(np.uint8)


def read_video(path, idx=None):
    cap = cv2.VideoCapture(path); out = {}; i = 0
    while True:
        ok, f = cap.read()
        if not ok: break
        if idx is None or i in idx: out[i] = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
        i += 1
    return out, i


PUBLIC = [0, 2, 11, 12, 13, 18, 21, 22, 23, 24, 26, 27, 31, 39, 40, 41, 42, 43, 44, 45]
EVAL = [1, 3, 5, 6, 8, 10, 14, 15, 16, 19, 20, 25, 28, 30, 32, 33, 35, 36, 37, 38]


def cmd_extract(a):
    mc, mb, _ = undist_maps(a.t3); m = mask_img()
    for cam in 'cb':
        os.makedirs(f'{a.work}/imgs/{cam}', exist_ok=True); os.makedirs(f'{a.work}/masks/{cam}', exist_ok=True)
    n = 0
    for ep in PUBLIC:
        _, N = read_video(f'{a.t3}/v/ep{ep}_c.mp4', idx=set())
        idx = set(range(0, N, a.step))
        for cam, mp in (('c', mc), ('b', mb)):
            fr, _ = read_video(f'{a.t3}/v/ep{ep}_{cam}.mp4', idx)
            for i, g in fr.items():
                nm = f'p{ep}_{i:04d}.jpg'
                cv2.imwrite(f'{a.work}/imgs/{cam}/{nm}', cv2.remap(g, mp[0], mp[1], cv2.INTER_LINEAR),
                            [cv2.IMWRITE_JPEG_QUALITY, 95])
                cv2.imwrite(f'{a.work}/masks/{cam}/{nm}.png', m); n += 1
        log('extract', ep, N, len(idx))
    log('images', n)


def cmd_features(a):
    import pycolmap as pc
    db = f'{a.work}/db.db'
    if os.path.exists(db): os.remove(db)
    ro = pc.ImageReaderOptions(); ro.camera_model = 'PINHOLE'; ro.camera_params = f'{F_},{F_},{W_/2},{H_/2}'
    ro.mask_path = f'{a.work}/masks'
    eo = pc.FeatureExtractionOptions(); eo.sift.first_octave = -1; eo.sift.max_num_features = 6000
    eo.num_threads = a.threads
    pc.extract_features(db, f'{a.work}/imgs', camera_mode=pc.CameraMode.PER_FOLDER, reader_options=ro,
                        extraction_options=eo, device=pc.Device.cpu)
    _, _, E = undist_maps(a.t3)
    rc = pc.RigConfig(); c = pc.RigConfigCamera(); c.ref_sensor = True; c.image_prefix = 'c/'
    b = pc.RigConfigCamera(); b.image_prefix = 'b/'; b.cam_from_rig = pc.Rigid3d(E[:3, :4])
    rc.cameras = [c, b]
    D = pc.Database.open(db); pc.apply_rig_config([rc], D); D.close()
    log('features done', db)


def cmd_match(a):
    import pycolmap as pc
    db = f'{a.work}/db.db'
    D = pc.Database.open(db); names = sorted(im.name for im in D.read_all_images()); D.close()
    ep = lambda n: n.split('/')[1].split('_')[0]
    fr = lambda n: int(n.split('_')[1].split('.')[0])
    pairs = set()
    for i, p in enumerate(names):
        for q in names[i + 1:]:
            if ep(p) == ep(q) or (fr(p) == 0 and fr(q) == 0): pairs.add((p, q))
    rng = random.Random(0)
    for p in names:
        other = [q for q in names if ep(q) != ep(p)]
        for q in rng.sample(other, a.partners): pairs.add(tuple(sorted((p, q))))
    with open(f'{a.work}/pairs.txt', 'w') as f:
        for p, q in sorted(pairs): f.write(f'{p} {q}\n')
    log('pairs', len(pairs))
    mo = pc.FeatureMatchingOptions(); mo.num_threads = a.threads; mo.use_gpu = False
    po = pc.ImportedPairingOptions(); po.match_list_path = f'{a.work}/pairs.txt'
    pc.match_image_pairs(db, matching_options=mo, pairing_options=po, device=pc.Device.cpu)
    log('matching done')


def cmd_map(a):
    import pycolmap as pc, shutil
    excl = {f'p{e}' for e in (a.exclude.split(',') if a.exclude else [])}
    D = pc.Database.open(f'{a.work}/db.db'); names = sorted(im.name for im in D.read_all_images()); D.close()
    keep = [n for n in names if n.split('/')[1].split('_')[0] not in excl]
    out = f'{a.work}/maps/{a.name}'; shutil.rmtree(out, ignore_errors=True); os.makedirs(out)
    o = pc.IncrementalPipelineOptions(); o.image_names = keep; o.num_threads = a.threads
    o.ba_refine_focal_length = False; o.ba_refine_principal_point = False; o.ba_refine_extra_params = False
    o.ba_refine_sensor_from_rig = False; o.multiple_models = False
    log('map', a.name, 'images', len(keep), 'of', len(names), 'excluded', sorted(excl))
    recs = pc.incremental_mapping(f'{a.work}/db.db', f'{a.work}/imgs', out, options=o)
    best = max(recs.values(), key=lambda r: r.num_reg_images())
    best.write(out)
    json.dump({'name': a.name, 'excluded': sorted(excl), 'images_in': len(keep), 'registered': best.num_reg_images(),
               'points': best.num_points3D(), 'mean_reproj_px': best.compute_mean_reprojection_error(),
               'models': len(recs)}, open(f'{out}/summary.json', 'w'), indent=1)
    log('map done', best.summary())
    make_bank(a.work, a.name)


def make_bank(work, name):
    """Descriptor bank: per registered image, its 3-D-observing descriptors (uint8) and point ids; c-camera poses."""
    import pycolmap as pc
    out = f'{work}/maps/{name}'; rec = pc.Reconstruction(out)
    D = pc.Database.open(f'{work}/db.db')
    descs, pids, owner, imgs = [], [], [], []
    for iid, im in rec.images.items():
        if not im.has_pose: continue
        d = D.read_descriptors(iid)
        p2 = im.points2D; ids = np.array([p.point3D_id for p in p2], np.int64)
        has = np.array([p.has_point3D() for p in p2], bool)
        k = np.nonzero(has)[0]
        if len(k) == 0: continue
        T = im.cam_from_world().matrix()                    # 3x4 cam <- world
        R, t = T[:, :3], T[:, 3]
        imgs.append(dict(name=im.name, axis=R[2].tolist(), center=(-R.T @ t).tolist(), n=len(k)))
        descs.append(d[k]); pids.append(ids[k]); owner.append(np.full(len(k), len(imgs) - 1, np.int32))
    D.close()
    pts = np.array([rec.points3D[i].xyz for i in sorted(rec.points3D)], np.float64)
    pidx = {pid: j for j, pid in enumerate(sorted(rec.points3D))}
    P = np.concatenate(pids)
    np.savez_compressed(f'{out}/bank.npz', desc=np.concatenate(descs), pt=np.array([pidx[p] for p in P], np.int32),
                        owner=np.concatenate(owner), xyz=pts)
    json.dump(imgs, open(f'{out}/bank_images.json', 'w'))
    log('bank', name, len(P), 'descriptors', len(imgs), 'images', len(pts), 'points')


class Reloc:
    def __init__(self, work, name, t3, ncand=20, max_err=6.0):
        import pycolmap as pc
        self.pc = pc
        B = np.load(f'{work}/maps/{name}/bank.npz')
        self.desc = B['desc'].astype(np.float32); self.pt = B['pt']; self.owner = B['owner']; self.xyz = B['xyz']
        self.imgs = json.load(open(f'{work}/maps/{name}/bank_images.json'))
        self.axes = np.array([m['axis'] for m in self.imgs])
        self.byimg = [np.nonzero(self.owner == j)[0] for j in range(len(self.imgs))]
        self.ncand, self.max_err = ncand, max_err
        mc, mb, E = undist_maps(t3); self.mc, self.mb = mc, mb
        cam = pc.Camera(model='PINHOLE', width=W_, height=H_, params=[F_, F_, W_ / 2, H_ / 2])
        self.cams = [cam, cam]; self.cfr = [pc.Rigid3d(), pc.Rigid3d(E[:3, :4])]
        eo = pc.FeatureExtractionOptions(); eo.sift.first_octave = 0; eo.sift.peak_threshold = 0.004
        eo.sift.max_num_features = 8192; eo.num_threads = 1
        self.sift = pc.Sift(eo, pc.Device.cpu); self.m = mask_img() > 0
        self.bf = cv2.BFMatcher(cv2.NORM_L2)
        self.dscale = 512.0                                   # COLMAP stores float SIFT x 512 as uint8
        self.prev_axis = self.axes.mean(0); self.prev_axis /= np.linalg.norm(self.prev_axis)

    def feats(self, g, mp):
        u = cv2.remap(g, mp[0], mp[1], cv2.INTER_LINEAR)
        kp, d = self.sift.extract(np.ascontiguousarray(u))
        x, y = kp[:, 0].astype(int).clip(0, W_ - 1), kp[:, 1].astype(int).clip(0, H_ - 1)
        k = self.m[y, x]
        return kp[k, :2].astype(np.float64), (d[k] * self.dscale).astype(np.float32)

    def match(self, d, cand):
        rows = np.concatenate([self.byimg[j] for j in cand])
        bank = self.desc[rows]
        knn = self.bf.knnMatch(d, bank, k=6)
        best = {}
        for qi, ms in enumerate(knn):
            if not ms: continue
            p0 = self.pt[rows[ms[0].trainIdx]]
            d2 = next((m.distance for m in ms[1:] if self.pt[rows[m.trainIdx]] != p0), None)
            if d2 is not None and ms[0].distance > 0.8 * d2: continue
            if p0 not in best or ms[0].distance < best[p0][1]: best[p0] = (qi, ms[0].distance)
        q = np.array([v[0] for v in best.values()], int); p = np.array(list(best.keys()), int)
        return q, p

    def solve(self, gc, gb, ncand=None):
        pc = self.pc; ncand = ncand or self.ncand
        cand = np.argsort(-(self.axes @ self.prev_axis))[:ncand]
        P2, P3, ci = [], [], []
        for c, (g, mp) in enumerate(((gc, self.mc), (gb, self.mb))):
            kp, d = self.feats(g, mp)
            if len(d) < 10: continue
            q, p = self.match(d, cand)
            P2.append(kp[q]); P3.append(self.xyz[p]); ci += [c] * len(q)
        if not ci: return None, 0
        P2, P3 = np.concatenate(P2), np.concatenate(P3)
        ro = pc.RANSACOptions(); ro.max_error = self.max_err
        r = pc.estimate_and_refine_generalized_absolute_pose(P2, P3, ci, self.cfr, self.cams, estimation_options=ro)
        if r is None: return None, 0
        n = int(r['num_inliers'])
        M = np.eye(4); M[:3, :] = r['rig_from_world'].matrix()  # c <- map (rig = cam c)
        return np.linalg.inv(M), n                               # map <- c

    def __call__(self, gc, gb):
        T, n = self.solve(gc, gb)
        if n < 30:
            T, n = self.solve(gc, gb, ncand=2 * self.ncand)
        if n >= 30:
            ax = T[:3, 2]; self.prev_axis = ax / np.linalg.norm(ax)
        return T, n


def gate(T, ok, thr_mm=5.0, k=5):
    """GT-free temporal gate (note 18 C9 analogue for per-frame poses): frame t is a glitch if its position differs
    from the linear interpolation of trusted frames t-k and t+k by > thr_mm while those two neighbours' own
    interpolation residuals are small. Glitch / failed frames are filled by interpolation (slerp + lerp) of the nearest
    trusted frames on each side."""
    from scipy.spatial.transform import Rotation as Rot, Slerp
    N = len(T); good = ok.copy(); dev = np.full(N, np.nan)
    for t in range(N):
        if not ok[t]: continue
        L = [s for s in range(max(0, t - k), t) if ok[s]]; R = [s for s in range(t + 1, min(N, t + k + 1)) if ok[s]]
        if not L or not R: continue
        l, r = L[0], R[-1]; w = (t - l) / (r - l)
        pred = (1 - w) * T[l][:3, 3] + w * T[r][:3, 3]
        dev[t] = np.linalg.norm(T[t][:3, 3] - pred) * 1000
    # a glitch stands out from both sides: robust local median of deviations
    for t in range(N):
        if np.isfinite(dev[t]) and dev[t] > thr_mm:
            nb = dev[max(0, t - k):t + k + 1]; nb = nb[np.isfinite(nb)]
            if dev[t] > 2 * np.median(nb) + thr_mm / 2: good[t] = False
    out = T.copy(); idx = np.nonzero(good)[0]
    if len(idx) >= 2:
        rots = Rot.from_matrix(T[idx][:, :3, :3]); sl = Slerp(idx, rots)
        for t in range(N):
            if good[t]: continue
            tt = min(max(t, idx[0]), idx[-1])
            out[t] = np.eye(4); out[t][:3, :3] = sl([tt]).as_matrix()[0]
            for j in range(3): out[t][j, 3] = np.interp(tt, idx, T[idx][:, j, 3])
    return out, good, dev


def cmd_reloc(a):
    R = Reloc(a.work, a.name, a.t3, ncand=a.ncand)
    vd = f'{a.t3}/v' if a.split == 'public' else f'{a.t3}/eval/v'
    fc, N = read_video(f'{vd}/ep{a.ep}_c.mp4'); fb, Nb = read_video(f'{vd}/ep{a.ep}_b.mp4')
    N = min(N, Nb); idx = list(range(0, N, a.stride))
    T = np.full((N, 4, 4), np.nan); inl = np.zeros(N, int); t0 = time.time()
    for k, i in enumerate(idx):
        M, n = R(fc[i], fb[i]); inl[i] = n
        if n >= 30: T[i] = M
        if k % 50 == 0: log('ep', a.ep, 'frame', i, 'inliers', n, f'{(time.time() - t0) / (k + 1):.2f} s/frame')
    ok = inl >= 30
    sel = np.array(idx)
    Tg, good, dev = gate(T[sel], ok[sel], a.gate_mm)
    np.savez(a.out, frames=sel, map_T_c=T[sel], inliers=inl[sel], ok=ok[sel], gate_good=good, gate_dev_mm=dev,
             map_T_c_gated=Tg, rect_T_c=rect_T_c(a.t3), n_frames=N, map=a.name, split=a.split, ep=a.ep,
             sec_per_frame=(time.time() - t0) / len(idx))
    log('done ep', a.ep, 'frames', len(idx), 'ok', int(ok[sel].sum()), 'gated out', int((ok[sel] & ~good).sum()),
        'inliers min/med', int(inl[sel].min()), int(np.median(inl[sel])),
        f'{(time.time() - t0) / len(idx):.2f} s/frame')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd'); ap.add_argument('--t3', default='/content/t3'); ap.add_argument('--work', required=True)
    ap.add_argument('--step', type=int, default=30); ap.add_argument('--threads', type=int, default=4)
    ap.add_argument('--partners', type=int, default=12); ap.add_argument('--name', default='run3')
    ap.add_argument('--exclude', default=''); ap.add_argument('--split', default='eval')
    ap.add_argument('--ep', type=int); ap.add_argument('--out'); ap.add_argument('--stride', type=int, default=1)
    ap.add_argument('--ncand', type=int, default=20); ap.add_argument('--gate_mm', type=float, default=5.0)
    a = ap.parse_args()
    {'extract': cmd_extract, 'features': cmd_features, 'match': cmd_match, 'map': cmd_map,
     'bank': lambda a: make_bank(a.work, a.name), 'reloc': cmd_reloc}[a.cmd](a)
