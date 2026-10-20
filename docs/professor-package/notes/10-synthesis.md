[← Index](../README.md) · [Summary](../00-summary.md) · [← 09](09-architectures-resourceful.md) · [11 →](11-placement-priors.md)

# 10 — V2D Track 3: research synthesis, candidate architectures and plan (2026-10-04)

Status: research only. Nothing built, trained or submitted. Every score/cost figure is an
estimate [E] or hypothesis [H] unless marked verified [V]. Sources: notes 01-09 in this folder
and `../[track3-requirements.md](../track3-requirements.md). Scripts for 02 and 07 are preserved in `scripts/`.

## 1. Bottom line

- The score is the simulated object trajectory vs mocap, plus our own meshes for CD-O. Error =
  reference error (perception) + tracking error (policy) + frame/timing bookkeeping errors.
- NVIDIA's baseline is a monocular, single-object, 30-fps-assuming chain with plain-IK hand
  retargeting [V 01]. It ignores the stereo pair, which the literature says is the single biggest
  perception lever on head-mounted rigs (HOT3D: 96.8 % vs 30.2 % within 10 cm) [V 03].
- Before any architecture matters, three bookkeeping traps must be closed, because each can zero
  episodes silently: frame timing [V 06], object-frame convention [V 07], symmetric slot-0 anchors
  [V 02/08/09].
- Recommended primary candidate: **"Stereo Object-First with Room Memory"** (section 4): stereo
  metric perception + a whole-episode world-frame smoother + a cross-episode object library +
  robot-native grasp synthesis checked in the evaluator's own physics, with repaired human-hand
  references as a per-segment fallback, trained with a timing-correct, score-aligned FlashCHORD
  recipe. It wins on both goals: leaderboard (attacks the dominant error terms) and Innovation
  (drops 3-D human hands/MANO, licence-cleaner, amortises across episodes).
- Cost to a competitive final: ~300-650 GPU-h (~$300-1,600) [E]; the first decisive week needs
  < 25 GPU-h. Per-policy RL time (assumed 2-4 GPU-h) is the main unmeasured cost driver.

## 2. What we know (load-bearing facts)

| Fact | Evidence |
|---|---|
| Losing a moved object ≈ "nothing moves" (AUC 0.55, MP-SR 0.05); common drift is the next biggest loss; MP-SR breaks at 3 cm constant offset, ~1.35 cm/axis noise, ~12° anchor rotation; scale matters little below ~18 % | [V 02] official scorer on public GT |
| Scorer aligns one rigid transform from slot-0 frame-0 pose; no scale correction; every public episode has a 13-117 frame static prefix before slot 0 moves | [V 02] |
| Stereo depth error 0.5-5.9 mm (0.25 px) over 0.3-1.0 m; mono metric depth 8-16 % | [V 02, 03] |
| Default Sharpa recipe (motion_speed 0.5, sim 20 fps) exports ~2 rows per source frame and the packer silently keeps the first N → packed row f ≈ source frame f/2 | [V 06] code reading, file:line |
| Scan frames: origin = area-weighted surface centroid; axes = surface-covariance eigenvectors, ascending variance; z sign by positive third moment (10/10); roll sign unresolved for the spoon (~50/50); cups/lid in-plane axes unstable under reconstruction noise | [V 07] all 10 scans |
| Spoon: 10/20 eval episodes (3,5,6,15,16,32,33,35,36,37), 3 spoon-only (35-37); no scan, no GT. Wrong roll ≈ −0.48 SP-SR, −0.50 MP-SR on the board (upper bound) | [V kit list; 07] |
| Cup is slot 0 in 6/20 eval episodes (8,10,14,20,32,33); spin about its axis is unobservable from shape; 10° spin → AUC 0.71, MP-SR 0.40 on those episodes | [V kit list; 02/08/09] |
| FlashCHORD reads no MANO fields; object reward weight 20 vs hand 0.25; keypoints at ±1 m over-weight rotation ~7-20× vs the score | [V 05, 04, 01] |
| Reference physical consistency is the largest published transfer lever (Regrind 0-3 % → ~99 %; V2P-Manip 0 → 79 %; C2Dex 18 → 58 %); NVIDIA's ego retargeter has its repair flags off by default | [V 04, 01] |
| Only `evaluation/{__init__,harness,metrics,rollout}.py` are digested; evaluation removes VOC assistance, terminations, resets to frame 0; everything else rebuilds from our checkpoint config | [V 01, 05] |
| Provided URDFs: mass 0.3 kg for every object (matches baseline default) | [V local URDFs] |
| FAQ: own meshes for CD-O; any embodiment; GPU credits under review; pretrained models allowed | [V FAQ 2026-10-02] |

## 3. Bookkeeping gates (must pass before any RL spend)

| Gate | Rule | Check |
|---|---|---|
| G1 timing | Reference parquet fps = 20.0 (true capture), `task.motion_speed=1.0`, `sim.fps=20`, N rows = N frames, start frame 0. (Overrides 01/08 advice to keep 0.5; needs organiser confirmation.) | Blocking: exported reference poses at row f equal input poses at frame f; `time_s·fps == reference_frame`; step count == roster N |
| G2 object frames | Canonicalise every own mesh with the 07 rule (`scripts/meshframe/canon.py`); mesh watertight, remeshed ≥ 2-3 mm edges before canonicalising | Rule reproduces all 10 public scans from our reconstructions of scanned objects (dev only) |
| G3 anchors | Slot-0 frame-0 pose = static-prefix estimate with support constraint; flag symmetric anchors (cups) | Per-episode anchor uncertainty report |
| G4 compliance | Physics/config freeze except reference, assets, training-side config | Config diff vs recipe for every physics field |
| G5 plumbing | Quaternion order (input wxyz), slot order = roster names, episode attribution from path | Packer + our own asserts |

## 4. Candidate architectures (final ranking)

### Primary — P: "Stereo Object-First with Room Memory"
Merges 08 Arch-1 perception, 09 R1 (hands-free grasps) and 09 R3 (object library).

| # | Step | Method (alternatives) | Add / cut vs NVIDIA | Moves |
|---|---|---|---|---|
| P1 | Rig conditioning | Rotate colour 180° with K; factory calibration; rectify mono pair; colour↔mono time-offset check | Cut AnyCalib/GeoCalib/MoGe intrinsics | everything |
| P2 | Stereo depth | FoundationStereo (TAO weights if licence OK; NVlabs NC otherwise), alternatives RAFT/IGEV (MIT), CREStereo (Apache), SGBM floor; reproject to colour; MoGe-2 only as hole filler | Add the stereo pair | scale, anchor, translation |
| P3 | Multi-object segmentation | Names from roster → Grounding DINO/OWLv2 on several frames → SAM2.1 bidirectional propagation with re-prompting and 3-D identity gating (SAM3.1 if licence OK) | Cut single frame-0 box, single object | object loss |
| P4 | Ego-motion + world | Stereo VO/SLAM with dynamic masks (DROID-SLAM stereo BSD, or cuVSLAM); table plane = gravity; world origin under slot-0 | Cut mono DROID + MoGe ratio, thinnest-PCA "up" | drift, gravity |
| P5 | Object library | One mesh per object across all episodes: masked stereo fusion along tracked poses (TSDF/2DGS) + generative completion (SAM3D/TRELLIS.2) registered Sim(3); canonical frame (G2); spoon chosen among fused/generative/parametric by silhouette+depth agreement | Cut single-view SAM3D + scale grid | CD-O, frames, sim geometry |
| P6 | 6-DoF tracking | FoundationPose with static-prefix multi-hypothesis registration, bidirectional, occlusion-aware IoU (hands removed), covariance out; OSI alternative MegaPose/GigaPose | Cut IoU<0.3 full-silhouette re-registration during grasps | noise, loss |
| P7 | World-frame batch smoother (keystone) | gtsam factor graph: robust measurements, exactly-static untouched segments, table support with stable poses, held-segment smoothness, inter-object non-penetration, zero-lag batch; anchor from static prefix | Cut camera-frame EKF | AUC, MP-SR, RPE, anchor |
| P8 | Interaction schedule | Object kinematics give *when*; stereo-triangulated MediaPipe palms give *which hand / where* | Cut HaMeR/Dyn-HaMR/MANO (kept as fallback) | contacts |
| P9 | Grasp synthesis | Own batched sampler in FlashCHORD physics: approach cone at palm prior, finger synergy closure, wrench support vs required wrench, whole-segment collision + carry test at VOC 0 | New stage | e_track |
| P10 | Reference composition + QA | wrist(t)=T_obj(t)·G; open contact-free frame 0; exact synthesised contacts; physical replay gate; per-segment fallback to repaired human hands (official retargeter with `--smooth_reference --surface_project --adaptive_offset`) | Add gates; cut plain IK as default | e_track, t=0 |
| P11 | Training | Sharpa FlashSAC with G1 timing; size-scaled object keypoints + symmetry-aware rotation weight [H]; evaluation-matched resets; contact robustness; replay flush at VOC 0; 2-3 seeds/episode; warm starts across same-family episodes if they pass [H] | Timing fix | e_track |
| P12 | Selection + packing | GT-free seed selection only if validated (Spearman ≥ 0.5 vs mocap on dev); G1-G5 gates; CD-O from P5 | — | all |

Why it should win: attacks the dominant budget terms in order (object loss → drift → anchor →
noise), uses the sensor NVIDIA ignored, and removes the least reliable stage (3-D human hands).
Biggest risks: non-prehensile segments (sweeping, lid, rack insertion, pouring) where rigid
grasps fail → per-segment fallback; spoon geometry/roll; cups as anchors.

### Alternative A — F: "Baseline+" (control and safety net; build first)
NVIDIA chain + G1-G5 + true fps + multi-object loader + stereo depth injected through the cached
depth folder (untested) + repair flags on + world-frame smoothing. Cheapest path to a valid first
submission (week 2); every P stage is measured against it.

### Alternative B — "Sim-Verified and Distilled" (09 R2)
Own sampling optimiser (SPIDER idea, re-implemented; code is CC BY-NC) finds an executable
trajectory in evaluator physics → distil into the policy → short RL. 25-50 GPU-h/submission if
distillation works. Use for failing windows only, after determinism (K2a) and distillation (K2b)
tests pass.

### Alternative C — "Joint whole-clip estimation" (08 Arch-3)
One optimisation over all frames/cameras with explicit flip/spin mode search and render-and-compare.
Too large to finish whole; apply to the worst 5 dev episodes if R3-diag shows > 25 % of error in
ambiguous windows.

### Deprioritised (with reasons)
- VLA / world-model as the scored policy: evaluator needs a FlashCHORD checkpoint [V 05].
- Generalist cross-episode policy: scene is built from one reference; heavy engineering [V 05].
- Embodiment swap: Sharpa is the only tuned recipe and closest to human hands [V 04]; cheap test only.
- Feed-forward 4D models as primary: unverified accuracy at cm level; use as cross-check [03, 05].

## 5. Experiment ladder (cheapest, most decisive first; GT only in scorer)

| Rung | Question | GPU-h | Kill/decide rule |
|---|---|---|---|
| R0 | G1 timing round-trip (pack GT through kit = perfect score), G2 rule on scans, CD-O code read, compliance diff | 0 | any failure blocks RL |
| R1 | Is cup/lid spin observable (texture)? colour shutter, sync | ~0-1 | unobservable → rely on organiser answer on scans |
| R2 | Stereo model/resolution vs scans placed at mocap pose | 2-4 | median < 3 mm at 0.4-0.7 m |
| R3 | Reference-only score: F vs P perception, smoother on/off, anchor variants, FP vs MegaPose | 5-15 | P must beat F by ≥ 0.1 reference-AUC |
| R4/K1a | Hand source: repaired human vs synthesised grasps, physical replay at VOC 0, 6 families | 1-5 | synthesised ≤ 0.5× error on ≥ 4/6 → fund P9 |
| R5 | e_track size, policy wall-clock, determinism on 2 GPU types, real-speed (G1) tracking | 10-20 | sizes fleet/seeds; if e_track ≫ e_ref move people to transfer |
| R10 | Spoon proxies (sweeper/dustpan handle as "unscanned") | 5-20 | pick spoon mesh method |
| R7 | Training factors one at a time (keypoint scale, resets, contacts, termination tail) | 50-100 | keep if gain > seed spread |
| R9 | GT-free selection validity | ~0 | Spearman ≥ 0.5 |
| R8 | Full v1 on 20 eval episodes; first pose + CD-O submissions | 60-120 | leaderboard calibration |
| R11 | Alternative C on worst episodes (conditional) | 20-60 | ≥ 0.03 reference-AUC gain |
| R12 | Final 20 × 3 seeds; holdout once; clean-host reproduction | 150-300 | final two picks |

## 6. Team split (4 core + optional)

- P1 Perception: rig, stereo depth, ego-motion/world, smoother (P1-P4, P7).
- P2 Objects: segmentation, tracking, object library, frames, spoon, CD-O (P3, P5, P6).
- P3 Transfer: interaction schedule, grasp synthesis, references, FlashCHORD training (P8-P11).
- P4 Infra/eval/compliance: harness, gates G1-G5, GPU fleet, fallback F, packing/submission.
- P5+ optional: Alternative B or C, GT-free selection, Innovation write-up.

Calendar [E]: week 1 R0-R5 and F; week 2 first submissions (CD-O, then F pose); week 3 P v1 +
R7/R10; week 4 R12, freeze recipe ~Oct 28, final three days for selection among genuine runs.

## 7. Questions for the organisers (ranked by score impact; the user owns sending)

1. May public scans be used as tracking templates and simulation assets (not for CD-O)? Decides
   cup-anchor spin (6 episodes), lid, and all object frames.
2. Spoon reference frame: is it the same canonical rule, and which roll sign? (~0.5 SP-SR/MP-SR.)
3. Timing: confirm `motion_speed=1.0` / fps 20.0 is the intended Track 3 setting; report the
   silent packer truncation under the default recipe.
4. Which asset/training settings are ours (URDF mass, collision mesh, support USDA, sim.fps)?
5. Are non-commercial components used by NVIDIA's own baseline (FoundationPose, BundleSDF,
   FoundationStereo research weights, nvdiffrast) acceptable under the Kaggle open-source rule?
6. How the six metrics combine into the track winner.
7. May unlabeled eval videos be pooled across episodes (object library, room priors)?

## 8. Unverified / open

- Per-policy RL time and real-speed tracking quality (R5). Determinism across GPU types (R5).
- Whether stereo depth injection through the baseline cache works without code edits (F).
- Grasp-synthesis coverage of non-prehensile segments (R4/K1a).
- Spoon roll sign; cup spin observability (R1, organisers).
- Licence wording interpretation (organisers).

## 9. Index
01 baseline dissection · 02 error budget · 03 perception literature · 04 transfer literature ·
05 alternatives · 06 timing audit · 07 mesh frame convention · 08 accuracy architectures ·
09 resourceful architectures · `scripts/` (error-budget, meshframe).


---
[← Index](../README.md) · [Summary](../00-summary.md) · [← 09](09-architectures-resourceful.md) · [11 →](11-placement-priors.md)
