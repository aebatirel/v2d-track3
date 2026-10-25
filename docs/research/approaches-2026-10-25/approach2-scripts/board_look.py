import sys, numpy as np, trimesh, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
L = '/home/user/v2d-track3/meshes/library_v3/'
fig, axs = plt.subplots(1, 2, figsize=(10, 6))
for j, nm in enumerate(['wooden_piece_1', 'wooden_piece_2']):
    m = trimesh.load(L + nm + '.glb', force='mesh')
    P = m.sample(40000); c = P.mean(0); ev, V = np.linalg.eigh(np.cov((P - c).T))
    t, w, l = V[:, 0], V[:, 1], V[:, 2]
    g = 0.002
    us = np.arange(-0.13, 0.13, g); vs = np.arange(-0.08, 0.08, g)
    U, Vv = np.meshgrid(us, vs, indexing='ij')
    orig = c + U.ravel()[:, None] * l + Vv.ravel()[:, None] * w - 0.05 * t
    dirs = np.tile(t, (len(orig), 1))
    loc, ri, ti = m.ray.intersects_location(orig, dirs, multiple_hits=True)
    s = (loc - c) @ t
    TH = np.zeros(len(orig)); LO = np.full(len(orig), np.nan); HI = np.full(len(orig), np.nan); NH = np.zeros(len(orig), int)
    for k in range(len(orig)):
        pass
    order = np.argsort(ri)
    ri, s = ri[order], s[order]
    starts = np.searchsorted(ri, np.arange(len(orig)))
    ends = np.searchsorted(ri, np.arange(len(orig)), side='right')
    for k in range(len(orig)):
        ss = np.sort(s[starts[k]:ends[k]]); NH[k] = len(ss)
        if len(ss) >= 2:
            TH[k] = sum(ss[i + 1] - ss[i] for i in range(0, len(ss) - 1, 2)); LO[k] = ss[0]; HI[k] = ss[-1]
    TH = TH.reshape(U.shape)
    pos = TH[TH > 0]
    print(nm, 'eig cm2', np.round(ev * 1e4, 2), 'footprint cells', (TH > 0).sum(), 'median thickness mm', round(np.median(pos) * 1e3, 2),
          'p10/p90', np.round(np.percentile(pos, [10, 90]) * 1e3, 1), 'mid-plane median mm', round(np.nanmedian((LO + HI) / 2) * 1e3, 2))
    im = axs[j].imshow(TH.T * 1e3, origin='lower', extent=[us[0]*100, us[-1]*100, vs[0]*100, vs[-1]*100], vmin=0, vmax=25, cmap='viridis')
    axs[j].set_title(f'{nm} ours: thickness (mm) along smallest PCA axis'); plt.colorbar(im, ax=axs[j], fraction=0.03)
    np.savez(f'out/{nm}_thick.npz', TH=TH, us=us, vs=vs, c=c, V=V, LO=LO.reshape(U.shape), HI=HI.reshape(U.shape))
plt.tight_layout(); plt.savefig('out/boards_thick.png', dpi=70)
