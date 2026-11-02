# G2 generation batch (C4 PREREG section 7, addendum 2; stage-2 extension section 10)

New generated candidates for the four weakest shipped meshes: white_pot, blue_cup, plastic_dish_rack and
water_pitcher. Spec: `../C4-audit/PREREG.md` section 7 (e573235) and section 10 (63e2c39). The working log is
`NOTES.md`. Labels: [D] diagnostic, scored against the public scan; [M] measured without ground truth; [E] estimate.

**The selection is GT-informed.** It is best-of-N by public-scan CD-O (stage 1, 6 seeds, all 264 meshes), as for
Tier B. The public scans stand in for the hidden ones, but picking the lowest of 72 also picks up seed and
registration luck, so the stage-1 minima are optimistic. Only the 50-seed C4 audit (stage 3, not run here) and rules
(A)/(B)/(C) decide adoption.

## What ran

| Step | Where | What |
|---|---|---|
| Crops | local CPU, GT-free | `scripts/make_crops.sh`: crops.py exactly as on 29 Oct (every 3rd frame, top 2, hand gate where hands.npz exists, our sweep tracks, library_v3 silhouette seed). All 11 planned (episode, object) pairs accepted: **22 crops**. |
| Generation | Vast box, `../../gen/box_g2.sh` | SAM 3D Objects, Hunyuan3D-2.1 (shape), TRELLIS.2-4B (1536 cascade, 1024 fallback), seeds 42 / 7 / 123 / 2025 on every crop. |
| Sim(3) | box CPUs | `gen/sim3_fit.py`, GT-free, to 40k of our observed points of the crop's own episode (`scripts/obs_sub.py`). |
| Freeze | git **1a3a044** (21:47:27 UTC) | `results/SHA256SUMS`: 528 files (264 raw + 264 Sim(3)), plus the generation and fit logs. Committed before any scan read of these meshes. |
| Stage 1 [D] | box CPUs, after the freeze | `../C4-audit/scripts/screen6.py`: one `mesh_metric.evaluate()` per Sim(3) copy, seeds 3001-3006, roster emptied, 64 workers, 21:48-21:51 UTC. 264 records, 0 errors. |
| Stage 2 | local CPU, GT-free | `scripts/stage2.py`: per object the 4 lowest stage-1 CD-O medians, then C1/T2 `place.py` into the library_v3 frame, then a C1/T3 `fit.py` copy with `cfg_frozen.json` (both unchanged). Output: `../C4-audit/candidates_g2.json`. |

- **Pairs.**
  - Pot: ep41 (k279, k285), ep43 (k300, k303), ep44 (k0, k3).
  - Blue cup: ep22 (k156, k159), ep21 (k15, k18), ep12 (k156, k159; rest gate only, since ep12 has no hands.npz).
  - Rack: ep31 (k285, k282), ep12 (k24, k21), ep26 (k144, k138).
  - Pitcher: ep22 (k33, k174), ep21 (k171, k33).
- **Where the screen ran.** The screen ran on the box's CPUs: about 82 cores, 3 min, roughly $0.2 of box time. Locally
  it would have taken about 4 h on 2 workers, since the 4 local cores were busy with another job. The kit, the 4
  public scans and their reference caches (`screen_pkg.tar`, sha256 91cf744b…) reached the box only after the freeze.
  - The box checked out 1a3a044 and confirmed with `cmp` that its SHA256SUMS matched the committed one.
  - The manifest hash-checked all 264 files: 0 mismatches.
  - The scorer env was py3.13 pinned to the local versions: numpy 2.5.4, scipy 1.18.1, trimesh 5.2.0, pandas 3.1.0.
- **Integrity.** Generation inputs were our crops, tracks, calibration, library_v3 and observed points. No scan, mocap,
  parquet pose or `*_align` file was used, and no eval data at all. The only scan reads are the stage-1 screen.

## Counts (generated / failed)

| Object | SAM 3D | Hunyuan3D-2.1 | TRELLIS.2 1536 | TRELLIS.2 1024 | Sim(3) | Total |
|---|---|---|---|---|---|---|
| white_pot | 24 / 0 | 24 / 0 | 24 / 0 | – | 72 | 72 |
| blue_cup | 24 / 0 | 24 / 0 | 18 / 6 OOM | 6 / 0 | 72 | 72 |
| plastic_dish_rack | 24 / 0 | 24 / 0 | 24 / 0 | – | 72 | 72 |
| water_pitcher | 16 / 0 | 16 / 0 | 16 / 0 | – | 48 | 48 |

- **TRELLIS.2 OOM.** All 6 failures at 1536 are ep22 blue-cup crops (k156 s42/s7/s2025, k159 s42/s7/s123).
  - They ran out of CUDA memory even on the 140 GB H200. Two failed with TRELLIS alone at 138.7 GB.
  - They were rerun at 1024, labelled `trellis2_1024`: 6/6 ok.
- **No mesh was lost.**
- **Sim(3) errors.log.** The 2-line `errors.log` in `sam3d_sim3` and `hy21_sim3` comes from xargs: with no input in the
  final gap-fill pass, it ran `sim3_fit.py` once without arguments. It is not a missing fit.

## Stage 1 [D]: best per object, and the stage-2 picks

The shipped values are the 13f meshes' 50-seed C4 medians, so the comparison is loose: 6 seeds and best-of-N here.
The full table, with ADD, anchor, W30 and ambiguity, is in `results/stage1_table.md`. The raw data is in
`results/screen/screen6.jsonl`.

| Object | Shipped CD-O (ADD) | Stage-1 best | Stage-2 picks (CD-O med, W30, ADD med mm) |
|---|---|---|---|
| white_pot | 0.3107 (6.3) | **0.2852** (-0.026) | sam3d ep44 k0 s7 (0.2852, 0, 6.1); trellis2 ep41 k279 s2025 (0.2948, 0, 6.6); hy21 ep44 k3 s42 (0.3027, 0, 8.4); trellis2 ep41 k285 s7 (0.3098, 0, 9.8) |
| blue_cup | 0.2646 (8.1) | **0.2430** (-0.022) | sam3d ep22 k159 s7 (0.2430, 0, 18.0); hy21 ep22 k159 s123 (0.2448, 0, 21.3); hy21 ep22 k156 s123 (0.2565, 0, 23.8); sam3d ep22 k156 s7 (0.2615, 0, 18.4) |
| plastic_dish_rack | 0.4182 (10.0) | **0.4027** (-0.016) | hy21 ep31 k282 s123 (0.4027, 0, 9.9); hy21 ep31 k285 s123 (0.4279, 0, 8.7); trellis2 ep31 k282 s42 (0.4294, 0, 8.8); hy21 ep12 k24 s42 (0.4418, 0, 26.3) |
| water_pitcher | 0.3713 (15.6) | 0.3868 (+0.016, worse) | hy21 ep22 k174 s123 (0.3868, 0, 35.1); trellis2 ep22 k33 s42 (0.4653, 0, 28.6); trellis2 ep22 k33 s2025 (0.4729, 0, 27.6); trellis2 ep22 k33 s7 (0.4777, 0, 29.6) |

- **Per-model medians** of the stage-1 CD-O medians:
  - pot: SAM 3D 0.409, Hunyuan 0.498, TRELLIS.2 0.369;
  - blue cup: SAM 3D 0.389, Hunyuan 2.020 (18 of 24 above 0.8: malformed shapes), TRELLIS.2 0.654;
  - rack: SAM 3D 0.602, Hunyuan 0.667, TRELLIS.2 0.503;
  - pitcher: SAM 3D 0.804, Hunyuan 1.231, TRELLIS.2 0.726.

  Best-of-N carries the result; typical outputs are far worse than the shipped meshes.
- **ADD here** belongs to the Sim(3) copy in our track frame, not to the placed copy. The placed copy's ADD will come
  from the audit. The blue-cup picks sit about 18-24 mm off in that frame.
- **One G2 blue-cup pick regenerates the shipped source.** `sam3d/ep22_blue_cup_k156_s7` uses the same crop file
  (`cmp`-identical) and the same seed as the shipped 13f blue cup's source, but it is not byte-identical, because
  SAM 3D is not deterministic across runs and GPUs. It is kept under the rule and flagged (`note` in
  `candidates_g2.json`).
- **Section-10 ADD extension ("add_ext").** The rule takes the 2 lowest stage-1 ADD medians among meshes with CD-O
  median <= shipped + 0.005, unless they are already among the 4. It was read literally: the 2 lowest are taken
  first, with no replacement. This reading was committed in `scripts/stage2.py` at 05828af, before any score. Under
  it, nothing was added:
  - pot: the 2 lowest ADD (6.14, 6.58) are picks 1-2;
  - blue cup: the 2 lowest ADD (18.0, 18.4) are picks 1 and 4;
  - rack: the only eligible mesh is pick 1;
  - pitcher: no mesh has CD-O <= 0.3763.

  The other reading, "the 2 lowest not already among the 4", would add:
  - pot: `sam3d/ep44_white_pot_k3_s7` (CD-O 0.3124, ADD 6.79) and `trellis2/ep41_white_pot_k279_s7` (0.3146, 11.07);
  - blue cup: `sam3d/ep21_blue_cup_k15_s42` (0.2630, 26.88).

  These 3 are not placed. Their Sim(3) copies are in the store.

## Stage 2 (GT-free placement and T3 fit) -> `../C4-audit/candidates_g2.json`

- **Output.** 16 picks, each with a placed copy and a T3-fit copy: **32 candidates**. Each has role `g2_candidate`,
  needs_place false, why `cdo_top4`, and kind `placed` or `t3fit`. `cdo_rec` holds the stage-1 CD-O median.
- **Checks.**
  - No candidate's md5 equals a public scan file.
  - Every source matched SHA256SUMS before placement.
- **Placement (`place.py`).**
  - Residual to library_v3, in mm: pot 3.4-3.9, blue cup 2.8-3.0, rack 4.9-5.5, pitcher 6.2-7.2.
  - Second-distinct residual, in mm: pot 4.2-4.7, cups 9.0-9.6, rack 8.4-9.0, pitcher 9.4-10.7.
  - The pot's placement is the least unique, since the margin is under 1 mm.
- **T3 fit** (frozen cfg, the episode's full observed points).
  - All 16 ran with rc 0, about 4000 faces each, and only one is watertight.
  - The GT-free held-out tmean90 [M] improves on all 16: pot 2.68-4.18 to 2.49-3.56 mm, blue cup 2.31-2.49 to
    1.57-1.76, rack 2.11-3.60 to 1.88-3.38, pitcher 3.51-5.54 to 3.01-5.32.
- **Paths.** The meshes are in `S/g2/stage2/` (S = the session scratchpad) and in the store at
  `runs/mesh-20261102-g2b-ff63482/stage2/`, together with `picks.json`, the place / fit JSONs and a copy of
  `candidates_g2.json`.
- **Next step: stage 3.** The 50-seed C4 audit of the 32 candidates and rules (A)/(B)/(C) (+ D1) are for the
  coordinator; they were not run here.

## Cost (measured from the Vast instance records)

| Run | Instance | Hardware | Time | Cost |
|---|---|---|---|---|
| mesh-20261102-g2-ff63482 | 58873650 | H100 NVL, interruptible, bid $1.30/h | created 20:26:51; **preempted** ~20:32 (whole machine rented on-demand); destroyed 20:33:53 | ~$2.80: 70.4 GB down at $37.33/TB + ~6 min at $1.398/h |
| mesh-20261102-g2b-ff63482 | 58874418 | H200 NVL, on-demand, $4.033/h, New Mexico | 20:35:21-21:54:16 (1.315 h) | **$5.50**: $5.30 + 71.7 GB at $2.67/TB + upload |
| **Total** | | | | **~$8.31** of the $25 cap |

- **Credit.** $127.84 before; $108.53 after. The credit includes other sessions' boxes.
- **Ledger.** `planned` / `actual` lines were written for both runs (LEDGER_SESSION=mesh-bold).
- **Instances.** Both are destroyed and confirmed absent in `ops/vast.sh show`.
- **Store.** `runs/mesh-20261102-g2b-ff63482/` holds 3.55 GB: all 528 .ply, the logs, the screen and stage 2.

## Deviations and problems

1. **Preemption.** The interruptible H100 NVL (the 29 Oct machine) was stopped about 4 min into generation. Nothing
   from it was kept or hashed.
   - The replacement was on-demand, so it could not be preempted again.
   - It was an H200 NVL rather than an H100: the same Hopper sm_90 architecture, so the compute_90 wheels apply. H100
     on-demand offers were scarce, and the extra memory was meant to avoid TRELLIS.2's OOM. It still did not fit the
     ep22 blue cup at 1536.
2. **hf CLI 2.2.0.** It reads a second `--include` value as a file name. As a result, `box_setup.sh` fetched no
   Hunyuan3D-2.1 weights (W-HY21-FAIL) and no TRELLIS.2 `pipeline.json`.
   - Both were fetched by hand with the Python API (`S/g2/launch_box.sh`, `hyfix.log`).
   - `box_setup.sh` is unchanged in git; it needs this fix before its next use.
3. **TRELLIS.2 beside Hunyuan.** TRELLIS.2 ran alongside the small Hunyuan job, after SAM 3D had finished; the queue
   would otherwise have waited for Hunyuan. One large model at a time still held, and the step is logged.
4. **Crop rankings vs 29 Oct.** Same picks for ep41 pot and ep22 blue cup. ep22 pitcher is now k33 + k174 (was
   k174 + k171) and ep26 rack k144 + k138 (was k144 + k96).
   - Scores differ by < 0.2 % with unchanged tracks and library_v3, likely because of local library versions.
   - Some masks have GrabCut notches (ep12 blue cup base, ep31 rack, pot floor), and ep21 pitcher k33 has
     skin-coloured pixels at its base.
5. **Prediction H8** (a rule-(A) win on at least one of pot / blue cup / pitcher). Not testable until the 50-seed audit.
   - At stage 1, pot (-0.026) and blue cup (-0.022) are past the -0.020 bar, but by best-of-72 on 6 seeds.
   - The pitcher's best is worse than shipped (+0.016).
   - The rack's best (0.403) beats shipped by 0.016, against the prediction that it would not.

## Files

| Path | Contents |
|---|---|
| `NOTES.md` | timestamped working log |
| `inputs/` | crops.py rankings per pair, crop and observed-point hashes |
| `results/SHA256SUMS` | the freeze (528 files) |
| `results/gen_logs/`, `results/sim3_fits/`, `results/box_logs/` | per-run generation records, Sim(3) fits, box log tails, the Vast instance record |
| `results/screen/` | `screen6.jsonl` (264 records), `manifest.tsv`, `screen.log` |
| `results/stage1_table.md` | stage-1 table per object |
| `scripts/` | make_crops.sh, obs_sub.py, screen_manifest.py, box_screen.sh, stage1_table.py, stage2.py |
| `../../gen/box_g2.sh` | box queue |
| `../C4-audit/scripts/screen6.py` | 6-seed screen |
| `../C4-audit/candidates_g2.json` | stage-2 candidates for the audit |
