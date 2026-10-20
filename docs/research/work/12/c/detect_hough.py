"""Second automatic sphere detector: Hough circles at the expected radius + smooth-interior test.
Targets grey spheres seen against grey floor at silhouettes, which the colour detector (detect2d.py) misses."""
import numpy as np, cv2

def detect_h(img_bgr, dexp, roi, smooth_max=9.0, acc=18):
    x0, y0, x1, y1 = roi; x0, y0 = max(x0, 0), max(y0, 0)
    g = cv2.cvtColor(img_bgr[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY)
    gb = cv2.GaussianBlur(g, (5, 5), 1.2)
    r0 = dexp / 2
    cs = cv2.HoughCircles(gb, cv2.HOUGH_GRADIENT, dp=1, minDist=0.9 * dexp, param1=60, param2=acc,
                          minRadius=int(0.6 * r0), maxRadius=int(1.35 * r0))
    out = []
    if cs is None: return out
    hsv = cv2.cvtColor(img_bgr[y0:y1, x0:x1], cv2.COLOR_BGR2HSV)
    lap = np.abs(cv2.Laplacian(g.astype(np.float32), cv2.CV_32F, ksize=3))
    H, W = g.shape
    for x, y, r in cs[0]:
        yy, xx = np.mgrid[0:H, 0:W]; d2 = (xx - x) ** 2 + (yy - y) ** 2
        inn = d2 <= (0.6 * r) ** 2
        if inn.sum() < 10: continue
        smooth = float(lap[inn].mean()); sat = float(hsv[..., 1][inn].mean()); val = float(hsv[..., 2][inn].mean())
        # spheres: smooth interior, low saturation, mid-grey
        if smooth < smooth_max and sat < 70 and 70 < val < 235:
            out.append(dict(x=float(x + x0), y=float(y + y0), r=float(r), smooth=smooth, sat=sat, val=val))
    return out
