"""ONE pre-registered mesh_metric scoring of a placed T2 probe pick (diagnostic [D], public scan as stand-in).

The placed copy is the probe-scored SAM 3D mesh moved by a GT-free Sim(3) into the library_v3 frame (place.py). Its
CD-O equals the probe's (kit CD-O normalises scale and registers rigidly); this scoring is for its NEW FRAME:
registration ADD and flips. Calls mesh_metric.evaluate() once: the object's eval seeds + 30 extra seeds
(11, 22, 33, 44, 55 = the baseline records' extras, then 1001..1025), then applies the PREREG gates:
  CD-O (probe, per eval pair) <= baseline - 0.02; add_med (the baseline record's 6 seeds) <= library add_med + 2.0 mm;
  flips 0 over all seeds (beige cup: kit-declared axial symmetry, spin is not a flip).
Refuses to run if OUT already holds a record of this mesh (one scoring per distinct mesh).
Usage: MESH_SCR=<scratch> score_t2.py OBJECT PLACED.glb OUT.jsonl
"""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'scripts')))
import mesh_metric as MM  # noqa: E402

# Pre-registered constants (PREREG.md s3, s5). Probe CD-O per eval episode: results/gen-probe/scores.jsonl [D].
CFG = {
    'water_pitcher': dict(label='T2/sam3d_ep22_water_pitcher_k174_s42_lib', probe_cdo={20: 0.771},
                          base_cdo={20: 0.894}, lib_add_med=7.97, base_extras=(11, 22, 33, 44, 55),
                          lib_seed_cdo={20: 0.8942}),
    'mini_dust_pan': dict(label='T2/sam3d_ep39_mini_dust_pan_k297_s42_lib', probe_cdo={19: 0.2619, 38: 0.2592},
                          base_cdo={19: 0.331, 38: 0.331}, lib_add_med=5.65, base_extras=(11, 22, 33, 44),
                          lib_seed_cdo={19: 0.3274, 38: 0.334}),
    'beige_cup': dict(label='T2/sam3d_ep11_beige_cup_k6_s42_lib', probe_cdo={10: 0.5191, 8: 0.5326},
                      base_cdo={10: 0.856, 8: 0.730}, lib_add_med=6.97, base_extras=(11, 22, 33, 44),
                      lib_seed_cdo={10: 0.8705, 8: 0.7251}),
}
EXTRA = (11, 22, 33, 44, 55) + tuple(range(1001, 1026))
assert len(EXTRA) == 30

obj, path, out = sys.argv[1:4]
c = CFG[obj]
sha = MM.sha(path)
if os.path.exists(out) and any(json.loads(l).get('sha') == sha for l in open(out) if l.strip()):
    raise SystemExit(f'{path} (sha1 {sha}) already scored in {out}: refusing a second scoring')
rec = MM.evaluate(c['label'], obj, path, group='cdo_c1_t2', seeds_extra=EXTRA, min_seeds=0, min_extra=30)
rows = rec['seeds']
assert rec['n_seeds'] == len(c['probe_cdo']) + 30, rec['n_seeds']
base6 = [r for r in rows if r['ep'] is not None or r['seed'] in c['base_extras']]
assert len(base6) == 6
rec['add_med6'] = float(np.median([r['add_mm'] for r in base6]))
ev = {r['ep']: r for r in rows if r['ep'] is not None}
G = dict(add_med6=rec['add_med6'], add_med_all=rec['add_med'], add_thr=round(c['lib_add_med'] + 2.0, 4),
         flips_all=rec['flips_all'], n_seeds=rec['n_seeds'], pairs={})
for e, pc in c['probe_cdo'].items():
    thr = round(c['base_cdo'][e] - 0.02, 4)
    win = bool(pc <= thr + 1e-9 and rec['add_med6'] <= G['add_thr'] + 1e-9 and rec['flips_all'] == 0)
    G['pairs'][e] = dict(probe_cdo=pc, cdo_thr=thr, placed_cdo_recheck=ev[e]['cdo_cm'], add_seed=ev[e]['add_mm'],
                         flip_seed=ev[e]['flip'], win=win,
                         secondary_vs_seed_base=bool(pc <= c['lib_seed_cdo'][e] - 0.02 + 1e-9))
G['win_any'] = any(p['win'] for p in G['pairs'].values())
G['win_all'] = all(p['win'] for p in G['pairs'].values())
rec['gates'] = G
with open(out, 'a') as fh:
    fh.write(json.dumps(rec) + '\n')
print(json.dumps({k: rec.get(k) for k in ('label', 'sha', 'cdo_eval', 'cdo_all', 'cdo_sd', 'add_eval', 'add_med',
                                           'add_med6', 'add_max', 'rot_max', 'flips_eval', 'flips_all', 'n_seeds',
                                           'amb_mm', 'secs')}, indent=1))
print(json.dumps(G, indent=1))
