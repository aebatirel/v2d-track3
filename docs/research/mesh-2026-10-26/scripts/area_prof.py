"""[D] Surface area per height bin along our fitted axis: scan (aligned into our frame) vs candidate meshes."""
import sys, numpy as np, trimesh
sys.path.insert(0, sys.argv[1])
import lathe_obs as L
Z = np.load(sys.argv[2]); P = Z['pts'].astype(np.float64); C = Z['cam'].astype(np.float64)
s = np.random.default_rng(0).choice(len(P), 60000, replace=False)
cost, c, d, k = L.fit_axis(P[s], C[s])
A = np.load(sys.argv[2].replace('.npz', '_align.npz'))
def prof(m, tf=None):
    V = np.asarray(m.vertices)
    if tf is not None: V = (V - tf['t']) @ tf['R']
    T = V[m.faces]; ar = 0.5 * np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1)
    hc = (T.mean(1) - c) @ d; return hc, ar
scan = trimesh.load(sys.argv[3], force='mesh'); hs, as_ = prof(scan, A)
lo, hi = min(hs.min(), -0.12), max(hs.max(), 0.12); bins = np.arange(lo, hi + 0.01, 0.01)
print('h_cm   ' + ' '.join(f'{(b+0.005)*100:6.1f}' for b in bins[:-1]))
print('scan   ' + ' '.join(f'{x*1e4:6.1f}' for x in np.histogram(hs, bins, weights=as_)[0]), f' total {as_.sum()*1e4:.0f} cm2  h range {hs.min()*100:.1f}..{hs.max()*100:.1f}')
for f in sys.argv[4:]:
    m = trimesh.load(f, force='mesh'); h2, a2 = prof(m)
    print(f'{f.split("/")[-1][:6]} ' + ' '.join(f'{x*1e4:6.1f}' for x in np.histogram(h2, bins, weights=a2)[0]), f' total {a2.sum()*1e4:.0f} cm2  h range {h2.min()*100:.1f}..{h2.max()*100:.1f}')
