# Pre-registration: point-track second opinion, public episodes (2 Nov 2026, point-track session)

Written and pushed before any scoring of the variants below. Labels: [M] measured, [D] public vs mocap, [E] estimate,
[H] hypothesis, [I] inference.

## Hypothesis [H]
A model-free check (2-D point tracks on each object's visible surface, lifted with our metric stereo depth, robust rigid
fit per frame) sees object motion that FoundationPose misses. Where FoundationPose stays put while the points move
coherently ("lag": a frozen or lost track), following the points instead brings the track closer to mocap.
Falsifier: mean ΔAUC ≤ 0 over the 20 public episodes, or any repaired episode getting worse by more than 0.01.

## What was looked at before this file (honest record)
- GT-free development on ep0, ep18, ep23 only (point tracks vs FoundationPose, overlays on the video).
- One mocap diagnostic of the **control** on ep23 (not of any variant): the ep23 loss is an identity swap of the two
  boards hidden by the frame-0 scene alignment (docs/work-log.md, 2 Nov point-track entry). A point-track check cannot
  repair identity, so **ep23 is expected not to recover** [I].
- Settings below were set on that GT-free development, not on scores.

## Inputs (inference reads no ground truth)
- Control: perception-tracking's ptrkD "Cr" outputs (store `runs/20261102-ptrkD-95cecd7/results/ptrk/Cr/ep<N>/`,
  tracker code 7fbc321): poses.npz (world_T_cam, cam_T_<obj>), det_f0.npz (object names only), track_guard.json.
- Depth: store `cache/depth/public/ep<N>/depths_fs0.5.npy` (the same cached FoundationStereo depth perc2 used).
- Templates: meshes/library_v3 (perc2's tracking templates, MESH_DIR of the control).
- Video: public ego_cam_c, rectified as in perc2.

## Method (pipeline/ptrack.py at the commit that adds this file)
- Seeds: the template rendered at FoundationPose's frame-0 pose, visible surface only, kept where it agrees with our
  depth (2 cm). (perc2's own frame-0 masks are not used: on ep0 the lid's mask lies on the pot handle [M].)
- Tracker: OpenCV pyramidal Lucas-Kanade (KLT), frame to frame, forward-backward check 1 px; up to 300 points per object
  (good features + grid); re-seed inside the template render at the point-track pose when < 60 % remain; restart from
  FoundationPose's pose after 10 lost frames (seeds only where its render agrees with depth; new segment).
- Fit: RANSAC 3-point Kabsch (1 cm) + trimmed refit; ≥ 12 inliers.
- Detector: window W = 15 frames; e(t) = mean distance over 200 template points between the point-motion prediction
  T_pt(t) T_pt(t−W)⁻¹ P_out(t−W) and FoundationPose P_fp(t); flagged when e > 2 cm for ≥ 5 consecutive frames.
  Type "lag" when the points moved more than FoundationPose over the window by > 1 cm, else "jump".
- Repair: from anchor (onset − W), P_out follows the point motion; hand back when e < 1 cm for 5 frames or when the points
  restart from FoundationPose, with a 10-frame blend; hold the last repaired pose while the fit is invalid.

## Variants
- **PT-lag (primary, the candidate):** `--repair lag` (only frozen / lost FoundationPose tracks are replaced).
- PT-all (report-only): `--repair all` (jump-type flags repaired too).
- Control: Cr poses_world_vo.npz unchanged. Variants change only flagged spans, so unflagged frames are identical (no
  tracker noise term needed).

## Scoring (after inference; mocap read only here)
`pipeline/score_registered.py EP <poses_world_vo.npz> --per_frame ...` with the public scans as candidate meshes (the
default; control and variants scored identically), kit at the 2 Nov download. 20 public episodes
0 2 11 12 13 18 21 22 23 24 26 27 31 39 40 41 42 43 44 45.

## Gate for PT-lag (fixed now)
1. mean ΔAUC ≥ +0.005 over the 20 episodes;
2. no episode ΔAUC < −0.01;
3. mean ΔMPPE ≤ 0 (cm);
4. reported, not gating: ep23 recovery (expected no), number of flagged / repaired spans per episode, frames > 3 cm
   position error (control vs variant).
Pass on 1–3 → handed to perception-tracking and the coordinator with apply instructions. Fail → reported as failed.
Any crash counts as the control for that episode and is reported.
[E] Prior expectation: small effect; on the three development episodes only ep18's sweeper shows flags, all "jump"
type, so PT-lag may change little, and the mean gate is likely to fail.

## Cost
CPU in this container, $0. No GPU. A BootsTAPIR arm would need a rented box and a separate PREREG and go-ahead.
