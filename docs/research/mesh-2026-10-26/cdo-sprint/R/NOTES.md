# Rack round R: working notes (resume from here)

Spec: `../C4-audit/PREREG.md` section 14 (addendum 9, f471f18a), with sections 2, 9, 12 and 13 for the copy types.
Template: G3 (`../G3/README.md`, `../G3/NOTES.md`, `../G3/scripts/`). Times UTC. Scratch S =
`/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad`, bulk under `S/r/`.
GPU cap for R $10; stop and destroy if Vast credit < $15. Ledger session mesh-bold. Stage 3 (50-seed audit) is the
coordinator's; not run here.

- 2026-11-03T07:36Z start. Read CLAUDE.md, STATUS.md (head), PREREG s2/s7-s14, G3 README / NOTES / scripts, G2 NOTES,
  crops.py, prim_rack.py header, results/prim/rack/*, C2/R-rack/PREREG.md. Local: 4 cores, 2.3 GB free disk.
  Vast credit $73.73; two instances of other sessions (20261103-ptrkH, 20261103-ipose; not ours, not touched).
- Rack episodes: pipeline/mesh_v5.json lists exactly 12 / 13 / 26 / 27 / 31 as the rack's public episodes, and those are
  the five with our tracks (data/sweep) and observed points (obs_all). No other public rack episode exists for crops.py.
- 07:37-07:39Z crops (local CPU, GT-free): `bash scripts/make_crops.sh S/r/inputs` = G3 make_crops.sh with `--n 6` and
  the five rack episodes; only crops.py's ranks 3-6 (`chosen[2:6]`) go to crops_flat. Ranks 1-2 reproduce the G2 / G3
  crops exactly (ep12 k24 / k21, ep13 k66 / k69, ep26 k144 / k138, ep27 k144 / k147; ep31 below), so the R crops are
  disjoint from G2 / G3. ep12 / ep27 have no hands.npz (rest gate only, as G2 / G3).
  **20 crops** (ranks 3-6 x 5 episodes): ep12 k18 / k27 / k15 / k12; ep13 k87 / k96 / k15 / k12; ep26 k132 / k150 /
  k96 / k126; ep27 k129 / k132 / k84 / k87; ep31 k279 / k0 / k3 / k6. Rankings `inputs/ep<E>_plastic_dish_rack_crops.json`,
  hashes `inputs/inputs_crops_sha256.txt`. Visual check (S/r/crops_montage.jpg), kept under the rule but flagged:
  - **ep31 ranks 4-6 (k0, k3, k6) have crops.py score 0**: MediaPipe hand joints (3-6) inside the rack's box, so the
    hand gate zeroes them; ep31 has only 3 frames with score > 0 (of 97). They are still crops.py's ranks 4-6 and show
    the whole rack with a notch where the hand is. Kept (PREREG s14 says ranks 3-6); stage 1 decides.
  - a hand on the cup holder in ep26 k96; skin / table at the right end of ep13 k96; GrabCut notches in the peg area of
    ep12 k12 / k15 / k27, ep13 k12 / k15 / k87, ep26 k126 / k150.
- 07:37-07:39Z Pixal3D-MV view sets (local CPU, GT-free): `bash scripts/make_views.sh S/r/inputs` = G3 make_views.sh for
  the rack only, with the rack's 29 Oct flags (`--skin 1 --held_speed_mm 8 --min_deg 15 --occl 0.15`, from
  S/gen/run_views2.sh); at-rest fallback `--skin 1 --min_deg 15 --occl 0.15` when view 0's mask / silhouette IoU < 0.75;
  then G3 `scripts/assemble_g3.py` unchanged. Every skin-gated set had view-0 IoU 0.51-0.69 (the lattice defeats GrabCut),
  so all 5 use the at-rest set, **one view each** (`inputs/views/selection.json`): ep12 k24 (IoU 0.68), ep13 k66 (0.66),
  ep26 k98 (0.51), ep27 k146 (0.69), ep31 k286 (0.65). ep12 / ep27 use the stub hands file (a_offset 1, no valid hand).
  The 29 Oct probe ran Pixal3D-MV on ep26 (view k138, seeds 42 / 7); R's ep26 set uses k98, so no R output repeats it.
- 07:40Z observed points for the box's Sim(3) fits: G3 `scripts/obs_sub.py` unchanged (40k of S/obs_all/ep<E>_plastic_dish_rack.npz,
  default_rng(0)); all five are cmp-identical to the G2 (ep12 / 26 / 31) and G3 (ep13 / 27) files. Hashes
  `inputs/inputs_obs_sha256.txt`, view files `inputs/inputs_views_sha256.txt`. Input tar S/r/r_inputs.tar (crops_flat,
  obs_sub, views_final) sha256 9ff31e5e3f989cfb...
- Box queue `scripts/box_r.sh` = G3 box_g3.sh with the R tar, seeds 42 / 7 / 123 / 2025 / 31337 / 777, marker R-GEN-DONE and
  an HF-download retry. Launcher `scripts/launch_box_r.sh` = G3's (hf-2.2 Python-API fetch), queue path changed. Screen:
  `scripts/screen_manifest_r.py` (G3's, rack only, label r/...), `scripts/box_screen_r.sh` (G3's, R paths),
  `../C4-audit/scripts/screen6.py` unchanged.
- 07:40Z commit 63eb2c5 pushed (inputs, scripts). Inputs uploaded to the store `runs/mesh-20261103-r-63eb2c5/inputs/r_inputs.tar`
  (Python API; sha256 9ff31e5e...). Ledger planned $8 (mesh-bold). Credit $73.73 at 07:39Z.
- 07:41:03Z rental, run `mesh-20261103-r-63eb2c5`. On-demand H200 offers: Colorado $3.64/h (32 cores), Spain $3.68/h
  ($20/TB), New Mexico $3.90/h (85 cores, 5.5 Gbps, $2.67/TB: the G2 / G3 host type). Chose New Mexico 58416016 (cores for
  Sim(3) + screen, proven). `SETUP=none DISK=120 IMAGE=vastai/pytorch:2.7.1-cu128-cuda-12.9-mini-py310-2026-10-23
  V2D_COMMIT=63eb2c5da14a83badb7d7a84458524eaef75032c ops/vast.sh create 58416016 mesh-20261103-r-63eb2c5
  'IDLE_MIN=130 bash docs/research/mesh-2026-10-26/gen/box_job.sh'` -> **instance 58934345**. IDLE_MIN 130 keeps the
  worst case (idle limit + ~15 min pull / push) at ~$9.8 < $10 cap. Expected ~1.6 h, ~$6.5 [E].
- R-prim scope (decided 07:44Z, before any R-prim file exists; GT-free reasoning only):
  - Measured prim racks (library_index [D] records, results/prim/rack/scores.jsonl, C2/R-rack/results/score.jsonl,
    C0 / clean-up work log 2026-10-27): the first run's per-episode `full` / `nomk` for all five episodes and its joint
    variants (code ca2aea0d, T_WALL 2.5 mm, **upright cup**, the default then); dev1 ep31 / ep12 full; the six clean-up
    joint selections (T 1.5 / 2.5 / 4.0 x lean 0 / 1; t2.5_lean1 joint = the shipped C0 rack); audit v0 joint; C2
    K_ep12_nomk (C0b points); C0b ep13_full.
  - prim_rack.py's **existing settings** are its current defaults: T_WALL 2.5 mm and CUP_LEAN = 1 (free lean, adopted by
    the clean-up round). At these settings only the joint was ever measured; no per-episode fit and no joint_nomk was.
    So the R-prim base run is `prim_rack.py run --obs_dir obs_all --episodes 12,13,26,27,31` (defaults, our obs_all
    points as C0 / dev1), all 4 variants (full, nomk; joint, joint_nomk).
  - **Existing variant flags:** prim_rack.py's three C2 option flags `--end_draft` (E), `--peg_kappa_free` (K),
    `--cup_quad` (Q), each run once on its own, same inputs and defaults. Combinations (EK, EQ, KQ, EKQ) and the C0b
    options (`--t_wall`, `--s0_min_t`, `--markers_dir`: settings / marker inputs, not variants) are not run; they would
    add 4 x 12 fits.
  - Every output whose sha1[:16] or md5 equals an already-measured file is dropped (expected: the base joint = the
    shipped C0 rack, byte-identical per the 2026-10-27 regression); byte-identical outputs (full == nomk when no marker
    is found) are kept once.
- 07:43:39Z R-prim base run started locally (nice 10): `cd S && prim_rack.py run --obs_dir obs_all --out r/prim/base
  --episodes 12,13,26,27,31`. 07:45:52Z E / K / Q runs started in parallel: same command with `--out r/prim/<E|K|Q>`
  plus `--end_draft` / `--peg_kappa_free` / `--cup_quad`. Logs S/r/prim/<run>.log.
- 07:48:13Z (box clock) box 58934345 answering exec (~7 min after create, image pull): H200 NVL 143.8 GB, cgroup quota ~82
  cores (nproc 256 host), repo at 63eb2c5, RUN_ID set. 07:48:28Z launched through exec:
  `NP=64 bash .../R/scripts/launch_box_r.sh` (box_setup.sh; sam3d_setup.sh after UV-; hf-2.2 fix after WEIGHTS-DONE; then
  box_r.sh).
- 07:43-07:47Z R-prim base run done (RC 0, ~3.5 min): it reproduces the 2026-10-27 clean-up round's t2.5_lean1 files
  byte for byte (all 12 md5-identical; that round scored only their joint). joint_joint = the shipped C0 rack
  (`results/prim/meshes/plastic_dish_rack_joint_v2.glb`, md5 bbca8ec0, measured) -> dropped. ep26 / ep27 full == nomk
  (no marker found) -> kept once.
- 07:50:09Z INPUTS-OK 9ff31e5e (20 crops, 5 view sets). 07:51:49Z setup markers all OK except W-HY21-FAIL (hf CLI 2.2
  `--include`, again), fixed by the launcher's Python-API fetch (HYFIX-OK). SAM 3D env C import OK.
- 07:51:49Z generation started: SAM 3D alongside Hunyuan3D-2.1, 20 crops x 6 seeds each (120 per model).
- 07:47-07:55Z R-prim E / K / Q runs done (RC 0 each, 12 meshes each). `scripts/prim_list.py` (drop already-measured
  files by sha1[:16] / md5 from `scripts/measured_rack.py`: 55 sha1 + 27 md5 of measured / audited rack files; keep
  byte-identical outputs once): **39 R-prim fits**, 9 dropped (base joint_joint = measured C0 rack; ep26 / ep27 nomk ==
  full in all four runs, no marker found there). Joint reference episode for t3fit = 12 (the joint episodes are 12 / 13 /
  27 in all runs; ep12 has the most 1.5 mm-voxel points, prim_rack.py's own reference rule). E_ep13_full is not
  watertight (raw); kept, as no rule excludes it.
- 07:56Z stage 2 for R-prim started (`scripts/stage2_r.py --only prim`, 4 parts in parallel, nice 10).
  **fit.py failed on every prim fit**: its first step decimates the input to work_faces 12000 with fast_simplification,
  which raises "target_count must be less than the number of faces" for inputs below 12000 faces (prim fits have
  958-3568). Stopped at 07:57Z (8 fits failed, outputs removed). **Deviation:** inputs with <= 12000 faces get exact
  midpoint subdivision (`trimesh.remesh.subdivide`, the same surface) until they exceed 12000 faces; fit.py itself and
  its frozen cfg are unchanged. R-gen meshes (> 12000 faces) are unaffected. Restarted 07:57:40Z; trim / outer outputs
  already written were reused. Early trims: 7 of 8 base fits remove 0 faces (prims lie on our points); base ep26 full
  removes 116 faces (4.6 % of area, centroid x +73 mm, z -117 mm). Outer drops the floating marker balls of `full` fits
  (fragments < 1 % area), else nothing.
- 07:57-08:03Z R-prim stage 2 done (4 parts, RC 0): 39 sources -> **90 candidates** before the merge (placed 39, plus the
  t3fit / trim / outer / trim_outer copies that are not no-ops and pass the kit budget; details in picks after the merge).
  fit.py now runs on the subdivided inputs (2 subdivisions each, 15-47k faces); a few fits end with fit.py's own final
  kit-budget error ("mesh simplification cannot satisfy the budget", as G3's 2 Pixal3D-MV fits), recorded as failed.
  Trim: a no-op on most prim fits (they lie on our points); outer: drops the floating marker balls of `full` fits.
- R-prim files committed: `results/prim/<base|E|K|Q>/` (prim_rack.py outputs, build records, logs; 2.3 MB),
  `results/prim/prim_list.json` (the 39), `prim_list_dropped.json` (the 9), `measured_rack.json`; prim_rack.py at
  01c25d29 (sha1 in `results/prim/code_sha1.txt`). Not scored (PREREG s14).
- 08:04Z box: SAM 3D 45/120, Hunyuan 25/120, 0 failures. Credit $71.93.
- 08:21:25Z SAM 3D done, **120/120 ok** (~15 s each, alongside Hunyuan3D-2.1); Pixal3D-MV 1536 started (5 view sets x 6
  seeds, one process). 08:25:43Z SAM 3D Sim(3) 120/120. 08:33:07Z Pixal3D-MV done, **30/30 ok at 1536** (no 1024
  fallback); TRELLIS.2 1536 started (20 crops x 6 seeds, one process). Hunyuan 97/120 at 08:33.
- 08:34Z GT-free frame check of the 30 Pixal3D-MV outputs on the box (`gen/mv_check.py`, our view masks only, as G3):
  silhouette IoU per mesh (single view each) ep12 0.93-0.94, ep13 0.94-0.97, ep26 0.74-0.79, ep27 0.97-0.98, ep31
  0.88-0.92. The outputs are in our object frame; ep26's lower IoU matches its view-0 mask / silhouette IoU of 0.51 (a
  poor GrabCut mask), not an axis error.
- 08:44:19Z Hunyuan3D-2.1 done **120/120** (~27 s each); Sim(3) 120/120 at 08:48. 08:54:39Z TRELLIS.2 1536 done
  **120/120** (~11 s each; no out-of-memory, no 1024 fallback); Sim(3) 120/120 at 08:58:38.
- 08:58:42Z **R-GEN-DONE**: SHA256SUMS over **780 .ply** = 360 raw single-image (SAM 3D 120, Hunyuan 120, TRELLIS.2 120)
  + 360 Sim(3) copies + 60 Pixal3D-MV (30 raw generator-cube `_gen` + 30 in our object frame). **0 failed, 0 lost.**
  Sim(3) errors.log files are empty.
- FREEZE: `results/SHA256SUMS` (sha256 c6ac6206f1eb4e87...), `results/gen_logs/`, `results/sim3_fits/`,
  `results/mv_check.jsonl`, `results/box_logs/` (log tails; scanned for tokens, none) committed next, BEFORE any
  public-scan read of these meshes. No R mesh has been scored or compared with a scan.
- 08:59Z after the freeze (cf30b25c pushed): screen_pkg.tar = G3's package unchanged (kit + 8 public scans + 8 b4096
  caches, sha256 830b4848...; the rack scan / cache inside are the ones G2 / G3 used) uploaded to
  runs/mesh-20261103-r-63eb2c5/screen/. Box fetched cf30b25c with the onstart.sh header pattern (GH_TOKEN from
  /etc/v2d_env, not printed) and checked it out; its SHA256SUMS == the committed one (cmp, SUMS-MATCH).
  08:59:49Z `NP=64 R/scripts/box_screen_r.sh` started, PKG-OK 830b4848.
- 08:59:47-09:04:07Z stage-1 screen [D] on the box's CPUs (`box_screen_r.sh`, 64 workers; py3.13 venv pinned to the local
  versions numpy 2.5.4, scipy 1.18.1, trimesh 5.2.0, pandas 3.1.0; box at cf30b25c; manifest 390 meshes = 360 Sim(3) +
  30 Pixal3D-MV object-frame, 0 hash mismatches). **390 records, 0 errors**, 0 "budget_mesh failed" fallbacks
  (`results/screen/screen6.jsonl`, sha256 e3aee80ac8942ea2...). Table: `results/stage1_table.md`
  (`scripts/stage1_table_r.py`).
  - Best **0.3876** hy21 ep12 k18 s31337 (13i rack 0.4016, so -0.014 at stage 1; rule A needs <= 0.3816 at 50 seeds).
    5 of 390 below 0.4016, none <= 0.3816. Per model (best / median of the CD-O medians): SAM 3D 0.507 / 0.606,
    Hunyuan 0.388 / 0.565, TRELLIS.2 0.393 / 0.494, Pixal3D-MV 0.512 / 0.611. W30 > 0 on 2 meshes (ep13).
  - Stage-2 picks (6 lowest): hy21 ep12 k18 s31337 (0.3876), trellis2 ep27 k129 s7 (0.3925), trellis2 ep27 k84 s42
    (0.3967), trellis2 ep27 k87 s123 (0.3968), hy21 ep31 k3 s777 (0.4014; ep31 k3 is a crops.py score-0 crop),
    trellis2 ep27 k132 s42 (0.4033).
- 09:04-09:07Z final store push from the box (`ops/box/store.sh push-run`, PUSH-RC 0): runs/mesh-20261103-r-63eb2c5/
  holds all 780 .ply + results/screen (5.0 GB). Checked from here: SHA256SUMS, screen6.jsonl and 3 sample .ply exist.
  (The exec call itself returned HTTP 524 after 100 s; the push kept running and finished.)
- 09:09Z instance record (`results/box_logs/vast_instance_58934345.txt`): start 07:41:06.67Z, $3.90/h, 71.8 GB down at
  $2.60/TB, 3.1 GB up at $3.91/TB. **09:09:37Z box 58934345 destroyed**, confirmed absent in `ops/vast.sh show` (0
  instances listed). **Measured cost $5.95** = 1.475 h x $3.90/h ($5.75) + $0.19 down + $0.01 up. Credit $67.34 at
  09:10Z (was $73.73 at 07:39Z; includes other sessions' boxes).
- 09:10Z ledger actual $5.95 (mesh-bold). The helper appended it 4 times again (its retry re-appends when the upload
  raises after landing) and was cut by a 120 s timeout. Removed the 3 identical duplicates with one parent_commit-guarded
  rewrite (210 -> 207 rows); that upload also returned HF 502 after landing. Re-read: one planned ($8) and one actual
  ($5.95) line for this run.
- 09:12Z the 6 stage-2 sources downloaded from the store (S/r/gendl); stage2_r.py checks each against the frozen
  SHA256SUMS. Stage 2 for R-gen started locally (`stage2_r.py --only gen`).
- 09:12-09:20Z R-gen stage 2 done (`stage2_r.py --only gen`, RC 0): 6 picks -> 30 candidates (all five copies each).
  place.py residual 4.4-4.9 mm, second-distinct start 8.2-8.8 mm (no near-ties); T3 fit held tmean90 improves on 5 / 6
  (hy21 ep31 k3 1.74 -> 1.75 mm); trim removes 22-2201 faces (<= 0.41 % area); outer drops 1478-1996 fragments of the
  TRELLIS.2 picks (0.4-1.1 % area) and 1-3 of the Hunyuan picks; no nested shell anywhere.
- 09:21Z merge (`stage2_r.py --merge`): **45 sources, 120 candidates** (placed 45, t3fit 41, trim 10, outer 18,
  trim_outer 6; R-gen 30, R-prim 90), 105 skipped copies with reasons (trim no-op 35, trim_outer without a trim 35,
  outer no-op 27, trim_outer no-op 4, t3fit failed 4 = the ep26 prims, fit.py's own final budget error). Checks: no
  candidate equals a public scan file (md5) or an already-measured rack file (sha1 / md5); no byte duplicates; all pass
  the kit budget_mesh(4096, 4096). -> `../C4-audit/candidates_rack_r.json` (md5 a0eed496...), `results/stage2_picks.json`,
  `results/stage2_skipped.json`. README.md written.
- 09:22Z store upload of S/r/stage2/out started (two pattern-limited commits: candidate .glb; records), HF 502 retries.
- 09:22-09:32Z (at the latest) store upload of S/r/stage2/out done after HF 502 retries: commits 51fb265c (candidate .glb) and 158e6acb
  (records). Checked from here: all 120 candidate files are under `runs/mesh-20261103-r-63eb2c5/stage2/`, plus
  cands_rack_r.json. Fit-stage .ply and the `_sub.glb` fit inputs were not uploaded (regenerable).
- Final: `ops/vast.sh show` lists 0 instances (58934345 destroyed 09:09:37Z). STATUS.md / docs/work-log.md left to the
  coordinator. Stage 3 (50-seed audit of candidates_rack_r.json, rules A/B/C, D1 vs the 13i rack) is the coordinator's.
