# Rack round R (C4 PREREG section 14, addendum 9)

A rack-only repeat of the G2 / G3 generation batches on crops G2 / G3 did not use (R-gen), plus CPU refits of the
primitive rack fitter at its existing settings and variant flags (R-prim). Both feed one stage-2 candidate list for the
coordinator's 50-seed audit. Spec: `../C4-audit/PREREG.md` section 14 (f471f18a), with sections 2, 9, 12 and 13 for the
copy types. Template: G3 (`../G3/`). Working log: `NOTES.md`. Labels: [D] diagnostic, scored against the public scan;
[M] measured without ground truth; [E] estimate.

**The selection is GT-informed.** The R-gen stage-2 picks are best-of-N by public-scan CD-O: the 6 lowest of 390
generated meshes, each screened on 6 seeds. This is the same disclosure as for G2, G3 and Tier B. The public scan stands
in for the hidden one, but taking the minimum of 390 also picks up seed and registration luck, so the stage-1 minima are
optimistic. R-prim fits were not scored. Only the 50-seed C4 audit (stage 3, not run here), rules (A)/(B)/(C) and the
D1 veto decide adoption.

## What ran

| Step | Where | What |
|---|---|---|
| Crops | local CPU, GT-free | `scripts/make_crops.sh` = G3's with `--n 6`. crops.py's **ranks 3-6** on all five public rack episodes (12 / 13 / 26 / 27 / 31). Ranks 1-2 reproduce the G2 / G3 crops exactly, so R's crops are disjoint from them. **20 crops.** |
| Pixal3D-MV views | local CPU, GT-free | `scripts/make_views.sh` = `gen/mv_views.py` with the rack's 29 Oct flags, at-rest fallback, then G3 `assemble_g3.py`. **5 view sets**, one view each. |
| R-prim | local CPU, GT-free | `scripts/prim_rack.py run` on our `obs_all` points of all five episodes, at its current defaults (T_WALL 2.5 mm, CUP_LEAN 1), and once each with the variant flags `--end_draft` (E), `--peg_kappa_free` (K) and `--cup_quad` (Q). `scripts/prim_list.py` drops already-measured files and byte duplicates: **39 fits**. |
| Generation | Vast H200 NVL, `scripts/box_r.sh` | SAM 3D Objects, Hunyuan3D-2.1 (shape) and TRELLIS.2-4B (1536, with a 1024 fallback) on every crop. Pixal3D-MV (1536) on every view set. Seeds 42 / 7 / 123 / 2025 / 31337 / 777. |
| Sim(3) | box CPUs | `gen/sim3_fit.py`, GT-free: each single-image output fitted to 40k of our observed points of the crop's own episode. Pixal3D-MV outputs are already in our object frame. |
| Frame check | box CPUs, GT-free | `gen/mv_check.py` on all 30 Pixal3D-MV outputs: silhouette IoU 0.74-0.98 (`results/mv_check.jsonl`). |
| Freeze | git **cf30b25c** | `results/SHA256SUMS`: 780 .ply, plus the generation, Sim(3) and mv_check logs. Committed before any scan read of these meshes. |
| Stage 1 [D] | box CPUs, after the freeze | `../C4-audit/scripts/screen6.py` (unchanged): seeds 3001-3006, roster emptied, 64 workers, 08:59:47-09:04:07 UTC. **390 records, 0 errors.** |
| Stage 2 | local CPU, GT-free | `scripts/stage2_r.py`. Sources: the 6 lowest stage-1 CD-O R-gen meshes (placed with `place.py`) and all 39 R-prim fits (used as built). Five copy types are made of each (see Stage 2). Output: `../C4-audit/candidates_rack_r.json`. |

- **Crops (crops.py ranks 3-6):**
  - ep12: k18, k27, k15, k12;
  - ep13: k87, k96, k15, k12;
  - ep26: k132, k150, k96, k126;
  - ep27: k129, k132, k84, k87;
  - ep31: k279, k0, k3, k6.

  No other public rack episode exists: `pipeline/mesh_v5.json` lists exactly these five.
- **Flagged inputs, kept under the rule:**
  - **ep31 ranks 4-6 (k0, k3, k6) have crops.py score 0.** MediaPipe found hand joints inside the rack's box, and only 3
    of 97 ep31 frames scored above 0. They are still crops.py's ranks 4-6, so they are kept. One of them (k3) produced
    stage-2 pick 5.
  - Other visual problems:
    - a hand on the cup holder in ep26 k96;
    - skin or table at the right end of ep13 k96;
    - GrabCut notches in several crops.
- **View sets.** Every skin-gated set had a view-0 mask / silhouette IoU below 0.75, so all five use the at-rest set:
  ep12 k24, ep13 k66, ep26 k98, ep27 k146, ep31 k286.
  - ep12 / ep27 have no hands.npz; they use G3's stub (a_offset 1, no valid hand).
  - The 29 Oct probe's ep26 rack view was k138, so no R output repeats it.
- **Integrity.**
  - Generation and R-prim inputs were all ours: crops, view sets, tracks, calibration, library_v3 and observed points.
    The trim also used the 13i rack, which is ours.
  - No scan, mocap, parquet pose or `*_align` file was used, and no eval data.
  - The only scan reads are:
    - the stage-1 screen, after the freeze;
    - the stage-2 md5 check against the scan files.
  - The box checked out cf30b25c and confirmed with `cmp` that its SHA256SUMS matched. The manifest hash-checked all 390
    screened files: 0 mismatches.
  - The screen package reached the box only after the freeze. It is G3's unchanged package (sha256 830b4848…).

## Counts (generated / failed)

| Model | Inputs | Generated / failed | Screened |
|---|---|---|---|
| SAM 3D Objects | 20 crops x 6 seeds | 120 / 0 | 120 (Sim(3) copies) |
| Hunyuan3D-2.1 | 20 crops x 6 seeds | 120 / 0 | 120 (Sim(3) copies) |
| TRELLIS.2 1536 | 20 crops x 6 seeds | 120 / 0 (no out-of-memory, 1024 fallback unused) | 120 (Sim(3) copies) |
| Pixal3D-MV 1536 | 5 view sets x 6 seeds | 30 / 0 | 30 (our object frame) |
| **total** | | **390 / 0** | **390** |

- **Hashed:** 780 .ply in total:
  - 360 raw single-image meshes and their 360 Sim(3) copies;
  - 30 Pixal3D-MV raw generator-cube meshes (`_gen`) and the same 30 in our object frame.
- **R-prim: 39 fits made** (not scored):
  - base 9, E 10, K 10, Q 10.
  - 9 outputs dropped:
    - the base `joint_joint` is byte-identical to the shipped C0 rack, which is measured;
    - in every run, ep26 / ep27 `nomk` equals `full`, because no marker was found there.
  - The base run reproduces the 2026-10-27 clean-up round's t2.5_lean1 files byte for byte. That round scored only
    their joint.
  - The C2 flag combinations (EK, EQ, KQ, EKQ) and the C0b setting flags were not run (NOTES, 07:44Z).

## Stage 1 [D]: best vs the 13i rack, and the stage-2 picks

The 13i rack (G2 #17) has a 50-seed C4 CD-O median of **0.4016**, so the comparison is loose: the R numbers come from 6
seeds and best-of-N. Full table: `results/stage1_table.md`; raw data: `results/screen/screen6.jsonl`.

| Rank | Mesh (stage-2 pick) | CD-O med | CD-O mean | W30 | ADD med mm | anchor med mm |
|---|---|---|---|---|---|---|
| 1 | hy21 ep12 k18 s31337 | **0.3876** | 0.3876 | 0 | 23.9 | 23.7 |
| 2 | trellis2 ep27 k129 s7 | 0.3925 | 0.3932 | 0 | 36.4 | 32.2 |
| 3 | trellis2 ep27 k84 s42 | 0.3967 | 0.3967 | 0 | 31.5 | 31.3 |
| 4 | trellis2 ep27 k87 s123 | 0.3968 | 0.3962 | 0 | 30.7 | 30.6 |
| 5 | hy21 ep31 k3 s777 | 0.4014 | 0.4015 | 0 | 7.8 | 5.6 |
| 6 | trellis2 ep27 k132 s42 | 0.4033 | 0.4042 | 0 | 30.0 | 29.9 |

- **Stage-1 best 0.3876 vs the 13i rack's 0.4016: -0.014.**
  - Rule A's bar is <= 0.3816 (-0.020), and **no R-gen mesh reaches it at stage 1** (0 of 390).
  - 5 of 390 are below 0.4016.
  - G3's best rack was 0.3953.
- **Per model** (best / median of the stage-1 CD-O medians):

  | Model | Best | Median |
  |---|---|---|
  | SAM 3D | 0.507 | 0.606 |
  | Hunyuan | **0.388** | 0.565 |
  | TRELLIS.2 | 0.393 | 0.494 |
  | Pixal3D-MV | 0.512 | 0.611 |

  Pixal3D-MV, given one posed view each, is no better than the single-image models.
- **Per episode (best):** ep12 0.388, ep27 0.393, ep31 0.401, ep13 0.416, ep26 0.449.
  - The score-0 ep31 crops (k0 / k3 / k6) did as well as rank 3 (k279): bests 0.405 / 0.401 / 0.408 vs 0.411.
- **W30 > 0** on 2 of 390 meshes, both ep13.
- **ADD / anchor** here are those of the Sim(3) copy in our track frame, not of the placed copy. The ep27 TRELLIS.2 picks
  sit about 30 mm off in the track frame; placement re-registers them.

## Stage 2 (GT-free copies) -> `../C4-audit/candidates_rack_r.json`

- **Output.** 45 sources (6 R-gen + 39 R-prim) gave **120 candidates**, role `rack_r`, needs_place false, `source`
  R-gen / R-prim:

  | Kind | R-gen | R-prim | Total |
  |---|---|---|---|
  | placed | 6 | 39 | 45 |
  | t3fit | 6 | 35 | 41 |
  | trim | 6 | 4 | 10 |
  | outer | 6 | 12 | 18 |
  | trim_outer | 6 | 0 | 6 |

  - `cdo_rec` is the stage-1 CD-O median for R-gen and null for R-prim.
  - Records: `results/stage2_picks.json`, and `results/stage2_skipped.json` (105 skipped copies, each with its reason).
- **Checks.**
  - No candidate's md5 equals any of the 10 public scan files.
  - No candidate equals an already-measured rack file. `scripts/measured_rack.py` collects 55 sha1 and 27 md5 hashes
    from library_index, the prim / C2 scores, every `candidates*.json` rack entry, and the 13h / 13i / outer racks.
  - No two candidates are byte-identical.
  - Every candidate passes the kit `budget_mesh(4096, 4096)`, so no copy was skipped for the budget.
- **placed.**
  - R-gen: `place.py`, with a residual to library_v3 of 4.4-4.9 mm [M]. The second-distinct start is 8.2-8.8 mm, so
    there are no near-ties.
  - R-prim: the fit as built, already in our frame.
- **t3fit** (fit.py and its frozen cfg unchanged; the observed points of the source's own episode, and ep12 for the
  joint fits, which is prim_rack.py's joint reference episode).
  - R-gen: 6 of 6 ran. Held-out tmean90 [M] improves on 5 of 6, e.g. 3.38 to 2.88 mm. hy21 ep31 is flat (1.74 to
    1.75 mm).
  - R-prim: **fit.py cannot take an input under 12000 faces.** Its first step decimates to work_faces 12000, and
    fast_simplification raises when the mesh already has fewer faces; the prim fits have 958-3568.
    - **Deviation:** these inputs get exact midpoint subdivision (the same surface) until they pass 12000 faces. fit.py
      itself is unchanged.
    - 35 of 39 then fit, and held-out tmean90 changes by -0.10 to +0.01 mm: prims already sit on our points.
    - The 4 ep26 fits (base / E / K / Q) end with fit.py's own final kit-budget error ("mesh simplification cannot
      satisfy the budget"), so they have no t3fit copy.
- **trim** (G3 `trim.py`, unchanged). It deletes faces more than 15 mm from both our observed rack points (the union of
  obs_all for eps 12 / 13 / 26 / 27 / 31, the R crop episodes) and the 13i rack.
  - R-gen: removes 22-2201 faces (at most 0.41 % of the area).
  - R-prim: a no-op on 35 of 39. Only the 4 ep26 fits lose faces (4.4-4.6 % of the area), near x +73 mm, z -117 mm.
- **outer** (`../C4-audit/scripts/outer_shell.py`, unchanged).
  - TRELLIS.2 picks: drops 1478-1996 small fragments, 0.4-1.1 % of the area.
  - Hunyuan picks: drops 1-3 fragments.
  - R-prim: drops the floating marker balls of 12 fits with markers (9 per-episode `full`, 3 `joint`); a no-op on
    the other 27.
  - No nested shell was found in any source.
- **trim_outer.** Outer applied to the trim. It exists for the 6 R-gen picks. For R-prim it is a no-op: either there is
  no trim copy, or the ep26 trims are a single body.
- **Paths.** The meshes are in `S/r/stage2/out/` (S = the session scratchpad) and in the store at
  `runs/mesh-20261103-r-63eb2c5/stage2/`, with the place / fit / trim / outer records and a copy of the candidate list.
  The R-prim fits are also committed in `results/prim/`.
- **Next step: stage 3.** The coordinator runs the 50-seed C4 audit of the 120 candidates, then rules (A)/(B)/(C) and D1
  against the 13i rack (CD-O 0.4016, W30 0, anchor 3.78, ADD 4.30). None of it was run here.

## Cost (measured from the Vast instance record)

| Run | Instance | Hardware | Time | Cost |
|---|---|---|---|---|
| mesh-20261103-r-63eb2c5 | 58934345 | H200 NVL, on-demand, $3.90/h, New Mexico | 07:41:06-09:09:37 UTC (1.475 h) | **$5.95**: $5.75 time + 71.8 GB down at $2.60/TB ($0.19) + 3.1 GB up ($0.01) |

- **Cap.** $5.95 of the $10 cap; the plan was ~$6.5 [E]. The idle limit was 130 min, keeping the worst case under $10.
- **Credit.** $73.73 before; $67.34 at 09:10 UTC, which includes other sessions' boxes. It never came near $15.
- **Ledger** (mesh-bold): one `planned` line ($8) and one `actual` line ($5.95). The helper appended the actual line 4
  times; the 3 duplicates were removed with one guarded rewrite.
- **Instance.** Destroyed at 09:09:37 UTC and confirmed absent in `ops/vast.sh show`.
- **Store.** `runs/mesh-20261103-r-63eb2c5/` holds:
  - the inputs and the screen package;
  - all 780 .ply with their logs (5.0 GB);
  - `stage2/`.

## Deviations and problems

1. **fit.py on primitive fits** (above). Inputs under 12000 faces get exact midpoint subdivision before the unchanged
   fit.py. Without it, no R-prim t3fit copy could exist. The first stage-2 attempt failed on 8 prims; it was stopped and
   rerun.
2. **hf CLI 2.2 `--include` bug, again** (W-HY21-FAIL). The launcher's Python-API fetch fixed it (HYFIX-OK), as in G2 /
   G3.
3. **The ep31 score-0 crops were kept** (ranks 4-6 by crops.py's own ranking, as PREREG s14 says). Every view set is a
   single view, because the rack's lattice defeats the GrabCut mask (view-0 IoU 0.51-0.69).
4. **R-prim scope is an interpretation of "existing settings and existing variant flags".** It covers the current
   defaults plus each C2 flag on its own (NOTES, 07:44Z). The 4 combinations and the C0b setting flags would add up to
   48 more fits.
5. **Exec calls.** The store push returned HTTP 524 after 100 s, but the push finished (PUSH-RC 0). The ledger
   duplicate-line bug and HF 502-after-landing recurred; both were handled as in G3.
6. **Prediction [H18]** (P(some candidate reaches <= 0.3816) ≈ 0.4) awaits the audit. No R-gen mesh reached it even at
   stage 1 (best 0.3876), so it now looks less likely [E]. The copies would have to gain ≥ 0.006, or a different seed
   set would have to favour a pick.

## Files

| Path | Contents |
|---|---|
| `NOTES.md` | timestamped working log |
| `inputs/` | crops.py rankings, crop / observed-point / view-set hashes, view-set metadata (`views/`) |
| `results/SHA256SUMS` | the freeze (780 files) |
| `results/gen_logs/`, `results/sim3_fits/`, `results/mv_check.jsonl`, `results/box_logs/` | per-run generation records, Sim(3) fits, the Pixal3D-MV frame check, box log tails, the Vast instance record |
| `results/screen/` | `screen6.jsonl` (390 records), `manifest.tsv`, `screen.log` |
| `results/stage1_table.md` | stage-1 table |
| `results/prim/` | R-prim fits (`base/`, `E/`, `K/`, `Q/`: meshes, build records, logs), `prim_list.json`, `prim_list_dropped.json`, `measured_rack.json`, prim_rack.py sha1 |
| `results/stage2_picks.json`, `results/stage2_skipped.json` | stage-2 per-source records (placement, fit, trim, outer, kit budget) and the skipped copies with reasons |
| `scripts/` | make_crops.sh, make_views.sh, box_r.sh, launch_box_r.sh, screen_manifest_r.py, box_screen_r.sh, stage1_table_r.py, measured_rack.py, prim_list.py, stage2_r.py |
| `../C4-audit/candidates_rack_r.json` | the 120 stage-2 candidates for the audit |
