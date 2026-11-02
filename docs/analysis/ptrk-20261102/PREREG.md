# Pre-registration: mask-guided tracking, public episodes (2 Nov 2026, tracking-perception session)

Written and pushed before any run of the variants below. Labels: [M] measured, [D] public vs mocap, [E] estimate,
[H] hypothesis, [L] literature.

## Hypothesis [H]
Our FoundationPose tracker loses the object when it moves fast or the hand covers it: the refiner's crop is centred on
the last pose and fits whatever depth lies in it (hand, background). Evidence: the drift-then-snap on evals 14 / 32 / 33
[M, perfect-following]; chaotic object losses in the 25 Oct iteration sweep (ep18 sweeper −0.25..−0.29, ep12 cup −0.25)
[D]; the slow drift of held objects (ep18 sweeper 3.4 cm, ep11 / 13 blue cup 1.3–1.6 cm) [D, all20]. Literature
[L]: FoundationPose++ / RRTrack (2-D video-segmentation track as a translation prior and gate), ObjectForesight
(re-register when the silhouette disagrees), YOTO / EgoGrasp (FoundationPose latches onto the hand).
A propagated 2-D object mask (SAM2 video predictor, started from perc2's own frame-0 detection) used to (a) keep only
object depth, (b) re-centre the pose before tracking when the mask leaves its silhouette, (c) re-register when the
silhouette still disagrees, makes the public tracks closer to mocap.

## Variants (ops/jobs/perc_vos.sh, pipeline/perc2.py + pipeline/vos_guide.py; same box, same code, same cached depth)
All: library_v3 templates, TRACK_GUARD on, today's detection, REG 5 / TRACK 2 (today's eval defaults).
- **C**: control (TRACK_VOS off).
- **C2**: control repeated (run-to-run noise of the tracker).
- **MG**: TRACK_VOS=1, VOS_DEPTH=1, VOS_PRIOR=1, VOS_RECOVER=1 (defaults VOS_COV 0.6, VOS_REC 0.5, VOS_EVERY 5,
  VOS_DIL 12, VOS_MINPX 150). **The candidate.**
- MD: VOS_DEPTH only; MR: VOS_PRIOR + VOS_RECOVER only (ablations, report-only).
No setting is tuned after seeing scores. If MG crashes on an episode, that episode counts as the control's track for the
gate (fallback) and the crash is reported.

## Scoring (after inference; mocap read only here)
`pipeline/score_registered.py` with the pack 9a+ meshes (md5 = posefix inputs.json), public scans, kit metric code,
per frame; 20 public episodes 0 2 11 12 13 18 21 22 23 24 26 27 31 39 40 41 42 43 44 45.

## Gate for MG (fixed now)
Against C on the same box:
1. mean ΔAUC ≥ +0.005 over the 20 episodes, and ≥ 2 × |mean ΔAUC(C2 − C)| (beats tracker noise);
2. no episode ΔAUC < −0.02;
3. mean ΔMPPE ≤ 0 and mean ΔRPE ≤ 0 (cm);
4. drift events not more frequent: frames with object position error > 3 cm (diagnostic, summed over objects and
   episodes) not higher than C's.
Pass on all four → handed to perfect-following with apply instructions for eval references. Fail on any → reported as
failed, not adopted. Falsifier of the hypothesis: MG's ΔAUC ≤ 0 or more > 3 cm frames than C.

## Cost plan
Two RTX 5090 boxes (≈ $0.6–0.8/h), 10 episodes × 5 variants each, ≈ 3–4 h each with cached depth: ≈ $5–7 [E].
Session budget $30.
