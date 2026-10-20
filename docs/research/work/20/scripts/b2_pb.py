# Stage B5: P(frame B) per candidate sign rule with the marker layout MEASURED at rest (this note, B1-B4), as a function of the
# unknown rest roll phi (phi > 0 = M1's side up). Table-frame offsets relative to the handle axis (lateral w, height h) are
# rotated into the body frame:  lat = w cos(phi) +- h sin(phi), up(toward concave) = -+w sin(phi) + h cos(phi).
# Bodies: note 13 round-handle priors (spoon_model.spoon_body), handle radius tightened to the measured 9.5-10.5 mm.
# Rules: note 13 b_spoon.rules (n07 x/y, hybrid(0.02), larger|skew|, noisy single-statistic, 15 F2, F2b, 154 F3 hybrids) and
# the noisy mid-axis skew rule with the c_noisy posterior over n (as in 13-verify v2_measured.py).
# [b2 copy of b_pb.py: adds layouts hl_bend12 (bend N(1.2,1.2) mm, M2 lateral sd 1.0), hl_bend1, and hl_r2 (re-run 2:
#  M2 lateral N(15.2,0.8) -> asym ~3.7+-1.0, bend N(1.6,0.7)); writes out/b2/]
# Usage: b_pb.py N seed layout  (layout: meas | meas_jointaxis | model)  -> out/b/pb_<layout>_<seed>.jsonl
import sys, json, numpy as np
from scipy.stats import norm
N, seed, LAY = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
sys.path.insert(0, '/Users/aebatirel/Documents/Code/v2d-research/work/13/scripts')
_argv = sys.argv; sys.argv = ['b_spoon', '0', '0', 'round']
import b_spoon as BS                                     # rules(), F2/F2b/F3 sets (Stage B survivors)
from b_feats import feats
from spoon_model import spoon_body, sphere, cylinder, assemble
sys.argv = _argv
rng = np.random.default_rng(seed)
ns, post = np.load('/Users/aebatirel/Documents/Code/v2d-research/work/13/out/c_noisy_post.npy')
OUTF = f'/Users/aebatirel/Documents/Code/v2d-research/work/20/out/b2/pb_{LAY}_{seed}.jsonl'
PHIS = [-10, 0, 10, 20, 25]


def draw():
    we = rng.uniform(0.0095, 0.0105); ratio = rng.uniform(0.9, 1.05); Lb = rng.uniform(0.085, 0.10)
    body = dict(L=rng.uniform(0.295, 0.312), Lb=Lb, wb=rng.uniform(0.024, 0.028), wn=rng.uniform(0.0075, 0.0095), we=we,
                tb=rng.uniform(0.0035, 0.006), th=2 * we * ratio, Db=rng.uniform(0.006, 0.015), asym_y=0.0,
                handle_off_x=rng.uniform(-0.008, 0.006), neck=rng.uniform(0.015, 0.035), ns=300, nphi=48)
    z1 = rng.uniform(0.113, 0.125)
    p = dict(body=body, z1=z1, z2=z1 + rng.uniform(0.041, 0.044), r=rng.uniform(0.0062, 0.0072), bh=rng.uniform(0.002, 0.006),
             kf=rng.uniform(0.5, 0.95))
    if LAY == 'meas':          # handle-axis line (e5 frames 0-2): M1 further out
        p.update(w1=rng.uniform(18.3, 20.2), h1=rng.uniform(4.5, 7.5), w2=rng.uniform(15.8, 18.8), h2=rng.uniform(8.0, 12.0))
    elif LAY == 'meas_jointaxis':   # joint bowl+handle centre line: lateral asymmetry ~0
        p.update(w1=rng.uniform(17.5, 19.5), h1=rng.uniform(4.5, 7.5), w2=rng.uniform(17.5, 19.5), h2=rng.uniform(8.0, 12.0))
    if LAY.startswith('hl'):    # markers relative to the HANDLE line (cam-a handle-only midline, 4 clips; stereo e5), bowl offset
        w1 = rng.normal(18.9, 0.6); p.update(w1=w1, w2=(rng.normal(15.2, 0.8) if LAY == 'hl_r2' else rng.normal(15.9, 1.0 if LAY == 'hl_bend12' else 0.7)), h1=rng.uniform(4.5, 7.5), h2=rng.uniform(8.0, 12.0),
                                             phi=float(rng.normal(-2.5, 3.0)), y3=rng.normal(-2.5, 1.2), h3=rng.uniform(9.5, 12.0),
                                             dz3=rng.uniform(0.002, 0.010))
        p['bend'] = {'hl_bend0': 0.0, 'hl_bend3': rng.uniform(1.5, 4.5), 'hl_bend5': rng.uniform(4.0, 6.5), 'hl_bend2': rng.normal(2.0, 1.5), 'hl_bend12': rng.normal(1.2, 1.2), 'hl_bend1': 1.0, 'hl_r2': rng.normal(1.6, 0.7),
                     'hl_nomark_bend0': 0.0, 'hl_nomark_bend2': rng.normal(2.0, 1.5)}[LAY]
        return p
    if LAY == 'final':         # combined measurement (B3): asym +0.5 +- 1.5, roll -2.5 +- 3 deg, all sampled jointly
        w1 = rng.normal(19.0, 0.6); p.update(w1=w1, w2=w1 - rng.normal(0.5, 1.5), h1=rng.uniform(4.5, 7.5), h2=rng.uniform(8.0, 12.0),
                                             phi=float(rng.normal(-2.5, 3.0)))
        p.update(y3=rng.normal(-0.4, 1.2), h3=rng.uniform(9.5, 12.0), dz3=rng.uniform(0.002, 0.010))
        return p
    p.update(y3=rng.uniform(-2.5, 0.5), h3=rng.uniform(9.5, 12.0), dz3=rng.uniform(0.002, 0.010))
    return p


def marker(axis_pt, c, r, bh, kf):
    d = c - axis_pt; d /= np.linalg.norm(d); s1 = c - d * 0.85 * r; s0 = s1 - d * bh
    return [cylinder(s0, s1, 0.0055), sphere(c, r, keep_dir=d, keep_frac=kf)]


def build(p, phi_deg):
    b = p['body']; L, Lb = b['L'], b['Lb']; V, F, halfw = spoon_body(**b)
    if p.get('bend'):   # bowl shifted toward M1's side (+y) by bend mm; linear blend to 0 over the neck (Lb*0.8 .. Lb+0.03)
        V = V.copy(); V[:, 1] += p['bend'] * 1e-3 * np.clip((Lb + 0.03 - V[:, 2]) / (0.2 * Lb + 0.03), 0, 1)
    parts = [(V, F)]
    ramp = lambda z: b['handle_off_x'] * np.clip((z - Lb) / (L - Lb), 0, 1); r, bh, kf = p['r'], p['bh'], p['kf']
    if LAY == 'model':          # note 13 placement: M1/M2 at halfw+base+0.85r in-plane, M3 on the axis
        for z, side in ((p['z1'], 1), (p['z2'], -1)):
            ax = np.array([ramp(z), 0, z]); c = np.array([ramp(z), side * (halfw(z) + bh + 0.85 * r), z]); parts += marker(ax, c, r, bh, kf)
        c = np.array([ramp(L), 0, L + bh + 0.85 * r]); parts += marker(np.array([ramp(L), 0, L - 0.05]), c, r, bh, kf)
        return assemble(parts)
    if 'nomark' in LAY: return assemble(parts)
    ph = np.radians(phi_deg); cs, sn = np.cos(ph), np.sin(ph)
    lat1 = p['w1'] * cs + p['h1'] * sn; up1 = -p['w1'] * sn + p['h1'] * cs
    lat2 = p['w2'] * cs - p['h2'] * sn; up2 = p['w2'] * sn + p['h2'] * cs
    lat3 = p['y3'] * cs + p['h3'] * sn; up3 = -p['y3'] * sn + p['h3'] * cs
    for z, side, lat, up in ((p['z1'], 1, lat1, up1), (p['z2'], -1, lat2, up2)):
        ax = np.array([ramp(z), 0, z]); c = np.array([ramp(z) - up * 1e-3, side * lat * 1e-3, z]); parts += marker(ax, c, r, bh, kf)
    c = np.array([ramp(L) - up3 * 1e-3, lat3 * 1e-3, L + p['dz3']])
    parts += marker(np.array([ramp(L), 0, L - 0.02]), c, r, bh, kf)
    return assemble(parts)


def noisy_mid(V, F, nsamp=150000):
    T = V[F]; a = 0.5 * np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1); A = a.sum()
    c = (a[:, None] * T.mean(1)).sum(0) / A; Q = T - c
    C = (sum(np.einsum('n,ni,nj->ij', a, Q[:, k], Q[:, k]) for k in range(3)) + np.einsum('n,ni,nj->ij', a, Q.sum(1), Q.sum(1))) / 12 / A
    w, E = np.linalg.eigh(C); sk = []
    for i in range(3):
        f = Q @ E[:, i]; x, y, z = f.T
        h3 = x ** 3 + y ** 3 + z ** 3 + x * x * (y + z) + y * y * (x + z) + z * z * (x + y) + x * y * z
        sk.append((a * h3).sum() / 10 / A / w[i] ** 1.5)
    idx = rng.choice(len(F), nsamp, p=a / A); u1, u2 = rng.random(nsamp), rng.random(nsamp); m = u1 + u2 > 1
    u1[m], u2[m] = 1 - u1[m], 1 - u2[m]; P = T[idx, 0] + u1[:, None] * (T[idx, 1] - T[idx, 0]) + u2[:, None] * (T[idx, 2] - T[idx, 0])
    u = ((P - c) @ E[:, 1]) / np.sqrt(w[1]); se1 = np.std(u ** 3 - 3 * u - 1.5 * sk[1] * (u ** 2 - 1))
    toM2 = sk[1] * np.sign(-E[1, 1]); toConc = sk[0] * np.sign(-E[0, 0]); toH = sk[2] * np.sign(E[2, 2])
    PB = float((norm.cdf(toM2 * np.sqrt(ns) / se1) * post).sum())
    return dict(toM2=float(toM2), toConc=float(toConc), toH=float(toH), PB_noisy_mid=PB, midIsY=bool(np.argmax(np.abs(E[:, 1])) == 1),
                sd_mm=(np.sqrt(w) * 1e3).round(2).tolist())


KEYS = ['n07_skew_x', 'n07_skew_y', 'n07_hybrid.02', 'n07_larger_abs', 'noisy_q10_y', 'noisy_-shalf_x', 'noisy_far3d_x']
for i in range(N):
    p = draw(); rec = dict(i=i, p={k: v for k, v in p.items() if k != 'body'}, body={k: v for k, v in p['body'].items() if k not in ('ns', 'nphi')}, res={})
    for phi in ([p['phi']] if (LAY == 'final' or LAY.startswith('hl')) else PHIS if LAY != 'model' else [0]):
        V, F = build(p, phi); S = BS.feats(V, F, hull=True) if hasattr(BS, 'feats') else feats(V, F, hull=True)
        R = BS.rules(S); nm = noisy_mid(V, F)
        f2 = [v for k, v in R.items() if k.startswith('F2|')]; f2b = [v for k, v in R.items() if k.startswith('F2b|')]
        rec['res'][phi] = dict(**nm, skew=[float(x) for x in S['skew']], **{k: R[k] for k in KEYS},
                               F2_shareB=float(np.mean([v.startswith('B') for v in f2])), F2b_shareB=float(np.mean([v.startswith('B') for v in f2b])),
                               F3_shareB=1 - R['F3_shareA'], zflip=float(np.mean(['zflip' in v for v in R.values() if isinstance(v, str)])))
    with open(OUTF, 'a') as f: f.write(json.dumps(rec) + '\n')
    print(i, ' | '.join(f"phi {ph}: toM2 {r['toM2']:+.3f} conc {r['toConc']:+.3f} PBmid {r['PB_noisy_mid']:.2f} x:{r['n07_skew_x'][0]} y:{r['n07_skew_y'][0]} F2 {r['F2_shareB']:.2f}"
                         for ph, r in rec['res'].items()), flush=True)
