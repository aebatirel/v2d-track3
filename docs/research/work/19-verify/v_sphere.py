# Sanity check of union depth: for the deepest union point, test whether a sphere of radius r around it lies
# entirely inside the hull union (then union depth >= r, independent of boundary sampling).
import sys, numpy as np
sys.path.insert(0, '/Users/aebatirel/Documents/Code/v2d-research/work/19-verify')
sys.argv_saved = sys.argv; sys.argv = [sys.argv[0]]
import v_uniondepth as U
import pandas as pd
lidp, potp, ep, f, direction = sys.argv_saved[1:6]; ep = int(ep); f = int(f)
L, Pt = U.U(U.load(lidp)), U.U(U.load(potp))
df = pd.read_parquet(U.P % ep); fi = f if f >= 0 else len(df) - 1
pose = {x['name']: x['pose'] for x in df['observation.objects'].iloc[fi]}
Ml, Mp = U.T(pose['white_pot_lid']), U.T(pose['white_pot'])
if direction == 'lid_in_pot': host, q = Pt, U.tr(np.linalg.inv(Mp) @ Ml, L.samples())
else: host, q = L, U.tr(np.linalg.inv(Ml) @ Mp, Pt.samples())
ph, ud = host.query(q); i = int(np.argmax(ud)); p = q[i]
print(f'{direction} ep{ep} f{fi}: deepest union pt per-hull {ph[i]*1e3:.2f} union-sample {ud[i]*1e3:.2f} mm; max per-hull overall {ph.max()*1e3:.2f}')
rng = np.random.default_rng(0); d = rng.normal(size=(4000, 3)); d /= np.linalg.norm(d, axis=1)[:, None]
for r in [2.0, 3.0, 4.0, 4.5, 5.0, 5.5, 6.0]:
    s = p + d * r * 1e-3
    ins = np.zeros(len(s), bool)
    for lo, hi, e in host.H:
        k = np.where(np.all((s >= lo) & (s <= hi), 1))[0]
        if len(k): ins[k] |= (s[k] @ e[:, :3].T + e[:, 3]).max(1) <= 0
    print(f'  sphere r {r:.1f} mm: fraction inside union {ins.mean():.4f}')
