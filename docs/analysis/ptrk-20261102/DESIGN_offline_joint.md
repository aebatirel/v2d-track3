# Design note: offline whole-video object pose estimation (proposal, not built)

Requested by keen-heisenberg for the owner (2 Nov 2026, 14:10 UTC). Labels: [M] measured, [D] measured on public data
against mocap, [E] estimate, [H] hypothesis, [I] inference, [L] literature.

## The idea
Today each object's pose is tracked frame to frame: FoundationPose refines frame t from the pose at frame t−1, using the
stereo depth (cams b/c) and the grey left image. The proposal is to estimate each object's whole trajectory at once,
offline:
- **Unknowns:** for each object, one pose per rest segment plus a smooth SE(3) trajectory over each moving segment.
- **Evidence at every frame:** render-and-compare against the object masks and the stereo depth, plus the third
  camera (ego_cam_a, colour, own calibration, one-frame offset to the stereo pair).
- **Physics and contact terms:** rest on the table or a support, no interpenetration, and the held object staying
  near the measured hand contacts.
- **Optimisation:** the tracker's output is the initial value, refined jointly (Gauss–Newton or Adam through a
  differentiable renderer).

How the leaders reach RPE ≈ 0.7 cm is not known to us. This is an inference from the size of their gap, not knowledge
of their method [I].

## Evidence from today and earlier

**For:**
1. **Tracker chaos [D].** On ep18 both control runs lose part of the sweeper (AUC 0.898, the two runs identical),
   while every perturbation recovers it (+0.05–0.06).
   - Earlier: the 25 Oct sweep lost ep18 with t4 / t8 and ep12's cup with t8 (−0.25).
   - A frame-to-frame tracker carries its own mistakes forward. A joint estimate with per-frame image evidence has no
     such state.
2. **The public loss is bias, not noise [D].**
   - Kalman, RTS and other smoothers fail (−0.0001), because they only re-weight the tracker's own poses.
   - A joint image-evidence fit can move the mean pose, for example over a rest segment of 50–200 frames seen from a
     moving head.
   - The frame-0 scene tilt alone is worth up to +0.016 (exact-tilt oracle, physperc).
   - Constant translation offsets are worth +0.030, mostly along the camera ray (oracle, physperc D4).
3. **More viewpoints per rest segment [I].** The head moves, so a resting object is seen from many directions. That
   constrains the along-ray component which a single view leaves loose.

**Against:**
1. **Mesh error bounds it [D].** The C0 pot base sits 7 mm low; the pitcher lacks half its base; our CD-O is 0.33 cm
   against the leaders' 0.21.
   - Render-and-compare against a wrong shape converges to a biased pose. Today's pitcher-template test addresses only
     a part of this.
2. **Earlier multi-frame and multi-view attempts failed [D].**
   - The refine-stage multi-frame / stable-pose fit gave −0.0013, but it used our poses, not image evidence.
   - Marker-ball stereo gave −0.083, and adding ego_cam_a as a third view gave no improvement.
   - Depth-ICP offset fitting recovered none of the offset.
   - Depth-based alignment against our meshes has so far not found the bias.
3. **Today's mask-based guidance hurt where it constrained depth (−0.0077) [D].** Masks of held objects are cut by the
   hand. Mask-driven terms must handle occlusion explicitly, or they pull the pose.
4. **Unknown leader method [I].** Their accuracy may come mostly from better meshes, or from not failing episodes,
   rather than from joint estimation.

## Minimal public test (pre-register before running)
**Stage 1: rest segments only.** This is the cheapest part and where most of the bias lives.
- Segments come from our own tracks (rest = speed below the refine stage's thresholds, ≥ 10 frames, no measured hand
  within 3 cm). That is GT-free.
- For each object and rest segment, optimise ONE pose against all frames of the segment:
  - silhouette IoU against the SAM2 video mask, with only the visible part counted (hand pixels excluded via the
    MediaPipe hand mask);
  - robust (Huber) depth residual on the object's visible pixels from the stereo depth;
  - a reprojection term in ego_cam_a (its calibration and frame offset as hands_mp.py uses them).
- Start from the tracker's segment median; on GPU with nvdiffrast, a few hundred iterations.
- **Score:** ΔAUC / MPPE / RPE on the 20 public episodes, with only rest frames changed. Moving frames keep the
  tracker poses, with a short ramp at segment ends.
- **Gate:**
  - ΔAUC ≥ +0.005;
  - no episode below −0.01;
  - ADD on rest frames lower on at least 14 of 20 episodes.
- **Falsifier:** rest-frame ADD not lower than the tracker's.
- **Diagnostic oracle first ($0, CPU):** replace only the rest-segment poses by mocap (diagnostic) to bound Stage 1's
  value. Build nothing if that bound is below +0.01.

**Stage 2, only if Stage 1 passes:** moving segments.
- An SE(3) spline per segment (knots every 3–5 frames), the same image terms, and a hand-contact term for held phases
  (fingertips near the surface, no penetration).
- Same gate, applied to all frames.

## Oracle bound, measured (2 Nov 14:25 UTC; `scripts/rest_oracle.py`, `results/rest_oracle_C.json`) [D]
- **Set-up:** on today's control tracks (eval defaults), every frame where mocap is at rest gets zero error; moving
  frames keep the track's error. Rest is mocap speed < 0.3 cm / frame, dilated 5 frames.
- **Result: +0.032 mean AUC over 19 public episodes** (ep23 excluded), above the +0.01 build bar.
  - ep24 +0.118, ep31 +0.112, ep11 +0.088, ep21 +0.083, ep18 +0.069, ep22 +0.057;
  - ep12 / 13 +0.02;
  - the pot-only episodes ≤ +0.003.
- **Caveats:**
  - This does not re-run the scorer's frame-0 alignment. Fixing frame 0 (always a rest frame) also fixes the scene
    tilt for every frame, so the true bound is likely larger [I].
  - A real Stage 1 recovers only part of it, limited by the meshes (pitcher, boards, rack).
- **Reading [I]:** most of the public perception loss sits in rest phases of the boards, the rack, the pitcher and
  the cups. That is where whole-segment, multi-view image evidence can act and frame-to-frame tracking cannot.

## Cost [E]
- **Oracle bound:** CPU, $0, about 1 h.
- **Stage 1 build:** about one working session of code (renderer, losses, segment logic, cam-a projection), developed on
  CPU with a GPU smoke test.
- **Stage 1 run:** about 2–5 GPU-minutes per episode, so about 1–2 h on one PRO 6000 for 20 episodes, about $2–3.
- **Stage 2:** about 3× Stage 1's run cost, plus a larger build.
- **Eval application:** the same GPU cost again for the 20 eval episodes, plus rebuilt references and retrains for the
  episodes it changes. That retraining is the expensive part (about $3–6 per episode on perfect-following's numbers).

## Risks
- **Bounded by mesh error.** Gains may stop at about the oracle's +0.01–0.02 unless the meshes improve too.
- **Occlusion handling.** Today's result shows mask terms hurt held objects without an explicit hand model.
- **Eval variance.** Tracker-level changes flip whole object tracks on single episodes (ep18, ep0 today), so eval
  references need per-episode checks (qa_physics, guard events) before swapping.
- **Camera a.** Its one-frame offset and rolling-shutter / colour differences must be modelled. A mistake there biases
  every pose.
- **Time and cost.** Every reference it changes needs a retrain to reach the board. Its board value is roughly 0.74 ×
  its public reference gain [E, measured transfer for the half-frame advance].
