"""DIG 18 B3: frame-to-frame stereo visual odometry baseline (no map), for drift comparison. Reads no GT.
Undistorted c (left, reference) / b (right) as a1. At each frame t: GFTT corners in c_t, stereo KLT c_t -> b_t with
forward-backward check, triangulation with the factory c->b extrinsic (depth 0.15-8 m, b reprojection < 1 px);
temporal KLT c_t -> c_{t+1} (fb check); PnP RANSAC (1.5 px) + LM refinement -> T_{c,t+1 <- c,t}; chained from the
frame-0 pose (stored as c_from_c0; b2_validate anchors it to the frame-0 pose of the relocalisation it validates).
usage: python b3_vo.py <split> <ep> <out json> [mask 0/1]"""
import sys, os, json, time, numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from a1_extract import NEW, newK, maps, clip, mask

SPLIT, EP, OUTJ = sys.argv[1], int(sys.argv[2]), sys.argv[3]; USE_MASK = int(sys.argv[4]) if len(sys.argv) > 4 else 0
TAG = ("p" if SPLIT == "public" else "e") + f"{EP:02d}"
CAL = json.load(open("/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public/meta/camera_calibration.json"))
T_bc = np.array([s for s in CAL["stereo_pairs"] if s["camera"] == "ego"][0]["left_to_right"], float)
K = newK("c"); Pc = K @ np.hstack([np.eye(3), np.zeros((3, 1))]); Pb = K @ T_bc[:3]
LK = dict(winSize=(21, 21), maxLevel=4, criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01))
MK = mask("c") if USE_MASK else None
RAY_EXACT = int(os.environ.get("B3_RAY_EXACT", "1"))


def klt(a, b, p):
    q, st, _ = cv2.calcOpticalFlowPyrLK(a, b, p, None, **LK)
    r, st2, _ = cv2.calcOpticalFlowPyrLK(b, a, q, None, **LK)
    ok = (st[:, 0] == 1) & (st2[:, 0] == 1) & (np.linalg.norm((r - p).reshape(-1, 2), axis=1) < 0.7)
    return q, ok


def stereo(c, b):
    p = cv2.goodFeaturesToTrack(c, 2500, 0.005, 7, mask=MK)
    if p is None: return None, None
    q, ok = klt(c, b, p); p, q = p[ok].reshape(-1, 2), q[ok].reshape(-1, 2)
    X = cv2.triangulatePoints(Pc, Pb, p.T, q.T); X = (X[:3] / X[3]).T
    xb = (T_bc[:3, :3] @ X.T + T_bc[:3, 3:]).T; uvb = (K @ xb.T).T; uvb = uvb[:, :2] / uvb[:, 2:3]
    ok = (X[:, 2] > 0.15) & (X[:, 2] < 8) & (np.linalg.norm(uvb - q, axis=1) < 1.0)
    # v2: keep the reference (c) ray exact and take only depth from stereo. v1 (b3_vo_v1_dltbias.py) used the DLT point,
    # which splits c/b vertical inconsistency between both views and gave a constant +0.058 deg/frame pitch bias.
    if RAY_EXACT:
        ray = np.linalg.solve(K, np.vstack([p.T, np.ones(len(p))])).T; X = ray * X[:, 2:3]
    return p[ok].astype(np.float32), X[ok]


Mp = {c: maps(c) for c in "bc"}
caps = {c: cv2.VideoCapture(clip(SPLIT, EP, c)) for c in "bc"}
T = np.eye(4)
rows = [dict(frame=0, c_from_c0=T[:3].tolist(), n3d=0, inl=0)]
prev = None; t = 0; t_start = time.time()
while True:
    fr = {c: caps[c].read() for c in "bc"}
    if not all(ok for ok, _ in fr.values()): break
    U = {c: cv2.remap(cv2.cvtColor(fr[c][1], cv2.COLOR_BGR2GRAY), *Mp[c][0], cv2.INTER_LINEAR) for c in "bc"}
    t0 = time.time()
    if prev is not None:
        pc, X = prev
        q, ok = klt(prevc, U["c"], pc.reshape(-1, 1, 2)); q = q.reshape(-1, 2)
        row = dict(frame=t, n3d=int(len(X)), ntrack=int(ok.sum()))
        if ok.sum() >= 12:
            succ, rv, tv, inl = cv2.solvePnPRansac(X[ok], q[ok], K, None, iterationsCount=300, reprojectionError=1.5,
                                                   confidence=0.999, flags=cv2.SOLVEPNP_EPNP)
            if succ and inl is not None and len(inl) >= 12:
                ii = inl[:, 0]; rv, tv = cv2.solvePnPRefineLM(X[ok][ii], q[ok][ii], K, None, rv, tv)
                Rr = cv2.Rodrigues(rv)[0]; D = np.eye(4); D[:3, :3] = Rr; D[:3, 3] = tv[:, 0]
                T = D @ T; row["inl"] = int(len(ii))
            else:
                row["inl"] = 0  # keep previous pose (constant-position fallback)
        else:
            row["inl"] = 0
        row["c_from_c0"] = T[:3].tolist(); row["dt"] = time.time() - t0; rows.append(row)
    prev = stereo(U["c"], U["b"]); prevc = U["c"]; t += 1
    if t % 50 == 0: print(time.strftime("%H:%M:%S"), TAG, t, rows[-1].get("inl"), flush=True)
json.dump(dict(split=SPLIT, ep=EP, tag=TAG, mask=USE_MASK, ray_exact=RAY_EXACT, frames=rows, wall_s=time.time() - t_start), open(OUTJ, "w"))
inl = np.array([r.get("inl", 0) for r in rows[1:]])
print(f"done {TAG}: {len(rows)} frames, inliers median {np.median(inl):.0f} min {inl.min()}, fails {(inl < 12).sum()}, "
      f"wall {time.time() - t_start:.0f}s", flush=True)
