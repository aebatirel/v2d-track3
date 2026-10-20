import sys; sys.path.insert(0, "scripts")
import numpy as np
import spoon_model as sm
def run(label, p, extra1=0.0, extra2=0.0):
    # monkeypatch lateral extra offsets for M1/M2
    V, F, halfw = sm.spoon_body(**p["body"])
    hw = lambda z, _h=halfw: _h(z)
    parts = [(V, F)]
    r = 0.0072; bh = 0.004; rb = 0.0055
    for name, side, ex in (("m1", 1, extra1), ("m2", -1, extra2)):
        z = p[name + "_z"]; ye = side*(hw(z) + ex)
        parts.append(sm.cylinder(np.array([0, ye, z]), np.array([0, ye + side*bh, z]), rb))
        parts.append(sm.sphere(np.array([0, ye + side*(bh + r*0.85), z]), r, keep_dir=np.array([0, side, 0.]), keep_frac=0.75))
    L = p["body"].get("L", 0.33)
    parts.append(sm.cylinder(np.array([0, 0, L - 0.001]), np.array([0, 0, L + bh]), rb))
    parts.append(sm.sphere(np.array([0, 0, L + bh + r*0.85]), r, keep_dir=np.array([0, 0, 1.]), keep_frac=0.75))
    V, F = sm.assemble(parts); c, w, E, sk, A = sm.frame_and_skews(V, F)
    print(f"{label:44s} skew x {sk[0]:+.4f} y {sk[1]:+.4f} z {sk[2]:+.4f}  halfw m1 {hw(p['m1_z'])*1e3:.1f} m2 {hw(p['m2_z'])*1e3:.1f} mm")
B = dict(body=dict(), m1_z=0.105, m2_z=0.155)
run("nominal", B)
run("uniform handle wn=we=10mm", dict(B, body=dict(wn=0.010, we=0.010)))
run("uniform handle, markers same z", dict(B, body=dict(wn=0.010, we=0.010), m1_z=0.13, m2_z=0.13))
run("nominal, M1 +2mm further out", B, extra1=0.002)
run("nominal, M2 +2mm further out", B, extra2=0.002)
run("nominal, M1 -2mm (closer)", B, extra1=-0.002)
run("uniform handle, M1 +2mm", dict(B, body=dict(wn=0.010, we=0.010)), extra1=0.002)
run("uniform handle, M1 +4mm", dict(B, body=dict(wn=0.010, we=0.010)), extra1=0.004)
run("M1 at z=0.095 (in bowl edge)", dict(B, m1_z=0.095))
run("M1 at z=0.115, M2 0.145 (3cm apart)", dict(B, m1_z=0.115, m2_z=0.145))
run("M2 at 0.185 (8cm apart)", dict(B, m2_z=0.185))
