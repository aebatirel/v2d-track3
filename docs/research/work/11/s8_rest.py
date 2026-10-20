"""Rest/stable poses and table height from public GT: static segments (>=10 frames, v<1.5 cm/s, w<8 deg/s)."""
from c11 import *
import json
from collections import defaultdict
PTS = {}
def pts(nm):
    if nm not in PTS: PTS[nm] = surface_points(nm, 4000, 2)
    return PTS[nm]
rec = defaultdict(list); table = []
for ep in PUBLIC:
    e = load_episode(ep); p = e['pose']; dt = 1 / 20.0
    for j, nm in enumerate(e['names']):
        x = p[:, j, :3]; q = p[:, j, 3:]
        v = np.r_[0, np.linalg.norm(np.diff(x, axis=0), axis=1)] / dt
        w = np.r_[0, np.degrees(Rot.from_quat(q[1:]).inv() * Rot.from_quat(q[:-1])).magnitude() if False else 0]
        w = np.r_[0, np.degrees((Rot.from_quat(q[1:]).inv() * Rot.from_quat(q[:-1])).magnitude())] / dt
        st = (v < 0.015) & (w < 8)
        # runs
        i = 0; T = len(st)
        while i < T:
            if st[i]:
                k = i
                while k < T and st[k]: k += 1
                if k - i >= 10:
                    m = (i + k) // 2
                    R = R_of(q[m]); P = pts(nm) @ R.T + x[m]
                    zmin = P[:, 2].min(); _, tilt = yaw_tilt(q[m], nm)
                    c = R[2, :]; a = np.argmax(np.abs(c)); up = ("+" if c[a] > 0 else "-") + "xyz"[a]
                    others = [o for o in e['names'] if o != nm]
                    rec[nm].append(dict(ep=ep, task=e['task'], f0=i, f1=k - 1, z=float(x[m, 2]), zmin=float(zmin), tilt=float(tilt), up=up))
                i = k
            else:
                i += 1
for nm, L in rec.items():
    print(f"\n{nm}")
    groups = defaultdict(list)
    for r in L:
        key = (r['up'], round(r['zmin'] / 0.01) * 0.01 < 0.612)
        groups[r['up'] + (' table' if r['zmin'] < 0.612 else ' raised')].append(r)
    for g, G in groups.items():
        z = np.array([r['z'] for r in G]); zm = np.array([r['zmin'] for r in G]); t = np.array([r['tilt'] for r in G])
        print(f"  {g:10s} n={len(G):2d} eps={sorted(set(r['ep'] for r in G))} origin z {z.mean():.4f}±{z.std()*1000:.1f}mm  lowest-pt z {zm.mean():.4f}±{zm.std()*1000:.1f}mm  tilt {t.mean():.1f}±{t.std():.1f}")
        if g.endswith('table'): table += list(zm)
table = np.array(table)
print(f"\nTABLE: lowest-point z over all on-table rests: median {np.median(table):.4f} IQR {np.percentile(table,25):.4f}-{np.percentile(table,75):.4f} n={len(table)}")
json.dump(rec, open('s8_rest.json', 'w'), indent=0)
