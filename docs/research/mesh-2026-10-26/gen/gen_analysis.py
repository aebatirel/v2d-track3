"""Batch-2 generative probe: results table [D] next to the GT-free metrics, and whether the GT-free metrics would have
picked the best generated mesh per object (2026-10-30). Reads only finished outputs; reads no scan.

Inputs: scores.jsonl (mesh_metric.py, one row per scored mesh), gtfree_scored.jsonl (gen_gtfree.py on the same
meshes), gtfree_library.jsonl, mv_check_final.jsonl (Pixal3D view IoU), the Sim(3) fits.jsonl files, and
baseline_library.jsonl (the library_v3 scores already in the repo).
Usage: gen_analysis.py SCORES GTFREE GTFREE_LIB MVCHECK RESULTS_GEN_DIR BASELINE OUT_DIR
"""
import glob, json, os, sys
from collections import defaultdict
import numpy as np
from scipy.stats import spearmanr

scores_p, gtf_p, gtl_p, mv_p, gen_dir, base_p, out = sys.argv[1:8]
os.makedirs(out, exist_ok=True)
OBJ = ['white_pot', 'white_pot_lid', 'blue_cup', 'water_pitcher', 'wooden_piece_1', 'wooden_piece_2',
       'plastic_dish_rack', 'mini_sweeper', 'mini_dust_pan', 'beige_cup']
EP = dict(white_pot=41, white_pot_lid=2, blue_cup=22, water_pitcher=22, wooden_piece_1=23, wooden_piece_2=23,
          plastic_dish_rack=26, mini_sweeper=31, mini_dust_pan=39, beige_cup=11)
BEST = dict(white_pot=(0.342, 3.05), white_pot_lid=(0.220, 4.46), plastic_dish_rack=(0.456, 5.37), blue_cup=(0.291, 4.1))
MODELS = ['pixal_mv', 'pixal_v1', 'trellis2', 'triposg', 'hy21', 'sam3d']
NAMES = dict(pixal_mv='Pixal3D-MV (posed)', pixal_v1='Pixal3D view 0 only', trellis2='TRELLIS.2', triposg='TripoSG',
             hy21='Hunyuan3D-2.1', sam3d='SAM 3D')

S = {r['label']: r for r in map(json.loads, open(scores_p))}
G = {r['label']: r for r in map(json.loads, open(gtf_p))}
GL = {r['ep_obj']: r for r in map(json.loads, open(gtl_p))}
MV = {}
for l in open(mv_p):
    try:
        r = json.loads(l)
    except json.JSONDecodeError:
        continue
    MV[r['mesh']] = r['mean_iou']
FITS = {}
for p in glob.glob(os.path.join(gen_dir, '*_sim3', 'fits.jsonl')):
    for l in open(p):
        r = json.loads(l)
        FITS[tuple(r['out'].split('/')[-2:])] = r          # (model_sim3, file): box paths differ from local ones
BASE = {r['object']: r for r in map(json.loads, open(base_p)) if r['label'].startswith('library_v3/')}


def cd(r):
    return r['cdo_eval'] if r.get('cdo_eval') is not None else r['cdo_all']


def add(r):
    return r['add_eval'] if r.get('add_eval') is not None else r['add_all']


rows = []
for lab, r in S.items():
    g = G[lab]
    m = r['group']
    seed = int(lab.rsplit('_s', 1)[1])
    fit = FITS.get(tuple(r['path'].split('/')[-2:]))
    mv = None
    if m.startswith('pixal'):
        mv = MV.get(os.path.basename(r['path']))
    rows.append(dict(label=lab, object=r['object'], model=m, seed=seed, cdo=cd(r), add=add(r), flips=r['flips_all'],
                     n_seeds=r['n_seeds'], amb=r.get('amb_mm'), res=('1024' if '_1024' in lab else ''),
                     o2m=g['obs_to_mesh_med_mm'], m2o=g['mesh_to_obs_med_mm'], o2m90=g['obs_to_mesh_p90_mm'],
                     gtf=g['obs_to_mesh_med_mm'] + g['mesh_to_obs_med_mm'], mv_iou=mv,
                     sim3_scale=None if fit is None else fit['scale'], path=r['path']))
json.dump(rows, open(os.path.join(out, 'rows.json'), 'w'), indent=1)

L = []
L.append('# Generative probe, batch 2: one-shot scan scores [D] next to GT-free metrics\n')
L.append('CD-O and ADD are the kit metrics as `mesh_metric.py` computes them (eval-pair seeds), against the PUBLIC scans; '
         'diagnostic only [D]. ADD/flips for the single-image models are those of the Sim(3) copy fitted to our '
         'observed points (GT-free); the raw generator output has the same CD-O (similarity-invariant) and no '
         'meaningful ADD. GT-free = median distance (mm) between the mesh surface and our observed points, '
         'obs->mesh / mesh->obs; library_v3 values in the first column.\n')
L.append('## Per object (CD-O cm, s42 / s7; ADD mm and flips in the detail table)\n')
hdr = '| object | library_v3 | best ours | ' + ' | '.join(NAMES[m] for m in MODELS) + ' |'
L.append(hdr); L.append('|' + '---|' * (3 + len(MODELS)))
summary = defaultdict(list)
for o in OBJ:
    b = BASE[o]
    cells = []
    for m in MODELS:
        rs = sorted([x for x in rows if x['object'] == o and x['model'] == m], key=lambda x: -x['seed'])
        if not rs:
            cells.append('-'); continue
        cells.append(' / '.join(f"{x['cdo']:.3f}{'*' if x['res'] else ''}" for x in rs))
        summary[m].append((o, np.mean([x['cdo'] for x in rs]), min(x['cdo'] for x in rs)))
    best = BEST.get(o)
    L.append(f"| {o} | {cd(b):.3f} | {best[0] if best else '-'} | " + ' | '.join(cells) + ' |')
L.append('\n`*` TRELLIS.2 at 1024 (1536 ran out of memory on this crop).\n')

L.append('## Per model, over the objects it covers\n')
L.append('| model | objects | mean CD-O (seed mean) | mean CD-O library_v3, same objects | objects better than library_v3 (seed mean) | objects better than our best (pot, lid, rack, blue cup) |')
L.append('|---|---|---|---|---|---|')
for m in MODELS:
    v = summary[m]
    if not v:
        continue
    lib = [cd(BASE[o]) for o, _, _ in v]
    better = [o for o, mu, _ in v if mu < cd(BASE[o])]
    bb = [o for o, mu, _ in v if o in BEST and mu < BEST[o][0]]
    L.append(f"| {NAMES[m]} | {len(v)} | {np.mean([mu for _, mu, _ in v]):.3f} | {np.mean(lib):.3f} | "
             f"{len(better)}: {', '.join(better) or '-'} | {', '.join(bb) or '-'} |")

L.append('\n## Detail: every scored mesh\n')
L.append('| object | model | seed | CD-O cm | ADD mm | flips | GT-free obs->mesh / mesh->obs mm (lib) | Pixal view IoU | Sim(3) scale |')
L.append('|---|---|---|---|---|---|---|---|---|')
for o in OBJ:
    gl = GL[f'ep{EP[o]}_{o}']
    b = BASE[o]
    L.append(f"| {o} | library_v3 | - | {cd(b):.3f} | {add(b):.1f} | {b['flips_all']}/{b['n_seeds']} | "
             f"{gl['obs_to_mesh_med_mm']:.2f} / {gl['mesh_to_obs_med_mm']:.2f} | - | - |")
    for x in sorted([x for x in rows if x['object'] == o], key=lambda x: (MODELS.index(x['model']), -x['seed'])):
        L.append(f"| {o} | {NAMES[x['model']]}{' (1024)' if x['res'] else ''} | {x['seed']} | {x['cdo']:.3f} | "
                 f"{x['add']:.1f} | {x['flips']}/{x['n_seeds']} | {x['o2m']:.2f} / {x['m2o']:.2f} | "
                 f"{'-' if x['mv_iou'] is None else round(x['mv_iou'], 3)} | "
                 f"{'-' if x['sim3_scale'] is None else round(x['sim3_scale'], 4)} |")

# GT-free selection: would the GT-free metric (obs->mesh + mesh->obs medians) have picked the best mesh?
L.append('\n## Would the GT-free metric have picked the best mesh? (per object, over its scored generated meshes)\n')
L.append('GT-free score = median obs->mesh + median mesh->obs (mm), lower is better. Spearman rho between the GT-free '
         'score and CD-O over the object\'s generated meshes; pick = the GT-free argmin; regret = its CD-O minus the '
         'best CD-O among the same meshes. "beats lib" asks whether the GT-free pick has lower CD-O than library_v3.\n')
L.append('| object | n | Spearman rho | GT-free pick | its CD-O | best generated (CD-O) | regret | GT-free pick beats library_v3? | GT-free would prefer the pick over library_v3? |')
L.append('|---|---|---|---|---|---|---|---|---|')
sel = []
for o in OBJ:
    rs = [x for x in rows if x['object'] == o]
    gtf = np.array([x['gtf'] for x in rs]); c = np.array([x['cdo'] for x in rs])
    rho = spearmanr(gtf, c).correlation
    pick = rs[int(np.argmin(gtf))]; best = rs[int(np.argmin(c))]
    gl = GL[f'ep{EP[o]}_{o}']; lib_gtf = gl['obs_to_mesh_med_mm'] + gl['mesh_to_obs_med_mm']
    sel.append(dict(object=o, n=len(rs), rho=rho, pick=pick['label'], pick_cdo=pick['cdo'], best=best['label'],
                    best_cdo=best['cdo'], regret=pick['cdo'] - best['cdo'], lib_cdo=cd(BASE[o]),
                    pick_beats_lib=pick['cdo'] < cd(BASE[o]), gtf_prefers_pick=pick['gtf'] < lib_gtf,
                    pick_gtf=pick['gtf'], lib_gtf=lib_gtf))
    s = sel[-1]
    L.append(f"| {o} | {len(rs)} | {rho:.2f} | {pick['label'].split('/', 1)[1]} | {pick['cdo']:.3f} | "
             f"{best['label'].split('/', 1)[1]} ({best['cdo']:.3f}) | {s['regret']:.3f} | "
             f"{'yes' if s['pick_beats_lib'] else 'no'} ({s['lib_cdo']:.3f}) | "
             f"{'yes' if s['gtf_prefers_pick'] else 'no'} ({pick['gtf']:.1f} vs {lib_gtf:.1f} mm) |")
allr = spearmanr([x['gtf'] for x in rows], [x['cdo'] for x in rows]).correlation
rhos = [s['rho'] for s in sel]
top1 = sum(s['pick'] == s['best'] for s in sel)
# rank of the GT-free pick among the object's meshes by CD-O
ranks = []
for s in sel:
    rs = sorted([x for x in rows if x['object'] == s['object']], key=lambda x: x['cdo'])
    ranks.append(1 + [x['label'] for x in rs].index(s['pick']))
L.append(f"\nAll {len(rows)} meshes pooled: Spearman rho(GT-free, CD-O) = {allr:.2f}. Per object: median rho "
         f"{np.median(rhos):.2f} (range {min(rhos):.2f} to {max(rhos):.2f}); the GT-free pick is the CD-O best on "
         f"{top1}/10 objects; its CD-O rank among the object's meshes: {ranks}; mean regret "
         f"{np.mean([s['regret'] for s in sel]):.3f} cm.")
# a GT-free selector over {library_v3, generated}: pick the lower GT-free score
sel_cd = [s['pick_cdo'] if s['gtf_prefers_pick'] else s['lib_cdo'] for s in sel]
L.append(f"A GT-free selector over {{library_v3, best-GT-free generated}} per object would choose generated on "
         f"{sum(s['gtf_prefers_pick'] for s in sel)}/10 objects; mean CD-O {np.mean(sel_cd):.3f} vs library_v3 "
         f"{np.mean([s['lib_cdo'] for s in sel]):.3f} [D].")
json.dump(dict(selection=sel, pooled_rho=allr, ranks=ranks, selector_mean_cdo=float(np.mean(sel_cd)),
               lib_mean_cdo=float(np.mean([s['lib_cdo'] for s in sel]))),
          open(os.path.join(out, 'selection.json'), 'w'), indent=1, default=float)
txt = '\n'.join(L) + '\n'
open(os.path.join(out, 'table.md'), 'w').write(txt)
print(txt)
