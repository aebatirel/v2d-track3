# D reset check: do the start nudges pop objects on tonight's D evals? (31 Oct 2026, CPU)

**Asked by** focused-pascal and keen-heisenberg, relaying the owner, ~21:15 UTC. Targeted D cells on evals 14, 16, 25, 30
and 33 start tonight. Before money is spent, check whether DR's start nudges (±1.5 mm, ±0.015 rad, fingers ±0.01 rad) make
objects that start nested or touching pop apart.

**Method** [M]. Diagnostic only; no ground truth was read, only our references.
- References: the packed references from focused-pascal's `docs/research/work/masses-eval-20261031/packed_refs.json`,
  pulled from the store. All md5s match the registry: 14 10d5f3ba, 16 f7e2ea92, 25 71ac95f3, 30 dd464c96, 33 2a7173ab.
- Assets:
  - grasp-lock evals use their packed assets (`refs/sf/ep<N>/assets`);
  - standard-learner evals use library_v3 built with `pipeline/make_assets.py` (as `hard_ab.sh`); library_v3 is
    unchanged for these objects since ee7ba8e;
  - eval 25 also uses `--pieces meshes/carve/ev25`, its packed carve; see the correction below.
  - The local copies have only `object_urdf_paths` remapped (`scripts/prep.py`).
- Run (`scripts/run_all.sh`): FlashCHORD at the evaluator pin with the box patch set (VOC fix + FDR + DR; scratchpad
  copy `rs/fc_box`), `FC_VOC_INERTIA=1 FC_FDR_OBJ=1 FC_FDR_TIPS=1`, 32 worlds,
  `tools/recipe_screen_tests/dr_patch_test.py`.
  - Each episode runs twice: without DR, and with `FC_DR_RESET=1.5,0.015,0.01 FC_DR_SEED=42`.
  - Same upstream reset frames and finger openings in both runs (checked), so the two runs differ only by the nudges.
  - Embodiment: sharpa_hands_mid for grasp lock, the default for the standard learner.
- Metric (`scripts/compare.py`): per world, the largest object-position difference (DR minus no DR) at three points:
  - right after the reset;
  - at the end of the 20-step VOC-1 settling hold (**the training-relevant number**);
  - 20 steps later, at VOC 0 in this env, which is harsher than training, where the curriculum assist is ≥ 0.25 most
    of the run.
- Calibration: the same check on the 4 public episodes where D was screened (physS1 references and assets as in the
  screen). Results are in `public_screen_episodes.json`.
- Not covered:
  - FC_IMMEDIATE_FIRST_FRAME starts (not drawn in this env); for 25/30, FC_DR_SKIP_IMMEDIATE leaves them untouched
    anyway;
  - pack-10 carve assets, which do not exist yet.

## Results [M]: DR minus no-DR object offset at the end of the hold

| episode | objects | median cm | p90 cm | max cm | worlds > 1 cm | no-DR motion in the hold, median cm |
|---|---|---|---|---|---|---|
| eval 14 | blue_cup, plastic_dish_rack | 0.63 | 1.57 | 3.15 | 31 % | 2.20 |
| eval 16 | plastic_dish_rack, wooden_spoon | 0.16 | 2.08 | 4.00 | 25 % | 0.49 |
| eval 25, **packed pieces** (`--pieces meshes/carve/ev25`) | wooden_piece_1, wooden_piece_2 | 0.46 | 1.73 | **5.79** (frame 156) | 25 % | 0.83 |
| eval 25, library_v3 without pieces (first run; NOT the packed assets) | wooden_piece_1, wooden_piece_2 | 0.60 | 2.12 | 6.70 (frame 170) | 34 % | 0.59 |
| eval 30 | mini_sweeper, plastic_dish_rack | 1.05 | 1.94 | 3.28 | 56 % | 1.28 |
| eval 33 | blue_cup, wooden_spoon | 0.57 | 1.51 | 2.60 | 28 % | 1.42 |
| public 2 (screen: D −0.11) | white_pot, white_pot_lid | 1.09 | 2.77 | 3.39 | 50 % | 2.11 |
| public 12 (screen: D +0.33) | blue_cup, plastic_dish_rack | 0.81 | 2.98 | 4.41 | 47 % | 1.94 |
| public 18 (screen: D −0.02) | mini_sweeper, mini_dust_pan | 0.00 | 0.00 | 1.32 | 3 % | 0.00 |
| public 24 (screen: D ≈ 0) | wooden_piece_1, wooden_piece_2 | 1.05 | 3.36 | 4.30 | 53 % | 1.67 |

- Every run is finite (no NaN).
- Right after the reset, every offset is ≤ 0.22 cm, as designed.
- Twenty steps after the hold at VOC 0, the divergence grows on every episode: median 1.5–2.5 cm; max 14–97 cm on the
  evals and 7–34 cm on the public episodes.

## Reading
- **No D eval episode is outside the range of the public episodes D was screened on.** Their medians (0.16–1.05 cm) and
  shares (25–56 %) sit inside the public range (0–1.09 cm, 3–53 %).
- **The largest single pop is eval 25: 5.8 cm** with the packed carve pieces (frame 156; 6.7 cm at frame 170 without
  them), about 1.3× the public maximum (4.4 cm). Its median is ordinary.
- **Correction, 21:56 UTC.** The first eval-25 run used library_v3 without the packed carve pieces. focused-pascal's
  packed_refs.json gives `pieces: meshes/carve/ev25` for eval 25 (none for 14/16/30/33). Re-run with
  `make_assets.py meshes/library_v3 OUT --pieces meshes/carve/ev25`, 42 collision entries per board URDF:
  `eval25_carved_pieces.json`.
- **This metric does not predict D's effect.** Public ep12 (D +0.33) and ep2 (D −0.11) look alike here. Read it as
  "no pathological start", not as a forecast.
- **The no-DR baseline already moves** 0.5–2.2 cm (median) during the hold on most episodes. The nudge adds a comparable
  amount; it does not create a new kind of start.
