"""Stage B resume: fit the constant body-frame correction X (as bodyx_test.py) separately per frame block, and report
hit rates per block with X = 0, X(moving, all) and X(block). Camera control: the same hit rates for a static object.
usage: bodyx_blocks.py ep object static_object "a-b,c-d,..." """
import sys, os, json, numpy as np, collections
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation as Rot
import lib17 as L, det17lib as D
ep, obj, sobj = int(sys.argv[1]), sys.argv[2], sys.argv[3]; blocks = [tuple(map(int, b.split('-'))) for b in sys.argv[4].split(',')]
THR = 0.3; SH0 = -0.5; WORLD = os.environ.get('XMODE') == 'world'  # XMODE=world: X in world axes instead of body axes
gt = L.load_gt(ep); RG = json.load(open(f'out/{os.environ.get("CAM", "reg2")}_{ep}.json')); d = np.load(f'out/det_{ep}.npz'); S = np.load(f'out/score_{ep}.npy')
cams = {'a': RG['cams'], 'b': RG['cams_b'], 'c': RG['cams_c']}; rows = d['rows']; R_ = rows[S >= THR]
idx = collections.defaultdict(list)
for i in range(len(R_)): idx[(int(R_[i, 0]), int(R_[i, 1]))].append(i)
def mk(name):
    j = gt['names'].index(name); return j, np.array([q['c'] for q in L.CAT[name]]), [m for m in d['MK'] if int(m[2]) == j]
def proj(j, M, m, X=None):
    t, ci, k = int(m[0]), int(m[1]), int(m[3]); c = 'abc'[ci]; Rj, tj = D.gt_interp(gt, j, t + SH0 - (RG['delta'] if c == 'a' else 0)); p = M[k]
    if X is not None and WORLD: pw = Rot.from_rotvec(X[:3]).apply(Rj @ p) + tj + X[3:] / 1000  # world-axes correction about the object origin
    else:
        if X is not None: p = Rot.from_rotvec(X[:3]).apply(p) + X[3:] / 1000
        pw = Rj @ p + tj
    return L.project(pw[None], np.array(cams[c][t]['Rwc']), np.array(cams[c][t]['C']), c, own=True)[0][0]
def near(m, uv, gate):
    Dd = R_[idx.get((int(m[0]), int(m[1])), [])]; r = m[4]
    if len(Dd) == 0: return False, None
    dd = np.hypot(Dd[:, 2] - uv[0], Dd[:, 3] - uv[1]); rr = Dd[:, 4] / r; dd = np.where((rr > 0.6) & (rr < 1.6), dd, np.inf); i = np.argmin(dd)
    rad = max(0.5 * r, 3.0 if m[1] == 0 else 2.0); return bool(dd[i] < rad), (Dd[i, 2:4] if dd[i] < gate else None)
def fitX(j, M, VV):
    X = np.zeros(6)
    for gm in (3.0, 1.5, 1.0):
        P = [(m, c) for m in VV for _, c in [near(m, proj(j, M, m, X), gm * m[4])] if c is not None]
        if len(P) < 6: return X, len(P)
        X = least_squares(lambda x: np.concatenate([(proj(j, M, m, x) - c) / m[4] for m, c in P]), X, loss='soft_l1', f_scale=0.3).x
    return X, len(P)
j, M, V = mk(obj); js, Ms, Vs = mk(sobj)
mov = V if os.environ.get('ALLX') == '1' else [m for m in V if int(m[5]) > 0]; Xall, _ = fitX(j, M, mov)  # ALLX=1: fit X on all views
fmt = lambda X: f'{np.degrees(np.linalg.norm(X[:3])):.1f} deg ax {np.round(X[:3] / max(np.linalg.norm(X[:3]), 1e-9), 2)} t {np.round(X[3:], 1)} mm'
print(f'ep {ep} {obj}: X(moving, all) = {fmt(Xall)}')
for a, b in blocks:
    VV = [m for m in V if a <= m[0] <= b]; SS = [m for m in Vs if a <= m[0] <= b]
    if not VV: continue
    Xb, npair = fitX(j, M, VV); segs = collections.Counter(int(m[5]) for m in VV)
    h = lambda X: np.mean([near(m, proj(j, M, m, X), 0)[0] for m in VV])
    hs = np.mean([near(m, proj(js, Ms, m), 0)[0] for m in SS]) if SS else np.nan
    print(f' t {a:3d}-{b:3d} segs {dict(segs)} n {len(VV):3d}: hit X0 {h(None):.2f} Xall {h(Xall):.2f} Xblock {h(Xb):.2f} [{fmt(Xb)}; pairs {npair}] | {sobj} hit {hs:.2f} (n {len(SS)})')
