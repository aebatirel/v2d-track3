"""Sign robustness of the spoon's canonical z (and x) across plausible wooden-spoon shapes."""
import itertools, numpy as np
from canon import spoon_mesh, tri_moments, third_moment
res = []
for L, Lb, wb, (wh0, wh1), Db, (tb, th) in itertools.product(
        (0.25, 0.30, 0.35), (0.06, 0.09), (0.020, 0.030), ((0.007, 0.010), (0.012, 0.016)),
        (0.004, 0.012, 0.020), ((0.003, 0.0045), (0.005, 0.007))):
    V, F = spoon_mesh(L=L, Lb=Lb, wb=wb, wh0=wh0, wh1=wh1, Db=Db, tb=tb, th=th, ns=300, nphi=48)
    _, _, c, cov = tri_moments(V, F)
    w, E = np.linalg.eigh(cov)
    ez = E[:, 2] * np.sign(E[2, 2])          # oriented bowl->handle
    ex = E[:, 0] * np.sign(E[0, 0])          # oriented toward concave side (+x model)
    res.append((third_moment(V, F, c, ez), third_moment(V, F, c, ex), w[1] / w[0], w[2] / w[1],
                (c[2]) / L, L, Lb, wb, wh1, Db))
r = np.array(res)
print(f"n shapes = {len(r)}")
print(f"skew along bowl->handle: min {r[:,0].min():+.3f} max {r[:,0].max():+.3f}  frac>0 {np.mean(r[:,0]>0):.3f}")
print(f"skew along concave-side normal: min {r[:,1].min():+.3f} max {r[:,1].max():+.3f}  frac>0 {np.mean(r[:,1]>0):.3f}")
print(f"eig ratio y/x min {r[:,2].min():.2f}; z/y min {r[:,3].min():.1f}")
print(f"centroid position along length (fraction from bowl tip): {r[:,4].min():.3f}-{r[:,4].max():.3f}")
neg = r[r[:, 0] <= 0]
print("shapes with non-positive bowl->handle skew:", neg[:, 5:].round(3).tolist()[:10])
