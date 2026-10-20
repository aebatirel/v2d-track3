# Stage C: budgeted convex decomposition of our own (HACD-style greedy merging, cf. Mamou & Ghorbel 2009 HACD /
# V-HACD), with an EXACT inflation cost: the cost of a convex piece is the largest distance by which its surface lies
# outside the exact W2 solid (W2 field grid, 1 mm, trilinear). Start from a grid of small cells (W2 mesh vertices per
# cell, with an overlap margin so neighbouring pieces overlap and leave no gaps), take each cell's convex hull, then
# repeatedly merge the adjacent pair whose merged hull is the least inflated. Snapshots at given piece counts.
# Each output piece is a closed convex mesh -> passes FlashCHORD's CoACD call unchanged (A14) = exactly one collision
# shape, so the shape count (C3/C4 budget) is chosen by us, not by CoACD.
# usage: c_hmerge.py <obj> <cell_mm> <margin_mm> <stop_mm> <outdir> <count,count,...>
import sys, os, time, heapq, numpy as np
from scipy.spatial import ConvexHull
from scipy.ndimage import map_coordinates
n, cell, marg, stop, od = sys.argv[1], float(sys.argv[2]) * 1e-3, float(sys.argv[3]) * 1e-3, float(sys.argv[4]), sys.argv[5]
snaps = sorted({int(x) for x in sys.argv[6].split(',')}, reverse=True)
W = '/Users/aebatirel/Documents/Code/v2d-research/work/19/b'
os.makedirs(od, exist_ok=True)
d = np.load(f'{W}/FG/{n}.npz'); F, lo, h = d['f'].astype(np.float32), d['lo'], float(d['h'])
def fval(P): return map_coordinates(F, ((P - lo) / h).T, order=1, mode='nearest') * 1e3     # mm, + outside W2
V = np.load(f'{W}/W2/{n}.npz')['v']
rng = np.random.default_rng(0)
def hull(P):
    try: return ConvexHull(P)
    except Exception:
        try: return ConvexHull(P, qhull_options='QJ')
        except Exception: return None
def cost(P):
    """max outward distance (mm) of the convex hull of P from W2; returns (cost, hull vertices)"""
    H = hull(P)
    if H is None: return 0.0, P
    hv = P[H.vertices]; tri = P[H.simplices]
    a = 0.5 * np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1)
    k = int(np.clip(a.sum() / 2e-6, 60, 800))                       # ~1 sample per 2 mm^2
    idx = rng.choice(len(tri), k, p=a / a.sum()) if a.sum() > 0 else np.zeros(k, int)
    r = rng.random((k, 2)); m = r.sum(1) > 1; r[m] = 1 - r[m]
    S = tri[idx, 0] + r[:, :1] * (tri[idx, 1] - tri[idx, 0]) + r[:, 1:] * (tri[idx, 2] - tri[idx, 0])
    E = 0.5 * (tri[:, [0, 1, 2]] + tri[:, [1, 2, 0]]).reshape(-1, 3)           # edge midpoints
    return float(max(fval(S).max(), fval(E).max(), fval(tri.mean(1)).max())), hv
t0 = time.time()
vmin = V.min(0) - marg
# assign vertices to every cell their +-margin box touches
pairs = set()
keys = []
for ox in (-1, 1):
    for oy in (-1, 1):
        for oz in (-1, 1):
            keys.append(np.floor((V + np.array([ox, oy, oz]) * marg - vmin) / cell).astype(np.int64))
K = np.unique(np.concatenate([np.column_stack([np.arange(len(V)), k]) for k in keys]), axis=0)
cid, inv = np.unique(K[:, 1:], axis=0, return_inverse=True)
order = np.argsort(inv, kind='stable'); bounds = np.searchsorted(inv[order], np.arange(len(cid) + 1))
pts = [V[K[order[bounds[i]:bounds[i + 1]], 0]] for i in range(len(cid))]
cl = {}; cost0 = []
for i, P in enumerate(pts):
    c, hv = cost(P); cl[i] = hv; cost0.append(c)
cost0 = np.array(cost0)
lut = {tuple(c): i for i, c in enumerate(cid)}
nb = {i: set() for i in cl}
for i, c in enumerate(cid):
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for dz in (-1, 0, 1):
                j = lut.get((c[0] + dx, c[1] + dy, c[2] + dz))
                if j is not None and j != i: nb[i].add(j)
print(f'{n}: {len(V)} W2 vertices, cell {cell*1e3:.0f} mm margin {marg*1e3:.1f} mm -> {len(cid)} cells; initial piece cost mm '
      f'median {np.median(cost0):.2f} p99 {np.percentile(cost0,99):.2f} max {cost0.max():.2f}; {time.time()-t0:.0f}s', flush=True)
own = {i: cost0[i] for i in cl}; ver = {i: 0 for i in cl}; heap = []
def push(i, j):
    c, hv = cost(np.vstack([cl[i], cl[j]])); heapq.heappush(heap, (c, i, j, ver[i], ver[j], hv))
for i in cl:
    for j in nb[i]:
        if i < j: push(i, j)
print(f'  initial candidates {len(heap)}; {time.time()-t0:.0f}s', flush=True)
nxt = len(cid); curmax = cost0.max(); log = []
def save(tag):
    p = f'{od}/{n}_{tag}.npz'; arrs = {}
    for k, (i, hv) in enumerate(cl.items()):
        H = hull(hv); arrs[f'v{k}'] = hv; arrs[f'f{k}'] = H.simplices if H is not None else np.zeros((0, 3), int)
    np.savez(p, n=len(cl), **arrs)
    print(f'  saved {p}: {len(cl)} pieces, max piece cost {max(own.values()):.2f} mm, median {np.median(list(own.values())):.2f}', flush=True)
si = 0
while heap and len(cl) > 1:
    c, i, j, vi, vj, hv = heapq.heappop(heap)
    if i not in cl or j not in cl or ver[i] != vi or ver[j] != vj: continue
    while si < len(snaps) and len(cl) <= snaps[si]: si += 1
    if c > stop: break
    k = nxt; nxt += 1
    cl[k] = hv; own[k] = c; ver[k] = 0; nb[k] = (nb[i] | nb[j]) - {i, j}
    for q in nb[k]: nb[q] -= {i, j}; nb[q].add(k)
    for q in (i, j): del cl[q], own[q], ver[q], nb[q]
    curmax = max(curmax, c); log.append((len(cl), c, max(own.values()) if len(cl) % 50 == 0 else np.nan))
    for q in nb[k]: push(min(k, q), max(k, q)) if False else push(k, q)
    if si < len(snaps) and len(cl) == snaps[si]:
        save(f'N{snaps[si]}'); si += 1
    if len(cl) % 500 == 0: print(f'  {len(cl)} pieces, last merge cost {c:.2f} mm, {time.time()-t0:.0f}s', flush=True)
print(f'stopped at {len(cl)} pieces (next merge cost {c:.2f} mm > stop {stop} or done); {time.time()-t0:.0f}s', flush=True)
save('final')
np.save(f'{od}/{n}_trace.npy', np.array([(a, b) for a, b, _ in log]))
