"""Stage B gap 2: band-pass detail energy of the inverted blue-cup base vs plain cup wall, cam a vs cam b vs cam c,
public ep 12 frame 180. Ellipses located by eye on this public frame (analysis only)."""
import cv2, numpy as np, sys, json
sys.argv = ['x']; exec(open('b2/camb12.py').read().split('fi =')[0])
im = {'a': cv2.imread('b/fr/p12_a_0180.png'), 'b': fr('b', 180), 'c': fr('c', 180)}
# (base centre, semi-axes), plain-wall box (x0,y0,x1,y1) just below the base; px per mm from base width / 70 mm [E]
G = {'a': ((1470, 903), (76, 50), (1430, 1000, 1510, 1040)), 'b': ((822, 480), (37, 26), (805, 520, 840, 535)),
     'c': ((893, 477), (36, 24), (876, 517, 911, 532))}
out = {}
for k, ((cx, cy), (ax, ay), (x0, y0, x1, y1)) in G.items():
    g = cv2.cvtColor(im[k], cv2.COLOR_BGR2GRAY).astype(np.float32)
    ppm = 2 * ax / 70.0
    s1, s2 = 0.7 * ppm, 3.0 * ppm
    dog = cv2.GaussianBlur(g, (0, 0), s1) - cv2.GaussianBlur(g, (0, 0), s2)
    yy, xx = np.mgrid[:g.shape[0], :g.shape[1]]
    m = ((xx - cx) / (0.7 * ax)) ** 2 + ((yy - cy) / (0.7 * ay)) ** 2 < 1
    base = dog[m].std(); wall = dog[y0:y1, x0:x1].std()
    out[k] = dict(px_per_mm=round(ppm, 2), base_width_px=2 * ax, base_rms=round(float(base), 2), wall_rms=round(float(wall), 2),
                  ratio=round(float(base / wall), 2), mean_grey=round(float(g[m].mean()), 1))
    print(k, out[k])
    v = cv2.normalize(dog[cy - ay - 5:cy + ay + 5, cx - ax - 5:cx + ax + 5], None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    cv2.imwrite(f'b2/e12_f180_base_dog_{k}.png', cv2.resize(v, (320, int(320 * v.shape[0] / v.shape[1])), interpolation=cv2.INTER_CUBIC))
json.dump(out, open('b2/base_snr.json', 'w'), indent=1)
