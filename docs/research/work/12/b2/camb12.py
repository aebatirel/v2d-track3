"""Stage B gap 2: base inscription in cam b (and cam c) for public ep 12 (blue cup inverted in the rack)."""
import cv2, numpy as np, sys
V = '/Users/aebatirel/Documents/Code/v2d-research/data/track_3/public/videos/chunk-000/observation.images.ego_cam_%s/episode_000012.mp4'
def fr(cam, i):
    c = cv2.VideoCapture(V % cam); c.set(cv2.CAP_PROP_POS_FRAMES, i); ok, im = c.read(); return im
fi = int(sys.argv[1]) if len(sys.argv) > 1 else 180
a = fr('a', fi); b = fr('b', fi); cc = fr('c', fi)
print('shapes', a.shape, b.shape, cc.shape)
s = 1280 / a.shape[1]
row = np.hstack([cv2.resize(a, (1280, int(a.shape[0] * s))), np.zeros((int(a.shape[0] * s), 10, 3), np.uint8)])
cv2.imwrite(f'b2/e12_f{fi}_a_small.jpg', cv2.resize(a, (1014, 760)))
cv2.imwrite(f'b2/e12_f{fi}_bc.jpg', np.hstack([b, cc]))
