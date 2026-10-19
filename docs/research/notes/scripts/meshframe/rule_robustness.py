"""How stable is rule R1 on the public scans under reconstruction-like defects?
Defects: (a) unobserved underside (faces facing down at the GT rest pose, lowest 15% of height),
(b) a missing 3 cm-radius patch, (c) smooth 1 mm normal displacement, (d) 2% anisotropic scale.
Report origin shift (mm), angle of each axis (deg, sign-insensitive), and sign flips vs the scan."""
import glob, os, json, numpy as np, trimesh, pandas as pd
from scipy.spatial.transform import Rotation as Rot
from canon import canonical_frame, third_moment
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..", "t3", "public", "mesh")
rest = pd.read_csv(os.path.join(HERE, "rest_poses.csv"))
rng = np.random.default_rng(0)

def up_axis(name):
    r = rest[rest.name == name].iloc[0]
    s, ax = r.up_axis_start[0], r.up_axis_start[1]
    u = np.zeros(3); u["xyz".index(ax)] = 1.0 if s == "+" else -1.0
    return u

rows = []
for p in sorted(glob.glob(ROOT + "/*/*.glb")):
    if p.endswith("_collision.glb"): continue
    name = os.path.basename(os.path.dirname(p))
    m = trimesh.load(p, force="mesh", process=False)
    V = np.asarray(m.vertices, float); F = np.asarray(m.faces)
    T = V[F]; cen = T.mean(1)
    fn = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); fn /= np.linalg.norm(fn, axis=1, keepdims=True) + 1e-30
    u = up_axis(name)
    h = cen @ u
    defects = {}
    defects["underside missing"] = (V, F[~((fn @ u < -0.5) & (h < h.min() + 0.15 * (h.max() - h.min())))])
    k = rng.integers(len(F)); defects["3cm patch missing"] = (V, F[np.linalg.norm(cen - cen[k], axis=1) > 0.03])
    vn = np.asarray(m.vertex_normals)
    disp = np.zeros(len(V))
    for _ in range(6):
        d = rng.normal(size=3); d /= np.linalg.norm(d)
        disp += np.sin(2 * np.pi * (V @ d) / 0.05 + rng.uniform(0, 2 * np.pi))
    disp *= 0.001 / disp.std()
    defects["smooth 1mm noise"] = (V + vn * disp[:, None], F)
    defects["2% anisotropic scale"] = (V * np.array([1.02, 0.98, 1.0]), F)
    for dname, (V2, F2) in defects.items():
        R, c, w = canonical_frame(V2, F2, "skew_x")
        # compare to identity (scan frame): axis angles sign-insensitive; flips
        angs = [float(np.degrees(np.arccos(min(1, abs(R[i, i]))))) for i in range(3)]
        flips = "".join("xyz"[i] for i in range(3) if R[i, i] < 0)
        rows.append(dict(obj=name, defect=dname, origin_shift_mm=float(np.linalg.norm(c) * 1000),
                         ang_x=angs[0], ang_y=angs[1], ang_z=angs[2], sign_flips=flips or "-",
                         eig_ratio_yx=float(w[1] / w[0]), eig_ratio_zy=float(w[2] / w[1])))
df = pd.DataFrame(rows)
pd.set_option("display.width", 200)
print(df.to_string(index=False, float_format=lambda v: f"{v:.2f}"))
df.to_csv(os.path.join(HERE, "rule_robustness.csv"), index=False)
