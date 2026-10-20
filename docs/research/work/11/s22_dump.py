"""Stage C: dump frame 0 (decoded, upright as delivered) of local public/eval cam_a clips. Research only."""
import cv2, os, sys
ROOT = "/Users/aebatirel/Documents/Code/v2d-research"
for split, eps in [("public", [0, 11, 12, 13, 18, 21, 22, 23, 26, 31, 39, 41])]:
    for ep in eps:
        p = f"{ROOT}/data/track_3/{split}/videos/chunk-000/observation.images.ego_cam_a/episode_{ep:06d}.mp4"
        c = cv2.VideoCapture(p); ok, f = c.read()
        if ok: cv2.imwrite(f"cfr/{split[:3]}{ep}_f0.png", f); print(ep, f.shape)
