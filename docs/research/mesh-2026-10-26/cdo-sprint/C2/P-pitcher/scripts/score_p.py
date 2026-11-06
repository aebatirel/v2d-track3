"""ONE pre-registered mesh_metric scoring of the C2/P pitcher pick (diagnostic [D], public scan as stand-in).
Calls mesh_metric.evaluate() once: the eval seed (eval 20, slot 1: 20000161) + 31 extra seeds (11, 22, 33, 44, 55 =
the library baseline record's own extras, then 1001..1026), then applies the PREREG gates (PREREG.md section 5).
Refuses to run if OUT already holds a record of this mesh (one scoring per distinct mesh).
Usage: MESH_SCR=<scratch> score_p.py MESH.glb OUT.jsonl
"""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'scripts')))
import mesh_metric as MM  # noqa: E402

L, A = 0.8942, 7.97            # library_v3 water_pitcher [D]: cdo_eval (seed 20000161), add_med over its 6 seeds
path, out = sys.argv[1:3]
sha = MM.sha(path)
if os.path.exists(out) and any(json.loads(l).get('sha') == sha for l in open(out) if l.strip()):
    raise SystemExit(f'{path} (sha1 {sha}) already scored in {out}: refusing a second scoring')
EXTRA = (11, 22, 33, 44, 55) + tuple(range(1001, 1027))
assert len(EXTRA) == 31
rec = MM.evaluate('C2P/' + os.path.basename(path)[:-4], 'water_pitcher', path, group='cdo_c2_p', seeds_extra=EXTRA,
                  min_seeds=32, min_extra=31)
rows = rec['seeds']
base6 = [r for r in rows if r['ep'] is not None or r['seed'] in (11, 22, 33, 44, 55)]
assert len(base6) == 6
rec['add_med6'] = float(np.median([r['add_mm'] for r in base6]))
ev = {r['ep']: r for r in rows if r['ep'] is not None}
G = dict(cdo_ev20=ev[20]['cdo_cm'], add_med6=rec['add_med6'], add_med32=rec['add_med'], flips_all=rec['flips_all'],
         n_seeds=rec['n_seeds'], thr_cdo=round(L - 0.02, 4), thr_add=round(A + 2.0, 2))
G['cdo_ok'] = bool(G['cdo_ev20'] <= L - 0.02 + 1e-9)
G['add_ok'] = bool(G['add_med6'] <= A + 2.0 + 1e-9)
G['flips_ok'] = bool(G['flips_all'] == 0)
G['WIN'] = bool(G['cdo_ok'] and G['add_ok'] and G['flips_ok'])
G['H_P'] = 'survives' if (G['WIN'] and G['cdo_ev20'] <= 0.6 + 1e-9) else 'falsified'
G['secondary'] = dict(add_med32_ok=bool(G['add_med32'] <= A + 2.0 + 1e-9), cdo_all=rec.get('cdo_all'))
rec['gates'] = G
with open(out, 'a') as fh:
    fh.write(json.dumps(rec) + '\n')
print(json.dumps({k: rec.get(k) for k in ('label', 'sha', 'cdo_eval', 'cdo_all', 'cdo_sd', 'add_eval', 'add_med',
                                           'add_med6', 'add_max', 'rot_max', 'flips_eval', 'flips_all', 'n_seeds',
                                           'amb_mm', 'secs')}, indent=1))
print(json.dumps(G, indent=1))
