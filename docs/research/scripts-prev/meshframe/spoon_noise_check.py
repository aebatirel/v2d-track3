"""Per-vertex iid noise inflates triangle area non-uniformly and drags the area centroid.
Compare fine vs coarse triangulations of the same spoon (noise sigma 0.5/1 mm)."""
import numpy as np
from canon import spoon_mesh, canonical_frame, tri_moments
for ns, nphi in ((600, 64), (150, 32), (75, 24)):
    V0, F0 = spoon_mesh(ns=ns, nphi=nphi)
    R0, c0, _ = canonical_frame(V0, F0)
    e = np.linalg.norm(V0[F0[:, 0]] - V0[F0[:, 1]], axis=1).mean()
    for sig in (0.0005, 0.001):
        V = V0 + np.random.default_rng(1).normal(0, sig, V0.shape)
        R, c, _ = canonical_frame(V, F0)
        print(f"grid {ns}x{nphi} (mean edge {e*1000:.1f} mm) noise {sig*1000:.1f} mm: area x{tri_moments(V,F0)[1]/tri_moments(V0,F0)[1]:.2f}, origin shift {np.linalg.norm(R0@(c-c0))*1000:.1f} mm")
