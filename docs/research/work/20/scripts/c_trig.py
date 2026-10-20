"""What triggered the contact signal C (A=120) and the motion signal M: ROI crops with the change mask at C_a and M_a.
usage: c_trig.py <ep> ... -> out/c/trig_p<ep>.jpg (analysis only)"""
import sys, os, numpy as np, cv2
sys.path.insert(0, os.path.dirname(__file__))
from c_lib import *
from c_detect import features
import c_eval2 as E
for ep in map(int, sys.argv[1:]):
    g = gt_ref(ep); R, C = cam0(ep); M0, z = silhouette(g['name'], g['e']['pose'][0, g['j']], R, C)
    c = E.contact_a(ep, 120); m = E.motion_a(ep, 2.0, kappa=0.15)
    ks = sorted(set(k for k in (c, min(m, c + 10)) if k < 160))
    F = frames('public', ep, 'a', n_max=max(ks) + 1)
    rows, box, vis = features(F, M0, keep_vis=set(ks))
    tiles = []
    for k in ks:
        im, ch, Mk = vis[k]; o = im.copy(); o[ch > 0] = (0.5 * o[ch > 0] + [0, 0, 128]).astype(np.uint8)
        cnt, _ = cv2.findContours(Mk.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE); cv2.drawContours(o, cnt, -1, (0, 255, 0), 1)
        o = cv2.resize(o, (320, int(320 * o.shape[0] / o.shape[1])))
        cv2.putText(o, f'p{ep} a{k} {"C" if k == c else ""}{"end" if k == min(m, c + 10) else ""}', (3, 15), 0, 0.5, (255, 255, 0), 1); tiles.append(o)
    h = max(t.shape[0] for t in tiles)
    cv2.imwrite(f'{OUT}/trig_p{ep}.jpg', np.hstack([np.pad(t, ((0, h - t.shape[0]), (0, 0), (0, 0))) for t in tiles]))
    print(ep, c, m, flush=True)
