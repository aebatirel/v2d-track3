"""Assemble canonical_refs.json (refcheck/resolve, 26 Oct 2026). Choices are made by hand from the evidence written up in
README.md next to this script (job.log / COMMIT / store sha256 / object-path comparisons); this script only fills in
paths, hashes, object names and checks that every chosen file exists locally.
Usage: python -I build_canonical.py STORE_ROOT HASHES_JSON OUT_JSON [OUT_JSON2 ...]"""
import glob, json, os, sys
import numpy as np

S = 'runs/'
E = [  # ep, ref_run, ref_variant, perception dir (under the run), producer perception run, results dir, mesh lib, commit, twin, notes
    dict(ep=0, ref_run='', ref_variant='', perc=('20261025-guard-fe3f407', 'results/sweep/guard'), res='', lib='library_v2 (white_pot / white_pot_lid identical to library_v3)',
         commit='fe3f407', twin='(pot + lid, like eval 1; not stated in docs)',
         notes='NO mkref reference with the current recipe. Newest perception = guard A/B arm (TRACK_GUARD=1, on-table rule, gated re-proposal, compact prior, Grounding DINO on; library_v2 templates); lid recovered at frame 0 by the guard (1 f0 retry). Box-stored registered perception AUC 0.964 (library_v2). Stale reference: runs/20261020-refsweep-ea14fdf/refs/perc2/ep0 (20 Oct, code 6ad3db7, perception with the PUBLIC SCANS as templates, pre-compact prior, mkref without contact retarget; fed by refsweep perc2/ep0, verified 0.001 mm).'),
    dict(ep=2, ref_run='20261024-e3-e49e83d', ref_variant='perc2mck', perc=('20261024-e3-e49e83d', 'perc2'), res='20261024-e3-e49e83d/results/glock_public/ep2/best',
         lib='library_v3 (pot / lid identical in v2, v3, v3x, v4)', commit='e49e83d', twin='eval 1',
         notes='Produced by e3 (glock_public PAIRS 2:new:mck, started 23 Oct 22:12 UTC); byte-identical copies in 20261024-std39-1f306be and 20261024-ev3-2c1e4dd. Perception predates the gated re-proposal, on-table rule and track guard, and ran with Grounding DINO OFF (24 Oct bug: transformers missing); compact prior on. Newest perception (sweep base, today\'s detection, library_v2) differs by <= 1.4 mm / 0.9 deg (pot), 0 (lid). Results: e3 grasp-lock recipe of 23 Oct (approach 6, REPLAN 1, no EVOLVE), not the frozen 24 Oct recipe; no frozen-recipe run exists for ep2. Box-recorded: perception AUC 0.994; policy registered AUC 0.306 +- 0.115 (5), sim_vs_ref 0.326.'),
    dict(ep=11, ref_run='20261025-twin11v3x-0e8aebb', ref_variant='perc2mck', perc=('20261025-twin11v3x-0e8aebb', 'perc2'), res='20261025-twin11v3x-0e8aebb/results/glock_public/ep11/best',
         lib='library_v3x (v3 + v5 beige cup)', commit='0e8aebb', twin='evals 10 and 8 (cups)',
         notes='Current recipe end to end (11:new:mck, 25 Oct 02:43 UTC): on-table rule, gated re-proposal, compact prior, TRACK_GUARD on (no intervention), Grounding DINO on, frozen grasp-lock recipe (EVOLVE 1, onset_anchor, approach 15). ALTERNATE same commit with library_v3: runs/20261025-twin11v3-0e8aebb/refs/perc2mck/ep11 (its poses_world_vo.npz is byte-identical to runs/20261025-cups-46b8389/perc2m/ep11, first stored 00:45 UTC: deterministic re-tracking, v2 = v3 for the cups, guard not triggered). v3 vs v3x references differ only by the beige cup (22.6 deg, measured). Box-recorded: policy registered AUC 0.570 (v3x) / 0.525 (v3); beige cup falls at the start in both.'),
    dict(ep=12, ref_run='20261023-fdr43-715c9f7', ref_variant='perc2mckd', perc=('20261021-auto18-966eb96', 'perc2m'), res='20261024-ev2-2c1e4dd/results/glock_public/ep12/best',
         lib='library_v2 (blue_cup / rack identical to library_v3)', commit='mkref 82a5fe4 (auto18 second auto_runs, 21 Oct); contact retarget 715c9f7 (fdr43, 22 Oct 21:59 UTC)', twin='eval 14',
         notes='No current-recipe (new:mck) reference for ep12. Newest mck-family reference = mc (auto18, 21 Oct) + contact retarget WITHOUT rest settle (fdr43, SUF kd); byte-identical copies in kf18-a674fd7, e1-e49e83d, ev3-2c1e4dd; fdr42-715c9f7 has a different file with the identical object path. Object path == auto18 perc2mc (0.0 mm, measured), so results_dir = ev2 frozen-recipe grasp lock trained on glockt built on mc (reference columns == this object path, 0.0 mm measured); alternate rollouts on this exact file: runs/20261023-fdr43-715c9f7/results/hard_ab/ep12/mckd-s43 (standard learner). Perception 21 Oct (old detection, compact prior); newest perception (guard arm) within 0.9 mm (rack), 0 (cup). Box-recorded: ev2 policy registered AUC 0.868 +- 0.122.'),
    dict(ep=13, ref_run='', ref_variant='', perc=('20261025-sweep-a894083', 'results/sweep/base'), res='', lib='library_v2 (blue_cup / rack identical to library_v3)', commit='a894083', twin='',
         notes='NO mkref reference with the current recipe. Newest perception = precision-sweep base arm (on-table rule, gated re-proposal, compact prior, Grounding DINO on; TRACK_GUARD did not exist yet in that code -> off; no guard run exists for ep13). Box-stored registered perception AUC 0.961. Stale reference: runs/20261020-refsweep-ea14fdf/refs/perc2/ep13 (public-scan templates, 20 Oct).'),
    dict(ep=18, ref_run='20261022-r4kfi-a30ac72', ref_variant='perc2mckfi', perc=('20261021-auto18-966eb96', 'perc2m'), res='20261024-ev3-2c1e4dd/results/glock_public/ep18/best',
         lib='tracking library_v2 (rounded sweeper); reference/simulation assets library_v3 (flattened sweeper)', commit='mkref 966eb96 (auto18); contact retarget a30ac72 (r4kfi, rest settle on)', twin='eval 19',
         notes='Producer r4kfi (22 Oct 03:22 UTC job) as perc2mckfi; byte-identical copies named perc2mckfid in fdr42/fdr43-715c9f7, glockpub-0f7e3a7, kf18-a674fd7, e1-e49e83d, ev3-2c1e4dd. Contact retarget WITH rest settle changes the object path vs mc (dust pan up to 29 mm / 12.9 deg, sweeper 4.2 mm / 5.3 deg, measured). results_dir = ev3 frozen recipe on the mckfid copy (reference columns == this file, 0.0 mm measured). Perception 21 Oct; newest perception (guard arm) byte-equivalent (0.0 mm). Box-recorded: ev3 policy registered AUC 0.957 +- 0.002, sim_vs_ref 0.992.'),
    dict(ep=21, ref_run='20261025-twin21arc-ee7ba8e', ref_variant='perc2mck', perc=('20261025-twin21arc-ee7ba8e', 'perc2'), res='20261025-twin21arc-ee7ba8e/results/glock_public/ep21/best',
         lib='library_v3', commit='ee7ba8e', twin='eval 20',
         notes='Current recipe end to end (21:new:mck, 25 Oct 14:58 UTC), SF_ARC=1 (arc foot adopted), eval_both grasp-lock defaults (REPLAN 1, EVOLVE 0, approach 15, no onset_anchor; not the frozen 24 Oct GL recipe). Perception with on-table rule, gated re-proposal, compact prior, TRACK_GUARD (no intervention), Grounding DINO on. ALTERNATE: runs/20261025-twin21base-ee7ba8e/refs/perc2mck/ep21 (SF_ARC=0; separate perception run, pitcher differs <= 1.7 mm). Box-recorded: perception AUC 0.924; policy registered AUC 0.772 +- 0.009, sim_vs_ref 0.983.'),
    dict(ep=22, ref_run='', ref_variant='', perc=('20261025-sweep-a894083', 'results/sweep/base'), res='', lib='library_v2 (blue_cup / water_pitcher identical to library_v3)', commit='a894083', twin='(cup + pitcher, like eval 20; not stated in docs)',
         notes='NO mkref reference with the current recipe. Newest perception = sweep base arm (no guard). Box-stored registered perception AUC 0.871 (pitcher 0.750). Stale reference: runs/20261020-refsweep-ea14fdf/refs/perc2/ep22 (public-scan templates).'),
    dict(ep=23, ref_run='', ref_variant='', perc=('20261025-guard-fe3f407', 'results/sweep/guard'), res='', lib='library_v2 (boards identical to library_v3)', commit='fe3f407', twin='(boards, like eval 25; not stated in docs)',
         notes='NO mkref reference with the current recipe. Newest perception = guard arm (guard intervened: board 1 5 implausible frames, 4 re-acquired); frame-0 identity swap of the two boards persists: box-stored registered perception AUC 0.041. Stale reference: runs/20261020-refsweep-ea14fdf/refs/perc2/ep23 (public-scan templates).'),
    dict(ep=24, ref_run='20261022-r5ks-72ecb2f', ref_variant='perc2mcsks', perc=('20261021-auto24-966eb96', 'perc2m'), res='20261024-ev3-2c1e4dd/results/glock_public/ep24/best',
         lib='library_v2 (boards identical to library_v3)', commit='mkref 966eb96 (auto24); contact retarget 72ecb2f (r5ks, no rest settle)', twin='eval 25',
         notes='The newest mck reference by date, runs/20261024-w1-37cc551/refs/perc2mck/ep24, is EXCLUDED: tracked with library_v4 (flattened boards, not adopted), box perception AUC 0.029, boards swapped/flipped vs the 21 Oct track (~180 deg, ~25 cm, measured); downloaded for diagnostics only. Chosen = auto24 mcs (hand separation) + contact retarget without rest settle (r5ks; copy in r5ks43). Object path == auto24 perc2mcs (0.0 mm, measured); results_dir = ev3 frozen recipe trained on glockt built on mcs (0.0 mm measured); alternate rollouts on this exact file: runs/20261022-r5ks-72ecb2f/results/hard_ab/ep24/mcsks-s42. Perception 21 Oct = identical (to 2e-8) to autohard-3c11668 perc2m/ep24 and to the 25 Oct sweep base and guard arms (deterministic re-tracking). Box-recorded: ev3 policy registered AUC 0.241 +- 0.125.'),
    dict(ep=26, ref_run='20261024-w1-37cc551', ref_variant='perc2mck', perc=('20261024-w1-37cc551', 'perc2'), res='20261024-w1-37cc551/results/glock_public/ep26/best',
         lib='library_v4 (pot / rack identical to library_v3; v4 differs only in the boards)', commit='37cc551', twin='eval 28',
         notes='Produced by w1 (26:new:mck, 23 Oct 22:29 UTC). Perception predates re-proposal, on-table rule and guard; Grounding DINO OFF (bug). Newest perception (sweep base) within 1.6 mm / 2.1 deg. Results: 23 Oct grasp-lock recipe (approach 15, REPLAN 1, no EVOLVE). Box-recorded: perception AUC 0.952; policy registered AUC 0.383 +- 0.131.'),
    dict(ep=27, ref_run='20261022-r1b-65c5a52', ref_variant='perc2mck', perc=('20261021-auto18-966eb96', 'perc2m'), res='20261024-ev2-2c1e4dd/results/glock_public/ep27/best',
         lib='library_v2 (pot / rack identical to library_v3)', commit='mkref 82a5fe4 (auto18 second auto_runs); contact retarget d4ac331 (r1b COMMIT; run name 65c5a52), no rest settle', twin='eval 28',
         notes='Producer r1b (CR at 21 Oct 22:25 UTC); byte-identical recomputation in r3kie-342d72c as perc2mcki (00:03 UTC 22 Oct). Object path == auto18 perc2mc (0.0 mm, measured); results_dir = ev2 frozen recipe on glockt built on mc (0.0 mm measured); alternate rollouts on this exact file: runs/20261022-r1b-65c5a52/results/hard_ab/ep27/mck-s42. Newest perception (sweep base) within 2.3 mm. Box-recorded: ev2 policy registered AUC 0.949 +- 0.010.'),
    dict(ep=31, ref_run='20261024-ev30rp-07eef1a', ref_variant='perc2mck', perc=('20261024-ev30rp-07eef1a', 'perc2'), res='20261024-ev30rp-07eef1a/results/glock_public/ep31/best',
         lib='library_v3 (flattened sweeper)', commit='07eef1a', twin='eval 30',
         notes='Produced by ev30rp (31:new:mck, 24 Oct 22:51 UTC) with DET_REPROP=1 (gated re-proposal fired: 1 box -> 3 proposals), frozen GL recipe (EVOLVE 1, onset_anchor, approach 15); on-table rule and track guard not yet in that code; Grounding DINO on. Byte-identical copies in pack2-46b8389 and std30-ee7ba8e. Newest perception (guard arm, library_v2 sweeper) within 3.4 mm / 4.7 deg. Older e2-e49e83d mck (23 Oct) superseded. Box-recorded: perception AUC 0.881; policy registered AUC 0.695 +- 0.122.'),
    dict(ep=39, ref_run='20261024-e3-e49e83d', ref_variant='perc2mck', perc=('20261024-e3-e49e83d', 'perc2'), res='20261024-ev3-2c1e4dd/results/glock_public/ep39/best',
         lib='library_v3 (dust pan identical in v2/v3)', commit='e49e83d', twin='eval 38',
         notes='Produced by e3 (39:new:mck, 23 Oct); copies (byte-identical) in std39-1f306be (as perc2mck and perc2mcks) and ev3-2c1e4dd. Grounding DINO OFF at perception (bug); newest perception (sweep base) identical (0.0 mm). results_dir = ev3 frozen recipe trained on this copy (reference columns == this file, 0.0 mm measured); e3\'s own 23 Oct rollouts (0.174) also stored. Box-recorded: perception AUC 0.982; ev3 policy registered AUC 0.958 +- 0.002.'),
] + [dict(ep=e, ref_run='', ref_variant='', perc=('20261025-sweep-a894083', 'results/sweep/base'), res='', lib='library_v2 (' + o + ' identical to library_v3)', commit='a894083', twin='',
          notes=f'NO mkref reference with the current recipe. Newest perception = sweep base arm (no guard; no guard run exists). Box-stored registered perception AUC {a}. Stale reference: runs/20261020-refsweep-ea14fdf/refs/perc2/ep{e} (public-scan templates, 20 Oct).')
     for e, o, a in ((40, 'mini_dust_pan', 0.957), (41, 'white_pot', 0.991), (42, 'white_pot', 0.9915), (43, 'white_pot', 0.948), (44, 'white_pot', 0.997), (45, 'white_pot', 0.9795))]

NEWEST = {  # newest stored perception per episode (today's detection; guard arm where one exists)
    **{e: '20261025-sweep-a894083/results/sweep/base' for e in (2, 13, 22, 26, 27, 39, 40, 41, 42, 43, 44, 45)},
    **{e: '20261025-guard-fe3f407/results/sweep/guard' for e in (0, 11, 12, 18, 21, 23, 24, 31)}}
ALT = {11: ['runs/20261025-twin11v3-0e8aebb/refs/perc2mck/ep11 (library_v3; results runs/20261025-twin11v3-0e8aebb/results/glock_public/ep11/best)'],
       12: ['runs/20261021-auto18-966eb96/refs/perc2mc/ep12 (same object path, no CR)', 'runs/20261023-fdr43-715c9f7/results/hard_ab/ep12/mckd-s43 (rollouts on the chosen file)'],
       18: ['runs/20261021-auto18-966eb96/refs/perc2mc/ep18 (pre rest-settle object path)', 'runs/20261022-r4kfi-a30ac72/results/hard_ab/ep18/mckfi-s42 (rollouts on the chosen file)'],
       21: ['runs/20261025-twin21base-ee7ba8e/refs/perc2mck/ep21 (SF_ARC=0; results runs/20261025-twin21base-ee7ba8e/results/glock_public/ep21/best)'],
       24: ['runs/20261021-auto24-966eb96/refs/perc2mcs/ep24 (same object path, no CR)', 'runs/20261022-r5ks-72ecb2f/results/hard_ab/ep24/mcsks-s42 (rollouts on the chosen file)',
            'runs/20261024-w1-37cc551/refs/perc2mck/ep24 (EXCLUDED: library_v4 track, swapped boards)'],
       27: ['runs/20261021-auto18-966eb96/refs/perc2mc/ep27 (same object path, no CR)', 'runs/20261022-r1b-65c5a52/results/hard_ab/ep27/mck-s42 (rollouts on the chosen file)'],
       39: ['runs/20261024-e3-e49e83d/results/glock_public/ep39/best (23 Oct recipe rollouts on the same reference)'],
       31: ['runs/20261024-e2-e49e83d/refs/perc2mck/ep31 (older, 23 Oct perception)']}

NOTES = (
    'Store root for every relative path: /tmp/claude-0/-home-user-v2d-track3/12630086-0942-582d-80bb-a9806af3e32b/scratchpad/refcheck/store '
    '(HF dataset aebatirel/v2d-store). Method: store file list + HF sha256 per file (get_paths_info) to group identical files; '
    'producer = the run whose job.log built the item first (job.log timestamps; COMMIT file for the code); tracking library from '
    'job flags, the work log and the make_assets fingerprint in job.log (sweeper extents 14.4 cm = v2, 14.7 = v3 family; beige cup '
    '1998 verts = v3x; board extents 12.9 = v4). Library md5 check (measured): v2 == v3 except mini_sweeper; v3x = v3 except beige_cup; '
    'v4 = v3 except the two boards, so the library label only matters for ep11 (beige cup), ep18 / ep31 (sweeper) and ep24 (boards). '
    'MEASURED here (CPU, scripts in docs/analysis/robustness-review-20261026/refcheck/resolve/, no ground truth read): '
    '(1) feed check (verify_feed.py -> feed_check.json): for every chosen reference the pre-contact-retarget object path '
    '(e2s_reference.parquet, else the processed parquet) equals a constant rigid transform of the named perception poses_world_vo.npz '
    'to <= 0.001 mm / 0.0 deg (mkref reads poses.npz in the same folder; poses_world_vo = world_T_cam @ cam_T_obj). '
    '(2) evaluator rollouts (compare_paths.py -> path_provenance.json): the reference_position / reference_quaternion columns of every '
    'chosen results dir equal the chosen reference object path exactly (0.0 mm, 0.0 deg, no offset); support_fill (ep2) and '
    'grasp lock + wrist ILC + evolve (glockt; ep2, ep39 and via the rollouts of 11, 12, 18, 21, 24, 26, 27, 31) leave the object path unchanged. '
    '(3) SURPRISE: contact_retarget --rest_settle 1, part of the current mck recipe since 22 Oct, DOES move objects '
    '(cr_object_change.json, e2s_reference -> final, max after removing a constant offset): ep2 pot 31 mm / 6.3 deg, ep18 dust pan 29 mm / 12.9 deg, '
    'ep26 pot 19 mm / 6.7 deg, ep31 rack 9 mm (constant z -9 mm), ep21 blue cup 7.9 mm, ep11 blue cup 4-9 mm, ep39 dust pan 7.6 mm / 4.9 deg; '
    'the older retarget without rest settle (ep12 mckd, ep24 mcsks, ep27 mck) leaves the object path unchanged (0.0 mm). So "hand-side stages do '
    'not change the object path" is FALSE for the contact-retarget stage of the current recipe and true for support fill / grasp lock. '
    '[H] rest settling changes the reference accuracy vs mocap in resting segments (sign unknown); falsify by scoring e2s_reference.parquet and '
    'the final parquet of the same reference per frame against mocap. '
    '(4) determinism: re-running perception with the same inputs gives byte-identical tracks (twin11v3 ep11 == cups-46b8389 perc2m ep11; '
    'sweep base ep24 == autohard-3c11668 21 Oct to 2e-8; ep18 guard == base == auto18), so equal hashes are not always copies. '
    '(5) staleness (stale_check.py -> stale_check.json): each chosen perception vs the newest stored perception (sweep base, or guard arm where '
    'one exists; today\'s detection, library_v2 templates) differs by <= 3.4 mm / 4.7 deg everywhere except ep11 beige cup (v3x vs v2 template, '
    '22.6 deg). Recipe status: current recipe end to end only for ep11 and ep21; ep31 lacks the on-table rule and track guard; ep2 / ep39 / ep26 lack '
    're-proposal, on-table rule and guard and ran with Grounding DINO off (24 Oct bug); ep12 / 18 / 24 / 27 are 21 Oct perc2m tracks (library_v2) with '
    '22 Oct contact retargeting. 10 episodes (0, 13, 22, 23, 40-45) have no own-mesh mkref reference at all: only 20 Oct refsweep references '
    'built from PUBLIC-SCAN-templated perception (downloaded, listed as stale_reference, not canonical). ep24: the newest mck (w1-37cc551) is '
    'excluded (library_v4 boards, perception AUC 0.029, boards swapped). All AUC / sim_vs_ref numbers in recipe_notes are box-recorded '
    '(job.log RESULT lines or stored score_registered.json), not recomputed here; no scoring process was run in this check. Extra keys per '
    'episode: ref_parquet (+sha256), ref_pre_contact_retarget (pure mkref output), newest_perception_path, alternates, stale_reference.')

if __name__ == '__main__':
    root, hashes, outs = sys.argv[1], json.load(open(sys.argv[2])), sys.argv[3:]
    eps, missing = [], []
    for d in E:
        ep = d['ep']; prun, pdir = d['perc']
        perc = f'{S}{prun}/{pdir}/ep{ep}/poses_world_vo.npz'
        assert os.path.exists(f'{root}/{perc}'), perc
        objs = list(np.load(f'{root}/{perc}').files)
        row = dict(ep=ep, objects=objs, eval_twin=d['twin'], ref_run=d['ref_run'], ref_variant=d['ref_variant'], ref_path='', perception_path=perc,
                   perception_sha256=hashes.get(perc, {}).get('sha256', ''), commit=d['commit'], tracking_mesh_library=d['lib'],
                   results_dir=(S + d['res']) if d['res'] else '', recipe_notes=d['notes'])
        loc = [f'{root}/{S}{prun}/{pdir}/ep{ep}']
        if d['ref_run']:
            rp = f'{S}{d["ref_run"]}/refs/{d["ref_variant"]}/ep{ep}'
            fs = sorted(glob.glob(f'{root}/{rp}/processed/*/*/*.parquet')); assert fs, rp
            row['ref_path'] = rp; row['ref_parquet'] = fs[0][len(root) + 1:]
            row['ref_parquet_sha256'] = hashes.get(row['ref_parquet'], {}).get('sha256', '')
            row['ref_pre_contact_retarget'] = f'{rp}/e2s_reference.parquet' if os.path.exists(f'{root}/{rp}/e2s_reference.parquet') else ''
            loc.insert(0, f'{root}/{rp}')
        else:
            missing.append(f'ep{ep}: no current-recipe mkref reference (perception only: {perc}; stale 20 Oct scan-template reference runs/20261020-refsweep-ea14fdf/refs/perc2/ep{ep})')
            row['stale_reference'] = f'{S}20261020-refsweep-ea14fdf/refs/perc2/ep{ep}'
            loc.append(f'{root}/{S}20261020-refsweep-ea14fdf/refs/perc2/ep{ep}')
        if d['res']:
            assert glob.glob(f'{root}/{S}{d["res"]}/r1/episode_{ep:06d}.parquet'), d['res']
            loc.append(f'{root}/{S}{d["res"]}')
        else:
            missing.append(f'ep{ep}: no evaluator results dir')
        row['newest_perception_path'] = f'{S}{NEWEST[ep]}/ep{ep}/poses_world_vo.npz'
        row['alternates'] = ALT.get(ep, [])
        row['local_paths'] = ' ; '.join(loc)
        for p in loc: assert os.path.exists(p), p
        eps.append(row)
    eps.sort(key=lambda r: r['ep'])
    missing += [
        'ep2, ep26: no evaluator rollouts with the frozen 24 Oct grasp-lock recipe (stored rollouts use the 23 Oct recipe: REPLAN 1, no EVOLVE)',
        'ep2, ep26, ep39: no reference from perception with Grounding DINO on, gated re-proposal, on-table rule or track guard',
        'ep12, ep18, ep24, ep27: no reference built from post-21-Oct perception (21 Oct perc2m tracks, library_v2; newest perception within 2.3 mm, measured)',
        'ep31: no reference with the on-table rule and track guard (ev30rp has the gated re-proposal only)',
        'ep21: no rollouts with the frozen GL recipe on the current reference (twin21 used eval_both defaults: REPLAN 1, EVOLVE 0, no onset_anchor)',
        'ep0, ep13, ep22, ep23, ep40-45: no stored evaluator rollouts and no own-mesh mkref reference in the store',
        'mesh library is not recorded in perc2 log.txt / result.json; inferred from job flags and the make_assets fingerprint in job.log',
    ]
    out = dict(episodes=eps, missing=missing, notes=NOTES)
    for o in outs:
        json.dump(out, open(o, 'w'), indent=1)
    print(len(eps), 'episodes,', len(missing), 'missing items')
