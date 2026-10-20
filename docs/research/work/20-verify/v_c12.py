"""Verifier (DIG 20 C1/C2): independent re-derivation of the slot-0 anchor-window bias from parquet GT and the
stored detector feature files (decision rule re-implemented here). Analysis only (public GT)."""
import sys, json, numpy as np, pandas as pd
from scipy.spatial.transform import Rotation as Rot
ROOT = '/Users/aebatirel/Documents/Code/v2d-research'
OUT = f'{ROOT}/work/20/out/c'
PUB = [0, 2, 11, 12, 13, 18, 21, 22, 23, 24, 26, 27, 31, 39, 40, 41, 42, 43, 44]
SYNC = json.load(open(f'{ROOT}/work/20/out/sync_table.json'))['episodes']

def load(ep):
    df = pd.read_parquet(f'{ROOT}/data/track_3/public/data/chunk-000/episode_{ep:06d}.parquet').sort_values('frame_index')
    objs = df['observation.objects'].tolist()
    names = [o['name'] for o in objs[0]]
    T = len(objs); P = np.full((T, len(names), 7), np.nan)
    for i, row in enumerate(objs):
        for o in row:
            p = np.asarray(o['pose'], float); j = names.index(o['name'])
            P[i, j] = [p[0], p[1], p[2], p[4], p[5], p[6], p[3]]   # -> xyz + quat xyzw
    assert (np.diff(df['frame_index'].to_numpy()) == 1).all()
    return names, P

def karcher(q):
    R = Rot.from_quat(q); M = R[0]
    for _ in range(50):
        d = (M.inv() * R).as_rotvec().mean(0); M = M * Rot.from_rotvec(d)
        if np.linalg.norm(d) < 1e-12: break
    return M

def bias(P, end, allP):
    if end < 0: return dict(n=0, dt=0, dR=0, shift=0)
    W = P[:end + 1]; t = W[:, :3].mean(0); M = karcher(W[:, 3:]); R0 = Rot.from_quat(P[0, 3:])
    dt = np.linalg.norm(t - P[0, :3]) * 1000; dR = np.degrees((M * R0.inv()).magnitude())
    # scorer-side induced error: achieved start = (t, M); warp = P0 * Mean^-1 applied to every object position
    Ra = (R0 * M.inv()).as_matrix(); off = P[0, :3] - Ra @ t
    X = allP[..., :3].reshape(-1, 3); X = X[np.isfinite(X).all(1)]
    sh = np.linalg.norm(X @ Ra.T + off - X, axis=1).mean() * 1000
    return dict(n=end + 1, dt=dt, dR=dR, shift=sh)

def first_run(k, hit, persist=2):
    run = 0
    for i, h in enumerate(hit):
        run = run + 1 if h else 0
        if run >= persist: return int(k[i - persist + 1])
    return 10 ** 4

def pairing(key, row):
    for s in SYNC[key]['pairing_a_to_b']:
        if s['rows'][0] <= row <= s['rows'][1]: return s['n']
    return 1

def detector(ep, A=120, T=2.0, kappa=0.15, L=10):
    f = np.load(f'{OUT}/feat_v2_p{ep}.npz')['rows']; C = first_run(f[:, 0], f[:, 1] >= A)
    z = np.load(f'{OUT}/mot_t2_p{ep}.npz'); r = z['rows']; r0 = float(z['r0']); depth = float(z['z'])
    st = r[:, 1:4]; ok = np.isfinite(st).all(1)
    px = np.where(ok, np.hypot(st[:, 0], st[:, 1]) + np.radians(np.abs(np.nan_to_num(st[:, 2]))) * r0, 0.)
    mm = px * depth / 500. * 1000; hf = np.nan_to_num(r[:, 6], nan=99.)
    hit = np.nonzero(mm >= T + kappa * hf)[0]; M = int(r[hit[0], 0]) if len(hit) else 10 ** 4
    return min(M, C + L), C, M, depth

if __name__ == '__main__':
    rows = []
    for ep in PUB:
        names, P = load(ep); p = P[:, 0]
        d = np.linalg.norm(p[:, :3] - p[0, :3], axis=1) * 1000
        a = np.degrees((Rot.from_quat(p[:, 3:]) * Rot.from_quat(p[0, 3:]).inv()).magnitude())
        x = (d > 1) | (a > 1); pert = int(np.argmax(x)) if x.any() else len(d)
        on = int(np.argmax(d > 10)) if (d > 10).any() else len(d)
        xr = (d > 1.5) | (a > 1.5); run = np.convolve(xr.astype(int), np.ones(3, int), 'valid') == 3
        pert_r = int(np.argmax(run)) if run.any() else len(d)
        ca, C, M, depth = detector(ep); n = pairing(f'p{ep}', min(ca, len(d) - 1)); end = min(ca - n - 3, len(d) - 1)
        maxrot_pre_on = a[:on].max(); maxd_pre_on = d[:on].max()
        r = dict(ep=ep, name=names[0], nobj=len(names), C=C, M=M, ca=ca, n=n, end=end, pert=pert, pert_r=pert_r, on=on,
                 depth=depth, maxrot_pre_on=maxrot_pre_on, maxd_pre_on=maxd_pre_on,
                 det=bias(p, end, P), orc=bias(p, pert - 1, P), orr=bias(p, pert_r - 1, P), cm1=bias(p, on - 1, P))
        rows.append(r)
        print(f"p{ep:2d} {names[0][:14]:14s} C{C:5d} M{M:5d} end{end:4d} pert{pert:3d}/{pert_r:3d} on{on:3d} z{depth:.2f} | det n{r['det']['n']:3d} {r['det']['dt']:.2f}mm {r['det']['dR']:.2f}d sh{r['det']['shift']:.2f}"
              f" | orc {r['orc']['dt']:.2f} {r['orc']['dR']:.2f} | 1cm n{r['cm1']['n']} {r['cm1']['dt']:.2f} {r['cm1']['dR']:.2f} sh{r['cm1']['shift']:.2f} | maxrot<on {maxrot_pre_on:.2f}", flush=True)
    for key in ('det', 'orc', 'orr', 'cm1'):
        v = lambda f: np.array([r[key][f] for r in rows])
        print(f"{key}: n med {np.median(v('n')):.0f} min {v('n').min()} | dt med/p90/max {np.median(v('dt')):.2f}/{np.percentile(v('dt'),90):.2f}/{v('dt').max():.2f}"
              f" | dR {np.median(v('dR')):.2f}/{np.percentile(v('dR'),90):.2f}/{v('dR').max():.2f} | shift {np.median(v('shift')):.2f}/{np.percentile(v('shift'),90):.2f}/{v('shift').max():.2f}")
    mr = np.array([r['maxrot_pre_on'] for r in rows]); print('max rot before 1cm onset: min/med/max', mr.min().round(2), np.median(mr).round(2), mr.max().round(2))
    late_raw = [r['ep'] for r in rows if r['end'] >= r['pert']]; late_rob = [r['ep'] for r in rows if r['end'] >= r['pert_r']]
    print('window end >= raw pert:', late_raw, ' >= robust pert:', late_rob)
    json.dump(rows, open(f'{ROOT}/work/20-verify/v_c12.json', 'w'), default=float, indent=0)
