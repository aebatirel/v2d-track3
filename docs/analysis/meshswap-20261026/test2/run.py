import json, os, shutil, subprocess, sys, collections, concurrent.futures as cf
X, L, KIT = sys.argv[1:4]; RES = 'https://huggingface.co/datasets/aebatirel/v2d-store/resolve/main/runs'
EPS = {24: ('20261024-ev3-2c1e4dd', {'wooden_piece_1': ['library_v4'], 'wooden_piece_2': ['library_v4']}),
       18: ('20261024-ev3-2c1e4dd', {'mini_sweeper': ['library_v3'], 'mini_dust_pan': ['library_v1']}),
       31: ('20261024-ev30rp-07eef1a', {'mini_sweeper': ['library_v3']})}
BASE = 'meshes/library_v2'                                   # these runs used the default library (v2)
jobs = []
for ep, (run, cand) in EPS.items():
    for i in (1, 2, 3):
        d = f'{X}/ep{ep}/r{i}'; os.makedirs(d, exist_ok=True)
        for x in ('parquet', 'json'):
            f = f'{d}/episode_{ep:06d}.{x}'
            if not os.path.exists(f): subprocess.run(['curl', '-sL', '-m', '120', '-o', f, f'{RES}/{run}/results/glock_public/ep{ep}/best/r{i}/episode_{ep:06d}.{x}'])
        for tag, o, lib in [('base', None, None)] + [(f'{o}:{lib}', o, lib) for o, libs in cand.items() for lib in libs]:
            m = f'{X}/meshes/{tag.replace(":", "__")}'
            if not os.path.isdir(m):
                os.makedirs(m); [shutil.copy(f'{BASE}/{n}', m) for n in os.listdir(BASE) if n.endswith('.glb')]
                if o: shutil.copy(f'meshes/{lib}/{o}.glb', f'{m}/{o}.glb')
            jobs.append((ep, i, tag, d, m))
def score(j):
    ep, i, tag, d, m = j; out = f'{d}/{tag.replace(":", "__")}.json'
    if not os.path.exists(out):
        subprocess.run([sys.executable, 'pipeline/score_registered.py', str(ep), d, '--t3', L, '--kit', KIT, '--meshes', m, '--out', out], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=900)
    try: r = json.load(open(out))['sim']; return (ep, i, tag, r['AUC'], r['per_obj_AUC'])
    except Exception: return (ep, i, tag, None, None)
with cf.ThreadPoolExecutor(4) as ex: R = list(ex.map(score, jobs))
json.dump(R, open(f'{X}/results.json', 'w')); agg = collections.defaultdict(list)
for ep, i, tag, a, po in R:
    if a is not None: agg[(ep, tag)].append(a)
for ep in EPS:
    b = agg[(ep, 'base')]; base = sum(b) / max(len(b), 1)
    print(f'ep{ep}: base {base:.3f} (n {len(b)}) ' + ' | '.join(f'{t}: {sum(v)/len(v):.3f} ({sum(v)/len(v)-base:+.3f})' for (e, t), v in sorted(agg.items()) if e == ep and t != 'base'))
