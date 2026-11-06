"""Assemble the showcase video for one episode from the phase-1 runs (2026-11-06).
For every robot found in the runs' results/showcase/ep<EP>_<robot>/: download summary.json + policy_trace.npz (the
physics replay of the trained policy, evaluator-style), re-render it on CPU with showcase/tools/render_style.py (styled
look, fixed camera), and compose the grid with showcase/tools/grid_video.py next to the real head-camera clip.
  assemble.py --ep 27 --runs RUN_A RUN_B ... --out DIR [--fc FLASHCHORD_DIR] [--real VIDEO] [--order r1,r2,...]
Needs: /content/refs/sc/ep<EP>_<robot> (the references the policies were trained on), the prepared robots in
/content/showcase/robots and the embodiment configs installed in FLASHCHORD_DIR (showcase/install_fc.sh).
Every tile is a physics rollout; the score line comes from the 5 official evaluations scored against mocap.
"""
import argparse, glob, json, os, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
p = argparse.ArgumentParser(); p.add_argument('--ep', type=int, default=27); p.add_argument('--runs', nargs='+', required=True)
p.add_argument('--out', required=True); p.add_argument('--fc', required=True); p.add_argument('--real', default='')
p.add_argument('--store', default='aebatirel/v2d-store'); p.add_argument('--order', default='sharpa,shadow,inspire,allegro,leap,dex3,barrett,dclaw,panda')
p.add_argument('--eye', default='0.50,-1.20,1.30'); p.add_argument('--target', default='-0.08,-0.12,0.80')
p.add_argument('--title', default=''); p.add_argument('--skip_render', action='store_true')
p.add_argument('--objects_dir', default='/content/showcase/objects_clean', help='clean closed meshes for rendering (showcase/tools/clean_meshes.py); empty = official scans')
p.add_argument('--ego', default='', help='REFDIR,PERCDIR: render every tile from the head-camera path (render_style.py --ego)')
p.add_argument('--tag', default='', help='suffix for tile / grid file names')
a = p.parse_args()
os.makedirs(a.out, exist_ok=True); dl = os.path.join(a.out, 'dl')

from huggingface_hub import snapshot_download
for run in a.runs:
    snapshot_download(a.store, repo_type='dataset', local_dir=dl, token=os.environ.get('HF_TOKEN', 'hf_dummy0000000000000000000000000000'),
                      allow_patterns=[f'runs/{run}/results/showcase/ep{a.ep}_*/summary.json', f'runs/{run}/results/showcase/ep{a.ep}_*/policy_trace.npz',
                                      f'runs/{run}/results/showcase/ep{a.ep}_*/view.mp4', f'runs/{run}/results/showcase/ep{a.ep}_*/selection.json'])
found = {}
for d in glob.glob(f'{dl}/runs/*/results/showcase/ep{a.ep}_*'):
    r = os.path.basename(d).split('_', 1)[1]
    if os.path.exists(f'{d}/summary.json'):
        found[r] = d
print('robots with results:', sorted(found))
import re
EMB = {'sharpa': 'sharpa_hands_mid'}
SPEC = {'sharpa': ('Sharpa Wave', 5, 22)}
NOTE = {'panda_pads': 'rubber pads', 'panda_pads_wide': 'wide soft pads'}


def base_of(tag):
    """robot model behind a result tag: ep27_<robot>[_<variant>][_s<seed>] (variants: showcase/prep_robots.py VARIANTS)"""
    t = re.sub(r'_s\d+$', '', tag)
    while t and not os.path.exists(f'/content/showcase/robots/{t}/robot.json') and t != 'sharpa':
        t = t.rsplit('_', 1)[0] if '_' in t else ''
    return t or tag


for r in found:
    if r in SPEC:
        continue
    b = base_of(r); EMB.setdefault(r, re.sub(r'_s\d+$', '', r))
    j = json.load(open(f'/content/showcase/robots/{b}/robot.json'))
    lab = j['label'] + (f" + {NOTE[EMB[r]]}" if EMB[r] in NOTE else '')
    SPEC[r] = (lab, j['fingers'], len(j['sides']['right']['joints']))
tiles, table = [], []
order = [x for x in a.order.split(',') if x in found]
for r in order + sorted(set(found) - set(order)):
    d = found[r]; s = json.load(open(f'{d}/summary.json'))
    pq = glob.glob(f'/content/refs/sc/ep{a.ep}_{base_of(r)}/processed/*/*/*.parquet')[0]
    tile = os.path.join(a.out, f'tile_{r}{a.tag}.mp4')
    if r in order and not a.skip_render and os.path.exists(f'{d}/policy_trace.npz') and not os.path.exists(tile):
        subprocess.run(['xvfb-run', '-a', '-s', '-screen 0 1280x1024x24', f'{a.fc}/.venv/bin/python', f'{HERE}/render_style.py', pq, tile,
                        '--emb', EMB.get(r, r), '--trace', f'{d}/policy_trace.npz', '--size', '772x680', f'--eye={a.eye}', f'--target={a.target}'] + (['--objects_dir', a.objects_dir] if a.objects_dir else []) + (['--ego', a.ego] if a.ego else []),
                       cwd=a.fc, check=False)
    n, auc, sd, mp = s['n'], s['auc_mocap_mean'], s['auc_mocap_sd'], s['mp_sr_pass']
    pot = [x['per_obj'] for x in s['draws']]
    score = f'AUC {auc:.2f} vs mocap | {mp}/{n} runs within 3 cm' if n else 'no scored runs'
    table.append(dict(robot=r, in_video=r in order, label=SPEC[r][0], fingers=SPEC[r][1], joints=SPEC[r][2], n=n, auc_mocap_mean=auc, auc_mocap_sd=sd,
                      mp_sr_pass=mp, draws=s['draws'], checkpoint=s['checkpoint']))
    if r in order and os.path.exists(tile):
        tiles.append(dict(video=tile, name=SPEC[r][0], spec=f'{SPEC[r][1]} fingers, {SPEC[r][2]} joints', score=score))
json.dump(table, open(os.path.join(a.out, 'results_table.json'), 'w'), indent=1)
json.dump(tiles, open(os.path.join(a.out, f'tiles{a.tag}.json'), 'w'), indent=1)
for t in table:
    print(f"{t['label']:<32} {t['fingers']} fingers {t['joints']:>2} joints  AUC vs mocap {t['auc_mocap_mean']} ± {t['auc_mocap_sd']}  MP pass {t['mp_sr_pass']}/{t['n']}")
if tiles and a.real:
    subprocess.run(['python3', f'{HERE}/grid_video.py', os.path.join(a.out, f'grid_ep{a.ep}{a.tag}.mp4'), '--real', a.real,
                    '--tiles', os.path.join(a.out, f'tiles{a.tag}.json'), '--title', a.title or f'One head-camera video, {len(tiles)} robot hands, each a trained policy in physics (ep{a.ep})'], check=True)
