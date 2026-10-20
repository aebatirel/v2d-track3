"""Stage C: prior-free acquisition by marker identity from inter-marker distances (no pose prior, no GT at inference).
Input: stage-B FULL-FRAME candidate rows (det_<ep>.npz rows with ff flag = 1, i.e. Hough over the whole image, no ROI) and
their LOEO v2 scores (score_<ep>.npy). Per such frame: b/c detections (score >= THR, NMS) matched along epipolar lines
(< 2 px, radius ratio 0.7-1.4, depth 0.2-1.5 m), triangulated in cam b; then for each object, every triple of 3-D points whose
pairwise distances match a triple of catalogue markers (|d - D| < TOL) gives a Kabsch pose; support = other 3-D points within
6 mm of other markers + cam-a detections within 6 px of projected markers; best hypothesis per object kept if support >= 0
(3 matched markers) and residual rms < 3 mm. Evaluation (after inference): pose -> mocap via Treg, vs GT(t - 0.5).
usage: [THR=0.5] [TOL=4] c/acq17.py ep"""
import sys, os, json, itertools, numpy as np, cv2
from scipy.spatial.transform import Rotation as Rot
sys.path.insert(0, '/Users/aebatirel/Documents/Code/v2d-research/work/17')
import lib17 as L, det17lib as D, seg17
ep = int(sys.argv[1]); THR = float(os.environ.get('THR', 0.5)); TOL = float(os.environ.get('TOL', 4)) / 1000
d = np.load(f'out/det_{ep}.npz'); rows = d['rows']; S = np.load(f'out/score_{ep}.npy'); VO = np.load(f'out/vo_public_{ep}.npy')
sy = json.load(open(f'out/sync_{ep}.json')); KA = int(round(sy['delta']))
Tba = L.ext('a').copy(); Tba[:3, :3] = Rot.from_rotvec(sy['drot']).as_matrix() @ Tba[:3, :3]; Tbc = L.ext('c')
Kb, db, _ = L.cam('b'); Kc, dc, _ = L.cam('c'); Tcb = np.linalg.inv(Tbc)                 # X_c = Tcb X_b
P_b = Kb @ np.eye(3, 4); P_c = Kc @ Tcb[:3]
names = L.load_gt(ep)['names']; OBJ = [n for n in names if n in L.CAT and len(L.CAT[n]) >= 3]
MK = {n: np.array([q['c'] for q in L.CAT[n]]) for n in OBJ}
def und(K, dd, uv): return cv2.undistortPoints(uv.reshape(-1, 1, 2).astype(np.float64), K, dd, P=K).reshape(-1, 2)
def kabsch(A, B):   # R, t with B ~ R A + t
    ca, cb = A.mean(0), B.mean(0); H = (A - ca).T @ (B - cb); U, s, Vt = np.linalg.svd(H); Dg = np.diag([1, 1, np.sign(np.linalg.det(Vt.T @ U.T))])
    R = Vt.T @ Dg @ U.T; return R, cb - R @ ca
ff = rows[:, 9] == 1; frames = sorted(set(rows[ff, 0].astype(int))); out = []
for t in frames:
    def dets(ci):
        m = (rows[:, 0] == t) & (rows[:, 1] == ci) & ff & (S >= THR); q = np.c_[rows[m][:, 2:5], S[m]]; q = q[np.argsort(-q[:, 3])]
        keep = []
        for i in range(len(q)):
            if all(np.hypot(*(q[i, :2] - q[k, :2])) > max(q[i, 2], q[k, 2]) for k in keep): keep.append(i)
        return q[keep]
    Bd, Cd, Ad = dets(1), dets(2), dets(0)
    if len(Bd) == 0 or len(Cd) == 0: out.append((t, len(Bd), len(Cd), 0, {})); continue
    ub, uc = und(Kb, db, Bd[:, :2]), und(Kc, dc, Cd[:, :2])
    F = np.linalg.inv(Kc).T @ (np.cross(np.eye(3), Tcb[:3, 3]) @ Tcb[:3, :3]) @ np.linalg.inv(Kb)     # x_c^T F x_b = 0
    X3 = []
    for i in range(len(Bd)):
        l = F @ np.r_[ub[i], 1]; dist = np.abs(np.c_[uc, np.ones(len(uc))] @ l) / np.hypot(l[0], l[1])
        for k in np.flatnonzero((dist < 2.0) & (Cd[:, 2] / Bd[i, 2] > 0.7) & (Cd[:, 2] / Bd[i, 2] < 1.4)):
            Xh = cv2.triangulatePoints(P_b, P_c, ub[i].reshape(2, 1), uc[k].reshape(2, 1)).ravel(); X = Xh[:3] / Xh[3]
            if 0.2 < X[2] < 1.5: X3.append(X)
    X3 = np.array(X3); res = {}
    if len(X3) >= 3:
        Pa = VO[t]; Pa_inv = np.linalg.inv(Tba)       # cam a frame t+KA ~ same head pose (VO frame b_t used as reference)
        for n in OBJ:
            M = MK[n]; DM = np.linalg.norm(M[:, None] - M[None], axis=2); DX = np.linalg.norm(X3[:, None] - X3[None], axis=2); best = None
            for (p, q, r) in itertools.combinations(range(len(X3)), 3):
                for (a, b, c) in itertools.permutations(range(len(M)), 3):
                    if abs(DX[p, q] - DM[a, b]) < TOL and abs(DX[p, r] - DM[a, c]) < TOL and abs(DX[q, r] - DM[b, c]) < TOL:
                        R, tt = kabsch(M[[a, b, c]], X3[[p, q, r]]); rms = np.sqrt(np.mean(np.sum((M[[a, b, c]] @ R.T + tt - X3[[p, q, r]]) ** 2, 1)))
                        if rms > 0.003: continue
                        Y = M @ R.T + tt; sup = sum(np.min(np.linalg.norm(X3 - Y[m], axis=1)) < 0.006 for m in range(len(M)) if m not in (a, b, c))
                        if len(Ad):   # cam a support (head pose of b_t, a frame t + KA; small motion ignored)
                            Ya = Y @ Pa_inv[:3, :3].T + Pa_inv[:3, 3]; uva, _ = cv2.projectPoints(Ya.reshape(-1, 1, 3), np.zeros(3), np.zeros(3), *L.cam('a')[:2]); uva = uva.reshape(-1, 2)
                            sup += 0.5 * sum(np.min(np.hypot(*(Ad[:, :2] - uva[m]).T)) < 6 for m in range(len(M)))
                        if best is None or (sup, -rms) > (best[0], -best[1]): best = (sup, rms, R, tt, (a, b, c))
            if best: res[n] = best
    out.append((t, len(Bd), len(Cd), len(X3), res))
# ---------------- evaluation (GT read only here) ----------------
gt = L.load_gt(ep); Treg = np.array(json.load(open(f'out/reg2_{ep}.json'))['Treg']); seg = seg17.segments(gt)[0]
print(f'ep {ep}: {len(frames)} full-frame sampled frames, THR {THR}, TOL {TOL*1000:.0f} mm')
summ = {n: [] for n in OBJ}
for t, nb, nc, nx, res in out:
    s = f'  t {t:3d} det b{nb} c{nc} 3D {nx}:'
    for n in OBJ:
        j = names.index(n); Rg, tg = D.gt_interp(gt, j, t - 0.5)
        if n in res:
            sup, rms, R, tt, ids = res[n]; P = VO[t]; Rw = Treg[:3, :3] @ P[:3, :3] @ R; tw = Treg[:3, :3] @ (P[:3, :3] @ tt + P[:3, 3]) + Treg[:3, 3]
            et = np.linalg.norm(tw - tg) * 1000; er = np.degrees(np.linalg.norm(Rot.from_matrix(Rg.T @ Rw).as_rotvec()))
            summ[n].append((t, seg[t, j], 1, et, er, sup)); s += f' {n[:10]} ids{ids} sup{sup:.1f} err {et:.0f} mm {er:.1f} deg |'
        else: summ[n].append((t, seg[t, j], 0, np.nan, np.nan, 0)); s += f' {n[:10]} - |'
    print(s)
for n in OBJ:
    A = np.array(summ[n]); ok = A[:, 2] == 1; good = ok & (A[:, 3] < 20) & (A[:, 4] < 10)
    print(f'{n}: acquired {ok.mean():.2f} of frames; correct (<20 mm, <10 deg) {good.mean():.2f}; wrong {np.mean(ok & ~good):.2f}; median err of correct {np.nanmedian(A[good, 3]) if good.any() else np.nan:.1f} mm {np.nanmedian(A[good, 4]) if good.any() else np.nan:.1f} deg')
