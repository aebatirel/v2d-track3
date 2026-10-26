"""Registered score (vs public mocap; development only) of stored public rollouts with one object's submitted mesh swapped
for one of OUR alternative reconstructions (approach-2 lathe outputs, fitted to our library mesh in its frame)."""
import json, os, shutil, subprocess, sys, concurrent.futures as cf
X, L, KIT, A2 = sys.argv[1:5]
RES = 'https://huggingface.co/datasets/aebatirel/v2d-store/resolve/main/runs'
EPS = {2: ('20261024-e3-e49e83d', ['white_pot', 'white_pot_lid']), 11: ('20261025-twin11v3-0e8aebb', ['beige_cup', 'blue_cup']),
       12: ('20261024-w2-37cc551', ['blue_cup', 'plastic_dish_rack']), 21: ('20261025-twin21arc-ee7ba8e', ['blue_cup', 'water_pitcher']),
       27: ('20261024-w2-37cc551', ['plastic_dish_rack', 'white_pot'])}
CAND = {'blue_cup': ['blue_cup', 'blue_cup_app'], 'white_pot': ['white_pot', 'white_pot_app'], 'water_pitcher': ['water_pitcher', 'water_pitcher_app'],
        'beige_cup': ['beige_cup_v3', 'beige_cup_v3_app']}
LIB = 'meshes/library_v3'
jobs = []
for ep, (run, objs) in EPS.items():
    for i in (1, 2, 3):
        d = f'{X}/ep{ep}/r{i}'; os.makedirs(d, exist_ok=True)
        for x in ('parquet', 'json'):
            f = f'{d}/episode_{ep:06d}.{x}'
            if not os.path.exists(f):
                subprocess.run(['curl', '-sL', '-m', '120', '-o', f, f'{RES}/{run}/results/glock_public/ep{ep}/best/r{i}/episode_{ep:06d}.{x}'])
        variants = [('base', None, None)] + [(f'{o}:{c}', o, c) for o in objs for c in CAND.get(o, [])]
        for tag, o, c in variants:
            m = f'{X}/meshes/{tag.replace(":", "__")}'
            if not os.path.isdir(m):
                os.makedirs(m, exist_ok=True)
                for n in os.listdir(LIB):
                    if n.endswith('.glb'): shutil.copy(f'{LIB}/{n}', m)
                if o: shutil.copy(f'{A2}/{c}.glb', f'{m}/{o}.glb')
            jobs.append((ep, i, tag, d, m))
def score(j):
    ep, i, tag, d, m = j; out = f'{d}/{tag.replace(":", "__")}.json'
    if not os.path.exists(out):
        subprocess.run([sys.executable, 'pipeline/score_registered.py', str(ep), d, '--t3', L, '--kit', KIT, '--meshes', m, '--out', out],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=900)
    try:
        r = json.load(open(out))['sim']; return (ep, i, tag, r['AUC'], r['per_obj_AUC'])
    except Exception:
        return (ep, i, tag, None, None)
with cf.ThreadPoolExecutor(4) as ex:
    R = list(ex.map(score, jobs))
json.dump(R, open(f'{X}/results.json', 'w'))
import collections
agg = collections.defaultdict(list)
for ep, i, tag, a, po in R:
    if a is not None: agg[(ep, tag)].append(a)
for ep in EPS:
    base = sum(agg[(ep, 'base')]) / max(len(agg[(ep, 'base')]), 1)
    print(f'ep{ep}: base {base:.3f} ' + ' | '.join(f'{t}: {sum(v)/len(v):.3f} ({sum(v)/len(v)-base:+.3f})' for (e, t), v in sorted(agg.items()) if e == ep and t != 'base'))
