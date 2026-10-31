# GT-free audit of the packed eval rollouts (packs 7 and 8), 31 Oct 2026

CPU only (this cloud VM), $0. No Vast, no GPU, no Kaggle; nothing posted, no pack changed. Labels: [M] measured here,
[E] estimate, [H] hypothesis.

**Integrity.** No ground truth was read. Each packed rollout is scored against **our own reference**: the reference
columns of the evaluator's output parquet, which hold the reference the policy was trained to follow. Scoring uses the
kit's metric functions (rdlib chain). The host geometry is our library mesh (identity registration), and object names
and slot order come from the kit roster `data/track_3_evaluation_objects.json`. The public check reads only rollout
parquets and the numbers already stored in `roll_rollouts.json`. It reads no public episode parquet and no scan.

## Answer first

1. **Pack 7 has one failed rollout of 20: eval 10 [M].**
   - In the beige cup's rollout the cup is **left behind**. The simulated cup travels 0.7 cm, while the reference
     lifts it 23 cm (frame ≈ 48) and sets it down 15.8 cm from its start. The blue cup also stays put (1.0 vs 5.7 cm).
   - Against our reference: RPE 15.76 cm, MPPE 8.54, AUC 0.458. The evaluator's own relative error is 16.27 cm.
   - The failure is structural, not an unlucky draw: H5 gave 0.4495 ± 0.007 over 10 draws. The same failure appears
     on its public twin ep11 P (left behind, 14.6 cm).
2. **No other rollout is dropped, flung or left behind by the rule.** Seven are marginal, and none of them costs more
   than 0.09 cm of the 20-episode mean.
   - **Eval 32 (blue cup knocked twice):** per-frame RPE is 10–35 cm in frames ≈ 21–39; the cup recovers, is knocked
     again at frame ≈ 250 and ends 7.6 cm off. RPE 3.69.
   - **Eval 14:** the relation error is above 5 cm in 28 % of frames. RPE 3.39. Its H5 mean is 0.615 ± 0.199, so the
     packed draw was a good one.
   - **Eval 16:** the spoon ends rotated (keypoint error 7.2 cm in the last 10 % of frames).
   - **Evals 1, 3, 19, 25, 30, 33:** short transients only.
3. **GT-free means over 20 vs the board (pack 7) [M]:**

   | | GT-free mean | Board |
   |---|---|---|
   | RPE | 2.450 cm | 3.932 cm |
   | MPPE | 1.561 cm | 2.921 cm |
   | AUC | 0.911 | 0.8146 |

   - Pack 8 only changes eval 1: RPE 2.89 → 2.46, also not a failure. Its 20-episode RPE is 2.428.
4. **Contribution of the failure [E].**
   - Eval 10 is 15.76 / 20 = **0.79 cm** of the 20-episode mean RPE. Its excess over the median non-failed
     two-object episode (1.90 cm) is **0.69 cm**.
   - MPPE: 0.43 cm (0.36 cm excess). AUC: −0.023 against the median.
   - If eval 10 were a typical success, the board RPE would fall to ≈ 3.93 − 0.69 ≈ **3.24 cm** [E]. This assumes
     total ≈ policy on a left-behind rollout, as measured on ep11 (14.56 vs 14.57).
5. **About 1.5 cm of the board RPE (≈ 30 cm summed over the 16 two-object episodes) is NOT a deviation from our
   reference [E from M].**
   - On the 70 public P-arm draws, total − policy RPE is −0.06 cm on average for successes (range −0.83 to +0.42).
   - So with public-like reference error, the board RPE would be ≈ the GT-free 2.45.
   - The rest must be eval-side reference-vs-truth error, or the registration of our meshes onto the hidden scans.
     This audit cannot see either.
   - The decomposition expected 2–4 failure episodes at 10–50 cm [E, rpe-decomp README §"What this hands on" 2].
     That expectation is falsified for policy failures: there is 1.
   - See the hypotheses below.

## Table: pack 7, 20 eval episodes (plus pack 8's eval 1) [M]

Columns:
- packed s_v_r: the packed sim_vs_ref from `summary.txt`.
- RPE / MPPE / AUC: the kit's metrics of the simulated trajectory vs our reference, in cm (AUC unitless).
- max RPE: the largest per-frame RPE, in cm.
- > 5 cm: the fraction of frames whose per-frame RPE exceeds 5 cm.

Learner sources: pack READMEs `20261025-track3c`, `20261026-track3d` and `20261030-track3{g,h}`.

| ep | objects | learner | packed s_v_r | RPE | MPPE | AUC | max RPE | > 5 cm | flag |
|---|---|---|---|---|---|---|---|---|---|
| 1 | white_pot + white_pot_lid | standard (std0116) | 0.9196 | 2.89 | 1.36 | 0.914 | 15.1 | 0.12 | marginal: pot off in 7 % of frames (transient), ends 0.9 cm |
| 3 | white_pot + wooden_spoon | grasp lock (seed43) | 0.9418 | 2.09 | 1.14 | 0.938 | 9.9 | 0.12 | marginal: relation transient |
| 5 | white_pot + wooden_spoon | grasp lock (seed43) | 0.9595 | 1.69 | 1.05 | 0.959 | 4.6 | 0.00 | ok |
| 6 | white_pot + wooden_spoon | grasp lock (pack 1) | 0.9713 | 1.65 | 0.89 | 0.966 | 5.3 | 0.00 | ok |
| 8 | beige_cup + white_pot | grasp lock (eval_both) | 0.9783 | 1.48 | 0.75 | 0.978 | 4.9 | 0.00 | ok |
| **10** | blue_cup + beige_cup | grasp lock, carved cups (gl10A2) | **0.4563** | **15.76** | **8.54** | **0.458** | 27.4 | **0.76** | **FAIL: beige cup left behind (sim travel 0.7 of ref 25.1 cm)** |
| 14 | blue_cup + plastic_dish_rack | grasp lock (eval_both) | 0.9094 | 3.39 | 1.46 | 0.897 | 8.3 | 0.28 | marginal: cup 7.9 cm off path, off in 6 % of frames |
| 15 | plastic_dish_rack + wooden_spoon | grasp lock (seed43) | 0.9465 | 1.51 | 0.97 | 0.960 | 3.3 | 0.00 | ok |
| 16 | plastic_dish_rack + wooden_spoon | grasp lock (seed43) | 0.9079 | 1.58 | 1.36 | 0.899 | 4.2 | 0.00 | marginal: spoon ends rotated (kp 7.2 cm, last 10 %) |
| 19 | mini_sweeper + mini_dust_pan | standard (std1928) | 0.9278 | 2.63 | 1.36 | 0.925 | 6.8 | 0.07 | marginal: relation transient |
| 20 | blue_cup + water_pitcher | grasp lock (eval_both) | 0.8948 | 1.30 | 1.79 | 0.887 | 6.4 | 0.03 | ok |
| 25 | wooden_piece_1 + wooden_piece_2 | standard, carve s42 | 0.8937 | 2.78 | 1.69 | 0.882 | 15.1 | 0.14 | marginal: piece 2 transient, ends 2.2 cm |
| 28 | plastic_dish_rack + white_pot | standard (std1928) | 0.9290 | 1.87 | 1.37 | 0.916 | 5.9 | 0.02 | ok |
| 30 | mini_sweeper + plastic_dish_rack | standard (std30) | 0.9229 | 2.79 | 1.46 | 0.908 | 8.3 | 0.11 | marginal: relation transient |
| 32 | blue_cup + wooden_spoon | grasp lock frozen s46 | 0.8656 | 3.69 | 2.59 | 0.815 | 35.0 | 0.17 | marginal: cup knocked twice (18 cm off path), ends 7.6 cm off |
| 33 | blue_cup + wooden_spoon | grasp lock arm B (rcB) | 0.9401 | 1.90 | 1.16 | 0.941 | 14.2 | 0.06 | marginal: relation transient |
| 35 | wooden_spoon | grasp lock (pack 1) | 0.9829 | 0 (1 object) | 0.82 | 0.984 | – | – | ok |
| 36 | wooden_spoon | grasp lock (pack 1) | 0.9912 | 0 | 0.63 | 0.994 | – | – | ok |
| 37 | wooden_spoon | grasp lock (pack 1) | 0.9979 | 0 | 0.46 | 0.998 | – | – | ok |
| 38 | mini_dust_pan | grasp lock (pack 1) | 0.9998 | 0 | 0.37 | 1.000 | – | – | ok |
| 1 (pack 8) | white_pot + white_pot_lid | standard, carve s43 (c01s43) | 0.9232 | 2.46 | 1.35 | 0.916 | 16.7 | 0.13 | marginal: pot off in 8 % of frames (transient), ends 0.7 cm |

- Per-object features are in `evalaudit.json`: AUC, MPPE, fraction of frames off, end and maximum error, reference vs
  simulated travel, distance from the reference path, and the vertical offset.
- The packed sim_vs_ref (`qa.py`) and the AUC here differ by at most 0.05 (eval 32: 0.866 vs 0.815). They are
  different AUC chains.
- The evaluator JSON's `relative_position_error_cm` equals our RPE within 0.03 cm where slot 0 has no symmetry axis
  (10 episodes). Where slot 0 is a cup it is higher (6 episodes), because the kit ignores cup spin.

**Contribution to the 20-episode mean RPE (pack 7) [M shares, E board effect].**
- Share = RPE / 20. Excess = (RPE − 1.90) / 20, where 1.90 cm is the median of the 15 non-failed two-object episodes.
- Eval 10: share 0.79, excess **0.69**.
- Eval 32: share 0.18, excess 0.09.
- Eval 14: 0.17, 0.07. Eval 1: 0.14, 0.05. Evals 25 and 30: 0.14, 0.04.
- The 15 non-failed two-object episodes average 2.22 cm and sum to 33.2 cm.
- The board implies (78.6 − 15.8) / 15 ≈ 4.2 cm for them, assuming the board RPE of eval 10 ≈ its GT-free 15.8 [E].

## Check on public draws (pipeline vs `roll_rollouts.json`) [M]

The same code path (`audit.py check`) was run on all 70 P-arm draws of
`docs/analysis/rpe-decomp-20261031/roll_rollouts.json`.
- **Policy numbers.** Our RPE, MPPE and AUC equal the stored GT-free "policy" numbers to 4 decimals in **70 / 70**
  draws (max |Δ| = 0).
- **Agreement with total.** r(policy RPE, total RPE) = 0.99983 and r(MPPE) = 0.99947. Total is the score against
  mocap, copied from the json; it was not recomputed here.
- **Flag.** It marks 33 draws, whose total RPE spans 10.1–76.8 cm. The 37 unmarked draws span 1.4–3.5 cm, so there is
  no overlap.
  - ep11: 10 of 10 marked, left behind.
  - ep13: 10 of 10 marked, flung or dropped.
  - ep2: 6 of 10 (s42) and 7 of 10 (s43) marked.
  - ep12 and ep31: 0 of 10 marked.

One cell in full, `mass0s42_glock_public/ep2` (pot + lid, bimodal):

| draw | RPE here | RPE roll policy | RPE total (mocap) | MPPE here | AUC here | flag |
|---|---|---|---|---|---|---|
| r1 | 17.7229 | 17.7229 | 17.12 | 12.733 | 0.177 | FAIL: pot and lid lost from 17 % of the episode |
| r2 | 1.8394 | 1.8394 | 1.80 | 0.912 | 0.961 | ok |
| r3 | 13.2439 | 13.2439 | 12.86 | 7.896 | 0.364 | FAIL: lid lost, ends 17 cm off |
| r4 | 18.0859 | 18.0859 | 17.82 | 12.945 | 0.314 | FAIL |
| r5 | 18.3355 | 18.3355 | 17.95 | 10.067 | 0.429 | FAIL: pot and lid left behind |
| r6 | 2.0441 | 2.0441 | 1.94 | 1.020 | 0.957 | ok |
| r7 | 19.4239 | 19.4239 | 18.82 | 11.943 | 0.147 | FAIL: lid flung 18 cm off path |
| r8 | 2.7332 | 2.7332 | 2.89 | 1.460 | 0.912 | ok (marginal) |
| r9 | 19.3026 | 19.3026 | 18.94 | 10.185 | 0.256 | FAIL |
| r10 | 1.8476 | 1.8476 | 1.85 | 0.831 | 0.967 | ok |

## Method

**Inputs: evaluator output files in the HF store `aebatirel/v2d-store`.** Each was fetched with single-file
`hf_hub_download`; there were no listings.
- `runs/20261026-pack6-5203d42/results/submission/results/episode_0000NN.{parquet,json}` and
  `.../submission/qa/epNN/qa_policy.json` for the 19 episodes other than 33.
- Eval 33: `runs/20261030-c33B-0202139/results/submission/...`.
- Pack 8's eval 1: `runs/20261030-e1conf2-d41382e/results/submission/...`.

**Check that these are the packed rollouts (`audit.py packcheck`) [M].**
- The packed poses of `20261030-track3g-candidate/track3_submission.parquet` (sha256 137c8687…) are identical (max |Δ|
  = 0) to these parquets' achieved columns in 20 / 20 episodes.
- The checkpoint sha256 matches the episode JSON in every episode.
- The same holds for pack 8 (`track3h`, f2bf0441…), with e1conf2's eval 1. Result: 0 mismatches.

**Chain** (roll.py's "policy" path, rdlib).
- Library mesh as host: anchor = surface centroid; 1000 samples, seed 7 + slot.
  - Symmetry for the cups: the distinct principal axis, order 360.
  - Symmetry for the lid: the thinnest axis, order 2.
  - Eval 8 uses `library_v3x`, its tracking library (pack 6 EP_LIB).
- Identity registration, then the kit's `_convert_object_body` and `_align_registered_scene` (frame 0), then the kit's
  `rpe_cm`, `mppe_cm` and `add_auc`.
- The metric files are byte-identical to the PR #215 kit's (RPE 3ec593c0…, MPPE 15d05004…, AUC 243f8009…, verified
  against `pr215/kit/kit.zip`). The roster json is identical too (be92ef6d…).

**Failure rule.** It was fixed before any eval rollout was scored, and its thresholds were checked on public draws only.
- Per object, "off" means a per-frame keypoint error (the kit's MPPE keypoints) above 5 cm.
- A rollout **fails** if any object is off in at least 20 % of its frames.
- The reason given is the first that applies:
  - **left behind:** the reference travels at least 5 cm and the simulated object less than 30 % of that;
  - **flung:** at least 15 cm from every point of the reference path;
  - **orientation:** a median position error below 3 cm in the off frames;
  - **dropped/lost:** otherwise.
- **Marginal:** not failed, but an object is off in at least 5 % of frames or ends more than 5 cm off, or the per-frame
  RPE exceeds 5 cm in at least 5 % of frames.
- Disclosure: v1 also failed a rollout when the per-frame RPE exceeded 5 cm in at least 20 % of frames. On the public
  check that clause flagged 6 successful draws (ep31, ep12; total 2.5–3.5 cm), because long lever arms inflate the
  relation error. It was demoted to "marginal" before the eval run.

## Hypotheses for the ≈ 1.5 cm not explained by rollouts (not tested here)

- **[H-spoon] The wooden spoon carries the gap.** It is eval-only, so no public twin measures its reference or
  registration error. It appears in 7 of the 16 two-object episodes (3, 5, 6, 15, 16, 32, 33).
  - If the gap sits there, each of those 7 episodes would carry ≈ 4 cm extra RPE [E].
  - Falsifier: a GT-free silhouette check of the spoon references. Project the spoon mesh at the reference pose into
    the eval video masks. If the spoon IoU / mask distance is no worse than the public objects', H-spoon weakens.
  - Depth alone cannot do this; the 30 Oct depth audit had AUROC 0.60.
- **[H-gross] One or two eval references are grossly wrong.** Example: an identity swap like public ep23 (14 cm on its
  own), whose twin is eval 25.
  - One such episode adds ≈ 0.7 cm to the board.
  - Falsifier: re-check eval 25's board naming (knob rule) and every eval reference's object-motion plausibility
    against the video.
- **[H-diffuse] Every eval reference is ≈ 2 cm worse in RPE than the public ones.** Falsifier: none GT-free; the
  public P-arm totals do not show it.

## For the retrain (1 Nov 18:00 UTC)

- The only GT-free failure is eval 10, which fails in every draw. Fixing it is worth ≈ 0.7 cm board RPE, ≈ 0.36 cm
  MPPE and ≈ +0.02 AUC [E].
- Secondary targets:
  - eval 32's knocked cup (≈ 0.09 cm);
  - the high-variance evals 14 and 1, whose packed draws are good. They matter only if checkpoints are re-run.
- Most of the RPE gap to the top six (1.10–1.73 cm) is not visible as rollout failure against our reference
  (point 5).

## Commands (CPU, ≈ 7 min in total: check 6 min, eval 1 min)

`S=/tmp/claude-0/-home-user-v2d-track3/6190fffb-f3a1-5d0e-84bd-7370ece99c2f/scratchpad`;
`D=` this folder; `R=docs/analysis/rpe-decomp-20261031`; `K=$S/dl/kit/v2d_submission_kit`.

`$S/fp` is a read-only worktree of `origin/claude/focused-pascal-2nz9s1` @ 137ec62; the pack folders are read from it.

```
python3 -I $D/audit.py fetch $S/evalaudit/dl      # single-file hf_hub_download, 63 files, all ok (first run: scratch fetch.py, same list)
python3 -I $D/audit.py packcheck $S/fp/results/submissions/20261030-track3g-candidate/track3_submission.parquet $S/evalaudit/dl p7
python3 -I $D/audit.py packcheck $S/fp/results/submissions/20261030-track3h-candidate/track3_submission.parquet $S/evalaudit/dl p8
python3 -I $D/audit.py check $R $K $R/roll_rollouts.json $S/evalaudit/check_P2.json \
  $S/roll/orcB:glock_public/ep{11,13,31} $S/roll/mass:mass0s4{2,3}_glock_public/ep{2,12}
python3 -I $D/audit.py eval $R $K $S/evalaudit/dl $S/fp/results/submissions/20261030-track3{g,h}-candidate/summary.txt \
  $D/evalaudit.json $S/evalaudit/check_P2.json
python3 -I $D/audit.py trace $R $K $S/evalaudit/dl/runs/20261026-pack6-5203d42/results/submission/results/episode_000032.parquet blue_cup,wooden_spoon 6
```

- Logs: `$S/evalaudit/{check_P2,eval2,packcheck}.log`, `trace10.txt`, `trace32.txt`.
- Code version: `claude/standings-20261031` @ 727c07b, plus this folder (uncommitted; the coordinating session
  commits).

## Files

| File | Content |
|---|---|
| `audit.py` | The script: modes `check`, `eval`, `trace`, `packcheck`. |
| `evalaudit.json` | Per episode and pack: metrics, per-object features, flag and reason, packed and qa sim_vs_ref, the evaluator's own metrics, the source run, the reference parquet and the checkpoint sha256. Also `public_check` (70 draws). |
