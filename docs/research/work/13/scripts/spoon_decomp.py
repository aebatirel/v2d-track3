import sys; sys.path.insert(0, "scripts")
import numpy as np
from spoon_model import *
def run(label, p):
    V, F = spoon_with_markers(p); c, w, E, sk, A = frame_and_skews(V, F)
    tilt_yz = np.degrees(np.arctan2(E[2, 1], E[1, 1]))
    print(f"{label:38s} A={A*1e4:5.0f}cm2 skew x {sk[0]:+.4f} y {sk[1]:+.4f} z {sk[2]:+.4f}  y-axis tilt toward z {tilt_yz:+.3f} deg  cz={c[2]*1e3:.0f}mm")
B = dict(body=dict(), m1_z=0.105, m2_z=0.155)
run("nominal", B)
run("no markers at all", dict(B, m3=False, keep_frac=1e-9, bases=False))
run("M3 only", dict(B, m1_z=0.0, m2_z=0.0, keep_frac=0.75) | {"only": 1}) if False else None
run("no M3", dict(B, m3=False))
run("no bases", dict(B, bases=False))
run("M1,M2 same z=0.13", dict(B, m1_z=0.13, m2_z=0.13))
run("M1 nearer handle (swap z)", dict(B, m1_z=0.155, m2_z=0.105))
run("markers 3mm toward +x", dict(B, marker_x=0.003))
run("markers 3mm toward -x", dict(B, marker_x=-0.003))
run("thin flat handle th=5mm", dict(B, body=dict(th=0.005)))
run("deep bowl Db=12mm", dict(B, body=dict(Db=0.012)))
run("short spoon L=0.29", dict(B, body=dict(L=0.29)))
run("full spheres", dict(B, keep_frac=1.0))
run("small coverage .4", dict(B, keep_frac=0.4))
run("asym_y +0.02", dict(B, body=dict(asym_y=0.02)))
