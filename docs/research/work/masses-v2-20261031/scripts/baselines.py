"""Masses v2 baseline table (31 Oct 2026, written before any Masses v2 run): every public episode, every measured
grasp-lock rollout baseline on our meshes (registered ADD-AUC vs mocap, a PAST public-episode score: allowed for the
selection), its run, recipe, reference and whether mass_check.sh can reuse that reference. Values are copied from the
runs' job.log RESULT lines (store runs/<run>/job.log, read once each; the line timestamps are given) and from committed
results. 'sd' is the population sd glock_public.sh logs (np.std), except where marked. Writes baselines.json.
Eligibility (PREREG.md section 3): see ELIG below. Nothing here reads ground truth beyond those past scores."""
import json, os, sys

FROZEN_GL = '--single_hand 1 --mcp_first 1 --close 10 --palm_clear -0.001 --wrap_where_held 1 --snap 1 --approach_cm 15 --onset_anchor 1'
EP_META = {0: ('Pot_with_lid', 373, 'white_pot, white_pot_lid'), 2: ('Pot_with_lid', 343, 'white_pot, white_pot_lid'),
           11: ('Cup_Stack', 137, 'blue_cup, beige_cup'), 12: ('Cup_In_Dish_Rack', 181, 'blue_cup, plastic_dish_rack'),
           13: ('Cup_In_Dish_Rack', 190, 'blue_cup, plastic_dish_rack'), 18: ('Dust_Brush', 353, 'mini_sweeper, mini_dust_pan'),
           21: ('Water_Can_Blue_Cup', 186, 'blue_cup, water_pitcher'), 22: ('Water_Can_Blue_Cup', 189, 'blue_cup, water_pitcher'),
           23: ('Planter_Stand', 325, 'wooden_piece_1, wooden_piece_2'), 24: ('Planter_Stand', 275, 'wooden_piece_1, wooden_piece_2'),
           26: ('Pan_In_Dishrack', 158, 'plastic_dish_rack, white_pot'), 27: ('Pan_In_Dishrack', 246, 'plastic_dish_rack, white_pot'),
           31: ('Brush_Dishrack', 290, 'mini_sweeper, plastic_dish_rack'), 39: ('Dustpan_Solo', 319, 'mini_dust_pan'),
           40: ('Dustpan_Solo', 260, 'mini_dust_pan'), 41: ('Pan_Solo', 299, 'white_pot'), 42: ('Pan_Solo', 257, 'white_pot'),
           43: ('Pan_Solo', 326, 'white_pot'), 44: ('Pan_Solo', 249, 'white_pot'), 45: ('Pan_Solo', 290, 'white_pot')}
# reference-level context only (NOT a selection input): Phase-1 P_o track vs mocap, library_v3 registration
# (docs/research/work/leak-decomp-20261030/phase1/RESULTS.md, "Per episode", column "P_o lib")
PO_LIB = {0: 0.9620, 2: 0.9866, 11: 0.8978, 12: 0.9662, 13: 0.9595, 18: 0.9144, 21: 0.8325, 22: 0.8707, 23: 0.0414, 24: 0.8117,
          26: 0.9717, 27: 0.9605, 31: 0.7998, 39: 0.9602, 40: 0.9570, 41: 0.9910, 42: 0.9903, 43: 0.9477, 44: 0.9967, 45: 0.9795}


def R(run, code, date, mean, sd, mn, mx, n, ck, recipe, ref, lib='library_v3', seeds='42', curve_rep=3, src='', elig=None, why=''):
    return dict(run=run, code=code, date=date, auc_mean=mean, auc_sd=sd, auc_min=mn, auc_max=mx, n=n, chosen_checkpoint=ck,
                seeds=seeds, learner='grasp-lock (glock_public.sh: 70,004,736-step FlashSAC fine-tune, FDR + VOC, kp 400)',
                curve_rep=curve_rep, reference_recipe=recipe, reference=ref, lib=lib, mass='0.3 kg placeholder',
                source=src, eligible=elig, why=why)


FZ = f'frozen: SF 1, REPLAN 0, EVOLVE 1, GL_ARGS [{FROZEN_GL}]'
NF = 'SF 1, REPLAN 1, EVOLVE 0, GL_ARGS without --onset_anchor (eval_both-style)'
RUNS = {
    2: [R('20261031-mass-2ed46ea', '2ed46ea', '2026-10-31', 0.5665, None, 0.1524, 0.9731, 20, 's42 70M / s43 60M',
          FZ + ' (built on that box)', 'runs/20261031-mass-2ed46ea/refs/glockt/ep2 (md5 ae4dbde8)', seeds='42, 43 (seed mean of 2 x 10)',
          src='docs/research/work/masses-transfer-20261031/results/summary.json, arm mass0', elig=False, why='excluded by the owner (ep2)')],
    11: [R('20261025-twin11v3-0e8aebb', '0e8aebb', '2026-10-25', 0.5249, 0.0043, 0.5164, 0.5278, 5, 'policy_40001536', FZ,
           'runs/20261025-twin11v3-0e8aebb/refs/glockt/ep11 (base perc2mck, assets refs/sf/ep11)',
           src='job.log 2026-10-25T03:39:36Z', elig=True, why='frozen recipe, library_v3, reusable stored reference'),
         R('20261025-twin11v3x-0e8aebb', '0e8aebb', '2026-10-25', 0.5696, 0.0014, 0.5668, 0.5703, 5, 'policy_70004736', FZ,
           'runs/20261025-twin11v3x-0e8aebb/refs/glockt/ep11', lib='library_v3x (v5 beige cup)', src='job.log 2026-10-25T04:27:40Z',
           elig=False, why='library_v3x, not library_v3'),
         R('20261030-orcB-38234d1 (arm P)', '38234d1', '2026-10-30', 0.5951, 0.0001, 0.5947, 0.5951, 10, 'policy_20000768',
           'gl10A2: SF 0, REPLAN 1, EVOLVE 0', 'runs/20261030-orcB-38234d1/refs/glockt/ep11 (names /content/assets_ev10)',
           lib='library_v3 + carve pieces meshes/carve/ev10', src='job.log 2026-10-30T18:52:20Z (static floor 0.5951)', elig=False,
           why='carve pieces ev10 (not library_v3); asset root /content/assets_ev10 is not a stored refs/sf copy, so mass_check.sh cannot reuse it')],
    12: [R('20261031-mass-2ed46ea', '2ed46ea', '2026-10-31', 0.9237, None, 0.8805, 0.9541, 20, 's42 60M / s43 40M', FZ,
           'runs/20261024-ev2-2c1e4dd/refs/glockt/ep12 (md5 c08eaf3f)', seeds='42, 43 (seed mean of 2 x 10)',
           src='docs/research/work/masses-transfer-20261031/results/summary.json, arm mass0', elig=False, why='excluded by the owner (ep12)'),
         R('20261029-rcA-34bf6ae', '34bf6ae', '2026-10-30', 0.9117, 0.0332, 0.8672, 0.9456, 5, 'policy_50003968', FZ + ' (ev2 reference reused)',
           'runs/20261024-ev2-2c1e4dd/refs/glockt/ep12', src='job.log 2026-10-30T01:17:36Z', elig=False, why='excluded by the owner (ep12)'),
         R('20261024-ev2-2c1e4dd', '2c1e4dd', '2026-10-24', 0.8680, 0.1215, 0.6255, 0.9420, 5, 'policy_40001536', FZ,
           'runs/20261024-ev2-2c1e4dd/refs/glockt/ep12', src='job.log 2026-10-24T11:01:36Z', elig=False, why='excluded by the owner (ep12)')],
    13: [R('20261030-orcB-38234d1 (arm P)', '38234d1', '2026-10-30', 0.5428, 0.0008, 0.5416, 0.5444, 10, 'policy_60002304',
           NF + ' (eval 14 packed reference recipe, evb1420)', 'runs/20261030-orcB-38234d1/refs/glockt/ep13 (base perc2mck, assets refs/sf/ep13)',
           src='job.log 2026-10-30T17:05:23Z (static floor 0.5416; arm O with the true motion 0.5437)', elig=True,
           why='current code and training recipe, library_v3, reusable stored reference (no frozen-recipe reference exists for ep13)')],
    18: [R('20261024-ev3-2c1e4dd', '2c1e4dd', '2026-10-24', 0.9573, 0.0023, 0.9544, 0.9596, 5, 'policy_70004736', FZ,
           'runs/20261024-ev3-2c1e4dd/refs/glockt/ep18 (base fdr43 perc2mckfid)', src='job.log 2026-10-24T11:23:18Z', elig=True, why='frozen recipe')],
    21: [R('20261025-twin21arc-ee7ba8e', 'ee7ba8e', '2026-10-25', 0.7723, 0.0092, 0.7655, 0.7903, 5, 'policy_70004736',
           NF + ', SF_ARC=1 (arc foot, adopted; the support_fill.py default since)', 'runs/20261025-twin21arc-ee7ba8e/refs/glockt/ep21',
           src='job.log 2026-10-25T16:22:49Z', elig=True, why='current support-fill default, library_v3, reusable stored reference'),
         R('20261025-twin21base-ee7ba8e', 'ee7ba8e', '2026-10-25', 0.6565, 0.0931, 0.4714, 0.7214, 5, 'policy_70004736', NF + ', SF_ARC=0',
           'runs/20261025-twin21base-ee7ba8e/refs/glockt/ep21', src='job.log 2026-10-25T15:55:17Z', elig=False,
           why='SF_ARC=0 was the control arm of the arc-foot test, superseded by the adopted default SF_ARC=1'),
         R('20261024-e2-e49e83d', 'e49e83d', '2026-10-23', 0.281, 0.012, None, None, 5, '30M', 'E-run: approach 6 cm, REPLAN 1, no onset anchor, no search',
           'runs/20261024-e2-e49e83d/refs/glockt/ep21', curve_rep=1, src='docs/work-log.md 23 Oct 23:30 UTC', elig=False,
           why='before the frozen recipe (code before 2c1e4dd); one evaluation per checkpoint')],
    24: [R('20261024-ev3-2c1e4dd', '2c1e4dd', '2026-10-24', 0.2406, 0.1246, 0.0897, 0.3674, 5, 'policy_50003968', FZ,
           'runs/20261024-ev3-2c1e4dd/refs/glockt/ep24 (base auto24 perc2mcs, assets refs/sf/ep24)', src='job.log 2026-10-24T12:00:47Z',
           elig=True, why='frozen recipe, library_v3, reusable stored reference')],
    26: [R('20261024-w1-37cc551', '37cc551', '2026-10-23', 0.3827, 0.1305, 0.2164, 0.5370, 5, 'policy_10002432',
           'pre-frozen: SF 1, REPLAN 1 (kept: the pot is ejected at the start), no search, GL_ARGS without --onset_anchor',
           'runs/20261024-w1-37cc551/refs/glockt/ep26', lib='library_v4 (pot and rack glb md5-identical to library_v3)', curve_rep=1,
           src='job.log 2026-10-23T23:22:01Z', elig=False,
           why='code 37cc551 before the frozen recipe; checkpoint chosen on ONE evaluation per checkpoint (CURVE_REP 3 came after this run)')],
    27: [R('20261024-ev2-2c1e4dd', '2c1e4dd', '2026-10-24', 0.9489, 0.0099, 0.9303, 0.9590, 5, 'policy_70004736', FZ,
           'runs/20261024-ev2-2c1e4dd/refs/glockt/ep27 (base auto18)', src='job.log 2026-10-24T10:57:46Z', elig=True, why='frozen recipe')],
    31: [R('20261024-ev30rp-07eef1a', '07eef1a', '2026-10-25', 0.6951, 0.1218, 0.4534, 0.7754, 5, 'policy_60002304', FZ + ', DET_REPROP=1 (now default)',
           'runs/20261024-ev30rp-07eef1a/refs/glockt/ep31 (base perc2mck, assets refs/sf/ep31)', src='job.log 2026-10-25T00:24:38Z',
           elig=True, why='frozen recipe, library_v3, reusable stored reference (preferred: frozen)'),
         R('20261030-orcB-38234d1 (arm P)', '38234d1', '2026-10-30', 0.7830, 0.0420, 0.6941, 0.8468, 10, 'policy_60002304', NF,
           'runs/20261030-orcB-38234d1/refs/glockt/ep31', src='job.log 2026-10-30T15:49:01Z', elig=True,
           why='eligible but not used: a frozen-recipe reference with a baseline exists (rule step 3)'),
         R('20261024-e2-e49e83d', 'e49e83d', '2026-10-23', 0.767, 0.016, None, None, 5, '70M', 'E-run (pre-frozen)', 'runs/20261024-e2-e49e83d/refs/glockt/ep31',
           curve_rep=1, src='docs/work-log.md 23 Oct 23:30 UTC', elig=False, why='before the frozen recipe')],
    39: [R('20261024-ev3-2c1e4dd', '2c1e4dd', '2026-10-24', 0.9579, 0.0019, 0.9547, 0.9604, 5, 'policy_60002304', FZ,
           'runs/20261024-ev3-2c1e4dd/refs/glockt/ep39 (base e3 perc2mck)', src='job.log 2026-10-24T11:08:00Z', elig=True, why='frozen recipe')],
}
NOREF = {0: 'refs/perc2{,g,v}/ep0 of 20261020-refsweep-ea14fdf only (20 Oct perception, before the hands / mkref / contact-retarget '
            'pipeline of 21-22 Oct): no finished grasp-lock reference, no base the frozen recipe builds from',
         22: 'refsweep (20 Oct) only', 23: 'refsweep (20 Oct) only; the tracks swap the two boards (P_o 0.04: a perception failure)',
         40: 'refsweep (20 Oct) only', 41: 'refsweep (20 Oct) only', 42: 'refsweep (20 Oct) only', 43: 'refsweep (20 Oct) only',
         44: 'refsweep (20 Oct) only', 45: 'refsweep (20 Oct) only'}
rows = []
for e, (task, frames, objs) in EP_META.items():
    runs = RUNS.get(e, [])
    el = [r for r in runs if r['eligible']]
    pick = None
    if el:
        fz = [r for r in el if r['reference_recipe'].startswith('frozen')]
        pick = (fz or sorted(el, key=lambda r: r['date'], reverse=True))[0]
    excl = 'owner: not ep2 or ep12' if e in (2, 12) else None
    rows.append(dict(episode=e, task=task, frames=frames, objects=objs, excluded=excl,
                     baseline=None if (pick is None or excl) else dict(auc=pick['auc_mean'], n=pick['n'], run=pick['run'],
                                                                       reference_recipe=pick['reference_recipe'], reference=pick['reference'],
                                                                       date=pick['date'], seeds=pick['seeds']),
                     no_baseline_reason=None if runs or excl else 'no grasp-lock rollout on this episode, ever',
                     stored_reference_note=NOREF.get(e), runs=runs, po_lib_track_context=PO_LIB[e]))
rank = sorted([r for r in rows if r['baseline']], key=lambda r: (r['baseline']['auc'], -r['baseline']['n'], r['episode']))
for i, r in enumerate(rank):
    r['rank'] = i + 1
chosen = [r['episode'] for r in rank[:4]]
out = dict(written='2026-10-31 (UTC), before any Masses v2 run', rule='PREREG.md section 3', public_split=sorted(EP_META),
           ranking=[(r['episode'], r['baseline']['auc'], r['baseline']['n'], r['baseline']['run']) for r in rank], chosen=chosen,
           episodes=rows)
json.dump(out, open(sys.argv[1], 'w'), indent=1)
print('ranking', out['ranking']); print('chosen', chosen)
