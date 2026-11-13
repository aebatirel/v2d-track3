# Gemini judge tests G-A and G-B: results (run 2026-11-12 23:21–23:38 UTC)

Both pre-registered tests are negative. **G-A (mesh selector): FAIL. G-B (track audit): FALSIFIED.**
Rules, texts, layout and inputs: `PREREG.md` (committed in ffc8a6e8 before the first scored call).
Labels: [M] measured, [D] diagnostic (never used for a verdict), [H] hypothesis, post hoc = looked at after the
verdict.

## Verdicts [M]

| test | statistic | value | bar | second criterion | verdict |
|---|---|---|---|---|---|
| G-A | ρ = Spearman(Gemini expected score, −CD-O), 104 meshes | **0.426** (object-bootstrap 95 % CI 0.16–0.65) | > 0.46 | top mesh = CD-O best on **1** of 10 objects (bar > 2) | **FAIL** |
| G-B | pooled AUROC of 1 − P(aligned) for ADD > 2 cm | **0.5245** (episode-bootstrap 95 % CI 0.43–0.63) | ≥ 0.75 informative, < 0.65 falsified | 16 episodes with positives (bar ≥ 8) | **FALSIFIED** |

- **G-A against the GT-free metric:** ρ 0.426 is below the metric's 0.4650 on the same 104 meshes, and Gemini's top
  pick is the CD-O best on 1 object (the dish rack) against the metric's 2.
- **G-B against the depth audit:** 0.5245 is below the falsified depth audit's 0.600 on the same rows (0.5992 on the
  7,808 answered rows). 98.6 % of the bootstrap draws fall below 0.65 and none reaches 0.75.
- **Missing answers:** G-A none. G-B 27 of 7,835 rows (0.34 %, under the 2 % limit): the API's input filter blocked them
  (`400 prohibited_content`) on the first pass and on all three allowed resumes. They are ordinary frames (sweeper,
  dust pan, one blue cup; `gb_scores.csv`, status `blocked`). One connection reset was retried successfully.
- Note 28 §5 said in advance: "If both fail, the product has no place in the pipeline and ideas 3–6 are dropped unless
  a new reason appears." Both failed. The owner decides.

## Cost actually spent [M]

| item | requests | input tokens | cost |
|---|---|---|---|
| format dry run (phase 1, synthetic images) | 1 | 2,855 | $0.0003 |
| G-A | 104 | 477,526 (428,076 image) | $0.0478 |
| G-B | 7,808 answered (+ 109 blocked or reset attempts) | 10,638,926 (8,440,448 image) | $1.0639 |
| **total** | | **11,119,307** | **$1.112** |

- Prices: $0.10 per 1M input tokens, no output charge; computed from the `usage` the API returned.
- Blocked requests returned no `usage`. If Google bills them, the upper bound is 108 × ≈ 1,370 tokens ≈ $0.015.
- Image tokens: 1,081 per image at `high`, as in the dry run. Estimate was ≈ $1.1; actual $1.11. Cap $5 not approached.
- No GPU. Machine: claude.ai cloud CPU VM (4 cores).

## Run record

- Code: commit ffc8a6e8 (this folder). Before the run, every sha256 in `PREREG.md` §8 matched (14 files), all 8,231
  pictures matched the sha256 pinned in the specs, and the working tree equalled the commit [M].
- Commands: exactly `PREREG.md` §7 (G-A run, G-A score, G-B run, three G-B resumes, G-B score).
- Times (UTC, 2026-11-12): G-A 23:21:39–23:21:58 (median latency 1.38 s); G-B 23:22:18–23:38:03, resumes until
  23:38:20 (median latency 0.92 s; token-rate limited at 800k/min).
- Caches (every request with images as path + sha256, every raw response), scratchpad
  `/tmp/claude-0/-home-user-v2d-track3/c39cfb04-cc2f-58cd-b84d-df803d82b152/scratchpad/gem/`:
  `ga/cache_GA.jsonl` (494 KB, sha256 7746efd9…), `gb/cache_GB.jsonl` (15.9 MB, sha256 1947feae…),
  `gb/run_GB.log`. Not uploaded to the HF store (this container's HF token is read-only).
- Deviations from `PREREG.md`: none in method. The scorers wrote to `results/`; their JSON files are renamed here as
  `results_GA.json` and `results_GB.json`, unchanged.

## G-A: mesh selector [M]

Per object (CD-O in cm, `rows.json` `cdo`; ρ within the object's meshes is a diagnostic):

| object | n | ρ Gemini | ρ GT-free | Gemini pick (expected score) | its CD-O | its CD-O rank | CD-O best | regret | GT-free pick (CD-O) |
|---|---|---|---|---|---|---|---|---|---|
| white_pot | 10 | 0.58 | 0.68 | sam3d k279 s7 (3.05) | 0.328 | 2 | trellis2 k279 s7 (0.318) | 0.010 | sam3d k279 s7 (0.328) |
| white_pot_lid | 10 | 0.58 | 0.52 | trellis2 k321 s42 (2.89) | 0.394 | 5 | pixal_mv s42 (0.253) | 0.140 | hy21 k321 s7 (0.353) |
| blue_cup | 10 | 0.36 | −0.21 | sam3d k156 s42 (3.12) | 0.299 | 3 | sam3d k156 s7 (0.268) | 0.031 | pixal_mv s42 (0.407) |
| water_pitcher | 10 | 0.07 | 0.67 | sam3d k174 s42 (3.19) | 0.771 | 6 | hy21 k174 s42 (0.378) | 0.393 | sam3d k174 s42 (0.771) |
| wooden_piece_1 | 10 | 0.76 | −0.15 | sam3d k27 s7 (3.07) | 0.204 | 3 | pixal_mv s42 (0.182) | 0.022 | triposg k27 s7 (0.336) |
| wooden_piece_2 | 12 | 0.02 | 0.21 | hy21 k6 s7 (2.98) | 0.438 | 11 | sam3d k6 s7 (0.202) | 0.237 | sam3d k6 s42 (0.321) |
| plastic_dish_rack | 10 | 0.82 | 0.65 | sam3d k144 s7 (2.98) | 0.604 | **1** | sam3d k144 s7 (0.604) | 0.000 | sam3d k144 s7 (0.604) |
| mini_sweeper | 10 | 0.55 | 0.22 | pixal_mv s42 (2.40) | 0.479 | 3 | sam3d k270 s7 (0.437) | 0.042 | sam3d k270 s7 (0.437) |
| mini_dust_pan | 12 | 0.26 | 0.71 | sam3d k297 s42 (3.20) | 0.261 | 4 | hy21 k297 s42 (0.231) | 0.029 | sam3d k297 s42 (0.261) |
| beige_cup | 10 | 0.27 | 0.72 | hy21 k6 s42 (2.97) | 0.461 | 3 | pixal_mv s42 (0.274) | 0.187 | sam3d k6 s42 (0.526) |

Per model (all its meshes):

| model | meshes | mean Gemini score | mean CD-O | Gemini picks |
|---|---|---|---|---|
| SAM 3D | 20 | 2.79 | 0.501 | 6 |
| Pixal3D view 0 only | 4 | 2.70 | 0.542 | 0 |
| TRELLIS.2 | 20 | 2.59 | 0.594 | 1 |
| Hunyuan3D-2.1 | 20 | 2.59 | 0.602 | 2 |
| Pixal3D-MV | 20 | 2.53 | 0.490 | 1 |
| TripoSG | 20 | 2.45 | 0.984 | 0 |

Diagnostics [D]:
- Mean within-object ρ 0.43 (GT-free metric: median 0.58). Spearman between Gemini and the GT-free metric 0.17: the two
  signals are nearly independent.
- Mean CD-O of Gemini's picks 0.424 (regret 0.109) against the GT-free picks' 0.434 (regret 0.120), library_v3 0.477,
  oracle 0.315. This difference is small and rests on 10 objects.
- Score spread: expected scores 0.62–3.20 (sd 0.46); the top level was 3 ("good match") for 66 of 104 meshes; mean
  answer confidence 0.39.
- Post hoc, not a test: averaging Gemini's and the GT-free metric's within-object ranks gives ρ 0.39 and 1 hit, so no
  gain from combining them.

Reading [H]:
- The judge ranks models roughly right at the extremes (TripoSG lowest, SAM 3D highest), but within an object it
  rarely finds the best seed or model. It favours SAM 3D's clean, smooth surfaces. Pixal3D-MV has the best mean CD-O
  but scores lowest but one, perhaps because its renders show holes and rough surfaces that CD-O barely penalises.
- On six objects the chosen frames lie within 0–14° of the views the generators saw (`PREREG.md` §9). The weakest
  objects are the pitcher (low coverage, ρ 0.07) and wooden piece 2 (up to 36° of new views, ρ 0.02), while the lid
  and the rack (low coverage) are among the best. Viewpoint coverage alone does not explain the failure.

## G-B: track audit [M]

Primary: AUROC 0.5245, 1,445 positives / 6,363 negatives on 7,808 answered rows, 16 episodes with positives,
95 % CI 0.43–0.63 (2,000 draws, seed 0; 98.6 % of draws < 0.65). Leave-one-episode-out 0.51–0.58.

Per episode (AUROC within the episode; depth audit's `behind` from its RESULTS.md, on all rows, for comparison):

| ep | rows answered | positives | Gemini AUROC | depth audit AUROC |
|---|---|---|---|---|
| 0 | 746 | 12 | 0.42 | 0.556 |
| 2 | 686 | 8 | 0.41 | 0.543 |
| 11 | 267 | 68 | 0.51 | 0.868 |
| 12 | 361 | 33 | 0.71 | 0.756 |
| 13 | 380 | 38 | 0.63 | 0.261 |
| 18 | 695 | 14 | 0.44 | 0.776 |
| 21 | 372 | 183 | 0.13 | 0.704 |
| 22 | 378 | 186 | 0.05 | 0.836 |
| 24 | 550 | 444 | 0.45 | 0.783 |
| 26 | 316 | 8 | 0.51 | 0.852 |
| 27 | 492 | 33 | 0.32 | 0.715 |
| 31 | 579 | 368 | 0.19 | 0.670 |
| 39 | 318 | 23 | 0.35 | 0.475 |
| 40 | 247 | 13 | 0.80 | 0.993 |
| 41 | 299 | 0 | – | – |
| 42 | 257 | 0 | – | – |
| 43 | 326 | 11 | 0.42 | 0.709 |
| 44 | 249 | 0 | – | – |
| 45 | 290 | 3 | 0.79 | 0.709 |

Per object class (pooled over its episodes; mean P(aligned) on negatives / positives):

| class | positives / negatives | Gemini AUROC | mean P(aligned) neg / pos | depth audit AUROC |
|---|---|---|---|---|
| plastic_dish_rack | 290 / 775 | 0.33 | 0.72 / 0.77 | 0.981 |
| wooden_piece_1 | 226 / 49 | 0.42 | 0.66 / 0.68 | 0.869 |
| wooden_piece_2 | 218 / 57 | 0.47 | 0.63 / 0.67 | 0.681 |
| water_pitcher | 369 / 6 | 0.53 | 0.66 / 0.65 | 0.603 |
| blue_cup | 134 / 741 | 0.34 | 0.49 / 0.57 | 0.592 |
| mini_sweeper | 79 / 552 | 0.62 | 0.66 / 0.58 | 0.455 |
| white_pot | 63 / 2,478 | 0.52 | 0.76 / 0.76 | 0.629 |
| mini_dust_pan | 49 / 869 | 0.49 | 0.73 / 0.69 | 0.634 |
| white_pot_lid | 12 / 704 | 0.22 | 0.42 / 0.63 | 0.683 |
| beige_cup | 5 / 132 | 0.45 | 0.51 / 0.55 | 0.876 |

Diagnostics [D]:
- Other thresholds: ADD > 1 cm 0.616, > 3 cm 0.497, > 5 cm 0.641 (21 positives in 4 episodes).
- Other label alignments (depth audit's verification): global SE(3) fit 0.587 (220 positives), frame-0 fit over all
  objects 0.660 (1,045 positives). Neither reaches 0.75.
- Mean within-track AUROC 0.48 (11 tracks with ≥ 10 positives and negatives). Spearman with the depth audit's
  `behind` −0.10.
- P(aligned): mean 0.67, median 0.72; 15.5 % of rows below 0.5 — 10.5 % of positives and 16.6 % of negatives, so
  Gemini flags good frames slightly more often than bad ones. Mean confidence 0.71.

Reading [H]:
- Gemini's answer varies more between objects than between good and bad frames (lid 0.42 and blue cup 0.49 against
  pot 0.76 on good frames). This is the same failure as the depth audit's: pooling ranks objects, not frames. On
  the episodes where the kit label is mostly an anchor offset (pitcher eps 21/22, rack ep31), Gemini calls the
  "bad" frames aligned and the other object's good frames less aligned, which drives those per-episode AUROCs to
  0.05–0.19.
- The depth audit's verification already showed that most kit-label positives are not visible camera-frame errors
  (median 2.86 cm; pitcher 98 % → 3 % bad under a global fit). A judge of the camera image cannot see them either.
  The global-fit label gives Gemini only 0.587, so it also misses most of what remains.
- The lumpy outlines of our library cups and lid may read as misalignment where the pose is right (lowest
  P(aligned) on good frames: lid, blue cup, beige cup).

## Files

| file | contents |
|---|---|
| `PREREG.md` | protocol, committed before the run (ffc8a6e8) |
| `README.md` | this file |
| `results_GA.json` | `score_GA.py` output: verdict, ρ, hits, bootstrap CI, per object, per mesh (score, level probabilities, confidence, CD-O, GT-free) |
| `results_GB.json` | `score_GB.py` output: verdict, AUROC, CI and bootstrap shares, `behind` check, thresholds, alignments, per episode, per class, leave-one-out, within-track, flag rates |
| `gb_scores.csv` | per G-B row: ep, obj, frame, P(aligned), confidence, status (`ok` or `blocked:prohibited_content`); Gemini's answers only, no label (304 KB) |
| scripts, `questions.json`, `frames_GA.json`, `sheet_*.png` | phase 1, unchanged since ffc8a6e8 |
