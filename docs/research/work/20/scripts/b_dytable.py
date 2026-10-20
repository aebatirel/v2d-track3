# Direct 2-D NCC measurement of the vertical misalignment on table patches (no warp), vs the global median and the field.
import sys, json, cv2, numpy as np
sys.path.insert(0, '.'); from b_lib import *
tag, k = sys.argv[1], int(sys.argv[2]); ep = int(tag[1:]); spl = 'public' if tag[0] == 'p' else 'evaluation'
gb = cv2.cvtColor(read_frames(spl, ep, 'b', [k])[k], cv2.COLOR_BGR2GRAY); gc = cv2.cvtColor(read_frames(spl, ep, 'c', [k])[k], cv2.COLOR_BGR2GRAY)
rc, rb = rect(gc, 'c').astype(np.float32), rect(gb, 'b').astype(np.float32)
f, info = dy_field(rc.astype(np.uint8), rb.astype(np.uint8))
rec = [r for r in json.load(open(f'{OUT}/meas_{tag}.json')) if r['k'] == k][0]
c, n = np.array(rec['plane_g_c']), np.array(rec['plane_g_n'])
res = []
for y in range(420, 960, 30):
    for x in range(300, 1400, 30):
        d = np.array([(x - CXR) / FR, (y - CYR) / FR, 1.0]); t = (c @ n) / (d @ n)
        if t <= 0 or t > 1.2: continue
        disp = FR * BASE / t
        P = cv2.getRectSubPix(rc, (41, 41), (float(x), float(y)))
        if P.std() < 4: continue
        best = None
        for ddy in np.arange(-2.0, 5.01, 0.25):
            for ddx in np.arange(-4, 4.01, 0.5):
                Q = cv2.getRectSubPix(rb, (41, 41), (float(x - disp + ddx), float(y + ddy)))
                a, b = P - P.mean(), Q - Q.mean(); s = (a * b).sum() / np.sqrt((a * a).sum() * (b * b).sum() + 1e-9)
                if best is None or s > best[0]: best = (s, ddx, ddy)
        if best[0] < 0.85: continue
        # sharpness in dy: NCC drop at +-1 px in dy at the best dx
        Qs = [cv2.getRectSubPix(rb, (41, 41), (float(x - disp + best[1]), float(y + best[2] + o))) for o in (-1, 1)]
        drop = np.mean([best[0] - ((P - P.mean()) * (q - q.mean())).sum() / np.sqrt(((P - P.mean()) ** 2).sum() * ((q - q.mean()) ** 2).sum()) for q in Qs])
        res.append((x, y, best[2], best[0], drop, float(f(x, y))))
R = np.array(res); good = R[:, 4] > 0.02
print(tag, k, 'patches', len(R), 'dy-sharp', good.sum(), '| global median', round(rec.get('dy_global', rec['dy']), 2))
for y0 in range(420, 960, 90):
    m = good & (R[:, 1] >= y0) & (R[:, 1] < y0 + 90)
    if m.sum(): print(f'  rows {y0}-{y0+90}: measured dy median {np.median(R[m,2]):.2f} (n {m.sum()}, IQR {np.percentile(R[m,2],25):.2f}..{np.percentile(R[m,2],75):.2f}) | field {np.median(R[m,5]):.2f}')
