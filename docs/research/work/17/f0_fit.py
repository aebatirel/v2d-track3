import sys, json, numpy as np, cv2
import lib17 as L, camfit as F
ep = int(sys.argv[1]); fr = int(sys.argv[2]); camset = sys.argv[3] if len(sys.argv) > 3 else 'abc'
gt = L.load_gt(ep); R0, C0 = L.s25_cam(ep)
G = {c: F.gray(L.Video(ep, c).get(fr)) for c in 'abc'}
R, C, info = F.fit_frame(gt, fr, G, R0, C0, camset=camset)
for t, x, r in zip(info['tags'], info['uv'], info['res']): print('  ', t[0], gt['names'][t[1]][:8], t[2], np.round(x, 1), f'res {r:.2f} px({t[0]})')
sd = np.sqrt(np.diag(info['cov'])) if info['cov'] is not None else np.full(6, np.nan)
dang = np.degrees(np.linalg.norm(cv2.Rodrigues(R0.T @ R)[0]))
print(f'ep {ep} f{fr} [{camset}] n {len(info["X"])} med res {np.median(info["res"]):.2f}  sd rot deg {np.round(np.degrees(sd[:3]),3)} sd C mm {np.round(sd[3:]*1000,1)}; vs s25 rot {dang:.2f} deg dC mm {np.round((C-C0)*1000,1)}')
json.dump(dict(ep=ep, fr=fr, Rwc=R.tolist(), C=C.tolist(), camset=camset), open(f'out/f0cam_{ep}_{fr}_{camset}.json', 'w'))
