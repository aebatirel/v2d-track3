"""Canonical frame of a parametric wooden spoon and its sensitivity to reconstruction errors.
Reference spoon = nominal parameters; 'ours' = perturbed reconstruction. Both canonicalised by
rule R1. Report the induced frame mismatch M = ref_T_ours (centroid offset, rotation angle)."""
import json, os, numpy as np
from scipy.spatial.transform import Rotation as Rot
from canon import spoon_mesh, canonical_frame, third_moment, tri_moments

HERE = os.path.dirname(os.path.abspath(__file__))
nom = dict(L=0.30, Lb=0.075, wb=0.027, wh0=0.008, wh1=0.011, tb=0.003, th=0.0045, Db=0.012)
V0, F0 = spoon_mesh(**nom)
R0, c0, w0 = canonical_frame(V0, F0, "skew_x")
print("nominal spoon: area=%.4f m2  centroid(z from bowl tip)=%.4f m" % (tri_moments(V0, F0)[1], c0[2]))
print("  eigvals (std mm):", np.round(np.sqrt(w0) * 1000, 2), " ratios:", np.round(w0[1] / w0[0], 2), np.round(w0[2] / w0[1], 2))
for name, ax in zip("xyz", R0):
    print(f"  canonical {name} in spoon coords {np.round(ax, 4)}  skew={third_moment(V0, F0, c0, ax):+.4f}")
print("  +z points toward handle end:", R0[2] @ np.array([0, 0, 1.0]) > 0,
      "; +x (skew_x rule) points toward bowl concave side (+x model):", R0[0] @ np.array([1.0, 0, 0]) > 0)

# perturbations of the reconstruction (the ref is the nominal spoon in the same physical placement)
cases = {
    "handle +1cm": dict(L=0.31), "handle -1cm": dict(L=0.29),
    "bowl width +10%": dict(wb=0.0297), "bowl width -10%": dict(wb=0.0243),
    "bowl depth +50%": dict(Db=0.018), "bowl depth -50%": dict(Db=0.006),
    "bowl length +10%": dict(Lb=0.0825), "thickness +30%": dict(tb=0.0039, th=0.00585),
    "handle width +20%": dict(wh0=0.0096, wh1=0.0132),
    "handle bent 5mm sideways": dict(bend=0.005), "handle tilted 3deg up": dict(handle_tilt=np.tan(np.radians(3))),
}
rows = []
for k, d in cases.items():
    p = dict(nom); p.update(d)
    V, F = spoon_mesh(**{kk: vv for kk, vv in p.items()}, **({} if "bend" in d or "handle_tilt" in d else {}))
    R, c, w = canonical_frame(V, F, "skew_x")
    # ours in ref canonical coordinates: origin offset and rotation
    t = R0 @ (c - c0)               # our origin expressed in ref canonical frame
    Rm = R0 @ R.T                   # ref_R_ours
    ang = np.degrees(Rot.from_matrix(Rm).magnitude())
    rows.append(dict(case=k, offset_mm=(t * 1000).round(2).tolist(), offset_norm_mm=float(np.linalg.norm(t) * 1000),
                     rot_deg=float(ang), skews=[float(third_moment(V, F, c, a)) for a in R]))
    print(f"  {k:26s} origin offset (ref canon, mm) {np.round(t*1000,2)} |{np.linalg.norm(t)*1000:5.2f}|  rot {ang:6.3f} deg  skews {np.round(rows[-1]['skews'],3)}")

# missing-surface case: drop part of the bowl underside (unobserved)
V, F = V0, F0
T = V[F]; cen = T.mean(1)
for frac_name, mask in {
    "bowl underside missing": (cen[:, 2] < nom["Lb"]) & (cen[:, 0] < -0.006),
    "handle end 3cm missing": cen[:, 2] > nom["L"] - 0.03,
    "one side (y<0) of handle missing": (cen[:, 1] < 0) & (cen[:, 2] > nom["Lb"]),
}.items():
    F2 = F[~mask]
    R, c, w = canonical_frame(V, F2, "skew_x")
    t = R0 @ (c - c0); ang = np.degrees(Rot.from_matrix(R0 @ R.T).magnitude())
    print(f"  {frac_name:26s} origin offset (mm) {np.round(t*1000,2)} |{np.linalg.norm(t)*1000:5.2f}|  rot {ang:6.3f} deg  removed area {100*(1-tri_moments(V,F2)[1]/tri_moments(V,F)[1]):.1f}%")
    rows.append(dict(case=frac_name, offset_mm=(t * 1000).round(2).tolist(), offset_norm_mm=float(np.linalg.norm(t) * 1000), rot_deg=float(ang)))

# vertex noise
rng = np.random.default_rng(0)
for sig in (0.0005, 0.001, 0.002):
    V2 = V0 + rng.normal(0, sig, V0.shape)
    R, c, w = canonical_frame(V2, F0, "skew_x")
    t = R0 @ (c - c0); ang = np.degrees(Rot.from_matrix(R0 @ R.T).magnitude())
    print(f"  vertex noise {sig*1000:.1f}mm          origin offset (mm) {np.round(t*1000,2)} |{np.linalg.norm(t)*1000:5.2f}|  rot {ang:6.3f} deg")
json.dump(rows, open(os.path.join(HERE, "spoon_sensitivity.json"), "w"), indent=1)
