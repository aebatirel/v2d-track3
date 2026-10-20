"""Verifier: sensitivity of the MC window to parameters, to the GT-derived object depth, and to the pairing."""
import numpy as np, itertools
from v_c12 import *
from scipy.spatial.transform import Rotation as Rot
CACHE = {}
def gtp(ep):
    if ep not in CACHE:
        names, P = load(ep); p = P[:, 0]
        d = np.linalg.norm(p[:, :3] - p[0, :3], axis=1) * 1000
        a = np.degrees((Rot.from_quat(p[:, 3:]) * Rot.from_quat(p[0, 3:]).inv()).magnitude())
        x = (d > 1) | (a > 1); pert = int(np.argmax(x)) if x.any() else len(d)
        CACHE[ep] = (P, p, pert)
    return CACHE[ep]
def det2(ep, A, T, kappa, L, zfix=None):
    f = np.load(f'{OUT}/feat_v2_p{ep}.npz')['rows']; C = first_run(f[:, 0], f[:, 1] >= A)
    z = np.load(f'{OUT}/mot_t2_p{ep}.npz'); r = z['rows']; r0 = float(z['r0']); depth = float(z['z']) if zfix is None else zfix
    st = r[:, 1:4]; ok = np.isfinite(st).all(1)
    px = np.where(ok, np.hypot(st[:, 0], st[:, 1]) + np.radians(np.abs(np.nan_to_num(st[:, 2]))) * r0, 0.)
    mm = px * depth / 500. * 1000; hf = np.nan_to_num(r[:, 6], nan=99.)
    hit = np.nonzero(mm >= T + kappa * hf)[0]; M = int(r[hit[0], 0]) if len(hit) else 10 ** 4
    return min(M, C + L)
def evalset(A=120, T=2.0, kappa=0.15, L=10, margin=3, zfix=None, npair=None):
    dts, dRs, ns, late = [], [], [], []
    for ep in PUB:
        P, p, pert = gtp(ep); ca = det2(ep, A, T, kappa, L, zfix)
        n = pairing(f'p{ep}', min(ca, len(p) - 1)) if npair is None else npair
        end = int(min(ca - n - margin, len(p) - 1)); b = bias(p, end, P)
        dts.append(b['dt']); dRs.append(b['dR']); ns.append(b['n']); late += [ep] if end >= pert else []
    dts, dRs = np.array(dts), np.array(dRs)
    return f'n med {np.median(ns):.0f} min {min(ns)} | dt {np.median(dts):.2f}/{np.percentile(dts,90):.2f}/{dts.max():.2f} | dR {np.median(dRs):.2f}/{np.percentile(dRs,90):.2f}/{dRs.max():.2f} | late(raw) {late}'
print('base            ', evalset())
print('z=0.55 const    ', evalset(zfix=0.55))
print('z=0.45 const    ', evalset(zfix=0.45))
print('z=0.65 const    ', evalset(zfix=0.65))
print('pairing n=0     ', evalset(npair=0))
print('margin 0        ', evalset(margin=0))
for L in (5, 15, 20, 30): print(f'L={L:2d}            ', evalset(L=L))
for T in (1.5, 3.0): print(f'T={T}           ', evalset(T=T))
for k in (0.0, 0.25): print(f'kappa={k}       ', evalset(kappa=k))
for A in (60, 240): print(f'A={A}           ', evalset(A=A))
