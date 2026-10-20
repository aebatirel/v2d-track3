"""Overlay (stage B resume): object markers projected with GT at SH0=-0.5 (green), with the body-frame correction X from
out/bodyx_<ep>_<obj>.json (cyan), plus a static reference object's markers (yellow), crops around the object, cams a and b.
usage: ov_bodyx.py ep obj ref t1 t2 ...  -> out/ovx_<ep>_<obj>.jpg"""
import sys, os, json, numpy as np, cv2, lib17 as L, det17lib as D
from scipy.spatial.transform import Rotation as Rot
ep, obj, ref = int(sys.argv[1]), sys.argv[2], sys.argv[3]; ts = [int(x) for x in sys.argv[4:]]
gt = L.load_gt(ep); RG = json.load(open(f'out/{os.environ.get("CAM", "reg2")}_{ep}.json')); X = np.array(json.load(open(f'out/bodyx_{ep}_{obj}{os.environ.get("CAM", "")}.json'))['X'])
j, jr = gt['names'].index(obj), gt['names'].index(ref); M = np.array([q['c'] for q in L.CAT[obj]]); Mr = np.array([q['c'] for q in L.CAT[ref]])
Mx = Rot.from_rotvec(X[:3]).apply(M) + X[3:] / 1000; tiles = []
for t in ts:
    row = []
    for c in 'ab':
        cams = RG['cams' if c == 'a' else f'cams_{c}']; R, C = np.array(cams[t]['Rwc']), np.array(cams[t]['C'])
        tau = t - 0.5 - (RG['delta'] if c == 'a' else 0); im = L.Video(ep, c).get(t).copy(); f = L.cam(c)[0][0, 0]
        def draw(MM, jj, col):
            Rj, tj = D.gt_interp(gt, jj, tau); uv, z = L.project(MM @ Rj.T + tj, R, C, c, own=True)
            for k in range(len(uv)): cv2.circle(im, (int(round(uv[k, 0])), int(round(uv[k, 1]))), max(int(round(f * 0.007 / z[k])), 2), col, 1)
            return uv
        uv = draw(M, j, (0, 255, 0)); draw(Mx, j, (255, 255, 0)); draw(Mr, jr, (0, 255, 255))
        s = 2 if c == 'b' else 1; cx, cy = uv.mean(0); hw = 110 // s
        x0, y0 = int(max(cx - hw, 0)), int(max(cy - hw, 0)); cr = im[y0:y0 + 2 * hw, x0:x0 + 2 * hw]
        cr = cv2.resize(cr, (220, 220), interpolation=cv2.INTER_NEAREST if s == 1 else cv2.INTER_LINEAR)
        cv2.putText(cr, f't{t} {c}', (4, 14), cv2.FONT_HERSHEY_PLAIN, 1.0, (255, 255, 255), 1); row.append(cr)
    tiles.append(np.hstack(row))
fn = f'out/ovx_{ep}_{obj}{os.environ.get("CAM", "")}.jpg'; cv2.imwrite(fn, np.vstack(tiles)); print(fn)
