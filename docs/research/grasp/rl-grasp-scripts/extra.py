"""Per-frame: which hand links pass through the ring hole, which side of the plate each nearby link is on (world above /
below), and how far nearby links reach below the table top (the hands do not collide with the table).
Usage: extra.py SRC OUT.jsonl --objs name=hulls=glb=holemap.npz ... [--ref] [--every N]
A link is 'near' if any of its collision samples is within 2 cm of the object's collision pieces (lower-bound SDF).
in_hole: >= 3 samples whose (axis1, axis2) fall in a free hole cell and whose axis3 lies between the band's bottom - 3 mm
and top + 3 mm. side: sign of the median axis3 offset of the link's samples from the plate mid-plane, translated to
world 'above' / 'below' with the plate normal's world z (|z| < 0.5 -> 'side-on')."""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from scipy.spatial.transform import Rotation as R
from rlgrasp_lib import TABLE_Z, ObjGeom, hand_points, load_trace, load_ref, link_world, to_obj

p = argparse.ArgumentParser(); p.add_argument('src'); p.add_argument('out'); p.add_argument('--objs', nargs='+', required=True)
p.add_argument('--ref', action='store_true'); p.add_argument('--every', type=int, default=1)
a = p.parse_args()
src = load_ref(a.src) if a.ref else load_trace(a.src)
O = {}
for s in a.objs:
    n, h, g, hm = s.split('='); G = ObjGeom(h, g); H = np.load(hm)
    mid = np.where(np.isnan(H['top']), np.nan, 0.5 * (H['top'] + H['bot']))
    from scipy import ndimage
    ring = ndimage.binary_dilation(H['hole'], iterations=4) & H['solid']
    O[n] = dict(G=G, H=H, mid=mid, midg=float(np.nanmedian(mid)), bt=float(np.nanmedian(H['top'][ring])), bb=float(np.nanmedian(H['bot'][ring])))
hp = {s: hand_points(s, n=120) for s in ('left', 'right')}
fh = open(a.out, 'w')
for f in range(0, src['T'], a.every):
    rec = dict(f=f, obj={})
    for n, d in O.items():
        G, H = d['G'], d['H']; op = src['obj'][n][f]; nz = float(R.from_quat(op[3:7]).apply(G.W[2])[2]); res = {}
        g = H['a1'][1] - H['a1'][0]
        for s in ('left', 'right'):
            for ln, P in hp[s].items():
                if ln not in src['links']:
                    continue
                Xw = link_world(src['links'][ln][f], P); X = to_obj(op, Xw)
                if np.linalg.norm(X.mean(0) - G.ctr) > G.radius + 0.06:
                    continue
                if G.lb(X)[0].min() > 0.02:
                    continue
                PX = G.pca(X); i1 = np.round((PX[:, 0] - H['a1'][0]) / g).astype(int); i2 = np.round((PX[:, 1] - H['a2'][0]) / g).astype(int)
                ok = (i1 >= 0) & (i1 < len(H['a1'])) & (i2 >= 0) & (i2 < len(H['a2']))
                inh = np.zeros(len(PX), bool); md = np.full(len(PX), d['midg'])
                if ok.any():
                    hh = H['hole'][i1[ok], i2[ok]]
                    m_ = d['mid'][i1[ok], i2[ok]]; md[ok] = np.where(np.isnan(m_), d['midg'], m_)
                    inh[ok] = hh & (PX[ok, 2] > d['bb'] - 0.003) & (PX[ok, 2] < d['bt'] + 0.003)
                off = float(np.median(PX[:, 2] - md)); w = off * nz
                side = 'side-on' if abs(nz) < 0.5 else ('above' if w > 0 else 'below')
                res[f'{s[0].upper()}:{ln.split("_", 1)[1]}'] = dict(in_hole=int(inh.sum()), side=side, off_cm=round(100 * off, 1),
                                                                   zmin_mm=round(1000 * (Xw[:, 2].min() - TABLE_Z), 1))
        rec['obj'][n] = dict(nz=round(nz, 3), links=res)
    fh.write(json.dumps(rec) + '\n')
fh.close(); print('wrote', a.out)
