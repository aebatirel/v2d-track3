# G3 generation batch (C4 PREREG section 12, addendum 7)

New generated candidates for the objects G2 did not cover (G3a: dust pan, beige cup, pot lid, sweeper, boards 1 and 2)
and more for the two heaviest objects (G3b: rack and pot, on public episodes G2 did not use). Spec:
`../C4-audit/PREREG.md` section 12 (d060f21e), resting on sections 2, 3, 9 and 10. G2 (`../G2/`) is the template. The
working log is `NOTES.md`. Labels: [D] diagnostic, scored against the public scan; [M] measured without ground truth;
[E] estimate.

**The selection is GT-informed.** Stage 1 is best-of-N by public-scan CD-O (6 seeds, all 468 screened meshes), as for G2
and Tier B. The public scans stand in for the hidden ones, but taking the lowest of 28-144 meshes also picks up seed and
registration luck, so the stage-1 minima are optimistic. Only the 50-seed C4 audit (stage 3, not run here), rules
(A)/(B)/(C) and the D1 veto decide adoption.

## What ran

| Step | Where | What |
|---|---|---|
| Crops | local CPU, GT-free | `scripts/make_crops.sh` = G2's (crops.py as on 29 Oct, top 2 per episode, hand gate where hands.npz exists). All 18 planned (episode, object) pairs accepted: **36 crops**. |
| Pixal3D-MV views | local CPU, GT-free | `scripts/make_views.sh` = `gen/mv_views.py` with the 29 Oct per-object flags, then `scripts/assemble_g3.py` = the 29 Oct assemble_views.py rule. **9 view sets**; ep0 lid had no usable frame. |
| Generation | Vast H200, `scripts/box_g3.sh` | SAM 3D Objects, Hunyuan3D-2.1 (shape) and TRELLIS.2-4B (1536, 1024 fallback) on every crop; Pixal3D-MV (1536) on every view set; seeds 42 / 7 / 123 / 2025. |
| Sim(3) | box CPUs | `gen/sim3_fit.py`, GT-free, single-image outputs to 40k of our observed points of the crop's own episode. Pixal3D-MV outputs are already in our object frame (no fit). |
| Frame check | box CPUs, GT-free | `gen/mv_check.py` on all 36 Pixal3D-MV outputs: silhouette IoU vs our view masks 0.84-0.99 per view (`results/mv_check.jsonl`). |
| Freeze | git **56d4710** | `results/SHA256SUMS`: 936 .ply, plus the generation, Sim(3) and mv_check logs. Committed before any scan read of these meshes. |
| Stage 1 [D] | box CPUs, after the freeze | `../C4-audit/scripts/screen6.py`: one `mesh_metric.evaluate()` per screened mesh (Sim(3) copy, or the Pixal3D-MV output in our frame), seeds 3001-3006, roster emptied, 64 workers, 03:38-03:45 UTC. **468 records, 0 errors.** |
| Stage 2 | local CPU, GT-free | `scripts/stage2.py`: per object the 4 lowest stage-1 CD-O medians -> C1/T2 `place.py` (library_v3 frame) -> C1/T3 `fit.py` copy (`cfg_frozen.json`) and a `scripts/trim.py` copy. Output: `../C4-audit/candidates_g3.json`. |

- **Pairs (crops.py picks).**
  - G3a: dust pan ep18 (k108, k99), ep39 (k297, k315), ep40 (k12, k9); beige ep11 (k0, k6), the only beige episode we
    track; lid ep0 (k0, k9), ep2 (k315, k321); sweeper ep18 (k162, k264), ep31 (k12, k270), the only two sweeper
    episodes; board 1 ep24 (k3, k6); board 2 ep24 (k6, k9).
  - G3b: rack ep13 (k66, k69), ep27 (k144, k147); pot ep0 (k285, k291), ep2 (k240, k258), ep26 (k33, k36), ep27 (k15,
    k6), ep42 (k237, k240), ep45 (k6, k9). These are every rack and pot episode we track that G2 did not use.
- **Pixal3D-MV view sets** (`inputs/views/selection.json`): dust pan ep18 (2 views), ep39 (3), ep40 (1); beige ep11 (1);
  lid ep2 (1); sweeper ep18 (5), ep31 (1); board 1 ep24 (2); board 2 ep24 (1).
  - ep18 and ep24 have no hands.npz. mv_views.py needs one, so a stub with a_offset 1 (the value in all 16 real files)
    and no valid hand stands in: rest and skin gates only, as crops.py has without `--hands`.
- **Integrity.** Generation inputs were our crops, view sets, tracks, calibration, library_v3 and observed points, plus
  the 13h meshes (ours) for the trim. No scan, mocap, parquet pose or `*_align` file was used, and no eval data. The
  only scan reads are the stage-1 screen, after the freeze.
  - The box checked out 56d4710 and confirmed with `cmp` that its SHA256SUMS matched the committed one. The manifest
    hash-checked all 468 screened files: 0 mismatches.
  - The screen package (kit + 8 public scans + 8 b4096 caches, sha256 830b4848…) reached the box only after the freeze.
  - The scorer env was py3.13 pinned to the local versions: numpy 2.5.4, scipy 1.18.1, trimesh 5.2.0, pandas 3.1.0.

## Counts (generated / failed)

| Object | SAM 3D | Hunyuan3D-2.1 | TRELLIS.2 1536 | TRELLIS.2 1024 | Pixal3D-MV | Screened |
|---|---|---|---|---|---|---|
| mini_dust_pan | 24 / 0 | 24 / 0 | 24 / 0 | – | 12 / 0 | 84 |
| beige_cup | 8 / 0 | 8 / 0 | 5 / 3 OOM | 3 / 0 | 4 / 0 | 28 |
| white_pot_lid | 16 / 0 | 16 / 0 | 16 / 0 | – | 4 / 0 (no ep0 view set) | 52 |
| mini_sweeper | 16 / 0 | 16 / 0 | 16 / 0 | – | 8 / 0 | 56 |
| wooden_piece_1 | 8 / 0 | 8 / 0 | 8 / 0 | – | 4 / 0 | 28 |
| wooden_piece_2 | 8 / 0 | 8 / 0 | 8 / 0 | – | 4 / 0 | 28 |
| plastic_dish_rack | 16 / 0 | 16 / 0 | 16 / 0 | – | – | 48 |
| white_pot | 48 / 0 | 48 / 0 | 48 / 0 | – | – | 144 |
| **total** | 144 | 144 | 141 / 3 | 3 | 36 | **468** |

- **TRELLIS.2 OOM.** All 3 failures at 1536 are ep11 beige-cup crops (k0 s123, k0 s2025, k6 s2025), two of them with
  Hunyuan's 8.6 GB still on the 140 GB GPU. They were rerun at 1024, labelled `trellis2_1024`: 3/3 ok. **No mesh was
  lost.**
- **Hashed:** 936 .ply = 432 raw single-image + 432 Sim(3) copies + 36 Pixal3D-MV raw (`_gen`, generator cube) + 36
  Pixal3D-MV in our object frame.
- **Input problems, kept under the rule (crops.py's own ranking) and flagged:**
  - The ep0 lid crops (k0, k9) show the wooden table with a white strip, not the lid. ep0's lid has only 2,104 observed
    points, so it is barely visible. Their meshes screened at 0.38 or worse.
  - Hands are visible in the ep18 sweeper and dust pan crops, the ep26 pot crops and an edge of the ep24 board-1 crops,
    and in the ep18 / ep24 view sets. ep27 pot masks have GrabCut holes.

## Stage 1 [D]: best per object vs the 13h mesh, and the stage-2 picks

The 13h values are the 13h meshes' 50-seed C4 medians, so the comparison is loose: 6 seeds and best-of-N here. The full
table, with ADD, anchor, W30 and ambiguity, is in `results/stage1_table.md`. The raw data is in
`results/screen/screen6.jsonl`.

| Object | 13h CD-O | Stage-1 best | Δ | Stage-2 picks (CD-O med, W30, ADD med mm) |
|---|---|---|---|---|
| white_pot | 0.2861 | **0.2404** trellis2 ep45 k9 s2025 | **-0.046** | that (0.2404, 0, 4.5); trellis2 ep42 k240 s2025 (0.3094, 0, 5.4); sam3d ep2 k258 s42 (0.3197, 0, 5.8); trellis2 ep42 k237 s2025 (0.3221, 0, 5.8) |
| plastic_dish_rack | 0.4016 | 0.3953 trellis2 ep27 k147 s7 | -0.006 | that (0.3953, 0, 31.3); trellis2 ep27 k147 s123 (0.4260, 0, 29.8); trellis2 ep13 k66 s42 (0.4376, 0, 22.7); trellis2 ep27 k144 s2025 (0.4394, 0, 28.8) |
| mini_dust_pan | 0.2291 | **0.2061** pixal_mv ep39 s2025 | **-0.023** | that (0.2061, 0, 5.6); sam3d ep18 k108 s2025 (0.2203, 0, 6.3); pixal_mv ep39 s123 (0.2230, 0, 5.7); sam3d ep18 k99 s2025 (0.2234, 0, 5.2) |
| beige_cup | 0.2501 | 0.2618 hy21 ep11 k0 s2025 | +0.012 (worse) | that (0.2618, 0, 12.2); pixal_mv ep11 s42 (0.2643, 0, 6.5); trellis2_1024 ep11 k0 s2025 (0.2680, 0, 26.8); trellis2_1024 ep11 k6 s2025 (0.2760, 0, 24.6) |
| white_pot_lid | 0.2177 | 0.2462 pixal_mv ep2 s42 | +0.029 (worse) | that (0.2462, 0, 6.7); pixal_mv ep2 s2025 (0.2667, 0, 7.9); trellis2 ep2 k315 s2025 (0.2675, 0, 7.1); trellis2 ep2 k315 s42 (0.2737, 0, 8.4) |
| mini_sweeper | 0.2220 | 0.2392 pixal_mv ep18 s123 | +0.017 (worse) | that (0.2392, 0, 6.5); sam3d ep18 k162 s123 (0.2394, **1.0**, 89.5); sam3d ep18 k264 s123 (0.2779, **1.0**, 75.2); sam3d ep18 k264 s2025 (0.2807, **1.0**, 87.5) |
| wooden_piece_1 | 0.1872 | **0.1629** pixal_mv ep24 s7 | **-0.024** | that (0.1629, 0, 4.8); hy21 ep24 k3 s2025 (0.1633, **1.0**, 89.7); hy21 ep24 k3 s42 (0.1651, 0.17, 27.0); hy21 ep24 k3 s123 (0.1659, **1.0**, 165.7) |
| wooden_piece_2 | 0.1649 | 0.1600 sam3d ep24 k9 s42 | -0.005 | that (0.1600, 0.17, 17.8); sam3d ep24 k9 s2025 (0.1643, **1.0**, 103.6); sam3d ep24 k6 s2025 (0.1643, **1.0**, 80.2); sam3d ep24 k9 s123 (0.1660, 0.33, 19.2) |

- **Past the rule-(A) bar at stage 1 (-0.020):** pot (-0.046), board 1 (-0.024) and dust pan (-0.023). The rack (-0.006)
  and board 2 (-0.005) are below the 13h value but not past the bar. Beige, lid and sweeper are worse than 13h.
- **The pot's best is an outlier.** trellis2 ep45 k9 s2025 is at 0.2404; the next pot mesh is at 0.3094, and G2's best
  was 0.2852. It may be a real shape gain or 6-seed luck; only the 50-seed audit can tell.
- **W30 / ADD here** belong to the screened copy in our track frame (the Sim(3) copy, or Pixal3D-MV as generated), not
  to the placed copy. The W30 = 1.0 rows (sweeper and board SAM 3D / Hunyuan copies) are Sim(3) fits that landed
  rotated by about 180° on near-symmetric plates; placement re-registers them to library_v3. Pixal3D-MV outputs, in our
  frame by construction, have W30 0 and ADD 4.8-6.7 mm.
- **Per-model medians** of the stage-1 CD-O medians (best in brackets):
  - pot: SAM 3D 0.510 (0.320), Hunyuan 0.621 (0.350), TRELLIS.2 0.489 (0.240);
  - rack: SAM 3D 0.623 (0.556), Hunyuan 0.782 (0.531), TRELLIS.2 0.466 (0.395);
  - dust pan: SAM 3D 0.335 (0.220), Hunyuan 0.388 (0.225), TRELLIS.2 0.504 (0.283), Pixal3D-MV 0.536 (0.206);
  - beige: SAM 3D 0.527 (0.321), Hunyuan 0.459 (0.262), TRELLIS.2 0.620 (0.268), Pixal3D-MV 0.458 (0.264);
  - lid: SAM 3D 1.346 (0.983), Hunyuan 0.449 (0.344), TRELLIS.2 0.396 (0.268), Pixal3D-MV 0.304 (0.246);
  - sweeper: SAM 3D 0.415 (0.239), Hunyuan 0.927 (0.412), TRELLIS.2 0.637 (0.417), Pixal3D-MV 0.455 (0.239);
  - board 1: SAM 3D 0.187 (0.175), Hunyuan 0.174 (0.163), TRELLIS.2 0.335 (0.178), Pixal3D-MV 0.224 (0.163);
  - board 2: SAM 3D 0.173 (0.160), Hunyuan 0.237 (0.203), TRELLIS.2 0.414 (0.314), Pixal3D-MV 0.543 (0.284).

  Best-of-N carries the result; typical outputs are far worse than the 13h meshes.
- **Best per episode (pot):** ep45 0.240, ep42 0.309, ep2 0.320, ep26 0.381, ep27 0.504, ep0 0.670 (lid on the pot).
  Rack: ep27 0.395, ep13 0.438. Dust pan: ep39 0.206, ep18 0.220, ep40 0.225. Sweeper: ep18 0.239, ep31 0.415.
- **Source regeneration.** The 13h dust pan's source crop (ep39 k297) is in G3 again; its G3 hy21 s42 output is not
  among the picks.

## Stage 2 (GT-free placement, T3 fit and trim) -> `../C4-audit/candidates_g3.json`

- **Output.** 32 picks (4 per object, why `cdo_top4`; section 12 lists no ADD extension). Each pick gives a placed copy,
  a T3-fit copy and a trim copy: **94 candidates** (32 placed, 30 t3fit, 32 trim), role `g3_candidate`, needs_place
  false, `cdo_rec` = the stage-1 CD-O median. Per pick details: `results/stage2_picks.json`.
- **Checks.** No candidate's md5 equals any of the 10 public scan files. Every source matched SHA256SUMS before
  placement.
- **Placement (`place.py`, Pixal3D-MV included).** Section 12 says the stage-2 picks are placed, and the C4 audit placed
  the 29 Oct Pixal3D-MV candidates. For the 7 Pixal3D-MV picks placement is close to identity: 0.6-9.8° rotation,
  scale 0.93-1.04, ≤ 1 cm shift [M].
  - Residual to library_v3 [M]: dust pan 2.7-3.0 mm, beige 5.2-6.1, lid 3.2-4.0, sweeper 1.8-2.4, boards 1.8-2.3,
    rack 4.4-5.2, pot 3.5-3.7.
  - **The boards' and the sweeper's placements are near-ties:** the second-distinct start is within 0.01-0.26 mm of the
    best (boards 0.01-0.08 mm). These are near-symmetric plates; prediction H14 (no board passes D1) is the relevant check.
- **T3 fit** (frozen cfg, the pick's own episode's full observed points).
  - 30 of 32 ran with rc 0. **2 failed:** `wooden_piece_1 pixal_mv ep24 s7` and `mini_sweeper pixal_mv ep18 s123`. fit.py's
    final kit `budget_mesh(4096, 4096)` raised "mesh simplification cannot satisfy the budget". They have no t3fit
    candidate.
  - Held-out tmean90 [M] improves on 29 of 30, e.g. lid 6.85 to 2.13 mm and beige 2.30 to 1.57 mm. It gets worse on
    one: the pot pick 1 (trellis2 ep45), 4.73 to 5.23 mm.
- **Trim** (`scripts/trim.py`, rack_trim.py generalised).
  - It deletes faces whose centroid is more than 15 mm from both our observed points and the 13h mesh. The observed
    points are the union over the object's G3 episodes, 1 mm voxel-deduplicated. No hole filling.
  - 13 of 32 trims removed 0 faces. Those trim copies have the same geometry as the placed copy and are marked by a
    `note`.
  - The others removed 35-10,242 faces (≤ 2.4 % of the area). The largest are rack pick 4 (2.4 %), beige picks 3 and 1
    (1.7 %, 1.2 %) and rack pick 2 (1.1 %).
- **Kit budget** (GT-free info, the packer's own simplifier). The placed and trim copies of the 2 Pixal3D-MV picks above
  fail `budget_mesh(4096, 4096)` (`note` in candidates_g3.json). mesh_metric scores such files raw, as the stage-1
  screen did for 18 meshes, but they could not be packed as they are. Every other candidate passes.
- **Paths.** The meshes are in `S/g3/stage2/` (S = the session scratchpad) and in the store at
  `runs/mesh-20261103-g3-2417282/stage2/`, together with `picks.json`, the place / fit / trim JSONs and a copy of
  `candidates_g3.json`.
- **Next step: stage 3.** The 50-seed C4 audit of the 94 candidates, rules (A)/(B)/(C) and D1 against the 13h meshes
  belong to the coordinator; they were not run here.

## Cost (measured from the Vast instance record)

| Run | Instance | Hardware | Time | Cost |
|---|---|---|---|---|
| mesh-20261103-g3-2417282 | 58904222 | H200 NVL, on-demand, $4.033/h, New Mexico (the G2 machine) | 01:59:26-03:47:33 UTC (1.802 h) | **$7.47**: $7.27 time + 71.8 GB down at $2.60/TB ($0.19) + 3.6 GB up ($0.01) |

- **Cap.** $7.47 of the $15 G3 cap; the plan estimated $7-11.
- **Credit.** $94.50 before; $78.91 at 03:50 UTC. The credit includes other sessions' boxes.
- **Ledger.** One `planned` ($11) and one `actual` ($7.47) line under mesh-bold. The helper had appended the actual line
  5 times; the 4 duplicates were removed.
- **Instance.** Destroyed 03:47:33 UTC and confirmed absent in `ops/vast.sh show`.
- **Store.** `runs/mesh-20261103-g3-2417282/` holds the inputs, the screen package, all 936 .ply with the logs
  (`results/`, 5.8 GB) and `stage2/`.

## Deviations and problems

1. **hf CLI 2.2.0 `--include` bug, again** (W-HY21-FAIL). The launcher (`scripts/launch_box_g3.sh`) fetched Hunyuan3D-2.1,
   TRELLIS.2-4B and the Pixal3D files with the Python API after the setup's own downloads. `box_setup.sh` is unchanged.
2. **Freeze checkout on the box.** The exec shell has no git credentials. The fetch of 56d4710 used the onstart.sh header
   pattern with the box's own GH_TOKEN (not printed).
3. **Two Pixal3D-MV view sets were missing or degraded.** ep0 lid had no usable frame. ep18 / ep24 used a stub hands
   file. Both are GT-free and logged.
4. **The ep0 lid crops are wrong** (table, not lid), but they were kept under the rule. Their meshes did not reach
   stage 2.
5. **Failed T3 fits (2) and kit-budget failures (4 files).** All come from Pixal3D-MV board-1 / sweeper outputs; see
   stage 2.
6. **stage2.py crashed twice** on the first failed fit (KeyError 'final'). It was patched to record `fit_failed` and to
   collect the parallel per-object runs with `--merge`; finished outputs were reused.
7. **Predictions (section 12).** H12 (rule-A wins most likely for the dust pan and beige) is half-supported at stage 1:
   the dust pan is past the bar, the beige is worse. H13 (a G3b rack or pot passes A or C) and H14 (no board candidate
   passes D1) await the audit.

## Files

| Path | Contents |
|---|---|
| `NOTES.md` | timestamped working log |
| `inputs/` | crops.py rankings, crop / observed-point / view-set hashes, view-set metadata (`views/`) |
| `results/SHA256SUMS` | the freeze (936 files) |
| `results/gen_logs/`, `results/sim3_fits/`, `results/mv_check.jsonl`, `results/box_logs/` | per-run generation records, Sim(3) fits, the Pixal3D-MV frame check, box log tails, the Vast instance record |
| `results/screen/` | `screen6.jsonl` (468 records), `manifest.tsv`, `screen.log` |
| `results/stage1_table.md` | stage-1 table per object |
| `results/stage2_picks.json` | stage-2 picks: placement, fit, trim, kit-budget details |
| `scripts/` | make_crops.sh, make_views.sh, assemble_g3.py, obs_sub.py, box_g3.sh, launch_box_g3.sh, screen_manifest.py, box_screen.sh, stage1_table.py, stage2.py, trim.py |
| `../C4-audit/scripts/screen6.py` | 6-seed screen (unchanged) |
| `../C4-audit/candidates_g3.json` | stage-2 candidates for the audit |
