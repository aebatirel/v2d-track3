"""DIG 20 stage C: object-motion features (cam a) for the slot-0 anchor window. No GT after frame 0.
Per step k-1 -> k: background homography H_bg from KLT points in a ring around the object (RANSAC), then a RANSAC
similarity A_k from H_bg-predicted object points to their tracked positions = object motion RELATIVE to its
surroundings (head motion cancels; parallax of a short step is sub-pixel). A_k composed from frame 0 gives the
object's image motion; reported as px displacement of the object centroid and of its extremity (radius r0).
usage: c_motion.py <tag> <ep> ...  -> out/c/mot_<tag>_p<ep>.npz"""
import sys, os, numpy as np, cv2
sys.path.insert(0, os.path.dirname(__file__))
from c_lib import *
from c_detect import fov_mask
LK = dict(winSize=(15, 15), maxLevel=3, criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 40, 0.01))


def track(g0, g1, p):
    if len(p) == 0: return p, np.zeros(0, bool)
    q, st, _ = cv2.calcOpticalFlowPyrLK(g0, g1, p, None, **LK)
    b, st2, _ = cv2.calcOpticalFlowPyrLK(g1, g0, q, None, **LK)
    ok = (st[:, 0] == 1) & (st2[:, 0] == 1) & (np.linalg.norm(b - p, axis=1) < 0.5)
    return q, ok


def seed(g, mask, n, md=5):
    p = cv2.goodFeaturesToTrack(g, n, 0.002, md, mask=mask, blockSize=5)
    return np.zeros((0, 2), np.float32) if p is None else p.reshape(-1, 2).astype(np.float32)


def motion(F, M0, max_k=None):
    H, W = M0.shape; FOV = fov_mask()
    ys, xs = np.nonzero(M0); bw, bh = np.ptp(xs) + 1, np.ptp(ys) + 1; m = int(0.6 * max(bw, bh) + 40)
    box = np.zeros((H, W), np.uint8); box[max(ys.min() - m, 0):ys.max() + m, max(xs.min() - m, 0):xs.max() + m] = 255
    G = [cv2.cvtColor(f, cv2.COLOR_BGR2GRAY) for f in F[:max_k]]
    Mk = M0.copy(); Tbg = np.eye(3)               # frame-0 -> k background map (for re-seeding the masks)
    A = np.eye(3)                                  # object relative motion (image, frame-0 coords of the object)
    c0 = np.array([xs.mean(), ys.mean()]); r0 = float(np.sqrt(((np.c_[xs, ys] - c0) ** 2).sum(1)).max())
    rows = []
    pob = pbg = None
    for k in range(1, len(G)):
        ring = cv2.subtract(cv2.bitwise_and(box, FOV), cv2.dilate(Mk, np.ones((31, 31), np.uint8)))
        inner = cv2.bitwise_and(cv2.erode(Mk, np.ones((7, 7), np.uint8)), FOV)
        if pbg is None or len(pbg) < 120: pbg = seed(G[k - 1], cv2.warpPerspective(ring, np.eye(3), (W, H)), 600)
        if pob is None or len(pob) < 40: pob = seed(G[k - 1], inner, 300, 4)
        qbg, okb = track(G[k - 1], G[k], pbg); qob, oko = track(G[k - 1], G[k], pob)
        step = (np.nan, np.nan, np.nan); nin = (int(okb.sum()), int(oko.sum())); hflow = np.nan
        Hb = None
        if okb.sum() >= 30:
            Hb, inl = cv2.findHomography(pbg[okb], qbg[okb], cv2.RANSAC, 1.5, maxIters=2000, confidence=0.995)
        if Hb is not None:
            cc0 = cv2.perspectiveTransform(np.array([[c0]], np.float32), Tbg)[0, 0]
            hflow = float(np.linalg.norm(cv2.perspectiveTransform(cc0[None, None].astype(np.float32), Hb)[0, 0] - cc0))
            Tbg = Hb @ Tbg
            if oko.sum() >= 12:
                pred = cv2.perspectiveTransform(pob[oko][None], Hb)[0]
                S, inl2 = cv2.estimateAffinePartial2D(pred, qob[oko], method=cv2.RANSAC, ransacReprojThreshold=1.0, maxIters=2000)
                if S is not None and inl2.sum() >= 10:
                    # step motion of the object relative to the background, at the current object centroid
                    cc = cv2.perspectiveTransform(np.array([[c0]], np.float32), Tbg)[0, 0]
                    dc = S[:, :2] @ cc + S[:, 2] - cc; th = np.degrees(np.arctan2(S[1, 0], S[0, 0])); sc = np.hypot(S[0, 0], S[1, 0])
                    step = (float(dc[0]), float(dc[1]), float(th)); nin = nin + (int(inl2.sum()), float(sc))
        rows.append((k,) + tuple(step) + (nin[0], nin[1], hflow))
        Mk = cv2.warpPerspective(M0, Tbg, (W, H), flags=cv2.INTER_NEAREST)
        pbg = qbg[okb]; pob = qob[oko]
    return np.array(rows, float), r0


if __name__ == '__main__':
    tag = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
    for ep in map(int, sys.argv[2:]):
        g = gt_ref(ep); R, C = cam0(ep)
        M0, z = silhouette(g['name'], g['e']['pose'][0, g['j']], R, C)
        pert = os.environ.get('MASKPERT', '')     # robustness to a worse frame-0 mask: dil<px>, ero<px>, shx<px>
        if pert.startswith('dil'): M0 = cv2.dilate(M0, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * int(pert[3:]) + 1,) * 2))
        if pert.startswith('ero'): M0 = cv2.erode(M0, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * int(pert[3:]) + 1,) * 2))
        if pert.startswith('shx'): M0 = np.roll(M0, int(pert[3:]), axis=1)
        F = frames('public', ep, 'a', n_max=140)
        rows, r0 = motion(F, M0)
        np.savez(f'{OUT}/mot_{tag}_p{ep}.npz', rows=rows, r0=r0, z=z, pert=g['pert'], pert_r=g['pert_r'], on=g['on'])
        st = rows[:, 1:4]; ok = np.isfinite(st).all(1)
        mag = np.where(ok, np.hypot(st[:, 0], st[:, 1]) + np.radians(np.abs(np.nan_to_num(st[:, 2]))) * r0, np.nan)
        print(f'p{ep} {g["name"][:12]} pert {g["pert"]}/{g["pert_r"]} on {g["on"]} r0 {r0:.0f}px z {z:.2f} | step mag (px) by a-index: '
              + ' '.join(f'{int(rows[i, 0])}:{mag[i]:.1f}' for i in range(len(rows)) if np.isfinite(mag[i]) and mag[i] > 0.6 and rows[i, 0] < g['on'] + 6), flush=True)
