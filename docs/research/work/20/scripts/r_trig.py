"""DIG 20 Stage C re-run: what triggered C (contact) and the window end on GT-free masks; frame-0 mask overlay plus ROI
crops with the change mask at C_a, M_a and c_a. Analysis/visual check only.
usage: r_trig.py <public|evaluation> <ep> ... -> out/c2/trig_<key>.jpg; r_trig.py sheet <public|evaluation> <eps...>"""
import sys, os, json, numpy as np, cv2
sys.path.insert(0, os.path.dirname(__file__))
import c_lib as L
from c_detect import features
OUT2 = f'{L.ROOT}/work/20/out/c2'

if sys.argv[1] == 'sheet':
    split = sys.argv[2]; rows = []
    for ep in map(int, sys.argv[3:]):
        key = f'{"p" if split == "public" else "e"}{ep}'; f = f'{OUT2}/trig_{key}.jpg'
        if os.path.exists(f):
            im = cv2.imread(f); rows.append(cv2.resize(im, (int(im.shape[1] * 200 / im.shape[0]), 200)))
    W = max(r.shape[1] for r in rows)
    cv2.imwrite(f'{OUT2}/trig_sheet_{split}.jpg', np.vstack([np.pad(r, ((0, 0), (0, W - r.shape[1]), (0, 0))) for r in rows]))
    sys.exit()
split = sys.argv[1]
for ep in map(int, sys.argv[2:]):
    key = f'{"p" if split == "public" else "e"}{ep}'
    d = json.loads(str(np.load(f'{OUT2}/run_{key}.npz')['dec']))
    M0 = (cv2.imread(f'{OUT2}/mask0_{key}.png', cv2.IMREAD_GRAYSCALE) > 127).astype(np.uint8) * 255
    ks = sorted(set(k for k in (d['C_a'], d['M_a'], d['c_a']) if k is not None and 0 < k < 160))
    F = L.frames(split, ep, 'a', n_max=(max(ks) + 1) if ks else 2)
    o0 = F[0].copy(); cnt, _ = cv2.findContours(M0, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE); cv2.drawContours(o0, cnt, -1, (0, 255, 0), 2)
    o0 = cv2.resize(o0, (320, 240)); cv2.putText(o0, f'{key} a0 mask', (3, 15), 0, 0.5, (255, 255, 0), 1)
    tiles = [o0]
    if ks:
        _, box, vis = features(F, M0, keep_vis=set(ks))
        for k in ks:
            im, ch, Mk = vis[k]; o = im.copy(); o[ch > 0] = (0.5 * o[ch > 0] + [0, 0, 128]).astype(np.uint8)
            cnt, _ = cv2.findContours(Mk.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE); cv2.drawContours(o, cnt, -1, (0, 255, 0), 1)
            o = cv2.resize(o, (int(240 * o.shape[1] / o.shape[0]), 240))
            lab = ('C' if k == d['C_a'] else '') + ('M' if k == d['M_a'] else '') + ('end' if k == d['c_a'] else '')
            cv2.putText(o, f'{key} a{k} {lab}', (3, 15), 0, 0.5, (255, 255, 0), 1); tiles.append(o)
    cv2.imwrite(f'{OUT2}/trig_{key}.jpg', np.hstack(tiles))
    print(key, d, flush=True)
