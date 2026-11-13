# C1 / T3 generate-then-fit: results

CPU only, $0. Pre-registration: `PREREG.md` at commit 2d2a8ee (pushed before any scoring). Scan reads: 10
`mesh_metric.py` scorings (one per fitted mesh; 30 extra seeds for the sweeper and both boards), plus the AUC guard
on the 3 CD-O WINs (17 single-swap runs, 3 own base runs, 14 base runs reused from C0). Nothing was re-scored or tuned
on a score. Labels: [D] public-scan diagnostic, [M] GT-free measurement, [E] estimate, [H] hypothesis.

## Answer
- **Nothing from T3 is adopted.** Three fitted meshes pass the CD-O gate (white pot, blue cup, dust pan), and all three
  fail the AUC guard [D].
- **H-GF is not falsified by the pre-registered rule, but only just:** exactly 3 WINs (the threshold), and the fitted
  mesh is worse than the raw pick on 3 of 10 objects (lid, blue cup, beige cup). Against the raw pick the fit gains
  -0.018 cm CD-O on average (median -0.011; better on 7/10) [D].
- **The fit created no new WIN.** The raw picks of the same three objects already pass the same gate (pot 0.3276 /
  8.18 mm, blue cup 0.4068 / 6.58 mm, dust pan 0.2606 / 7.47 mm). The fit lowered their registration offset (add_med
  -1.9, -2.1, -0.7 mm) and CD-O changed by -0.016, +0.003, -0.006 cm. The six non-WINs fail on registration (add_med
  10-85 mm from the probe's biased Sim(3) placement, which a stiff fit does not undo), on board/sweeper flips, or on
  CD-O (boards, rack, sweeper).
- **GT-free signal that worked [M -> D]:** the sign of the held-out-frame residual change (computed before scoring,
  PREREG section 4) matched the sign of the [D] CD-O change on 9 of 10 objects (miss: blue cup).

## Per object [D] (fitted = one-shot score of `meshes/<obj>_t3fit.glb`; raw = the probe's existing record)
| Object | Raw pick [D] CD-O / add_med / flips | Fitted [D] CD-O / add_med / flips (extra) | d vs raw | Gate baseline(s) | CD-O ok | ADD ok | flips ok | WIN | vs C0 | GT-free held-out tmean90 mm in -> fit |
|---|---|---|---|---|---|---|---|---|---|---|
| white_pot | 0.3276 / 8.18 / 0 of 8 | 0.3112 / 6.28 / 0 of 8 | -0.0164 | pack 0.4371 / 6.69 | y | y | y | **WIN** | C0 0.3417: beats | 2.14 -> 2.02 |
| white_pot_lid | 0.3533 / 27.28 / 0 of 6 | 0.3598 / 39.65 / 0 of 6 | +0.0065 | pack 0.4211 / 8.13 | y | n | y | no | C0 0.2199: no | 2.23 -> 2.31 |
| blue_cup | 0.4068 / 6.58 / 0 of 7 | 0.4100 / 4.53 / 0 of 7 | +0.0031 | pack 0.5233 / 10.14 | y | y | y | **WIN** | C0 0.2906: no | 2.44 -> 2.14 |
| water_pitcher | 0.7710 / 33.38 / 0 of 6 | 0.7226 / 33.03 / 0 of 6 | -0.0484 | pack 0.8942 / 7.97 | y | n | y | no |  | 2.97 -> 2.79 |
| wooden_piece_1 | 0.3355 / 21.98 / 1 of 6 | 0.3322 / 20.92 / 7 of 31 (7/30 extra) | -0.0033 | pack 0.2219 / 2.49 | n | n | n | no |  | 1.78 -> 1.75 |
| wooden_piece_2 | 0.3211 / 84.96 / 6 of 6 | 0.2420 / 84.75 / 26 of 31 (25/30 extra) | -0.0791 | pack 0.2158 / 3.31 | n | n | n | no |  | 2.23 -> 2.10 |
| plastic_dish_rack | 0.6041 / 21.07 / 0 of 7 | 0.5724 / 21.60 / 0 of 7 | -0.0318 | pack 0.5551 / 5.79 | n | n | y | no | C0 0.4560: no | 3.11 -> 2.79 |
| mini_sweeper | 0.4370 / 9.07 / 2 of 6 | 0.4185 / 10.39 / 5 of 32 (5/30 extra) | -0.0184 | pack 0.3170 / 5.25 | n | n | n | no |  | 2.63 -> 2.47 |
| mini_dust_pan | 0.2606 / 7.46 / 0 of 6 | 0.2541 / 6.75 / 0 of 6 | -0.0064 | pack 0.3307 / 5.65 | y | y | y | **WIN** |  | 1.88 -> 1.70 |
| beige_cup | 0.5258 / 21.76 / 0 of 6 | 0.5424 / 21.73 / 0 of 6 | +0.0166 | eval10 library_v3 0.8562 / 6.96; eval8 library_v3x 0.7299 / 5.51 | y/y | n/n | y | no |  | 1.65 -> 1.81 |

Notes: "vs C0" = whether the fitted mesh beats C0's candidate CD-O by 0.02 (pot 0.3112 vs C0 0.3417: yes; but see the
guard). Beige cup is gated per eval pair (eval 10 library_v3, eval 8 library_v3x). Flips for the boards and sweeper
are over the 30 extra seeds 1001-1030 (plus eval seeds); other objects use the default seeds. Board 2's ep23 track is
the wrong board's (known), so 25/30 flips are expected; its CD-O nevertheless improves most (0.321 -> 0.242).

## AUC guard [D] (rule: mean dAUC >= -0.005, min dAUC >= -0.02, mean dMPPE <= +0.2 cm, mean dRPE <= +0.2 cm)
| Object | Twins | mean dAUC | min dAUC (episode) | mean dMPPE cm | mean dRPE cm | mean dMP_SR | Verdict |
|---|---|---|---|---|---|---|---|
| white_pot | 0, 2, 26, 27, 41-45 | -0.0099 | -0.0416 (ep45) | +0.148 | +0.088 | 0 | **FAIL** (mean and min) |
| blue_cup | 11, 12, 13, 21, 22 | +0.0217 | -0.0422 (ep13) | -0.228 | +0.009 | +0.2 | **FAIL** (min) |
| mini_dust_pan | 18, 39, 40 | -0.0056 | -0.0425 (ep18) | -0.031 | +0.106 | 0 | **FAIL** (mean and min) |

Per-twin values: `auc_<obj>.json`; raw run JSONs and log: `auc_runs/`. Base = library_v3 for all 10 objects; C0's
base dir is byte-identical to `meshes/library_v3` (sha256 checked file by file), so C0's base JSONs were reused for
the 14 twins C0 ran; ep18/39/40 base were run here (their public parquets were downloaded for scoring only).
The blue cup raises mean AUC (+0.022) but loses 0.042 on ep13; C0's blue-cup lathe (0.2906) is anyway far better on
CD-O than this fit (0.4100).

## How the fit was chosen (GT-free; full log `NOTES.md`, `dev_diag/`)
Dev object white_pot ep41 (most eval pairs of the 10; SAM 3D pick like 7 of 10). Own optimal-step NICP (Amberg 2007)
with a robust, visibility-tested, point-to-plane data term in observed regions only.
1. v0, PCA normals of the observed points: too noisy (lambda0/sum median 0.22) -> almost no change.
2. v1, camera-visibility test, vertex->point + point->surface: shrank the pot 2 % away from the observed band.
3. v2, point->surface only, 8 nearest samples: shrank more. Cause [M]: half of the near observed points lie behind the
   generated wall's front face (their camera-facing face is the far side of a 4 mm wall), library_v3 71 % vs SAM 42 %
   camera-facing; 8-NN never reached it. Synthetic sphere and thin-shell tests (`scripts/test_*.py`) behaved.
4. v3/v4, 32-64 NN: train residual down, held-out residual up at every alpha (2.14 -> 2.16 ... 2.29 mm): the rule
   written beforehand picks "no fit".
5. v5 (the one extra variant the rule allowed): cap 6 mm, trim 0.8, beta 0: held-out 2.14 -> 2.02 (alpha 100),
   2.05 (50), 2.09 (25) -> frozen `cfg_frozen.json` = one stage at alpha 100. The build reproduced dev v5 stage 0
   exactly.
The frozen fit is stiff: median vertex displacement 0.7-2.2 mm, RMS radius within 2 %.

## Failures and deviations
- **pymeshlab meshing plugins do not load** (no libOpenGL): no hole closing or self-intersection repair; trimesh
  repair only. **8 of 10 fitted meshes are not watertight** (pot and board 2 are); the 12k working decimation already
  opens the raw meshes. The kit never checks watertightness (C0 notes); [D] numbers are on these meshes.
- Blue cup has 4002 faces (hole filling after the 4000-face decimation); within the kit's 4096 budget, so the packer
  does not re-simplify.
- Self-intersections rise on several meshes (rack 12 -> 389, dust pan 49 -> 527, sweeper 100 -> 355) [M]; only the
  dev object was held to the self-intersection limit.
- Confound (pre-registered): raw was budgeted straight from 100-400k faces, fitted went 12k -> fit -> 4k; part of the
  small fitted-vs-raw differences may be the decimation path. No control scoring was spent.
- `mesh_metric.py run --seeds` uses only max(2, 6 - n_eval) of the given extra seeds; the 30-seed flip counts here
  come from `scripts/score.py` calling `evaluate(min_extra=30)`. (The gmg PREREG C.1 command as written would
  count 4-5 seeds, not 30.)
- Usage: dev runs v0-v3 were stopped early by me (own PIDs) when the diagnosis was clear; v3 was too slow (~1 h per
  object), hence the speed settings of v4/v5.

## What it means for the board [E]
No change: nothing passes both gates. Had the pot passed, swapping it alone would move the 36-pair CD-O by
6 x (0.4371 - 0.3112) / 36 = -0.021 cm vs library_v3, or -0.005 cm vs C0's pot [E].

## Next hypotheses [H] (with falsifiers)
- The pose loss comes from where the generated surface sits relative to our tracked frame, not from its shape: the
  probe's Sim(3) placement is biased (lid, pitcher, beige, rack, boards add_med 20-85 mm), and a stiff local fit only
  corrects 1-2 mm. Register to a compliant reference surface or use a visibility/free-space-aware placement before the
  fit. Falsified if the pot/blue-cup/dust-pan guards still fail with add_med <= the library's.
- The held-out-frame residual is a usable GT-free predictor of the CD-O direction (9/10 here). Falsified if on a new
  set of fits the sign agreement falls to <= 6/10.

## Files
`PREREG.md`, `NOTES.md`, `cfg_frozen.json`, `build_manifest.json`, `score_manifest.tsv`, `meshes/` (10 fitted
meshes), `scores.jsonl` + `score.log` (the 10 scorings), `gates.json`, `auc_*.json`, `auc_runs/`, `dev_diag/`,
`scripts/` (fit.py, run_fits.sh, manifest.py, score.py, gates.py, run_auc.sh, guard.py, results_table.py, picks.py,
dev analysis and synthetic tests). Bulk (working meshes, per-stage PLYs): scratchpad `cdo_c1/t3/`.
