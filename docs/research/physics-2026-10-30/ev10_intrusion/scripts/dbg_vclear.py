import sys, glob, importlib.util, numpy as np, trimesh
spec2 = importlib.util.spec_from_file_location('intrusion', '/home/user/v2d-track3/tools/intrusion.py'); I = importlib.util.module_from_spec(spec2); spec2.loader.exec_module(I)
src = open(sys.argv[1]).read(); exec(src[src.index('def heightmap'):src.index('def analyse')])
names, O, P, Q, fps = I.load_ref(sys.argv[2]); Oi = I.inv_pose(O); REL = np.einsum('tij,tjk->tik', Oi[:, 0], O[:, 1])
UA = I.Union(sorted(glob.glob('/home/user/v2d-track3/meshes/carve/ev10/blue_cup/piece_*.obj')))
UG = I.Union(sorted(glob.glob('/home/user/v2d-track3/meshes/carve/ev10/beige_cup/piece_*.obj')))
xs, ys, H = heightmap(lambda X: UA.depth_lb(X) > 0, UA.alo, UA.ahi); h = xs[1] - xs[0]; cx, cy = 0.0026, 0.0041
G = UG.surface(0.002)
# beige radial profile in its own frame
r = np.hypot(G[:, 0] - 0.0026, G[:, 1] - 0.0041); hz = -G[:, 2]
for a in range(-85, 90, 20):
    k = (hz >= a / 1000) & (hz < a / 1000 + 0.01); print('beige h', a, 'r max', round(r[k].max() * 1e3, 1) if k.any() else None)
gx, gy = np.meshgrid(xs, ys, indexing='ij'); rb = np.hypot(gx - cx, gy - cy)
for f in (110, 140):
    X = G @ REL[f, :3, :3].T + REL[f, :3, 3]; hz = -X[:, 2]; rr = np.hypot(X[:, 0] - cx, X[:, 1] - cy)
    i = np.clip(np.round((X[:, 0] - xs[0]) / h).astype(int), 0, len(xs) - 1); j = np.clip(np.round((X[:, 1] - ys[0]) / h).astype(int), 0, len(ys) - 1)
    Hp = H[i, j]; ok = np.isfinite(Hp) & (rr < 0.04); v = np.where(ok, hz - Hp, np.inf); k = np.argmin(v)
    print(f, 'min vclear', round(v[k] * 1e3, 1), 'at r', round(rr[k] * 1e3, 1), 'h', round(hz[k] * 1e3, 1), 'H', round(Hp[k] * 1e3, 1), 'inside blue?', UA.depth_lb(X[k:k+1])[0] * 1e3)
    # blue top surface around that radius
    print('   blue H at r-bands', [(a, round(float(np.nanmedian(H[(rb >= a/1000) & (rb < a/1000 + 0.001)])) * 1e3, 1)) for a in range(int(rr[k]*1e3) - 3, int(rr[k]*1e3) + 3)])
    nb = (v < -0.005).sum(); print('   points with vclear < -5 mm:', nb, 'of', ok.sum())
