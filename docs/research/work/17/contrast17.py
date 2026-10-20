"""Stage B: photometric stats at z-visible projected markers (GT at t + SH, cam a also - delta).
Per marker: disc mean (r < 0.6 R), ring mean (1.3-2.0 R), ring sd, radial edge strength at R (mean |dI/dr| over 16 probes,
sign-free), disc saturation (cam a, HSV S 0-255), and the same edge measure at R for a 'null' ring offset by 3 R (texture
baseline). usage: contrast17.py ep step -> out/contrast_<ep>.npz"""
import sys, os, json, time, numpy as np, cv2
import lib17 as L, det17lib as D, seg17
ep, step = int(sys.argv[1]), int(sys.argv[2]); SH = float(os.environ.get('SH', -0.5))
gt = L.load_gt(ep); RG = json.load(open(f'out/reg2_{ep}.json')); z = np.load(f'out/census_{ep}.npz'); seg = seg17.segments(gt)[0]
cams = {'a': RG['cams'], 'b': RG['cams_b'], 'c': RG['cams_c']}; T = len(cams['a']); N = len(gt['names'])
vids = {c: L.Video(ep, c) for c in 'abc'}; out = []; t0 = time.time()
ang = np.linspace(0, 2 * np.pi, 16, endpoint=False); cs, sn = np.cos(ang), np.sin(ang)
def ring_stats(Gf, gx, gy, u, v, R):
    H, W = Gf.shape
    yy, xx = np.mgrid[int(v - 2.2 * R):int(v + 2.2 * R) + 1, int(u - 2.2 * R):int(u + 2.2 * R) + 1]
    ok = (yy >= 0) & (yy < H) & (xx >= 0) & (xx < W); yy, xx = yy[ok], xx[ok]
    d = np.hypot(xx - u, yy - v) / R; g = Gf[yy, xx]
    din = g[d < 0.6].mean() if (d < 0.6).any() else np.nan
    rg = g[(d > 1.3) & (d < 2.0)]; rmean = rg.mean() if len(rg) else np.nan; rsd = rg.std() if len(rg) else np.nan
    px, py = u + R * cs, v + R * sn; m = (px >= 0) & (px < W - 1) & (py >= 0) & (py < H - 1)
    if not m.any(): return din, rmean, rsd, np.nan
    ix, iy = px[m].round().astype(int), py[m].round().astype(int)
    edge = np.abs(gx[iy, ix] * cs[m] + gy[iy, ix] * sn[m]).mean()
    return din, rmean, rsd, edge
for t in range(0, T, step):
    for ci, c in enumerate('abc'):
        if not z['VIS'][t, ci].any(): continue
        BGR = vids[c].get(t); G = cv2.cvtColor(BGR, cv2.COLOR_BGR2GRAY); Gf = cv2.GaussianBlur(G.astype(np.float32), (0, 0), 0.7)
        gx = cv2.Sobel(Gf, cv2.CV_32F, 1, 0, ksize=3) / 8; gy = cv2.Sobel(Gf, cv2.CV_32F, 0, 1, ksize=3) / 8
        hsv = cv2.cvtColor(BGR, cv2.COLOR_BGR2HSV) if c == 'a' else None
        R_, C_ = np.array(cams[c][t]['Rwc']), np.array(cams[c][t]['C']); tau = t + SH - (RG['delta'] if c == 'a' else 0)
        for j in range(N):
            if not z['VIS'][t, ci, j].any(): continue
            uv, zz, rp = D.project_markers(gt, j, tau, R_, C_, c)
            for k in range(len(uv)):
                if not z['VIS'][t, ci, j, k]: continue
                u, v = uv[k]; din, rm, rsd, edge = ring_stats(Gf, gx, gy, u, v, rp[k])
                _, _, _, edge0 = ring_stats(Gf, gx, gy, u + 3 * rp[k], v, rp[k])
                sat = np.nan
                if hsv is not None:
                    q = max(int(0.5 * rp[k]), 1); ui, vi = int(round(u)), int(round(v))
                    sat = hsv[max(vi - q, 0):vi + q + 1, max(ui - q, 0):ui + q + 1, 1].mean()
                out.append((t, ci, j, k, rp[k], seg[t, j], z['SPD'][t, ci, j, k], din, rm, rsd, edge, edge0, sat))
    if t % 30 == 0: print(f'ep {ep} t {t} n {len(out)} {time.time()-t0:.0f}s', flush=True)
np.savez(f'out/contrast_{ep}.npz', A=np.array(out, np.float32), names=np.array(gt['names']),
         cols=np.array(['t', 'cam', 'j', 'k', 'rpx', 'seg', 'spd', 'disc', 'ring', 'ringsd', 'edge', 'edge_null', 'sat']))
print('done', time.time() - t0)
