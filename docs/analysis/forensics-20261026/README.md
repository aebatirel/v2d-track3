# Forensics of the third submission (Track 3 AUC 0.789, 4th) — 26 Oct 2026

Owner's request (26 Oct): "get the videos of our current episodes and also do forensics on what went wrong and what
can be improved"; "something more ambitious". No ground truth was read for any eval episode; public-episode numbers
come from earlier mocap scoring recorded in the repo (sources cited).

Inputs:
- the 20 official rollouts of pack 3 (`20261025-pack3-3758189`, the uploaded file);
- each episode's reference and checkpoint (sha256-checked);
- FlashCHORD on CPU for the physics tests.

## 1. Where the score goes

| Quantity | Value | Kind |
|---|---|---|
| Leaderboard AUC | 0.789 (4th; 3rd is 0.865, 1st 0.932) | measured (Kaggle) |
| Same rollouts against OUR reference (sim_vs_ref) | 0.883 | measured |
| Public twins: true AUC ≈ 0.979 × sim_vs_ref when the reference is sound (57 policy means, 10 episodes) | → 0.864 expected | derived |
| Policy loss (sim vs our reference) | 0.117 | measured |
| Eval-specific reference / anchor / mesh loss beyond the public norm | ≈ 0.075 | derived (0.864 − 0.789) |

So two levers of similar size: the policy not following our reference, and our reference (perception, frame-0 anchor,
meshes) not matching the truth on eval episodes. sim_vs_ref cannot see the second.

## 2. Policy loss by episode (sim vs our reference; `rollout_errors.png`)

Evals 10, 33 and 32 hold 54 % of the policy loss; 10 and 33 alone 46 %.

(per-episode table: filled in below)

## 3. Reference vs the simulator's collision geometry (`hull_census/`)

(filled in below)

## 4. Hidden losses (not visible in sim_vs_ref)

(filled in below)

## 5. What can be improved, ranked

(filled in below)
