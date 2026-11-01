"""C1 report: [E] board CD-O on top of C0 (pack 9a), same model as C0/cdo_estimate.json.

Board = pair-weighted mean over the 36 eval pairs. Baseline per pair = the value C0's estimate used for pack 7
(library_v3 cdo_eval; eval-8 beige = library_v3x cdo_eval). New per pair = the adopted mesh's own one-shot [D] CD-O
at that pair's eval seed (score_t1.jsonl / score_t2.jsonl, the scored file is the packed file). Reads only our own
result files; no scoring.

Usage: python -I c1_estimate.py MESH_RESEARCH_DIR OUT.json
"""
import json
import sys

R, OUT = sys.argv[1], sys.argv[2]
SP = f'{R}/cdo-sprint'
c0 = json.load(open(f'{SP}/C0/cdo_estimate.json'))
base = {json.loads(l)['label']: json.loads(l) for l in open(f'{R}/results/baseline_library.jsonl')}


def per_pair(path, sha):
    recs = [json.loads(l) for l in open(path)]
    r = [x for x in recs if x['sha'] == sha]
    assert len(r) == 1, (path, sha, len(r))
    return {s['ep']: s['cdo_cm'] for s in r[0]['seeds'] if s['ep'] is not None}


beige = per_pair(f'{SP}/C1/T1-beige-lathe/results/score_t1.jsonl', '46b06543747faf02')
dust = per_pair(f'{SP}/C1/T2-probe-picks/results/score_t2.jsonl', '3a0c62f390b4646e')
pairs = [
    dict(ep=10, slot=1, object='beige_cup', old_label='library_v3/beige_cup', new=beige[10], src='C1/T1'),
    dict(ep=8, slot=0, object='beige_cup', old_label='library_v3x/beige_cup', new=beige[8], src='C1/T1'),
    dict(ep=19, slot=1, object='mini_dust_pan', old_label='library_v3/mini_dust_pan', new=dust[19], src='C1/T2'),
    dict(ep=38, slot=0, object='mini_dust_pan', old_label='library_v3/mini_dust_pan', new=dust[38], src='C1/T2'),
]
for p in pairs:
    p['old'] = base[p['old_label']]['cdo_eval']
    p['delta_cm'] = round(p['new'] - p['old'], 5)
    p['board_delta_cm'] = round(p['delta_cm'] / 36, 5)


def s(sel):
    return sum(p['delta_cm'] for p in pairs if sel(p)) / 36


b9a = c0['adopted_subsets_cm']['white_pot+white_pot_lid+plastic_dish_rack']
b9a_exact = c0['board_pack7_cm'] + sum(c0['per_object'][o]['weighted_delta_sum_cm']
                                       for o in ('white_pot', 'white_pot_lid', 'plastic_dish_rack')) / 36
bbc = c0['board_pack7_cm'] + c0['total_weighted_delta_cm'] / 36
d_all = s(lambda p: True)
est = dict(label='[E] same assumptions as C0/cdo_estimate.json (hidden scans = public scans; per-pair CD-O = public '
                 'one-shot CD-O at the eval seed)',
           pairs=pairs,
           board_delta_beige_both_cm=round(s(lambda p: p['object'] == 'beige_cup'), 4),
           board_delta_beige_eval10_only_cm=round(s(lambda p: p['ep'] == 10), 4),
           board_delta_beige_eval8_only_cm=round(s(lambda p: p['ep'] == 8), 4),
           board_delta_dust_pan_cm=round(s(lambda p: p['object'] == 'mini_dust_pan'), 4),
           board_delta_c1_cm=round(d_all, 4),
           board_pack7_cm=c0['board_pack7_cm'],
           board_pack9a_cm=round(b9a_exact, 4), board_pack9a_c0_file_cm=b9a,
           board_pack9a_plus_c1_cm=round(b9a_exact + d_all, 4),
           board_pack9a_plus_c1_beige_eval10_only_cm=round(b9a_exact + s(lambda p: p['ep'] != 8), 4),
           board_pack9a_plus_held_blue_cup_plus_c1_cm=round(bbc + d_all, 4),
           board_pack7_plus_c1_only_cm=round(c0['board_pack7_cm'] + d_all, 4))
json.dump(est, open(OUT, 'w'), indent=1)
print(json.dumps(est, indent=1))
