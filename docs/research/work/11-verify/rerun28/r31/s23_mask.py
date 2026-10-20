"""Stage C: object foreground mask (white | blue | beige-white) and don't-care (dark) mask, frame 0, public cam_a.
Research only (GT-side camera-pose analysis)."""
import cv2, numpy as np
def masks(img, scale=1.0):
    if scale != 1.0: img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    H, S, V = hsv[..., 0].astype(int), hsv[..., 1].astype(int), hsv[..., 2].astype(int)
    white = (S < 55) & (V > 185)
    blue = (H >= 95) & (H <= 130) & (S > 50) & (V > 50)
    dark = V < 60
    fg = cv2.morphologyEx((white | blue).astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)) > 0
    return img, fg, dark & ~fg
if __name__ == "__main__":
    out = []
    for ep in [12, 21, 26, 0]:
        img, fg, dc = masks(cv2.imread(f"cfr/pub{ep}_f0.png"), 0.5)
        vis = img.copy(); vis[fg] = (0, 0, 255); vis[dc] = (255, 0, 0)
        out.append(vis)
    cv2.imwrite("cfr/mask_check.png", np.vstack([np.hstack(out[:2]), np.hstack(out[2:])]))
