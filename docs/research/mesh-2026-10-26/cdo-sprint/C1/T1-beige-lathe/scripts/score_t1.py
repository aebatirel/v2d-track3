"""ONE pre-registered mesh_metric scoring of the T1 beige-cup lathe (diagnostic [D], public scan as stand-in).
Calls mesh_metric.evaluate() once: the 2 eval seeds (eval 8 slot 0, eval 10 slot 1) + 30 extra seeds
(11, 22, 33, 44 = the baseline record's extras, then 1001..1026), then applies the PREREG gates.
Refuses to run if OUT already holds a record of this mesh (one scoring per distinct mesh).
Usage: MESH_SCR=<scratch> score_t1.py MESH.glb OUT.jsonl
"""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'scripts')))
import mesh_metric as MM  # noqa: E402

path, out = sys.argv[1:3]
sha = MM.sha(path)
if os.path.exists(out) and any(json.loads(l).get('sha') == sha for l in open(out) if l.strip()):
    raise SystemExit(f'{path} (sha1 {sha}) already scored in {out}: refusing a second scoring')
EXTRA = (11, 22, 33, 44) + tuple(range(1001, 1027))
assert len(EXTRA) == 30
rec = MM.evaluate('T1/ep11_beige_cup_sep_g1', 'beige_cup', path, group='cdo_c1_t1', seeds_extra=EXTRA,
                  min_seeds=32, min_extra=30)
rows = rec['seeds']
base6 = [r for r in rows if r['ep'] is not None or r['seed'] in (11, 22, 33, 44)]
rec['add_med6'] = float(np.median([r['add_mm'] for r in base6]))
ev = {r['ep']: r for r in rows if r['ep'] is not None}
G = dict(cdo_ev10=ev[10]['cdo_cm'], cdo_ev8=ev[8]['cdo_cm'], add_med6=rec['add_med6'], add_med32=rec['add_med'],
         flips_all=rec['flips_all'], n_seeds=rec['n_seeds'])
G['win_ev10'] = bool(G['cdo_ev10'] <= 0.856 - 0.02 and G['add_med6'] <= 6.97 + 2.0 and G['flips_all'] == 0)
G['win_ev8'] = bool(G['cdo_ev8'] <= 0.730 - 0.02 and G['add_med6'] <= 6.97 + 2.0 and G['flips_all'] == 0)
G['secondary'] = dict(ev10_vs_seed_base_0p8705=bool(G['cdo_ev10'] <= 0.8705 - 0.02),
                      ev8_vs_seed_base_0p7251=bool(G['cdo_ev8'] <= 0.7251 - 0.02),
                      add_med6_vs_v3x_5p51=bool(G['add_med6'] <= 5.51 + 2.0),
                      add_med32_vs_6p97=bool(G['add_med32'] <= 6.97 + 2.0))
G['H_BL'] = 'survives' if (G['win_ev10'] and G['win_ev8']) else 'falsified'
rec['gates'] = G
with open(out, 'a') as fh:
    fh.write(json.dumps(rec) + '\n')
print(json.dumps({k: rec.get(k) for k in ('label', 'sha', 'cdo_eval', 'cdo_all', 'cdo_sd', 'add_eval', 'add_med',
                                           'add_med6', 'add_max', 'rot_max', 'flips_eval', 'flips_all', 'n_seeds',
                                           'amb_mm', 'secs')}, indent=1))
print(json.dumps(G, indent=1))
