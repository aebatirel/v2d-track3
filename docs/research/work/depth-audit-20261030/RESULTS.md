# Depth audit, build and public calibration (30 Oct 2026): FALSIFIED by the pre-registered rule (verified, fragile)

Labels: [M] measured here, [C] read from code, [E] estimate, [H] hypothesis. Two verifiers reviewed the build. Their
defects are fixed and re-run in "Verification and fixes" below. The verdict and the decision are unchanged.

## Verdict
- **Primary result [M]:** pooled AUROC of `behind` for frames with registered ADD > 2 cm is **0.600**, 95 % episode-bootstrap CI 0.40–0.78. That covers 19 public episodes, 7,835 valid object-frames, 1,447 positives, and 16 episodes with positives.
- **Rule** (`PREREG.md`, written before any ground truth was read):
  - informative iff AUROC ≥ 0.75 **and** at least 8 primary episodes contribute a valid positive;
  - falsified iff AUROC < 0.65;
  - inconclusive otherwise.
  **0.600 < 0.65, so the hypothesis "the depth audit tracks our pose error" is falsified.**
- **The verdict follows the pre-registered point-estimate rule, but it is fragile [M]:**
  - The CI (0.40–0.78) reaches the informative region. 64 % of bootstrap draws fall below 0.65 and 12 % reach 0.75 or more.
  - Leaving one episode out gives 0.53–0.74. Without ep24 it is 0.740, which would be inconclusive. Without ep31 it is 0.533.
  - Four episodes (24, 31, 22, 21) hold 82 % of the positives, so only about 5.1 episodes effectively carry positives.
  - With each episode weighted equally, AUROC is 0.645. At a violation margin τ = 2.0 cm it is 0.672, which is inconclusive.
  - The verdict also holds under two other label alignments (0.416 and 0.405).
  - Every alternative above still leads to the same decision: no eval audit and no spend.
- **Consequences under the rule:**
  - no reference or spoon spend on the strength of this audit;
  - the eval audit and the spoon test (planned only if informative) were **not run**;
  - no eval depth was read *in this stage*.
  - The map stage, before `PREREG.md` was written, did read eval-3 depth (4 frames; see Integrity). Eval 3 is therefore excluded from any future spoon test (`PREREG.md`, note 2).
- **What depth can see.** This depends on how the label is aligned. The figures below use the kit's frame-0 alignment; see "Label alignment" under Verification.
  - [M] ADD > 3 cm: 0.754 (CI 0.53–0.88), but 0.653 without ep31, whose rack holds 289 of the 690 positives.
    - This is one track-level offset, not sensitivity to large errors frame by frame.
    - It is a secondary label; picking 3 cm after the fact would be a forking path.
    - Under the other two alignments, ADD > 3 cm gives 0.496 and 0.499.
  - [M] ADD > 5 cm: 0.796, from only 21 positives in 4 episodes (kit alignment).
  - [M, alignment-dependent] Dish rack: 0.98. This compares ep31's rack against the racks of eps 12, 13, 26 and 27; it is not a per-frame result.
    - ep31's rack counts as wrong on all 290 frames under the kit alignment, but on 0 frames under either other alignment.
    - Depth does see that rack sitting a median 0.77 cm proud of the observed surface (`behind` 0.121).
  - [H] Most of the common kit-label errors (median positive ADD 2.86 cm; 52 % between 2 and 3 cm) are invisible to the audit. Examples are the pitcher and the board errors.
    - Many of them may not be camera-frame errors at all: under a global alignment the pitcher drops from 98 % to 3 % bad frames, and ep24's boards from about 80 % to 13 %.
- **Cost:** $0 (CPU cloud VM, 4 cores).
  - Build: about 16 min of audits (2 passes) and 2 min 49 s of label scoring.
  - Fixes: about 4 min of CPU, plus one 0.88 GB public depth download.
  - No GPU, no Kaggle call, no git operation by this step.

## Integrity
- **Audit code is inference-only.** `pipeline/depth_audit.py` reads only our perception poses, our hands, our meshes and the stored stereo depth.
  - Its guard is `refine.assert_inference_input`. The one exception is a reference parquet under `refs/<variant>/` that has no `observation.*` column.
  - It never opened mocap, a dataset parquet, `refine/baseline/` or `refine/quarantine_gt/`.
- **Guard tightened after verification [M].** Before the fix, the guard accepted this study's own label files (`work/gt/lab*/ep*_pf.npz`, `ep*_lib.json`) and `calib/calib.json` and `calib/per_episode.csv`. It refused only `calib/per_frame.csv`.
  - It now also refuses `_pf.npz`, `/gt/`, `calib_gt`, and any directory named `gt` or `*_gt` (shared by `refine.py` and `depth_audit.py`).
  - The calibration outputs moved from `calib/` to `calib_gt/`. The verifiers' ground-truth outputs moved under `daudit/work/gt/verify_r{1,2}/`, with symlinks left at their old paths.
  - The audit never read any of these. The fix keeps a future eval step from reading them.
- **Order of events [M]:**

| time (UTC) | event |
|---|---|
| 06:38–06:40 | **map stage: eval-3 depth read** (frames 0/100/200/312), our eval-3 perception and reference (pot, spoon) rendered against it (`MAP.md` §5) |
| 06:50 | `MAP.md` written (scratchpad; now copied unchanged into this folder) |
| 07:00–07:08 | audit v1 |
| 07:02 | `PREREG.md` written, during v1 |
| 07:10 | amendment 1 (exploratory rest metric only) |
| 07:08:40–07:16:24 | audit v2 |
| 07:16:40 | first ground-truth read (`score_registered.py`) |
| 07:20 | calibration (`calib_gt/v1_build/`) |
| 07:26–07:43 | verifiers' checks (verifier 2's calibration re-run and τ re-audits; verifier 1's geometry checks and alignment labels) |
| 07:45–07:58 | fixes and re-runs (guard, ep11 re-audit, alignment labels 07:49:00–07:50:26, calibration v2) |

- **Eval-3 disclosure.** The build's first draft of this report did not mention the map-stage read.
  - It touched public calibration in no way. But the spoon `behind` fractions on those 4 frames (0.008–0.056) were seen before the spoon-test range was fixed.
  - So if the spoon test ever runs, eval 3 is reported apart and not counted (`PREREG.md` note 2).
  - No other eval depth was read by this study [M: the `daudit/dl_*` folders and logs].
- **v2 equals v1 exactly** on every primary array (`behind`, `front`, `valid`, `hidden`, `n_sel` …) on all 20 episodes [M]. The audit is therefore deterministic.
  - Re-auditing ep11 with the tightened guard code gives all 18 arrays bit-identical [M].
- **The ground-truth side is only:**
  - `pipeline/score_registered.py` (labels);
  - `scripts/gt_align_labels.py` (alternative alignments, added in verification);
  - `calibrate.py` (join and AUROC).
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
  - Since verification, the CI is withheld when fewer than 95 % of draws hold both classes, or when one episode holds all the positives.
- Reports:
  - pooled, per-class, per-episode and mean within-episode AUROC;
  - the score × label grid and the hidden accounting;
  - since verification: leave-one-out, balanced AUROCs, positive concentration, within-track figures, the 3 cm label with and without ep31, the Spearman CI and the alternative alignments.

## Commands (machine: claude.ai cloud CPU VM)
- **Code versions:**
  - Build: repo HEAD d41382e plus the then-uncommitted files. The audits ran with `depth_audit.py` sha256 `e337ac7f…` (recorded in every `audit.json`). A one-word docstring fix gave `f6147b99…`, the version the verifier's τ audits used.
  - Fixes: committed as WIP by the orchestrator in 8c51b23 and e23faa5 (the build itself in d7d4e01).
    - The guard change gives `depth_audit.py` `53fc8abf…` and `refine.py` `1f6a2adf…`; it changes no computation.
    - `calibrate.py` is now `be3ac019…` and `scripts/gt_align_labels.py` `f6d73d8c…`.
```
S=/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad; W=$S/daudit
REPO=/home/user/v2d-track3; D=$REPO/docs/research/work/depth-audit-20261030; PY=$S/map/scoring/venv/bin/python
# (1) audits, inference side (scripts/run_pub_ep.sh: own new download dir, python -I, delete the 0.9-2.4 GB cache after)
echo 0 2 11 12 13 18 21 22 23 24 26 27 31 39 40 41 42 43 44 45 | tr ' ' '\n' | xargs -P 2 -I{} bash $W/scripts/run_pub_ep.sh {}
#   per episode: python3 -I dl.py $W/dl_depth_pub_ep$e cache/depth/public/ep$e/depths_fs0.5.npy
#   OMP_NUM_THREADS=2 $PY -I $REPO/pipeline/depth_audit.py --poses $S/refine/in/ep$e/poses.npz \
#     --depth .../depths_fs0.5.npy --hands $S/refine/in/ep$e/hands_refined.npz --meshes $REPO/meshes/library_v3 \
#     --out $D/audit/public/ep$e --pylib $W/pylib --selftest 0 --force
python3 -I $W/scripts/audit_summary.py $D/audit/public $D/audit_summary_public.csv
# (1b) S2-shifted tracks for the secondary label (inference side, no GT)
$PY -I $REPO/pipeline/refine.py --in $S/refine/in/ep$e --out $W/work/s2/ep$e --steps S2
# (1c) verifier 2: tau 1.0 / 2.0 cm re-audits, no rest metric (vstat/scripts/run_tau.sh; copied to audit/public_tau0{10,20})
$PY -I $REPO/pipeline/depth_audit.py ... --out $W/vstat/tau/t$t/ep$e --no_rest --tau $t --force
# (2) labels, GT side, after (1): 40 jobs, 4 parallel (scripts/gt_label_jobs.sh, list in scripts/gt_label_jobs.txt)
$PY -I $REPO/pipeline/score_registered.py $e $S/refine/in/ep$e/poses_world_vo.npz \
  --t3 $S/map/scoring/t3 --kit $S/map/scoring/kit/v2d_submission_kit --meshes $REPO/meshes/library_v3 \
  --out $W/work/gt/lab/ep${e}_lib.json --per_frame $W/work/gt/lab/ep${e}_pf.npz      # and the same on $W/work/s2/ep$e
# (2b) verification, GT side: alternative scene alignments, 20 jobs, 4 parallel, 07:49:00-07:50:26 (list in work/gt/lab_align/jobs.txt)
$PY -I $D/scripts/gt_align_labels.py $e $S/refine/in/ep$e/poses_world_vo.npz $S/map/scoring/t3 \
  $S/map/scoring/kit/v2d_submission_kit $REPO/meshes/library_v3 $W/work/gt/lab_align/ep$e.npz
# (3) calibration: build (v1, now calib_gt/v1_build) and after the fixes (v2, 40 s), plus the tau audits
$PY -I $D/calibrate.py --audit_root $D/audit/public --labels $W/work/gt/lab --labels_s2 $W/work/gt/lab_s2 \
  --labels_align $W/work/gt/lab_align --out $D/calib_gt/v2
$PY -I $D/calibrate.py --audit_root $D/audit/public_tau0{10,20} --labels $W/work/gt/lab --labels_align $W/work/gt/lab_align \
  --out $D/calib_gt/v2_tau0{10,20}            # one run each; per_frame.csv deleted (regenerable)
# (4) fix checks (no GT)
python3 -I $D/scripts/guard_test.py $REPO $S $D                                   # 448 accepted, 349 GT paths refused
$PY -I $REPO/docs/research/work/refine/check_refine.py $S/refine/in/ep11 $W/fixchk/check_refine   # ALL OK, 21 s
# ep11 re-audit with the new guard code -> $W/fixchk/audit_ep11 (07:48:09-07:48:31, 0.88 GB download deleted)
```
**Inputs:**
- Perception and hands: the 25-Oct current-recipe tracks in `refine/in/ep<N>` (store paths in `refine/README_inputs.md` §2), the same tracks the refine baseline scored.
- Depth: store `cache/depth/public/ep<N>/depths_fs0.5.npy`, 20 episodes, 5,246 frames, 33.6 GB. It was downloaded twice in the build and twice more by verifier 1 (eps 13, 21) and verifier 2 (all 20). The fixes downloaded ep11 once. Every copy was deleted after use.
- The label `.npz` files hold mocap-derived errors. They stay in the scratchpad under `daudit/work/gt/`, and the guard refuses that path. Their content is in `calib_gt/*/per_frame.csv`.

## Results [M]
### Pooled, primary set (19 episodes; ep23 apart)

| score (valid object-frames) | label | AUROC | 95 % CI | n_pos / n_neg |
|---|---|---|---|---|
| **behind (primary)** | **symmetric ADD > 2 cm** | **0.600** | **0.40–0.78** | 1447 / 6388 |
| behind | S2-shifted symmetric ADD > 2 cm | 0.600 | – | 1319 / 6516 |
| behind | plain ADD > 2 cm | 0.588 | – | 1812 / 6023 |
| behind | symmetric ADD > 1 / 3 / 5 cm | 0.506 / 0.754 / 0.796 | – / 0.53–0.88 / – | 3984 / 690 / 21 pos |
| behind | ADD > 3 cm without ep31 | 0.653 | 0.48–0.86 | 395 pos |
| front | ADD > 2 | 0.449 | 0.28–0.62 | |
| behind + front | ADD > 2 | 0.533 | 0.34–0.72 | |
| \|median r\| | ADD > 2 | 0.605 | 0.49–0.73 | |
| behind_any (no hidden gate) | ADD > 2 | 0.600 | 0.40–0.78 | 1447 / 6395 |
| 1 − vis_frac | ADD > 2 | 0.565 | 0.44–0.67 | |
| \|rest height\| (rest frames only) | ADD > 2 | 0.593 | 0.51–0.96 | 487 / 2943, 5 episodes |

**Other summary numbers:**
- **Within episodes:** mean AUROC 0.700 over the 13 episodes with ≥ 10 positives and ≥ 10 negatives (range 0.26 for ep13 to 0.99 for ep40). Pooling the pairs within episodes gives 0.708.
- **Within tracks** (one object in one episode): mean 0.628 over the 11 tracks with ≥ 10 positives and ≥ 10 negatives. Pooling the pairs within tracks gives 0.608.
  - So most of the 0.70 within episodes comes from differences *between* the two objects of an episode.
- **Balanced weights:** each episode's positives and negatives weighted to 1 gives 0.645; the same per track gives 0.609.
- **Ranking across episodes:** at the episode-object level, mean `behind` against the share of frames with ADD > 2 cm gives Spearman ρ = 0.24 (95 % CI −0.13 to 0.55, Fisher z; p = 0.20; n = 31 episode-objects). That is no evidence that the audit ranks episode-objects by error.
- **Hidden or too small:** 7 of 7,842 object-frames (all blue cup, ep11). They hold 0 % of the positives, so the hidden gate plays no role.

### Per class (pooled over the episodes containing it; kit-aligned label)

| class | AUROC | n_pos / n_neg | episodes | `behind` mean on negatives / positives |
|---|---|---|---|---|
| plastic_dish_rack | 0.981 | 290 / 775 | 12, 13, 26, 27, 31 | 0.010 / 0.121. All positives are ep31, so this compares ep31 against the other racks; CI withheld. |
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

When one episode holds all of a class's positives (rack, both boards, beige cup), `calib_gt/v2` withholds the CI. Before the fix, `calib_gt/v1_build` printed a rack CI of 0.970–0.991 from only 1,367 of 2,000 draws.

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

**ep13's AUROC of 0.26 comes from the one-sided score [M]:**
- Its 38 bad blue-cup frames show up as `front`: median `front` 0.50 against 0.06 on good frames, and median r −1.5 cm (p10 −3.9).
- So our cup sits beyond the observed surface, the direction the self-test showed `behind` cannot see.
- Within that track, `front` scores 0.75 and −median r scores 0.81 (post hoc). Pooled over all episodes, `front` scores only 0.449, because hands also produce `front`.

## Why it fails (measured, then hypotheses)
1. **Baseline level differs between objects more than the error signal [M].**
   - On *correct* frames, `behind` averages 0.046 on the white pot, 0.058 on the sweeper and 0.033 on the blue cup, but only 0.002–0.010 on the boards, lid and rack. The pitcher sits in between at 0.029.
   - Of the objects with the most positives, the boards (ep24) have the lowest `behind` and the pitcher (eps 21/22) a low one.
   - Pooling therefore ranks objects rather than frames.
   - Within single tracks it does no better:
     - mean within-track AUROC 0.628, or 0.608 with the pairs pooled;
     - centring `behind` on each track's median gives a pooled 0.517 (post hoc, not used for the verdict).
2. **The label is mostly not a camera-frame error, and what remains is small [M, H].**
   - [M] The kit aligns the scene once, at frame 0: rotation from the first object without a symmetry axis, translation from object 0 (`track3_pose.py:93-106`) [C]. That anchor object's frame-0 error is pushed into every object of the episode as a rigid offset. Depth cannot see such an offset.
     - Kit alignment against one global fit: 10.2° apart on ep31, 5.2° on ep21, 4.9° on ep22.
     - Re-labelled under other alignments, the pitcher, ep31's rack and ep24's boards lose most of their bad frames (table below).
   - [M] The ep21 pitcher agrees with depth on every valid frame (|median r| p50 0.11 cm, p90 0.28, max 0.49 over 186 frames), although its kit label reads 2.4–5.7 cm.
   - [M] What is left is small. The median positive ADD is 2.86 cm, and half-resolution stereo resolves about 1.1 cm at 0.5 m (map §1).
   - [M] Board slides along the table plane change almost no depth: the planted sideways shift gives behind + front of 0.00–0.13 on the boards.
   - [H] Much of the pitcher and board label is alignment or anchor offset, or in-plane drift.
     - Falsifier: the scan-mesh audit (`--meshes` set to the public scans) against the same label, plus the global-fit label. If the boards' and pitcher's global-fit errors stay invisible on scan meshes too, the mesh is not the reason.
3. **Not independent of the tracker [C].** FoundationPose fitted these same depth frames (`perc2.py:461, 473`), so what remains is what the tracker's own fit could not resolve.
4. **What depth does flag [M], and what that is worth [H]:**
   - [M] A per-object level offset: ep31's rack has a mean `behind` of 0.121, against ≤ 0.014 on eps 12, 13, 26 and 27, and a median r of +0.77 cm.
   - [M] Dust-pan errors on ep40 (0.99 within the track).
   - [H] This may make it a per-object anomaly flag for gross failures. It is not a per-frame error estimate, and the ep31 rack's offset is under 2 cm in camera depth.
     - Falsifier: a per-track AUROC ≥ 0.75 for "track has > 50 % bad frames" under both the kit label and the global-fit label, on public data.
5. **The ep23 hypothesis is wrong as stated [M].** The map expected the board identity swap to be invisible. In fact ep23 has the second-highest mean `behind` (0.093), and wooden_piece_1 is hidden on 36 frames. The track also has depth-visible errors besides the swap.

## Verification and fixes (30 Oct; verifiers 07:26–07:43 UTC, fixes 07:45–07:58 UTC; CPU, $0)
Two verifiers reviewed the build.
- **Verifier 1:** independent geometry and label checks. Verdict: defective in the report only.
- **Verifier 2:** statistics and τ sensitivity. Verdict: sound, with reporting defects.

Each defect below was reproduced before it was fixed. No verifier claim was rejected. Two small corrections to their numbers are noted.

### What the verifiers confirmed (no change needed) [M]
- **Inputs:** every `audit.json` lists only inference inputs. `perc2.py` writes `poses.npz` (line 501) before it reads mocap (line 508), and the hands code reads no `observation`, parquet or mocap data.
- **Geometry and units:**
  - Depth is (N, 1000, 1600) in metres at full-resolution KR. KR recomputed with `cv2.stereoRectify` equals the stored KR exactly.
  - An independent renderer reproduces `n_sel`, `behind`, `front` and `med_r` exactly on ep13 and ep21.
  - Low-error frames have a median residual of +0.09 cm.
  - Each wrong convention fails clearly: transposed rotation, world pose read as a camera pose, half-resolution K, OpenGL axes, and frame offsets of ±1 to ±4.
- **Statistics:**
  - Re-running `calibrate.py` reproduced the build byte for byte.
  - An independent pair-counting AUROC gives 0.60024; counting ties as losses or as wins gives 0.599 or 0.602.
  - An independent bootstrap gives the same CI.
  - Audit and label frames join 1:1. The label's `poses_world_vo` equals `world_T_cam @ cam_T` exactly.
  - All 20 public episodes are used; adding ep23 back gives 0.607.

### Defects and fixes

| # | defect (verifier) | evidence reproduced here [M] | fix | result after re-run [M] |
|---|---|---|---|---|
| 1 | "What depth can see" claims depend on the kit's frame-0 alignment (V1 D1) | Verifier 1's script, copied unchanged as `scripts/gt_align_labels.py` and re-run on all 20 episodes, matches the verifier's files to 0 difference. Its kit label equals the stored label to 0.0 cm. | Label-robustness table added (below); calibrate gains `--labels_align`. The 3 cm, 5 cm, rack, pitcher and board claims are marked alignment-dependent; the "gross-failure flag" is downgraded to [H]. | Falsified under all three alignments (0.600 / 0.416 / 0.405) |
| 2 | Eval-3 depth read in the map stage before PREREG, undisclosed (V1 D2) | File times: `sanity_ev3_{perc4,ref4}.json` 06:40:13–14 UTC; `dl_eval3` 06:38; `MAP.md` 06:49:59 | Disclosed in Integrity and in `PREREG.md` note 2. Eval 3 is excluded from any spoon test or reported apart. `MAP.md` copied unchanged into this folder. | Spoon set, if ever run: 5, 6, 15, 16, 32, 33, 35, 36, 37 |
| 3 | Guard accepts this study's ground-truth outputs (V1 D3) | Before the fix: `ep12_pf.npz`, `ep12_lib.json`, `calib/calib.json` and `calib/per_episode.csv` were accepted, and only `per_frame.csv` was refused. | `refine.FORBIDDEN_SUBSTR` gains `_pf.npz`, `/gt/` and `calib_gt`, plus a `gt` / `*_gt` directory rule; `depth_audit.assert_ref_parquet` uses the same list. `calib/` becomes `calib_gt/`. Verifier ground-truth outputs move under `work/gt/`. | `scripts/guard_test.py`: 448 inference paths accepted, 349 GT paths refused; 40/40 eval reference parquets still pass the refs allowance; `check_refine.py` ALL OK; ep11 re-audit bit-identical |
| 4 | Verdict's fragility not reported (V2 D1) | LOO 0.533–0.740; 81.7 % of positives in eps 24/31/22/21; 5.09 effective episodes; 63.9 % of draws < 0.65 and 12.1 % ≥ 0.75; episode-balanced 0.645 (0.672 at τ 2.0 cm) | Added to Verdict; `calibrate.py` writes `fragility` (LOO with the rule's verdict per drop, balanced AUROCs, concentration, bootstrap shares) | Only dropping ep24 moves the verdict, to INCONCLUSIVE. Same decision. |
| 5 | "ADD > 3 cm 0.754" overstated (V2 D2) | CI 0.53–0.88; without ep31 0.653 (CI 0.48–0.86); ep31's rack holds 289 of 690 positives; LOO at 3 cm 0.653–0.836 | Verdict line replaced; `calibrate.py` writes `thr3` | Secondary label only. Verifier 2 attached the 0.53–0.88 CI to the "without ep31" figure; that CI belongs to all episodes. Without ep31 the CI is 0.48–0.86. |
| 6 | Within-episode 0.700 shown without within-track figures (V2 D3) | Within-track mean 0.628 (11 tracks), pairs pooled within tracks 0.608, within episodes 0.708 | Added to Results and "Why it fails"; `calibrate.py` writes `within` | – |
| 7 | "Cannot rank episodes" claims too much (V2 D4) | ρ 0.24, Fisher-z 95 % CI −0.13 to 0.55, n = 31 episode-objects | Reworded; CI written to `calib.json` | – |
| 8 | Rack per-class CI from 1,367 of 2,000 draws (V2 D5) | `calib_gt/v1_build`: [0.970, 0.991, 1367] | `boot_ci` withholds the CI if < 95 % of draws are finite or one episode holds all positives, and gives the reason | Rack, both boards and beige cup now `ci: null` |
| 9 | Nits (V2) | Rule line lacked the ≥ 8-episode condition; the pitcher's `behind` (0.029 on negatives) is low but not the lowest | Both fixed | – |
| 10 | Note: ep13 0.26 is one-sided (V1) | ep13 bad cup frames: median `front` 0.50, median r −1.5 cm; within-track `front` 0.75 | Added under the per-episode table | – |

### Label alignment (same registration and symmetric ADD; only the scene alignment differs) [M]

| label | positives > 2 cm | `behind` AUROC > 1 / > 2 / > 3 cm | 95 % CI (> 2 cm) | verdict by rule (> 2 cm) |
|---|---|---|---|---|
| kit: frame 0, anchor object (stored, primary) | 1447 | 0.506 / **0.600** / 0.754 | 0.40–0.78 | FALSIFIED |
| one global SE(3) fit over all frames and objects | 222 | 0.455 / **0.416** / 0.496 (40 pos) | 0.24–0.81 | FALSIFIED |
| frame-0 fit over all objects | 1047 | 0.457 / **0.405** / 0.499 (477 pos) | 0.30–0.58 | FALSIFIED |

**Share of frames with ADD > 2 cm, kit → global fit → frame-0 all-object fit:**
- ep21/22 pitcher: 0.98 → 0.03 → 0.25 / 0.20.
- ep31 rack: 1.00 → 0.00 → 0.00.
- ep31 sweeper: 0.27 → 0.02 → 0.01.
- ep24 boards: 0.82 / 0.79 → 0.13 / 0.13 → 0.83 / 0.79.
- ep11 cups: 0.46 / 0.04 → 0.21 / 0.00 → 1.00 / 1.00.

**Caveats:**
- No label equals the camera-frame error that depth sees, because the mocap-to-camera transform is unknown.
- The kit label injects the anchor object's frame-0 error into all objects.
- The global fit absorbs any constant per-episode offset, so it is lenient. ep31's rack is +0.77 cm proud in depth, yet has 0 % bad frames under the global fit.
- Under the global label, `|median r|` at > 3 cm gives 0.757 and behind + front 0.681. That rests on 40 positives in 7 episodes and is post hoc.
- Verifier 1 reported 1,054 positives for the frame-0 all-object fit. Their own script on the same files gives 1,047, the figure used here.

### Violation margin τ (verifier 2's re-audits of all 20 episodes; calibrated here with `calibrate.py`) [M]

| τ | AUROC > 2 cm | 95 % CI | > 1 cm | > 3 cm | episode-balanced | LOO range | verdict by rule |
|---|---|---|---|---|---|---|---|
| 1.0 cm | 0.584 | 0.38–0.78 | 0.477 | 0.767 | 0.599 | 0.497–0.713 | FALSIFIED |
| 1.5 cm (build) | 0.600 | 0.40–0.78 | 0.506 | 0.754 | 0.645 | 0.533–0.740 | FALSIFIED |
| 2.0 cm | 0.606 | 0.42–0.79 | 0.522 | 0.722 | 0.672 | 0.562–0.742 | FALSIFIED |

At every τ, only dropping ep24 makes it INCONCLUSIVE.

## Side findings (exploratory; not used for any decision)
- **Rest label bug [M].** The rest label comes from our own track only, so an object held still in the hand counts as resting. That gives maximum |rest height| of 13–23 cm (ep39 13.1, ep24 14.7, ep44 21.1, ep45 22.5). Before reuse, a rest frame needs hand_frac = 0, or a support test against the plane.
- **Rest height medians [M]:**
  - our dish rack sits 1.0–1.3 cm *below* the local table plane (eps 12, 13, 27);
  - the pot lid on eps 0/2 sits 1.3–1.4 cm below it (about 165 frames each).
  - [H] This is mesh foot or rim geometry against blurred depth, or a real 1 cm sink. The audit cannot tell which.
- **v1 rest planes [M].** With no offset gate, the v1 ring planes latched onto the floor 60 cm down on eps 21, 22, 26 and 27. This was fixed in v2 before the ground truth was read (amendment 1).

## Not done (by the rule)
- Eval perception- and reference-mode audits, per-episode predicted reference loss, and the spoon test.
  - If any of these ever runs, eval 3 is reported apart (`PREREG.md` note 2).
- **Side question from the map, still possible but not run here:**
  - The question: on evals 8, 14, 30, 32 and 33, which of the two eval tracks agrees with depth?
  - It is a GT-free sanity check, and the 25–45 cm disagreement is the gross level at which `behind` works.

## Files
**Repository** (committed as WIP by the orchestrator in d7d4e01, 8c51b23 and e23faa5; this RESULTS.md is uncommitted):
- `pipeline/depth_audit.py`: new; inference side. The guard now shares the refine list.
- `pipeline/refine.py`: guard only; `FORBIDDEN_SUBSTR` gains `_pf.npz`, `/gt/` and `calib_gt`, plus `gt_dir_parts()`.
- `pipeline/score_registered.py`: `--per_frame` adds `<src>_adds_cm`; default outputs unchanged.
- In `docs/research/work/depth-audit-20261030/`:
  - `PREREG.md`: the rule, amendment 1, and note 2 (eval-3 disclosure, added after verification).
  - `MAP.md`: the map-stage record (06:50 UTC), copied unchanged from the scratchpad.
  - `RESULTS.md`: this file.
  - `calibrate.py`: ground-truth side.
  - `audit/public/ep<N>/audit.{npz,json}`: 20 episodes, 844 KB in total.
  - `audit/public_tau010/`, `audit/public_tau020/`: verifier 2's τ = 1.0 / 2.0 cm re-audits (no rest metric), inference side.
  - `audit_summary_public.csv`: per object; written before the ground truth was read.
  - `calib_gt/` (ground-truth derived; refused by the guard):
    - `v1_build/`: the build's output, moved unchanged from `calib/`;
    - `v2/`: after the fixes, with `fragility`, `within`, `thr3`, `label_alignment` and the Spearman CI. Its `per_frame.csv` (diagnostics only) adds `adds_glob_cm` and `adds_f0all_cm`;
    - `v2_tau010/`, `v2_tau020/`: the same for the τ audits.
  - `hand_mask_check_ep12.png`.
  - `scripts/`:
    - `run_pub_ep.sh`, `gt_label_jobs.sh`, `gt_label_jobs.txt`, `audit_summary.py`, `viz_hand.py`, `dl.py`;
    - new: `gt_align_labels.py` (ground-truth side) and `guard_test.py` (path checks only).

**Scratchpad only** (`/tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/daudit/`):
- `work/v1/`: the v1 audits, kept.
- `work/gt/` (ground truth; refused by the guard):
  - `lab/` and `lab_s2/`: labels;
  - `lab_align/`: alignment labels and their logs;
  - `verify_r1/vgeo_out/` and `verify_r2/{calib_rerun,stats_t15.json,tau_stats.json}`: the verifiers' ground-truth outputs, moved here with symlinks at the old paths.
- `work/s2/`: the S2 tracks.
- `fixchk/`: the ep11 re-audit, the `check_refine` work dir and logs.
- `vgeo/`, `vstat/scripts/`, `vstat/tau/`: the verifiers' scripts and τ audits.
