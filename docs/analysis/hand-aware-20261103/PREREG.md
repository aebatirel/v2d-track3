# PREREG: hand-masked ray correction (HRC) of held phases, public episodes (3 Nov 2026)

Written before any holdout number of this method was computed. Branch `claude/hand-aware-20261103`.
Labels: [M] measured, [D] public vs mocap, [E] estimate, [H] hypothesis, [I] inference.

## Evidence that led here (all on public episodes; mocap read only by scoring and diagnostics)
- Control C (perception-tracking's eval-default track: library_v3 + TRACK_GUARD; ep23 with identity_fix), scored with
  the registered scorer and the 14p public meshes: **70 % of the AUC loss is in mocap-held frames** [D].
- Rigid-in-grasp with our MediaPipe hands as the pose source **fails** (−0.014 to −0.79 per episode on 12 / 18 / 24 /
  27): the hand estimate is noisier than the track [D]. Not pursued further.
- The held-phase excursions lie **along the camera ray** (ep13 cup +2.7 cm, ep18 sweeper +14.6 cm, ep21 pitcher
  −4.3 cm, ep11 cup −3.6 cm, ep24 board −2.2 cm) [D]. An oracle that removes the ray component in held frames would
  add +0.0195 mean AUC (20 episodes; gated at 1.5 cm: +0.0148) [E, oracle].
- A GT-free residual (stereo depth minus the template rendered at the tracked pose, hand pixels and other objects'
  pixels removed) tracks the ray error where **the track has drifted off its own depth** (ep18 sweeper r = 0.95, ep13
  cup r = 0.82), sees nothing where depth agrees with the track (ep11 cup), and has the **wrong sign on the pitcher**
  (ep21 r = −0.83; template shape error) [D]. These four episodes were inspected, so they are development episodes.

## Hypothesis [H]
Shifting the tracked pose along the camera ray to cancel the hand-masked depth residual, only in hand-contact frames
and only where the residual departs from the object's own pre-contact baseline by more than a threshold, recovers
part of the held-phase loss without harming other frames.
**Falsifier:** the holdout gates below fail.

## Method (HRC), a post-processor on perc2's track; inference reads only the track, the stereo depth cache, our
library_v3 templates, our MediaPipe hand fits (pipeline/hands_mp.py --api tasks + pipeline/hand_refine.py),
calibration, and object names / slot order
1. **Residual** r(t) per object (scripts/ray_residual.py): template splatted at 1/4 resolution, eroded silhouette, own
   surface in front, observed depth > 0, outside the hand mask (21 joints + bones as 1.5 cm capsules), |z_obs −
   z_render| < band; median of z_obs − z_render; ≥ 20 valid pixels.
2. **Contact frames (GT-free hold detection):** ≥ 2 fingertips of one hand within CONTACT_CM of the tracked template
   surface, runs bridged over gaps ≤ 12 frames, dilated ±8 frames.
3. **Baseline:** b = median r over the object's frames before its first contact frame (at least 5 frames, else the
   first 10 frames). It absorbs the per-episode template-vs-depth offset.
4. **Correction:** in contact frames where |r − b| > TAU, translate the pose along the camera ray through the object's
   origin by the amount that cancels r − b (converted from depth to ray length by the ray's z-component), re-render and
   repeat up to ITERS times or until |r − b| < 0.3 cm. A frame is corrected only if the final |r − b| < half the
   initial one (consistency check); otherwise the track is kept.
5. **Temporal clean-up:** the correction vector is median-filtered over 5 frames inside each corrected span; spans
   shorter than MIN_SPAN frames are dropped.
6. Free parameters: TAU, CONTACT_CM, MIN_SPAN, band, ITERS, plus per-object eligibility (below). They are chosen on
   DEV only and frozen in an addendum committed before any holdout scoring.

## Split (fixed now)
- **DEV:** 11, 13, 18, 21 (already inspected), plus 0, 41, 43 (pot / lid rest-heavy episodes to check that nothing
  is broken).
- **HOLDOUT:** 2, 12, 22, 23, 24, 26, 27, 31, 39, 40, 42, 44, 45.
  - It covers the coordinator's list: pot 27 and others; boards 23 / 24; cup 12; pitcher 22; sweeper 31; dust pan
    39 / 40.
  - Held phases checked against mocap motion (scripts/held_diag.py, held_diag_C.json): every listed object has a held
    run in its episode.
- ep23 uses the control with identity_fix applied (as in perception-tracking's srpublic / round 3).
- **Per-object eligibility** (e.g. excluding the pitcher because of its template error) may be decided on DEV only.
  If the pitcher is excluded, ep22 still counts in the holdout with the pitcher unchanged.

## Scoring (fixed now)
- `pipeline/score_registered.py` (perception-tracking version) with `--meshes meshes/m14p_public --reg_seeds 10`,
  `perception_seedmean`; kit from pipeline/setup.sh (kit.zip sha256 7e1fdd00…). Per-frame errors: single seed
  `--per_frame`.
- Control: C as above. Noise: Cr (same config, re-run), scored the same way. ep23 Cr also with identity_fix.
- Held frames for the gate: mocap-held frames (held_diag.py: moving > 5 mm or > 3° within ±10 frames, dilated ±8),
  read by scoring only.

## Gates (holdout; all must pass)
1. Held-phase median symmetric ADD (pooled over all holdout held frames of all objects, seed 0) ≥ 20 % lower than the
   control.
2. Whole-episode mean AUC (10-seed) ≥ +0.005 vs the control, and ≥ 2 × the C-vs-Cr noise mean |ΔAUC|.
3. No holdout episode below −0.01.
4. Report (no gate): per-object SP / MP-SR against mocap (scripts/sr_public.py logic, 10 seeds); MPPE / RPE; the
   held-frame mean ADD; frames corrected; frames with > 3 cm error.

Reading: gate 1 is strict for a gated, sparse correction (most held frames are < 1 cm and untouched) [I]. If gates
2–3 pass and gate 1 fails, the result is reported as a FAIL with that detail; no gate is changed after scoring.

## Cost
CPU in the cloud session: $0. No GPU is needed for phase 1 (MediaPipe on CPU ≈ 1 min per episode; depth caches from
the HF store).

## Addendum 1 (coordinator, 3 Nov ~10:36 UTC; committed before any holdout scoring)
Gate 1 is replaced, because a held-phase **median** does not fit a sparse, gated correction. The new gate 1 is:
- holdout held-phase **mean** symmetric ADD (pooled over all holdout held frames of all objects, seed 0) ≥ 10 % lower
  than the control, **or**
- holdout held-phase AUC ≥ +0.01 vs the control. This is the kit AUC (thresholds 1–9 cm) recomputed on held frames
  only, per object and averaged over holdout objects, seed 0.

Gates 2 (whole-episode AUC ≥ +0.005 and ≥ 2 × noise) and 3 (no episode below −0.01) are unchanged. Per-object SR
against mocap is reported. For a later eval phase, the ray-correction sizes (cm) per corrected span are also reported.
