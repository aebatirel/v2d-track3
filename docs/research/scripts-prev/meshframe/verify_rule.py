"""Apply rule R1 to each public scan and report residual vs the published frame."""
import glob, os, numpy as np, trimesh
from canon import canonical_frame, tri_moments
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "t3", "public", "mesh")
for p in sorted(glob.glob(ROOT + "/*/*.glb")):
    if p.endswith("_collision.glb"): continue
    m = trimesh.load(p, force="mesh", process=False)
    V = np.asarray(m.vertices, float); F = np.asarray(m.faces)
    _, A, c, cov = tri_moments(V, F)
    out = []
    for rule in ["skew_x", "skew_y", "hybrid"]:
        R, c2, w = canonical_frame(V, F, rule)
        ang = np.degrees(np.arccos(np.clip((np.trace(R) - 1) / 2, -1, 1)))
        out.append(f"{rule}: R_diag={np.round(np.diag(R),6)} angle_to_identity={ang:.4g}deg")
    print(f"{os.path.basename(p):26s} |centroid|={np.linalg.norm(c):.2e} m  maxoffdiag/maxdiag={np.abs(cov-np.diag(np.diag(cov))).max()/np.diag(cov).max():.1e}  " + " | ".join(out))
