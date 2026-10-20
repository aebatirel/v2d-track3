"""Summarise out/contrast_<ep>.npz. usage: contrast_summ.py ep ..."""
import sys, numpy as np
A = []; 
for e in sys.argv[1:]:
    z = np.load(f'out/contrast_{e}.npz'); a = z['A']; A.append(a)
A = np.vstack(A); cols = list(z['cols']); g = lambda n: A[:, cols.index(n)]
cam, seg, rp = g('cam'), g('seg'), g('rpx'); con = g('disc') - g('ring'); edge, edge0, rsd, sat = g('edge'), g('edge_null'), g('ringsd'), g('sat')
small = rp < np.where(cam == 0, 11.5, 5.8)
print('n', len(A))
for ci, c in enumerate('abc'):
    for sz, sm in (('large', ~small), ('small', small)):
        for s in range(3):
            m = (cam == ci) & sm & (seg == s)
            if m.sum() < 10: continue
            print(f'cam {c} {sz:5s} {["rest","held","carried"][s]:8s} n {m.sum():5d} r {np.median(rp[m]):5.1f} | disc-ring med {np.median(con[m]):+6.1f} [p10 {np.percentile(con[m],10):+6.1f}, p90 {np.percentile(con[m],90):+6.1f}] |abs| med {np.median(np.abs(con[m])):5.1f} | ring sd {np.median(rsd[m]):5.1f} | edge {np.median(edge[m]):5.2f} null {np.median(edge0[m]):5.2f} | edge>2x null {np.mean(edge[m]>2*edge0[m]):.2f}' + (f' | disc sat {np.median(sat[m]):5.1f}' if ci == 0 else ''))
