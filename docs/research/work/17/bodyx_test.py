"""Stage B resume: is an object's in-hand projection miss a time offset or a body-frame error? For z-visible marker views
(det sample), candidates = Hough rows with score >= THR. (1) wide time scan ds -10..+10 frames (absolute, b/c clock; cam a
also -delta). (2) constant body-frame correction X (6-DoF) fitted on MOVING views by robust reprojection to the nearest
candidate (gates 3r -> 1.5r -> 1r), GT at SH0 = -0.5; hit rates before/after on moving and rest views (rest = check).
usage: [THR=0.3] bodyx_test.py ep object"""
import sys, os, json, numpy as np, collections
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation as Rot
import lib17 as L, det17lib as D
ep, obj = int(sys.argv[1]), sys.argv[2]; THR = float(os.environ.get('THR', 0.3)); SH0 = -0.5
gt = L.load_gt(ep); RG = json.load(open(f'out/{os.environ.get("CAM", "reg2")}_{ep}.json')); d = np.load(f'out/det_{ep}.npz'); S = np.load(f'out/score_{ep}.npy')
cams = {'a': RG['cams'], 'b': RG['cams_b'], 'c': RG['cams_c']}; j = gt['names'].index(obj)
M = np.array([q['c'] for q in L.CAT[obj]]); rows = d['rows']; keep = S >= THR; R_ = rows[keep]
idx = collections.defaultdict(list)
for i in range(len(R_)): idx[(int(R_[i, 0]), int(R_[i, 1]))].append(i)
V = [m for m in d['MK'] if int(m[2]) == j]
def proj(m, ds, X=None):
    t, ci, k = int(m[0]), int(m[1]), int(m[3]); c = 'abc'[ci]
    tau = t + ds - (RG['delta'] if c == 'a' else 0); Rj, tj = D.gt_interp(gt, j, tau); p = M[k]
    if X is not None: p = Rot.from_rotvec(X[:3]).apply(p) + X[3:] / 1000
    uv, z = L.project((Rj @ p + tj)[None], np.array(cams[c][t]['Rwc']), np.array(cams[c][t]['C']), c, own=True); return uv[0]
def hit(m, uv, gate=None):
    Dd = R_[idx.get((int(m[0]), int(m[1])), [])]; r = m[4]
    if len(Dd) == 0: return False, None
    dd = np.hypot(Dd[:, 2] - uv[0], Dd[:, 3] - uv[1]); rr = Dd[:, 4] / r; ok = (rr > 0.6) & (rr < 1.6)
    if not ok.any(): return False, None
    i = np.argmin(np.where(ok, dd, np.inf)); rad = max(0.5 * r, 3.0 if m[1] == 0 else 2.0)
    return bool(dd[i] < rad), (Dd[i, 2:4] if dd[i] < (gate if gate else rad) * 1.0 else None)
mov = [m for m in V if int(m[5]) in (1, 2)]; rst = [m for m in V if int(m[5]) == 0]
print(f'ep {ep} {obj}: views moving {len(mov)} rest {len(rst)}; THR {THR}')
for nm, VV in (('moving', mov), ('rest', rst)):
    if not VV: continue
    print(f' time scan {nm}: ' + ' '.join(f'{ds:+.1f}:{np.mean([hit(m, proj(m, ds))[0] for m in VV]):.2f}' for ds in np.arange(-10, 10.1, 1.0)))
X = np.zeros(6)
for gm in (3.0, 1.5, 1.0):
    pairs = []
    for m in mov:
        uv = proj(m, SH0, X); _, cand = hit(m, uv, gate=gm * m[4])
        if cand is not None: pairs.append((m, cand))
    if len(pairs) < 6: print(' too few pairs', len(pairs)); break
    f = lambda x: np.concatenate([(proj(m, SH0, x) - cnd) / m[4] for m, cnd in pairs])
    X = least_squares(f, X, loss='soft_l1', f_scale=0.3).x
    print(f' gate {gm} r: pairs {len(pairs)}; X rot {np.degrees(np.linalg.norm(X[:3])):.2f} deg axis {np.round(X[:3]/max(np.linalg.norm(X[:3]),1e-9),2)} t {np.round(X[3:],1)} mm')
for nm, VV in (('moving', mov), ('rest', rst)):
    if VV: print(f' hit rate {nm}: before {np.mean([hit(m, proj(m, SH0))[0] for m in VV]):.2f} after {np.mean([hit(m, proj(m, SH0, X))[0] for m in VV]):.2f} (n {len(VV)})')
json.dump(dict(ep=ep, obj=obj, X=X.tolist()), open(f'out/bodyx_{ep}_{obj}{os.environ.get("CAM", "")}.json', 'w'))
