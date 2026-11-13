# Track 3 winner's talk (team "richchentw", presenter Yu-Chuan Chen), first 16 slides, 2026-11-13

Source: 16 phone photos of the online V2D tutorial session (CoRL), shared by the owner in chat on 13 Nov. The photos are
not in git (faces of participants). Everything below the "Their pipeline" heading is transcribed from the slides and
the live captions. It is **their claim**, not verified by us. Our numbers are from this repo and labelled [M] measured,
[E] estimate, [H] hypothesis. Part 2 (11 more slides, the rest of Learn through Next steps) was added the same day; see "Part 2" below.

## Their pipeline (as shown)

Five stages: perceive, reconstruct, reference, learn, select. Captions: "Every mesh and every trajectory we submitted
comes from the evaluation videos, and the whole pipeline runs on one laptop GPU."

1. **Perceive** ("masks, metric depth and a level world")
   - Grounding DINO + SAM 2: object masks in every frame.
   - FoundationStereo: metric depth from the monochrome stereo pair.
   - SIFT + PnP: head pose against a metric key-frame map.
   - Table plane defines a level, gravity-aligned world.
2. **Reconstruct** ("every object rebuilt from the evaluation videos")
   - Parametric shapes sized from silhouettes, stereo points and markers (the mocap marker balls are modelled on the
     spoon, boards, lid, pitcher, dust pan).
   - nvdiffrast fitting: differentiable rendering against silhouettes and stereo points (shown: episode 1, white pot and
     pot lid).
   - Water pitcher: RecGen generative reconstruction from six frames of episode 20 with their stereo depth.
   - Every submitted mesh ≤ 4,096 faces. Face counts shown: pitcher 4,096, lid 3,904, rack 3,931, dust pan 3,892,
     blue cup 3,312, beige cup 3,312, white pot 2,796, sweeper 2,672, spoon 1,897, board 1 1,562, board 2 1,188.
3. **Reference** ("object poses in every frame, physically consistent")
   - Silhouette + depth tracker follows each object through the clip.
   - FoundationPose refines each object's pose in every frame.
   - Motion states per object: in the hand → tracked pose; at rest → level on its support.
   - Release timing: "where an early release would drop an object, the robot hand holds a little longer"
     (human vs robot bars; "hold extended · no drop").
4. **Learn** ("one dexterous-hand policy per episode")
   - MediaPipe Hands; wrist lifted to 3-D with stereo depth; grasps retargeted to the Sharpa hand.
   - Reference → policy (soft actor-critic) → Newton (GPU-parallel simulation) → reward.
   - Default key-point reward: 1° ≈ 1.75 cm ("rotation weighed far above the official metrics").
   - Their centroid reward: key-points on a 0.1 m lever arm around the centroid, 1° ≈ 0.17 cm;
     `r = Σ exp(-‖p - p_ref‖ / σ) - b`, σ = 3 cm, b = reward centering.

RecGen = "Reconstruction by Generation" (TRI, arXiv 2604.27106, Apr 2026). It takes RGB + **depth** + mask +
intrinsics, from one or more views, and outputs a mesh **and its 6-DoF pose**. The inference code is public
(TRI-ML/recgen); the training code is not.

## Side by side with our pipeline

| Stage | Winner | Us (pack 7) | Difference |
|---|---|---|---|
| Masks | GDINO + SAM 2, every frame | SAM2 proposals × DINOv2 vs mesh renders at frame 0, GDINO term for the spoon, then FoundationPose | They have a silhouette in every frame. Our wrist/watch mis-tracks (evals 30, 33, 14) would show as mask disagreement. |
| Depth | FoundationStereo | same | none |
| Head pose | SIFT + PnP against a metric key-frame map | visual odometry | Theirs has bounded drift. "Camera drift via room map" was on our fix list, never built. |
| World frame | table plane | table plane | none |
| Meshes | parametric + nvdiffrast fit to **eval** silhouettes and depth; RecGen pitcher; markers modelled | library_v3 from public episodes (TSDF along scan-seeded tracks); kit-of-parts pot/lid/rack built but not shipped | Theirs are fitted per eval episode by differentiable rendering. Our CD-O is 0.402 cm, 11th; leaders 0.11 [M]. |
| Pitcher | RecGen, RGB-D, 6 views | our mesh; public twin 0.57 vs 0.95 with the scan [M] | Our generator probe failed on *placement* (Sim(3) fit of a depth-free mesh, ADD 10–29 mm [M]). RecGen takes depth and returns pose. |
| Reference | tracker + FoundationPose; at rest level on support; release delayed when it would drop | FoundationPose + track guard; grasp lock; refine-stage snap/tilt rejected (−0.0077 / −0.0013) [M] | They make the reference *physically consistent* (support-aware rest, release timing). |
| Hands | MediaPipe + stereo wrist + Sharpa retarget | same (+ contact-anchored retargeting) | none visible |
| Learner | SAC in Newton, one policy per episode | FlashSAC in Newton, one per episode; two recipes | same family |
| Object reward | 0.1 m centroid keypoints, Laplacian σ = 3 cm, reward centering | FDR 128-point surface match, mean of top-3 point distances, exp(−e / 0.1 m), no centering | Same diagnosis, different fix (below). |
| Compute | "one laptop GPU" | 246 GPU-h on RTX PRO 6000, $376 [M] | Unknown how; look for steps and wall-clock in the next slides. |

## The reward point in detail

We found the same default flaw on 22 Oct (`ops/box/patch_flashchord.py`: FlashCHORD's object keypoints sit on unit
vectors 1 m out with exp(−error / 0.1), "a 3° wobble costs as much as 5 cm"). Our fixes:
- `FC_OBJECT_KEYPOINT_SCALE=0.15` on ep24/ep18 showed no effect (0.313 vs 0.307; work log 22 Oct). This test was
  confounded: both episodes were then broken by reference faults (all variants 0.306–0.318).
- We adopted FDR's point match instead. It also removes the 1 m lever, but it keeps σ = 0.1 m.

Our kernel is flat across the metric's range, theirs is not. ADD-AUC sweeps 1–9 cm.

| Error | ours exp(−e/0.10) | theirs exp(−e/0.03) |
|---|---|---|
| 1 cm | 0.90 | 0.72 |
| 3 cm | 0.74 | 0.37 |
| 9 cm | 0.41 | 0.05 |

Our reward barely separates a 1 cm track from a 3 cm one. Our top-3 maximum also keeps rotation heavy on long objects:
the spoon tip is about 12 cm out.

## Lessons for us, ranked (each a hypothesis until tested)

1. **H-W1, physically consistent reference: support-aware rest and delayed release.**
   - Target failures [M]:
     - evals 15/16: spoon flips on release;
     - eval 14: cup pushed into the rack;
     - eval 28: pot set into the rack;
     - eval 30: sweeper starts inside the rack;
     - eval 1: lid inside the pot's hulls.
   - Our snap was scored against mocap and hurt, so their gain is probably in simulation (no drops or flings), not in
     reference accuracy.
   - Falsifier: on public twins with release events, the policy drop/flip rate does not fall, or AUC vs mocap gains
     < +0.01 over 2 seeds.
   - Cost: CPU reference change plus retrains.
2. **H-W2, sharper object kernel (σ 3 cm) plus reward centering.**
   - Falsifier: A/B on ep12/18/22/27 and one spoon twin, 2 seeds. Reject if the mean gain is < +0.01 or any
     episode drops > 0.03.
   - Cost: about 10 policies ≈ $25–33 [E].
   - σ is a config value (`objective.object_keypoints.var`). Reward centering needs a FlashSAC change.
3. **H-W3, meshes fitted by nvdiffrast to eval silhouettes and depth.**
   - We already have nvdiffrast code (`pipeline/perc.py`, `spoon/fit_spoon.py`) and the kit-of-parts DSL.
   - Attacks CD-O (11th) and registration loss.
   - Falsifier: on public episodes, fitted CD-O is not below library_v3 0.477 cm mean [M].
4. **H-W4, RecGen for the pitcher (and maybe the cups).**
   - Falsifier: on ep21/ep22 against the scan, CD-O not below our lathe mesh, or ADD after placement > 6 mm.
   - Small GPU job.
5. **Key-frame-map head pose and per-frame masks.** Robustness; they would also give automatic, GT-free triggers
   in place of our hand-applied per-episode fixes.


## Part 2: Select, Results, Lessons, Next steps (11 slides)

### What they showed
- **Learn:** the human and the policy side by side from the same head camera (eval 1-type pot + lid scene).
- **Select:** "the best of up to 320 official-evaluator rollouts".
  - The simulator is not deterministic. Their white-pot distance to their own reference over 90 rollouts stays in a
    0–3.5 mm band (10–90 %).
  - Each policy is run up to 320 times with the official evaluator. Every rollout is scored with the official metric
    code against **their own reference**, and the best one is submitted.
  - Scatter of 320 rollouts: MPPE 0.108–0.181 cm, RPE 0.236–0.347 cm, all against their own reference.
- **Results, hidden test set (20 eval episodes, 11 object types, 14 combinations, 20 policies):**

  | Board | Winner | Best other team | Us, pack 7 (30 Oct) [M] |
  |---|---|---|---|
  | ADD-AUC | **0.984** (1st) | 0.953 | 0.8146 |
  | RPE | **0.630 cm** (1st) | 0.925 | 3.932 |
  | MPPE | **0.603 cm** (1st) | 0.928 | 2.921 |
  | SP-SR | 1.00 (tied 1st) | 1.00 | 0.85 |
  | MP-SR | 1.00 (tied 1st) | 1.00 | 0.65 |
  | CD-O | 0.217 cm (2nd) | 0.207 | 0.402 |

  Their episode tiles use our numbering (ep8 pot + cup, ep10 two cups, ep14 cup + rack, ep15 rack + spoon). The tiles
  show mostly the real video beside a thin strip of simulation, so whether ep10's cups nest in their rollout cannot be
  seen. The caption says every episode is "solved by its own policy".
- **Score history on the hidden set** (AUC; RPE / MPPE cm):

  | Step | AUC | RPE | MPPE |
  |---|---|---|---|
  | First submission | 0.902 | 1.519 | 1.465 |
  | + FoundationPose references | 0.940 | 1.150 | 1.151 |
  | + metric-aligned reward | 0.963 | 0.802 | 0.900 |
  | + levelled world, rest refits | 0.968 | 0.720 | 0.821 |
  | + registration calibration | 0.980 | 0.715 | 0.690 |
  | Final | 0.984 | 0.630 | 0.603 |

  Their **first** upload (0.902) was already above our best (0.8146). It had no FoundationPose: their silhouette +
  depth tracker alone. The slides do not say what else it contained.
- **Lessons (theirs):**
  1. *The reference dominates.* Policy vs its own reference MPPE 0.10 cm; leaderboard vs Vicon 0.60 cm. "Most of the
     error is in the video estimate, not in the policy."
  2. *The reward must match the metric.* Centroid reward "with polishing": public-episode MPPE 0.851 → 0.666 cm.
  3. *Mesh shape and pose are coupled.* A mesh tuned only for shape dropped ADD-AUC 0.984 → 0.963 and MPPE
     0.636 → 0.793 cm. The scorer's registration flipped the lid by 159°. "Re-posing fixed it."
  4. *One anchor amplifies small errors.* The scorer aligns the scene on one anchor object. 1° at 30 cm ≈ 5 mm; a
     3.7° anchor tilt took MP-SR 1.00 → 0.95, and levelling restored 1.00. "Make rest phases physically consistent
     first."
- **Next steps (theirs):** estimate object pose, hand pose and contact jointly, with the simulator in the loop. For
  the benchmark: align over all static objects instead of one anchor; average several rollouts "to remove simulator
  noise from the ranking".
- Not shown anywhere: training steps, wall-clock per policy, wrist stiffness, how the spoon is tracked.

### Our error, split the same way
> **Correction (13 Nov, later):** this section uses our 30 Oct state (pack 7), because this branch held only the
> repository as of 30 Oct.
> - Our final counted file was pack 14p: AUC 0.886, SP-SR 0.90, MP-SR 0.80, RPE 2.21, MPPE 1.80, CD-O 0.239. That is
>   9th by rank sum (Kaggle API, 13 Nov).
> - By 3 Nov our packed rollouts all passed SP/MP-SR against our own references (branch
>   `claude/perfect-following-20261101`), so the final loss is mainly reference vs truth.
> - The plan that follows from this: `docs/research/work/plan-20261113/PLAN.md`.

- **Policy vs our own reference [M]:**
  - packed sim_vs_ref 0.917; mean of 10 fresh draws 0.876 (H5).
  - That is ≈ 0.08–0.12 AUC lost to the policy alone. Theirs is ≈ 0 (MPPE 0.10 cm).
  - Our draws spread widely: sd up to 0.255 (evals 1, 14, 30). Their 320 draws all sit in a band ~0.07 cm wide.
- **Our reference vs truth:**
  - ≈ 0.10 AUC [E] on eval.
  - On 20 public episodes, the 20 Oct perception (public scans as templates, `results/registered/perc2_refsweep_*`)
    had a **median MPPE of 0.68 cm** [M], close to their 0.60. But the mean was 3.92 cm because of failures (ep26 53.8,
    ep0 9.3, ep24 2.2).
  - So on a typical episode our tracking was at their level. Tail failures, eval meshes and the policy are where we
    lost.

### What this changes in our hypotheses
- **H-W1 (physically consistent reference) moves up.** Their policies track to about 1 mm. Ours miss by centimetres,
  exactly where our references are infeasible: cup into rack (14), sweeper inside rack (30), lid inside pot hulls (1),
  release flips (15, 16), the eval-10 stack.
- **New H-W5: best-of-N official rollouts against our own reference.**
  - Our rule (d) since 29 Oct was "never a best draw". We feared organiser re-runs.
  - The winner submitted the best of up to 320 and won. Their own "next steps" asks the benchmark to average
    rollouts. That says single submitted trajectories are what was scored.
  - With our spread, best-of-N would have recovered much of the 0.04 gap between our packed and mean draws, and more
    on evals 1, 14 and 30. That is an estimate. It cannot fix systematic failures (eval 10 at 0.45 ± 0.007).
  - Spending best-of-N against our own reference is GT-free and within the rules as they evidently applied.
- **New H-W6: level the anchor object's frame-0 pose, and judge it on SP-SR/MP-SR, not only on AUC.**
  - Our S3 "tilt-to-plane anchor" was rejected on AUC (−0.0013, 30 Oct).
  - Its MP-SR effect was never measured: `docs/research/work/refine/results/` stores AUC only.
  - MP-SR (0.65) was our weakest pose board, and the final rank sums six board ranks.
  - Falsifier: on public episodes, S3 does not raise MP-SR or SP-SR.
- **New H-W7: calibrate how our mesh registers to the scan before shipping a mesh change.**
  - They gained +0.012 from it. Our pitcher swap lost 0.0045 the same way.
  - We already have `pipeline/score_registered.py`, which emulates the scorer's ICP.
  - Open rule question for the owner: they appear to calibrate against the scan of the same physical object.
- **H-W2 (reward) confirmed as their second-largest step:** +0.023 AUC on the hidden set.
