# C0b / E0b verify_0: adversarial integrity check

- **When and where.** 2026-10-31, 22:31-22:55 UTC, on the shared cloud VM (4 loaded cores, my jobs at nice 19). CPU only, $0.
- **Lens.** Integrity:
  - the constants the builds actually used (command lines, build records, logs), re-audited independently;
  - whether any scan-derived or unknown constant remains in the shipped meshes;
  - PREREG `8174998` pushed before the builds and the scorings (git and remote reflog times);
  - picks recomputed from the raw fidelity rows;
  - one scoring per mesh;
  - the AUC guard applied exactly as C0's;
  - no alignment to library_v3.
- **Inputs.** The repo at `9d644e4` and the pulled box trees in the scratchpad: `c0b/box/dl/runs/mesh-20261031-c0b-00e8584` (C0b) and `e0b/box/dl/runs/mesh-20261031-e0b-c8f1c33` (E0b).
- **Ground truth.** I opened no scan, mocap, parquet or `*_align` file. I read only [D] records that already existed (`results/score_c0b.jsonl`, the `score_registered.py` JSONs in `results/auc/` and `SCR/cdo_c0*/runs/`, `results/baseline_library.jsonl`) to recompute rules. I scored nothing.
- **My scripts.** Scratchpad `c0b_verify0/code/`: `repick.py`, `repick_e0b.py`, `guard_re.py`, plus a regression re-run in `c0b_verify0/regress/`.
- **Labels.** [M] measured here without ground truth; [D] recomputed from existing scan-scored records; [H] hypothesis.

## Verdict

**No blocking finding.** The two adopted objects (white_pot, beige_cup) and their E0b eval meshes follow PREREG `8174998`:
- timing holds;
- every pick and the ship rule reproduce from raw rows with independent code;
- the four scorings are one per distinct mesh;
- the guard numbers and rule reproduce;
- every shipped or guarded mesh is byte-identical to the file the builder wrote (no alignment).

One claim needs a correction before pack 10 is described as free of scan-derived constants (N1). The other findings correct records.

## 1. Timing [M] (commit time / push time from the remote-tracking reflog)

| Event | Time (UTC) | Evidence |
|---|---|---|
| AUDIT committed | 16:57:20 | `9451062` |
| PREREG committed / pushed | 17:31:39 / 17:31:51 | `8174998`, pushed with `0d9a8b7`. It is the only commit that touches `PREREG.md` or `REPLACEMENTS.json`, and the working tree is clean for both. |
| C0 regression rebuilds written | 17:39-17:41 | file mtimes in `SCR/c0b/regress` (after the PREREG push) |
| DEVIATIONS_PUBLIC (D1-D10) committed | 18:00:13 | `ade3608`, never edited after |
| Box code committed / pushed | 18:21:51 / 18:21:53 | `00e8584`. The box log records commit `00e8584`, dirty=0. |
| C0b box created / first build | 18:22:58 / 19:27 | NOTES, `c0b_job.log` |
| Box `select`, then the `report` stage (library_v3 and C0 fidelity) | 19:31:43 / 19:31:43-19:32:02 | `c0b_job.log`: the report stage starts after `select` |
| Picks committed / pushed | 19:55:50 / 19:55:54 | `9f99ae0` |
| First scoring command / first scoring log | 19:56:33 / 20:05:22 | `SCR/cdo_c0b/score.sh`, `score_white_pot.log` mtimes |
| Guard runs | 20:17-20:28 | `SCR/cdo_c0b/runs/c0b/*.json` mtimes |
| Adoption pushed | 20:30:54 | `d84bc87` |
| DEVIATIONS_E0B (X1-X15) committed | 21:18:35 | `acfd7b8`. This is before the E0b box; X14 and X15 were written during the dry runs. |
| E0b code pushed / box created | 21:30:42 / 21:32 | `c8f1c33`. The box log shows dirty=0, and the box stages `fref` and `select` run before `report`. |

PREREG 3.10's regression check ran before any C0b build. The E0b stage ran after the section 8 verdict, as PREREG 9 "Timing" requires.

## 2. Constants the builds actually used (independent re-audit)

**Sources.** Ground truth here is what ran, not what the scripts' defaults say:
- the E0b box command lists (`commands/build.txt`, `obsA.txt`, `obsB.txt`, `report.txt`);
- the `c0b_options` and `c0b` blocks the builders wrote into each build record;
- `params.json`;
- the markers JSONs;
- `t0_c0b.json`.

### 2.1 What ran for the shipped meshes [M]

| Mesh | Command line as run (paths shortened) | Values in the build record |
|---|---|---|
| E0b white_pot `pot/ep3/thick` (ships on evals 1, 3, 5, 6, 8, 28; md5 `073872f4...`) | `prim_potlid.py pot B/ep3_white_pot.npz ... --variant thick --c0b --sigma 0.00141528 --t_fallback 0.0045594 --bar_t0 0.0045594 --markers_json markers/ep3.json --axis_cache ...` | <ul><li>t measured 2.61 mm from 11 two-wall bins, doubled to 5.22 mm;</li><li>h_o 0.5, reach_rel 0.5, TIE 1.0;</li><li>app_d 3 sigma = 4.25 mm;</li><li>handle T = t0_C0b 4.6 mm (prior: no side evidence);</li><li>32 gmg balls, r 10.4-12.48 mm, 0 stems;</li><li>markers settings sha `488ac3b6`.</li></ul> |
| E0b beige_cup `beige/ep8/g1` (ships on evals 8, 10; md5 `0d926da1...`) | `lathe_obs.py B/ep8_beige_cup_sep.npz ... --tie 1.0 --floor base_t --t_fallback 0.00348925 --tmax 0.008 --tmin 0.0015 --app_d 0.00280755` | <ul><li>t measured 2.08 mm from 23 two-wall bins;</li><li>floor base_t, TIE 1.0.</li></ul> |
| Observed points behind both | `c0b_obs.sh` -> `obs_points.py ... --roi_cube 0.30`; pass B adds `--others_pts <co-object>=<its pass-A npz>` | <ul><li>Cube guard: 0 near-face points on the ep3 pot and ep8 beige files.</li><li>M_sep on eval 8 kept 110 of 110 frames: the mask removed nothing there.</li></ul> |

**library_v3** appears only in the 27 `report.txt` lines, which run after `select` [M]. The E0b staging asserts that no input name contains `scan`, `mocap`, `_align`, `.parquet`, `/mesh/` or `library_v`. The staged inputs are:
- eval tracks and hands;
- calibration;
- the kit;
- `t0_c0b.json`;
- the C0b public candidates used as frame references.

**t0_C0b = 4.559 mm** [M]. This is A.1: the median over the 9 per-object medians (the pot's own median, 4.559, is the 5th of 9).
- It is fittable: 6 objects have at least 200 measurements.
- `origin: fitted:own`; it is not the 2.5 mm fallback.
- The E0b copy is byte-identical (sha256 `eeec0910...`).

### 2.2 Code paths [M] (`prim_potlid.py` blob `c98344f`, identical at `00e8584`, `c8f1c33` and HEAD)

With `--c0b --markers_json`, the pot path never reaches any of these:
- `MK_R0` / `MK_RMIN` / `MK_RMAX` / `MK_*`;
- `T_MIN` / `T_MAX`, the 4 mm fallback, `BAR_T0` 5 mm;
- `h_O` 0.6;
- `rmax + 60 mm`;
- the old marker acceptance.

`build_pot` returns through `gmg_markers()` before the old marker block. The remaining literal `APP_D` uses (lines 603, 761, 781) sit only in the `tsdf` and old-marker branches, which C0b never runs.

In `lathe_obs.py`, `--floor base_t` skips the S-dev floor rule (line 269), and `--t_fallback` replaces the 3 mm fallback. In `obs_points.py`, `--roi_cube` and `--others_pts` exclude `--roi` and `--others` (`p.error`).

### 2.3 Result

- **No scan-derived (S) value reaches either shipped mesh** [M]. This is consistent with AUDIT `9451062` and REPLACEMENTS: every S record is replaced, never selected, or sits on an unused path.
- **"No unknown constant" cannot be confirmed.** Constants of unknown or "informed" origin remain in what built the shipped meshes:
  - **(a) By design and disclosed (PREREG 3.1, 3.8, 12):** 40 KEEP records of class U, declared generic post hoc. One of them is U-suspect: the obs_points `--table_band` of 8 mm. Those on the shipped meshes' paths:
    - obs_points: `other_r`, `edge_thr`, vote settings, per-frame table refit, `table_plane thr`;
    - prim_potlid: open-end test, rim window, body extent, rim height, bar width, bar ends, handle hole, handle cluster size;
    - lathe_obs: `app_min`, cap-in margin, appendage splat.
  - **(b) Outside the audit's scope and not disclosed in C0b** (see N1). The C0b audit covered `prim_potlid`, `prim_rack`, `lathe_obs`, `obs_points`, `obs_fidelity` and `recon_mesh`. It did not cover these imported modules:
    - `gmg/markers.py`: FROZEN settings, including the 6/9/13/17 mm vote neighbourhoods and the 15,000 seeds;
    - `gmg/thickness.py` with `autokit/shell.py`: the t0 and the shipped pot's handle T;
    - `gmg/bundle._sigma`: APP_D;
    - `autokit/parts.py`: sphere fits; `robust_scale` for the lid;
    - `c0b_prep.py`: M_sep and the cube guard. Its values are pre-registered in PREREG 3.4 and 10.

    REPLACEMENTS takes the gmg values on gmg's labels.
  - **(c) Not a constant, disclosed (record 161, flag F4):** the public sweep tracks and the eval evperc tracks are seeded with library_v3. So the object frame, and therefore the ±0.30 m cube centre, comes from library_v3.

## 3. Picks recomputed [M] (own code, raw rows)

**C0b public.** `repick.py` reads `check/*.json` (watertight raw, kit budget) and `fid/*/*@all.jsonl`. It sorts by (sum_mm at 3 dp, raw faces, label bytes).

| Object | Pick | sum_mm | Runner-up | Equals box and local |
|---|---|---|---|---|
| white_pot | pot/ep43/fit | 3.407 | pot/ep43/nostem 3.407 (same faces 25922, label order) | yes |
| plastic_dish_rack | rack/ep13/full | 33.32 | rack/ep13/nomk 37.811 | yes |
| blue_cup | cup/ep21/g1 | 3.377 | cup/ep22/g1 3.518 | yes |
| beige_cup | beige/ep11/g1 | 3.91 | beige/ep11/g0 5.167 | yes |

- All candidates are eligible: 32/12/5/2 of 32/12/5/2.
- The pot ALL set includes ep0 (9 per-episode rows).
- The repo copies' sha256 equal the box candidate files and `picks.json`.

**E0b.** `repick_e0b.py` re-derives the frame thresholds from the 38 `fref/*.json` rows: 3 x the maximum per statistic, with an axis checked only when the neighbouring eigenvalue ratio is below 0.8.
- Pot thresholds: centroid 108.56 mm, median distance 12.92 mm, axes 42.1 / 26.6 / 36.2°. These equal `frame_thresholds.json`.
- Excluded: only `cup/ep20/g1` and `cup/ep20/g0` (median distance 7.28 and 16.61 > 5.41 mm).

| Object | Pick | sum_mm | Runner-up | C0b public on ALL | Ratio (rule (e) threshold 0.85) | Ships |
|---|---|---|---|---|---|---|
| white_pot | pot/ep3/thick | 3.275 | pot/ep3/fit 3.319 | 3.602 | 1.0998 | E0b |
| beige_cup | beige/ep8/g1 | 3.322 | beige/merged/g1 3.403 | 3.277 | 0.9865 | E0b |
| lid (info) | lid/ep1/a6b2_nomk | 2.976 | lid/ep1/a6b1_nomk 2.979 | none | - | not adopted |
| blue cup (info) | cup/merged/g1 | 5.033 | cup/ep33/g1 5.154 | 5.181 | 1.0294 | not adopted |
| rack | none (run crashed) | - | - | 19.067 | - | not adopted |

**Packaging** [M]:
- `meshes/library_e0b` differs from `library_v3` and `library_e0bx` differs from `library_v3x` only in `white_pot.glb` and `beige_cup.glb`. The README and `*.recon.json` / `*.v5.json` sidecars are not copied, by design.
- md5 of both shipped files = `E0b/meshes/*` = the box `cand/` files.
- The kit check (`c0b_check.py`, re-run here on the shipped files) gives:

  | Mesh | Raw watertight | Budget | Eligible |
  |---|---|---|---|
  | pot | yes | 4096 faces / 2050 vertices | yes |
  | beige | yes | 4096 faces / 2043 vertices | yes |

## 4. Scorings [D]

`score_c0b.jsonl` holds 4 records with 4 distinct sha1[:16]: pot `5d883a54`, rack `84195053`, blue cup `92e758ad`, beige `7d1202e3`.
- Each says `scored once (mesh_metric.evaluate defaults)`.
- A repo-wide search for these sha1 values finds no other score record (the other hit is `box/check.jsonl`, which holds no score).
- The WIN thresholds in `score_c0b.py` equal `results/baseline_library.jsonl`: pot L 0.43712 / A 6.69; library_v3 beige cdo_eval 0.85625; library_v3x 0.72995.
- The verdicts follow: pot 0.3924 <= 0.41712, add_med 4.94 <= 8.69, 0 flips; beige 0.3007 <= 0.83625 and 0.2983 <= 0.70995, add_med 2.94 <= 8.965.
- No E0b mesh was scored.

## 5. AUC guard [D]

- **Runner and evaluator.** The diffs against C0's `run_auc_guard.sh` and `guard_eval.py` change only the mesh dirs, the output dir and the object list (beige twin 11 added). The thresholds are unchanged (-0.005 / -0.02 / +0.2 / +0.2 cm, EPS 1e-9).
- **Base runs.** The 15 base JSONs used are byte-identical to C0's committed `C0/auc/base/ep*.json`.
- **Mesh dirs.** Each `single/<o>` dir differs from `cdo_c0/base` (= library_v3 minus `wooden_spoon`) in exactly one file, the pick's sha256 as built. The joint dir `c0b` differs in the four picks.
- **Recomputed with `guard_re.py`.** The results equal `guard_result_c0b.json`:

  | Object | Mean dAUC | Min dAUC | dMPPE | dRPE | Result |
  |---|---|---|---|---|---|
  | pot | +0.0009 | -0.0107 | -0.025 | -0.027 | PASS |
  | rack | -0.1325 | -0.3043 | | | FAIL |
  | blue cup | -0.5462 | -0.6273 | | | FAIL |
  | beige | +0.0139 | | -0.214 | +0.018 | PASS |
  | joint (reported only) | -0.2159 | -0.9293 | | | |

- **Run files.** All 35 run JSONs in `results/auc/` are byte-identical to the scratch runs.

## 6. No alignment [M]

The sha256 chain matches at every step: builder output on the box -> repo `C0b/meshes` / `E0b/meshes` -> guard mesh dirs -> `library_e0b` / `library_e0bx`. Nothing transforms a mesh between the builder and the pack. The frame check against library_v3 (`frame_check_report.json`) is a report written after the picks were pushed. The E0b frame check is against the C0b public pick, not library_v3.

## 7. Old defaults byte-reproducible [M]

- **Lid and cup.** I re-ran the regression with HEAD code (the same blobs as `00e8584` and `c8f1c33`, clean tree) at nice 19:
  - `PRIM_T_LID=0.0025 prim_potlid.py lid ep2 --variant fit` is byte-identical to the committed `results/prim/meshes/white_pot_lid_ep2_fit_v2.glb`;
  - `lathe_obs.py obs/ep21_blue_cup.npz` (all defaults) is byte-identical to `C0/meshes/ep21_blue_cup_g1.glb`.
- **Pot.** My re-run of `prim_potlid.py pot obs_all/ep2_white_pot.npz --variant fit`, with the axis searched from scratch, is byte-identical to C0's candidate `SCR/prim/potlid/cand/white_pot_ep2_fit.glb` (md5 `ac6f4d96...`). Its axis cache is byte-identical to `SCR/prim/potlid/axis/ep2_white_pot.json`. The agent's 17:41 rebuild agrees.
- **Code version.** `prim_potlid.py` and `lathe_obs.py` have the same blobs at `ade3608` (18:00), `00e8584` and `c8f1c33`. The rack orig-vs-mod check is the agent's (not re-run here).

## 8. Findings

### Blocking
None.

### Non-blocking (corrections and disclosures)

- **N1. The marker detector carries an "informed" setting that C0b labels "generic".**
  - **What gmg says.** gmg PREREG A.6's origin column for "ball detector" reads "generic; seed count informed (changed once after a first run)". gmg SPEC §10 is more specific: "The seed count was raised from 5,000 to 15,000 after a first run by agents who knew the scan catalogue (about 7 mm, about 5 balls). So the detector is not independent of that knowledge (informed)."
  - **What the first run shows.** `SCR/gmg/design/obs-first/ball_probe_v1.log`: with 5,000 seeds the probe found 0 strong balls on ep41 pot and ep31 sweeper.
  - **What C0b says.** C0b REPLACEMENTS / PREREG 3.2 give the MK class the origin "generic: gmg PREREG A.6 ball detector and radius window" and do not mention this.
  - **How C0b's own classes would rate it.** At least U. It is arguably U-suspect: a value set after a result, by authors who had the scan numbers in context.
  - **Effect.** The seed count sets recall, so it shapes the 32 balls on the shipped E0b pot (and the 26 on the public pick, which carries the guard and the WIN). It does not set a radius: the balls are 10.4-12.48 mm, not 7 mm. The balls also lower fidelity (ep3: thick 3.275 / fit 3.319 vs nomk 3.377; public ep43: fit 3.407 vs nomk 3.634 [M]), so the setting also feeds the pick.
  - **Required.** Word pack 10 as "no scan-derived value; the gmg ball detector carries one setting gmg labels informed (seed count)". Do not write "no scan-derived or unknown constant".
  - **[H] (untested).** Seeds 5,000 vs 15,000 do not change the eval 3 pot's balls materially. Falsifying experiment: GT-free `detect_episode` on the eval 3 C0b points with seeds = 5,000, comparing the ball count and positions. It costs about 20 min on a box; it was not run.
  - **Note.** Swapping the shipped pot for `nomk` now would be a post-hoc change; that is the owner's call.
- **N2. The A.6b extent table is also "informed".** gmg A.6 says so ("part vocabulary and A.6b table informed"), and A.6b says the author had seen the program windows. Only the lid uses it, and the lid is not adopted. The E0b lid pick (info only, `a6b2`) inherits this.
- **N3. The single-scoring guard was split across two files.** `SCR/cdo_c0b/score.sh` ran two streams, writing `score_c0b.jsonl` (pot, rack) and `score_c0b.jsonl.b` (blue cup, beige), later merged. Each stream's "already scored" check saw only its own file, so a duplicate across streams would not have been refused. No duplicate happened: 4 meshes, 4 distinct sha1 [M].
- **N4. The E0b hand-off says the dry-run outputs "were deleted". They were not.** `SCR/e0b/dry` still holds 244 files, including eval 8 / 10 candidate meshes at stride 8 and a `selection.json`. DEVIATIONS_E0B says "discarded", meaning not used, which holds: packaging read only the box tree, and no rule changed after the dry run (the post-dry-run fixes are memory, path and KeyError fixes; X14 and X15 change no rule).
- **N5. Two C0b picks also feed a mocap-scored re-track test.** PUBOWN's ep11 beige (`5c39b656...`) and ep21 blue cup (`27957f76...`) are byte-identical to the C0b public beige and blue-cup picks. They go to a perception re-track test scored against mocap in another session. That would be a second ground-truth use of the C0b beige pick. It did not feed this adoption (decided 20:30). It must not be used to revise the C0b / E0b adoption without a new pre-registration.
- **N6. The E0b rack ran a different `prim_rack.py` from the one C0b validated.** E0b used blob `27e778e` (the C2/R options from `01c25d2`, defaults claimed byte-identical by C2), not `8387454`, which C0b regression-checked. The crash site `lip_tops` is unchanged by C2. The rack is not adopted, so this matters for provenance only.
- **N7. The beige WIN rule compares unlike quantities, as pre-registered.** It compares the pick's CD-O at one seed with library_v3's / v3x's mean `cdo_eval` (0.85625 / 0.72995), not with their values at the same seed (0.8705 / 0.7251). That is the T1 rule as written in PREREG 6. The margin is large (0.30 vs about 0.8), so the verdict does not depend on it.
- **N8. The cube-guard counts are confirmed** [M] from the guard JSONL: public 16 pass-A + 11 pass-B rebuilds (ep21 blue cup still over at 0.45 m); eval 8 + 3 (rack eval 28 and cup eval 20 still over). The 17:5x NOTES "17" is wrong, as already corrected.

### Confirmed
- PREREG pushed before every build and scoring.
- Picks and the ship rule reproduce from raw rows (C0b 4/4; E0b 5/5, frame thresholds included).
- One scoring per distinct mesh (4/4).
- Guard rule, base reuse and mesh dirs as C0's; numbers reproduce.
- No alignment anywhere.
- No S value in the shipped pot and beige.
- Old defaults rebuild C0's lid, cup and pot (with its axis file) byte-identically (re-run here).
- Shipped md5s, library diffs and kit budget re-checked.

**Not checked here:** ledger lines, box destruction, the rack orig-vs-mod regression, and the 1361 / 1530 pulled-file
sha256 lists (outside the integrity lens or already verified by the agents).
