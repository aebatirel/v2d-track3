# Depth audit, build and public calibration (30 Oct 2026): FALSIFIED by the pre-registered rule

Labels: [M] measured here, [C] read from code, [E] estimate, [H] hypothesis.

## Verdict
- **Primary result [M]:** pooled AUROC of `behind` for frames with registered ADD > 2 cm is **0.600**, 95 % episode-bootstrap CI 0.40–0.78. That covers 19 public episodes, 7,835 valid object-frames, 1,447 positives, and 16 episodes with positives.
- **Rule** (`PREREG.md`, written before any ground truth was read): informative iff ≥ 0.75; falsified iff < 0.65.
  **0.600 < 0.65, so the hypothesis "the depth audit tracks our pose error" is falsified.**
- **Consequences under the rule:**
  - no reference or spoon spend on the strength of this audit;
  - the eval audit and the spoon test (planned only if informative) were **not run**;
  - no eval depth was read in this stage.
- **What depth can see [M]:** only large errors, and only on some objects.
  - ADD > 3 cm: AUROC 0.754 (690 positives, 12 episodes).
  - ADD > 5 cm: 0.796, but only 21 positives in 4 episodes.
  - Dish rack: 0.98, driven by ep31's rack, which is wrong (ADD > 2 cm) on all 290 frames.
  - The common errors (median positive ADD 2.86 cm; 52 % between 2 and 3 cm) are invisible to it. Examples: in-plane slides of the boards, and the pitcher error.
- **Cost:** $0 (CPU cloud VM, 4 cores). Wall time: about 16 min of audits (2 passes) and 2 min 49 s of label scoring. No GPU, no Kaggle, no git operation.

## Integrity
- **Audit code is inference-only.** `pipeline/depth_audit.py` reads only our perception poses, our hands, our meshes and the stored stereo depth.
  - Its guard is `refine.assert_inference_input`. The one exception is a reference parquet under `refs/<variant>/` that has no `observation.*` column.
  - It never opened mocap, a dataset parquet, `refine/baseline/` or `refine/quarantine_gt/`.
- **Order of events [M]:**

| time (UTC) | event |
|---|---|
| 07:00–07:08 | audit v1 |
| 07:02 | `PREREG.md` written, during v1 |
| 07:10 | amendment 1 (exploratory rest metric only) |
| 07:08:40–07:16:24 | audit v2 |
| 07:16:40 | first ground-truth read (`score_registered.py`) |
| 07:20 | calibration |

- **v2 equals v1 exactly** on every primary array (`behind`, `front`, `valid`, `hidden`, `n_sel` …) on all 20 episodes [M]. The audit is therefore deterministic.
- **The ground-truth side is only** `pipeline/score_registered.py` (labels) and `calibrate.py` (join + AUROC).
- **Default scoring is unchanged.** The new `--per_frame` key leaves the default output untouched: the 20 registered AUCs equal the 29 Oct baseline to 0.0000 [M].

## What was built
**`pipeline/depth_audit.py`** (inference side). Thresholds are fixed in `PREREG.md`.
- **Inputs, per episode:**
  - `depths_fs0.5.npy`: FoundationStereo at half scale; full-resolution KR; metres; frame i = video frame i;
  - our `poses.npz`: `cam_T_<obj>`, `world_T_cam`;
  - `hands_refined.npz`: KR and MediaPipe joints;
  - `meshes/library_v3`.
  - Reference mode (`--ref --table`) maps a FlashCHORD reference back to the camera. It is implemented but **not run** (eval only, gated on an informative result).
- **Rendering and masks:**
  - Embree rays (embreex 4.4.0.post1 in `scratchpad/daudit/pylib`, passed with `--pylib`), one BVH per object in its body frame;
  - z-buffer and front-most object id;
  - hand mask: capsules of 1.2 cm along the 21-joint bones, palm filled, on `valid` frames only.
- **Per frame and object:**
  - `behind`: **primary**. Over front-most pixels eroded 4 px, with valid depth and outside the hand mask, the fraction with observed − rendered > 1.5 cm.
  - `front` and `med_r_cm`: exploratory.
  - `vis_frac`: the frame is hidden if < 0.20. The score is NaN when hidden or when fewer than 50 pixels are selected.
  - `behind_any` / `front_any`: without the hidden gate.
  - Rest height: lowest mesh vertex against a local RANSAC plane in a ring 8–40 px around the object.
    - Only on frames our own track labels as resting and where the object is not on or over another object (`refine.moving_labels`, `refine.support_relation`).
    - The plane is gated to ≤ 25° and ≤ 5 cm from the global table plane (amendment 1).
- **Outputs:** `audit.npz` holds per-(T,B) arrays. `audit.json` holds input sha256s, the commit, the parameters, a self-test and summaries.
- **Speed [M]:** 11.5–50 s per episode (608 s for all 20), about 0.05–0.15 s per frame. The depth download runs at about 80 MB/s.

**Self-test on frame 0 of every episode [M]** (in each `audit.json`):
- **Identity check:** feeding our own render as the observed depth gives `behind` = `front` = 0 for all 33 objects.
- **Planted 3 cm shift towards the camera:** `behind` = 0.71–1.00.
- **Planted 3 cm sideways shift:** behind + front = 0.00–0.97. The boards on ep23/24 give 0.00–0.13 and the lid 0.19: flat objects sliding along their own plane barely change depth.
- **Planted 3 cm shift away from the camera:** 23 of 33 objects turn *hidden*. The other 10 are caught only by `front` (0.54–0.80; `behind` ≤ 0.20). The audit has no handle on errors in that direction.

**Hand-mask check [M]:**
- `hand_mask_check_ep12.png` (frames 60 and 90, our silhouettes on depth): the masks sit on the hands.
- Forearms and hands MediaPipe missed are not masked. They only affect `front`.

**`pipeline/score_registered.py`:** under `--per_frame` only, a new key `<src>_adds_cm` gives the kit's symmetric ADD, the one the AUC uses (cup spin, lid 180°). Nothing else changed.

**`docs/research/work/depth-audit-20261030/calibrate.py`** (ground-truth side):
- Joins the audit with the labels by object name and frame.
- AUROC is Mann-Whitney with average ranks.
- 95 % CI from an episode-cluster bootstrap: 2000 draws, seed 0, percentile.
- Reports pooled, per-class, per-episode and mean within-episode AUROC, plus the score × label grid and the hidden accounting.

## Commands (machine: claude.ai cloud CPU VM; repo HEAD d41382e plus the uncommitted files listed below)
- **Code versions:**
  - The audits ran with `depth_audit.py` sha256 `e337ac7f…` (recorded in every `audit.json`).
  - Since then the only change is a one-word typo fix in the docstring, giving sha256 `f6147b99…`; no code changed.
```
S=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad; W=$S/daudit
REPO=/home/user/v2d-track3; D=$REPO/docs/research/work/depth-audit-20261030
# (1) audits, inference side (scripts/run_pub_ep.sh: own new download dir, python -I, delete the 0.9-2.4 GB cache after)
echo 0 2 11 12 13 18 21 22 23 24 26 27 31 39 40 41 42 43 44 45 | tr ' ' '\n' | xargs -P 2 -I{} bash $W/scripts/run_pub_ep.sh {}
#   per episode: python3 -I dl.py $W/dl_depth_pub_ep$e cache/depth/public/ep$e/depths_fs0.5.npy
#   OMP_NUM_THREADS=2 $S/map/scoring/venv/bin/python -I $REPO/pipeline/depth_audit.py --poses $S/refine/in/ep$e/poses.npz \
#     --depth .../depths_fs0.5.npy --hands $S/refine/in/ep$e/hands_refined.npz --meshes $REPO/meshes/library_v3 \
#     --out $D/audit/public/ep$e --pylib $W/pylib --selftest 0 --force
python3 -I $W/scripts/audit_summary.py $D/audit/public $D/audit_summary_public.csv
# (1b) S2-shifted tracks for the secondary label (inference side, no GT)
$S/map/scoring/venv/bin/python -I $REPO/pipeline/refine.py --in $S/refine/in/ep$e --out $W/work/s2/ep$e --steps S2
# (2) labels, GT side, after (1): 40 jobs, 4 parallel (scripts/gt_label_jobs.sh, list in scripts/gt_label_jobs.txt)
$S/map/scoring/venv/bin/python -I $REPO/pipeline/score_registered.py $e $S/refine/in/ep$e/poses_world_vo.npz \
  --t3 $S/map/scoring/t3 --kit $S/map/scoring/kit/v2d_submission_kit --meshes $REPO/meshes/library_v3 \
  --out $W/work/gt/lab/ep${e}_lib.json --per_frame $W/work/gt/lab/ep${e}_pf.npz      # and the same on $W/work/s2/ep$e
# (3) calibration
$S/map/scoring/venv/bin/python -I $D/calibrate.py --audit_root $D/audit/public --labels $W/work/gt/lab \
  --labels_s2 $W/work/gt/lab_s2 --out $D/calib
```
**Inputs:**
- Perception and hands: the 25-Oct current-recipe tracks in `refine/in/ep<N>` (store paths in `refine/README_inputs.md` §2), the same tracks the refine baseline scored.
- Depth: store `cache/depth/public/ep<N>/depths_fs0.5.npy`, 20 episodes, 5,246 frames, 33.6 GB, downloaded twice and deleted after each audit.
- The label `.npz` files hold mocap-derived errors. They stay in the scratchpad (`daudit/work/gt/`); their content is in `calib/per_frame.csv`.

## Results [M]
### Pooled, primary set (19 episodes; ep23 apart)

| score (valid object-frames) | label | AUROC | 95 % CI | n_pos / n_neg |
|---|---|---|---|---|
| **behind (primary)** | **symmetric ADD > 2 cm** | **0.600** | **0.40–0.78** | 1447 / 6388 |
| behind | S2-shifted symmetric ADD > 2 cm | 0.600 | – | 1319 / 6516 |
| behind | plain ADD > 2 cm | 0.588 | – | 1812 / 6023 |
| behind | symmetric ADD > 1 / 3 / 5 cm | 0.506 / 0.754 / 0.796 | – | 3984 / 690 / 21 pos |
| front | ADD > 2 | 0.449 | 0.28–0.62 | |
| behind + front | ADD > 2 | 0.533 | 0.34–0.72 | |
| \|median r\| | ADD > 2 | 0.605 | 0.49–0.73 | |
| behind_any (no hidden gate) | ADD > 2 | 0.600 | 0.40–0.78 | 1447 / 6395 |
| 1 − vis_frac | ADD > 2 | 0.565 | 0.44–0.67 | |
| \|rest height\| (rest frames only) | ADD > 2 | 0.593 | 0.51–0.96 | 487 / 2943, 5 episodes |

**Other summary numbers:**
- Mean within-episode AUROC: 0.700, over the 13 episodes with ≥ 10 positives and ≥ 10 negatives. Range 0.26 (ep13) to 0.99 (ep40).
- Episode-object level, mean `behind` vs share of frames with ADD > 2 cm: Spearman ρ = 0.24, p = 0.20, n = 31. So the audit cannot rank episodes by error either.
- Hidden or too small: 7 of 7,842 object-frames (all blue cup, ep11). They hold 0 % of the positives, so the hidden gate plays no role.

### Per class (pooled over the episodes containing it)

| class | AUROC | n_pos / n_neg | episodes | `behind` mean on negatives / positives |
|---|---|---|---|---|
| plastic_dish_rack | 0.981 | 290 / 775 | 12, 13, 26, 27, 31 | 0.010 / 0.121 (all positives are ep31) |
| wooden_piece_1 | 0.869 | 226 / 49 | 24 | 0.003 / 0.011 |
| beige_cup | 0.876 | 5 / 132 (< 30 pos) | 11 | 0.006 / 0.017 |
| wooden_piece_2 | 0.681 | 218 / 57 | 24 | 0.002 / 0.004 |
| white_pot_lid | 0.683 | 12 / 704 (< 30 pos) | 0, 2 | 0.003 / 0.004 |
| mini_dust_pan (thin) | 0.634 | 49 / 883 | 18, 39, 40 | 0.012 / 0.089 |
| white_pot | 0.629 | 63 / 2478 | 0, 2, 26, 27, 41–45 | 0.046 / 0.064 |
| water_pitcher | 0.603 | 369 / 6 | 21, 22 | 0.029 / 0.038 |
| blue_cup | 0.592 | 135 / 741 | 11, 12, 13, 21, 22 | 0.033 / 0.056 |
| mini_sweeper (thin) | 0.455 | 80 / 563 | 18, 31 | 0.058 / 0.055 |
| thin, pooled | 0.560 | 129 / 1446 | 18, 31, 39, 40 | |

Single-episode classes have a degenerate bootstrap CI.

### Per episode (symmetric ADD > 2 cm; reg. AUC = registered ADD-AUC of the same track, identical to the baseline)

| ep | objects | obj-frames | valid | pos | AUROC | behind mean | ADD med / p90 (cm) | reg. AUC | per-object AUROC (n_pos) |
|---|---|---|---|---|---|---|---|---|---|
| 0 | white_pot, white_pot_lid | 746 | 746 | 12 | 0.556 | 0.010 | 1.12 / 1.46 | 0.9641 | pot 0.651 (5); lid 0.680 (7) |
| 2 | white_pot, white_pot_lid | 686 | 686 | 8 | 0.543 | 0.014 | 0.84 / 1.14 | 0.9823 | pot 0.537 (3); lid 0.773 (5) |
| 11 | blue_cup, beige_cup | 274 | 267 | 68 | 0.868 | 0.042 | 1.54 / 3.45 | 0.8978 | blue 0.693 (63); beige 0.876 (5) |
| 12 | blue_cup, plastic_dish_rack | 362 | 362 | 34 | 0.756 | 0.023 | 0.64 / 1.99 | 0.9662 | blue 0.603 (34); rack – (0) |
| 13 | blue_cup, plastic_dish_rack | 380 | 380 | 38 | 0.261 | 0.019 | 0.94 / 2.00 | 0.9605 | blue 0.162 (38); rack – (0) |
| 18 | mini_sweeper, mini_dust_pan | 706 | 706 | 14 | 0.776 | 0.029 | 1.10 / 1.71 | 0.9642 | sweeper 0.648 (1); dust pan 0.848 (13) |
| 21 | blue_cup, water_pitcher | 372 | 372 | 183 | 0.704 | 0.035 | 1.54 / 4.38 | 0.8325 | blue – (0); pitcher 0.470 (183) |
| 22 | blue_cup, water_pitcher | 378 | 378 | 186 | 0.836 | 0.029 | 1.63 / 3.96 | 0.8710 | blue – (0); pitcher 0.776 (186) |
| 24 | wooden_piece_1, wooden_piece_2 | 550 | 550 | 444 | 0.783 | 0.007 | 2.47 / 3.27 | 0.8117 | wp1 0.869 (226); wp2 0.681 (218) |
| 26 | plastic_dish_rack, white_pot | 316 | 316 | 8 | 0.852 | 0.044 | 1.01 / 1.49 | 0.9652 | rack – (0); pot 0.734 (8) |
| 27 | plastic_dish_rack, white_pot | 492 | 492 | 33 | 0.715 | 0.034 | 0.69 / 1.89 | 0.9611 | rack – (0); pot 0.446 (33) |
| 31 | mini_sweeper, plastic_dish_rack | 580 | 580 | 369 | 0.670 | 0.098 | 3.04 / 3.25 | 0.7999 | sweeper 0.424 (79); rack – (290 of 290) |
| 39 | mini_dust_pan | 319 | 319 | 23 | 0.475 | 0.008 | 1.00 / 1.88 | 0.9602 | 0.475 (23) |
| 40 | mini_dust_pan | 260 | 260 | 13 | 0.993 | 0.027 | 0.84 / 1.60 | 0.9570 | 0.993 (13) |
| 41 | white_pot | 299 | 299 | 0 | – | 0.040 | 0.60 / 1.12 | 0.9910 | – |
| 42 | white_pot | 257 | 257 | 0 | – | 0.064 | 0.56 / 1.11 | 0.9915 | – |
| 43 | white_pot | 326 | 326 | 11 | 0.709 | 0.052 | 1.23 / 1.75 | 0.9482 | 0.709 (11) |
| 44 | white_pot | 249 | 249 | 0 | – | 0.031 | 0.48 / 0.90 | 0.9967 | – |
| 45 | white_pot | 290 | 290 | 3 | 0.709 | 0.079 | 0.67 / 1.54 | 0.9795 | 0.709 (3) |
| 23 (apart) | wooden_piece_1, wooden_piece_2 | 650 | 614 | 593 | 0.890 (21 neg) | 0.093 | 18.4 / 27.1 | 0.0414 | wp1 0.800 (268); wp2 – (325 of 325) |

## Why it fails (measured, then hypotheses)
1. **Baseline level differs between objects more than the error signal [M].**
   - On *correct* frames, `behind` averages 0.046 on the white pot, 0.058 on the sweeper and 0.033 on the blue cup, but 0.002–0.010 on the boards, lid and rack.
   - The objects with the most positives (boards in ep24, pitcher in 21/22) have the lowest `behind`.
   - Pooling therefore ranks objects rather than frames. Within single tracks it does no better: centring `behind` on each track's median gives pooled AUROC 0.517 (post hoc, not for the verdict).
   - The 0.70 within-episode mean comes mostly from differences *between* the two objects of an episode.
2. **Most positives are small and of a kind depth cannot see [M, H].**
   - The median positive ADD is 2.86 cm. Half-resolution stereo resolves about 1.1 cm at 0.5 m (map §1).
   - Board slides along the table plane change almost no depth: the planted sideways shift gives behind + front of 0.00–0.13 on the boards.
   - The pitcher error (reg. AUC 0.68 / 0.75) is not visible as free space: pitcher AUROC 0.47 / 0.78.
   - [H] Much of the pitcher and board label is registration or anchor offset, or in-plane drift, which agrees with depth.
   - Falsifier: an audit on the scan meshes (`--meshes` = public scans), compared with the same label.
3. **Not independent of the tracker [C].** FoundationPose fitted these same depth frames (`perc2.py:461, 473`), so what remains is what the tracker's own fit could not resolve.
4. **What depth does catch [M]:**
   - large offsets: ADD > 3 cm gives AUROC 0.75, ep31 rack 0.98 (the rack's mean `behind` 0.121 against ≤ 0.014 on eps 12, 13, 26 and 27);
   - dust-pan errors on ep40 (0.99).
   - That is useful as a per-object anomaly flag for gross failures. It is not a per-frame error estimate.
5. **The ep23 hypothesis is wrong as stated [M].** The map expected the board identity swap to be invisible. In fact ep23 has the second-highest mean `behind` (0.093) and wooden_piece_1 is hidden on 36 frames. The track also has depth-visible errors besides the swap.

## Side findings (exploratory; not used for any decision)
- **Rest label bug [M].** The rest label comes from our own track only, so an object held still in the hand counts as resting. That gives maximum |rest height| of 13–23 cm (ep39 13.1, ep24 14.7, ep44 21.1, ep45 22.5). Before reuse, a rest frame needs hand_frac = 0, or a support test against the plane.
- **Rest height medians [M]:**
  - our dish rack sits 1.0–1.3 cm *below* the local table plane (eps 12, 13, 27);
  - the pot lid on eps 0/2 sits 1.3–1.4 cm below it (about 165 frames each).
  - [H] This is mesh foot or rim geometry against blurred depth, or a real 1 cm sink. The audit cannot tell which.
- **v1 rest planes [M].** With no offset gate, the v1 ring planes latched onto the floor 60 cm down on eps 21, 22, 26 and 27. This was fixed in v2 before the ground truth was read (amendment 1).

## Not done (by the rule)
- Eval perception- and reference-mode audits, per-episode predicted reference loss, and the spoon test.
- The side question from the map (which of the two eval tracks for 8, 14, 30, 32 and 33 agrees with depth) needs only `behind` at the gross level that works (a 25–45 cm disagreement), so it remains possible as a GT-free sanity check. It was **not** run here.

## Files
**Repository (uncommitted; the orchestrator commits):**
- `pipeline/depth_audit.py`: new; inference side.
- `pipeline/score_registered.py`: `--per_frame` adds `<src>_adds_cm`; default outputs unchanged.
- In `docs/research/work/depth-audit-20261030/`:
  - `PREREG.md`: the rule and amendment 1, written before the ground truth was read.
  - `RESULTS.md`: this file.
  - `calibrate.py`: ground-truth side.
  - `audit/public/ep<N>/audit.{npz,json}`: 20 episodes, 844 KB in total.
  - `audit_summary_public.csv`: per object; written before the ground truth was read.
  - `calib/calib.json`: all AUROCs, the grid, per class, per episode, the accounting.
  - `calib/per_episode.csv`.
  - `calib/per_frame.csv`: the joined audit and label table, 0.9 MB. It contains mocap-derived errors and is diagnostics only.
  - `hand_mask_check_ep12.png`.
  - `scripts/`: `run_pub_ep.sh`, `gt_label_jobs.sh`, `gt_label_jobs.txt`, `audit_summary.py`, `viz_hand.py`, `dl.py`.

**Scratchpad only:**
- `daudit/work/v1/`: the v1 audits, kept.
- `daudit/work/gt/`: the label files, ground truth.
- `daudit/work/s2/`: the S2 tracks.
