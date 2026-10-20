import sys, json, numpy as np, cv2, lib17 as L, det17lib as D
ep, t, c = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]; SHf = float(sys.argv[4]) if len(sys.argv) > 4 else -0.5
gt = L.load_gt(ep); RG = json.load(open(f'out/reg2_{ep}.json')); cams = RG['cams' if c == 'a' else f'cams_{c}']
R, C = np.array(cams[t]['Rwc']), np.array(cams[t]['C']); tau = t + SHf - (RG['delta'] if c == 'a' else 0)
im = L.Video(ep, c).get(t).copy(); z = np.load(f'out/census_{ep}.npz'); ci = 'abc'.index(c)
for j, n in enumerate(gt['names']):
    uv, zz, rp = D.project_markers(gt, j, tau, R, C, c)
    Xs = L.surf(n)[::20]; Rj, tj = D.gt_interp(gt, j, tau); ps, _ = L.project(Xs @ Rj.T + tj, R, C, c, own=True)
    for p in ps[::3]: cv2.circle(im, (int(p[0]), int(p[1])), 0, (255, 0, 255), -1)
    for k in range(len(uv)):
        col = (0, 255, 0) if z['VIS'][t, ci, j, k] else (0, 0, 255)
        cv2.circle(im, (int(round(uv[k, 0])), int(round(uv[k, 1]))), int(round(rp[k])), col, 1); cv2.putText(im, f'{n[:4]}{k}', (int(uv[k, 0]) + 8, int(uv[k, 1])), cv2.FONT_HERSHEY_PLAIN, 0.8, col, 1)
uvs = np.vstack([D.project_markers(gt, j, tau, R, C, c)[0] for j in range(len(gt['names'])) if 'sweep' in gt['names'][j] or ep != 31])
x0, y0 = np.clip(uvs.min(0) - 150, 0, None).astype(int); x1, y1 = (uvs.max(0) + 150).astype(int)
cv2.imwrite(f'out/ov_{ep}_{t}_{c}.jpg', im[y0:y1, x0:x1]); print(f'out/ov_{ep}_{t}_{c}.jpg')
