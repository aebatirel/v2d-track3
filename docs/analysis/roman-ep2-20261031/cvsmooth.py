"""Cross-validated zero-lag smoother (owner: perception improvements, 31 Oct). Settings are chosen on one half of the
public episodes and scored on the other half, both ways, so the reported gain is not tuned on its own test data.
Half A = episodes at even positions of the sorted list, half B = odd positions. Every variant includes the half-frame
advance (adopted S2). Score: mean ADD on a 5 cm sphere after one constant offset per object (diagnostic, mocap).
Usage: cvsmooth.py DATA_DIR MESHDIR OUT.json
"""
import glob, json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import all20 as A  # noqa: E402
from rtssweep import prep  # noqa: E402

data, meshdir, outf = sys.argv[1:4]
eps = sorted(glob.glob(f'{data}/ep*'), key=lambda s: int(s.rsplit('ep', 1)[1]))
half = {os.path.basename(d): ('A' if i % 2 == 0 else 'B') for i, d in enumerate(eps)}
objs = sum([prep(d, meshdir) for d in eps], [])
adv = [(A.advance(o['p'], A.ADV), A.qadvance(o['q'], A.ADV)) for o in objs]
raw = np.array([A.add_cm(o['p'], o['q'], o['R0'], o['G']) for o in objs])
shift = np.array([A.add_cm(p, q, o['R0'], o['G']) for (p, q), o in zip(adv, objs)])
grid = [(s, qf, r) for s in (0.001, 0.002, 0.004, 0.008, 0.016) for qf in (0.25, 1.0, 4.0) for r in (1.0, 1e-2)]
cell = {}
for g in grid:
    sig, qf, r = g; v = []
    for (p, q), o in zip(adv, objs):
        ps = A.kf(p, o['held'], sig, qf, qf * r, smooth=True)
        qq = A.kf(q, o['held'], sig / 0.1 * np.deg2rad(0.3) / 2, qf * 2.5, qf * 2.5 * r, smooth=True)
        v.append(A.add_cm(ps, qq, o['R0'], o['G']))
    cell[g] = np.array(v)
H = np.array([half[o['ep']] for o in objs]); out = {'grid': [list(g) for g in grid]}
for tr, te in (('A', 'B'), ('B', 'A')):
    best = min(grid, key=lambda g: cell[g][H == tr].mean()); v = cell[best][H == te]
    d_raw = v - raw[H == te]; d_sh = v - shift[H == te]
    out[f'train_{tr}_test_{te}'] = dict(best=list(best), objects=int((H == te).sum()),
        test_raw=float(raw[H == te].mean()), test_shift=float(shift[H == te].mean()), test_shift_smooth=float(v.mean()),
        rel_vs_raw_pct=float(100 * (v.mean() / raw[H == te].mean() - 1)), rel_vs_shift_pct=float(100 * (v.mean() / shift[H == te].mean() - 1)),
        better_vs_shift=int((d_sh < -0.005).sum()), worse_vs_shift=int((d_sh > 0.005).sum()), worst_vs_shift_cm=float(d_sh.max()))
json.dump(out, open(outf, 'w'), indent=1); print(json.dumps({k: v for k, v in out.items() if k != 'grid'}, indent=1))
