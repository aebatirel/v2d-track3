# Pre-registration: instance-level 6-D pose network for the white pot vs our tracker (3 Nov 2026)

Lane: instance-pose (branch `claude/instance-pose-20261103`). Owner's word via keen-heisenberg, 06:30 UTC:
"go in all". Public episodes only; no eval run in this task.
**Written and pushed before any network is trained or any network output is scored.**
Labels: [M] measured, [D] public vs mocap, [E] estimate, [H] hypothesis, [L] literature.

## Hypothesis
[H] A network trained on the exact pot mesh (instance-level), run per frame with stereo-depth fitting, gives pot
poses closer to mocap than perc2's zero-shot FoundationPose track on held-out public episodes.
- **Falsifier:** the gate below fails for both arms.
- **Prior [E]:** the control is already strong on the pot (unregistered perc2 pot AUC 0.973–0.998 on the pot-only
  episodes, 0.87–0.92 on ep26 / 27 with the rack; no lost frames), so the pass probability is modest (≈ 25 %). Most of
  the headroom is in ep26 / 27-type scenes.

## Fixed split (rule, applied before any training)
White-pot public episodes, checked in the parquets: **0, 2, 26, 27, 41, 42, 43, 44, 45** (9; no others).
- Rule: in each scene group, the higher episode indices are held out:
  - pot + lid {0, 2} → test 2;
  - rack + pot {26, 27} → test 27;
  - pot only {41, 42, 43, 44, 45}: ep43 must be in train, because the submitted pot mesh (TSDF from ep43 frames) was
    built from it; of {41, 42, 44, 45} the two highest → test 44, 45.
- **Train: 0, 26, 41, 42, 43. Test: 2, 27, 44, 45.**
- Test episodes are never trained on, neither their frames nor their labels nor their tracks. The synthetic pose
  distribution is drawn from the train episodes' control tracks only.

## Model and data (both arms)
- **Mesh:** the submitted pose-pack pot `white_pot_potlid_tsdf_ep43.glb` (md5 3591440e2dbf2029be908d46b29bfc96;
  13p / 14p), so the network's body frame equals the submitted mesh's frame. Its choice was GT-informed (13p's public
  pose CV, disclosed there). Both arms and the control are scored with the same mesh.
- **Network:** an own GDRN-style geometry-guided correspondence regressor in plain PyTorch (`pipeline/ipose/`), after
  GDR-Net / GDRNPP [L]. ResNet-34 encoder (ImageNet weights), U-Net decoder. On a 256² grey crop it predicts, at 64²,
  the visible mask, the amodal mask and normalised object coordinates (XYZ).
- **Pose from a crop:** the predicted XYZ of visible pixels is paired with stereo-depth points (FoundationStereo cache,
  rectified left) → RANSAC Kabsch (3-point samples, 1 cm inlier threshold) → least-squares refit on the inliers.
- **ROI:** the control track's projected pot box × 1.3 (GT-free; this is the "combine with the track" part).
- **Synthetic data (R):** 15k crops rendered with our own point-splat renderer at our rectified-left intrinsics.
  - Real backgrounds from public non-pot episodes (11, 12, 13, 18, 21, 22, 23, 24, 31, 39, 40).
  - Random hand-like occluders and distractor patches.
  - Random lighting, albedo gain and gamma; noise and blur.
  - Poses: train-episode control poses, perturbed by a random rotation (≤ 45° about a random axis, 15 % fully random)
    and a translation jitter.
- **Training:** AdamW 3e-4, cosine, batch 32, AMP. Loss: L1 on XYZ over visible pixels + BCE on both masks.
  - R: 40 epochs on synth.
  - R+M: from R, then 10 epochs on synth : real 1 : 1. Real crops are the train episodes' frames; their labels come
    from mocap, moved to our camera by a per-episode world alignment A (rotation chordal mean, translation mean over
    frames, fitted to the control track) and to the mesh frame by the kit's registration of the TSDF mesh to the scan
    (seed 1_000_003·ep + 101·slot). Visible-mask labels come from stereo-depth agreement (< 1.5 cm).
  - **R+M is GT-informed.** Its eval use would need the owner's explicit yes. R is GT-free.

## Variants (fixed now; primary = N)
- **N (primary):** per-frame network pose with depth (RANSAC Kabsch). The track pose is used on frames with < 25
  inliers (fallback, counted).
- NP: PnP only (RGB, no depth). Report only; it tells whether depth matters, and whether an RGB-only spoon network
  could work.
- NS: N smoothed over ±2 frames (translation median, rotation chordal mean). Report only.
- NT: the track corrected by the network, T_track(t) · Δ̄(t), where Δ̄ is the robust mean of T_track⁻¹ · T_N over
  ±15 frames. Report only.
Output poses are moved to the world by the control's `world_T_cam` (same VO cameras as the control). Every other
object in the episode keeps its control pose.

## Scoring and gate
- `pipeline/score_registered.py --reg_seeds 10` (perception-tracking's version), with the 13p mesh set for every
  object in both arms, applied to the control C (ptrkA ep2; ptrkB ep27, 44, 45) and to each variant.
- **Reported per test episode:**
  - pot AUC (10-seed mean);
  - pot plain ADD, mean over frames;
  - MPPE (episode);
  - pot position error, mean;
  - lost frames (pot ADD > 3 cm);
  - fallback frames.
- **Gate (per arm, variant N only):** mean pot ΔAUC over the 4 test episodes ≥ +0.02 vs the control, and no test
  episode below −0.01. R and R+M are reported separately. Secondary variants are exploratory and cannot pass the gate
  in this test; a passing secondary would need its own pre-registered replication.
- **Reading R for the spoon:** if R passes or comes within 0.01 of the control, a GT-free rendered-only network is
  credible for objects without public GT (the spoon). If R is far below the control and R+M is not, rendered-only
  training is not trustworthy here.

## Cost
- One 24 GB box (RTX 4090 / 3090 class, ≈ $0.3–0.5/h) for ≈ 3–4 h: ≈ $1.5–3 [E]. Cap $15.
- The box self-destroys when done, with a stall watchdog.
- Scoring on CPU here ($0).

## Addendum 1 (07:05 UTC, before any training or network output; coordinator's request)
**Secondary criterion** (variant N, per arm), added because the pot AUC is near its ceiling:
- per test episode, the median over frames of the plain pot ADD (base registration seed, after the scorer's alignment);
- **passes** if the mean relative reduction over the 4 test episodes is ≥ 20 % and no test episode's median ADD is
  higher than the control's.
- Lost frames (> 3 cm) are reported per episode.

The primary gate is unchanged. Passing only the secondary is reported as "accuracy gain without AUC gain"; it does not
by itself justify eval use.

Scoring meshes, confirmed by perception-tracking: the m13p set, i.e. the 13f payloads, except:
- pot: TSDF X;
- rack: library_c0 (md5 bbca8ec0…);
- wooden_piece_2: library_v3.

Reference base13p numbers are at docs/analysis/ptrk-20261102/results/base13p @ 42ac69e. Only the rack (ep27's alignment
object) and the pot enter the pot score.

No second object in this batch. The coordinator offered one as optional; it is declined to keep this test clean and
within its time.
