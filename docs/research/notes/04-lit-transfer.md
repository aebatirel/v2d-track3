# 04 — Literature: transfer half (noisy HOI reconstruction -> simulated dexterous policy)

Status: COMPLETE for this pass (research only; no installs, no code edits, no SlamDunk code).
Started 2026-10-04. Scope: V2D Challenge Track 3, FlashCHORD transfer half.
Evaluator facts and rules: `reports/v2d-challenge/track3-requirements.md`.

Legend: [V] verified from primary source text read in this session; [U] unverified
(abstract-only, secondary source, or inference); [H] our hypothesis.

## TL;DR (details and evidence below; ranked ideas in section 10)
- The score is the simulated object vs mocap, so total error = reconstruction error + policy
  tracking error to our reference, minus whatever physics filters out. Log all three terms.
- Biggest published lever not exploited by CHORD/FlashCHORD: physically consistent,
  contact-consistent references (Regrind IK+RL 0-3% vs interaction-mesh ~99%; V2P-Manip w/o
  geometric constraints 0% vs 79%; C2Dex 18% -> 58%). FlashCHORD's ego retargeter is plain IK
  with de-penetration/smoothing flags that default to OFF.
- CHORD's contact-wrench reward is worth +0.14 AUC / +0.28 MP-SR on clean data but degrades
  with noisy contacts (paper's own limitation; force-closure fallback exists, disabled).
- CHORD/FlashCHORD never test object-reference noise; FlashCHORD's object reward uses 1 m
  keypoint levers, over-weighting rotation ~7-20x relative to ADD/MP-SR [H].
- Drop raw finger trajectories, not the grasp/contact prior: object-only (Human2Sim2Robot)
  loses 0.19 AUC to CHORD on clean mocap.
- Evaluator rebuilds physics from the checkpoint config: keep sim/scene/collision/embodiment
  at recipe defaults; several physics-changing variants exist in the repo and are rule risks.

## 1. CHORD (arXiv 2607.00033v2) and the FlashCHORD code that implements it

Source: https://arxiv.org/abs/2607.00033 (v1 2026-06-22, v2 2026-08-14), HTML v2 read via
WebFetch (summarised by a fetch model, so exact wording is paraphrase unless quoted).
Code read: github.com/nvidia-isaac/video_to_data @ main 7c0d3b94ce97b28deb571b4e7fdfeb5b2158df80
(2026-10-04), `robotic_grounding/flash_chord/` (FlashCHORD v0.4 port) and
`robotic_grounding/scripts/retarget/`. Evaluator pin per kit is 8c778f90 (track3-requirements.md);
I did not diff 7c0d3b94 against 8c778f90 for the files below [U: assumed unchanged].

### Method (paper) [V, paraphrased]
- Contact-wrench-space (CWS) guidance: per object part k, human contact points p and normals n
  in the object frame -> polyhedral friction cone (d edges) -> primitive wrenches
  [f; p x f] -> support function sigma = max over columns of B^T W along b pre-sampled 6-D
  unit directions. Robot support sigma_r computed the same way from sim contacts.
- r_cws = exp(-||max(0,(1-beta)sigma_h - sigma_r)||^2/v - ||max(0, sigma_r-(1+beta)sigma_h)||^2/v):
  a band reward; robot must produce a similar *set of wrench directions*, not the same points.
- Total r = r_task (object SE(3) tracking, + relative object term during inter-object contact)
  + r_imit (robot keypoints vs retargeted robot reference) + r_contact (CWS, missed-contact
  and unintended-contact penalties). Optional reduced force-closure reward
  r_fc = fraction of basis directions with sigma_r > eps, for unreliable contact labels.
- Residual policy around the IK-retargeted reference (wrist pos 0.05 m, wrist ori 0.15 rad,
  finger 0.15 rad scales; EMA 0.3). Observations: wrist state, finger joints, all object poses,
  command deltas (future targets), action history, contact positions/force directions.
- Virtual object controller (VOC): PD wrench on objects, fully on for a short stabilisation
  window after reset, then annealed by a curriculum. Training perturbations: wrenches sampled
  from the human contact wrench matrix.
- Terminations: time-out, wrist deviation, object deviation (paper: 15 cm / 40 deg).
- RL: FlashSAC, 2,048 envs, single L40S, ~2 h per sequence; same hyperparameters for all
  1,831 tasks. Paper states DexMachina / ManipTrans / SPIDER need ~10 / 20 / 4 h per task.
- Retargeting is plain IK from human keypoints; no physics-based reference repair described.

### Results (paper) [V, numbers as extracted]
- Benchmark 4,739 bimanual tasks from ARCTIC, TACO, HOT3D, OakInk2, GRAB, DexYCB, in-house
  third-person video recon; 1,831 evaluated; 82.12% task success (task success = completion
  ratio > 0.7 of rollouts without 15 cm / 40 deg object failure).
- Table 1 (60 tasks, 3 seeds): CHORD AUC 0.918, SP-SR 0.926, MP-SR 0.894, RPE 5.14 cm,
  MPPE 5.11 cm; SPIDER 0.804/0.911/0.789/6.99/14.28; DexMachina 0.737/0.690/0.569/9.92/15.88;
  ManipTrans 0.506/0.423/0.323/9.91/21.24; Human2Sim2Robot 0.730/0.686/0.569/9.78/16.59.
  These are exactly the challenge metrics (AUC from DexMachina, SP-SR from SPIDER, MP-SR from
  ManipTrans), so the challenge evaluator descends from this table.
- Table 2 ablation: Position-only contact reward (DexMachina-style) AUC 0.862 / MP-SR 0.780;
  no contact guidance AUC 0.774 / MP-SR 0.612. Contact term worth ~+0.14 AUC, +0.28 MP-SR on
  clean mocap references.
- Table 3 (whole-body G1, hand-only demos): CHORD SR 0.925 vs position-only 0.217.
- CWS reward vs success Pearson r ~0.80 across 1,831 runs (0.76-0.89 within datasets);
  usable as a GT-free proxy for "will this policy track" [V paper claim].
- Long horizon 40-48 s sequences: ADD-AUC ~0.85-0.98.
- Noise study (App. A.1, Fig. 9): synthetic Gaussian-like noise tiers 1-6 = wrist pos
  10..60 mm, wrist ori 5..30 deg, contact pos 5..30 mm, contact normal 5..30 deg.
  Settings: (a) noisy hand + clean contact: "robust to moderate hand-pose noise";
  (b) noisy hand + noisy contact + CWS: degrades more; (c) + force-closure reward instead of
  CWS: more stable at high noise but less dextrous. Numbers only in a figure [U: exact values
  not extracted]. IMPORTANT: noise is on hand/contact only; object reference noise (scale,
  pose jitter, drift) was NOT studied there [V from table 4 content; U that no other study exists].
- Video pipeline (App. C): MoGe metric depth, Grounding DINO -> SAM2 -> SAM3D mesh ->
  FoundationPose; ViPE + DynHaMR hands; Gaussian-splat joint refinement with temporal
  smoothing. Demonstrated on ONE brush task (qualitative). This is the challenge baseline.
- Limitations stated: needs relatively clean demos; noisy contacts degrade reward and need
  force-closure; object pose error is an imperfect task metric.

### FlashCHORD v0.4 code facts (the thing we actually train) [V, code read]
Recipe `configs/experiment/sharpa_flash_sac.yaml`:
- 4,096 worlds, 250,003,456 env steps, updates_per_collection 8, actor 256 / critic 512 hidden,
  replay 4.19 M, `task.motion_speed: 0.5` (reference played at half speed: twice as many control
  steps; `data/resampling.py::playback_times`).
- Objective `objective/tracking.yaml` + curriculum weights: object_keypoints 20.0 (Laplacian
  kernel, var 0.1), hand_keypoints 0.25, hand_joint_pos 0.25, contact_wrench_support 10.0
  (tolerance beta 0.1, var 0.1), missed_contact -1, unintended_contact -10, termination -100,
  action_rate -0.005, action_l2 -0.002; force_closure and contact_force_l2 present but disabled.
  Wrench basis 512 directions, 8 friction-cone edges, friction_coefficient 0.1 (for the wrench
  model only), torque dims scaled by 1/body radius.
- So the object term dominates (20 vs 0.25 for hand imitation): FlashCHORD is already mostly
  object-centric; hand references act as feed-forward + weak prior + contact source.
- Termination (training): wrist position 0.15 m, object position 0.10 m, object orientation
  0.50 rad (= SP-SR thresholds), reference end.
- VOC (`runtime/object_control.py`): mass-normalised PD on object root, k=400 1/s^2, d=40 1/s,
  plus gravity compensation, clamped 200 N / 50 Nm, multiplied by voc_scale.
  Curriculum `tracking_250m_mixed_reset.yaml`: voc_scale 1.0 -> .75 -> .5 -> .25 -> .1 -> .05 ->
  .025 -> .01 -> 0 at thresholds 19.7M ... 137.6M steps, then 0 until 250M; final ~50M steps
  reset to frame 0 with probability 0.5 (matches evaluation, which always starts at frame 0).
- Evaluation (`evaluation/harness.py::apply_evaluation_composition`): rebuilds env FROM THE
  CHECKPOINT'S OWN RESOLVED CONFIG, then forces voc_scale 0, VOC max force/torque 0, auto_reset
  off, always reset to first frame, seed 42, failure terminations disabled (scored afterwards).
  Scene fields read from the checkpoint config include `contact_friction`,
  `object_free_joint_damping`, `object_scale_min/max`, collision policy, embodiment, support.
  -> RULE RISK: these are physics. Changing them would be "altering physics"; keep recipe
  defaults unless organizers confirm. `motion_speed` is task timing, not physics, but ask
  organizers before changing it from the default 0.5 [H].
- Reference contacts (`data/mano_sharpa.py`) come from the parquet fields
  `mano_{side}_object_contact_{positions,normals,part_ids}` written by the upstream loader;
  contact fields are sampled nearest-neighbour. We control these fields -> contact labels are a
  legitimate lever (repair/relabel) [H].
- Official ego retargeter `scripts/retarget/ego_recon_to_sharpa.py` already exposes noise
  mitigations (all default OFF): `--smooth_reference` (Savitzky-Golay window 9, order 2; notes
  WiLoR finger velocity p95 ~7-9 rad/s with 50 rad/s spikes), `--surface_project` (push
  penetrating IK targets out of an OBB proxy, margin 5 mm, per-finger rigid),
  `--adaptive_offset` (outward push alpha 1.2 x smoothed penetration, cap 3 cm),
  `--hand_object_offset`; `--mano_to_robot_scale` default 1.2. Comment: penetrating MANO grasps
  make "the sim contact solver eject the hands". `contact_labels.py` (used by the Dexmate
  whole-body retargeter) labels contacts by probe-to-surface distance + min consecutive run +
  an object-motion gate (10-frame displacement > 10 mm; rest drift < ~8.5 mm in ego recon).

### FlashCHORD runtime facts relevant to transfer (cont.) [V, code read]
- Sim (`configs/sim/rl.yaml`): control 20 Hz, 5 substeps (100 Hz physics), MuJoCo-Warp
  solver via Newton, implicitfast, pyramidal cone, impratio 20, 100 solver iterations.
- Reset (`configs/reset/reference.yaml`): reference-state initialisation over all frames
  (frame 0 with prob 0.1, then 0.5 in the final stage), finger openness random in [0,0.7],
  20-step VOC decay after reset.
- Scene (`configs/scene/train.yaml` = eval.yaml): support true, object_scale 1.0-1.0,
  contact_friction 1.0, object_free_joint_damping 0.0. Collision: hand self-collision on,
  robot-object on, robot-support OFF (hands may pass through the table) [V config; U what
  "support" geometry is: per-episode `<sequence>_support.usda` from reconstruction].
- FlashSAC recipe (`training/reference_flash_sac.yaml` + experiment overrides): discount 0.99,
  batch 2048, n-step 3, 2 critics x 101 atoms, residual actor head, reward normalisation on,
  replay not cleared on curriculum stage change (`clear_on_stage_change: false`), BC coefficient
  0, fp16 mixed precision.

## 2. DexMachina (arXiv 2505.24853, Mandi et al., Stanford/NVIDIA, 2025) [V via fetch summary]
- Virtual object controller (6 virtual 1-DoF base joints + 1 articulation joint, PD) with an
  ADAPTIVE curriculum: gains decay multiplicatively (kp*phi_p, kv*phi_v) only when the running
  mean of each normalised reward (task, imitation, BC, contact) exceeds its std (Alg. 1);
  gains set to 0 when kp <= 0.01. FlashCHORD instead uses a FIXED step schedule.
- Rewards: r_task = exp(-b_pos d_pos) * exp(-b_rot d_rot) * exp(-b_ang d_ang) (multiplicative);
  auxiliary imitation (keypoints), BC (joint targets), contact reward (distance-based contact
  approximation, threshold 0.01 m, FPS-subsampled <= 50 contacts).
- ADD-AUC per object part then averaged (the challenge's AUC metric originates here).
- 6 hands (Allegro, Inspire, XHand, Schunk, Ability, DexRobot): "larger, fully-actuated hands
  achieve both higher final performance and better learning efficiency"; DoF matters more
  than size similarity; less capable hands deviate more from human guidance.
- Genesis, PPO (rl-games), 12k envs, one L40S/H100; CHORD quotes ~10 h/task.
- Reference repair: kinematic retarget, then replay the retargeted joints as soft PD targets in
  sim with the OBJECT FIXED to resolve hand-object penetration (App. A.2).
- Baselines: ManipTrans-style physics curriculum "no clear improvement"; curriculum on VOC
  beats no-curriculum on long horizons with the same rewards. Tighter wrist residual bounds
  gave the best result (action ablation).
- No noise-robustness study (ARCTIC mocap only).

## 3. ManipTrans (arXiv 2503.21860, CVPR 2025, Li et al., BIGAI) [V via fetch summary]
- Stage 1: generalist hand-trajectory imitator (wrist 6-DoF force + finger PD targets) pretrained
  on hand-only motion; Stage 2: per-sequence residual module with object state, COM, gravity,
  BPS shape code, hand-object distances, contact forces. a = a_I + delta_a_R.
- Physics curriculum: gravity 0 -> g, friction high -> normal; termination thresholds tighten
  (finger 6 -> 4 cm; object 90 deg/6 cm -> 30 deg/2 cm). (DexMachina and CHORD report this
  physics curriculum underperforms VOC curricula.)
- Success (this is the challenge MP-SR): object rotation <= 30 deg, translation <= 3 cm, joint
  error <= 8 cm, fingertip <= 6 cm, all must hold (per frame, per object for bimanual).
  The challenge drops the hand terms and keeps "every frame, every object < 3 cm and < 30 deg".
- Noise: Gaussian noise on the HAND trajectory input only, sigma 0.5/1.0/1.5 cm ->
  single-hand SR 55.1/55.3/46.7%, bimanual 30.1/19.5/39.2% [V as extracted; the bimanual series
  is non-monotonic, so treat as weak evidence; baseline clean SR 58.1/39.5%].
- ~15 min per 60-frame single-hand sequence on RTX 4090, IsaacGym 4096 envs (CHORD quotes ~20 h
  per task for its bimanual long-horizon benchmark).
- Embodiments: Inspire (main), Shadow, Allegro, articulated MANO without hyperparameter change.

## 4. SPIDER (arXiv 2511.09484v2, FAIR Meta + CMU) [V via fetch + repo README]
- Physics-based retargeting by annealed sampling-based MPC (DIAL-MPC-style kernel): 1,024
  samples, horizon 1.2 s (repo default 1.6 s), 16 annealing iterations, knot spline controls,
  covariance annealed over iterations and horizon. Cost = object + robot state tracking + effort.
- Virtual contact guidance: virtual constraints hold relative positions of contact pairs early
  and are tightened (penalty -> inf) over iterations; a contact filter drops unstable contacts
  (too short or drifting) -> explicit robustness mechanism for noisy contact labels.
- Robustification: pessimistic (max-cost) objective over domain-randomised friction, contact
  margin, mass. Augmentation: object pose/scale perturbation, mesh swap.
- Success (= challenge SP-SR): rotation error < 0.5 rad and average per-step translation error
  < 0.1 m (whole-trajectory averages, not per-frame).
- Results: OakInk Allegro ablation success kinematic 0.13 -> vanilla sampling 0.40 -> annealed
  0.69 -> + contact guidance 0.85. Table 3: SPIDER OakInk 47.9% at 2.5 FPS vs ManipTrans 39.5% at
  0.1 FPS; ARCTIC SPIDER 42.0% at 1.5 FPS vs DexMachina 67.1% at 0.05 FPS (RL still wins on
  long bimanual ARCTIC; SPIDER wins on speed). CHORD Table 1 has SPIDER AUC 0.804, SP-SR 0.911,
  MP-SR 0.789 but MPPE 14.3 cm and JPE 41 deg (good average tracking, poor per-frame precision).
- Output is open-loop controls; residual PPO on top (u = u_SPIDER + pi(o)) is supported.
  Supports MuJoCo-Warp, MJX, Genesis, IsaacGym; one demo is a single-RGB-video reconstruction
  (penetrations and artefacts "corrected via physics grounding", qualitative only).
- Repo facebookresearch/spider @ 44717007 (pushed 2026-09-22): LICENSE is CC BY-NC 4.0.
  Challenge winners must release Apache-2.0 code -> do NOT vendor SPIDER code; reimplement the
  idea from the paper if used [V license file; H on rule consequence]. Released dataset
  retarget_full (7,876 trajectories) on 2026-09-22.

## 5. FlashSAC (arXiv 2604.04539, RSS 2026, Kim et al.) [V via fetch summary]
- Few gradient updates with large models and high throughput; UTD 2/1024 in the paper, batch
  2048, ~2.5 M-param 6-layer inverted-residual nets with BN + RMSNorm, weight projection to unit
  norm, distributional critic, adaptive reward scaling bounded by return variance, Zeta-length
  noise repetition for exploration. Largest gains vs PPO on high-dimensional dexterous tasks.
- Ablation: overly large replay buffers slow learning (recent data sampled less often).
  [H] Relevant to FlashCHORD because VOC-assisted transitions from early stages stay in the
  4.19 M replay after VOC reaches 0 (`clear_on_stage_change: false`) -> stale-dynamics data.

## 6. Object-centric / hand-reference-light methods
### ObjDex (arXiv 2411.04005, CoRL 2024, Chen, Wang, Yang, Liu) [V via fetch summary]
- Hierarchy: generative high-level wrist planner (trained on ARCTIC MoCap, conditioned on object
  goal) + RL low-level finger controller with residual wrist. NO finger reference from humans.
- Reward purely object-centric: exp(-(20*rot + 1*trans + 5*joint)) error.
- Ablation "w. FR" (adding fingertip-matching reward) performed WORSE than object-only: human
  finger motion was counter-productive for the Shadow hand [V claim; numbers not extracted].
- IsaacGym, 2x Shadow on UR10e, PPO; ARCTIC 339 seqs.
### Human2Sim2Robot (arXiv 2504.12609v3, CoRL 2025, Lum et al.) [V via fetch summary]
- From one RGB-D video uses only (1) the object pose trajectory (FoundationPose) as an
  object-keypoint reward (3 anchors at L=0.2 m, exp kernel) and (2) one pre-manipulation hand pose
  for initialisation/exploration. Full hand-trajectory reward "does not show any substantial
  improvement". Robustness via observation noise (sigma 0.01) and random object force
  perturbations; IsaacGym 4096 envs, A100, 5-24 h per task.
- But on clean mocap CHORD Table 1 shows Human2Sim2Robot AUC 0.730 / MP-SR 0.569 vs CHORD
  0.918 / 0.894: object-only rewards lose when good hand+contact guidance exists. With noisy ego
  hands the ranking may change -> testable (Exp. T2 below).
### Dexplore (arXiv 2509.09671, CoRL 2025, Xu et al., NVIDIA) [V via fetch summary]
- Single loop retarget+track directly from raw MANO (no separate retargeting); demonstrations are
  "soft guidance": per-criterion termination envelopes that start wide and shrink adaptively,
  kappa = kappa_init * N_fail / N_total.
- Kinematic hand-matching weight scaled w(D) = min(1, D / 0.20 m) by hand-object distance, i.e.
  hand imitation is relaxed NEAR the object, where reconstruction errors and embodiment gaps hurt.
- GRAB, Inspire 87.7% / Allegro 78.7% success. No quantitative noise study reported.
### InterMimic (arXiv 2502.20390, CVPR 2025, Xu et al.) [V via fetch summary]
- Learns from imperfect MoCap (inaccurate contacts, poor hand detail) via subject teachers ->
  student distillation -> RL fine-tune.
- Physical State Initialization (PSI): start episodes from a buffer of reference states PLUS
  high-reward simulated states from earlier rollouts, because imperfect reference states cause
  "contact floating or incorrect hand motion, leading to unrecoverable failures". Ablation:
  w/o PSI object error 9.2 -> 10.2 cm, duration 42.6 -> 36.1 s.
- Interaction early termination; 3-level contact reward (promote / penalise / neutral band) to
  tolerate inaccurate reference contact distances.
- [H] PSI is only a training-distribution device; the evaluator still starts at reference frame
  0, so frame-0 physical validity must also be fixed in the reference itself.
### GALATEA (arXiv 2609.10050, Wu et al., 2026-09-09) - grounding generated videos [V via fetch]
- Noisy (AI-generated video) HOI references -> sim RL experts -> distilled controller.
- Reward: object position weighted 5x hand position; hand tracking gated to contact or lift
  phases only (no dense hand tracking during approach); lift bonus.
- Reference preprocessing: metric alignment from first-frame stereo depth (trimmed LSQ),
  contact relabelling from an HOI detector, penetration fix by OPENING hand joints instead of the
  retargeted penetrating pose, EMA smoothing of PD targets, 5 augmented variants of approach.
- Asymmetric actor-critic (critic sees clean object pose); SAPG. 78.6% vs PPO 77.2% vs two-stage
  68.5% mean success over 42 objects.

## 7. Reconstruction-side reference repair evaluated through sim policies (2025-2026)
### V2P-Manip (arXiv 2606.16436, Chen et al., 2026-06) [V via fetch summary]
- Monocular video -> MoGe-2-class depth with canonical intrinsics, FoundationPose +
  SpatialTracker multi-hypothesis tracking -> two-stage geometric optimisation (anatomically
  weighted contact loss favouring thumb/index, penetration threshold 3 mm) -> physical
  optimisation (force closure in friction cones) -> ManipTrans-style residual RL (IsaacGym).
- Ablation (XHand, 8 tasks): w/o geometric constraints 0% success; w/o physical constraints
  54.4%; full 79.3%. Embodiment: Arti-MANO 82.4, Inspire 78.8, Shadow 61.6, Allegro 52.0%.
- Strongest published evidence that hand-object contact/penetration repair BEFORE RL decides
  success on video-derived references.
### C2Dex (arXiv 2608.07045, Ren et al., 2026-08-07) [V via fetch summary]
- Aggregates noisy per-frame hand-object contacts in canonical OBJECT space (normal-compatible
  ray casts, DBSCAN medoid per hand vertex within stable segments), then optimises hand pose with
  contact-consistency + SDF penetration + regularisation; Laplacian interaction retargeting;
  ManipTrans residual RL (IsaacGym, PPO).
- Ablation: removing cross-frame contact consistency drops DexYCB success 57.78% -> 17.78%.
  Limitation: object pose drift corrupts canonical contact aggregation.

### Regrind (arXiv 2607.11874, Feng, ..., Qi, Culbertson; Cornell + Amazon FAR, 2026-07-13) [V via fetch]
- One video; interaction-mesh (Laplacian deformation, OmniRetarget-style) retargeting instead of
  IK; residual PPO with keypoint object reward, RSI, object-pose augmentation; IsaacSim.
- Sim Table 1 (object error, success): Regrind 5.3-6.5 mm, 98.7-99.8%; DexMachina 5.9-67 mm,
  0-99.7%; Mink IK + RL 10-39 mm, 0-3.1%; SPIDER 117-176 mm, 0% on these scissors/screwdriver
  tasks. => With the same RL, the retargeted reference quality (penetration-free,
  interaction-preserving) is the dominant factor [V numbers; U generality beyond 2 tools].
### EgoEngine (arXiv 2606.12604, 2026-06) - egocentric Aria video -> robot demos [V via fetch]
- Per 20-step chunk escalates Replay -> sampling MPC (SPIDER) -> residual RL (PPO) only when the
  cheaper mode fails an object-tracking feasibility test over two chunks; object-pose reward
  C - e_t with termination at e_t > C.
- On noisy Aria ego data MPC alone succeeded 0.20 vs RL 0.90; mixed mode saves 22-53% sim steps.
- Ego noise handling: finger human-mimic regularisation DISABLED (noisy retargeted fingers),
  loose feasibility thresholds (0.08 m, 2.5 rad), DR on pose/joint noise and mass [0.8, 1.2].
### Others found (abstract-level only) [U]
- VideoManip (arXiv 2602.09013, Chen et al., 2026-02): contact optimisation + synthetic variants
  from one video; 70.25% sim success (Inspire, 20 objects).
- Do as I Do (arXiv 2606.19333, Paliwal, ..., Malik, 2026-06): monocular HOI recon + retarget,
  per-reference MPPI dynamics-aware optimisation (per GALATEA's description).
- DexImit (arXiv 2602.10105, 2026): video -> grasp synthesis + motion planning (drops hand
  trajectory in favour of synthesised grasps).
- QuasiSim (arXiv 2404.07988, ECCV 2024): curriculum of parameterised quasi-physical simulators
  (soft spring-damper contacts -> rigid) for transferring penetrating MANO demos; +11% success.
  Equivalent spirit to VOC annealing but on the contact model; NOT usable at evaluation.
- DexTrack (arXiv 2502.09614, ICLR 2025, Liu et al.): generalist tracker + per-trajectory
  homotopy optimisation (solve easier "parent" reference tasks first, diffusion model proposes
  them) + data flywheel; qualitatively robust to cm-scale reference penetration; GRAB 46.7/65.5%
  vs PPO 38.6/54.8% under 10cm-20deg / 10cm-40deg criteria. IsaacGym 8192 envs.
- OmniRetarget (arXiv 2509.26633, Yang et al. 2025): interaction-mesh retargeting with hard
  kinematic/non-penetration constraints; downstream RL with 5 reward terms and no curriculum.
- GMR "Retargeting Matters" (arXiv 2510.02252, Araujo, Ze, Xu, Wu, Liu): retargeting artefacts
  measurably change tracking-policy success with reward fixed (humanoids).
- OmniTrack (arXiv 2602.23832, 2026-02): generate physics-consistent references with a
  privileged generalist policy rollout, then train the tracker on those instead of raw refs.
- PhysHOI (arXiv 2312.04393): contact-graph reward critical for HOI imitation.
- HOP (arXiv 2409.08273, Singh et al. 2024): video HOI -> sim-grounded robot trajectories ->
  generative prior + RL/BC fine-tune; notes video-recon noise as main limitation.
- Sampling MPC background: MuJoCo MPC / Predictive Sampling (arXiv 2212.00541, Howell et al.);
  DIAL-MPC diffusion-style annealing (arXiv 2409.15610), the kernel SPIDER builds on.

## 8. Additional FlashCHORD code findings that change the transfer analysis [V, code read @7c0d3b94]
- Object reward geometry (`objectives/keypoints.py`): object keypoints are the 6 object-frame
  UNIT axis vectors (+-X,+-Y,+-Z, i.e. 1 m lever arms), Laplacian shaping exp(-|d|/0.1) per
  keypoint, mean over keypoints. A pure 1 cm translation error costs exp(-0.1)=0.90; a 0.1 rad
  (5.7 deg) rotation moves 4 of 6 keypoints by ~10 cm -> ~0.37 each. So training values ~6 deg of
  rotation like ~10 cm of translation. The challenge metrics are translation-dominated: ADD on
  mesh points (object radius ~5-15 cm: 6 deg ~ 0.5-1.5 cm ADD), MP-SR 3 cm vs 30 deg, SP-SR
  10 cm vs 0.5 rad. [H] The default reward over-weights rotation ~7-20x relative to the score and
  makes the policy chase rotation noise (e.g. about the symmetry axis of cups/spoons, where
  FoundationPose-type trackers are least reliable).
- No relative-object reward (`r_relative` in the paper) and no human-wrench training
  perturbations exist in the v0.4 objective term list (OBJECTIVE_TERM_NAMES: object_keypoints,
  hand_keypoints, hand_joint_pos, contact_wrench_support, missed_contact, unintended_contact,
  termination, action_rate_l2, action_l2, contact_force_l2, force_closure) [V term list; U
  whether perturbations live elsewhere - grep found none in lifecycle/runtime/envs].
- FlashSAC has a TD3+BC-style term (`behavior_cloning_coefficient`, loss = mean (a - a_replay)^2,
  default 0) and `checkpoint.load_replay_path` -> a replay preloaded with external rollouts (e.g.
  MPC solutions) could serve as a demonstration prior [V code; U replay format compatibility].
- Built-in GT-free diagnostics: `scripts/debug/replay.py replay=physical` (open-loop physical
  replay of the reference) and evaluator in-sim metrics (ADD-AUC on thresholds 1..9 cm, SPIDER
  0.1 m/0.5 rad, ManipTrans 3 cm/30 deg, RPE, MPPE) computed against OUR reference.
- Support surfaces (`retarget/support_recon.py`, `scene/support.py`): thin kinematic disks
  generated from frames where each reconstructed object is at rest (hand-release gate optional).
  Support geometry is therefore a reconstruction output; table-height errors -> objects drop or
  pop at reset. [H/rule] Only video-justified supports are defensible; adding disks to pin
  objects would be an evaluation hack.
- Evaluator inherits sim/scene/collision/embodiment blocks from the checkpoint config. Variants
  that already exist in the repo but change physics/actuation: `embodiment=sharpa_hands_stiff`
  + `action=residual_hand_pose_stiff` (wrist kp 1200, tau 2000; documented for KINEMATIC replay),
  `scene.contact_friction`, `scene.object_free_joint_damping`, `scene.object_scale_*`,
  `sim.*` (substeps, iterations, impratio, cone), `collision.*`. Treat all of these as frozen at
  recipe defaults unless organizers approve in writing; add a pre-submission diff check of the
  resolved checkpoint config against the default recipe [H, compliance].
- Sharpa Wave: 22 active DoF, human-sized (208 x 90 x 50 mm, 1.3 kg) per vendor coverage
  (cnx-software 2026-06-02) [U secondary source]; retargeter default mano_to_robot_scale 1.2.

## 9. Synthesis

### 9.1 What drives object-tracking success (evidence, strongest first)
1. Reference physical/geometric consistency (hand-object non-penetration, contact-preserving
   retargeting). Same RL, different reference: Regrind interaction-mesh ~99% vs IK+RL 0-3%;
   V2P-Manip w/o geometric constraints 0% vs 79.3%; C2Dex contact consistency 17.8 -> 57.8%;
   GMR/OmniRetarget same message for humanoids. FlashCHORD uses plain IK (+ optional, default-off
   de-penetration flags). This is the largest published lever and is NOT studied by CHORD.
2. Contact guidance in the reward when contacts are reliable: CHORD Table 2 +0.14 AUC / +0.28
   MP-SR over no contact term; PhysHOI contact graph. With unreliable contacts CHORD itself says
   CWS degrades and force-closure is safer (Fig. 9, numbers not extracted).
3. Assistance curriculum that removes itself (VOC annealing) beats physics-relaxation curricula
   (DexMachina, CHORD); DexMachina's decay is adaptive, FlashCHORD's is fixed-step.
4. Object-centric reward dominance; human finger imitation can hurt (ObjDex FR ablation;
   Human2Sim2Robot; GALATEA 5x object weight, gated hand tracking; EgoEngine disables finger
   mimic on ego data). FlashCHORD already weights object 20 vs hand 0.25 + 0.25.
5. Residual actions around a feed-forward reference with tight wrist bounds (DexMachina action
   ablation; CHORD; ManipTrans; Regrind).
6. Matching train-time initial state distribution to evaluation (frame-0 resets; FlashCHORD resets to
   frame 0 with p=0.1, raised to p=0.5 only in the last ~50 M steps; InterMimic PSI shows state-init quality matters).
7. Learner/compute: FlashSAC >> PPO in wall-clock on dexterous tasks (FlashSAC paper); CHORD ~2 h
   L40S/sequence; numbers for the 4,096-world 250 M-step recipe are unmeasured.

### 9.2 Robustness to reference noise, by error type
| Error in our reconstruction | What the literature shows | Transfer-side mitigation |
|---|---|---|
| Global metric scale | Not studied by any transfer paper read. GALATEA/V2P fix it upstream (stereo/depth alignment). Scorer does not correct scale, and the policy tracks our (scaled) object trajectory, so scale error passes ~1:1 into ADD/MP-SR [H]. | None on transfer side; fix in reconstruction (stereo pair). |
| Object pose jitter | Physics + residual policy low-pass the motion; CHORD/FlashCHORD never test object-reference noise. Rotation noise is amplified by the 1 m keypoint reward [H, sec. 8]. | Smooth object reference (static-when-untouched, SE(3) smoothing); size-scaled object keypoints. |
| Object drift while resting | contact_labels.py notes ego-recon rest drift < ~8.5 mm per 10 frames; drifting static objects invite the policy to push them (or fail MP-SR). | Clamp untouched objects to a static pose; support from rest poses. |
| Hand-object penetration | Sim "ejects the hands" (official retargeter comment); DexMachina fixes by physical replay with object fixed; GALATEA opens penetrating fingers; V2P 3 mm penetration limit; C2Dex SDF loss; DexTrack qualitatively tolerant to cm-scale penetration. | Turn on/replace `--surface_project`/`--adaptive_offset`; SDF-based de-penetration; DexMachina-style physical replay; frame-0 validity check. |
| Missing / spurious contacts | CHORD: CWS degrades with contact noise, force-closure fallback; SPIDER contact filter (drop short/drifting contacts); InterMimic neutral band; C2Dex canonical-space aggregation; GALATEA detector relabel. | Relabel contacts from repaired hand + object motion gate; filter; widen CWS tolerance; FC blend. |
| Wrong hand / finger pose | CHORD robust to moderate hand noise when contacts are clean (wrist noise up to 60 mm/30 deg tiers); ManipTrans SR falls ~55 -> 47% at 1.5 cm hand noise (single hand); Dexplore relaxes hand matching near object; ObjDex/H2S2R drop finger refs. | Reduce/gate finger imitation; object-anchored hand during grasp segments. |
| Wrong timing / frame drops | Not studied. | Reconstruction side; keep motion_speed default. |

### 9.3 Can hand references be dropped?
- In FlashCHORD the hand reference plays four roles: (a) residual feed-forward (the action is a
  residual around it), (b) command observation, (c) imitation reward (0.25 + 0.25, small),
  (d) the source of reference contacts for the CWS reward (weight 10, large) and
  missed/unintended-contact penalties. Setting (c) to zero is a config change; removing (a)/(d)
  needs a substitute feed-forward and contact source.
- Evidence: object-only works for short, simple tasks (Human2Sim2Robot, ObjDex with a learned
  wrist planner), but on clean mocap CHORD beats object-only H2S2R by 0.19 AUC / 0.33 MP-SR and
  "no contact guidance" loses 0.14 AUC. So drop the *finger trajectory*, keep a *grasp/contact
  prior*. Recommended middle ground [H]: object-anchored hand reference - per contact segment,
  express the hand in the object frame, take a robust (median/medoid, C2Dex-style) relative pose,
  and re-synthesise the wrist and fingers as object pose x constant grasp; free-space approach
  and release keep the (smoothed) reconstructed trajectory.

### 9.4 Embodiment trade-offs
- DexMachina: larger, fully actuated hands learn faster and better; DoF > size match.
  V2P-Manip: Arti-MANO 82.4 > Inspire 78.8 > Shadow 61.6 > Allegro 52.0%. ManipTrans transfers
  across Inspire/Shadow/Allegro/MANO without retuning.
- Sharpa Wave (22 DoF, human-sized, isomorphic) is the closest available robot to MANO and is the
  only recipe with released, tuned FlashSAC settings. Floating hands avoid arm reachability and
  whole-body balance failure modes present in `dexmate_sharpa` (fixed-base arm+hand) and `g1_dex3`.
  Recommendation: floating Sharpa unless organizers allow a non-robot (MANO-like) hand, which
  FlashCHORD does not ship [H; ask organizers before any custom embodiment].

### 9.5 Per-sequence training cost (as reported)
| Method | Cost per sequence | Notes |
|---|---|---|
| CHORD (FlashSAC) | ~2 h, 1x L40S, 2,048 envs | paper |
| FlashCHORD Sharpa recipe | unmeasured; 4,096 worlds, 250 M steps, >= 46 GB free | repo |
| SPIDER | ~4 h (CHORD's number); 1.5-2.5 FPS of trajectory | MPC, no policy |
| DexMachina | ~10 h (CHORD's number); 12k envs PPO | |
| ManipTrans | ~20 h for long bimanual (CHORD); 15 min for 60-frame single hand | |
| Human2Sim2Robot | 5-24 h, A100, 0.6 B frames | |
| EgoEngine mixed mode | 22-53% fewer sim steps than pure RL | |

## 10. Ranked transfer-side ideas for FlashCHORD (no evaluator or physics change)
All require only reference/parquet changes or training-side code/config (objectives, curriculum,
reset, learner) outside the four digest files. Each must be validated on the 20 public episodes
against mocap with >= 3 seeds, reporting AUC, SP-SR, MP-SR, RPE, MPPE, the in-sim tracking error
to our own reference, training GPU-hours and failures together.
Decomposition to log for every run [H]: err(sim, mocap) vs err(ref, mocap) vs err(sim, ref).

1. Physically consistent reference pre-pass (de-penetration + MANO/object smoothing +
   static-when-untouched objects + frame-0 validity). Evidence: Regrind, V2P, C2Dex, DexMachina
   A.2, official flags exist. Cost: CPU/GPU minutes per episode, no RL change.
   Falsify: (a) cheap: `replay=physical` object error and frame-0 settling displacement before vs
   after; (b) full: FlashCHORD 3 seeds on 6-8 public episodes; reject if mean AUC/MP-SR gain is
   within seed std or if err(ref, mocap) worsens by more than err(sim, ref) improves.
2. Contact-label repair + robust contact reward: recompute part-wise contacts from the repaired
   hand with object-motion gating and SPIDER-style filtering (min duration, max drift in object
   frame); fall back to or blend `force_closure` when label confidence is low; widen CWS
   tolerance (beta 0.1 -> ~0.3) for noisy labels. Evidence: CHORD Table 2 + noise appendix, SPIDER,
   InterMimic, C2Dex. Falsify: CWS(raw) vs CWS(relabelled) vs FC on the same episodes/seeds; also
   check CHORD's CWS-success correlation (r ~0.8) holds on our data before using CWS as a proxy.
3. Score-aligned object reward [new H]: object keypoints scaled to the object's size (e.g. mesh
   bounding radius or sampled surface points, like ADD and Human2Sim2Robot's L=0.2 m anchors) so
   translation is not dominated by 1 m-lever rotation terms; optionally down-weight rotation
   about detected symmetry axes. Falsify: AUC and MP-SR translation-failure fraction vs default;
   reject if SP-SR/MP-SR rotation failures rise enough to offset gains.
4. Object-anchored hand reference (drop raw finger trajectory during grasp, keep grasp prior) and
   hand-imitation gating near the object (Dexplore w(D), GALATEA, EgoEngine). Falsify: per-episode
   A/B vs default; expect gains on episodes with poor hand reconstruction (GT-free flag: high
   penetration/contact-inconsistency statistics); reject if no correlation between the flag and
   the gain.
5. Evaluation-matched training: frame-0 resets from earlier stages, PSI-like buffer of good sim
   states for non-zero-frame resets, longer VOC=0 tail, flush/shrink replay at the VOC=0 stage
   (`clear_on_stage_change`). Falsify: compare training-mode success vs evaluator (frame 0, no VOC)
   success; the idea is moot if that gap is already < 2-3 points.
6. Adaptive VOC decay (DexMachina reward-plateau rule) instead of fixed thresholds; possibly
   decay object-orientation assistance before position. Falsify: same budget, compare final
   VOC=0 metrics and wall-clock; reject if not better than fixed schedule across >= 6 episodes.
7. Multi-seed / multi-variant per episode, select by GT-free proxy (in-sim err(sim, ref), CWS
   score, physical plausibility) - never by mocap on eval episodes. Falsify on public episodes:
   rank correlation between proxy and mocap AUC across seeds; useless if Spearman < ~0.5.
8. Physics-based reference optimisation with sampling MPC on the same Newton/MuJoCo-Warp model
   (SPIDER/DIAL-MPC idea, own Apache-2.0 implementation; SPIDER code is CC BY-NC 4.0) to produce a
   dynamically feasible hand+object reference, optionally preloaded as replay for the BC term.
   Evidence: SPIDER, OmniTrack, EgoEngine (MPC alone 0.20 vs RL 0.90 on ego data -> use as
   reference repair, not as final controller). Cost: hours per episode + engineering. Falsify:
   err(ref_mpc, mocap) vs err(ref, mocap) BEFORE any RL; abandon if MPC moves the reference away
   from mocap or fails on > half the episodes.
9. Interaction-mesh (Laplacian) retargeting replacing IK in the Sharpa retargeter (Regrind,
   OmniRetarget, C2Dex). Overlaps with idea 1; larger engineering. Falsify as idea 1.
Not recommended without written organizer approval (rule risk): changing contact friction,
damping, object scale randomisation in the checkpoint config, stiff embodiment, sim solver
settings, collision policy, `motion_speed`, synthetic support surfaces.

## 11. Open questions for organizers (transfer side)
- Are `motion_speed`, embodiment gains/variants (e.g. stiff wrist), scene friction/damping and
  object-scale randomisation in the checkpoint config considered "physics"?
- May the support USDA be edited/regenerated by participants, and under what constraints?
- Is a custom embodiment (e.g. MANO-like hand) acceptable for ranking?

## Progress log
- 2026-10-04 ~21:05 file created.
- 2026-10-04 ~21:10-22:30 local: CHORD paper + FlashCHORD code, DexMachina, ManipTrans,
  SPIDER (+repo, license), FlashSAC, ObjDex, Human2Sim2Robot, Dexplore, InterMimic, GALATEA,
  V2P-Manip, C2Dex, Regrind, EgoEngine, DexTrack, QuasiSim, OmniRetarget, GMR, OmniTrack, PhysHOI,
  HOP, DexMV, MaskedManipulator (title-level), MJPC, DIAL-MPC. Track 3 leaderboard still empty at
  2026-10-04 18:07 UTC (MVerghese/v2d-leaderboard-data).
- Not done: CHORD Fig. 9 numeric values; diff of 7c0d3b94 vs evaluator pin 8c778f90 for the
  objective/curriculum files; MaskedManipulator, HDMI, VideoMimic details; HOP/DexMV specifics
  beyond abstracts.
