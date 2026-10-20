"""DIG 20 stage C: automatic first-contact detector for the slot-0 anchor window (cam a, colour).
Inputs at inference: the video and a frame-0 slot-0 mask (here: GT mesh rendered with the D18 frame-0 camera, a
stand-in for the perception stack's frame-0 segmentation). No GT after frame 0 is read by detect().
Method: object-local registration frame 0 -> k (KLT from frame 0 with homography prediction + RANSAC on the static
neighbourhood), shift-tolerant colour change vs the warped frame 0, morphological cleaning, and an intrusion score =
changed area inside the dilated object mask that belongs to a changed component reaching outside the object
(something entering), or a large change inside the object (object motion backstop).
Output frames are cam-a indices; converted to the b/c timeline with the Stage A pairing.
usage: c_detect.py <tag> <ep> ...   -> out/c/det_<tag>_p<ep>.npz, printed summary"""
import sys, os, json, numpy as np, cv2
sys.path.insert(0, os.path.dirname(__file__))
from c_lib import *

P = dict(margin=0.6, shift=3, tau=28.0, open=3, r_touch=8, a_touch=120, a_inside=600, persist=2, max_frames=160,
         min_inl=25, chroma_w=1.0)


def pairing_n(key, row):
    t = json.load(open(f'{ROOT}/work/20/out/sync_table.json'))['episodes'][key]
    for s in t['pairing_a_to_b']:
        if s['rows'][0] <= row <= s['rows'][1]: return s['n']
    return 1


def shift_min_diff(A, B, s):
    """min over integer shifts |d|<=s of mean-abs colour diff between A(x) and B(x+d) (float32 HxWx3)."""
    H, W = A.shape[:2]; best = np.full((H, W), 1e9, np.float32)
    Bp = cv2.copyMakeBorder(B, s, s, s, s, cv2.BORDER_REPLICATE)
    for dy in range(-s, s + 1):
        for dx in range(-s, s + 1):
            d = np.abs(A - Bp[s + dy:s + dy + H, s + dx:s + dx + W]).mean(2)
            np.minimum(best, d, out=best)
    return best


def fov_mask():
    """pixels of the undistorted pinhole cam a that lie inside the original image."""
    (m1, m2), (w0, h0) = d18maps('a')
    return ((m1 >= 1) & (m1 <= w0 - 2) & (m2 >= 1) & (m2 <= h0 - 2)).astype(np.uint8) * 255


def features(F, M0, p=P, keep_vis=()):
    """Per-frame features (no decision). Columns: k, touch (intruder area within r_touch of the object), overlap
    (intruder area inside the eroded object), inside (object-confined change area), dmin_px (closest intruder pixel
    to the object), n_inl, reg_med_px, changed_total, roi_border_touch (intruder touching the ROI border)."""
    H, W = M0.shape; FOV = fov_mask()
    ys, xs = np.nonzero(M0); bw, bh = np.ptp(xs) + 1, np.ptp(ys) + 1
    m = int(p['margin'] * max(bw, bh) + 40)
    x0, x1, y0, y1 = max(xs.min() - m, 0), min(xs.max() + m + 1, W), max(ys.min() - m, 0), min(ys.max() + m + 1, H)
    roi = np.zeros((H, W), np.uint8); roi[y0:y1, x0:x1] = 255; roi &= FOV
    g0 = cv2.cvtColor(F[0], cv2.COLOR_BGR2GRAY)
    pts0 = cv2.goodFeaturesToTrack(g0, 800, 0.003, 6, mask=cv2.erode(roi, np.ones((9, 9), np.uint8)), blockSize=5)
    pts0 = pts0.reshape(-1, 2).astype(np.float32)
    I0 = F[0][y0:y1, x0:x1].astype(np.float32); V0 = FOV[y0:y1, x0:x1]; Fk_ = FOV[y0:y1, x0:x1] > 0
    S = np.array([[1, 0, x0], [0, 1, y0], [0, 0, 1.0]]); Si = np.linalg.inv(S)
    Hk = np.eye(3); lk = dict(winSize=(21, 21), maxLevel=4, criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 40, 0.01))
    se = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * p['r_touch'] + 1,) * 2)
    rows = []; vis = {}
    for k in range(1, len(F)):
        gk = cv2.cvtColor(F[k], cv2.COLOR_BGR2GRAY)
        pr = cv2.perspectiveTransform(pts0[None], Hk)[0].astype(np.float32)
        p1, st, _ = cv2.calcOpticalFlowPyrLK(g0, gk, pts0, pr.copy(), flags=cv2.OPTFLOW_USE_INITIAL_FLOW, **lk)
        pb, st2, _ = cv2.calcOpticalFlowPyrLK(gk, g0, p1, pts0.copy(), flags=cv2.OPTFLOW_USE_INITIAL_FLOW, **lk)
        ok = (st[:, 0] == 1) & (st2[:, 0] == 1) & (np.linalg.norm(pb - pts0, axis=1) < 1.0)
        ninl = int(ok.sum()); med = np.nan
        if ok.sum() >= p['min_inl']:
            Hn, inl = cv2.findHomography(pts0[ok], p1[ok], cv2.RANSAC, 2.5, maxIters=2000, confidence=0.995)
            if Hn is not None and inl.sum() >= p['min_inl']:
                ninl = int(inl.sum()); q = inl[:, 0] == 1
                med = float(np.median(np.linalg.norm(cv2.perspectiveTransform(pts0[ok][q][None], Hn)[0] - p1[ok][q], axis=1)))
                Hk = Hn
        T = Si @ Hk @ S; sz = (x1 - x0, y1 - y0)
        Iw = cv2.warpPerspective(I0, T, sz, flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        Mk = cv2.warpPerspective(M0[y0:y1, x0:x1], T, sz, flags=cv2.INTER_NEAREST) > 0
        valid = (cv2.warpPerspective(V0, T, sz, flags=cv2.INTER_NEAREST) > 0) & Fk_
        valid = cv2.erode(valid.astype(np.uint8), np.ones((2 * p['shift'] + 3,) * 2, np.uint8)) > 0
        Ik = F[k][y0:y1, x0:x1].astype(np.float32)
        g = np.array([np.median(Ik[..., c][valid] + 1) / np.median(Iw[..., c][valid] + 1) for c in range(3)], np.float32)
        D = shift_min_diff(Ik, Iw * g, p['shift'])
        ch = ((D > p['tau']) & valid).astype(np.uint8)
        if p['open']: ch = cv2.morphologyEx(ch, cv2.MORPH_OPEN, np.ones((p['open'], p['open']), np.uint8))
        Md = cv2.dilate(Mk.astype(np.uint8), se) > 0
        Me = cv2.erode(Mk.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
        dist = cv2.distanceTransform((~Mk).astype(np.uint8), cv2.DIST_L2, 3)
        n, lab, stats, _ = cv2.connectedComponentsWithStats(ch, connectivity=8)
        touch = overlap = inside = 0; dmin = 1e4; border = 0
        bmask = np.zeros_like(ch, bool); bmask[[0, -1], :] = True; bmask[:, [0, -1]] = True
        for i in range(1, n):
            if stats[i, cv2.CC_STAT_AREA] < 40: continue
            comp = lab == i
            a_out = int((comp & ~Md).sum())
            if a_out >= 30:
                dmin = min(dmin, float(dist[comp].min()))
                a_t = int((comp & Md).sum()); touch += a_t; overlap += int((comp & Me).sum())
                if a_t > 0 and (comp & bmask).any(): border += a_t
            else:
                inside += int((comp & Md).sum())
        rows.append((k, touch, overlap, inside, dmin, ninl, med, int(ch.sum()), border))
        if k in keep_vis: vis[k] = (F[k][y0:y1, x0:x1].copy(), ch.copy(), Mk.copy())
    return np.array(rows, float), (x0, y0, x1, y1), vis


if __name__ == '__main__':
    tag = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
    for ep in map(int, sys.argv[2:]):
        g = gt_ref(ep); R, C = cam0(ep)
        M0, z = silhouette(g['name'], g['e']['pose'][0, g['j']], R, C)
        F = frames('public', ep, 'a', n_max=P['max_frames'])
        keep = set(range(max(g['pert'] - 12, 1), min(g['pert'] + 6, len(F)), 3))
        rows, box, vis = features(F, M0, keep_vis=keep)
        np.savez(f'{OUT}/feat_{tag}_p{ep}.npz', rows=rows, pert=g['pert'], on=g['on'], box=box, z=z, n=g['n'])
        tiles = []
        for k in sorted(vis):
            im, ch, Mk = vis[k]; o = im.copy(); o[ch > 0] = (0.5 * o[ch > 0] + [0, 0, 128]).astype(np.uint8)
            cnt, _ = cv2.findContours(Mk.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            cv2.drawContours(o, cnt, -1, (0, 255, 0), 1)
            o = cv2.resize(o, (240, int(240 * o.shape[0] / o.shape[1]))); cv2.putText(o, f'a{k}', (3, 14), 0, 0.45, (255, 255, 0), 1)
            tiles.append(o)
        if tiles: cv2.imwrite(f'{OUT}/feat_{tag}_p{ep}.jpg', np.hstack(tiles))
        print(f'p{ep} done n_proc {len(rows)} pert {g["pert"]} z {z:.2f}', flush=True)
