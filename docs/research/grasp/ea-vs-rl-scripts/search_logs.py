"""Summarise tools/grasp_evolve.py OUT.json logs (2026-10-24, ea-vs-rl report).
Usage: python -I search_logs.py OUT1.json [OUT2.json ...]
Prints per run: population, generations, evaluations, world-steps, wall-clock, unedited -> best, the generation means,
final sigma, the best edit in physical units, and how many normalised coordinates sit at the +-4 sigma box bound."""
import json, sys
import numpy as np
for f in sys.argv[1:]:
    d = json.load(open(f)); g = d['generations']; lam = d['args']['pop']; K = d['args'].get('robust') or 1
    n_frames = d['window'][1] - d['window'][0]
    th = np.array(d['best']['theta']); sig = np.array(d['sigma']); dim = d['dim']; z = th[:dim] / sig[:dim]
    print(f"{f}\n  object {d['object']} hold {d['hold']} window {d['window']} dim {dim} worlds/gen {lam} robust K {K}")
    print(f"  generations {len(g)}  evaluations {lam * len(g)}  world-steps {lam * len(g) * n_frames}  wall-clock {sum(x['seconds'] for x in g):.0f} s")
    print(f"  unedited {g[0]['unedited']}  best {d['best']['fit']:.4f} (gen {d['best']['gen']})  final sigma {g[-1]['sigma']}")
    print(f"  generation best  {[x['best'] for x in g]}")
    print(f"  generation mean  {[x['mean'] for x in g]}")
    print(f"  best edit: wrist {np.round(th[:3] * 100, 1).tolist()} cm, rpy {np.round(th[3:6], 2).tolist()} rad, |finger| max {np.abs(th[6:]).max():.2f} rad;"
          f" coordinates at the +-4 sigma bound: {int((np.abs(z) >= 3.99).sum())} of {dim}")
if len(sys.argv) == 1:
    print(__doc__)
