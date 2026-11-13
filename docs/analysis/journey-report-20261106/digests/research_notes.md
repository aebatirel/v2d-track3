# Research notes digest (notes 01-26)

Source: opening and conclusion excerpts of the numbered deep-research notes (27 sections; two share number 23). Tags: [V] verified, [E] estimate, [H] hypothesis, [U] unverified, [C] computed. Most note bodies are cut in the excerpts, so figures are those that survive in the summaries.

### 01 NVIDIA V2D baseline dissection
- **Question:** how does NVIDIA's ego-video baseline work, and what breaks for Track 3?
- **Method and data:** read-only code study at pin 7c0d3b94; nothing executed.
- **Findings:** all metric quantities come from monocular MoGe-2 depth; the calibrated 75 mm stereo pair is unused. One object only (`obj_dets[0]`); code assumes 30 fps; frame-0 registration of hands, object and scale, and the run raises if either is absent. RE and RW defaults differ (e.g. gsplat epochs 10 vs 20).
- **Verdict:** not a Track 3 solution as shipped (two-object episodes unsupported). Use as control and fallback.
- **Pipeline:** the `result.npz` contract is the interface to match. DROID-SLAM and GeoCalib are unpinned clones (reproducibility risk).

### 02 Track 3 error budget
- **Question:** which errors dominate the official score?
- **Method and data:** 20 public episodes (5,246 frames); GT perturbed and scored with kit metric functions; AUC object approximated with 500 box-surface points.
- **Findings:** dropping the most-moving object gives AUC 0.55, MP-SR 0.05. A 5 cm linear drift costs 0.20 AUC. A 3 cm slot-0 anchor error gives MP-SR 0.63; a 10 deg anchor rotation gives MP-SR 0.68. A cup in slot 0 with 10 deg spin gives AUC 0.71, MP-SR 0.40. Lag costs about 1% AUC per frame. Scale below 5% is low return.
- **Verdict:** priorities are object continuity, one world frame, an excellent slot-0 frame-0 pose, and noise at or below 0.5 cm and 2 deg. No external literature.

### 03 Perception literature and open source
- **Question:** which stack gives metric object 6-DoF poses and own meshes from head-mounted video?
- **Method and data:** survey of papers, author repos, HF cards and BOP boards; nothing installed.
- **Findings:** HOT3D recall@10 cm 96.8% with stereo vs 30.2% with monocular depth. FoundationPose YCB-V ADD AUC 96.0. BundleSDF HO3D CD 0.57 cm; 6DOPE-GS 0.41 cm. Non-commercial: FoundationPose, BundleSDF, FoundationStereo, UniDepth, MASt3R-SLAM, WiLoR, HaWoR, GoTrack. OSI-clean: SAM2.1, Grounding DINO, MoGe-2, DROID-SLAM, MegaPose, GigaPose. MANO is research-only.
- **Verdict:** stereo is the main expected advantage. Three stacks proposed (S1 organiser-aligned, S2 accurate, S3 licence-clean); none tested. Licence is the main non-technical risk.

### 04 Transfer literature
- **Question:** how to turn a noisy hand-object reconstruction into a simulated dexterous policy?
- **Method and data:** primary papers via fetch-model summaries (largely paraphrase), plus a FlashCHORD code read.
- **Findings:** CHORD Table 1 (60 tasks, 3 seeds): AUC 0.918, SP-SR 0.926, MP-SR 0.894, MPPE 5.11 cm. Position-only contact reward: AUC 0.862 / MP-SR 0.780; no contact: 0.774 / 0.612. Regrind 0-3% to about 99% and V2P-Manip 0% to 79% with physical repair. FlashCHORD's unit-length keypoints value 6 deg of rotation like 10 cm of translation [H].
- **Verdict:** physically consistent references are the largest published lever; repair before RL. The CHORD table is optimistic (note 14). Object-reference noise was never studied.

### 05 Alternative architectures
- **Question:** what beats "baseline plus better parts"?
- **Method and data:** ideation and source reading of the checkpoint format; nothing run.
- **Findings:** [V] the evaluator rebuilds from the checkpoint config and forces VOC 0, frame-0 start and seed 42, so reference parquet, assets and embodiment are ours. Warm starts are native if observation layout matches. Strongest hypotheses: object-first references with synthesised grasps, whole-clip estimation, public episodes as supervision, a cross-episode object library. Experiment 0 (about 6 GPU-h) recommended first.
- **Verdict:** ranked hypotheses only. SPIDER and GoTrack are CC BY-NC.

### 06 Timing and row-alignment audit
- **Question:** do exported policy rows match source frames?
- **Method and data:** code reading at 8c778f90, plus running FlashCHORD's resampling functions on the kit roster.
- **Findings:** with `motion_speed` 0.5 the rollout has about 1.975(N-1) steps; the packer silently keeps rows 0..N-1, so row f holds source frame about 0.508f. Episode 1: N = 335, M = 659. Exact only at `motion_speed` 1 with fps exactly 20.0. Measured ceiling with the bug: AUC 0.415, MP-SR 0.00 [C].
- **Verdict:** real and silent; the evaluator cannot correct it, so set timing at training time and add a timing gate.

### 07 Mesh frame convention and the spoon
- **Question:** what object-frame convention does the scorer use, and what frame does the unscanned spoon need?
- **Method and data:** 10 public scans with URDF cross-checks; 10 sign statistics; scorer imported unchanged; score-impact simulations.
- **Findings:** origin = area-weighted surface centroid (residual <= 6e-10 m); axes = surface-covariance eigenvectors, ascending variance; z sign by positive third moment (10/10; chance 1/1024). The roll (x, y) sign is undetermined. Wrong roll: dSP-SR -0.48, dMP-SR -0.50, dAUC -0.13; wrong z sign: dAUC -0.28.
- **Verdict:** canonicalise own meshes this way; ask organisers for the spoon frame; do not hedge with 90 deg. Partly superseded by note 13.

### 08 Maximum-accuracy architectures
- **Question:** what architecture maximises the leaderboard under team, schedule and licence limits?
- **Method and data:** design plus adversarial review; two web checks (one from a search snippet).
- **Findings:** scored error ~ reference + tracking + anchor + frame offset + timing. Clean-reference policy error about 1-2 cm ADD [E]. Ranking: Arch-1 stereo-modular first; object-first with synthesised grasps as upgrade; Arch-F baseline-plus-fixes as control. Cost 330-650 GPU-h [E].
- **Verdict:** Arch-1 base. Licence exposure is high (FoundationPose, MANO, FoundationStereo).

### 09 Resourceful and innovation architectures
- **Question:** which design gives the best score per GPU-dollar, and what does a submission cost?
- **Method and data:** design and adversarial review; cost arithmetic on stated assumptions.
- **Findings:** about $1 per GPU-hour (range $0.7-2.2). Baseline-style about 65 GPU-h; hands-free grasp design about 70; distillation 30-50 if it works, about 90 if not; room memory about 30 after a warm pool exists. Perception passes cost 3-7 GPU-h per 20 episodes; RL dominates.
- **Verdict:** iterate perception without RL; gate references before RL. OSI-clean alternatives (RAFT-Stereo, IGEV, SAM2.1, MediaPipe) named; accuracy cost unmeasured.

### 10 Synthesis (round 2)
- **Question:** what single plan follows from notes 01-09?
- **Findings:** primary candidate "Stereo Object-First with Room Memory", with five bookkeeping gates (timing, object frames, anchors, compliance, plumbing). Cost about 300-650 GPU-h [E]. Per-policy RL time (2-4 GPU-h) assumed, not measured.
- **Verdict:** superseded in parts by notes 16 and 21; its timing recommendation was carried forward.

### 11 Placement priors and room-fixed world
- **Question:** can staging priors supply the yaw of symmetric slot-0 anchors?
- **Method and data:** all 20 public takes; leave-one-out on 4 public episodes; kit `score()`.
- **Findings:** start-yaw spread within a task is at most 4 deg rms. Camera heading W is measured to 1.18 deg rms LOO. Cup anchor AUC 0.277 (random spin) to 0.871 (exact W), 0.734 at W +-10 deg. Two-fold anchors AUC 0.616 to 1.0 for W error up to 10 deg. Projected eval gain about +0.18 AUC [E]. Rest snap +0.014 to +0.058 median AUC, never harmful. Cannot solve eval 8, 32, 33.
- **Verdict:** fallback and consistency check. Only 4 episodes in LOO.

### 12 Spin observability of near-symmetric objects
- **Question:** is spin about the rest axis observable for cups, lid, pot and pitcher?
- **Method and data:** scan self-similarity; marker solver with 1.5 px noise; one real frame (public ep 11 f0) with 4.07 px PnP error.
- **Findings:** cups are featureless; markers are the only cue. Beige cup's three markers are near-equilateral; on the real frame two markers flip 21-28 of 40 frames, and a third marker cuts this to 0-1 of 40. One marker at 1 px gives 0.4-0.7 deg. A 120 deg flip costs about 0.8 AUC. Pot and pitcher are unique by geometry.
- **Verdict:** needs a learned sphere detector and a multi-hypothesis identity check. The real-frame camera was fitted to GT, so agreement is not an accuracy measurement.

### 13 The wooden spoon
- **Question:** spoon appearance, frame sign convention, reconstruction, roll bit?
- **Method and data:** 10 Track 3 scans; 29 Track 2 scans as holdout; search over 9,139 sign rules.
- **Findings:** on the Track 2 holdout the mid-axis sign was right on 12/14 unseen scans (P = 0.006). P(frame B) 0.80-0.87 given markers in the scan. CD-O of complete spoon meshes 0.11-0.16 cm vs a 0.073 cm floor. Stereo roll median 2.5-6 deg at 0.5 px, 10 deg at 2 px; a 9-frame smoother halves it. No Track 3-only rule is significant (null P 0.21-0.28).
- **Verdict:** commit to frame B and ask organisers; a board A/B is not recommended. Contested: note 16 measured P(B) 0.09-0.14 under the mid-axis rule; note 20 measured 0.33 and about 0.45-0.5 overall.

### 14 Policy tracking error and training budget
- **Question:** how much error does the policy add (e_track), and what training budget is needed?
- **Method and data:** literature, code, leaderboard read, CPU computations; no RL or GPU.
- **Findings:** half-speed export as packed: AUC 0.415, SP-SR 0.30, MP-SR 0.00 [C]. Real speed, clean reference, soft wrist, one seed on eval task classes: AUC 0.70-0.79, SP-SR 0.69-0.90, MP-SR 0.24-0.54; best-of-3 0.74-0.81 / 0.76-0.93 / 0.39-0.67. Wrist kp 25 N/m sags 0.3 kg by 11.8 cm, saturating 19-25 of 27 carried tracks at real speed vs 0-1 at half speed. Track 2 Tier 1 0.510 / 0.700 / 0.200. Budget 40-80 GPU-h [E] for one seed over 20 episodes.
- **Verdict:** policy error is first-order for AUC and MP-SR; SP-SR at the frontier is more plausibly perception [H]. Physics is not configured deterministic.

### 15 Eval video survey
- **Question:** which eval episodes will break the pipeline, judged from video without GT?
- **Method and data:** eval videos viewed for design only; CoACD checks with the pinned version 1.0.11.
- **Findings:** robot grasp-and-carry likely fails on 7/20 (14, 15, 16, 20, 25, 28, 35); partial on 8; feasible on 4 (1, 8, 37, 38). Measured: GT contact states sit 4-15 mm inside pinned hulls (lid on pot 7.7-8.4 mm; sweeper in rack 10.5-15.3). Episode 20 starts with the cup in mid-air. Pre-contact windows are empty for 20 and 32, about 15 frames for 5, 6, 10, 14, 19, 33, 35, 37.
- **Verdict:** hull-aware references, pre-loaded frame-0 grasps for 20 and 32, and a window-based anchor.

### 16 Round-3 synthesis
- **Question:** which conclusions survive, and how should levers rank by AUC?
- **Method and data:** synthesis with skeptic passes on 11-15.
- **Findings:** leaderboard snapshot 2026-10-06: leader AUC 0.649, SP-SR 0.35, MP-SR 0.25; second 0.212 / 0.05 / 0.00. Working assumption: ADD-AUC alone orders the ranking [E]. Expected AUC levers: policy discrete failures -0.1 to -0.3; object loss about -0.55; slot-0 flip about -0.8 per episode; 5 cm drift -0.20; hull fix +0.02 to +0.05.
- **Verdict:** re-ranked plan; spoon-roll line later revised by notes 20 and 13.

### 17 Marker-based tracking
- **Question:** can mocap markers be the primary 6-DoF tracker?
- **Method and data:** learned sphere detector, leave-one-episode-out on five public episodes; emulated prior (GT plus AR(1) noise); verifier pass.
- **Findings:** lid alone: AUC 0.977. Cup, pot and pitcher are lost at the first carry (AUC 0.15-0.76). With a 10 mm / 5 deg prior, cup fixes from 2+ markers occur in 0.22-1.00 of rest and 0.53-0.98 of carried frames; trajectory AUC +0.03 to +0.11. Spin vote correct 9/10 with abstain. Runtime 0.4-1.4 s per frame.
- **Verdict:** HYBRID: a correction layer, primary only for the lid. Verifier: gains come from one noise draw; isotropic noise flatters the hybrid, since depth error survives on 2-marker fixes.

### 18 Persistent room map registered to mocap
- **Question:** can a room map give drift-free head pose for every frame?
- **Method and data:** pycolmap SfM on 525 public images (21.5 min CPU); relocalisation of all 20 eval clips; held-out GT checks.
- **Findings:** public-only map gives 100% coverage with at least 500 rig inliers (30 needed). Held-out cam-a residual median 0.12-0.13 cm; pose error 1.8-2.4 mm and 0.02-0.03 deg. Table height 0.6017 m vs GT 0.6012 m. Keyframe glitches 7-11 mm in 0.1-0.2% of frames. 75% occlusion gives up to 4.4 cm; 90% fails. Gain +0.10 AUC vs measured factory-stereo VO; +0.01 vs a 3x better VO. About 0.31 CPU-s per frame.
- **Verdict:** adopt the public-only map. Note 21 corrected the board gain to +0.06-0.07.

### 19 Collision hulls and CoACD inflation
- **Question:** can hull inflation be removed on the asset side?
- **Method and data:** CoACD 1.0.11 with the exact call; 21 GT contact states; exact solids as floor. Mostly macOS runs; Linux checked later.
- **Findings:** two causes: voxel preprocessing of non-manifold scans (median +2.9 mm / +1.3 mm) and concavity tolerance of 0.025 L per mesh (rack 12.6 mm, pot 8.7, lid 4.6; median +3.9 / +1.5 mm). Exact colliders still show 1.6-4.3 mm. Splitting rack and pot to 120 mm and lid, cups, sweeper to 60 mm brings all states within 0.9 mm of the floor. Costs: about 1 crashing debris hull per 2,100 split hulls on macOS; 0.1-1 TB RAM for 4096-world split-rack training; output differs across macOS and Linux.
- **Verdict:** removable on the asset side. Welding the boards restores 1.6-3.2 mm clearance, the cheapest clear fix. Build on the evaluator's platform.

### 20 Camera sync, spoon frame and slot-0 window
- **Question:** camera time offsets, spoon frame, and an automatic slot-0 pre-motion window?
- **Method and data:** frame-content analysis of 39 clips; rolling-shutter fit; GT-free detector on public and eval clips.
- **Findings:** b and c hardware-synchronous (-0.01 +- 0.09 ms). Cam a: a[k+1] ~ b[k] in 36/39 clips; rolling shutter about 31.6 ms per image height. Spoon marker triangle 53.0 / 153.2 / 194.2 mm; P(B) 0.33 under the mid-axis rule, 0.88-1.00 under x-skew rules. Window bias median 0.14 deg / 0.13 mm (max 0.59 deg / 2.2 mm) on 19 public episodes; stake about 0.001 AUC. Wrong identity (twin planks) gives AUC 0.73 even with an exact tracker.
- **Verdict:** apply the camera offset (up to 0.11 AUC per object if ignored). Not independently verified; the verifier failed on network outages.

### 21 Round-4 synthesis: architecture v3
- **Question:** what architecture follows from notes 17-20?
- **Findings:** room map +0.06-0.07 board AUC (corrected); marker layer +0.02 to +0.10, conditional on the emulated prior; anchor window about 0.001. Open: real tracker error, e_track at real speed, split-asset behaviour in the real evaluator.
- **Verdict:** v3 pipeline (room-map camera, tracker plus marker layer, GT-free anchor, asset fixes, repaired hands, timing gate, stiff-wrist option). Day-1 runbook: E1 smoke about 1 GPU-h; E2 12-24 GPU-h on six twin episodes.

### 22 FlashCHORD reference contract and a MANO-free hand path
- **Question:** what does FlashCHORD require of a reference, and can a hand path avoid MANO?
- **Method and data:** read-only code study at 8c778f90.
- **Findings:** `mano_*_joints`, betas and poses are not read. All-zero contacts load but penalise grasping: unintended contact (-10) fires on any touch. Wrist termination at 0.15 m. Pink-IK retargeter runs without MANO. Both hands are always built; an absent hand must be parked.
- **Verdict:** MANO-free route feasible as a hypothesis; MANO canonical axes are inferred and unverified.

### 23a Non-RL grasp controller in the reference
- **Question:** can a written grasp controller, followed by RL, hold objects?
- **Method and data:** literature agents; trials in evaluator physics scored with `sim_vs_ref` (against our own reference, no GT).
- **Findings:** zero action does not grip; pinch locks lift at most 1.7 cm. Wrap grasp on eval episode 3: zero-action 0.462 (floor 0.439; RL alone 0.380); episode 35: 0.205 to 0.267 (floor 0.112). Literature: SPIDER ADD-AUC 11.0 to 56.9 with contact guidance (CC BY-NC); PPO from a SPIDER reference task progress 0.99 vs 0.07 kinematic.
- **Verdict:** promising. The rules were developed on eval episodes 3 and 35, and the note asks for public-episode confirmation before reliance. This needs checking against the no-tuning-on-eval rule.

### 23b Is the 250M-step budget needed?
- **Question:** does FlashCHORD need 250M steps?
- **Method and data:** config reading; one Colab run; literature review.
- **Findings:** 250M = NVIDIA's 1.97B PPO schedule divided by 10, plus 50M frame-0 stage. 92 min at a measured 45,300 env steps/s. Training metrics are discarded (logging disabled); intermediate policies not kept. One data point: tissue-box policy at 20M steps, AUC 0.918, object motion unknown.
- **Verdict:** unknown. Measure the learning curve on day 1 (about +1 GPU-h), then A/B 125M vs 250M on three public episodes (18 GPU-h, $9-29). Curves still rising at 50M, per the note.

### 24 Physics-aware grasp design
- **Question:** can grasps be designed from contact physics and anatomy?
- **Method and data:** measured simulator inventory; grip-force LP; results on eval episodes 3 and 35 with sim_vs_ref and five repeated official evaluations.
- **Findings:** zero-action spoon roll in hand reaches 72 deg (kp 25) and 63 deg (kp 400). Episode 3, kp 400: fine-tune at 70M steps 0.981; five repeats mean 0.968, sd 0.020, min 0.928. Episode 35: 40M steps 0.979; five repeats mean 0.978, sd 0.002. Plain-reference RL reached at most 0.41 at 250M. The anatomy closing rule lowered episode 3's zero-action score from 0.658 to 0.43. Copying human hand switches gives 0.07-0.18.
- **Verdict:** a stiff wrist is essential once RL fine-tunes; anatomy rules unvalidated on public episodes. Cited: Markenscoff 1990, Napier 1956, Feix 2014, Muzykewicz 2013, Johansson and Westling 1984, Sancho-Bru 2003, used as design rules.

### 25 Support-consistent meshes
- **Question:** can a mesh be designed to rest stably at the start pose?
- **Method and data:** rigid-body statics certificate; fills of 0.5-2 cm; simulator rest check; public episodes 18, 12, 24, 27 without GT.
- **Findings:** episode 18 registered AUC 0.320 (previous best 0.889); the brush moved 88.7 mm / 81.7 deg before grasp, because its mesh touched the table over 0.6 x 0.4 cm. Certificate: centre of mass inside the support polygon with margin >= 3 mm and tilt >= 3 deg.
- **Verdict:** standard statics. The test outcome is not in the digest; hypothesis H1 (episode 18 AUC >= 0.8; episodes 12 and 27 within their spread) is falsifiable.

### 26 Carry-aware control, force feedback, Kalman filtering
- **Question:** can control theory, carry-aware methods or force feedback help the policy?
- **Method and data:** code study; three literature reviews; adversarial verification; nothing run.
- **Findings:** the kp 25 N/m wrist has a natural frequency of about 0.64 Hz with the object and saturates on 23 of 27 moving public tracks (note 14 says 19-25). kp >= 100 removed saturation in reruns. Ball-wrist damping ratio 4-5.5. The actor sees contact directions, not magnitudes. An 18 mm contact threshold can mislabel a carry as "no contact". Cited: Zorina 2024 windowed smoothing (YCB-V ADD(-S) 0.84 to 0.90).
- **Verdict:** Kalman filtering belongs in the reference, not the policy; a config-only wrist gain is the top lever, but the best gain is open. Plan: 16-30 runs, $35-100 (owner approval needed).

## Cross-note lessons about the task and current technology

- **Timing is the silent killer.** The default `motion_speed` 0.5 caps the packed score near AUC 0.415 [C]. Set timing at training time and assert row counts.
- **One rigid anchor sets the episode.** Slot-0 frame-0 alignment propagates anchor errors (symmetric cups, spoon roll, pre-contact motion) into every frame.
- **Continuity beats precision.** Losing an object costs about 0.45-0.55 AUC; 5 cm drift costs 0.20.
- **The soft wrist is a shared bottleneck.** Notes 14, 24 and 26 agree on saturation at real speed; they disagree on the right gain (note 14 hypothesises kp 200-600; note 24 used kp 400 on two episodes).
- **Physics is fixed; assets are not.** Collision meshes, inertials and object frames are our levers (notes 19, 22); organiser acceptance is unconfirmed.
- **Spoon frame and symmetric anchors remain open.** P(frame B) ranges from 0.09 to 0.87 across notes 13, 16 and 20.
- **Evidence grades vary.** Literature facts often come from fetch summaries; the CHORD table is the authors' own; many costs and gains are estimates from emulated priors or 4-episode LOO.
- **Eval-episode use needs care.** Notes 15, 23a and 24 used eval videos or episodes for design; their gains need public-episode confirmation.
- **Silent failures need asserts.** Row truncation (06), twin-object identity (20), debris hulls that crash MuJoCo (19) and platform-dependent hulls all fail without a kit error.
- **Compute claims differ widely.** Per-pass estimates run 40-80 GPU-h; programme estimates 300-650 GPU-h; the only measured throughput is 45,300 env steps/s (note 23b).
- **Determinism is not guaranteed.** Keep the first evaluation per checkpoint; log hardware.
- **Licences constrain the stack.** FoundationPose, FoundationStereo, BundleSDF, SPIDER and GoTrack are non-commercial; MANO is research-only; the Kaggle clause was not read from the competition text.
- **Open organiser questions:** AUC-only ranking; spoon frame and markers; `motion_speed` and fps; wrist variant; collision and inertial ownership; evaluation world count and platform.
