"""Grasp / lift windows of a reference for the lift-window training starts (2026-11-02, perfect-following lane;
docs/research/work/pf-lift-20261102/PREREG.md). GT-free: hold phases of OUR reference (pipeline/hold_phases.py: MANO
contacts + the object track). Prints "a-b,c-d,..." with one window [start - BEFORE, start + AFTER] per hold phase (merged
when they overlap), clipped to 1 .. T-2. Usage: lift_windows.py REF.parquet [--before 5] [--after 15]"""
import argparse, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'pipeline'))
from hold_phases import hold_phases
ap = argparse.ArgumentParser(); ap.add_argument('ref'); ap.add_argument('--before', type=int, default=5); ap.add_argument('--after', type=int, default=15)
a = ap.parse_args()
h = hold_phases(a.ref)[0]; T = h['frames']
w = sorted((max(1, p['start'] - a.before), min(T - 2, p['start'] + a.after)) for p in h['phases'])
m = []
for x, y in w:
    if m and x <= m[-1][1] + 1: m[-1] = (m[-1][0], max(m[-1][1], y))
    else: m.append((x, y))
if not m: sys.exit('no hold phase')
print(','.join(f'{x}-{y}' for x, y in m))
