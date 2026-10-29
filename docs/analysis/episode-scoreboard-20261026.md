# Per-episode scoreboard, 26 Oct 2026 (for the owner)

**What the numbers are:**
- Every number is OUR sim_vs_ref: the official evaluator's rollout against our own reference, 0 to 1. Kaggle reports
  only the totals, never per-episode scores.
- Ground-truth errors in the reference itself (the "hidden loss", about 0.075 of the leaderboard) cannot be seen here.

**Sources:**
- packs 1–3: `results/submissions/2026102*/summary.txt`;
- 5-evaluation means: `docs/work-log.md`;
- causes: `docs/analysis/forensics-20261026/README.md`.

**Leaderboard (Track 3 AUC):**

| Pack | AUC | Rank |
|---|---|---|
| Pack 1 (24 Oct) | 0.575 | 9th |
| Pack 2 (25 Oct) | 0.583 | 9th |
| Pack 3 (25 Oct, on the board now) | 0.789 | 4th |
| Pack 4 | running | |

Our own means: 0.710 → 0.722 → 0.883.

## Table

- \* Pack 3 packed pack 1's rollout here by mistake (the cp -n bug, fixed). Pack 4 restores pack 2's rule-chosen
  seed-43 rollout.
- Pack-4 values for 10 / 25 / 33 are the new policies' 5-evaluation means (expected value). The packed number will be
  one fresh rollout.

| Eval | Objects | Pack 1 | Pack 2 | Pack 3 | Pack 4 | What got it there | What still goes wrong |
|---|---|---|---|---|---|---|---|
| 1 | pot, lid | 0.21 | 0.21 | **0.92** | keep | standard learner (pack 3) | pot spikes 9 cm in the carry; the lid sits inside the pot's collision hulls |
| 3 | pot, spoon | 0.87 | 0.94 | 0.87\* | 0.94 | grasp lock; seed 43 chosen by 5-eval mean | pot 10 cm off in two carries (grip slip); spoon hidden in the pot |
| 5 | pot, spoon | 0.97 | 0.96 | 0.97\* | 0.96 | grasp lock; seed 43 | spoon pose (hidden loss) |
| 6 | pot, spoon | 0.97 | 0.97 | 0.97 | keep | grasp lock | spoon pose (hidden loss) |
| 8 | beige cup, pot | 0.82 | 0.82 | **0.98** | keep | rebuilt reference (track guard), v5 beige-cup mesh, grasp lock | little |
| 10 | blue cup, beige cup | 0.34 | 0.34 | 0.34 | ≈ 0.45 | pack 4: hybrid cup collision copy (the beige cup stands) + standard learner | **largest loss:** the cup stacking is not learned; the policy barely beats leaving the cups at rest |
| 14 | blue cup, rack | 0.56 | 0.56 | **0.91** | keep | track guard, grasp lock | lucky draw (5-eval mean 0.66); our reference pushes the cup INTO our rack mesh |
| 15 | rack, spoon | 0.96 | 0.95 | 0.96\* | 0.95 | grasp lock; seed 43 | spoon rotates 46° on release |
| 16 | rack, spoon | 0.85 | 0.91 | 0.85\* | 0.91 | grasp lock; seed 43 | spoon flips when released into the holder |
| 19 | sweeper, dust pan | 0.63 | 0.68 | **0.93** | keep | seed 43 (pack 2), standard learner (pack 3) | 2–4 cm off during the sweep |
| 20 | blue cup, pitcher | 0.34 | 0.34 | **0.89** | keep | track guard, arc foot (our pitcher mesh lacks half its base), grasp lock | pitcher mesh (hidden: twin 0.57 with our mesh vs 0.95 with the scan) |
| 25 | two boards | 0.23 | 0.23 | **0.84** | ≈ 0.79 | identity fix (boards were swapped), standard learner; pack 4: slot carve | pack 3 drew lucky (mean 0.71); board 2 twists out after insertion (the carve fixes it in sim) |
| 28 | rack, pot | 0.75 | 0.75 | **0.93** | keep | standard learner | pot 6 cm spike; pot set into the rack mesh |
| 30 | sweeper, rack | 0.47 | 0.55 | **0.92** | keep | detection fix (the sweeper starts in the rack) (pack 2), standard learner (pack 3) | sweeper 2 cm / 11° off |
| 32 | blue cup, spoon | 0.84 | 0.84 | 0.79 | keep | rebuilt reference (track guard), frozen grasp lock | cup tips during the grasp (17 cm spike); spoon anchor roll (hidden) |
| 33 | blue cup, spoon | 0.42 | 0.42 | 0.61 | ≈ 0.79 | track guard, frozen grasp lock; pack 4: seed 43 | two-handed carry for 270 frames (both 4–10 cm off); in reality the spoon scoops inside the cup |
| 35 | spoon | 0.98 | 0.98 | 0.98 | keep | grasp lock | spoon anchor roll (hidden: 0.03–0.15 per episode, estimate) |
| 36 | spoon | 0.99 | 0.99 | 0.99 | keep | grasp lock | same |
| 37 | spoon | 1.00 | 1.00 | 1.00 | keep | grasp lock | same |
| 38 | dust pan | 1.00 | 1.00 | 1.00 | keep | grasp lock | — |

Eval 32's lower pack-3 number is against a rebuilt (better) reference, so it is not comparable with packs 1–2.

## Where the remaining score is lost (estimates, from the forensics)

**1. Our reference vs the truth: ≈ 0.075 of the leaderboard, invisible to our score.**
- Spoon pose in the 10 spoon episodes ≈ 0.063 (implied spoon accuracy ≈ 0.81).
- Pitcher mesh (eval 20) and boards (eval 25): the rest.
- With today's policies and a perfect reference: ≈ 0.865 (3rd place).

**2. Policies not following our reference: ≈ 0.115 of the leaderboard.**
- Evals 10, 33 and 32 hold more than half of it.
- Then 25, 16, 3 and 14.

**3. Luck of the single packed rollout.**
- Evals 14, 25 and 33 swing by 0.2–0.6 between rollouts of the same policy.
