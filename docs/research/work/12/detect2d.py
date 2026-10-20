"""Simple automatic marker-blob detector: grey, low-saturation, round blobs next to a black mount."""
import numpy as np, cv2
def detect(img_bgr, rmin=9, rmax=24, roi=None):
    x0, y0 = 0, 0
    if roi is not None:
        x0, y0, x1, y1 = roi; img_bgr = img_bgr[y0:y1, x0:x1]
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV).astype(np.float32)
    S, V = hsv[..., 1] / 255, hsv[..., 2] / 255
    grey = ((S < 0.18) & (V > 0.35) & (V < 0.92)).astype(np.uint8)
    dark = (V < 0.16).astype(np.uint8)
    grey = cv2.morphologyEx(grey, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lab, st, cen = cv2.connectedComponentsWithStats(grey)
    darkd = cv2.dilate(dark, np.ones((9, 9), np.uint8))
    out = []
    for k in range(1, n):
        x, y, w, h, a = st[k]
        if not (2 * rmin <= max(w, h) <= 2 * rmax + 6): continue
        fill = a / (np.pi * (max(w, h) / 2) ** 2)
        if fill < 0.55 or min(w, h) / max(w, h) < 0.6: continue
        # adjacent black mount
        ring = cv2.dilate((lab == k).astype(np.uint8), np.ones((7, 7), np.uint8)) & (lab != k).astype(np.uint8)
        darkfrac = (darkd[ring > 0] > 0).mean()
        out.append(dict(x=float(cen[k][0] + x0), y=float(cen[k][1] + y0), d=float((w + h) / 2), fill=float(fill), dark=float(darkfrac)))
    return out
if __name__ == '__main__':
    import sys
    im = cv2.imread(sys.argv[1]); roi = tuple(map(int, sys.argv[2].split(','))) if len(sys.argv) > 2 else None
    for q in detect(im, roi=roi): print({k: round(v, 2) for k, v in q.items()})
