"""C0 assembly (CD-O sprint, stage 1): roster.json, MANIFEST.json, cdo_estimate.json, AUC-test mesh dirs and
perception-track conversion. GT-free: reads only repo files, our meshes, the kit roster and our perception tracks
(sweep poses.npz: world_T_cam and cam_T_<obj>, our own inference output). No scan, no parquet, no mocap.

Usage: python -I build_c0.py REPO SCRATCH KIT_DIR
"""
import hashlib
import json
import os
import shutil
import sys

import numpy as np

REPO, SCR, KIT = sys.argv[1:4]
C0 = 'docs/research/mesh-2026-10-26/cdo-sprint/C0'
RES = 'docs/research/mesh-2026-10-26/results'
OUT = f'{SCR}/cdo_c0'


def sha256(p):
    return hashlib.sha256(open(os.path.join(REPO, p) if not os.path.isabs(p) else p, 'rb').read()).hexdigest()


def sha1_16(p):
    return hashlib.sha1(open(os.path.join(REPO, p) if not os.path.isabs(p) else p, 'rb').read()).hexdigest()[:16]


def rec(path, label):
    for line in open(os.path.join(REPO, path)):
        r = json.loads(line)
        if r.get('label') == label:
            return r
    raise SystemExit(f'no record {label} in {path}')


# ---------------------------------------------------------------- the 4 swaps and their score records [D]
SWAPS = {
    'white_pot': dict(
        mesh=f'{RES}/prim/meshes/white_pot_ep41_fit.glb',
        built_as=f'{SCR}/prim/potlid/cand/white_pot_ep41_fit.glb',
        method='kit-of-parts primitive assembly (prim_potlid.py pot --variant fit), fitted to ep41 observed stereo points',
        selection='GT-free obs_fidelity over all pot candidates (results/prim/potlid/selection.json), pre-registered '
                  'in docs/work-log.md 2026-10-27 before scoring',
        score_file=f'{RES}/prim/potlid/metric_all.jsonl', score_label='potlid/fit/ep41',
        flags=[]),
    'white_pot_lid': dict(
        mesh=f'{RES}/prim/meshes/white_pot_lid_ep2_fit_v2.glb',
        built_as=f'{SCR}/prim/clean/lid/t2.5_fit.glb',
        method='kit-of-parts (prim_potlid.py lid --variant fit, PRIM_T_LID=0.0025), fitted to ep2 observed points',
        selection='clean-up round pre-registered in docs/work-log.md 2026-10-27: fidelity picks fit vs tsdf at each '
                  'thickness; shipped default T_LID 2.5 mm (grid midpoint) because all of 1.5/2.5/4.0 passed',
        score_file=f'{RES}/prim/clean/lid_scores.jsonl', score_label='clean/lid/t2.5_fit',
        flags=['T_LID 2.5 mm equals the value that leaked from scan measurements into the first brief (scan lid wall '
               '1.8 mm); the clean-up round passed at 1.5/2.5/4.0 mm (worst 0.224 / 5.06 mm) and 2.5 is kept as the '
               'grid midpoint, not chosen by fidelity (fidelity prefers the thinnest sheet: 1.436 < 1.686 < 2.259)']),
    'plastic_dish_rack': dict(
        mesh=f'{RES}/prim/meshes/plastic_dish_rack_joint_v2.glb',
        built_as=f'{SCR}/prim/clean/rack/t2.5_lean1/plastic_dish_rack/joint_joint.glb',
        method='kit-of-parts (prim_rack.py run, PRIM_T_WALL=0.0025, PRIM_CUP_LEAN=1), joint fit of eps 12/13/27',
        selection='prim_rack GT-free selection (joint) per config; fidelity picks lean (5.935) over upright (6.116) at '
                  '2.5 mm; clean-up round pre-registered 2026-10-27; T_WALL 2.5 mm kept as grid midpoint',
        score_file=f'{RES}/prim/clean/rack_scores.jsonl', score_label='clean/rack/t2.5_lean1/all_joint',
        flags=['T_WALL 2.5 mm equals the scan rack wall median that leaked into the first brief; clean-up round '
               'passed at 1.5/2.5/4.0 mm (worst 0.458 / 6.23 mm); single-seed ADD reaches 6.08 mm at 2.5']),
    'blue_cup': dict(
        mesh=f'{C0}/meshes/ep21_blue_cup_g1.glb',
        built_as=f'{SCR}/lathe/ep21_blue_cup_g1.glb',
        method='obs-lathe (lathe_obs.py, hollow + observed appendages by voxel splat, config g1) on ep21 observed points',
        selection='GT-free obs_fidelity over 5 candidates with ep21+ep22 points (results/obs_diag.txt): ep21 4.084 < '
                  'merged 4.234 < ep22 5.788 < library_v3 5.86 < ep22 no-markers 6.628 mm',
        score_file=f'{RES}/lathe_obs.jsonl', score_label='lathe_obs_g/a1/ep21/blue_cup',
        flags=['obs_fidelity.py was written on 26 Oct AFTER the five blue-cup lathes had been scored against the scan '
               '(work log 2026-10-26 ~16:40 UTC); the pick is GT-free but the selector was not pre-registered before '
               'those scores (Spearman 0.5, n=5)',
               'after the kit budget_mesh the mesh is not watertight (11 bodies; raw mesh watertight, 5 bodies); '
               'library_v3 blue_cup is not watertight after budget either; the kit never checks watertightness']),
}
LIB = 'meshes/library_v3'
BASE_REC = {}
for line in open(os.path.join(REPO, f'{RES}/baseline_library.jsonl')):
    r = json.loads(line)
    BASE_REC[r['label']] = r

for o, s in SWAPS.items():
    r = rec(s['score_file'], s['score_label'])
    assert r['sha'] == sha1_16(s['mesh']), (o, r['sha'], sha1_16(s['mesh']))
    assert os.path.exists(s['built_as']) and sha1_16(s['built_as']) == r['sha'], o
    lib = BASE_REC[f'library_v3/{o}']
    assert lib['sha'] == sha1_16(f'{LIB}/{o}.glb'), o
    s['score'] = dict(file=s['score_file'], label=s['score_label'], sha1_16=r['sha'],
                      cdo_eval_cm=round(r['cdo_eval'], 4), add_eval_mm=round(r['add_eval'], 3),
                      flips_all=r['flips_all'],
                      library_v3=dict(cdo_eval_cm=round(lib['cdo_eval'], 4), add_eval_mm=round(lib['add_eval'], 3),
                                      flips_all=lib['flips_all'], sha1_16=lib['sha']))
    s['sha256'] = sha256(s['mesh'])
    s['bytes'] = os.path.getsize(os.path.join(REPO, s['mesh']))

# ---------------------------------------------------------------- roster (kit file) and pack 7
roster = json.load(open(f'{KIT}/data/track_3_evaluation_objects.json'))['episodes']
EP_LIB = {'8': 'meshes/library_v3x'}           # pack 7: EP_LIB 8:library_v3x (beige cup v5); everything else library_v3
pairs = []
for ep, objs in sorted(roster.items(), key=lambda kv: int(kv[0])):
    for slot, o in enumerate(objs):
        lib = EP_LIB.get(ep, LIB)
        p = f'{lib}/{o}.glb'
        pairs.append(dict(eval_episode=int(ep), slot=slot, object=o, pack7_mesh=p, pack7_sha256=sha256(p)))
assert len(pairs) == 36
note8 = ('eval 8 is packed from meshes/library_v3x (EP_LIB); its white_pot is byte-identical to library_v3, its '
         'beige_cup is the v5 rebuild')
json.dump(dict(source=f'{KIT}/data/track_3_evaluation_objects.json (kit roster; object order = slot order)',
               pack7='library_v3 for every pair except eval 8 (library_v3x); focused-pascal-eval-refs-20261031.md',
               note_eval8=note8, n_pairs=len(pairs),
               pairs_per_object={o: sum(p['object'] == o for p in pairs) for o in sorted({p['object'] for p in pairs})},
               pairs=pairs), open(f'{REPO}/{C0}/roster.json', 'w'), indent=1)

# ---------------------------------------------------------------- MANIFEST
TIER = 'tier P1: fitted to our stereo points along library_v3-anchored tracks'
man = []
for p in pairs:
    o = p['object']
    if o in SWAPS:
        s = SWAPS[o]
        man.append(dict(eval_episode=p['eval_episode'], slot=p['slot'], object=o, swapped=True,
                        c0_mesh=s['mesh'], c0_sha256=s['sha256'], source_path=s['built_as'],
                        provenance_tier=TIER + ' (same tier as library_v3)', method=s['method'],
                        selection=s['selection'], public_D=s['score'], flags=s['flags'],
                        replaces=p['pack7_mesh'], replaces_sha256=p['pack7_sha256']))
    else:
        lab = 'library_v3x/beige_cup' if p['pack7_mesh'] == 'meshes/library_v3x/beige_cup.glb' else f'library_v3/{o}'
        r = BASE_REC.get(lab)
        man.append(dict(eval_episode=p['eval_episode'], slot=p['slot'], object=o, swapped=False,
                        c0_mesh=p['pack7_mesh'], c0_sha256=p['pack7_sha256'], source_path=p['pack7_mesh'],
                        provenance_tier='unchanged from pack 7',
                        public_D=None if r is None else dict(file=f'{RES}/baseline_library.jsonl', label=lab,
                                                             cdo_eval_cm=round(r['cdo_eval'], 4),
                                                             add_eval_mm=round(r['add_eval'], 3),
                                                             flips_all=r['flips_all']),
                        note=('wooden_spoon has no public scan; no [D] CD-O' if o == 'wooden_spoon' else None)))
json.dump(dict(candidate='C0', status='assembled, AUC guard pre-registered (PREREG.md), not adopted',
               rule='packed mesh only; simulator copies and rollouts unchanged', n_pairs=len(man),
               n_swapped=sum(m['swapped'] for m in man), swaps={o: dict(mesh=s['mesh'], sha256=s['sha256'],
                                                                         bytes=s['bytes'], source_path=s['built_as'],
                                                                         public_D=s['score'], flags=s['flags'])
                                                                for o, s in SWAPS.items()},
               pairs=man), open(f'{REPO}/{C0}/MANIFEST.json', 'w'), indent=1)

# ---------------------------------------------------------------- CD-O estimate [E] (board model)
lib_cdo = {o: BASE_REC[f'library_v3/{o}']['cdo_eval'] for o in
           ['white_pot', 'white_pot_lid', 'plastic_dish_rack', 'blue_cup', 'beige_cup', 'mini_dust_pan',
            'mini_sweeper', 'water_pitcher', 'wooden_piece_1', 'wooden_piece_2']}
v3x_beige = BASE_REC['library_v3x/beige_cup']['cdo_eval']
nonspoon = [p for p in pairs if p['object'] != 'wooden_spoon']


def pack_cdo(p, c0):
    if c0 and p['object'] in SWAPS:
        return SWAPS[p['object']]['score']['cdo_eval_cm']
    if p['pack7_mesh'] == 'meshes/library_v3x/beige_cup.glb':
        return v3x_beige
    return lib_cdo[p['object']]


s7 = sum(pack_cdo(p, False) for p in nonspoon)
sc0 = sum(pack_cdo(p, True) for p in nonspoon)
s_v3_only = sum(lib_cdo[p['object']] for p in nonspoon)
BOARD = 0.402
spoon = (BOARD * 36 - s7) / 10
per = {}
for o, s in SWAPS.items():
    n = sum(p['object'] == o for p in pairs)
    d = s['score']['cdo_eval_cm'] - s['score']['library_v3']['cdo_eval_cm']
    per[o] = dict(pairs=n, lib_cm=s['score']['library_v3']['cdo_eval_cm'], new_cm=s['score']['cdo_eval_cm'],
                  delta_per_pair_cm=round(d, 4), weighted_delta_sum_cm=round(n * d, 4),
                  board_delta_cm=round(n * d / 36, 4))
tot = sum(v['weighted_delta_sum_cm'] for v in per.values())
est = dict(label='[E] estimate; assumes the hidden eval scans match the public scans and per-pair CD-O equals the '
                 'public-scan CD-O at eval seeds',
           model='board CD-O = pair-weighted mean over 36 eval pairs; spoon CD-O inferred from the board',
           board_pack7_cm=BOARD,
           nonspoon_sum_pack7_cm=round(s7, 4), nonspoon_mean_pack7_cm=round(s7 / 26, 4),
           nonspoon_mean_library_v3_only_cm=round(s_v3_only / 26, 4),
           spoon_inferred_cm=round(spoon, 4),
           spoon_formula='(0.402*36 - nonspoon_sum_pack7)/10',
           per_object=per, total_weighted_delta_cm=round(tot, 4), board_delta_cm=round(tot / 36, 4),
           board_c0_cm=round(BOARD + tot / 36, 4),
           check_board_c0_from_sums_cm=round((sc0 + 10 * spoon) / 36, 4),
           adopted_subsets_cm={k: round(BOARD + sum(per[o]['weighted_delta_sum_cm'] for o in k.split('+')) / 36, 4)
                               for k in ['white_pot', 'white_pot_lid', 'plastic_dish_rack', 'blue_cup',
                                         'white_pot+white_pot_lid+plastic_dish_rack',
                                         'white_pot+white_pot_lid+plastic_dish_rack+blue_cup']})
json.dump(est, open(f'{REPO}/{C0}/cdo_estimate.json', 'w'), indent=1)
print(json.dumps({k: est[k] for k in ('nonspoon_mean_pack7_cm', 'nonspoon_mean_library_v3_only_cm',
                                      'spoon_inferred_cm', 'board_delta_cm', 'board_c0_cm')}))
for o, v in per.items():
    print(o, v)

# ---------------------------------------------------------------- mesh dirs for the AUC test
PUBLIC = ['beige_cup', 'blue_cup', 'mini_dust_pan', 'mini_sweeper', 'plastic_dish_rack', 'water_pitcher',
          'white_pot', 'white_pot_lid', 'wooden_piece_1', 'wooden_piece_2']


def fill(d, swaps):
    os.makedirs(d, exist_ok=True)
    for o in PUBLIC:
        src = os.path.join(REPO, SWAPS[o]['mesh'] if o in swaps else f'{LIB}/{o}.glb')
        shutil.copyfile(src, f'{d}/{o}.glb')
    return {o: hashlib.sha256(open(f'{d}/{o}.glb', 'rb').read()).hexdigest() for o in PUBLIC}


dirs = {'base': fill(f'{OUT}/base', [])}
dirs['c0'] = fill(f'{OUT}/c0', list(SWAPS))
for o in SWAPS:
    dirs[f'single/{o}'] = fill(f'{OUT}/single/{o}', [o])
json.dump(dirs, open(f'{OUT}/mesh_dirs_sha256.json', 'w'), indent=1)

# ---------------------------------------------------------------- perception tracks -> poses_world_vo.npz
TWINS = [0, 2, 11, 12, 13, 21, 22, 26, 27, 31, 41, 42, 43, 44, 45]
trk = {}
for e in TWINS:
    src = f'{SCR}/data/sweep/ep{e}/poses.npz'
    P = np.load(src, allow_pickle=False)
    W = np.asarray(P['world_T_cam'], np.float64)
    names = [k[len('cam_T_'):] for k in P.files if k.startswith('cam_T_')]
    d = f'{OUT}/tracks/ep{e}'
    os.makedirs(d, exist_ok=True)
    np.savez(f'{d}/poses_world_vo.npz', **{n: np.einsum('tij,tjk->tik', W, np.asarray(P[f'cam_T_{n}'], np.float64))
                                           for n in names})
    trk[e] = dict(source=src, source_sha256=hashlib.sha256(open(src, 'rb').read()).hexdigest(), objects=names,
                  frames=int(len(W)), out=f'{d}/poses_world_vo.npz',
                  out_sha256=hashlib.sha256(open(f'{d}/poses_world_vo.npz', 'rb').read()).hexdigest())
json.dump(trk, open(f'{OUT}/tracks/tracks.json', 'w'), indent=1)
print('dirs', {k: len(v) for k, v in dirs.items()}, 'tracks', len(trk))
