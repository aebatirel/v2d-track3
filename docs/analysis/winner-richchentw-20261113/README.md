# Track 3 winner's talk (team "richchentw", presenter Yu-Chuan Chen), first 16 slides, 2026-11-13

Source: 16 phone photos of the online V2D tutorial session (CoRL), shared by the owner in chat on 13 Nov. The photos are
not in git (faces of participants). Everything below the "Their pipeline" heading is transcribed from the slides and
the live captions. It is **their claim**, not verified by us. Our numbers are from this repo and labelled [M] measured,
[E] estimate, [H] hypothesis. Slides still to come: the rest of 4 Learn, 5 Select, Results, Lessons, Next steps.

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

## What to read in the remaining slides
- **Select:** what is selected (seeds, checkpoints or rollouts), by which GT-free criterion, and how many draws. This
  is our lucky-draw problem.
- **Results:** per-board scores (CD-O especially), weak episodes (eval 10 cup stacking? spoon?).
- **Compute:** training steps and wall-clock per policy on a laptop, against our 250M steps.
- **Embodiment:** stock wrist kp 25 or a stiffer custom one?
- **Spoon:** how it is tracked under occlusion (10 of 20 eval episodes).
