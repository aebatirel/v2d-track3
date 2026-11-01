# C2 / Track P (water_pitcher): adversarial verification

Written 2026-10-31, 20:40-21:05 UTC, against the track as pushed at 416a4fc. CPU only, $0; no Vast box, no ledger line.
The verifier ran no mesh_metric scoring, read no scan, mocap or parquet pose, and changed no track file. It used only
the track's repo files, its scratch outputs (`SCR/cdo_c2/P/`), the C0b box files the track used, recorded score lines,
and its own GT-free re-runs (in `SCR/cdo_c2/P_verify/`).
`SCR` = `/tmp/claude-0/-home-user-v2d-track3/90d4009c-b597-536b-9d55-58f81afca135/scratchpad`.
Tags: [M] measured without ground truth; [D] recorded scan-scored value (none re-run here).

## Verdict

**There is no blocking finding.** The track's outcome stands:
- the pick is not a WIN [D];
- the AUC guard was correctly not run;
- the pick is not adopted, and library_v3 stays on eval 20;
- H-P is falsified.

The pre-registration order, the pick, the single scoring, the gates and the mesh bytes all check out.

Several statements in RESULTS and the result summary are wrong or overstated (N1-N6 below), and one citation is
imprecise on a constant that binds (N3). None of them changes a decision.

## Confirmed

### 1. Pre-registration came before building and scoring

Commit times are from `git log`. Push times are from the `origin/claude/bold-albattani-6qmxsv` reflog.

| Step | Commit | Pushed | Evidence that the next step came later |
|---|---|---|---|
| PREREG | 5982c31, 18:33:53 | 18:33:55 | no build before 19:17 (NOTES; `SCR/cdo_c2/P/cand/*` mtimes 19:19-19:23) |
| A1 | 07d2536, 18:38:43 | 18:38:46 | smoke test 18:39:38; candidate builds 19:17-19:24 |
| A2 | cc63fc2, 19:50:24 | 19:50:27 | text repair 1230b6d pushed 19:50:52; filter applied 19:51:38 (`keep_a2.log` mtime) |
| A2 pick | 3ded2f9, 20:04:19 | 20:04:23 | see below |
| scoring | d8ff6ac, 20:20:53 | 20:20:55 | |

- **When the scoring started.** `score.log` and `score_p.jsonl` were written at 20:20:29.72. mesh_metric's `secs` (958.0)
  is counted from the start of `evaluate()`. So `evaluate()` started at about 20:04:31.7, 8.7 s after the pick was pushed.
  This is consistent with commit, push and score run back to back. It cannot be proven to the second.
- **The A2 repair changed no rule.** The 1230b6d diff only restores the 4 backticked names that the heredoc had emptied.
- **What came before the PREREG** (allowed by PREREG section 9): the obs points, the local `obs_c0b.sh` runs and the
  `diag_pitcher.py` preview.

### 2. Constant origins (against C0b `AUDIT.json` and `REPLACEMENTS.json`)

**Every audit id cited in the PREREG table exists, with the class the PREREG states:**
- G: 106, 108-115, 119, 120, 124, 125, 127, 129, 136, 137, 139, 141, 143, 148, 152-154;
- O: 116, 123, 126, 150, 151;
- GEN: 107 (tie 1.0), 131 (`base_t`);
- NEVER: 122;
- TH: 128;
- A6: 117 (3 sigma), 121, 142;
- KEEP: 118, 130, 132, 135, 138, 140, 145, 149;
- LIB: 133, 134;
- RULE: 155;
- INPUT: 161 (flag F4).

**The lathe arguments are C0b's own.** They match `C0b/jobs/c0b_tasks.py:122` `lathe_args`: `--tie 1.0 --floor base_t
--t_fallback T --tmax 0.008 --tmin 0.0015`, plus `--app_d` = 3 sigma.

**Measured values [M]:**
- sigma: 1.733 mm (ep21), 1.739 mm (ep22), 1.736 mm (merged), inside the C0b clamp of [0.5, 3] mm;
- app_d: 5.198 / 5.218 / 5.208 mm;
- thickness chain: thickness.py median 5.99 mm (n = 877, pooled 878) for ep21 and merged; -1 for ep22 (n = 1,
  t0_C0b absent). `params_p.py` implements C0b 3.3 as written.
- The pick did not use the fallback: `t_src` is `measured`, from 6 two-wall bins.

**Constants that are new in this track** (none is in the C0b audit):

| Constant | Where | Effect on the scored mesh |
|---|---|---|
| LINK 8 mm (A2) | `keep_connected.py` | none: non-binding, see section 3 |
| REST_DH 10 mm | `rest_axis.py` | none: A1 candidates only, none picked |
| support_fill still windows: 3 mm, 2 deg, 10 frames | `rest_axis.py` | none: A1 candidates only |
| centring at the mean height | `lathe_axis.py` | none: A1 candidates only |
| rest-check statics | `rest_check.py` | none: reported only |

### 3. The pick, recomputed

- **From the stored tables.** Applying the section 4 rule to `results/pick_A2.json` gives `ep22_g1` at 6.732 mm. On
  `pick_A1.json` it gives `ep22_g1` at 6.624 mm. The track's picks reproduce.
- **Independent re-run [M].** `obs_fidelity.py` on ALL, using the same pass-B points and `cand_a2` files, gave:
  - ep22_g1: 3.903 + 2.829 = **6.732 mm**;
  - ep21_g1: 4.501 + 2.947 = **7.448 mm**.

  Both are identical to the track's values.
- **The exclusions cannot change the pick.** merged_g1 (8.095) and ep21r_g1 (8.640) are not watertight, and both sum
  higher than 6.732. Every candidate's `budget_mesh` result is 4096 faces and 2043-2060 vertices, so all pass.
- **The A2 filter output is correct.**
  - `cand_a2/ep22_water_pitcher_g1.glb` sha256 = the committed pick.
  - The 8 unchanged candidates are byte-identical to `cand/` (sha256 prefixes match).
  - The 4 changed ones each lost one 82-85 cm2 piece at about (231, 227, -181) mm.
  - In ep21r_g1, a 2-face piece 73.5 mm from the largest component is kept through a 0.0 mm link to another component.
    That is correct under the transitive rule.
- **LINK is not binding [M].** Within the pick, the lathe body is 0.3 mm from the splat and the clutter piece is
  228.9 mm away. Any LINK between 0.3 and 228.9 mm gives the same pick.
  - In the other three filtered candidates, the in-object gaps are at most 2.4 mm and the clutter is 229-285 mm away.

### 4. Inputs equal the C0b box's

- **Point files.** The sha256 of the pass-B files used match the track's claims:
  - ep21: `4774f750...a09dc`, 4,253,726 points;
  - ep22: `b5334be0...0ba20`, 4,625,229 points.
- **Local and box pass A are the same data.** Local pass-A ep21 pitcher vs the box's: `pts`, `cam`, `frame`, `lo`,
  `hi`, `vox`, `hits` and `free` are array-equal. In `args`, only the path strings differ. All numeric options are
  equal: `roi_cube` 0.3, stride 2, `table_band` 0.008, vote 4 mm / 4 / 10 / 3 / 0.5, hand 30 / 45 / 150 mm, edge 20 mm.
- **Input hashes.** The box's `inputs_SHA256SUMS` equals our sweep tracks, hands and calib for ep21 and ep22.
  - Tracks: `7e4dae9c`, `50acd616`.
  - Hands: `8143230b`, `77b56f43`.
  - Calib: `23e2d9c4`.
- **Cube guard.**
  - Pitcher shares: 0.0167 % (ep21 B) and 0 (ep22 B), so no rebuild.
  - Blue-cup pass A was rebuilt at 0.45 m, as the rule says. ep21 is still 0.162 % after the rebuild, which the
    rebuild-once rule allows.
- **Pass B carving.** ep22 pass B carves `blue_cup=pts/A/ep22_blue_cup.npz`, the 0.45 m rebuild.

### 5. There was one scoring

- `results/score_p.jsonl` holds 1 line, sha1[:16] `478b9fb3cc65c841`.
- The sha1[:16] of all 24 candidate files (in `cand/` and `cand_a2/`) were searched for across `docs/`, `results/` and
  every json, jsonl and log under `SCR`. Only the pick's sha appears, and only in this track's score files.
- `SCR/cdo_c2/P/logs/score.log` is identical to `results/score_p.log`.
- `mesh_metric.py` is unchanged since 15b860d (sha1 `e161e892...`). That is the version behind the library baseline
  record.

### 6. The gates were applied exactly

**Baseline** (`results/baseline_library.jsonl`, sha `2ec881574c17ad01`) [D]:
- CD-O at seed 20000161: 0.8942;
- 6 seeds 20000161, 11, 22, 33, 44, 55 with add_mm 7.63, 8.52, 7.89, 8.43, 6.31, 8.05, so add_med 7.97;
- 0 flips.

**Pick** [D]:
- CD-O at seed 20000161: 1.1600 against the 0.8742 threshold, a FAIL;
- add_mm over the same 6 seeds: 10.64, 10.91, 11.70, 11.42, 13.49, 9.43, so the median is (10.91 + 11.42) / 2 =
  11.165, against the 9.97 threshold, a FAIL;
- flips 0 / 32, a PASS.

So it is not a WIN, and H-P is falsified (it also needed CD-O <= 0.60).

**Symmetry.** The kit's `tracks.json` declares only beige_cup and blue_cup (axial) and white_pot_lid (half-turn) as
symmetric, so the pitcher has no flip exemption.

**AUC guard.** It was not run, as PREREG sections 6 and 7 require (guard only after a WIN; adoption needs both).
- The unused runner differs from C0's `run_auc_guard.sh` only in the mesh dir, the output dir, the twin list (21, 22)
  and the base-reuse path.
- `guard_eval_p.py` keeps C0's thresholds.

### 7. The scored bytes are the committed bytes

| File | sha256 |
|---|---|
| `meshes/ep22_water_pitcher_g1_a2.glb` (working tree, `HEAD` and `3ded2f9`) | `fadf3e7b...d1f6` |
| `SCR/cdo_c2/P/cand_a2/ep22_water_pitcher_g1.glb` | `fadf3e7b...d1f6` |

- The mesh's sha1[:16] is `478b9fb3cc65c841`, which is the sha in the score record.
- The record's path is the repo file. That file's mtime (20:04:07) is earlier than the pick commit.

### 8. The frame is not aligned to library_v3

- No track script aligns, registers or ICPs to library_v3:
  - `obs_fidelity` runs with no ICP;
  - `score_p.py` passes no `frame_tf`;
  - `lathe_obs` and `lathe_axis` work in the track frame.
- The track frame is the library_v3 pitcher frame through the library-seeded sweep tracks (C0b 161, flag F4,
  disclosed). library_v2 and library_v3 `water_pitcher.glb` are byte-identical (sha256 `9f16ed2a...`).
- library_v3 is read only for:
  - the reported-only fidelity row and rest rows;
  - the unused guard base dir.

### 9. Other claims checked [M]

| Claim | Check |
|---|---|
| fit-axis rotational consistency | 9.15 (ep21), 12.29 (ep22), 10.06 (merged) mm |
| rest-axis rotational consistency | 10.4, 13.19, 11.64 mm, so >= 9 mm on every axis |
| the two episodes' fit axes differ by about 20 deg | 20.09 deg |
| resting up is about 38 deg from z | 37.9-39.0 deg |
| ep21 and ep22 resting ups differ by about 1 deg | 1.32 deg |
| one-sided views | azimuth cover 90 / 60 deg |
| clutter clusters | ep21 365 points, ep22 7,896 points |
| per-episode fidelity | values as in RESULTS |
| rest verdicts | as in the RESULTS table |
| board effect had it shipped, +0.0074 [E] | (1.16 - 0.8942) / 36 = 0.0074 |
| the subject is an elephant-shaped watering can, not near-axial | our ep22 crop `SCR/crops/ep22/water_pitcher_k174.png` |

## Nonblocking findings

**N1. "87-89 deg from the resting up" holds only for ep22's axis.**
- Recomputed axis-to-rest-up angles (undirected):
  - ep22's fit axis, the pick's: 88.2-89.2 deg;
  - ep21's fit axis: 80.5-81.3 deg;
  - the A1 preview axes on `obs_all`: 82.4 deg (ep21) and 81.7 deg (ep22), not "about 87 deg" as A1 states.
- The conclusion (a near-horizontal axis, not the vessel's axis) is unaffected.
- The text should read "81-89 deg".

**N2. "80-85 % of points are more than 3 sigma outside any lathe" is true only for lathe_obs's own fit-axis lathe.**
- `diag_c0b.json` gives `app_frac` 0.849 / 0.803 for that lathe.
- For the rest-up lathes, the build logs give these shares of the downsampled points as appendage points:
  - ep21r: 88,919 / 264,610 = 34 %;
  - ep22r: 89,929 / 244,235 = 37 %;
  - mergedr: about 23 % [E].
- RESULTS section 2 says "that lathe", which is correct. The summary's "any lathe" is not.

**N3. tmax is cited to the wrong audit id, and it binds.**
- The PREREG cites audit id 121 for `--tmax 0.008`. Record 121 covers only `--tmin`.
- The 8 mm clip traces to C0b's `lathe_args` and REPLACEMENTS ids 16 / 40 / 58 (A6, "wall clip (two voxels)").
- tmax is binding for the pick: lathe_obs measured 11.24 mm on 6 two-wall bins (`diag_c0b.json`), and the wall was
  clipped to 8.0 mm. It also binds for every rest-axis build.
- The value is allowed (C0b's own). Only the citation is imprecise.

**N4. Every lathe_obs appendage splat is inside out, not just the pick's.** Signed volumes (trimesh, `process=True`):

| Mesh | Splat or appendage components | Lathe body |
|---|---|---|
| pick | -964.0 cm3 | +210.4 cm3 (total -753.6) |
| other g1 candidates | negative in every one | |
| `meshes/library_c0/blue_cup.glb` | 4 appendages, -5.3 to -8.5 cm3 | |
| C0b blue cup | 5 components, -4 to -60 cm3 | |
| C0b beige cup, adopted for pack 10 | 2 components, -33.9 and -39.0 cm3 | |

- The `-754 cm3` in the failure list is the whole mesh. The splat alone is -964 cm3.
- CD-O and AUC do not depend on face orientation. mesh_metric reports `abs(volume)` (753.6), which hides the
  inversion.
- Any mass, COM, rest or simulator use of lathe_obs meshes is affected. This is out of P's scope; it is for the
  C0b / E0b owners and `lathe_obs.py`'s splat step.

**N5. The rest-up lathes standing on ep22 is largely in-sample, and the summary leaves out ep21.**
- On ep22 the result is by construction: the ep22r axis is the mean resting up at those same 9 ep22 frames, and the
  lathe is built from ep22's points.
- On ep21's 8 rests (`rest_pick_ep21.json`), ep22r_g0 passes 1 of 8 and mergedr_g0 passes 3 of 8. Most margins are
  0.7-5.5 mm against the 3 mm rule.
- The rest-up lathes also float 4-14 mm above the table at the rest frames (`gap_mm`). The base sits at the lowest
  observed point, about one table band up.
- RESULTS' table carries the ep21 counts. The result summary's "STAND at all 9 ep22 rests" should add these caveats.

**N6. The board-weight bound is understated.** At 1 pair of 36:
- a pitcher at the generator range's best (0.38 cm, a figure the track itself discloses) would move the board by
  (0.8942 - 0.38) / 36 = **-0.014** [E];
- a perfect mesh would move it by -0.025.

So "at most about -0.01" is too low. The ranking below the rack (5 pairs at 0.456) still holds.

**N7. The switch of input source was not written into the PREREG.** PREREG section 2 says the points are "built here
by `scripts/obs_c0b.sh`". The track used the C0b box's pass-B files.
- The switch is recorded in NOTES (19:10) and RESULTS only.
- Equivalence is proven for ep21 pass A (section 4 above). For ep22 and pass B it rests on the same code (obs_points.py
  unchanged since 957a2aa, before the box code 00e8584) and equal input shas.

**N8. Wording.**
- "mesh_metric sha1 478b9fb3cc65c841" is the mesh's sha1[:16], computed by mesh_metric. It is not a hash of
  mesh_metric.py.
- "That sheet is open on the far side": the splat is watertight. It is a closed, thickened shell of the seen surface;
  what is missing is the object's unseen side, not a hole in the shell.

**N9. The A1 rationale came from S-input-built points.** The `obs_all` preview points used library_v3 as ROI and as
the carving source (C0b 133 / 134, S-input).
- This is disclosed, and A1 only added candidates. None of them was picked, so the scored mesh is unaffected.

**N10. An extra GT-free observation [M], for H-P2 planning.** The lathe body is 28.8 % of the pick's surface area.
About 80 % of it lies more than 5 mm from the splat: the median distance is 12.2 mm and P90 30.8 mm (5,000 samples,
nearest splat vertex). Only about 2 % lies within the splat sheet.
- So more than a quarter of the area that the kit's CD-O samples is a horizontal-axis solid of revolution placed mostly
  off the observed surface.
- [H]: this adds to the "one-sided splat" explanation in RESULTS section 5.
- Falsifier (one pre-registered scoring of a new mesh): a g1 variant without the lathe body, i.e. the splat alone, does
  not score a lower CD-O than the same splat with the body.

## Files read or produced by this verification

**Repository:**
- this file;
- `PREREG.md`, `NOTES.md`, `RESULTS.md`, `scripts/*`, `results/*`, `meshes/*`;
- C0b `AUDIT.json`, `REPLACEMENTS.json`, `jobs/c0b_tasks.py`, `results/box/guard/*`;
- C0 `scripts/run_auc_guard.sh`, `guard_eval.py`;
- `results/baseline_library.jsonl`.

**Scratch** (`SCR/cdo_c2/P_verify/`):
- `fid_ep22_water_pitcher_g1.out`, `fid_ep21_water_pitcher_g1.out` (the fidelity re-runs);
- `cand_sha1.txt` (the candidate hashes used for the scoring search).
