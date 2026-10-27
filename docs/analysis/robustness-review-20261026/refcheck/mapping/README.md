# mapping: does sim_vs_ref predict the truth score? (public episodes, 27 Oct 2026)

Check for the robustness review (`docs/analysis/robustness-review-20261026.md`). The review's loss budget rests on
two relations that no script in the repo recomputed:
- "true AUC ≈ 0.979 × sim_vs_ref when the reference is sound (57 policy means, 10 episodes)" (forensics README §1);
- the multiplicative model "truth ≈ sim_vs_ref × reference accuracy" (`loss_budget.py`, which solves the spoon from it).

This folder recomputes both from every stored public rollout, using public mocap. Mocap is read only by scoring and
diagnostics, after inference. Labels: **[M]** measured here (command in "Commands"), **[D]** taken from a doc,
**[E]** derived from measured numbers, **[H]** hypothesis, with the experiment that would falsify it.

## Answer

All numbers below are **[M]**, from `calibrate.py fit`, unless marked otherwise.

**1. The 0.979 factor is right in size but cannot be reproduced exactly.**
- From our rollouts (own-mesh policy means), T = k·S gives:

  | Policies | k | RMSE |
  |---|---|---|
  | all 266 (10 episodes) | 0.982 | 0.040 |
  | R ≥ 0.95: 125 (episodes 2, 18, 27, 39) | 0.985 | 0.029 |
  | S ≥ 0.8 and R ≥ 0.95: 37 (episodes 18, 27, 39), the regime of packed eval rollouts | 0.976 | 0.015 |

  With each episode weighted equally, k is 0.969–0.972.
- The box-recorded `summary.json` means are 58 distinct policy means over 10 episodes, very likely the forensics'
  "57". They give a least-squares k of 0.976 and a sum ratio of 0.989. Dropping one of them gives 0.983.
- No subset gives exactly 0.979, and the forensics recorded no recipe.
- For the review this is harmless. Applied to pack 4 (mean S 0.912 [D], leaderboard 0.8106 [D]), k = 0.969–0.985
  puts the eval-specific loss at **0.073–0.088 [E]**. The review uses 0.082.

**2. T = k·S is not a law that ignores the reference. It holds only where the reference is good (R ≳ 0.93).**

| R group | S 0–0.3 | 0.3–0.6 | 0.6–0.8 | 0.8–0.9 | 0.9–1.0 |
|---|---|---|---|---|---|
| R ≥ 0.95 (ep2, 18, 27, 39) | 1.020 | 1.038 | 0.985 | 0.968 | 0.978 |
| 0.85–0.95 (ep11, 12, 24, 26, 31) | 1.028 | 1.054 | 0.996 | 0.992 | 0.981 |
| R < 0.85 (ep21, 24, 31) | 1.029 | 0.933 | 0.934 | 0.820 | 0.800 |

(sum T / sum S of own-mesh policy means, by S bin; `tables.md`, "Where each model breaks")

- At low S, T ≈ S whatever the reference.
- At high S, T/S falls to about R. On ep21, the pitcher reference has R 0.78, and policies with sim_vs_ref 0.98 score
  T 0.77–0.80, a residual of −0.17 against k·S.
- The pooled fits look good because most stored policies are low-S checkpoint-curve points.
- The qualifier "when the reference is sound" carries the whole claim. On eval episodes, reference soundness is
  exactly what we cannot see.

**3. The multiplicative model T = S·R has the right shape at high S and the wrong shape at low S.**
- **At S ≥ 0.8** (55 policies, 5 episodes):

  | Model | RMSE | Bias |
  |---|---|---|
  | T = S·R | 0.029 | +0.022 (T above S·R) |
  | T = a·S·R, a = 1.025 | 0.020 (the best model there) | |
  | T = k·S | 0.045 | |

- **At low and mid S,** S·R under-predicts T by 0.01–0.09: about +0.01–0.03 with R ≥ 0.95 and +0.04–0.09 with
  R < 0.95. The reference's error is not paid where the simulation does not follow the reference.
- **By object** (S ≥ 0.8), T_obj − S_obj·R_obj is ≈ 0 for most objects. The exceptions:
  - ep12 rack: +0.090;
  - ep21 pitcher: +0.050;
  - ep27 pot: +0.037.

  There T exceeds the product: the rack in frames where it rests, the pitcher and the pot in frames where they move
  (see 7).
- **By episode,** with all policies (the residual of S·R):

  | Episode | Residual |
  |---|---|
  | ep11 | +0.13: the blue cup is never moved in simulation and sits on the truth (T_obj 1.00) while our reference drifts (R_obj 0.86) |
  | ep31 | +0.08 |
  | ep12 | +0.04 |
  | ep24 | +0.04 |
  | ep2 | −0.03 |

**4. How much of a sim_vs_ref gain transfers to T.**
- **Public pairs:** inside one episode, reference and mesh set, the slope dT/dS is:

  | Policies | Slope |
  |---|---|
  | own-mesh, 266 policies in 18 groups | 0.94 |
  | R ≥ 0.95 | 0.97 |
  | R < 0.95 | 0.88 |

- In groups that reach high S, the slope is close to R:

  | Episode | Slope | R |
  |---|---|---|
  | ep27 | 0.962 | 0.962 |
  | ep39 | 0.948 | 0.956 |
  | ep18 | 0.968 | 0.966 |
  | ep12 | 0.970 | 0.935 |
  | ep21 (two groups) | 0.71 / 0.74 | 0.77 / 0.78 |

- **Leaderboard, pack 3 → pack 4** (7 changed episodes):
  - Σ dS / 20 = 0.0291 and dLB = 0.0216 [D], so 0.743 of the raw sim_vs_ref gain transferred.
  - Against the 0.979 × dS prediction the ratio is 0.759: that is the work log's "76 %".
  - Error bar from single-draw noise alone: σ(T | S) = 0.008 per draw for public policies with S ≥ 0.8, two draws per
    changed episode, so σ(transfer) ≈ 0.05.
  - So the leaderboard transfer sits about 4σ below the public pairs (0.94–0.97). It is also about 2.6σ below what
    `loss_budget.py`'s per-object accuracies predict for those 7 episodes (0.88) **[E]**.
  - Reading: on public pairs the marginal transfer at high S equals R (see 7). If that holds on eval, the changed eval
    episodes have a dS-weighted reference accuracy of ≈ 0.74 ± 0.05, against the ≈ 0.88 that `loss_budget.py`
    assumes for them **[E, H-scale]**.
  - Eval 33, the spoon and cup hold, carries 0.32 of the 0.58 summed dS. If the other six transferred as modelled,
    eval 33 transferred only ≈ 0.62 ± 0.10 (draw noise only) **[E]**. The model's value for it is 0.875.

**5. The `loss_budget.py` spoon solve is fragile.**
- With a = 1.015 or 1.027 (the high-S fits) instead of 1, the implied spoon accuracy moves from 0.80 to 0.76 or 0.73
  **[E]** (pack 4).
- The multiplicative form is the right one at high S, but its scale is uncertain by a few percent, and the spoon
  absorbs all of that uncertainty.

**6. The yardstick choice does not matter.**
- The GT-free leaderboard-style yardstick S_mesh (our mesh, symmetry, registered scene alignment) tracks T no better
  than the pipeline's S. Policy RMSE under T = k·S: 0.039 vs 0.040; at S ≥ 0.8: 0.045 vs 0.045. Hypothesis H-yard is
  falsified.
- The evaluator's own `metrics.add_auc` is worse: corr(T, ·) 0.977 vs 0.986 (rollouts), RMSE 0.057 vs 0.040
  (policies).
- The pipeline's choice of S (qa.py) is therefore the right one to keep.

**7. Frame by frame (diagnostic, 713 own-mesh rollouts; mocap per frame).**
- **The frame-local product is no better than S·R.** mean_f g_s·g_r beats S·R only slightly:

  | Rollouts | RMSE, product | Bias, product | RMSE, S·R |
  |---|---|---|---|
  | all | 0.055 | +0.035 | 0.058 |
  | S ≥ 0.8 | 0.029 | +0.020 | 0.030 |

  - The covariance of g_s and g_r is small (+0.005).
  - The two other combinations do worse: √(e_s²+e_r²) about the same, e_s+e_r much worse (bias +0.10).
  - So the errors neither add nor stack in time. The leftover is T sitting above the product.
- **Where T beats the product: in frames where the true object is at rest** (H-rest; within 1.5 cm and 5° of its
  frame-0 pose). Of the mean +0.035 excess:
  - +0.025 comes from rest frames;
  - with R < 0.95: +0.043 of +0.047;
  - at S ≥ 0.8 with R < 0.95: +0.034 of +0.034.
- The objects behind this mostly rest in the truth for the whole episode:

  | Object | Excess from rest frames | T_obj | R_obj |
  |---|---|---|---|
  | ep11 blue cup | +0.25 | 0.98 | 0.87 |
  | ep31 rack | +0.10 | 0.58 | 0.74 |
  | ep12 rack | +0.09 | 0.96 | 0.94 |
  | ep24 board 2 | +0.05 | 0.35 | 0.86 |
  | ep26 pot | +0.04 | 0.22 | 0.86 |

  (The excess is measured against the per-object product; T_obj and R_obj are means over all own-mesh rollouts. The
  ep24 board and the ep26 pot rest only part of the time: rest shares 0.42 and 0.33.)

  Our reference drifts or jitters them (occlusion while the other object is handled). The simulation leaves them
  where they are, which is where the truth is. S then charges the policy for not following the drift, and R charges
  the reference for it. That double count is the main reason a > 1.
- **The opposite case exists:** the ep26 rack (−0.03) is knocked in simulation while the truth stays put.
- **Transfer is predicted by the global R.** At high S (1 063 pairs with the better policy at S ≥ 0.8), dT is
  predicted by:

  | Prediction | RMSE | Bias | Σ dT / Σ prediction |
  |---|---|---|---|
  | dS·R | 0.018 | +0.001 | 1.003 |
  | the frame-local dT_local = mean_f Δg_s·g_r | 0.019 | | |
  | dS alone | 0.027 | −0.012 | 0.95 |

  The marginal value of a sim_vs_ref gain at high S is R, and the frame-local refinement adds nothing on public data.

## Per episode (own-mesh policy means; residual = T − prediction, k = 0.985)

| ep | objects | policies / rollouts | R | mean S | mean T | Σ T / Σ S | resid k·S | resid S·R | at S ≥ 0.8: policies, T/S, resid S·R |
|---|---|---|---|---|---|---|---|---|---|
| 2 | pot + lid | 4 / 9 | 0.980 | 0.285 | 0.248 | 0.869 | −0.033 | −0.032 | none |
| 11 | blue + beige cup | 14 / 52 | 0.884–0.899 | 0.452 | 0.535 | 1.185 | +0.091 | +0.133 | none |
| 12 | blue cup + rack | 47 / 122 | 0.932–0.935 | 0.737 | 0.729 | 0.990 | +0.004 | +0.040 | 14, 0.986, +0.045 |
| 18 | sweeper + dust pan | 75 / 185 | 0.963–0.966 | 0.353 | 0.360 | 1.020 | +0.012 | +0.020 | 6, 0.965, −0.000 |
| 21 | blue cup + pitcher | 18 / 61 | 0.774–0.778 | 0.483 | 0.409 | 0.846 | −0.067 | +0.034 | 4, 0.804, +0.025 |
| 24 | two boards | 47 / 113 | 0.816–0.882 | 0.211 | 0.215 | 1.016 | +0.007 | +0.041 | none |
| 26 | rack + pot | 4 / 9 | 0.923 | 0.432 | 0.391 | 0.906 | −0.034 | −0.008 | none |
| 27 | rack + pot | 31 / 83 | 0.962 | 0.876 | 0.864 | 0.987 | +0.002 | +0.022 | 23, 0.984, +0.021 |
| 31 | sweeper + rack | 11 / 35 | 0.823–0.853 | 0.580 | 0.565 | 0.975 | −0.006 | +0.082 | none |
| 39 | dust pan | 15 / 44 | 0.956 | 0.640 | 0.619 | 0.967 | −0.011 | +0.007 | 8, 0.959, +0.003 |
| 0, 13, 22, 23, 40–45 | — | no stored rollouts | | | | | | | |

The ep21 rows here are policy means over all S. The high-S ep21 policies are the ones that break k·S (−0.17).

## Hypotheses (not established; each with the experiment that would falsify it)

- **H-local (tested on public data: falsified as stated).** The claim was that a gain transfers at the reference's
  accuracy in the frames where it happens, rather than at the global R. On 1 063 high-S public pairs, the frame-local
  prediction was no better than dS·R (RMSE 0.019 vs 0.018). What survives is the simpler "transfer ≈ R at high S".
- **H-rest (survives the public test).** Where the true object rests and our reference drifts, the simulation keeps
  the object at the truth. Then T_obj > S_obj·R_obj, and both the policy-loss and the reference-loss buckets
  over-count.
  - Evidence: the positive part of T − mean(g_s·g_r) sits in rest frames (section 7).
  - Further test: the same split on new public references. H-rest is falsified if objects with full rest share show
    no excess when their references drift by more than 1 cm.
- **H-freeze (new, untested).** Freezing, in the reference, every object that no hand touches would raise R and S
  on those objects without lowering T. One example is the ep11 blue cup, which rests the whole episode but drifts in
  our reference. GT-free trigger: no hand-object contact in the reference.
  - CPU test on public episodes: freeze the never-contacted objects at their median pose; score R and the existing
    rollouts' S. Falsified if R does not rise on ep11, ep12 and ep31.
  - It is not established that freezing changes T: the simulation already keeps those objects still, and ep26 shows
    the opposite case.
- **H-scale.** On eval episodes, a sim_vs_ref gain transfers at the reference's accuracy, as on public pairs. Then
  the pack 3 → 4 transfer of 0.74 means the changed eval episodes' references are ≈ 0.74 accurate (dS-weighted).
  - Test: a pack that changes only one episode with public-like objects (e.g. eval 19 or 38). Its transfer should be
    ≈ 0.95; transfer < 0.85 would falsify H-scale.
  - A pack that changes only eval 33 should show ≈ 0.6.

## Caveats and problems

**About the data:**
- **The "sound reference" evidence is thin.** Only 4 of the 10 episodes reach R ≥ 0.95 (2, 18, 27, 39), and only 3
  of those reach S ≥ 0.8.
  - Of the high-S episodes, only ep21 (one pitcher reference, two groups) has a bad reference. So "transfer ≈ R at
    low R" rests on one object.
- **The most recent evidence is all on unsound references.** The 60 most recent rollouts are the ep21 and ep11 twins,
  and T = k·S gives k = 0.83 there.
- **The fits are not independent samples.** Policies are mostly checkpoint-curve points of a few trainings
  (ep18: 75 policies). Each episode weighted equally gives k 0.969–0.972.

**About the scorer:**
- **The hidden mesh is approximated.** T and R use the public scan in its place, as `score_registered.py` does.
  The leaderboard's own hidden mesh can differ (`../scorer/`).
- **The leaderboard transfer is a single measurement.** It rests on 7 changed episodes. Its σ covers single-draw
  noise only, taken from public high-S policies. Eval 25 is bimodal, so that σ is a lower bound.

**Fixed in this pass:**
- Six 21 Oct rollouts had been assigned library_v3. They ran before route A, so they are now scored with the scans.
- `calibration.json` had missed the box-summary and leaderboard parts, which were written after the dump.

**Not fixed:** the 0.979 recipe is not recorded anywhere (section 1).

## Method

**Rollouts.**
- The store lists 2 819 evaluator parquets (`episode_XXXXXX.parquet`) of public episodes. Grouped by the file's
  sha256 (the HF LFS hash), they give 747 distinct rollouts [M].
- All 747 were downloaded and scored, so the "~60 most recent" cap was not needed and nothing was dropped. The 60 most
  recent rollouts (by run date) are also fitted on their own (`recent60_rollouts`).
- A **policy** is one checkpoint (sha256 from the episode json), one reference (digest of its `reference_xyzw`
  columns) and one mesh set. Its numbers are means over its distinct rollouts.
- Kinds: 319 repeat evaluations of a chosen checkpoint, 282 checkpoint-curve points, 99 sweep points, 47 single
  rollouts.
- Only 10 public episodes have rollouts: 2, 11, 12, 18, 21, 24, 26, 27, 31, 39. Episodes 0, 13, 22, 23 and 40–45
  have none (as `resolve/canonical_refs.json` found).

**Three numbers per rollout.**
- **T** (truth): the simulated object path against mocap. This is the registered Track 3 ADD AUC, exactly as
  `pipeline/score_registered.py` computes it. The hidden mesh is stood in for by the public scan, and the meshes the
  run simulated are registered to it.
- **R** (reference accuracy): our reference (the rollout's `reference_xyzw`) against mocap. Same computation and
  meshes as T.
- **S** (sim_vs_ref): the simulated path against our reference, computed the way the pipeline does
  (`pipeline/qa.py policy`, also `tools/choose_learner.py`):
  - the kit AUC with the frame-0 warp;
  - 500 points on a 5 cm sphere per object;
  - no mesh, no symmetry.
  This is the number in every box's `qa_policy.json` and `summary.json`. The evaluator's own `metrics.add_auc`
  (episode json) is fitted as an alternative.
- **Meshes the run simulated:** from the `make_assets` fingerprint in each run's job.log (object extents matched to
  `meshes/library_*`).
  - Runs before route A (job.log starting before 21 Oct 10:20 UTC, no fingerprint, or `assets: PUBLIC scans`) used
    the public scans.
  - 34 rollouts (22 policies) simulated the scans. They are kept out of the own-mesh fits. The other 713 rollouts
    simulated our meshes: library_v3 576, library_v2 111, library_v3x 26.

**Checks that the numbers are the right ones** [M]:
- `verify`: 16 rollouts (every episode × mesh set) scored with `pipeline/score_registered.py` itself. 16/16 equal in
  T, R and per-object AUC (`verify.json`).
- T equals the box-stored `score_registered*.json` in 202/202 rollouts where the box scored with the simulated
  meshes.
- S equals the box `qa_policy.json` in 733/733 rollouts that have one (max difference 0.0000).
- Six 21 Oct "hard" rollouts were first scored with library_v3 by the default rule. The job.log shows they ran
  before route A, so they were re-scored with the scans. That reproduces the work log's box numbers [D]: ep21
  0.825, ep18 0.128 / 0.337, ep24 0.236 / 0.152.

**Models fitted** (least squares, no intercept unless stated). Fits are run on rollouts and on policy means, on all
data and on subsets:
- T = k·S;
- T = 0.979·S (the forensics claim);
- T = S·R and T = a·S·R;
- T = S·R̄, with R̄ the mean per-object reference AUC (`loss_budget.py`'s form);
- T = b·S + c.

**Diagnostics** (they need mocap, so they are not usable on eval):
- **frame-local models** (`frames`), per frame and object:
  - g_s = the kit's per-frame AUC share of the sim-vs-reference error;
  - g_r = the same for the reference-vs-truth error;
  - g_t = the same for the sim-vs-truth error.
  - Compared: T against mean(g_s·g_r), mean g(√(e_s²+e_r²)) and mean g(e_s+e_r). The difference T − mean(g_s·g_r) is
    split by whether the true object is at rest at its frame-0 pose (within 1.5 cm and 5°).
- **GT-free alternative yardstick S_mesh** (`symS`): the leaderboard's registered computation with OUR reference as
  the truth and OUR simulated mesh as the scan. It uses the symmetry axes from our mesh and reads no mocap.

## Commands

All CPU, one process at a time, on the session container. Python env:
`source /tmp/claude-0/-home-user-v2d-track3/12630086-0942-582d-80bb-a9806af3e32b/scratchpad/refcheck/venv/bin/activate`.
The scratch root (`--sp`) defaults to the refcheck scratch. WORK = `<sp>/work/mapping`.

```
cd docs/analysis/robustness-review-20261026/refcheck/mapping
python -I calibrate.py inventory   # HF file list + sha256 via get_paths_info -> WORK/inventory.json (2819 -> 747)
python -I calibrate.py fetch       # one copy of each distinct parquet + episode json / qa_policy / score_registered / job.log
python -I calibrate.py libs        # make_assets fingerprints -> WORK/run_libs.json
python -I calibrate.py score       # T, R, S per rollout -> WORK/rows.jsonl (747 rows, ~70 min on one core; resumable)
python -I calibrate.py verify      # 16 rollouts through pipeline/score_registered.py -> verify.json (~7 min)
python -I calibrate.py symS        # S_mesh per own-mesh rollout -> WORK/s_mesh.json (~6 min)
python -I calibrate.py frames      # frame-local diagnostics -> WORK/frames.json, WORK/frames_arr/ (~8 min)
python -I calibrate.py fit         # -> calibration.json, tables.md, policies.json, rollouts.json, box_summaries.json
WORK/plotenv/bin/python -I calibrate.py plot   # -> calibration.png (the scoring venv has no matplotlib)
```

The `score` step re-scores any row whose mesh rule has changed. The six hard-run rows above were re-scored this way.

**When things ran:**
- The 741 other rows were scored on 26 Oct, about 17:12–18:22 UTC (same code path).
- On 27 Oct (UTC):

  | Step | Time |
  |---|---|
  | verify | 03:21–03:28 |
  | re-score | 03:29 |
  | symS | 03:30–03:36 |
  | frames | 03:45–03:52 |
  | fit and plot | 03:53 |

**Machine and code:**
- All on the session's CPU container. No GPU, no Vast, no uploads.
- The repo was at e2f0a6b, plus this folder's uncommitted `calibrate.py`. The pipeline scripts it calls are unchanged.

## Files

- `calibrate.py`: the whole computation, re-runnable from the store.
- `calibration.json`: every fit, subset, per-episode and per-object residual, transfer, leaderboard and frame-local
  number.
- `tables.md`: the same as tables, generated.
- `policies.json`: the 288 policy means.
- `rollouts.json`: the 747 rollouts with T, R, S and per-object values.
- `box_summaries.json`: the 58 box-recorded policy means used for the 0.979 reproduction.
- `verify.json`: the 16 comparisons with `pipeline/score_registered.py`.
- `calibration.png`, four panels:
  - T against S;
  - T against S·R;
  - the residual of k·S against R;
  - the within-group transfer slope against R.
