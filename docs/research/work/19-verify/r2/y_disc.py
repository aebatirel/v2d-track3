import sys, numpy as np, pandas as pd
V = '/Users/aebatirel/Documents/Code/v2d-research/work/19-verify/'
args = sys.argv[1:]
g1 = {}; sys.argv = ['x']; exec(open(V + 'v_uniondepth2.py').read().split('_o = {}')[0], g1)
g2 = {}; sys.argv = ['x', 'none=none']; exec(open(V + 'r2/y_ud.py').read().split('_o = {}')[0], g2)
from scipy.ndimage import distance_transform_edt, map_coordinates
dr, ep, f, a, b, dirn = args[0], int(args[1]), int(args[2]), args[3], args[4], args[5]
W = '/Users/aebatirel/Documents/Code/v2d-research/work/19/'
if dirn == 'BA': a, b = b, a
A1 = g1['Obj'](W + dr + f'/{a}.npz'); B1 = g1['Obj'](W + dr + f'/{b}.npz'); B2 = g2['Obj'](W + dr + f'/{b}.npz')
df = pd.read_parquet(g1['P'] % ep); fi = f if f >= 0 else len(df) - 1
pose = {x['name']: x['pose'] for x in df['observation.objects'].iloc[fi]}; Ma, Mb = g1['T'](pose[a]), g1['T'](pose[b])
q = g1['tr'](np.linalg.inv(Mb) @ Ma, A1.S); ph, ud = B1.depth(q); i = int(np.argmax(ud)); p = q[i]
print(f'round-1: max union {ud[i]:.2f} mm (per-hull there {ph[i]:.2f}); max per-hull overall {ph.max():.2f}')
# my EDT at that point with a generous tile
H = 1e-4; Rr = ud[i] * 1e-3 + 4e-3; lo = p - Rr; n = int(np.ceil(2 * Rr / H)) + 1
G = np.stack(np.meshgrid(*[lo[k] + H * np.arange(n) for k in range(3)], indexing='ij'), -1).reshape(-1, 3)
m = B2.occ(G).reshape(n, n, n); D = distance_transform_edt(m) * H
e = map_coordinates(D, ((p - lo) / H)[:, None], order=1)[0] - H / 2
print(f'EDT (0.1 mm voxels, tile radius {Rr*1e3:.1f} mm) at that point: {e*1e3:.2f} mm')
# sphere containment
rng = np.random.default_rng(0); u = rng.normal(size=(20000, 3)); u /= np.linalg.norm(u, axis=1)[:, None]
for r in [ph[i], e * 1e3 - 0.2, e * 1e3 + 0.2, ud[i] - 0.2]:
    s = p + u * r * 1e-3; inside = B2.occ(s).mean() if False else (B2.perhull(s) >= 0).mean()
    print(f'  sphere r {r:5.2f} mm: fraction of sphere points inside B union {inside:.4f}')
# nearest boundary sample used by round 1
sel = np.where(np.all((B1.hi >= p - 0.02) & (B1.lo <= p + 0.02), 1))[0]
Bs = np.vstack([B1.boundary(j) for j in sel]); dd = np.linalg.norm(Bs - p, axis=1); j = np.argmin(dd)
print(f'round-1 nearest boundary sample at {dd[j]*1e3:.2f} mm; per-hull depth of that sample {B2.perhull(Bs[j:j+1])[0]*1e3:+.3f} mm (should be ~0)')
# nearest point of the EDT outside set
idx = np.argwhere(~m); c = lo + idx * H; k = np.argmin(np.linalg.norm(c - p, axis=1)); print(f'nearest outside voxel at {np.linalg.norm(c[k]-p)*1e3:.2f} mm, its per-hull depth {B2.perhull(c[k:k+1])[0]*1e3:+.3f}')
# my branch-and-bound on round-1's A samples and on my own A samples
A2 = g2['Obj'](W + dr + f'/{a}.npz')
print('my maxdepth on round-1 A samples:', B2.maxdepth(q)[:2])
Px, bnd = A2.surf(1e6, 9000); q2 = g1['tr'](np.linalg.inv(Mb) @ Ma, Px)
print('my maxdepth on my A samples (all):', B2.maxdepth(q2)[:2], ' n samples', len(q2), 'within 1 mm of p:', int((np.linalg.norm(q2 - p, axis=1) < 1e-3).sum()))
near = np.linalg.norm(q2 - p, axis=1) < 1e-3
if near.any(): print('   my maxdepth restricted to my samples within 1 mm of p:', B2.maxdepth(q2[near])[:2], 'ub of those', np.round(B2.ub_tree().query(q2[near])[0][:5]*1e3,2))
print('ub at p:', B2.ub_tree().query(p[None])[0]*1e3)
P2, bnd2 = B2.surf(2e6, 5000); Bb = P2[bnd2]; dd2 = np.linalg.norm(Bb - p, axis=1); j2 = np.argmin(dd2); s = Bb[j2]
dist = [(Bb[j2] @ B2.E[j][:, :3].T + B2.E[j][:, 3]).max() * 1e3 for j in range(len(B2.hv))]
o = np.argsort(dist)[:4]
print('my nearest "boundary" sample at %.2f mm; its signed plane distance to the 4 nearest hulls (mm, <0 inside):' % (dd2[j2] * 1e3), [(int(j), round(dist[j], 4)) for j in o])
