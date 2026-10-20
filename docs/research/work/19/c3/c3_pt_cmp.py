# Stage C3: compare Linux arm64 / amd64 (and macOS, run here) exact-call outputs with the input convex pieces.
import sys, glob, json, os, io, numpy as np
sys.path.insert(0, '/Users/aebatirel/Documents/Code/v2d-research/work/15-verify/pylib11'); import coacd
from scipy.spatial import ConvexHull
P = '/Users/aebatirel/Documents/Code/v2d-research/work/19/c3/pt/'; names = json.load(open(P + 'names.json'))
def outside(p, eq): return (p @ eq[:, :3].T + eq[:, 3]).max(1)
def metr(w, hulls):
    E = ConvexHull(w).equations; ov = np.vstack(hulls); o1 = outside(ov, E).max() * 1e3
    o2 = max(min(outside(w[i:i+1], ConvexHull(h).equations)[0] for h in hulls) for i in range(len(w))) * 1e3
    return o1, o2, sum(len(h) for h in hulls), max(len(ConvexHull(h).vertices) for h in hulls)
worst = {}
for k, nm in enumerate(names):
    d = np.load(P + f'p{k:02d}.npz'); w = d['v']; row = f'{nm[:34]:34s} in-v {len(w):4d}'
    mac = coacd.run_coacd(coacd.Mesh(w, d['f']), threshold=0.05, max_convex_hull=-1, preprocess_mode='auto')
    sets = {'mac': [np.asarray(p[0]) for p in mac]}
    for a in ('lin_arm64', 'lin_amd64'):
        e = np.load(P + f'{a}/p{k:02d}.npz'); sets[a] = [e[f'v{i}'] for i in range(int(e['n']))]
    for a, hs in sets.items():
        o1, o2, nv, hv = metr(w, hs); worst[a] = max(worst.get(a, (0, 0)), (o1, o2))
        row += f' | {a} h{len(hs)} v{nv:4d} hv{hv:3d} {o1:+.4f}/{o2:+.4f}'
    va = np.vstack(sets['lin_arm64']); vb = np.vstack(sets['lin_amd64'])
    row += ' | arm==amd ' + str(va.shape == vb.shape and np.array_equal(va, vb))
    print(row, flush=True)
print('worst (out-outside-in, in-outside-out) mm:', {a: tuple(round(x, 4) for x in v) for a, v in worst.items()})
