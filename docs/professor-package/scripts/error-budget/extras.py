"""Extra cases: spin about a near-symmetry axis (cups: body z; lid: body x), and SP-SR/MP-SR
of the trivial static predictor per task. Uses budget.metrics (verified == official score)."""
import numpy as np
from common import *
import budget as B

CUPS = {"beige_cup", "blue_cup"}


def spin(slot, axis, deg):
    def f(p, rng, e):
        o = p.copy(); o[:, slot, 3:] = qmul(p[:, slot, 3:], qaxang(np.array(axis, float), np.radians(deg))[None]); return o
    return f


def run_on(eps, f):
    ms = [B.metrics(f(e["pose"], None, e), e["pose"], e["names"]) for e in eps]
    return {k: float(np.mean([m[k] for m in ms])) for k in ms[0]}


cup0 = [e for e in B.EPS if e["names"][0] in CUPS]
lid1 = [e for e in B.EPS if len(e["names"]) > 1 and e["names"][1] == "white_pot_lid"]
print(f"slot-0 cup episodes: {[e['ep'] for e in cup0]}; lid (slot 1) episodes: {[e['ep'] for e in lid1]}")
print(f"{'case':44s} {'AUC':>6} {'SP-SR':>6} {'MP-SR':>6} {'RPE':>6} {'MPPE':>6}")
for d in [10, 30, 90, 180]:
    m = run_on(cup0, spin(0, [0, 0, 1], d))
    print(f"{f'slot0 cup spin {d} deg about body z (5 eps)':44s} {m['AUC']:6.3f} {m['SPSR']:6.2f} {m['MPSR']:6.2f} {m['RPE']:6.2f} {m['MPPE']:6.2f}")
for d in [30, 90, 180]:
    m = run_on(lid1, spin(1, [1, 0, 0], d))
    print(f"{f'slot1 lid spin {d} deg about body x (2 eps)':44s} {m['AUC']:6.3f} {m['SPSR']:6.2f} {m['MPSR']:6.2f} {m['RPE']:6.2f} {m['MPPE']:6.2f}")

print("\nper-episode static predictor (all objects frozen at frame 0):")
for e in B.EPS:
    m = B.metrics(B.drop("all", "start")(e["pose"], None, e), e["pose"], e["names"])
    print(f"  ep {e['ep']:2d} {TASKS[e['ep']]:18s} AUC {m['AUC']:.3f} SP {m['SPSR']:.0f} MP {m['MPSR']:.0f} RPE {m['RPE']:5.2f} MPPE {m['MPPE']:5.2f}")
