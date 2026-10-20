"""DIG 18 C11 = c1_reloc.py + synthetic occluder (env C11_OCC: c50/c75 = central vertical band of 50/75 %% of the width, b67 = lower 67 %% of the height, l50 = left half; g60/g160 = gamma; s30 = 30 %% exposure + noise; applied to a, b and c after undistortion). (Original doc: copy of B1 + C1_PUBONLY env, c-only PnP, periodic dumps): relocalise EVERY frame of a clip against a room map (pycolmap 4.2.1, CPU). Reads no GT.
Per frame t (frames matched by index across a/b/c):
  - undistort b, c, a exactly as a1 (PINHOLE; b/c 1280x800 f=420, a 1014x760 f=500);
  - SIFT (pycolmap, first_octave 0 for speed; map used first_octave -1);
  - candidate map images = the N map images whose optical axis is closest to the prior pose's (prior = last
    successful pose, else the clip's frame-0 map image); excluded: own-session images other than frame 0 if
    exclude_own=1 (for run1; run2 does not contain them anyway);
  - 2D-3D matching against the candidates' 3D-point-observing descriptors, Lowe ratio vs the best DIFFERENT 3D point;
  - b/c: generalized absolute pose of the c-referenced rig (c->b factory extrinsic), LO-RANSAC + refinement;
  - a: single-camera absolute pose (its own map images).
Output json: per frame poses (cam_from_world 3x4 in MAP coordinates), inliers, timings, blur.
usage: python b1_reloc.py <model dir> <split public|evaluation> <ep> <out json> [exclude_own 0/1] [stride] [maxframes]"""
import sys, os, json, time, numpy as np, cv2
import pycolmap

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from a1_extract import NEW, maps, clip
ROOT = "/Users/aebatirel/Documents/Code/v2d-research"
CAL = json.load(open(f"{ROOT}/data/track_3/public/meta/camera_calibration.json"))
EGO = [s for s in CAL["stereo_pairs"] if s["camera"] == "ego"][0]
T_bc = np.array(EGO["left_to_right"], float)  # X_b = R X_c + t

MODEL = os.path.abspath(sys.argv[1]); SPLIT = sys.argv[2]; EP = int(sys.argv[3]); OUTJ = sys.argv[4]
EXCL = int(sys.argv[5]) if len(sys.argv) > 5 else 0
STRIDE = int(sys.argv[6]) if len(sys.argv) > 6 else 1
MAXF = int(sys.argv[7]) if len(sys.argv) > 7 else 10 ** 6
TAG = ("p" if SPLIT == "public" else "e") + f"{EP:02d}"
N_BC, N_A, RATIO, KNN = 20, 12, 0.8, 6


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


# ---------------- map bank (cached per model) ----------------
def load_bank():
    cache = f"{MODEL}/bank.npz"
    rec = pycolmap.Reconstruction(MODEL)
    pts = {pid: np.asarray(p.xyz) for pid, p in rec.points3D.items()}
    if os.path.exists(cache) and os.path.exists(cache + ".json"):  # own cache: arrays npz (no pickle) + meta json
        z = np.load(cache); mj = json.load(open(cache + ".json"))
        meta = {n: dict(v, R=np.array(v["R"]), t=np.array(v["t"]), axis=np.array(v["axis"]), C=np.array(v["C"])) for n, v in mj.items()}
        return rec, pts, meta, z["desc"], z["pid"], z["img"]
    dbp = os.path.join(os.path.dirname(os.path.dirname(MODEL)), "db.db")
    db = pycolmap.Database.open(dbp)
    D, P, I, meta = [], [], [], {}
    for k, (iid, im) in enumerate(sorted(rec.images.items())):
        T = im.cam_from_world(); R = T.rotation.matrix(); t = np.asarray(T.translation)
        idx = [j for j, p2 in enumerate(im.points2D) if p2.has_point3D()]
        pid = [im.points2D[j].point3D_id for j in idx]
        d = db.read_descriptors(iid).data[idx]
        meta[im.name] = dict(k=k, R=R, t=t, axis=R[2], C=-R.T @ t, cam=im.name.split("/")[0])
        D.append(d); P.append(np.array(pid, np.int64)); I.append(np.full(len(idx), k, np.int32))
    db.close()
    D, P, I = np.vstack(D), np.concatenate(P), np.concatenate(I)
    np.savez(cache, desc=D, pid=P, img=I)
    json.dump({n: {k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in m.items()} for n, m in meta.items()},
              open(cache + ".json", "w"))
    return rec, pts, meta, D, P, I


rec, PTS, META, DESC, PID, IMGK = load_bank()
NAME_OF_K = {v["k"]: n for n, v in META.items()}
CAMS = {}
for im in rec.images.values():
    CAMS.setdefault(im.name.split("/")[0], rec.cameras[im.camera_id])
log("bank", DESC.shape, "images", len(META), "points", len(PTS))


PUBONLY = int(os.environ.get("C1_PUBONLY", "0"))


def allowed(name):
    tag, fr = name.split("/")[1].split("_")[0], int(name.split("_")[1][:4])
    if PUBONLY and tag.startswith("e"): return False  # public-only map images (no pooled eval frames used for matching)
    return not (EXCL and tag == TAG and fr != 0)


def candidates(axis, cams, n):
    L = [(float(np.arccos(np.clip(META[nm]["axis"] @ axis, -1, 1))), nm) for nm in META
         if META[nm]["cam"] in cams and allowed(nm)]
    L.sort(); return [nm for _, nm in L[:n]]


_BANK = {}
BF = cv2.BFMatcher(cv2.NORM_L2)


def bank_for(names):
    key = tuple(sorted(names))
    if key not in _BANK:
        if len(_BANK) > 6: _BANK.clear()
        ks = np.array([META[n]["k"] for n in names]); sel = np.isin(IMGK, ks)
        _BANK[key] = (np.ascontiguousarray(DESC[sel].astype(np.float32)), None, PID[sel])
    return _BANK[key]


def match(q, B, Bn, pid):
    """q: n x 128 float32 (x512 scale). Lowe ratio vs the best match to a DIFFERENT 3D point among the k nearest.
    returns (query idx, point3D id, dist)."""
    if len(q) == 0 or len(B) < KNN: return np.zeros(0, int), np.zeros(0, np.int64), np.zeros(0)
    km = BF.knnMatch(np.ascontiguousarray(q, dtype=np.float32), B, k=KNN)
    qi, pp, dd = [], [], []
    for i, ms in enumerate(km):
        if not ms: continue
        p0 = pid[ms[0].trainIdx]; d1 = ms[0].distance; d2 = None
        for m in ms[1:]:
            if pid[m.trainIdx] != p0: d2 = m.distance; break
        if (d2 is not None and d1 < RATIO * d2) or (d2 is None and d1 < 250):
            qi.append(i); pp.append(p0); dd.append(d1)
    if not qi: return np.zeros(0, int), np.zeros(0, np.int64), np.zeros(0)
    qi, pp, dd = np.array(qi), np.array(pp), np.array(dd)
    best = {}
    for i in np.argsort(dd):  # one query per 3D point (closest)
        best.setdefault(pp[i], i)
    keep = np.array(sorted(best.values()))
    return qi[keep], pp[keep], dd[keep]


FO = int(os.environ.get("B1_FO", "0")); PEAK = float(os.environ.get("B1_PEAK", "0.004"))
EO = pycolmap.FeatureExtractionOptions(); EO.sift.max_num_features = 6000; EO.sift.first_octave = FO; EO.num_threads = 1
EO.sift.peak_threshold = PEAK
SIFT = pycolmap.FeatureExtractor.create(EO, pycolmap.Device.cpu)


def sift(g):
    kp, d = SIFT.extract_from_uint8_array(np.ascontiguousarray(g))
    xy = np.array([(k.x, k.y) for k in kp], np.float64).reshape(-1, 2); d = np.asarray(d.data).astype(np.float32)
    return xy, d  # uint8 descriptors are 512 x unit RootSIFT, same scale as the database


RANSAC = pycolmap.RANSACOptions(); RANSAC.max_error = 6.0; RANSAC.min_inlier_ratio = 0.05; RANSAC.max_num_trials = 5000
APE = pycolmap.AbsolutePoseEstimationOptions(); APE.ransac.max_error = 6.0; APE.ransac.min_inlier_ratio = 0.05
REF = pycolmap.AbsolutePoseRefinementOptions(); REF.refine_focal_length = False; REF.refine_extra_params = False
RIG = [pycolmap.Rigid3d(), pycolmap.Rigid3d(T_bc[:3, :])]


def rig_pose(obs):
    """obs: {'c': (xy, pids), 'b': (xy, pids)} -> dict or None"""
    xy, X, ci = [], [], []
    for j, c in enumerate("cb"):
        q, p = obs[c]
        if len(p): xy.append(q); X.append(np.array([PTS[i] for i in p])); ci += [j] * len(p)
    if len(ci) < 12: return None
    r = pycolmap.estimate_and_refine_generalized_absolute_pose(np.vstack(xy), np.vstack(X), ci, RIG,
                                                                [CAMS["c"], CAMS["b"]], RANSAC, REF)
    return r


def mono_pose(xy, p, cam):
    if len(p) < 8: return None
    return pycolmap.estimate_and_refine_absolute_pose(xy, np.array([PTS[i] for i in p]), CAMS[cam], APE, REF)


def T34(T):
    return np.hstack([T.rotation.matrix(), np.asarray(T.translation)[:, None]])


# ---------------- main loop ----------------
M = {c: maps(c) for c in "abc"}
caps = {c: cv2.VideoCapture(clip(SPLIT, EP, c)) for c in "abc"}
nfr = min(int(caps[c].get(cv2.CAP_PROP_FRAME_COUNT)) for c in "abc")
f0 = {c: f"{c}/{TAG}_0000.jpg" for c in "abc"}
def mean_axis(cam):
    v = np.mean([META[n]["axis"] for n in META if META[n]["cam"] == cam and allowed(n)], axis=0); return v / np.linalg.norm(v)


prior = {c: (META[f0[c]]["axis"] if (f0[c] in META and allowed(f0[c])) else mean_axis(c)) for c in "ca"}
log(TAG, "frames", nfr, "prior from map frame 0:", {k: v is not None for k, v in prior.items()}, "exclude_own", EXCL)
R_bc = T_bc[:3, :3]
rows = []; t_start = time.time()
for t in range(min(nfr, MAXF)):
    fr = {c: caps[c].read() for c in "abc"}
    if not all(ok for ok, _ in fr.values()): break
    if t % STRIDE: continue
    tm = {}; row = dict(frame=t)
    t0 = time.time(); U = {}
    for c in "abc":
        (m1, m2), _ = M[c]; img = fr[c][1]
        g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
        U[c] = cv2.remap(g, m1, m2, cv2.INTER_AREA if c == "a" else cv2.INTER_LINEAR)
    tm["undist"] = time.time() - t0
    OCC = os.environ.get("C11_OCC", "")
    for c in "abc":
        h, w = U[c].shape
        if OCC.startswith("c"):
            fw = int(OCC[1:]) / 100; x0 = int(w * (0.5 - fw / 2)); U[c][:, x0:x0 + int(w * fw)] = 128
        elif OCC.startswith("b"):
            U[c][int(h * (1 - int(OCC[1:]) / 100)):, :] = 128
        elif OCC.startswith("l"):
            U[c][:, :int(w * int(OCC[1:]) / 100)] = 128
        elif OCC.startswith("g"):  # global gamma (g60 = gamma 0.6 brighter, g160 darker)
            U[c] = (255 * (U[c] / 255.0) ** (int(OCC[1:]) / 100)).astype(np.uint8)
        elif OCC.startswith("s"):  # exposure scale (s30 = 30 %% intensity, 8-bit requantised) + read noise sigma 2
            U[c] = np.clip(U[c] * (int(OCC[1:]) / 100) + np.random.default_rng(t).normal(0, 2, U[c].shape), 0, 255).astype(np.uint8)
    row["blur_c"] = float(cv2.Laplacian(U["c"], cv2.CV_64F).var()); row["blur_a"] = float(cv2.Laplacian(U["a"], cv2.CV_64F).var())
    t0 = time.time(); F = {c: sift(U[c]) for c in "abc"}; tm["sift"] = time.time() - t0
    row["nfeat"] = {c: len(F[c][0]) for c in "abc"}
    # ---- b/c rig ----
    t0 = time.time()
    axis_c = prior["c"] if prior["c"] is not None else META[candidates(np.array([0, 0, 1.0]), "c", 1)[0]]["axis"]
    res = None
    for n in (N_BC, 2 * N_BC):
        cand = candidates(axis_c, "bc", n); B, Bn, pid = bank_for(cand)
        obs = {}
        for c in "cb":
            qi, pp, _ = match(F[c][1], B, Bn, pid); obs[c] = (F[c][0][qi], pp)
        tm["match_bc"] = time.time() - t0; t1 = time.time()
        res = rig_pose(obs); tm["pnp_bc"] = time.time() - t1
        row["nmatch_bc"] = {c: int(len(obs[c][1])) for c in "cb"}
        if res is not None and res["num_inliers"] >= 30: break
    if res is not None:
        T = T34(res["rig_from_world"]); row["c_from_world"] = T.tolist(); row["inl_bc"] = int(res["num_inliers"])
        m = np.asarray(res["inlier_mask"]); nc = len(obs["c"][1]); row["inl_c"] = int(m[:nc].sum()); row["inl_b"] = int(m[nc:].sum())
        if res["num_inliers"] >= 30: prior["c"] = T[2, :3]
    else:
        row["inl_bc"] = 0
    rco = mono_pose(*obs["c"], "c") if len(obs["c"][1]) >= 8 else None  # c-only PnP (rig-extrinsic-free check)
    if rco is not None: row["c_only_from_world"] = T34(rco["cam_from_world"]).tolist(); row["inl_c_only"] = int(rco["num_inliers"])
    # ---- cam_a own PnP ----
    t0 = time.time()
    axis_a = prior["a"] if prior["a"] is not None else (R_bc.T[:, 2] if False else axis_c)
    ra = None
    for n in (N_A, 2 * N_A):
        cand = candidates(axis_a, "a", n); B, Bn, pid = bank_for(cand)
        qi, pp, _ = match(F["a"][1], B, Bn, pid)
        ra = mono_pose(F["a"][0][qi], pp, "a"); row["nmatch_a"] = int(len(pp))
        if ra is not None and ra["num_inliers"] >= 30: break
    tm["a_total"] = time.time() - t0
    if ra is not None:
        T = T34(ra["cam_from_world"]); row["a_from_world"] = T.tolist(); row["inl_a"] = int(ra["num_inliers"])
        if ra["num_inliers"] >= 30: prior["a"] = T[2, :3]
    else:
        row["inl_a"] = 0
    row["time"] = tm; rows.append(row)
    if len(rows) % 40 == 0:
        json.dump(dict(partial=True, frames=rows), open(OUTJ + ".part", "w"))
    if t % 20 == 0:
        log(f"t={t} feat {row['nfeat']} match_bc {row.get('nmatch_bc')} inl_bc {row['inl_bc']} (c {row.get('inl_c')} b {row.get('inl_b')}) "
            f"inl_a {row['inl_a']} | " + " ".join(f"{k} {v:.2f}" for k, v in tm.items()))
json.dump(dict(occ=os.environ.get("C11_OCC", ""), pubonly=PUBONLY, model=MODEL, split=SPLIT, ep=EP, tag=TAG, exclude_own=EXCL, stride=STRIDE, n_bc=N_BC, n_a=N_A,
               ratio=RATIO, sift_first_octave=FO, sift_peak=PEAK, frames=rows, wall_s=time.time() - t_start), open(OUTJ, "w"))
ok = np.array([r["inl_bc"] >= 30 for r in rows]); oka = np.array([r["inl_a"] >= 30 for r in rows])
log(f"done {TAG}: {len(rows)} frames, rig ok {ok.mean():.3f}, a ok {oka.mean():.3f}, wall {time.time() - t_start:.0f}s")
