# Pre-registration: Purple's model-to-cloud registration for cups on our public data (13 Nov 2026)

Owner (13 Nov): "can you test their system or try to replicate it, you can also look at the other people in github who
scored higher than us".

## What is replicable
- The winner (richchentw), DDD, Zihao Guo and egocube published no code (GitHub and HF searched 13 Nov).
- SRL's repository (kyounginbaik/SRL_V2D) is no longer reachable.
- Purple / Barry Allen (AUC 0.933, cringeyburger/purple-v2d-track3 @ 8f823be, Apache-2.0) published a source snapshot.
  - Their FoundationPose driver, SAM 3 masks and cuVSLAM tracks are absent, so the system cannot run end to end.
  - Their spoon registration (`reconstruction/tools/spoon_register.py`) is complete and object-agnostic:
    - masked stereo cloud with hand pixels removed;
    - starts = previous pose (if ≤ 3 frames old) + 8 PCA starts;
    - trimmed (85 %) point-to-plane ICP;
    - score = trimmed mean distance (mm) + 20 × (1 − silhouette IoU outside the hand);
    - best start refined.
  - Per our 9 Nov read (`docs/research/competitors-2026-11-09.md` §6.5), they used FoundationPose-free geometric fits
    for the spoon and the cups, which carry half of the eval object weight.

## Hypothesis (written 9 Nov, §6.5, never tested)
Cup poses from clean masked stereo points by model-to-cloud registration beat our FoundationPose cup tracks.

## Port (GT-free; `purple_track.py` in this folder)
- **Algorithm:** Purple's `spoon_register.py`, unchanged in its steps and constants.
- **Our inputs instead of theirs:**
  - control C tracks and cameras (ptrkA/B, as stage 1b);
  - our depth cache;
  - our SAM2 video masks (400 × 250, single camera);
  - our scoring meshes as models (library_v3 + pack 9a+ overrides).
- **Hand mask:** the convex hull of each detected hand's 21 MediaPipe joints (`refs/perc2/ep<N>/hands.npz`, rectified
  left camera frame 0), projected per frame and dilated 31 px at 1600 × 1000.
- **Masks:** eroded 1 px at mask resolution.
- **Cloud gate:** mask ≥ 146 px (Purple's 1500 px at 1280 × 800, rescaled) and ≥ 300 points.
- **Frames:** frames without a cloud keep our tracker's pose. All other objects keep C.

## Scoring (after inference)
- `score_registered.py` (perception-tracking version), meshes_9aplus, kit 7e1fdd00, as stage 1b.
- Cups: blue_cup and beige_cup. Episodes 11, 12, 21, 22 (the 9 Nov rule); 13 also reported.

## Rule (9 Nov §6.5, unchanged)
- Pass: mean per-object AUC of the cup objects over episodes 11, 12, 21 and 22 improves by ≥ +0.02 vs C, and no
  episode's AUC is worse by more than 0.01.
- Falsified: mean cup ΔAUC ≤ 0.
- Otherwise inconclusive.
