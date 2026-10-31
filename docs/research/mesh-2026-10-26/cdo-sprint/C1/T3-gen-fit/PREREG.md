# C1 / T3 generate-then-fit: pre-registration

Written 2026-10-31 (UTC times in `NOTES.md`), before any scoring of this track. Up to the commit that adds this file,
nothing in T3 has read ground truth: no public scan, no mocap, no parquet pose, no `*_align.npz`. The only inputs were
the generative probe's placed meshes (our object frame), our observed points (`obs_all` npz from `scripts/obs_points.py`
on our own tracks), the kit roster and packer, and existing score records (`baseline_library.jsonl`, the probe's
`scores.jsonl`, `selection.json`) written before this sprint.

## 1. Hypothesis H-GF and falsifier
H-GF [H]: fitting a generated mesh to our observed points beats both the raw generated mesh and the library (as in
AGILE, MagicHOI, GenPC-type pipelines).
- **Falsified if** the fitted mesh is a CD-O-gate WIN (section 5) on fewer than 3 of the 10 objects, **or** its
  one-shot public CD-O is worse than the raw pick's [D] CD-O on a majority of the scored objects.
- Dev-object prediction (section 3): on the white pot the GT-free held-out residual says the chosen fit helps a little
  (held-out trimmed mean 2.14 -> 2.02 mm); the earlier, more flexible settings (v4) made it worse.

## 2. Inputs (fixed; GT-free)
For each of the 10 public objects: the probe's GT-free pick (`results/gen-probe/selection.json`, field `pick`), its
episode, the probe's own Sim(3)-placed file of that pick (the exact mesh the probe scored; sha256 matches
`results/gen-probe/SHA256SUMS`), and that episode's observed points. Resolver: `scripts/picks.py`.

| Object | Pick (model / episode / crop / seed) | Placed mesh sha256 (16) | Observed points | npz sha256 (16) | Raw pick [D] CD-O / add_med mm / flips |
|---|---|---|---|---|---|
| white_pot | sam3d ep41 k279 s7 | 24470905e07fa73a | `obs_all/ep41_white_pot.npz` | 1da1e1090c021375 | 0.3276 / 8.19 / 0 of 8 |
| white_pot_lid | hy21 ep2 k321 s7 | 4c80ef1b5e1026cd | `obs_all/ep2_white_pot_lid.npz` | d608aeb9e30357d3 | 0.3533 / 27.28 / 0 of 6 |
| blue_cup | pixal_mv ep22 s42 | d2de438532e29eb8 | `obs_all/ep22_blue_cup.npz` | ecaa870975295599 | 0.4068 / 6.58 / 0 of 7 |
| water_pitcher | sam3d ep22 k174 s42 | 9c0690fa2b2dd700 | `obs_all/ep22_water_pitcher.npz` | 6b1caf6af108abc1 | 0.7710 / 33.38 / 0 of 6 |
| wooden_piece_1 | triposg ep23 k27 s7 | f356f5943494eb11 | `obs_all/ep23_wooden_piece_1.npz` | 61e5177a52f907af | 0.3355 / 21.98 / 1 of 6 |
| wooden_piece_2 | sam3d ep23 k6 s42 | 19b710ff65792984 | `obs_all/ep23_wooden_piece_2.npz` | 635c938fd7996826 | 0.3211 / 84.96 / 6 of 6 |
| plastic_dish_rack | sam3d ep26 k144 s7 | 4b5f4518c22c2ac2 | `obs_all/ep26_plastic_dish_rack.npz` | f034938d93318e68 | 0.6041 / 21.07 / 0 of 7 |
| mini_sweeper | sam3d ep31 k270 s7 | e6697a6acdafa5b9 | `obs_all/ep31_mini_sweeper.npz` | 033dc4baea98cce0 | 0.4370 / 9.07 / 2 of 6 |
| mini_dust_pan | sam3d ep39 k297 s42 | 65f23d48c47a487a | `obs_all/ep39_mini_dust_pan.npz` | 160450183c46de9f | 0.2606 / 7.47 / 0 of 6 |
| beige_cup | sam3d ep11 k6 s42 | 4373364a569d17d1 | `obs_all/ep11_beige_cup.npz` | 7fd1dec0fa7402a2 | 0.5258 / 21.76 / 0 of 6 |

Paths are under the session scratchpad. The raw-pick numbers are the probe's existing one-shot records [D]
(`results/gen-probe/scores.jsonl`); they are not re-scored. Known input caveats (from earlier reports, not from new
scan reads): the ep23 board-2 track is the wrong board's (identity swap), the ep23 board-1 track covers ~16 % of the
board, the ep11 beige-cup track is wrong at frame 0, the hy21 lid was generated from a frame where the lid sits on the
pot. `obs_all` used library_v3 as ROI box and as the "others" mask (provenance caveat in `diag-2026-10-30`).

## 3. Method and frozen settings
`scripts/fit.py` (code at this commit), settings `cfg_frozen.json` (this folder). Steps:
1. **Sim(3) placement**: reused, not re-run: the probe's `gen/sim3_fit.py` output (multi-start trimmed Sim(3) ICP to
   our points), i.e. the placed file above.
2. **Non-rigid fit**: own implementation of optimal-step NICP (Amberg et al. 2007): per-vertex affine, stiffness
   alpha over mesh edges, Tikhonov eps to keep unobserved pieces in place. Data term in observed regions only: each
   observed point (2 mm voxel average, 80 % of 10-frame blocks; 20 % held out) pulls the nearest of its 32 nearest
   surface samples whose face faces the camera that saw the point (n . unit(cam - p) >= 0.2), within a 6 mm cap,
   best 80 % kept, pure point-to-plane (beta 0). Working mesh: the placed mesh decimated to 12 000 faces.
3. **Repair and pack**: trimesh weld / degenerate and duplicate faces / winding / small holes, then quadric decimation
   to a 4 000-face target (fast_simplification, the kit packer's simplifier; the small-hole filling after it can add
   a few faces, e.g. blue cup 4 002), then the kit's `budget_mesh(4096, 4096)` check: every mesh is <= 4 096 faces
   and vertices, so the packer does not simplify it again. pymeshlab hole closing is not available here (its meshing plugin needs libOpenGL), so meshes that are not
   watertight after the 12k decimation stay open; the kit never checks watertightness (C0 notes).

How the settings were chosen (GT-free, dev object = white_pot ep41, chosen because it has the most eval pairs of the
10 and is a SAM 3D pick like 7 of 10): five dev versions, diagnostics per alpha stage (train and held-out
observed->mesh residual, mesh->observed residual, free-space violation from the obs voxel grid, area and RMS-radius
change, face flips, self-intersections). Full log: `NOTES.md`, `dev_diag/`.
- v0: PCA normals of the observed points as the orientation test: normals too noisy (lambda0/sum median 0.22).
- v1: visibility test, vertex->point and point->surface (nearest only): pot shrank 2 % away from the observed band.
- v2: point->surface only, 8-NN: shrank more (the observed band lies behind the generated wall's front face, 8-NN
  never reached the camera-facing face).
- v3/v4: 32-64 NN, cap 10 mm, trim 0.9, beta 0.1, alpha 100 -> 3: train residual down, held-out residual up at
  every stage (2.14 -> 2.16 ... 2.29 mm) -> the pre-written rule picks "no fit".
- v5 (the one extra variant allowed by the rule written before it ran): cap 6 mm, trim 0.8, beta 0, alphas
  100/50/25. Stage choice by the rule written before v5 ran (argmin held-out tmean90 subject to flips <= 0.5 %,
  self-intersections <= input + 1 % of faces, |area change| <= 10 %, free-space violation <= input + 0.01; ties
  within 0.02 mm -> stiffer): held-out tmean90 input 2.14, alpha 100 2.02, alpha 50 2.05, alpha 25 2.09 mm; all constraints hold -> stage 0 (alpha 100).

Frozen: `cfg_frozen.json` = v5 settings with `alphas` = [100.0] (one stage, up to 5 iterations) (sha256 e380755a2e55abf2aae5898b535ca678c1f42d1387fdaf3e3a2beb8372ebf5a3).

## 4. Meshes to score (one scoring each, never re-scored)
Built by `bash scripts/run_fits.sh cfg_frozen.json <scratch>/cdo_c1/t3/build` (two streams of five objects). Every
fitted mesh, its sha256 and its GT-free diagnostics: `build_manifest.json`; scoring manifest `score_manifest.tsv`.

| Object | Fitted mesh (this folder) | sha256 | faces / watertight / bodies | GT-free [M]: held-out tmean90 mm in -> fit; train; free-space frac; area x; RMS-radius x; self-int faces in -> fit |
|---|---|---|---|---|
| white_pot | `meshes/white_pot_t3fit.glb` | `ff2c26624b24ffc8c0ee2813b52d171ead7f74f5f8414164253f726ce2236df1` | 4000 / True / 4 | 2.14 -> 2.02; 2.82 -> 2.50; 0.076 -> 0.072; 1.026; 1.0047; 12 -> 50 |
| white_pot_lid | `meshes/white_pot_lid_t3fit.glb` | `1e647af6a78c2e30cf26b939e859e8f6857700e59a671ec781d13d8f094ae6ec` | 4000 / False / 1 | 2.23 -> 2.31; 2.48 -> 2.58; 0.111 -> 0.103; 1.002; 1.0005; 16 -> 16 |
| blue_cup | `meshes/blue_cup_t3fit.glb` | `84a103978bb340b2ccdb702cd93848b5a393b4af7626473941a8d067b297759c` | 4002 / False / 1 | 2.44 -> 2.14; 2.42 -> 2.14; 0.057 -> 0.051; 1.031; 1.0113; 1026 -> 1026 |
| water_pitcher | `meshes/water_pitcher_t3fit.glb` | `6425bfa3a9f1f81bbac5e4d69e162dec3456446447f43886cc959245abc14c21` | 4000 / False / 7 | 2.97 -> 2.79; 3.44 -> 3.22; 0.136 -> 0.117; 1.004; 0.9997; 50 -> 47 |
| wooden_piece_1 | `meshes/wooden_piece_1_t3fit.glb` | `e1f55980b0929caffceb9ae739982a18c6b2992a2f741b627b83134d1539f8f0` | 4000 / False / 1 | 1.78 -> 1.75; 1.70 -> 1.45; 0.239 -> 0.212; 0.970; 0.9899; 131 -> 131 |
| wooden_piece_2 | `meshes/wooden_piece_2_t3fit.glb` | `4ce208a309c5ca2597c7a5216090d9abb8338a036835bad61b8dfa152d4c2075` | 4000 / True / 6 | 2.23 -> 2.10; 2.44 -> 2.30; 0.210 -> 0.159; 0.963; 0.9902; 73 -> 154 |
| plastic_dish_rack | `meshes/plastic_dish_rack_t3fit.glb` | `5c4e045d2dc3d6fb039a36568ef2d1d2c4fb17ef2d614adce1487ad6916e1778` | 4000 / False / 24 | 3.11 -> 2.79; 3.20 -> 2.88; 0.510 -> 0.449; 0.988; 1.0027; 12 -> 389 |
| mini_sweeper | `meshes/mini_sweeper_t3fit.glb` | `89cdc1b779fe193244a63c7aae21d6546fb82bb762f33d0204ceb991966d7848` | 3999 / False / 5 | 2.63 -> 2.47; 3.00 -> 2.84; 0.227 -> 0.166; 0.938; 0.9800; 100 -> 355 |
| mini_dust_pan | `meshes/mini_dust_pan_t3fit.glb` | `64a48c0ff0da33c4b4498a201b702ef9322c0ef2b285c55ff7ac3709826b3be1` | 3999 / False / 13 | 1.88 -> 1.70; 2.01 -> 1.80; 0.087 -> 0.086; 1.096; 1.0194; 49 -> 527 |
| beige_cup | `meshes/beige_cup_t3fit.glb` | `566d9cbda9714693b239ecb77d4d5fbad57116a14aad3f65aa10c2d77d314188` | 4000 / False / 4 | 1.65 -> 1.81; 1.90 -> 1.82; 0.080 -> 0.083; 1.013; 1.0048; 31 -> 137 |

The held-out residual got worse on the lid (2.23 -> 2.31) and the beige cup (1.65 -> 1.81) and better on the other 8. These GT-free changes are recorded now as predictions; they do not select or drop any mesh (all 10 are scored).

## 5. Scoring and the CD-O GATE
Command (one process, after this file is pushed):
`venv/bin/python -I scripts/score.py score_manifest.tsv <scratch>/cdo_c1/t3/scores.jsonl`, copied to
`scores.jsonl` here. `score.py` calls `scripts/mesh_metric.py evaluate()` (kit CD-O at the scorer's eval seeds, kit
registration ADD and symmetry-aware flips): default seeds for 7 objects; for `mini_sweeper`, `wooden_piece_1`,
`wooden_piece_2` the extra seeds are 1001..1030 and **all 30 are used** (`min_extra=30`; the CLI's `--seeds` would use
only max(2, 6 - n_eval) of them, which is why the wrapper exists). Total: 10 scorings.

CD-O GATE (per object; for the beige cup per eval pair): **WIN** iff
- one-shot public CD-O (`cdo_eval`) <= baseline - 0.02, baselines (packed mesh, `results/baseline_library.jsonl`):
  pot 0.4371, lid 0.4211, rack 0.5551, blue cup 0.5233, pitcher 0.8942, dust pan 0.3307, sweeper 0.3170, board 1
  0.2219, board 2 0.2158, beige cup 0.8562 (eval 10, library_v3) and 0.7299 (eval 8, library_v3x);
- AND `add_med` <= library add_med + 2.0 mm (pot 6.69, lid 8.13, rack 5.79, blue cup 10.14, pitcher 7.97, dust pan
  5.65, sweeper 5.245, board 1 2.49, board 2 3.315, beige 6.965 (v3) / 5.51 (v3x));
- AND flips: sweeper and boards <= 1 of the 30 extra seeds (and 0 on eval seeds); every other object 0 flips
  (mesh_metric's flip test is symmetry-aware for the kit-declared symmetric beige cup, blue cup and lid).

Also reported (not gates): the change vs the raw pick's [D] CD-O; for pot, lid, rack and blue cup whether the fitted
mesh beats C0's candidate by 0.02 (C0: 0.3417, 0.2199, 0.4560, 0.2906) — a WIN that does not beat C0 is not a
candidate over C0; the per-object GT-free held-out change next to the [D] CD-O change.
Verdicts: `python -I scripts/gates.py scores.jsonl gates.json` (rules above, nothing else).

## 6. AUC GUARD (only for WINs; same rule as C0)
Twins = the public episodes whose perception tracks contain the object: pot 0, 2, 26, 27, 41-45; lid 0, 2; blue cup
11, 12, 13, 21, 22; beige cup 11; pitcher 21, 22; rack 12, 13, 26, 27, 31; sweeper 18, 31; dust pan 18, 39, 40;
boards 23, 24. Runs: base (library_v3 for all 10 objects; byte-identical to C0's `cdo_c0/base`, so C0's base JSONs are
reused for the twins C0 ran) and single-swap (base + the fitted mesh, already in our object frame = library frame).
`bash scripts/run_auc.sh OBJ fit.glb` -> `pipeline/score_registered.py EP poses_world_vo.npz --meshes DIR`.
dAUC_e = AUC(single) - AUC(base) on the episode's `perception` entry. **PASS** iff mean dAUC >= -0.005 AND min dAUC
>= -0.02 AND mean dMPPE <= +0.2 cm AND mean dRPE <= +0.2 cm. A missing twin result fails the guard.

## 7. Labels and reporting
[D] public-scan diagnostics (CD-O, ADD, flips, AUC guard), [M] GT-free measurements, [E] estimates, [H] hypotheses.
Failures are reported. `RESULTS.md` will list every scoring, the gate and guard verdicts, the H-GF verdict and cost
(CPU only, $0).
