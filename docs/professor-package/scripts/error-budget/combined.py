"""Combined hypothetical pipelines and leave-one-out attribution (which fix buys most)."""
import numpy as np
from common import *
import budget as B

R = 8


def compose(parts):
    def f(p, rng, e):
        for _, g in parts:
            p = g(p, rng, e)
        return p
    return f


SCEN = {
    "A: careful stereo": [("anchor 0.5cm", B.anchor_trans(0.5)), ("anchor rot 2deg", B.anchor_rot(2)),
                          ("jitter 0.5cm", B.jitter(0.5, anchor=False)), ("rot jitter 2deg", B.jitter(0, rot_deg=2)),
                          ("drift 2cm", B.drift(2)), ("scale 1%", B.scale(0.01)), ("body rot 5deg s1", B.body_offset(rot_deg=5))],
    "B: rough mono/learned": [("anchor 1.5cm", B.anchor_trans(1.5)), ("anchor rot 5deg", B.anchor_rot(5)),
                              ("jitter 1cm", B.jitter(1.0, anchor=False)), ("rot jitter 3deg", B.jitter(0, rot_deg=3)),
                              ("drift 5cm", B.drift(5)), ("scale 10%", B.scale(0.10)), ("lag 2fr", B.lag(2)),
                              ("body rot 15deg s1", B.body_offset(rot_deg=15))],
}
print(f"{'scenario / leave-one-out':40s} {'AUC':>6} {'SP-SR':>6} {'MP-SR':>6} {'RPE':>6} {'MPPE':>6}")
for name, parts in SCEN.items():
    m, _ = B.run(compose(parts), R)
    print(f"{name:40s} {m['AUC']:6.3f} {m['SPSR']:6.2f} {m['MPSR']:6.2f} {m['RPE']:6.2f} {m['MPPE']:6.2f}")
    for i, (lab, _) in enumerate(parts):
        m2, _ = B.run(compose(parts[:i] + parts[i+1:]), R)
        print(f"{'  without ' + lab:40s} {m2['AUC']:6.3f} {m2['SPSR']:6.2f} {m2['MPSR']:6.2f} {m2['RPE']:6.2f} {m2['MPPE']:6.2f}", flush=True)
