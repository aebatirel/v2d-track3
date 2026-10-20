"""Crop sheet of z-visible markers that the LOEO detector MISSED (or hit) at THR, for visual cause labelling.
usage: missed17.py ep cam(a|b|c) seg(rest|held|carried|moving) n seed [hit=0|1]  -> out/missed_<ep>_<cam>_<seg>_<hit>.jpg
Red circle: projected marker (GT at SH); green: kept detections (score >= THR) near it. Tiles numbered."""
import sys, os, json, numpy as np, cv2
import lib17 as L, det17lib as D
ep, c, sg, n, seed = int(sys.argv[1]), sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5]); hitw = len(sys.argv) > 6 and sys.argv[6] == '1'
THR = float(os.environ.get('THR', 0.5)); ci = 'abc'.index(c); TS = 128
d = np.load(f'out/det_{ep}.npz'); rows = d['rows']; S = np.load(f'out/score_{ep}.npy'); MK = d['MK']; SHIFTS = d['SHIFTS']; i0 = int(np.argmin(np.abs(SHIFTS - float(d['SH'])))); ns = len(SHIFTS)
R = np.c_[rows, S]; names = list(np.load(f'out/census_{ep}.npz')['names'])
segs = {'rest': [0], 'held': [1], 'carried': [2], 'moving': [1, 2]}[sg]
cand = []
for m in MK:
    if int(m[1]) != ci or int(m[5]) not in segs: continue
    t = int(m[0]); Dt = R[(R[:, 0] == t) & (R[:, 1] == ci) & (R[:, 10] >= THR)]; K = D.nms(Dt, 10) if len(Dt) else Dt
    hit = D.match(K, m[7 + i0], m[7 + ns + i0], m[4], ci)
    if hit == hitw: cand.append((m, K))
rng = np.random.default_rng(seed); sel = [cand[i] for i in sorted(rng.choice(len(cand), min(n, len(cand)), replace=False))]
vid = L.Video(ep, c); tiles = []
for q, (m, K) in enumerate(sel):
    t, j, k, r = int(m[0]), int(m[2]), int(m[3]), m[4]; u, v = m[7 + i0], m[7 + ns + i0]
    im = vid.get(t).copy(); h = max(int(4 * r), 12)
    for kk in K:
        if abs(kk[2] - u) < 2 * h and abs(kk[3] - v) < 2 * h: cv2.circle(im, (int(round(kk[2])), int(round(kk[3]))), int(round(kk[4])), (0, 255, 0), 1)
    pad = cv2.copyMakeBorder(im, h, h, h, h, cv2.BORDER_CONSTANT); cr = pad[int(v):int(v) + 2 * h, int(u):int(u) + 2 * h]
    s = TS / (2 * h); cr = cv2.resize(cr, (TS, TS), interpolation=cv2.INTER_NEAREST if s > 2 else cv2.INTER_LINEAR)
    cv2.circle(cr, (TS // 2, TS // 2), max(int(r * s), 1), (0, 0, 255), 1)
    cv2.putText(cr, f'#{q} t{t} {names[j][:6]}{k}', (1, 10), cv2.FONT_HERSHEY_PLAIN, 0.75, (0, 255, 255), 1)
    cv2.putText(cr, f'r{r:.0f} v{m[6]:.0f}', (1, TS - 3), cv2.FONT_HERSHEY_PLAIN, 0.75, (0, 255, 255), 1)
    tiles.append(cr)
while len(tiles) % 8: tiles.append(np.zeros((TS, TS, 3), np.uint8))
sheet = np.vstack([np.hstack(tiles[i:i + 8]) for i in range(0, len(tiles), 8)])
out = f'out/missed_{ep}_{c}_{sg}_{int(hitw)}.jpg'; cv2.imwrite(out, sheet); print(out, len(cand), 'candidates')
