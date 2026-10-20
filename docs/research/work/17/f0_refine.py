"""A2: refine frame-0 cam_a pose of a public episode by PnP on GT-placed marker spheres (all objects static at f0).
Start: note 11 s25 silhouette camera. Check: cam b and cam c residuals with the calibrated extrinsics (independent)."""
import sys, json, numpy as np, cv2
import lib17 as L, det17 as D
ep = int(sys.argv[1]); fr = int(sys.argv[2]) if len(sys.argv) > 2 else 0
gt = L.load_gt(ep); R, C = L.s25_cam(ep)
ims = {c: L.Video(ep, c).get(fr) for c in 'abc'}; G = {c: D.gray(ims[c]) for c in 'abc'}
for it, win in enumerate([90, 40, 15, 10]):
    X, uv, cams, tags = [], [], [], []
    vis = L.visibility(gt, fr, R, C, 'a')
    for j, n in enumerate(gt['names']):
        Mw = L.markers_world(gt, fr, j)
        for k in range(len(Mw)):
            if not vis[j]['vis'][k]: continue
            d = D.detect_one(G['a'], vis[j]['uv'][k], vis[j]['rpx'][k], win)
            if d is None or d['contrast'] < 0.03: continue
            X.append(Mw[k]); uv.append([d['u'], d['v']]); cams.append('a'); tags.append((n, k, round(d['contrast'], 2)))
    if len(X) < 3: print('too few', len(X)); break
    R, C, sol, cov = D.refine(R, C, X, uv, cams)
    p, _ = L.project(np.array(X), R, C, 'a'); e = np.linalg.norm(p - np.array(uv), axis=1)
    print(f'iter {it} win {win}: n {len(X)} resid px med {np.median(e):.2f} max {e.max():.2f}', [(t[0][:6], t[1], round(float(ee), 1)) for t, ee in zip(tags, e)])
sd = np.sqrt(np.diag(cov)) if cov is not None else None
print('cam C', np.round(C, 4), 'sd rot deg', np.round(np.degrees(sd[:3]), 3) if sd is not None else None, 'sd C mm', np.round(sd[3:] * 1000, 1) if sd is not None else None)
psi = np.degrees(np.arctan2(R[1, 2], R[0, 2])); th = -np.degrees(np.arcsin(R[2, 2]))
R0, C0 = L.s25_cam(ep); dang = np.degrees(np.linalg.norm(cv2.Rodrigues(R0.T @ R)[0]))
print(f'heading psi {psi:.2f} pitch {th:.2f}; vs s25: rot diff {dang:.2f} deg, C diff mm {np.round((C - C0) * 1000, 1)}')
# independent check in cam b and c
for c in 'bc':
    vis = L.visibility(gt, fr, R, C, c); E = []
    for j, n in enumerate(gt['names']):
        Mw = L.markers_world(gt, fr, j)
        for k in range(len(Mw)):
            if not vis[j]['vis'][k]: continue
            d = D.detect_one(G[c], vis[j]['uv'][k], vis[j]['rpx'][k], 12)
            if d is None or d['contrast'] < 0.03: continue
            E.append((n[:6], k, d['u'] - vis[j]['uv'][k][0], d['v'] - vis[j]['uv'][k][1], d['contrast']))
    e = np.array([np.hypot(a[2], a[3]) for a in E])
    print(f'cam {c}: n {len(E)} resid px med {np.median(e) if len(e) else np.nan:.2f}', [(a[0], a[1], round(a[2], 1), round(a[3], 1), round(a[4], 2)) for a in E])
json.dump(dict(ep=ep, fr=fr, Rwc=R.tolist(), C=C.tolist()), open(f'out/f0cam_{ep}_{fr}.json', 'w'))
# overlay crops
crops = []
vis = L.visibility(gt, fr, R, C, 'a')
for j, n in enumerate(gt['names']):
    for k, (u, v) in enumerate(vis[j]['uv']):
        if not (60 <= u < 2028 - 60 and 60 <= v < 1520 - 60): continue
        cr = ims['a'][int(v) - 60:int(v) + 60, int(u) - 60:int(u) + 60].copy()
        cv2.circle(cr, (60, 60), int(vis[j]['rpx'][k]), (0, 255, 0) if vis[j]['vis'][k] else (0, 0, 255), 1)
        cv2.putText(cr, f'{n[:5]}{k}', (2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1); crops.append(cr)
if crops: cv2.imwrite(f'out/f0crops_{ep}_{fr}.jpg', np.concatenate(crops, 1))
