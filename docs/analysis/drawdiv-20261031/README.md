# Where do draws of one checkpoint part ways? (31 Oct 2026, CPU, $0)

Prof. İnceoğlu's question (31 Oct chat): take a successful and a failed rollout of the same episode, compare them frame
by frame, and find where the error starts. He expected different rollouts to fail in different places.

- **Data:** run `20261030-orcB-38234d1` (oracle twins, option B, commit 38234d1). Public ep11 / ep13 / ep31, grasp-lock
  learner, seed 42. 10 official evaluator draws of the chosen checkpoint per arm, rollout parquets kept by
  `glock_public.sh`.
  - Arm P (`glock_public`) uses our perceived reference.
  - Arm O (`oracle_glock_public`) uses the mocap object motion. It is a public-only diagnostic.
- **Method:** `drawdiv.py`. Errors are measured against the reference stored in each rollout parquet (our reference for
  P, the oracle reference for O), so no other ground truth is read. ADD uses 500 points on a 5 cm sphere, as
  `pipeline/qa.py`. Failure onset = an object stays > 3 cm off for ≥ 8 frames, as `physics_solve/failures.py`.
- **Commands** (this cloud container, 4 CPU, ~45 s):
  `bash fetch.sh <dir>`, then
  `python -I drawdiv.py <dir> glock_public 31 oracle_glock_public 31 oracle_glock_public 11 glock_public 11 glock_public 13 oracle_glock_public 13 > drawdiv_orcB.json`.
- Labels: [M] measured here, [I] inference.

## Results [M]

| Twin, arm | sim_vs_ref, 10 draws | Draws first differ (> 10 µm) | All draw pairs split by 2 cm at | Failure onsets (> 3 cm, ≥ 8 frames) |
|---|---|---|---|---|
| ep31 P (sweeper + rack) | 0.758 ± 0.019 | frame 1–10 | median f52 (min 48, max 229) | 5 of 10 draws: f50–57 (rack / sweeper) in 2, f162–233 in 3 |
| ep31 O | 0.883 ± 0.045 | f2–9 | median f53 | sweeper f46–50 in 8 of 10 draws |
| ep11 O (cup stacking) | 0.964 ± 0.029 | f5–11 | median f41 (42 of 45 pairs) | beige cup f63–69 in 3 of 10 draws |
| ep11 P | 0.518 ± 0.003 | f5–11 | no pair splits by 2 cm | every draw: beige cup f27, blue cup f67 |
| ep13 P (cup into rack, hand-over) | 0.556 ± 0.001 | f1–7 | median f37 | every draw: blue cup f15 |
| ep13 O | 0.573 ± 0.000 | f2–11 | 17 of 45 pairs, f39–40 | every draw: blue cup f26–27 |

**What happens at the split [M]:**
- **ep31, sweeper lift-off.** The reference sweeper starts its fast lift at f45–50 (9 → 30 cm/s). Before that, every
  draw already sits 2.3–3.3 cm off the reference sweeper. At the lift, the good draws follow (error falls to 0.5–1.5 cm),
  while the bad draws lose it (4.7 → 8.6 cm by f66 in P r7; 6.2 → 10.1 cm in O r10).
  - In arm P the rack is also knocked at the same moment (3.7–5.6 cm). This fits eval 30's forensics: the sweeper starts
    inside our rack mesh.
- **ep11 O, beige cup carry before nesting.** The bad draw drifts 2–3 cm from f42 and fails at the nest (f63–69).
- **ep11 P and ep13:** the policy fails identically in every draw (sd ≤ 0.003). The ep13 cup goes during a fast
  motion (42 cm/s at f29). This is a plan failure, not variance.

## Reading
1. **Draws differ from the first steps, but only by micrometres** (GPU non-determinism). They stay within 5 mm until
   a contact event (median split frames 5–37), and split by 2 cm **at the same event in nearly every pair** [M].
2. **In these three twins the failures cluster at one or two events per episode,** not at random places. ep31 has a
   main event (lift-off, f48–57) and a second, later one (f162–233, 3 draws) [M]. This is contrary to the expectation;
   with an n of three twins it is not a general rule [I].
3. **Variance appears only where the policy is marginal at an event.** Where it fails deterministically, draws agree
   [M]. At ep31's lift-off the grasp starts 2–3 cm off in every draw, so a margin problem sits there [M+I].
4. **Consequences [I]:**
   - Target those events. Grasp margin at the sweeper lift-off and the rack seat (the mesh session's interlock
     priority) for eval 30; the cup carry and nest for eval 10.
   - Robustness noise should go where it matters: jittered bank states in the solver↔RL loop, rather than global
     domain randomisation.
5. **Limits:**
   - These twins have low spread (sd 0.02–0.05), against eval 30's 0.255 and ep2's ≈ 0.23.
   - The public twin uses the grasp-lock learner; eval 30's packed policy is the standard learner.
   - The high-spread case is tested next on the masses-check run `20261031-mass-2ed46ea` (public ep2 / ep12, 2 seeds ×
     10 draws, rollouts kept; due ≈ 12:30–14:00 UTC), with the same script.
