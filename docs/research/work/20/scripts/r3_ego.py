"""DIG 20 Stage C round 3: AUTOMATIC ego / non-ego label of every contact trigger (replaces the visual check of R6).
For each clip: C_a from the stored frozen-detector run (out/c3/run_<key>.npz when a round-3 mask exists, else
out/c2/run_<key>.npz); the contact features are recomputed on frames 0..C_a+1 only (same code, c_detect.features with
keep_vis) to get the ROI change map at C_a and C_a+1. Intruders = changed components that touch the dilated object mask
and reach >= 30 px outside it (the detector's own definition). For each intruder:
  - entry = where it crosses the ROI border (mean of its border pixels); none -> 'local' (shadow, reflection, small
    object, or an arm whose only change is near the object);
  - direction = entry - object centroid; ego if the entry is on the ROI's bottom side, or the direction is within
    EGO_DEG of image-down (the head camera sees the wearer's arms enter from the bottom); else 'other' (from the
    left/top/right: a second person, or an object/arm crossing the scene sideways).
A trigger's label = the label of its largest intruder at C_a (C_a+1 as tie-break). Inference-safe (video + mask only).
usage: r3_ego.py <keys...> -> out/c3/ego.json, out/c3/ego_<key>.jpg, out/c3/ego_sheet.jpg"""
import sys, os, json, numpy as np, cv2
sys.path.insert(0, os.path.dirname(__file__))
import c_lib as L
from c_detect import features, P as DP
O2 = f'{L.ROOT}/work/20/out/c2'; O3 = f'{L.ROOT}/work/20/out/c3'
EGO_DEG = float(os.environ.get('EGO_DEG', '60')); BAND = int(os.environ.get('BAND', '10'))


def src(key):
    for o in (O3, O2):
        if os.path.exists(f'{o}/run_{key}.npz') and os.path.exists(f'{o}/mask0_{key}.png'): return o
    return None


def label_frame(ch, Mk):
    """touching intruders (detector definition) -> extended by a 21-px closing of the change map (arms are fragmented)
    -> far end = extended-intruder pixel farthest from the object centroid; angle of the far end (0 = image-down);
    reach = the extended intruder enters the outer BAND px of the ROI. ego if |angle| <= EGO_DEG."""
    se = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * DP['r_touch'] + 1,) * 2)
    Md = cv2.dilate(Mk.astype(np.uint8), se) > 0
    Hc, Wc = ch.shape
    ys, xs = np.nonzero(Mk); cy, cx = (ys.mean(), xs.mean()) if len(ys) else (Hc / 2, Wc / 2)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(ch, connectivity=8)
    chc = cv2.morphologyEx(ch, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (21, 21)))
    nc, labc = cv2.connectedComponents(chc, connectivity=8)
    b = BAND; bp = np.zeros((Hc, Wc), bool); bp[:b, :] = True; bp[-b:, :] = True; bp[:, :b] = True; bp[:, -b:] = True
    touch_j = {}
    for i in range(1, n):
        if stats[i, cv2.CC_STAT_AREA] < 40: continue
        comp = lab == i
        if (comp & ~Md).sum() < 30 or not (comp & Md).any(): continue
        j = int(np.bincount(labc[comp]).argmax())
        touch_j[j] = touch_j.get(j, 0) + int((comp & Md).sum())      # touch summed over the fragments of one arm
    out = []
    for j, tch in touch_j.items():
        ext = (labc == j) & ~Md
        ey, ex = np.nonzero(ext)
        if len(ey) == 0: continue
        r = np.hypot(ey - cy, ex - cx); k = np.argsort(r)[-max(1, len(r) // 20):]      # far 5 %
        dy, dx = ey[k].mean() - cy, ex[k].mean() - cx
        ang = float(np.degrees(np.arctan2(dx, dy)))          # 0 = straight down, +-90 = right/left, 180 = up
        reach = bool((ext & bp).any())
        sides = dict(bottom=int(ext[-b:, :].sum()), top=int(ext[:b, :].sum()), left=int(ext[:, :b].sum()), right=int(ext[:, -b:].sum()))
        out.append(dict(area=int(ext.sum()), touch=tch, label='ego' if abs(ang) <= EGO_DEG else 'other',
                        angle=ang, reach=reach, far_r=float(r[k].mean()), sides=sides))
    out.sort(key=lambda d: -d['touch'])
    return out


if __name__ == '__main__':
    res = {}; tiles = []
    for key in sys.argv[1:]:
        o = src(key)
        if o is None: print(key, 'no run'); continue
        split = 'public' if key[0] == 'p' else 'evaluation'; ep = int(key[1:])
        d = json.loads(str(np.load(f'{o}/run_{key}.npz')['dec']))
        C = d['C_a']
        if C is None: res[key] = dict(C_a=None, label='no trigger'); print(key, 'no C'); continue
        M0 = (cv2.imread(f'{o}/mask0_{key}.png', cv2.IMREAD_GRAYSCALE) > 127).astype(np.uint8) * 255
        F = L.frames(split, ep, 'a', n_max=C + 2)
        fr, box, vis = features(F, M0, keep_vis={C, C + 1})
        labs = {k: label_frame(vis[k][1], vis[k][2]) for k in sorted(vis)}
        top = labs.get(C) or labs.get(C + 1) or []
        lab0 = top[0]['label'] if top else 'none'
        res[key] = dict(C_a=C, src=os.path.basename(o), label=lab0, intruders={str(k): v for k, v in labs.items()})
        im, ch, Mk = vis[C]; t = im.copy(); t[ch > 0] = (0.5 * t[ch > 0] + [0, 0, 128]).astype(np.uint8)
        cnt, _ = cv2.findContours(Mk.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE); cv2.drawContours(t, cnt, -1, (0, 255, 0), 1)
        t = cv2.resize(t, (300, int(300 * t.shape[0] / t.shape[1])))
        t = cv2.copyMakeBorder(t[:260], 0, max(0, 260 - t[:260].shape[0]), 0, 0, cv2.BORDER_CONSTANT)
        cv2.putText(t, f'{key} a{C} {lab0}', (4, 18), 0, 0.55, (0, 255, 255), 2)
        cv2.imwrite(f'{O3}/ego_{key}.jpg', t); tiles.append(t)
        print(key, f'C a{C}', lab0, [(x['label'], x['touch'], round(x['angle']), 'reach' if x['reach'] else 'local', round(x['far_r'])) for x in top[:3]], flush=True)
    json.dump(res, open(f'{O3}/ego.json', 'w'), indent=1)
    if tiles:
        while len(tiles) % 8: tiles.append(np.zeros_like(tiles[0]))
        cv2.imwrite(f'{O3}/ego_sheet.jpg', np.vstack([np.hstack(tiles[i:i + 8]) for i in range(0, len(tiles), 8)]))
