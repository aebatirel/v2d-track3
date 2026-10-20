[← Index](../README.md) · [Summary](../00-summary.md) · [← 04](04-lit-transfer.md) · [06 →](06-timing-audit.md)

# 05 — Alternative architectures for V2D Track 3 (beyond "baseline + better parts")

Status: COMPLETE v1 2026-10-04 (ideation + research only; no installs, no code edits, no SlamDunk
code; nothing run). All levers/compute figures are untested hypotheses unless marked [V].
Started 2026-10-04. Context: `reports/v2d-challenge/[track3-requirements.md](../track3-requirements.md).
Sibling notes (other owners): [03-lit-perception.md](03-lit-perception.md), [04-lit-transfer.md](04-lit-transfer.md).

Legend: [V] verified from primary source text read in this session; [U] unverified
(abstract-only, secondary source, or inference); [H] our hypothesis (untested).

## TL;DR
- [V] The checkpoint fixes only the learner type (FlashSAC/PPO) and the evaluation-time
  overrides; the reference parquet, object assets and registered embodiment travel inside the
  checkpoint config and are ours. FlashCHORD never reads MANO fields, so a robot-space hand
  reference can be synthesised directly. Physical replay at `voc_scale=0` is a near-free
  trackability probe. Warm starts across episodes are native if the observation layout matches.
- [H] Strongest alternatives: A (object-first references with synthesised Sharpa grasps, no
  3D human hands), B (whole-clip multi-camera estimator with static/support priors and a
  static-prefix slot-0 anchor), E (public episodes used as in-domain supervision, priors and
  policy warm starts), I (cross-episode object library for CD-O and the spoon).
  Conditional on cheap tests: C (physics-in-the-loop fill of occlusions), H (pick rollouts
  by video consistency), K (sample-then-distill to cut RL). Low priority: F (generalist,
  heavy engineering), G (embodiment knob, cheap to test), J (VLA/world model; does not fit
  the checkpoint format except as a VLM scheduling aid).
- [H] Scorer-geometry risk: an object model whose body frame differs from the organisers' scan
  frame is penalised on every frame; the unscanned spoon needs the scan convention inferred
  from the 10 public scans. Check numerically with the kit scorer first.
- Run Experiment 0 (error-budget split, ~6 GPU-h) before committing the team.
- Licences: SPIDER and GoTrack code are CC BY-NC 4.0 -> re-implement ideas, ask organisers.

## Progress log
- 2026-10-04 start: skeleton; begin searches (CHORD/FlashCHORD, object-centric HOI,
  render-and-compare, physics-in-loop, 4D foundation models, point trackers, priors,
  generalist trackers, embodiments, world models/VLA).
- 2026-10-04 +~8 min: section 0 (checkpoint constraint, verified from source) saved.
- 2026-10-04 +~18 min: section 1 source register (transfer + 4D) saved.
- 2026-10-04 +~28 min: embodiment facts, more sources, frame-convention insight saved.
- 2026-10-04 +~42 min: loader/replay facts, HOT/Dex4D, datasets, panel saved. Next: candidates.
- 2026-10-04 +~55 min: section 2 Exp0, A, B saved.
- 2026-10-04 +~62 min: candidates C, D, E saved.
- 2026-10-04 +~70 min: licence notes, F, G, H saved.
- 2026-10-04 +~78 min: I, J, K saved. Next: ranking, portfolio, organiser questions.
- 2026-10-04 +~88 min: comparison table, portfolio, organiser questions saved. COMPLETE (v1).

## 0. What the checkpoint constraint actually fixes (read from source, main branch, 2026-10-04)

Source: `nvidia-isaac/video_to_data` main, `robotic_grounding/flash_chord/` (files fetched to
session scratchpad only). CHORD paper: arXiv 2607.00033 (HTML read).

- [V] `evaluation/harness.py::evaluate_checkpoint` rebuilds the environment **from the
  checkpoint's own saved resolved config** (embodiment, action space, observation, collision,
  scene, sim, reference parquet path, curriculum stage) and then only forces:
  `voc_scale=0`, VOC max force/torque 0, `always_reset_to_first_frame`, reset seed 42,
  `auto_reset=False`, tracking-failure terminations off, deterministic actions, world_count.
  Supported learners: exactly two typed targets (FlashSAC `TrainingConfig`, PPO `TrainingConfig`);
  anything else raises `unsupported checkpoint training target`.
- [V] Consequence: the *reference parquet* (our reconstruction: wrist poses, finger joints,
  object body poses, per-hand contact points/normals/part ids, object URDF/mesh paths) and the
  *embodiment* are ours to choose per episode. The scored object trajectory is
  `sim(policy, our reference, our object meshes)`; the reference itself is never scored.
- [V] Registered embodiments: `sharpa_hands` (floating, default recipe), `sharpa_hands_primitive`,
  `sharpa_hands_stiff`, `dexmate_sharpa` (Vega arm+hand, `motion_v1/single_robot`), `g1_dex3`.
  Action spaces: `residual_hand_pose`, `residual_hand_pose_stiff`, `residual_joint_position`,
  `sonic_joint_residual` (G1). FlashCHORD rejects objectless motions.
- [V] Policy observation (`observation/policy.yaml`): wrist pose/vel, finger joints, object
  pose, *commanded* wrist/finger/object deltas from the reference, raw/processed action,
  reference contact positions/directions. Action = residual on the retargeted hand reference.
  So the hand reference acts as (a) the action prior and (b) the source of contact-wrench
  guidance; it is not itself scored.
- [V] Reward weights in the canonical Sharpa FlashSAC recipe (`curriculum/tracking_250m_mixed_reset`):
  object_keypoints 20.0, hand_keypoints 0.25, hand_joint_pos 0.25, contact_wrench_support 10,
  missed_contact -1, unintended_contact -10, termination -100; VOC annealed 1.0 -> 0 over
  ~123M of 250M steps; last ~50M steps half the episodes start at frame 0. `force_closure`
  term exists but is disabled. 4,096 worlds, 250,003,456 env steps, `motion_speed: 0.5`.
- [V] Warm start is native: FlashSAC config has `training.resume`, `checkpoint_path`,
  `checkpoint.load_replay_path`; `state_<steps>.safetensors` is complete resumable learner
  state, `policy_<steps>.safetensors` is eval-only. Checkpoints store exact policy input
  descriptions and reject incompatible ones (=> a cross-episode warm start needs identical
  observation layout, e.g. same object-body count / contact K).
- [V] CHORD paper: per-sequence policies (not generalist), FlashSAC 2,048 envs ~2 h on one L40S;
  ablation AUC 0.918 (wrench guidance) vs 0.862 (position only) vs 0.774 (no contact);
  "robust to moderate hand-pose noise", degrades at ~30 deg orientation noise; with noisy
  contacts a force-closure objective "can outperform corrupted wrench guidance but reduces
  dexterity". Limitation listed: "Effective contact guidance requires relatively clean human
  demonstrations".
- [H] Scene config fields saved in the checkpoint include `contact_friction`,
  `object_free_joint_damping`, object scale range and `support`. Tuning these per episode is
  plausibly "changing simulator physics" -> treat as off-limits unless organisers say otherwise.
  Object mass/inertia come from *our* URDFs, which is part of reconstruction and is fair game
  but must be physically honest (ask organisers if in doubt).

Implication used throughout this note [H]: error(scored) = error(reference object trajectory,
incl. mesh frame/scale) + error(policy tracking). Any architecture that improves the object
reference **and** makes it easier to track physically wins; hand reconstruction quality matters
only through trackability (action prior + contact guidance).

## 1. Source register (grows as read; [V]=read primary text this session, [U]=search snippet only)

Transfer / physics-in-loop:
- [V] SPIDER (FAIR+CMU, arXiv 2511.09484 v2, Feb 2026): sampling-based (annealed-covariance)
  physics retargeting with *virtual contact guidance* that first "sticks" object to desired
  contact points then relaxes; runs on MuJoCo Warp/MJX/Genesis/IsaacGym, 100 Hz physics,
  "2.5 Hz" full method, ~10x faster than RL baselines; 9 embodiments; OakInk 47.9 % /
  GigaHands 87.9 % success (Inspire); output used as feed-forward + RL residual
  `u = u_SPIDER + pi(o)`. Code: github.com/facebookresearch/spider, **CC BY-NC 4.0**
  (see licence notes below).
- [V] Grasp-and-Lift (arXiv 2601.18121, Jan 2026): physics-in-the-loop refinement of
  vision-aligned HOI (DexYCB/HO3D) in MuJoCo; MANO PCA-10 + wrist spline keyframes every 5
  frames; CMA-ES sliding window of 4 keyframes; objective = object pose + object velocity +
  hand joints + contact + smoothness; 0.67 cm / 2.97 deg object error, 71.7 % success
  (<30 deg, <3 cm), ~557 s/sequence (3-4x faster than ManipTrans 1987 s). Code: not stated.
- [V] DexImit (RSS 2026, arXiv 2602.10105; Shanghai AI Lab/Tsinghua/CUHK/NVIDIA): monocular
  video -> SpatialTrackerV2 depth (scaled by hand priors) + SAM3D mesh + FoundationPose
  "align-render-align"; **grasps are synthesised by force-closure optimisation and ranked by
  distance to the reconstructed human hand**, then the hand follows the object transform
  (object-centric motion generation). Sim success 100 % put-cup, 78 % pot, 52 % stack-cups;
  object trajectory "usability" 76-82 % with SpaTrackerV2+FoundationPose. Code: not stated.
- [U] DexMan (NTU/Stanford, arXiv 2510.08475, code github.com/EmbodiedAI-NTU/DexMan, no
  licence on GitHub): monocular 3rd-person video, no calibration/depth/assets; residual RL to
  reproduce object trajectories guided by hand motion + contact priors; 27.4 % TACO, 37.0 %
  Veo3-generated videos.
- [U] DexMachina (Stanford+NVIDIA, ICML 2026, arXiv 2505.24853): VOC with decaying strength
  (origin of FlashCHORD's VOC curriculum).
- [U] DexTrack (ICLR 2025, arXiv 2502.09614): generalist neural tracking controller trained
  from per-trajectory RL demos + IL with a "data flywheel" and homotopy optimisation; >10 %
  success over baselines.
- [U] AGILE (arXiv 2602.04672): agentic generation for sim-ready HOI from monocular video
  under occlusion (watertight meshes + 6D poses).
- [U] "Recovering Physically Plausible HOI from Monocular Videos" (CVPR 2026): RL policy in
  simulator reproduces interaction to remove penetration/floating.

4D / tracking foundation models:
- [V] Any4D (CMU, CVPR 2026, arXiv 2512.10935; github Any-4D/Any4D Apache-2.0): feed-forward
  metric 4D (depth, allocentric scene flow, cam pose) for N frames; optional depth/intrinsics/
  poses inputs; 0.50 s for 50 frames on H100; no HOI evaluation.
- [V] D4RT (DeepMind/UCL/Oxford, CVPR 2026, arXiv 2512.08924): query-based any-point
  any-time 3D tracking; TAPVid-3D AJ 0.875 (cam) — beats SpaTrackerV2/pi3/VGGT/MegaSaM.
  No public repo found (google-deepmind/d4rt 404) -> not usable.
- [U] SpatialTrackerV2 (ICCV 2025; github henry123-boy/SpaTrackerV2, custom licence);
  TAPIP3D (github zbw001/TAPIP3D, Apache-2.0; RGB or RGB-D input, camera-stabilised feature
  clouds); CoTracker3 (facebookresearch/co-tracker, custom licence); MapAnything
  (facebookresearch/map-anything, Apache-2.0).

More sources:
- [V] FlashCHORD floating-hand actuation (configs): default `residual_hand_pose` wrist PD
  kp 25 / tau_max 45, EMA 0.3, residual scales wrist 5 cm / 0.15 rad, fingers 0.15;
  shipped `residual_hand_pose_stiff` = wrist kp 1200 / tau_max 2000; `sharpa_hands_primitive`
  = primitive-collision URDF with prismatic wrist base. Sim: 20 Hz control, 5 substeps
  (100 Hz), Newton solver, MuJoCo contacts, pyramidal cone. Training terminations: wrist >
  15 cm, object > 10 cm or > 0.5 rad. FlashCHORD also ships a pretrained generalist
  humanoid tracker (SONIC ONNX encoder/decoder) used as a base under `sonic_joint_residual`
  -> precedent inside the official stack for "pretrained generalist + per-episode residual".
- [U] GoTrack (Meta, arXiv 2506.07155; github facebookresearch/gotrack): CAD-based pose
  refinement + tracking, model-to-frame *and* frame-to-frame registration via flow on DINOv2,
  pose confidence without a scorer; evaluated on HOT3D egocentric Aria/Quest3 HOI.
- [U] ManiDext (arXiv 2409.09300): diffusion that synthesises hand manipulation/grasp poses
  conditioned solely on a 3D object trajectory (vertex-level correspondence embeddings).
- [U] ManipTrans (CVPR 2025): generalist hand-trajectory imitator pre-trained, then
  per-task residual under interaction constraints (DexManipNet 3.3K episodes).
- [U] MaskedManipulator (NVIDIA, SIGGRAPH Asia 2025): tracking controller distilled into a
  goal-conditioned generative policy (full-body; object goals).
- [U] BIGS (CVPR 2025): bimanual hand + unknown object 3DGS from monocular video, SDS prior
  for unseen parts.
- [U] Being-H0 (arXiv 2507.15597), EgoVLA (arXiv 2507.12440), DreamGen (arXiv 2505.12705),
  DreamDojo (arXiv 2602.06949): VLA / world models from human egocentric video. None outputs
  a FlashSAC/PPO checkpoint; see candidate J.

Scorer-geometry insight [H, derived from the scorer description in [track3-requirements.md](../track3-requirements.md),
needs a numeric check with the kit scorer]: if our object body frame differs from the scan
frame by a constant O=(R_O,t_O), then (a) for slot 0 the first-pose alignment hides it at t=0,
but a later pure translation d is scored with error ||R_O^T d - d|| = 2 sin(theta_O/2)|d|
(theta_O=20 deg -> 35 % of every displacement); (b) for slots >0 the error is a constant
||O x - x|| on every frame. So for the 5 pose boards the *frame convention* of each object
model is as important as tracking accuracy. Scanned objects: use the scan frame (if
organisers allow scans as tracking priors). Wooden spoon: must guess the organisers' scan
convention -> infer it from the 10 public scans (origin/axes rule) before anything else.

More verified facts relevant to alternatives:
- [V] `data/mano_sharpa.py::load_mano_sharpa` requires only: `fps`, object body positions/
  wxyz (T,B,·), object names/mesh paths/URDF paths/mesh radii, and per side
  `robot_{left,right}_wrist_position`, `robot_{side}_wrist_wxyz`, `robot_{side}_finger_joints`
  (+ contacts/frames). **MANO fields are not read by FlashCHORD**; a robot-space hand reference
  synthesised directly (no MANO, no retargeter) is a valid input. Both sides are always present
  (an idle hand needs a parked reference).
- [V] `configs/replay.yaml` + `replay/physical.yaml`: open-loop physical replay of the
  reference with the same embodiment/action stack and a configurable `voc_scale`
  (`replay/kinematic.yaml` uses stiff VOC 10000). Running physical replay at `voc_scale=0`
  is a near-free, GT-free trackability probe for any reference before spending RL GPU-hours.
- [U] HOT (HKUST et al., arXiv 2512.19583): generalist hand-object tracker trained only on
  synthetic demos (force-closure grasps + 8 interpolated meta-skills), teacher-student PPO
  distillation, Isaac Gym, MANO/Shadow/Allegro; zero-shot on GRAB 18/31 full sequences;
  grasp/move/place 94/99/98 % success but rotate 56 %.
- [U] Dex4D (arXiv 2602.15828; github Dex4D/Dex4D-Simulation): policy conditioned on paired
  3D point tracks (current vs target) of the object, trained on 3,200 objects; tracks come
  from 4D reconstruction of generated videos.
- [U] Datasets usable as external priors: HOT3D (833 min egocentric multi-view, 33 objects,
  hands+objects+cameras GT), EgoDex (829 h Vision Pro egocentric with hand joints, 194 tasks),
  GigaHands (34 h, 417 objects, 14k clips). Licences not yet checked.
- [V] Innovation panel (challenge page): Hao Su (Fudan), Yunzhu Li (Columbia/SceniX/World
  Labs), Louis Lian (Lightwheel), Changliu Liu (CMU), Yuting Ye (Meta), Kaifeng Zhang (Sharpa),
  Javier Romero (Meta). Criteria: economic viability, data flywheel, challenging an assumption,
  complexity reduction. (Panel mixes hand-tracking/MANO, physics-world-model and sim-data people.)

## 2. Candidate architectures (all ideas below are [H] hypotheses unless a line says [V]/[U])

Shared error model [H]: scored error ~= (object reference error, incl. mesh frame + metric
scale + first-pose error of slot 0) (+) (policy tracking error, incl. drops/ejections/knocked
static objects). SP-SR (<=10 cm & <=0.5 rad) and MP-SR (<3 cm & <30 deg, *every* object) are
dominated by catastrophic frames; AUC/MPPE by mean accuracy; RPE by inter-object consistency;
CD-O by mesh shape only (Sim(3)-registered).

### Experiment 0 (prerequisite for choosing among A-K): split the error budget
On 3 public episodes (one each: Pan_Solo, Pot_with_lid, Cup_In_Dish_Rack) train FlashCHORD with
the **mocap GT object trajectory** as the object reference (hands from whichever source exists
first) and score the evaluator rollout against the same GT with the kit scorer. This is the
policy-only ceiling. Compare with reference-only error (our perception vs GT, no sim).
~6 GPU-h. Decides whether the team's marginal hour goes to perception (B/D/E) or transfer
(A/C/G). Also run `replay.py` physical at `voc_scale=0` on the same references (minutes) to
calibrate whether open-loop replay success predicts trained-policy success.

### A. Object-first references with synthesised robot grasps (no 3D human hands)
Idea: the scored quantity is the object; FlashCHORD only needs *a* robot hand reference that
can physically produce the object motion. Replace HaMeR/DynHaMR -> MANO -> retargeting with
grasps synthesised directly in Sharpa space from the object trajectory.
Steps:
1. Object trajectories (any perception stack; B is the intended one).
2. Interaction segmentation per object/frame: resting / held-L / held-R / bimanual / tool
   contact, from object kinematics (leaves support, speed), 2D hand masks/boxes only (no 3D
   hand), mask adjacency; optional VLM keyframe script (DexImit uses Qwen3-VL for scheduling [V]).
3. Grasp synthesis per held interval on our object mesh: force-closure optimisation or
   sampling in the FlashCHORD scene; constraints: approach side consistent with where the 2D
   hand is, no table/other-object collision along the whole interval, stable under the
   interval's accelerations. Rank by a sim holding test along that interval (VOC 0).
4. Wrist(t) = T_obj(t) * G during hold; min-jerk approach/retreat from a parked pose; finger
   close/open ramps; idle hand parked away from static objects (protects MP-SR).
5. Contacts (points/normals/part ids) written from the synthesised grasp -> contact-wrench
   guidance is exact instead of inferred from occluded hands.
6. Physical replay probe; on slip/drop try next grasp; then normal FlashCHORD training.
Why it might win: references are physically consistent by construction (no penetration,
no missed contact, correct scale relative to object) -> lower tracking error and fewer
catastrophic failures (SP-SR, MP-SR, AUC). CHORD itself reports force-closure guidance can
beat corrupted wrench guidance [V]; DexImit/HOT build demos this way [V/U]. Removes the
scale-ambiguous monocular hand stack and the MANO licence dependency [V: FlashCHORD never
reads MANO fields].
Risks: tool/non-prehensile phases (dustpan+sweeper sweeping, lid placement) may need contact
types not covered by a static grasp; regrasps/handovers need correct segmentation; a
robot grasp unlike the human's can make the demonstrated object orientation unreachable
(cup into rack slot); loses "human-likeness" (not scored, but panel may ask).
Compute: grasp search + replay ~minutes/episode on one GPU [estimate]; saves the 3D hand stage.
Innovation: challenges "video-to-robot needs 3D human hand reconstruction"; complexity
reduction (fewer models, no MANO); pitch hands as 2D cues only.
First cheap falsifier: on 3 public episodes, hold the object trajectory fixed (same source
for both arms) and vary only the hand source: (a) baseline reconstructed+retargeted hands,
(b) synthesised grasps. Step 1: physical replay at VOC 0 (~0 GPU-h) - object ADD vs GT.
Step 2: equal-budget FlashCHORD training (6 policies). Kill A if (b) is not >= (a) on >= 2/3
episodes in eval ADD-AUC or replay survival.

### B. Whole-clip, multi-camera analysis-by-synthesis object estimator with physical priors
Idea: replace per-frame tracking with one batch estimate per clip that uses all cameras,
stereo metric depth and "how objects behave in a kitchen" priors.
Steps:
1. Rig model: colour (rotated 180 deg) + mono L/R factory extrinsics; stereo depth on the
   mono pair reprojected to colour; ego-motion from stereo VO with hands/objects masked;
   table plane + gravity from the static scene.
2. Per-frame initialisation (FoundationPose / GoTrack-style refiner [U]) on colour+depth.
3. Joint optimisation over all frames and objects: multi-camera silhouette + stereo depth +
   feature/flow render-and-compare residuals; priors = piecewise-static when untouched
   (exactly constant world pose), resting on table in a stable pose, no inter-object
   penetration, SE(3) spline smoothness while held, confidence-weighted occlusion.
4. Slot-0 first pose: average over the static prefix (objects normally rest at clip start),
   because the scorer aligns the whole episode on that single pose [V track3-requirements]
   (5 deg there ~ 2.6 cm at 30 cm lever arm).
Why it might win: object-reference error is likely the dominant term; static segments
become exactly static (near-zero ADD for untouched objects, helps MP-SR), occlusion gaps are
bridged smoothly, scale is metric (stereo), slot-0 anchor is precise.
Risks: mono cams sit +/-37.5 mm from the colour cam, so occlusion diversity is small
[H: occluder 0.40 m, object 0.55 m, f ~562 px -> ~14 px relative shift]; depth/scale is the
main gain, not occlusion; mono images are greyscale (feature mismatch); colour/mono time sync
unverified; textureless objects (white pot).
Compute: ~10-30 GPU-min/episode [estimate].
Innovation: moderate (better parts + priors); complexity reduction if stereo replaces
MoGe + DROID-SLAM + gravity alignment.
First cheap falsifier: on public GT, (i) measure what fraction of object-frames are static
and what fraction of per-frame-tracker error lives in them; (ii) compare per-frame tracker vs
batch-smoothed vs mocap (ADD-AUC, % frames <3 cm/30 deg) on 5 episodes. Kill the batch layer
if gain < ~2 AUC points.

### C. Physics-in-the-loop reconstruction ("the simulator is the smoother")
Idea: let the same physics the evaluator uses decide what the object could have done while
it was occluded, and hand FlashCHORD a reference that is already executable.
Steps:
1. Inputs: object observations with per-frame confidence (B), interaction segments + hand
   reference (A or baseline).
2. Sampling-based optimisation in MuJoCo-Warp/Newton with the actual Sharpa embodiment and
   scene: variables = wrist/finger keyframe splines (Grasp-and-Lift: keyframes every 5
   frames, CMA-ES windows of 4 [V]; SPIDER: annealed-covariance sampling with virtual contact
   guidance [V]); cost = confidence-weighted residual between *simulated* object and the
   observations (or rendered mask/depth residual) + contact consistency + smoothness.
3. Output: executed object+robot trajectory -> new FlashCHORD reference (and an open-loop
   action prior; FlashCHORD's residual action space already builds on the reference).
4. Optional EM loop after RL: render the policy rollout, find frames where rollout disagrees
   with video or the policy fails, re-optimise those windows, retrain/fine-tune.
Why it might win: occlusion gaps get physically consistent fills (object moves with the hand
or rests), physically impossible reference artefacts (floating, teleport, penetration) are
removed before RL, so the policy is not asked to do the impossible -> fewer catastrophic
frames (SP-SR/MP-SR), lower tracking error, faster RL convergence.
Risks: highest engineering cost; sim friction (scene `contact_friction` 1.0) and our URDF
masses may make "physically plausible" differ from what happened, biasing the trajectory
away from the evidence; local minima; Grasp-and-Lift needs ~557 s/sequence on CPU MuJoCo [V]
(we would need a GPU-batched variant).
Compute: ~0.1-0.5 GPU-h/episode [estimate], plus EM retrains if used.
Innovation: high (physics as the perception prior; "sim-verified data"); fits panel members
working on physics-informed world models.
First cheap falsifier: on public episodes, find occluded windows (object mask < 50 % visible)
and measure their share of total ADD error for the per-frame tracker. If < ~25 %, C's
ceiling is small -> keep only a light "repair failing windows" version. Otherwise compare
kinematic smoother (B) vs physics-in-loop fill in those windows against mocap.

### D. Model-free object motion from 4D foundation models / 3D point tracks
Idea: track the object as a rigid cloud of 3D point tracks instead of a mesh; needed most for
the unscanned wooden spoon (10/20 eval episodes).
Steps:
1. Video masks (SAM2-class) on colour; stereo metric depth.
2. Dense 3D point tracks on object pixels: TAPIP3D with RGB-D input (Apache-2.0 [U]),
   SpatialTrackerV2 (custom licence [U]) or Any4D with metric depth input (Apache-2.0,
   0.5 s / 50 frames on H100 [V]). D4RT is best on TAPVid-3D but has no public weights [V].
3. Per-frame robust SE(3) (RANSAC + weighted Kabsch over visible tracks), temporal spline.
4. Object frame chosen by the inferred scan convention (section 1 insight); mesh by fusing
   object-frame points across the clip (+ generative completion) -> also a CD-O mesh.
5. Where a scan exists, use D only as initialiser/outlier check for B.
Why it might win: no mesh needed (spoon), tracks survive partial occlusion, gives a
mesh-free rotation estimate for thin/symmetric objects where silhouette render-and-compare
is ambiguous.
Risks: spoon handle ~22-34 px wide in a 562 px-focal mono image at 0.5 m [H, arithmetic];
roll about the long axis weakly observed; generic 3D trackers are not trained on HOI;
drift turns into rotation error under rigid fitting.
Compute: few GPU-min per clip.
Innovation: moderate; complexity reduction (mesh-free tracking).
First cheap falsifier: treat a scanned elongated public object (dust brush / sweeper handle)
as unscanned; compare D vs scan-based tracker vs mocap (rotation + translation error).

### E. Same-room flywheel: public episodes as supervision, priors and warm starts
Idea: the 20 public episodes share rig, room, objects and 9/20 eval task setups - use them as
an in-domain training set, not just a validation set.
Steps:
1. Per public episode recover camera<->mocap alignment and video<->mocap time offset from
   our own estimates of static objects vs GT (training-time only; never at eval inference).
2. Fine-tune the object pose refiner / tracker on ~20 x 262 frames x 3 cams of GT poses
   for the 10 scanned objects; train an error/confidence model used to weight B/C residuals.
3. Room prior file: table plane height/normal, gravity, stable rest poses per object,
   plausible masses/friction (checked against public URDFs).
4. Task-motion priors for eval episodes with public analogues (weak, DTW-aligned templates
   used only inside low-confidence gaps).
5. Policy flywheel: train public-episode policies (needed for local validation anyway), keep
   `state_*.safetensors`, warm-start eval episodes that share the object set/observation
   layout (`training.resume`, `checkpoint_path` [V]).
6. Tune reward weights / curriculum / embodiment per task family on public episodes with the
   kit scorer.
Why it might win: in-domain supervised signal is the strongest lever available and it is
legal (public data); improves every board; warm starts cut GPU-h per eval episode.
Risks: overfitting 20 episodes (use leave-one-task-out); alignment noise contaminates labels;
the spoon and ep 8 (beige_cup + white_pot) have no analogue; template priors can bias
novel motions.
Compute: fine-tuning 5-20 GPU-h; public policies ~40 GPU-h (also serves validation).
Innovation: direct hit on "data flywheel".
First cheap falsifier: (i) leave-one-episode-out tracker fine-tune vs off-the-shelf on held-
out public episodes of a *different* task; (ii) warm-start test: Pan_Solo ep A -> ep B at 25 %
of the step budget vs scratch at 100 %. Kill warm starts if final eval ADD-AUC is worse.

Licence notes found while grounding C/B [V, GitHub 2026-10-04]: SPIDER official code is
`facebookresearch/spider` (README badge **CC BY-NC 4.0**; MuJoCo-Warp/Genesis backends;
2026-09-22 release of 7,876 retargeted trajectories); GoTrack `facebookresearch/gotrack`
LICENSE = **CC BY-NC 4.0**. Winners must release Apache-2.0 code, so for C/B re-implement the
*ideas* (annealed sampling + virtual contact guidance; flow-based model-to-frame +
frame-to-frame refinement) rather than vendor these repos; confirm with organisers whether
NC-licensed pretrained weights are an acceptable "reasonable cost" dependency.

### F. Generalist tracker across episodes, then per-episode fine-tune
Idea: train one FlashSAC tracker over many references, then emit one cheap fine-tuned
checkpoint per episode (the constraint is one checkpoint *per episode*, not one training run).
Steps:
1. Reference corpus: public GT object trajectories + our reconstructed references for all 40
   episodes + augmentations (time-warp, SE(3) perturbation, dropout noise) + synthetic
   meta-skills (grasp/move/place/rotate as in HOT [U]) on the 11 object meshes.
2. Extend *training* (not evaluation) to sample a reference per world. Evaluation modules are
   untouched [V: only evaluation/{__init__,harness,metrics,rollout}.py are digested]. Keep a
   fixed observation layout (pad object slots / contacts) or one generalist per object count.
3. Train generalist; per eval episode resume from its learner state on that episode's parquet
   for a short budget; checkpoint config points at that parquet.
Why it might win: per-episode GPU-h falls (economic viability) and the policy has seen noisy
and perturbed references, so it may tolerate reference errors better (tracking error).
Precedent: ManipTrans pre-trains a generalist imitator then per-task residual [U]; DexTrack
flywheel [U]; FlashCHORD ships SONIC as a pretrained base under per-episode residuals [V].
Risks: `setup_scene` builds all worlds from one parquet [V] -> heterogeneous worlds need real
engineering in Newton/Warp; checkpoint input-description validation [V] forces exact layout
match; underfitting episode specifics; 4-week budget.
Compute: generalist 20-60 GPU-h [estimate] + ~0.3-0.5 GPU-h/episode fine-tune [H].
Innovation: economic viability + flywheel; "train once, deploy per video".
First cheap falsifier (no multi-reference code): the sequential warm-start test of E.6. If a
same-task warm start does not save >= 50 % of steps at equal final error, a generalist
across tasks is unlikely to pay off within 4 weeks.

### G. Embodiment as a per-episode design variable
Options registered in the pinned stack [V]: floating `sharpa_hands` (wrist kp 25, tau 45),
shipped stiff variant (`residual_hand_pose_stiff`: kp 1200, tau 2000), primitive-collision
Sharpa, `dexmate_sharpa` (Vega arm+hand), `g1_dex3` (+SONIC base). FAQ: Sharpa default,
floating hands and fixed-base arm+hand welcome [V track3-requirements].
Why it might win: object fidelity is all that is scored; a stiff floating wrist removes
wrist-tracking error so hold-phase error reduces to grasp slip; arm/humanoid embodiments
add reach/joint limits and are expected to score lower [H]. Choosing per task family (e.g.
stiff for carry tasks, default for tool/contact-rich tasks) is cheap.
Risks: stiff wrist + imperfect reference -> large contact forces, ejections, knocked static
objects; organisers might view non-default stiffness as a physics change (it is a shipped
config; still ask). Custom embodiments outside the pinned commit cannot be evaluated by the
official evaluator [H from harness design].
Compute: +1 policy per variant tested.
Innovation: low for score variants; an arm+hand entry could be pitched as "deployable" but
costs score.
First cheap falsifier: 2 public episodes x {default, stiff} with the same reference and budget;
also physical replay at VOC 0 for both (minutes). Keep stiff only where it wins.

### H. GT-free checkpoint selection by rendering the rollout against the video
Idea: our reference can be wrong; choose among genuine policy variants the one whose
*simulated* object best explains the raw video, not the one closest to our reference.
Steps: per episode train N variants (seeds, A vs baseline hands, G embodiments, B/C reference
variants) -> official evaluator -> render the rollout object poses into the 3 cameras with our
camera poses -> score vs masks / stereo depth / features -> pick best; flag episodes where all
variants are poor for re-reconstruction (automatic failure mining = flywheel).
Why it might win: directly reduces catastrophic episodes on all pose boards; legitimate
model selection without GT or leaderboard probing.
Risks: proxy may not correlate with mocap error (camera-pose error, occlusion, first-pose
alignment); prior experience in this workspace found GT-free proxies weak (rho <= 0.47 in an
unrelated SLAM project), so this must be validated, not assumed; N x training cost.
Compute: N x policy cost (N=2-4); rendering negligible.
First cheap falsifier: on public episodes, compute Spearman rho between the video-consistency
score and true ADD-AUC over >= 10 checkpoints/variants. Kill if rho < 0.5.

### I. Cross-episode object library (CD-O meshes, spoon sim mesh, frame conventions)
Idea: the same 11 physical objects recur across 40 episodes; reconstruct each *identity*
once from all videos instead of once per episode.
Steps:
1. Identity association per episode (task/object list is given per episode [V kit object
   list]; appearance check as a guard).
2. Per-episode partial models: stereo depth fused in the object frame using tracked poses
   (BundleSDF-style object-centric fusion), masks from video segmentation.
3. Cross-episode Sim(3) registration and fusion of partials; generative completion
   (SAM 3D Objects / similar) only for never-seen regions; watertight + convex decomposition
   for sim; mass from volume x density class.
4. Canonicalise each mesh to the inferred organiser scan convention (origin/axes rule learned
   from the 10 public scans) - matters for the pose boards, not for CD-O.
5. Emit the identity mesh for every episode-object pair (CD-O), and use it as the sim asset.
Why it might win: CD-O is Sim(3)-registered Chamfer, so shape completeness dominates; many
episodes expose all sides; the spoon gets a real mesh from 10 eval episodes instead of a
single-view hallucination; better sim geometry -> better contact physics for the spoon.
Risks: whether pooling other episodes' videos (no GT) for one episode's mesh is acceptable
is a rules question [ask]; association errors; thin spoon depth is noisy.
Compute: ~10-20 GPU-min per identity [estimate].
Innovation: flywheel ("every new video improves the asset library"); economic (assets built
once, reused).
First cheap falsifier: for 2 scanned public objects, Chamfer(scan, single-episode recon) vs
Chamfer(scan, multi-episode fused recon) using public episodes only. Kill if < ~20 % gain.

### J. World-model / VLA routes - fit with the checkpoint constraint
- As the scored policy: does not fit. The evaluator accepts only the FlashSAC or PPO typed
  training targets and validates the saved policy input description [V harness.py,
  training/README]; the policy observes FlashCHORD state, not pixels. A VLA cannot be the
  checkpoint.
- As a distillation teacher: possible in principle (any teacher acting in the same sim ->
  BC/DAgger into the FlashSAC/PPO actor), but no off-the-shelf teacher exists for Sharpa in
  Newton; F and K are the realistic forms of this.
- As perception: video-generative "amodal completion" of occluded objects can hallucinate
  and cannot be validated without GT -> not recommended for scored trajectories.
- As planning/annotation aid: a VLM keyframe script (who grasps what, when) is cheap and
  directly useful to A (DexImit does this with Qwen3-VL [V]).
- As data generator for F: world-model videos -> 4D -> extra training references
  (DreamGen/Dex4D-style [U]) - flywheel story, weak score lever in 4 weeks.
Verdict [H]: use a VLM only for interaction scheduling in A; mention generated references as
future flywheel in the report; do not spend core GPU-h here.

### K. Sample-then-distill: executed trajectory first, minimal RL second
Idea: evaluation is deterministic (reset to frame 0, seed 42, deterministic actions, VOC 0
[V harness.py]; 1 world per episode per the kit command [V in [track3-requirements.md](../track3-requirements.md); the
repo's default `evaluation/flash_sac.yaml` says 4096]); a policy only has to reproduce *one* successful executed trajectory robustly. Find that
trajectory by sampling-based optimisation (C) and distil it into the FlashSAC actor
(supervised regression on (observation, action) pairs from the executed rollout and noisy
perturbations around it), then run a short RL fine-tune (VOC already 0) for robustness.
Why it might win: GPU-h per episode could fall several-fold vs 250M-step RL [H]; the policy
starts from an executed solution instead of exploring; good economics story.
Risks: contact-rich sim is chaotic -> a memorised open-loop solution may diverge under
tiny numeric differences (different GPU/driver at reproduction) -> must check bitwise or
near-bitwise determinism of the pinned evaluator across two GPU types; writing a valid
FlashSAC checkpoint from BC needs custom training code (allowed; eval code untouched); risk
that the panel sees it as over-fitting to deterministic evaluation (it is still a closed-loop
policy in the official format - state this openly).
Compute: sampling ~0.1-0.5 GPU-h + BC minutes + short RL [estimate].
Innovation: challenges "each video needs hours of RL"; complexity + cost reduction.
First cheap falsifier: (i) run the official evaluator twice on two GPU models with one
baseline checkpoint and diff the trajectories (determinism); (ii) on one public episode,
BC-distil a physical-replay trajectory into the actor and evaluate before any RL.

## 3. Comparison (all entries [H]; "lever" = expected leaderboard effect if the falsifier passes)

| ID | Main boards | Lever | Eng. effort | Extra GPU-h | Innovation | Main risk | Falsifier cost |
|---|---|---|---|---|---|---|---|
| A object-first grasps | SP-SR, MP-SR, AUC, MPPE | high | ~1.5 person-wk | low | high | tool/contact-rich tasks | replay ~0 + 6 policies |
| B batch multi-cam + priors | all pose boards, slot-0 anchor | high | ~2 person-wk | low | low-med | small camera baseline | ~0 (public GT) |
| C physics-in-loop | SP-SR, MP-SR | med-high, conditional | 2-3 person-wk | med | high | sim-vs-real bias, effort | analysis only |
| D 4D point tracks | spoon episodes (10/20) | med-high there | ~1 person-wk | low | med | thin object, drift | small |
| E same-room flywheel | all | high | ~1.5 person-wk | 40-60 (doubles as validation) | high (flywheel) | overfitting 20 eps | small |
| F generalist + fine-tune | cost, robustness | low-med | 3+ person-wk | 20-60 | med-high | multi-ref engineering | ~4 GPU-h |
| G embodiment choice | SP-SR | low-med | days | +1 policy/variant | low | stiff = ejections | ~4 GPU-h |
| H render-rollout selection | all (catastrophes) | med | ~0.5 person-wk | N x policies | med | proxy may not correlate | analysis |
| I object library | CD-O, spoon sim asset | high for CD-O | ~1 person-wk | low | med (flywheel) | rules on pooling | small |
| J VLA / world model | none directly | low | - | - | buzzword risk | does not fit checkpoint | - |
| K sample-then-distill | cost | low-med | ~1.5 person-wk | low | high | sim nondeterminism | ~1 GPU-h |

Suggested portfolio for 4 people x 4 weeks (freeze 2026-11-04 17:00 EST) [H]:
- Week 1: Exp 0 + VOC-0 replay probe; scan frame-convention check (public meshes);
  evaluator determinism check (K-i); B static-fraction analysis; D on an elongated scanned
  object; A grasp-synthesis prototype; local kit-scorer harness.
- Week 2: A-vs-baseline-hands decision; B batch layer; E tracker fine-tune + warm-start test;
  I fused meshes for 2 scanned objects (Chamfer vs scan).
- Week 3: full 20-episode v1 run and first submissions; H proxy validation on public
  episodes; C-lite (re-optimise only failing windows); G per task family.
- Week 4: failure mining via H, final picks, single-command reproducibility, report.
Owners (proposal): P1 perception (B, D, spoon frame), P2 transfer (A, G, C-lite, K),
P3 infra/eval/flywheel (scorer harness, E, H, GPU queue), P4 meshes + write-up (I, CD-O,
innovation narrative, organiser liaison).

Innovation narrative that the evidence could support [H]: "Object-first, physics-verified
video-to-policy" - no 3D human hand model in the loop (A), every reference checked in the
evaluator's own physics before RL (C/replay), training cost cut by warm starts / distillation
(E/K), assets and priors that improve with each recorded episode (E/I), and a GT-free self-
check that mines failures (H). Report GPU-h and wall-clock per episode next to the
baseline's (~2 GPU-h/policy [V CHORD] + 10-15 min reconstruction [V repo README via
track3-requirements]).

## 4. Questions to add to the organiser email
1. May public scanned meshes/URDFs be used as tracking priors and sim assets for the five
   pose boards (CD-O already excluded)?
2. May one episode's pipeline use other episodes' *videos* (no GT) for meshes/room priors (I, E)?
3. Are shipped non-default configs (`residual_hand_pose_stiff`, other registered
   embodiments) acceptable, and are scene fields (`contact_friction`, damping) considered
   physics changes?
4. Does the hidden wooden-spoon scan follow the same frame convention as the public scans?
5. Are NC-licensed dependencies (SPIDER, GoTrack: CC BY-NC 4.0) acceptable given the
   Apache-2.0 release requirement?
6. Will reproduction re-run the evaluator on different GPUs (affects K)?

## 5. Not covered here
Perception model choice details -> [03-lit-perception.md](03-lit-perception.md); transfer literature depth ->
[04-lit-transfer.md](04-lit-transfer.md) (other owners). Nothing in this note was run; all lever/compute numbers
marked [estimate]/[H] are untested.


---
[← Index](../README.md) · [Summary](../00-summary.md) · [← 04](04-lit-transfer.md) · [06 →](06-timing-audit.md)
