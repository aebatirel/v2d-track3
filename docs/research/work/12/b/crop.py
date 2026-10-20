"""crop.py split ep cam frame x0 y0 x1 y1 out [zoom] : extract one exact frame (no rotation) and crop at full res.
Adds a 10 px tick ruler on the top/left edge (every 10 px short tick, every 50 px long tick)."""
import sys, subprocess, numpy as np, cv2, os
split, ep, cam, fr = sys.argv[1], int(sys.argv[2]), sys.argv[3], int(sys.argv[4])
x0, y0, x1, y1 = map(int, sys.argv[5:9]); out = sys.argv[9]; zoom = float(sys.argv[10]) if len(sys.argv) > 10 else 1.0
mp4 = f'/Users/aebatirel/Documents/Code/v2d-research/data/track_3/{split}/videos/chunk-000/observation.images.ego_cam_{cam}/episode_{ep:06d}.mp4'
cache = f'/Users/aebatirel/Documents/Code/v2d-research/work/12/b/fr/{split[0]}{ep}_{cam}_{fr:04d}.png'
os.makedirs(os.path.dirname(cache), exist_ok=True)
if not os.path.exists(cache):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', mp4, '-vf', f'select=eq(n\\,{fr})', '-vsync', '0', '-frames:v', '1', cache], check=True, timeout=120)
im = cv2.imread(cache); c = im[y0:y1, x0:x1].copy()
if zoom != 1: c = cv2.resize(c, None, fx=zoom, fy=zoom, interpolation=cv2.INTER_NEAREST)
for k in range(0, x1 - x0, 10):
    L = 12 if k % 50 == 0 else 5; c[:L, int(k * zoom)] = (0, 0, 255)
for k in range(0, y1 - y0, 10):
    L = 12 if k % 50 == 0 else 5; c[int(k * zoom), :L] = (0, 0, 255)
cv2.imwrite(out, c); print(out, c.shape, 'full frame', im.shape)
