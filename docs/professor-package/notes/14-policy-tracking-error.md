[← Index](../README.md) · [Summary](../00-summary.md) · [← 13](13-spoon.md) · [15 →](15-eval-video-survey.md)

# 14 - Policy tracking error (e_track) of FlashCHORD Sharpa and its training budget

Status: COMPLETE (stages A, B, C on 2026-10-05; B and C re-run 2026-10-06 after outages, sections H and I). Agent id 14.
Research/analysis only; no RL runs, no GPU. Work dir: /Users/aebatirel/Documents/Code/v2d-research/work/14/ (re-run scripts in c2/).
Labels: [V] verified from primary source/code, [E] estimate, [H] hypothesis.

## Summary (final, rewritten 2026-10-06; read this first; details in sections A-I and the stage verdicts)
1. [V] Nobody has published an e_track number for the FlashCHORD Sharpa port, and no trained actor is released (upstream head
   60dd1aabae, 2026-10-05: flash_chord unchanged since the evaluator pin 8c778f90). e_track is nevertheless free to observe per episode:
   every evaluator run writes metrics_output (AUC / SP-SR / MP-SR / MPPE / RPE of the sim vs OUR reference, leaderboard thresholds, no
   frame-0 alignment). Perception error is observable only on the 20 public GT episodes.
2. [E] e_track for the EVAL set (scored vs the reference tracked, AUC / SP-SR / MP-SR), with note 15's task classes priced in:
   real speed + default soft wrist, 1 seed 0.70-0.79 / 0.69-0.90 / 0.24-0.54; best-of-3 0.74-0.81 / 0.76-0.93 / 0.39-0.67; wrist
   headroom fixed + best-of-3 0.78-0.87 / 0.77-0.93 / 0.42-0.67 (0.86-0.92 / 0.86-0.96 / 0.65-0.83 if recipe fixes halve the structural
   failures). Class-blind public-like tasks (verifier-corrected): 1 seed 0.75-0.84 / 0.78-0.95 / 0.55-0.81, headroom fixed + best-of-3
   0.94-0.97 / 0.96-1.0 / 0.92-1.0. motion_speed 0.5 packed as-is: 0.415 / 0.30 / 0 regardless of tracking [V computed; disqualifying].
3. [E] Clean vs noisy references: a noisy reference costs twice, directly and by raising the policy's failure rate p. Track 2 implies
   +0.10-0.17 on p for bounded 1.9 cm / 21 deg noise; CHORD Appendix C (one monocular-video task, AUC 0.647 vs 0.918 on mocap) implies
   +0.35-0.5. Composed with a middle-quality perception reference, scored vs GT on the eval set (real speed, 1 seed): 0.61-0.67 /
   0.77-0.85 / 0.09-0.20 with the Track 2 increase, 0.58-0.64 / 0.72-0.80 / 0.04-0.14 with the Appendix C increase.
4. [V computed + H] Real speed vs half speed: under the default wrist (kp 25 N/m, 0.2 m per-axis clip) the 0.3 kg placeholder object
   weight uses 11.8 cm of the clip, and 19-25/27 carried public tracks saturate (4.6-6.9 % of moving frames, mostly z) at motion_speed 1.0
   vs 0-1/27 at 0.5. Half speed cannot be submitted, so the lever is wrist headroom: the port ships a stiff variant as Hydra config
   (embodiment=sharpa_hands_stiff, kp 6000 N/m; action=residual_hand_pose_stiff), documented only for collision-free replay at 200 Hz.
   The FAQ welcomes other embodiments. [H] An intermediate gain (kp ~200-600) is the likelier sweet spot.
5. [E] Where the error mass is (eval set, real speed, 1 seed): AUC loss ~0.26 = continuous soft-wrist lag ~40 % + discrete failures on the
   8 "likely fails" episodes ~32 % + 8 partial episodes ~18 % + 4 plain grasp-and-carry episodes ~8 %. MP-SR loss is ~90 % discrete failures
   on hard tasks (hand-overs, flips, frame-0 in-hand grasp, plank pivots, spoon twirls, tool contact, hull-overlapping frame-0 states).
   These are mostly seed-independent: best-of-3 recovers ~0.04 AUC on the eval set, so recipe changes matter more than seed count.
6. [E] Perception vs policy: for AUC and MP-SR, e_track on the eval set (-0.21..-0.30 AUC, -0.46..-0.76 MP-SR vs perfect
   tracking) is as large as or LARGER than a middle-quality perception error alone (PERC_M: -0.20 / -0.22), so policy work is first-order. For SP-SR, e_track alone cannot go below ~0.58 even if
   every episode fails, while the Track 3 leader has 0.35 (0.649 AUC, 0.25 MP-SR). So SP-SR at the frontier is set by perception and
   convention rotation terms (spoon roll bit, cup spin; notes 07/11/12/13) [H for the leader's actual cause].
7. [V code/doc] Determinism: the actor (mean action, eval-mode batch norm) and reset (seed 42, frame 0, VOC 0, world_count 1) are
   deterministic. Newton/MuJoCo-Warp physics is not configured to be, and MJWarp documents no global determinism. The scorer never re-runs,
   but the FAQ records the checkpoint hash "for later validation", so a re-run that flips a marginal grasp is a validation risk.
   Keep the first eval per checkpoint, select over trained seeds rather than evaluator re-rolls, and log the hardware.
8. [V/E] Budget: the recipe is 250M transitions x 4,096 worlds with >= 46,000 MiB free GPU memory, and VOC switches off only after 122.9M.
   The paper reports ~2 h per sequence per seed (L40S), but hard tasks need longer. There is no budget or seed rule (FAQ). Plan [E]:
   40-80 GPU-h for 1 seed x 20 eps, ~80-170 GPU-h with one recipe variant for the 16 hard eps plus adaptive reseeds.
9. Cheapest decisive experiment (section I verdict item 6): E-1, score our perception output alone vs public GT (0 GPU), then E1, a smoke
   run (~1 GPU-h: throughput plus a 64-world determinism spread), then E2: one 250M seed on public twins 44/21/13/26/23/31 spanning the
   task classes (~12-24 GPU-h), with a second seed only on failures. Then E3: wrist-gain and noisy-reference variants (~10-20 GPU-h).
10. [V code] Correction kept from 2026-10-05: the port uses the paper's residual scale (wrist 0.05 m / 0.15 rad per unit, EMA 0.3); the Sharpa
   recipe adds a rational normalized mapping (residual.py:61-67) that stretches the actor's +-1 to the 0.2 m / 1.0 rad clip. The
   controllers differ in that mapping, the clip and the PD gains, not in the base scale (section F's "Paper action space" is superseded).

## Progress log
- 2026-10-05 start: read notes 10 (synthesis), 06 (timing), 04 §1 (CHORD), 01 C.8-C.10, 05 §0.
- 2026-10-05 +15 min: repo pin 8c778f90 read (README, docs/media manifest, V2D_INTEGRATION, configs,
  evaluation harness/tests); live Track 2 leaderboard read. Findings below (section A, C).
- 2026-10-05 Stage A done (section E), Stage B done (section F), Stage C done (section G + Stage C verdict); verifier pass appended.
- 2026-10-06 Stage B re-run (section H): paper gaps filled (Appendix C video AUC 0.647, force-closure option, budget
  qualifier, Sec. 4.3), leaderboard re-read (new Track 2 FF rows, first Track 3 rows).
- 2026-10-06 Stage C re-run (section I): upstream head + FAQ checked, eval-set e_track prior with note-15 classes
  (work/14/c2/eval_prior.py), stiff-wrist config found, leader reconciliation, new experiment ladder. Summary rewritten.

## A. NVIDIA repo at 8c778f90: what release validation actually publishes [V]
- "EVT-07" appears in exactly two files: flash_chord/README.md ("Full training: 48 GiB GPU with
  >=46,000 MiB free, as validated in EVT-07") and docs/media/README.md ("Policy GIFs: deterministic
  rollouts from frame 0 using the terminal EVT-07 actors"). No EVT-07 metrics JSON, report, log or
  wall-clock is in the tree (searched all 4,842 paths + GitHub code search). Only other EVT is
  reconstruction evt04_airplane expected outputs.
- docs/media/manifest.json: Sharpa tissue-box terminal actor (250,003,456 steps, sha256 8d27a10d...)
  rollout = 518 sim steps = 25.9 s at 20 Hz under motion_speed 0.5; kinematic reference playback
  1,296 frames / 25.92 s. So the one validated Sharpa demo is ~13 s of source motion played at half
  speed. G1 snack-box actor 349,999,104 steps; rollout 800 steps = 16.0 s at 50 Hz.
  `final_reset_pose_max_difference: 0.0` for both (viewer reset reproduces frame-0 pose exactly).
- V2D_INTEGRATION.md "Verification at import": 613 passed / 55 skipped unit tests; scene-build gates
  only. Explicitly: "These are import/scene gates, not the final training-reproduction gate. The
  release cohort still requires bounded train/save/resume/evaluate smokes and the signed-off full
  Sharpa, Dexmate/Sharpa, and G1 training runs." => NO published tracking-accuracy number for the
  FlashCHORD port on any reference. [V]
- No training wall-clock statement anywhere in flash_chord docs. Only hardware: 48 GiB GPU.
  The (old Isaac-Lab lane) Vega tissue-box PPO model card: 4,096 envs, 20,000 iters (~1.97e9
  transitions), one L40, seed 42; training-reset evaluation 117/128 = 91.4 % "sequence survival",
  explicitly not task success. Different lane (Isaac Lab PPO, Vega arm), not FlashCHORD Sharpa.
- docs/configuration.md: sharpa_flash_sac = "4,096 worlds, validated 250M-step schedule"; curriculum
  "preserves the validated 10-stage reduction in VOC assistance"; final stage from 200,007,680 steps
  with 0.5 first-frame resets.
- Evaluation determinism (code): actor evaluated with running batch-norm stats (training=False), so the
  action is a pure function of the observation, independent of world_count
  (tests/training/flash_sac/test_flash_sac_evaluation.py:63-97, :100-133); reset seed forced 42
  (harness.py:237); explicit reset to frame 0; VOC 0. Remaining nondeterminism = GPU physics
  (MuJoCo-Warp contact solve) and fp16 actor math (training compute_dtype float16) across GPU types.
  WE run the evaluator and upload the trajectory; organisers can only audit by re-running.
- 2026-10-05 +30 min: CHORD v2 HTML + figures 4/6/9 read; Track 2 data README read. Sections B, C below.

## B. CHORD paper (arXiv 2607.00033v2, HTML) - numbers that bound e_track [V unless marked]
- Table 1 (60 hand-picked tasks: 17 rigid/24 articulated/19 multi-object, 3 seeds, 4,096 envs
  per seed; clean mocap MANO references; Isaac Lab implementation, NOT the FlashCHORD Newton port):
  CHORD AUC 0.918+-0.018, SP-SR 0.926, MP-SR 0.894, RPE 5.14 cm, MPPE 5.11 cm.
- Table 2 ablation (same 60): position-only contact 0.862/0.856/0.780, MPPE 7.63; no contact
  0.774/0.756/0.612, MPPE 14.38.
- Fig. 4 (1,831 tasks, success = completion ratio >0.7 under 15 cm / 40 deg terminations, LOOSER
  than SP-SR): HOT3D-1obj 0.772+-0.012 (n=1131), HOT3D-2obj 0.753 (n=150), OakInk2-1obj 0.786,
  OakInk2-2obj 0.746, ARCTIC 0.814, TACO 0.935. HOT3D = egocentric tabletop with mocap objects =
  closest analogue of Track 3; ~23-25 % of its clips fail even the loose criterion on CLEAN refs.
- Fig. 6 (per-sequence AUC vs horizon, up to 5 seeds): most CHORD sequences 0.85-0.98, but a
  heavy tail: ~3 of ~20 below 0.4 (0.04, 0.16, 0.39) and several with seed std 0.2-0.35
  (e.g. 0.87 with error bar 0.41-1.0; 0.65 with 0.43-0.87; 0.39 with 0.04-0.74). [V read off figure]
  => per-episode seed variance is large; multi-seed selection matters.
- Fig. 9 / Table 4 noise study: random-walk noise on WRIST pose and CONTACTS only (object reference
  clean). Tiers 1..6 = wrist 10..60 mm, 5..30 deg; contact 5..30 mm, 5..30 deg. AUC read off the
  figure: hand-noise-only 0.60, 0.53, 0.57, 0.49, 0.52, 0.54; hand+contact 0.61, 0.60, 0.58, 0.53,
  0.33, 0.47; hand+contact w/ force-closure 0.52, 0.52, 0.52, 0.57, 0.50, 0.50; shaded bands
  +-0.07..0.2. No tier-0 (clean) point and task set unstated, so the 0.92 -> ~0.6 gap cannot be
  attributed to noise alone [H: probably a harder task subset]. Robust reading: within the noisy
  regime the curve is nearly flat from 10 mm to 60 mm wrist noise -> hand-reference noise is NOT the
  dominant term once contacts are reasonable; contact noise >= 25 mm / 25 deg collapses it.
- OBJECT-reference noise (our dominant Track 3 perception error) was never studied. [V]
- Training cost: "FlashSAC with 2,048 environments ... single L40S GPU in ~2 hours" per sequence;
  DexMachina/ManipTrans/SPIDER ~10/20/4 h. The released Sharpa recipe uses 4,096 worlds and 250M
  steps; no wall-clock is published for it. [V]
- Paper evaluation for Tables 1-3 is over 4,096 envs per seed (implies sampled starts, not the
  challenge's single frame-0 rollout) [E: not stated explicitly].
- Stated limitation: "effective contact guidance requires relatively clean human demonstrations".

## C. Track 2 public baseline = direct measurement of policy-only error on clean references [V]
Live leaderboard JSON (generated 2026-10-04T21:18Z; Track 3 has no rows yet):
| Track 2 tier | team | AUC | SP-SR | MP-SR | MPPE cm |
|---|---|---|---|---|---|
| T1 clean MV caption | CHORD Baseline | 0.510 | 0.700 (21/30) | 0.200 (6/30) | 17.74 |
| T1 | Xueyi Wang (FF) | 0.527 | 0.700 | 0.500 (15/30) | 12.48 |
| T2 synthetic noise | CHORD Baseline | 0.374 | 0.533 (16/30) | 0.067 (2/30) | 20.52 |
| T3 CARI4D recon | CHORD Baseline | 0.002 | 0.0 | 0.0 | 70.17 |
- Track 2 = 30 single-object episodes, 440-1,003 frames at 30 fps nominal (15-33 s), G1+Dex3
  whole-body loco-manipulation of LARGE objects (desk, chair, luggage pushed with a foot, stool
  tipping, walking with sign). Scored against the clean trajectory; the packer applies one rigid
  transform between evaluator reference and the tier input. Tier 1 input = the scored trajectory,
  so Tier-1 error is (almost) pure retarget+policy error: AUC 0.51 / MP-SR 0.20 for the official
  G1 baseline. Tier 1->2 (synthetic jitter/dropout/contact errors from Track 1 distributions)
  costs -0.14 AUC, -0.17 SP-SR, -0.13 MP-SR. Tier 3 (real monocular recon) -> zero.
- Caveats for transfer to Track 3: G1 whole-body (balance, walking, 3-finger hand) is much harder
  than floating Sharpa on a table; G1 recipe plays 30 fps data at 50 Hz with source_frame_playback
  (1.67x real speed, note 06); big objects make ADD rotation-dominated. So Track 2 Tier 1 is a
  PESSIMISTIC bound for floating-Sharpa e_track, but it proves the official recipe does not
  saturate the metrics even with perfect input. FF's MP-SR 0.5 vs 0.2 shows policy-side work alone
  moves MP-SR by +0.3 on clean input.
- 2026-10-05 +50 min: controller constants read (section D). Next: GT kinematics + policy-error
  models scored with the official Track 3 metric functions (work/14/*.py).

## D. Why real-speed playback is harder: the soft floating-wrist controller [V code, H consequence]
- sharpa_hands.py:56-60: wrist prismatic x/y/z PD kp=25 N/m, kd=6 N s/m, effort 45 N; ball wrist
  effort-PD kp=25 Nm/rad, passive damping 6 Nm s/rad. Hand gravity-compensated; hand mass from
  URDF = 1.243 kg (sum of 33 links, right_sharpawave.urdf). Comment at :67-70: the stiff variant
  exists because the default wrist "lag[s] under the soft default gains".
- control.py:5-7: position targets only; no target velocity / feed-forward (damping always opposes
  motion). hand_pose.py:273-298 target = reference wrist + filtered residual; residual.py:97-100
  EMA 0.3 then clamp to wrist_pos_clip 0.2 m / wrist_ori_clip 1.0 rad (rational mapping lets the
  policy reach the full clip).
- Observation gives only the current-step command (no multi-frame look-ahead) [V observation.py].
- Consequence [H, first-order physics]: to follow the reference the policy must hold a residual
  offset of ~ (kd v + m a + m_obj g)/kp. Object weight alone (URDF 0.3 kg, not compensated) costs
  2.94 N = 11.8 cm of the 20 cm clip; damping costs 0.24 s x v (12 cm at 0.5 m/s at real speed, 6 cm
  at motion_speed 0.5); rotation damping costs 0.24 s x omega (0.84 rad at 200 deg/s vs the 1.0 rad
  clip). Real-speed playback (G1 timing gate) therefore pushes the default action space toward
  saturation on fast lifts/flips; half speed halves the velocity terms and quarters inertial ones.

## E. Stage A (resumed 2026-10-05, after outage): thresholds and built-in metric outputs [V code @8c778f90]
- configs/termination/tracking.yaml (TRAINING terminations): object_position 0.10 m, object_orientation
  0.50 rad, wrist_position 0.15 m, wrist_orientation disabled, reference_end on. These are exactly the
  SP-SR thresholds, so training already pushes every frame inside the SP-SR tube; it applies them PER
  FRAME (stricter than SP-SR, which uses the per-episode MEAN error).
- evaluation/metrics.py chord_success() raises if any world terminated: "evaluation rollout must disable
  the tracking-failure termination terms" -> evaluation always rolls the full reference, no early stop.
- evaluation/metrics.py implements the same metric family as the challenge scorer, against the policy's
  OWN reference: ADD AUC over 0.01..0.09 m (500 mesh vertices, seed 0), SPIDER SR (mean pos <=0.10 m and
  mean geodesic <=0.5 rad, "time-mean subtraction is omitted"), ManipTrans SR (<3 cm and <30 deg per
  object, mean over time), MPPE (six +-5 cm body keypoints, max over bodies, mean), RPE (pairwise root
  error in first object's frame), plus CHORD success (completion with termination causes). NO rigid
  alignment (_aligned_poses only validates shapes). Quaternions are xyzw here (challenge parquet is wxyz).
  => e_track is directly measurable for free: evaluate_policy with `metrics_output=<json>` +
  `object_trajectories_output` (configs/evaluation/flash_sac.yaml) scores sim vs our reference with the
  same thresholds the leaderboard uses (minus the leaderboard's frame-0 rigid alignment). [V]
- Curriculum tracking_250m_mixed_reset.yaml: 11 stages ending at 19.66M, 34.41M, 49.15M, 63.90M, 78.64M,
  93.39M, 108.13M, 122.88M, 137.63M, 200.01M, 250.00M transitions; VOC scale 1.0, 0.75, 0.5, 0.25, 0.1,
  0.05, 0.025, 0.01, 0, 0, 0(+0.5 frame-0 resets). So VOC (virtual object controller assistance) is fully
  off only after ~123M steps (~49 % of the budget); the last ~127M steps are unassisted. Reward weights
  constant: object_keypoints 20, hand_keypoints 0.25, hand_joint_pos 0.25, missed_contact -1,
  unintended_contact -10, termination -100. [V; stage-boundary reading E: thresholds read as stage ends]
- [V] lifecycle/curriculum.py stage_index = min(bisect_right(thresholds, step), n-1): confirms the stage
  reading above (VOC = 0 from 122.88M; frame-0 mixed resets from 200.0M; 250M = end). The FlashSAC
  schedule descends from W&B run `sizirwre` (reference_curriculum(): thresholds 2000..15500 learner
  iterations, object_keypoints weight ramped 0 -> 20); the Sharpa FlashSAC recipe instead keeps weight 20
  throughout. Steps are cumulative control-step transitions (training/README.md): 250M / 4,096 worlds =
  61,036 control steps per world = 3,052 s of 20 Hz sim time per world.
- [V] Evaluation harness (harness.py:168-250) recovers the training thresholds, then sets them to 1e6 for
  the rollout, and scores "CHORD success" = reaching reference end without ANY frame crossing
  10 cm / 0.5 rad (object) or 15 cm (wrist). object_trajectories export (schema
  flash_chord_object_trajectories_v1, xyzw) stores achieved AND reference per step/world/body plus
  checkpoint/eval-script/eval-code sha256 and episode index (test_object_trajectory_export.py) - the
  provenance chain the organisers can audit.
- [V] No trained FlashCHORD Sharpa actor is released in the tree (only docs/media GIFs + checkpoint sha256);
  the only shipped policy weights are SONIC (G1 whole-body) and the old Isaac-Lab Vega tissue-box ONNX.
  So e_track cannot be measured without training our own actor.
- [V] CHORD project page (docs/chord/index.html @pin) repeats Table 1 and "82.12 % average success over
  1,831 tasks", 90.77 % whole-body; no training-time or per-step-throughput numbers.
- [V kit] The submission kit's evaluator configs are byte-identical to the pin (evaluation/flash_sac.yaml
  diff empty). kit evaluate_policy.yaml: "The environment, task, embodiment, and strategy selections are
  rebuilt from the checkpoint's own resolved config" -> whatever training config we use (embodiment
  variant, motion_speed, termination, curriculum) is what evaluation replays; only evaluation surfaces are
  fixed. examples/run_policy_evaluation.py runs world_count=1 (config/tracks.json worlds_per_episode = 1),
  reset_mode explicit, and ALWAYS writes `evaluation.metrics_output=<results>/episode_XXXXXX.json`
  beside the trajectory parquet -> every submission rollout already yields a self-scored e_track
  (sim vs our reference, same thresholds, no frame-0 alignment). Track 3 README: "train a policy for each
  scored episode"; skill: "one policy per sequence". No training-budget, seed-count or wall-clock rule.
  [H] Whether non-default embodiment/controller variants (e.g. the stiff wrist) are allowed is a RULES
  question, not a code limit; our constraint "no evaluator/physics changes" must be checked against it.
- [V] No metrics JSON / evaluation output is committed anywhere in robotic_grounding at the pin.

### Stage A verdict (what the repo does and does not tell us about e_track)
1. [V] NVIDIA publishes NO tracking-accuracy number for the FlashCHORD Sharpa port (EVT-07 = a memory and
   media gate; V2D_INTEGRATION calls full training reproduction still pending). The only quantitative
   e_track evidence is (a) CHORD paper Table 1 / Fig. 4 / Fig. 6 (Isaac Lab, clean mocap, 2,048-4,096
   envs, ~2 h L40S) and (b) the Track 2 Tier-1 leaderboard (G1, AUC 0.51 / MP-SR 0.20 on clean input).
2. [V] Training budget statements: 250M transitions, 4,096 worlds, 48 GiB GPU (>=46,000 MiB free);
   VOC assistance off after 122.9M; no wall-clock. Paper: ~2 h/sequence on one L40S with 2,048 envs
   (implementation and step count unstated). Old Vega PPO lane: 20,000 iters x 4,096 x 24 ~ 1.97e9
   transitions on one L40 (no time stated).
3. [V] The code gives a FREE, exact e_track measurement: training terminations equal the SP-SR thresholds,
   and evaluation writes metrics_output (AUC/SPIDER/ManipTrans/MPPE/RPE/CHORD success vs OUR reference).
   [E] Decomposition rule for later stages: leaderboard error ~= perception error (our ref vs GT)
   composed with e_track (sim vs our ref); e_track is observable per episode before submission,
   perception error only on the 20 public GT episodes.
- 2026-10-05 Stage A complete. Next (stage B, not started here): quantify e_track priors per episode.

## F. Stage B (2026-10-05): CHORD paper tables in full + Track 2 baseline re-read
Source: arXiv 2607.00033v2 HTML saved as work/14/chord_v2.html / chord_v2.txt (line refs below = chord_v2.txt).
- [V] Table 1 full (60 tasks = 17 rigid / 24 articulated / 19 multi-object, 3 seeds, Sharpa hands for ALL
  methods; baselines re-implemented by the CHORD authors on Sharpa, txt:901-924):
  | method | AUC | SP-SR | MP-SR | JPE deg | RPE cm | MPPE cm |
  |---|---|---|---|---|---|---|
  | DexMachina | 0.737+-0.053 | 0.690+-0.068 | 0.569+-0.097 | 13.10 | 9.92 | 15.88 |
  | ManipTrans | 0.506+-0.006 | 0.423+-0.011 | 0.323+-0.003 | 30.07 | 9.91 | 21.24 |
  | SPIDER | 0.804+-0.044 | 0.911+-0.039 | 0.789+-0.047 | 41.35 | 6.99 | 14.28 |
  | H2S2R | 0.730+-0.056 | 0.686+-0.068 | 0.569+-0.085 | 11.80 | 9.78 | 16.59 |
  | CHORD | 0.918+-0.018 | 0.926+-0.022 | 0.894+-0.032 | 4.34 | 5.14 | 5.11 |
  (+-) = std across the 3 training seeds of the 60-task mean, NOT per-task spread.
- [V] Table 2 ablation (same 60 tasks, 3 seeds, 4,096 envs/seed): Pos-Only 0.862/0.856/0.780, JPE 6.41,
  RPE 7.81, MPPE 7.63; No-Contact 0.774/0.756/0.612, JPE 9.81, RPE 10.91, MPPE 14.38. Object keypoint +
  hand tracking rewards alone (No-Contact) lose -0.14 AUC / -0.28 MP-SR vs full CHORD on clean refs.
- [V] Table 3 (G1+Dex3 whole-body, hand-only refs, 12 tasks, 4 seeds, 4,096 eval eps): CHORD SR 0.925+-0.104
  (rigid 0.994, articulated 0.914, multi 0.866) vs Position-Only 0.217+-0.333. SR here = CHORD completion
  criterion, not SP-SR.
- [V] Large-scale criterion (txt:~196): rollout success = no object termination at 15 cm / 40 deg; task
  success = completion ratio > 0.7. 82.12 % over 1,831 tasks. Real robot (Dexmate + 2 Sharpa, mocap state):
  5/5, 3/5, 5/5, 5/5, 5/5; box pick-place open-loop 6/7, closed-loop 7/7.
- [V] arXiv abs page fetched 2026-10-05 12:3x (work/14/abs_now.html): v2 (14 Aug 2026) is the latest version;
  v1 22 Jun 2026. All Stage B paper numbers are from v2.
- [V] Fig. 9 re-read (work/14/fig_noise_ablation.png, y = "AUC Score", x = noise level 1..6, Table 4 tiers:
  wrist 10/20/30/40/50/60 mm and 5..30 deg, contact pos 5..30 mm, contact normal 5..30 deg, random walk):
  values in section B confirmed. Band widths: hand-only +-0.07..0.2 (tier 2 band 0.34..0.73, tier 4
  0.31..0.66); hand+contact tier 5 band 0.15..0.50. No tier-0 point, no MP-SR/SP-SR for the noise study,
  task count not stated. Observation corruption is OFF in all large-scale experiments (txt:733).
- [V] Paper action space (Isaac Lab, txt:735-737): residual wrist pos scale 0.05 m, wrist ori 0.15 rad,
  finger 0.15 rad, EMA 0.3, "wrist force/torque tracking controller". FlashCHORD port instead clips the
  filtered residual at 0.2 m / 1.0 rad (section D) -> the paper's controller/action numbers do not transfer
  1:1 to the Newton/MuJoCo-Warp port; Table 1 is evidence for the METHOD, not for the port. [V code vs paper]
- [V] Paper reset (txt:745): episodes start at a RANDOM reference frame, VOC reset to 1.0 with a 20-step
  warm-up, fingers partially opened (interp 0..0.7). Large-scale eval reports completion ratio over
  rollouts; Tables 1-3 average over 4,096 eval envs per seed. Challenge scoring = ONE deterministic rollout
  from frame 0 (kit world_count=1) -> challenge e_track has no averaging over starts: an episode either
  holds the object or drops it [E].
- [V] Leaderboard re-fetched 2026-10-05 12:39 (work/14/lb_live3.json, md5 ff71223e... identical to the
  10:48 and 11:59 copies; generated_at 2026-10-04T21:18:19Z). History of leaderboard.json (17 commits,
  work/14/lbcommits.json; versions ee37b32993 / 62a82bd7c7 saved in work/14/lbhist/): Track 2 baseline
  rows appeared 2026-10-01T00:03Z and have NOT changed since (submission_count 1 each). Track 3 still has
  NO rows (metrics declared: AUC, SP-SR, MP-SR, RPE cm, MPPE cm, CD-O cm). Track 2 has no RPE column
  (single object). The leaderboard repo holds only aggregate rows; no per-episode breakdown is public.
- [V] Kit tracks/track_2/README.md: all 3 tiers are scored vs the CLEAN multi-view reference in its fixed
  world frame; packer maps evaluator poses through ONE rigid transform (evaluator reference -> tier input).
  "Tier 2 and Tier 3 evaluator metrics describe tracking against their policy input" -> Tier 1 leaderboard
  = pure retarget+policy error (e_track), Tier 2 = noise + e_track composed. Tier 2 dataset README (HF,
  saved work/14/t2/track_2_tier_2_synthetic_noise_README.md) gives NO noise magnitude; only "synthetically
  perturbed human and object trajectories" with timing/visibility/meshes preserved.
- 2026-10-05 12:45 next: download Track 2 tier-1 and tier-2 object poses (30 eps x 2, ~1 MB each) to
  work/14/t2/{tier1,tier2}/ and measure the injected object-pose noise, so the Tier 1 -> Tier 2 drop can be
  read as a dose-response point (noise-only score vs leaderboard Tier 2).
- [V computed] Track 2 Tier-2 injected noise measured (work/14/t2/t2_noise.py -> t2_noise.csv; 30 eps, tier-2 vs
  tier-1 object pose on visible frames, all 22,990 frames visible in both): object position error mean 1.87 cm
  (per-episode 1.02..2.67), HARD-CLIPPED at 3.00 cm (max = 3.000 in 23/30 eps); rotation mean 21.4 deg
  (11.6..29.0), clipped at 30.0 deg (p95 = 30 in 23/30); lag-1 autocorrelation 0.98..0.996 -> a slow
  bounded random walk (bias of the per-episode mean offset 0.5..2.4 cm), not white jitter. Human root
  translation noise mean 1.09 cm. Timing/visibility untouched.
- [V computed] "Perfect tracker of the noisy input" scored with the kit's Track 2 definitions (no frame-0
  alignment): SP-SR 29/30 = 0.967 (ep 17 traffic_cone fails on mean rot 28.95 deg = 0.505 rad > 0.5),
  MP-SR 30/30 = 1.0 (all eps under 3 cm and 30 deg, but rotation uses 39..97 % of the 30 deg budget),
  MPPE 2.36 cm. AUC needs the scorer's mesh vertices (not downloaded); proxy with the 6 MPPE keypoints
  (5 cm radius) = 0.82, a strong UPPER bound because Track 2 objects are large (desk, ladder, luggage).
- [E computed] Noise-only AUC proxy (work/14/t2/t2_auc_box.py; bboxes from GLB JSON headers via HTTP range,
  work/14/t2/glb_bbox.json; 500 surface points per object, seed 0): box-surface 0.319 (mean ADD 8.4 cm),
  inscribed-ellipsoid 0.399 (mean ADD 6.8 cm). The scorer's real mesh-vertex samples should fall between
  -> noise-only AUC ~0.32..0.40. Per object: small items (spray bottle, water bottle, basket, book) 0.72..0.83,
  furniture (round table, squeegee, trash can, chair, stool, luggage) 0.03..0.08: 21 deg of rotation noise on
  a 0.5..0.8 m object alone exceeds the 9 cm AUC ceiling.
- [E] Track 2 decomposition (leaderboard CHORD baseline vs noise-only):
  | metric | noise only (perfect tracker of tier-2 input) | policy only (Tier 1 LB) | composed (Tier 2 LB) |
  |---|---|---|---|
  | AUC | ~0.32..0.40 [E proxy] | 0.510 | 0.374 |
  | SP-SR | 0.967 | 0.700 | 0.533 |
  | MP-SR | 1.000 | 0.200 | 0.067 |
  | MPPE cm | 2.36 | 17.74 | 20.52 |
  Readings: (1) SP-SR and MP-SR compose BELOW the min of their two terms, AUC lands inside the noise-only proxy range; MPPE composes ~additively
  (2.4 + 17.7 = 20.1 vs 20.5). (2) SP-SR: noise alone fails 1/30 (and that one only on the 0.5 rad mean),
  yet the composed run fails 14/30 vs 9/30 on clean input -> 4-5 extra episodes (at most 1, ep 17, explained by noise alone) were lost by the POLICY
  because its reference was noisy (bounded 3 cm / 30 deg random walk) [H: physically inconsistent object
  reference -> drop/termination-like failure; cannot be confirmed without per-episode rows]. So reference
  noise inflates e_track, it does not merely add to it. (3) MP-SR is policy-dominated (0.20 on clean input);
  noise that uses 70 % of the 30 deg budget kills most of the rest. (4) AUC is scale-dominated: on large
  objects even 21 deg of reference rotation error saturates ADD; the Tier 2 AUC (0.374) is no better than
  a perfect tracker of the noisy input.
  Transfer to Track 3 [H]: Track 3 objects are tabletop-sized (comparable to the small Track 2 items with
  noise-only AUC 0.72..0.83), so the AUC is less rotation-dominated there; but the composition rule
  (scored rate <= min(perception-only, policy-only), and noisy references degrade the policy itself) should hold.
- [V] Selection effects that make the paper's clean-reference numbers OPTIMISTIC for Track 3 (txt:805-810):
  (a) HOT3D long recordings are cut into ATOMIC contact-window clips (contact = fingertip-object < 2 cm,
  gaps <= 15 frames bridged): ~294 recordings -> ~4,045 clips; the Fig. 4 HOT3D 0.77 is over such atomic
  clips, not over approach+grasp+move+release episodes like Track 3's ~13 s clips. (b) Every retarget passes
  a QC gate: rejected if hand-object or hand-hand capsule penetration > 2 cm in ANY frame, and if a 300-step
  Isaac replay fails. (c) Table 1's 60 tasks are "selected" from the 1,831 (criterion unstated).
  Track 3 references from video will not get (b) for free -> need our own penetration/replay QC [H].
- [V text / E] Hands in the paper are floating: reset "restores the right and left wrist root poses and
  velocities" (txt:745); retargeting is per-frame diff-IK on wrist pose + fingertips. Same floating-wrist
  topology as the FlashCHORD Sharpa port, but a different controller and action scaling (above).
- [V] No FlashSAC citation, no step count and no throughput in the paper; "~2 h per sequence, 2,048 envs,
  single L40S, lightweight MLPs, no per-task tuning" is the only budget statement. Prior methods: DexMachina
  ~10 h, ManipTrans ~20 h, SPIDER ~4 h per task. Neither the fetched repo files nor the challenge page give a
  FlashSAC steps/s figure (grep of work/14/repo and work/14/full; only an Isaac datagen skill mentions
  startup-bound wall-clock).
- [V] Challenge page (work/14/challenge_page.txt:59, 92): Track 3 "provide[s] an end-to-end baseline that
  participants may build upon"; evaluation "against a multi-view reconstruction (MV) baseline, representing
  an upper bound". No Track 3 baseline score is published (leaderboard has no Track 3 rows).

### Stage B verdict (2026-10-05): published e_track priors and budget
e_track prior ladder for one Sharpa policy tracking a Track 3-like reference, best to worst. All values are
policy-vs-own-reference unless marked.
| evidence | setting | AUC | SP-SR | MP-SR | MPPE cm | label |
|---|---|---|---|---|---|---|
| CHORD Table 1 | 60 selected tasks, clean mocap, Isaac Lab, 3 seeds x 4,096 eval envs | 0.918 | 0.926 | 0.894 | 5.11 | [V] |
| CHORD Table 2 Pos-Only | same, contact-position reward | 0.862 | 0.856 | 0.780 | 7.63 | [V] |
| CHORD Table 2 No-Contact | same, keypoint tracking only | 0.774 | 0.756 | 0.612 | 14.38 | [V] |
| CHORD Fig. 4 HOT3D 1-obj | 1,131 atomic clips, loose 15 cm/40 deg completion > 0.7 | - | ~0.77 (loose) | - | - | [V] |
| CHORD Fig. 9 noisy hand refs | wrist 10..60 mm / 5..30 deg random walk, object ref clean | 0.49..0.60 | - | - | - | [V fig] |
| Track 2 Tier 1 (G1+Dex3) | clean ref, official recipe, 1 rollout, scored vs clean | 0.510 | 0.700 | 0.200 | 17.74 | [V] pessimistic |
| Track 2 Tier 2 (G1+Dex3) | + 1.9 cm / 21 deg bounded random-walk object noise | 0.374 | 0.533 | 0.067 | 20.52 | [V] composed |
1. [E] For tabletop floating Sharpa on clean references, a realistic e_track prior is between the
   No-Contact and full-CHORD rows: AUC ~0.75..0.92, SP-SR ~0.75..0.93, MP-SR ~0.6..0.9. The paper rows are
   optimistic (selected tasks, QC-filtered retargets, atomic clips, sampled starts averaged over 4,096 envs,
   different controller), and the per-sequence seed spread is large (Fig. 6: std up to 0.2..0.35 AUC; ~3/20
   sequences below 0.4). With one deterministic frame-0 rollout per episode, a seed that drops the object
   scores ~0 for that episode, so best-of-N seed selection on the free metrics_output is worth budgeting [E].
2. [V+E] Reference noise is not additive. Track 2 shows that SP-SR and MP-SR compose below the min of the two
   terms, and that a bounded noise of 1.9 cm / 21 deg, which a perfect tracker would survive (SP-SR 0.97,
   MP-SR 1.0), still costs the policy 4-5 of 30 extra SP-SR failures. MP-SR is the most fragile: the policy
   alone got 0.20 on clean input, and noise using 70 % of the 30 deg budget cut it to 0.07. => For Track 3,
   MP-SR (< 3 cm and < 30 deg per object, mean) needs BOTH perception rotation error well under 30 deg and a
   policy that holds the object [E]. Only the CHORD Fig. 9 study and Track 2 Tier 2 are published dose
   points; neither injects noise into a Sharpa OBJECT reference.
3. [V] Training budget: paper ~2 h per sequence, 2,048 envs, one L40S (no step count). Released recipe:
   250M transitions, 4,096 worlds, >= 46,000 MiB free GPU memory, VOC off from 122.9M; no wall-clock.
   [E] At 262 frames (13.1 s), 250M transitions = 61k control steps per world = ~233 full-reference
   traversals per world at motion_speed 1 (~116 at 0.5). Taking the paper's 2 h as the per-seed cost:
   20 eval episodes x 1 seed ~ 40 L40S-hours; 3 seeds for best-of-3 ~ 120 h. The throughput of the
   Newton/MuJoCo-Warp port is unpublished, so this needs a timed smoke run before planning.
4. [E] Which term dominates. Track 2 Tier 1 shows the official policy alone gets MP-SR 0.20 and MPPE
   17.7 cm on clean input (G1), and a policy-side change moved MP-SR from 0.2 to 0.5 (FF team). So at the
   current state of the art the POLICY term is at least as large as a ~2 cm / 20 deg perception error for
   MP-SR and MPPE. AUC is perception/scale-dominated for large objects. The Track 3 split must be MEASURED:
   compare our metrics_output (e_track) with perception error on the 20 public GT episodes (stage C).
- 2026-10-05 Stage B complete. New artifacts: work/14/t2/{tier1,tier2}/ (60 parquets), t2_noise.py/.csv,
  glb_bbox.py/.json, t2_auc_box.py, t2/track_2_tier_2_synthetic_noise_README.md, t2/meshtree.json,
  lb_live3.json, lbcommits.json, lbhist/, lbtree.json, abs_now.html. Stage C not started.

## G. Stage C (2026-10-05, resumed after outage): e_track estimates for floating Sharpa
- Resume note: work/14/{common14.py, kin.py, kin.csv, kin.txt, track_err.py, track_err.txt} were produced
  before the outage (11:01-11:56) but never logged here. Re-read and checked: common14.metrics() calls the
  kit's own Track 3 functions (AUC._normalise_quaternions/_warp_to_reference_start/_object_add/_add_auc,
  SP-SR._spider_success, MP-SR._maniptrans_success, RPE, MPPE) with 500 area-weighted samples of the
  public scan per object (seed 0) -> numbers are valid [V code path; AUC vertices E: scorer may sample
  differently]. Public GT used for analysis only.
- [V computed, work/14/kin.txt] Wrist-residual demand of the DEFAULT soft floating wrist (kp 25 N/m,
  kd 6 N s/m, clip 0.2 m / 1.0 rad), object motion as a proxy for the holding wrist, 27 moving
  object-tracks in the 20 public episodes, 0.3 kg object assumed:
  | playback | median dpos95 | max dpos | objects with any pos saturation | frame-weighted pos sat. | rot sat. objs |
  |---|---|---|---|---|---|
  | motion_speed 1.0 (real 20 fps) | 0.217 m | 0.349 m | 24 / 27 | 7.9 % | 2 / 27 (ep 13 blue_cup, ep 26 white_pot) |
  | motion_speed 0.5 | 0.155 m | 0.200 m | 0 / 27 | 0.0 % | 0 / 27 |
  GT object speeds: median v95 0.33 m/s, max 0.56 m/s; median w95 112 deg/s, max 358 deg/s (ep 26
  white_pot flip). ~12 cm of the 20 cm clip is the static weight term of a 0.3 kg object (mg/kp).
  [H] At real speed the default action space saturates on fast lifts/flips -> lag/drop; at half speed it
  just fits. Mass sensitivity checked below.
- [V computed, work/14/track_err.txt] Score cost of policy-side error models applied to public GT and
  scored with the kit metrics (4 random reps per episode for stochastic models, 20 episodes):
  | policy error model (sim vs reference) | AUC | SP-SR | MP-SR | RPE cm | MPPE cm |
  |---|---|---|---|---|---|
  | first-order lag tau 0.05 / 0.10 / 0.20 / 0.30 s | 0.992 / 0.971 / 0.924 / 0.882 | 1 | 1 | 0.35..1.63 | 0.29..1.35 |
  | slot-0 settle at reset 2 deg + 2 mm (row 0 only) | 0.998 | 1 | 1 | 0 | 0.44 |
  | slot-0 settle 5 deg + 3 mm, persists until first motion | 0.956 | 1 | 0.97 | 0.18 | 0.99 |
  | slot-0 settle 10 deg + 5 mm, persists | 0.836 | 1 | 0.76 | 0.37 | 1.96 |
  | placement offset after last motion 1 cm/3 deg; 2/5; 4/10 | 0.986; 0.959; 0.903 | 1 | 1 | 0.27..1.05 | 0.23..0.91 |
  | in-hand jitter 3 mm / 1 deg | 0.999 | 1 | 1 | 0.54 | 0.49 |
  | most-moving object never moves (failed grasp) | 0.555 | 0.55 | 0.00 | 7.45 | 7.55 |
  | most-moving object freezes at 50 % of its motion (drop) | 0.688 | 0.85 | 0.00 | 5.65 | 5.23 |
  | most-moving object freezes at 80 % of its motion | 0.823 | 1.00 | 0.50 | 1.58 | 2.61 |
  | half-speed export packed as real speed (row f = source 0.508 f) | 0.415 | 0.30 | 0.00 | 11.10 | 9.48 |
  | POL_GOOD = tau 0.1 + 3 mm/1 deg + place 1 cm/3 deg + settle 1.5 deg | 0.966 | 1 | 1 | 0.98 | 0.88 |
  | POL_MID = tau 0.2 + 5 mm/2 deg + place 2 cm/5 deg + settle 3 deg | 0.900 | 1 | 1 | 1.73 | 1.51 |
  Composition with note-02-style perception models (perception applied first, policy model tracks it):
  | reference | alone | + POL_GOOD | + POL_MID |
  |---|---|---|---|
  | PERC_A careful stereo (anchor 0.5 cm/2 deg, jitter 0.5 cm/2 deg, drift 2 cm, scale 1 %) | 0.914 / MP 1.00 | 0.900 / 1.00 | 0.844 / 0.97 |
  | PERC_M middle (1 cm/3 deg, 0.8 cm/3 deg, 3 cm, 3 %) | 0.800 / 0.78 | 0.814 / 0.78 | 0.771 / 0.57 |
  | PERC_B rough mono (1.5 cm/5 deg, 1 cm/3 deg, 5 cm, 10 %) | 0.592 / 0.06 | 0.622 / 0.16 | 0.596 / 0.06 |
  (values AUC / MP-SR; SP-SR = 1.00 in all nine.) Readings [E]: (1) a policy that TRACKS (continuous
  small errors: lag, jitter, placement, settle) costs only 0.03..0.10 AUC and never breaks SP-SR; MP-SR
  survives unless slot-0 settle/tilt exceeds ~5 deg. (2) The error mass of e_track is in DISCRETE
  failures: one failed grasp or drop of the most-moving object costs 0.18..0.45 AUC, kills MP-SR and
  (never-moves) fails SP-SR in 45 % of episodes. (3) A small-error policy low-pass-filters reference
  jitter, so on noisy references it can slightly IMPROVE AUC (PERC_B 0.592 -> 0.622) - only while it
  keeps holding the object. (4) The single largest avoidable loss is a timing bug: a motion_speed 0.5
  rollout packed as if real-time scores AUC 0.415 / MP-SR 0 even with perfect tracking.
- [V code @8c778f90, fetched scene/builder.py, objects.py, setup.py into work/14/repo/src/flash_chord/scene/]
  build order in build_scene: embodiment.build(copy) FIRST (its gravity-compensation loop sets mujoco:gravcomp=1
  only for the bodies present then = hand bodies), THEN spawn_objects() adds objects via add_urdf(...,
  ignore_inertial_definitions=False). So objects are NOT gravity-compensated and keep their URDF mass. [V data]
  All 10 public Track 3 object URDFs (public/urdf/*_rigid.urdf) declare mass 0.3 kg -> the 0.3 kg in
  kin.py is the actual sim mass, and the static weight term mg/kp = 0.3*9.81/25 = 11.8 cm of the 20 cm
  wrist clip is real for every carried object under the default gains. task/default.yaml: motion_speed 0.5
  (default), source_frame_playback false; sim/rl.yaml fps 20, substeps 5 (100 Hz physics), MuJoCo implicitfast,
  pyramidal cone, 100 solver iterations. scene/eval.yaml: world_count 1, support on, CoACD decomposition,
  object scale fixed 1.0, contact friction 1.0, object free-joint damping 0.
- [V code] Evaluator determinism, physics side. FlashCHORD's evaluation "deterministic: true" (configs/evaluation
  /flash_sac.yaml:3) means the ACTOR MEAN action, not deterministic physics. runtime/sim.py (fetched @pin)
  build_solver() creates newton.solvers.SolverMuJoCo with solver/integrator/cone/iterations only; no
  warp.config.deterministic, no deterministic contact ordering; harness.py only fixes reset seed 42; the kit sets
  no physics/XLA determinism flag either (grep of kit and fetched repo files). [V doc] Isaac Lab 3.0 reproducibility page
  (https://isaac-sim.github.io/IsaacLab/release/3.0.0/source/features/reproducibility.html) and Warp docs
  (https://nvidia.github.io/warp/stable/user_guide/execution_and_performance/deterministic_execution.html):
  Newton physics is NOT deterministic by default; float atomics on CUDA reduce in arbitrary order; determinism
  needs explicit deterministic_mode run_to_run / gpu_to_gpu + warp.config.deterministic before env creation, costs
  speed/memory, and MJWarp needs sensors disabled. => [E] the default FlashCHORD rollout is bitwise reproducible
  only by luck; contact-rich grasps can amplify ulp differences into a held vs dropped object [H, magnitude unmeasured].
- [V kit] config/tracks.json comment: worlds_per_episode=1 because "every world resets to the same frame and runs a
  deterministic policy, so the cohort is expected to be redundant ... Raise this if that turns out to be wrong" ->
  the organisers ASSUME determinism and have not verified it. accepted_eval_script_sha256 / accepted_eval_code_sha256
  are empty lists (check disabled). The scorer never re-runs physics: it scores the uploaded trajectory and checks
  provenance only (GitHub commit URL; evaluator version allowlist; per-episode provenance columns constant
  within an episode = one set of weights per episode, AUC.py:338-372). Track 3 pack_submission checks only the
  row grid (no reference available), so the evaluator's metrics_output is our only pre-submission e_track number.
- [E] Consequences: (1) for submission, nondeterminism does not change the score of a trajectory we already have;
  (2) it makes A/B comparisons between our own policies noisy (need >=3 eval repeats or a 64-world spread test);
  (3) re-running the evaluator on the same checkpoint and keeping the best rollout would be cherry-picking a
  stochastic evaluation - treat as NOT allowed unless the organisers say otherwise; keep the first run per
  checkpoint and log all runs. Best-of-N over independently TRAINED seeds (different weights) is ordinary model
  selection on our own reference and needs no GT.
- [V code] Action headroom (configs/experiment/sharpa_flash_sac.yaml: action.input_mode normalized, normalized_mapping
  rational; action/residual_hand_pose.yaml: wrist_pos_scale 0.05, wrist_ori_scale 0.15, clip 0.2 m / 1.0 rad, ema 0.3,
  filtered = 0.3*prev + 0.7*value*scale; residual.py:61-67 input_scale = clip / ((1-ema)*scale) = 5.71 for position)
  -> the full 0.2 m clip IS reachable at |a| = 1. [E arithmetic] Holding a 0.3 kg object (11.8 cm steady offset) needs a
  steady normalized wrist-z action of ~0.80 (rational map n / ((1-n) + n/5.71) = 2.36): most of the range is spent on
  gravity before any velocity/acceleration demand. The EMA itself adds negligible lag (~1 step).
- [V computed, work/14/e_mix.py -> e_mix.csv / e_mix.txt; e_mix_table.py -> e_mix_table.txt; 20 public eps, 2 reps,
  scored vs GT with kit metrics] Per-policy-outcome scores on clean and perception-noisy references:
  | reference \ policy outcome | good (POL_GOOD) | mid (POL_MID) | lag 0.30 s (saturated soft wrist) | drop at 50 % (+good) | never grasps (+good) |
  |---|---|---|---|---|---|
  | GT (clean) | 0.965 / 1.00 / 1.00 | 0.900 / 1.00 / 1.00 | 0.882 / 1.00 / 1.00 | 0.700 / 0.90 / 0.08 | 0.537 / 0.50 / 0.00 |
  | PERC_A careful stereo | 0.900 / 1.00 / 1.00 | 0.845 / 1.00 / 1.00 | 0.831 / 1.00 / 0.85 | 0.668 / 0.85 / 0.08 | 0.514 / 0.48 / 0.00 |
  | PERC_M middle | 0.813 / 1.00 / 0.85 | 0.770 / 1.00 / 0.55 | 0.758 / 1.00 / 0.43 | 0.617 / 0.85 / 0.05 | 0.478 / 0.48 / 0.00 |
  | PERC_B rough mono | 0.619 / 1.00 / 0.13 | 0.594 / 1.00 / 0.05 | 0.587 / 1.00 / 0.03 | 0.494 / 0.78 / 0.00 | 0.394 / 0.43 / 0.00 |
  (AUC / SP-SR / MP-SR.) Mixture E[m] = (1-q) good + q fail, fail = 50/50 never/drop, q = p^N for best-of-N trained seeds
  selected on metrics_output (a discrete failure is visible as sim-vs-our-reference error, no GT needed):
  | reference | p (per-seed failure) | N=1 AUC / SP / MP | N=3 AUC / SP / MP |
  |---|---|---|---|
  | GT | 0.10 | 0.930 / 0.97 / 0.90 | 0.965 / 1.00 / 1.00 |
  | GT | 0.20 | 0.896 / 0.94 / 0.81 | 0.962 / 1.00 / 0.99 |
  | GT | 0.30 | 0.861 / 0.91 / 0.71 | 0.956 / 0.99 / 0.97 |
  | GT | 0.45 | 0.809 / 0.87 / 0.57 | 0.933 / 0.97 / 0.91 |
  | PERC_A | 0.20 | 0.838 / 0.93 / 0.81 | 0.897 / 1.00 / 0.99 |
  | PERC_M | 0.20 | 0.760 / 0.93 / 0.69 | 0.811 / 1.00 / 0.84 |
  | PERC_M | 0.45 | 0.694 / 0.85 / 0.48 | 0.789 / 0.97 / 0.78 |
  | PERC_B | 0.20 | 0.584 / 0.92 / 0.10 | 0.618 / 1.00 / 0.12 |
  Caveat [E]: q = p^N assumes independent seeds. CHORD Fig. 6 shows some sequences fail across seeds (0.04, 0.16).
  Correlated example: 10 % "hard" episodes with p = 0.8, rest p = 0.15 -> q = 0.215 at N=1, 0.054 at N=3 (not 0.008).

### Stage C verdict (2026-10-05): e_track estimate, error mass, determinism, cheapest measurement (ranges and item 6 superseded by the section I verdict)
1. e_track estimates for floating Sharpa, ONE deterministic frame-0 rollout per episode (policy-only = scored vs
   the clean reference it tracked; "total" rows include the perception model). All [E] unless marked.
   | condition | assumed per-seed discrete-failure p | continuous error | e_track-only AUC / SP-SR / MP-SR (N=1) | with best-of-3 seeds |
   |---|---|---|---|---|
   | motion_speed 0.5, default export packed as-is | any | timing: row f = source 0.508 f | 0.415 / 0.30 / 0.00 [V computed] | same (disqualifying, note 06) |
   | clean ref, motion_speed 1.0, default soft wrist (kp 25) | 0.20-0.45 (24/27 carried objects saturate the 0.2 m clip; [H]) | lag-like, POL_MID / tau 0.3 (AUC 0.88-0.90) | 0.76-0.84 / 0.87-0.94 / 0.57-0.81 | 0.86-0.90 / 0.97-1.00 / 0.91-0.99 (independent seeds; lower if failures correlate) |
   | clean ref, half-speed-equivalent physics with exact rows (fps 10 parquet + sim.fps 10, note 06 option [H]) or stiff wrist [H rules] | 0.07-0.25 (CHORD Table 1 SP-SR 0.926; HOT3D 0.77 loose) | POL_GOOD (AUC 0.965) | 0.88-0.94 / 0.93-0.98 / 0.76-0.93 | 0.96 / 1.00 / 0.99-1.00 |
   | PERC_M-quality reference (1 cm / 3 deg anchor, 0.8 cm / 3 deg jitter, 3 cm drift, 3 % scale), real speed | 0.30-0.62 (= p + 0.10..0.17, from Track 2 Tier 1 -> 2: 9/30 -> 14/30 SP-SR failures) | as above | total vs GT 0.63-0.70 / 0.79-0.90 / 0.18-0.39 | total 0.71-0.76 / 0.92-0.99 / 0.33-0.54 |
   | PERC_A-quality reference (careful stereo), real speed | 0.25-0.50 (= p + ~0.05 [H]) | as above | total vs GT 0.71-0.78 / 0.83-0.92 / 0.44-0.76 | total 0.80-0.84 / 0.96-1.00 / 0.75-0.99 |
   (exact mixture ranges: work/14/e_rows.py -> e_rows.txt; min/max over continuous term {mid, lag30} or {good} and the p range.)
   Reading: at real speed with the soft wrist, the lag-like continuous error alone collapses MP-SR on noisy references
   (PERC_M + lag 0.3 s: MP-SR 0.43 even with p = 0), so wrist headroom matters for MP-SR even without drops.
2. Where the error mass is [E from e_mix tables]: (a) DISCRETE failures of the most-moving object (no grasp, or a drop)
   dominate e_track. Each one costs 0.3-0.45 AUC on that episode and zeroes MP-SR; "never grasps" fails SP-SR in about
   half the episodes. At p = 0.2 they cost ~0.07 AUC and ~0.19 MP-SR, about twice what continuous tracking error costs
   (0.035 AUC, 0 MP-SR). (b) Continuous tracking error (lag, jitter, placement offset) costs only 0.03-0.10 AUC, never
   breaks SP-SR, and breaks MP-SR only when combined with perception error near the 3 cm / 30 deg budget. (c) The
   reset settle of slot-0 is amplified by the scorer's frame-0 alignment: 10 deg of tilt costs 0.16 AUC and 0.24 MP-SR
   with perfect tracking, so a physically consistent frame-0 object pose matters (cups are slot 0 in 6/20 eval eps).
   (d) A timing mistake (motion_speed 0.5) outweighs everything. (e) The probable CAUSE of discrete failures at real speed
   is the soft floating wrist: 0.3 kg x g / 25 N/m = 11.8 cm of the 20 cm residual clip is used just to hold the object,
   so fast lifts and flips (median v95 0.33 m/s, w up to 358 deg/s) saturate on 7.9 % of carried frames at
   motion_speed 1.0 and on 0 % at 0.5 [V computed proxy, H consequence].
3. Perception vs policy [E]: with ONE seed at real speed and the default soft wrist, the policy term (GT reference,
   relative to good tracking 0.965) is as large as or larger than a middle-quality perception error (PERC_M with good
   tracking) for AUC (-0.12..-0.20 vs -0.15) and MP-SR (-0.19..-0.43 vs -0.15). It is the ONLY term that breaks SP-SR (the
   perception models here never fail SP-SR). With best-of-3 seeds and the real-speed saturation solved, the policy term
   shrinks to ~0.04 AUC below perfect (0.035 of it continuous tracking error) and perception dominates every metric. So the policy matters first through (i) correct
   timing, (ii) wrist headroom at real speed and (iii) seed count. After those, perception decides the ranking. Noisy
   references also raise p (Track 2: SP-SR and MP-SR compose below min(noise-only, policy-only)), so perception quality
   pays twice.
4. Evaluator determinism [V code + V doc; E magnitude]: the actor is deterministic (mean action, eval-mode batch norm),
   the reset is fixed (seed 42, frame 0, VOC 0, terminations off), and world_count = 1. Physics is NOT configured to be
   deterministic (no warp.config.deterministic, no deterministic contact ordering; Newton is non-deterministic by
   default), so repeated runs can differ, and a near-marginal grasp can flip. The scorer never re-runs: it scores the
   uploaded trajectory and checks only provenance (the hash allowlists are currently empty). Use: keep the first eval
   per checkpoint; seed selection is legitimate, re-rolling the evaluator is not (treat as disallowed unless organisers
   say otherwise).
5. Training budget [V + E]: released recipe 250M transitions x 4,096 worlds, at least 46,000 MiB free GPU memory, VOC
   assistance off only after 122.9M (49 %), so stopping before ~130M leaves an assisted policy. Paper: ~2 h per sequence
   per seed on one L40S (Isaac Lab, 2,048 envs). Port throughput is unpublished. Plan: [E] 2-4 GPU-h per policy ->
   20 eval eps x 1 seed = 40-80 GPU-h; fixed best-of-3 = 120-240 GPU-h. Adaptive best-of-N (train another seed only
   where metrics_output shows a failure) needs 1 + p + p^2 = 1.25-1.65 seeds per episode for the same q = p^3, which is
   ~25-35 policies, or ~50-140 GPU-h. Checkpoints every 10.0M steps (save_interval 10,000,384) allow a budget curve
   from 130M to 250M without extra runs.
6. Cheapest experiment that measures e_track (rung R5 of note 10, ~10-20 GPU-h, no leaderboard use):
   - E0 (done, 0 GPU-h): score-cost tables above (work/14/track_err.txt, e_mix*.txt, kin.txt).
   - E1 smoke (~1 GPU-h): sharpa_flash_sac with task.motion_speed=1.0, sim.fps 20, on public ep 44 (single white_pot,
     slow). Measure steps/s and peak memory over ~5-10M steps, then evaluate the checkpoint 3 times with world_count=1
     and once with world_count=64 under reset_mode explicit. Any spread between the 64 identical worlds in the
     object-trajectory export, or between repeats, measures physics nondeterminism directly.
   - E2 (~8-16 GPU-h): one full 250M seed on 4 public episodes covering the difficulty range: 44 (slow, single object),
     21 (blue_cup + water_pitcher, two objects), 13 (blue_cup spin, w95 203 deg/s), 26 (white_pot flip, rot saturation).
     Object reference = public GT (clean) + our video hand retarget. Read metrics_output (e_track) at every 10M checkpoint
     from 130M; also score the exported trajectory vs GT with the kit metric functions.
   - E3 (same cost again, can be cut to eps 21 + 26): same episodes with the object reference replaced by our perception
     output (or GT + PERC_M noise), which gives the noise-induced increase in p; plus ep 26 with a half-speed-equivalent
     (fps 10 exact-row) or stiff-wrist variant, which tests the saturation hypothesis (after a rules check).
   - Falsifiers: if E2 at motion_speed 1.0 with default gains holds every object (p ~ 0) with AUC >= 0.95 vs its
     reference, the saturation hypothesis is wrong and perception dominates, so move effort to perception. If ep 26 / 13
     drop at real speed but hold under the half-speed-equivalent variant, wrist headroom is the lever. If E3 raises p by
     less than ~0.05, noisy references do not degrade the policy and the composition is additive.
- 2026-10-05 Stage C complete. New artifacts: work/14/e_mix.py, e_mix.csv, e_mix.txt, e_mix_table.py, e_mix_table.txt, e_rows.py, e_rows.txt;
  fetched @pin: work/14/repo/src/flash_chord/scene/{builder,objects,setup}.py, runtime/sim.py.

## Verifier pass (2026-10-05, independent; scripts and notes in /Users/aebatirel/Documents/Code/v2d-research/work/14-verify/)
- C1 holds [V]: EVT-07 appears only in the memory and media gates, V2D_INTEGRATION.md:83 says the training-reproduction gate is still pending, the tree has no Sharpa actor weights, and a HF API search finds no model. The kit's run_policy_evaluation.py:74-77 always writes metrics_output, the thresholds match the scorer, and _aligned_poses only checks shapes. Caveat: each value is one nondeterministic rollout, scored on the sim mesh's own 500 samples, and does not include the leaderboard's frame-0 alignment.
- C2: the numbers reproduce with my own models scored through the kit's score() (c2_kit.py): good 0.966/1/1, never+good 0.542/0.55/0, lag30 0.881/1/1. Three corrections. (a) "Most e_track is discrete" holds for SP-SR and MP-SR, but that follows from how the model is built. For AUC, discrete failures are only 31-56 % of the loss at real speed (the note's own lag30/mid, p 0.2-0.45) and 41-71 % at half speed. (b) The per-episode cost of a failure ranges from 0.04 to 0.83 AUC: the median is ~0.6 for single-object episodes and ~0.3 for two-object episodes, and 0.3-0.45 is only the cross-episode mean. (c) The freeze-in-air drop model understates the SP-SR loss. A drop where the object falls to the table and tips fails SP-SR in 55-65 % of episodes, against 10-15 % for the freeze model.
- C3: the arithmetic is correct [V]: mg/kp = 11.8 cm, a = 0.80, input_scale 5.71, and gravity compensation is set before spawn_objects. However, the residual is clamped PER AXIS (hand_pose.py:247-257, :408), not on the norm. Under the per-axis criterion, 19-25/27 tracks saturate at s=1 on 4.6-6.9 % of moving frames (nearly all on z), with a median excess of 2-4 cm (p95 7-12 cm). At s=0.5 it is 0-1/27. The result depends on the 0.3 kg mass, which the URDF comment calls a placeholder: at 0.15 kg it is 12/27 and 1.3 %, and at 0 kg 1/27.
- C4: the mixture reproduces to within 0.015. Its inputs are the weak part. p = 0.07 contradicts CHORD Table 1 under the note's own failure model, which implies p 0.11-0.25, and the upper ends of the half-speed range exceed Table 1 itself. The real-speed p 0.2-0.45 is a judgment, not a derived value. Best-of-3 assumes independent seeds. Corrected ranges (c4_corrected.txt), with independent-to-correlated seeds and freeze or physical drops:
  - Real speed, 1 seed: AUC 0.75-0.84, SP-SR 0.78-0.95, MP-SR 0.55-0.81.
  - Real speed, best-of-3: AUC 0.84-0.90, SP-SR 0.94-1.0, MP-SR 0.87-0.99.
  - Half-speed equivalent, 1 seed: AUC 0.87-0.93, SP-SR 0.88-0.97, MP-SR 0.75-0.89.
  - Half-speed equivalent, best-of-3: AUC 0.94-0.97, SP-SR 0.96-1.0, MP-SR 0.92-1.0.
  The half-speed equivalent also requires 10 Hz control, which is an untested hypothesis whose rules status is unconfirmed (note 06).

## H. Stage B re-run (2026-10-06, "try again" after outage): gap check of section F against chord_v2.txt
- Resume note: section F + Stage B verdict (2026-10-05) were re-read and kept; this pass only adds what F missed and
  re-checks live sources. Line refs below are to work/14/chord_v2.txt (965 lines; F's "txt:901-924" for Table 1 is
  stale - Table 1 is txt:187-230, Table 2 :237-266, Table 3 :283-303, Table 4 :672-707).
- [V, txt:761-802] NEW - Appendix C "CHORD Validation from Human Video": ONE brush task, reference reconstructed from a
  single monocular egocentric RGB video (Grounding DINO + SAM2 + SAM3D mesh, MoGe metric depth, FoundationPose object
  6-DoF, ViPE + Dyn-HaMR MANO hand, DROID-SLAM camera init, Gaussian-splat joint refinement with temporal smoothing).
  Reported: "0.647 AUC". This is the ONLY published CHORD number on a video-derived (not mocap) reference, and the
  closest analogue of Track 3 inference. Caveats [V]: n = 1 task, no seed count, no SP-SR/MP-SR, and the text does not
  say whether AUC is sim vs the reconstructed reference (= e_track on a noisy reference) or vs any ground truth (none
  exists for that video) -> [E] it is e_track on a video-derived reference. Read as a dose point: clean-mocap e_track
  AUC 0.918 (Table 1) -> 0.647 on a mono-video reference, a -0.27 drop from reference quality alone acting through the
  policy (the object reference itself is what the policy is scored against, so this is NOT perception error vs GT).
  Consistent with Fig. 9's 0.49-0.60 for noisy hand+contact refs and with Track 2 (noisy refs inflate e_track).
- [V, txt:174, 178] NEW - training-budget qualifier missing from F: the 1,831-task run used ONE hyperparameter set
  (VOC gains, curriculum, reward weights) for all tasks, and "stable training requires the contact wrench reward to
  converge before decaying the VOC; harder tasks with small contact regions or delicate interactions generally require
  longer optimization." -> the "~2 h per sequence" (txt:760) is a typical figure, not a fixed budget; hard episodes
  need more. [E] For Track 3 that argues for an adaptive budget: extend training (or add a seed) where metrics_output
  shows a failure, rather than a fixed 250M for every episode.
- [V, txt:159] NEW - for RGB-video references the paper itself switches objective: "When contact estimates are
  noisy due to hand-object misalignment, as in demonstrations reconstructed from RGB videos, directly matching human
  contact wrenches can be unreliable" -> reduced force-closure reward r_fc (fraction of 512 wrench basis directions
  with positive robot support). Used for TPV whole-body refs; Fig. 9 shows FC flat at ~0.50-0.57 AUC across noise
  tiers 1-6 while noisy-wrench CWS falls to 0.33 at tier 5. Cost [V txt:717]: FC "reduces dexterity, as it prioritizes
  stable grasps over faithful imitation". Applicability to Track 3 [H]: our contacts come from video hand fits
  (noisy), so FC vs CWS is a real recipe choice; check whether the FlashCHORD port ships an FC reward (next item).
- [V, txt:900-923] NEW - Appendix G baseline reproduction shows controller gains/action space matter enough that the
  authors trained DexMachina on Sharpa in 4 variants x 5 seeds per sequence (DexMachina-tuned vs CHORD-Isaac-Lab gains,
  hybrid vs residual action space) and reported the best (DexMachina gains + hybrid). ManipTrans reproduction on its
  own Inspire hand: 64.1 % single-hand / 29.7 % bimanual success on 77 OakInk2 primitives. SPIDER: 5 seeds per task.
  [E] So the Table 1 baselines are best-of-variant, and per-embodiment gain tuning is standard practice in this
  literature; consistent with our section D concern that the port's soft default wrist (kp 25 N/m) is a first-order
  factor. It does not show what the CHORD Isaac-Lab gains are (no numeric gains in the paper; "wrist force/torque
  tracking controller", txt:737).
- [V code @8c778f90] The port HAS the paper's FC fallback: configs/objective/tracking.yaml defines force_closure
  (ForceClosureObjectiveTermConfig, enabled false, weight 0.0, min_support 0.01; 512 wrench basis directions, 8 cone
  edges, friction 0.1) beside contact_wrench_support (enabled, weight 10.0, tolerance 0.1, var 0.1). The Sharpa curriculum
  tracking_250m_mixed_reset.yaml interpolates both weights from the objective config (CWS 10, FC 0) in all 11 stages,
  so switching a Track 3 policy to FC is a training-config override (objective.force_closure.enabled/weight), not a code
  change. The G1 recon_body_flash_sac.yaml curriculum (2,048 worlds, 350M steps, VOC 0 from 60 %) already uses
  force_closure 5.0, i.e. NVIDIA chose FC for its reconstructed-video G1 lane. [H] For Track 3 (video hands and contacts),
  CWS-with-noisy-contacts vs FC is a measurable recipe ablation, best run in E3 (Stage C item 6); the paper predicts FC
  wins only at contact noise >= ~25 mm / 25 deg (Fig. 9 tier 5).
- [V] Leaderboard re-fetched 2026-10-06 22:12 local (work/14/lb_live4.json, md5 c42eb3ff..., generated_at
  2026-10-06T07:44:21Z; the 10-04 copy lb_live3.json kept). CHANGED since section F. Baselines unchanged; new team rows
  (display names as on the public board, member handles not recorded):
  | board | team | AUC | SP-SR | MP-SR | RPE cm | MPPE cm | CD-O | last submission (UTC) |
  |---|---|---|---|---|---|---|---|---|
  | T2 Tier 1 (clean) | CHORD Baseline | 0.510 | 0.700 | 0.200 | - | 17.74 | - | 09-30 |
  | T2 Tier 1 (clean) | Xueyi Wang (FF), 2nd submission | 0.557 (was 0.527) | 0.700 | 0.667 (was 0.500) | - | 8.22 (was 12.48) | - | 10-06 06:19 |
  | T2 Tier 2 (noisy) | CHORD Baseline | 0.374 | 0.533 | 0.067 | - | 20.52 | - | 09-30 |
  | T2 Tier 2 (noisy) | Xueyi Wang (FF) | 0.421 | 0.533 | 0.267 | - | 15.34 | - | 10-06 05:34 |
  | T2 Tier 3 (own recon) | CHORD Baseline (CARI4D) | 0.002 | 0 | 0 | - | 70.17 | - | 09-30 |
  | T2 Tier 3 (own recon) | Xueyi Wang (FF) | 0.153 | 0 | 0 | - | 77.67 | - | 10-06 05:34 |
  | T3 Egocentric | SoySauceChicken (rank 1, CD-O missing) | 0.649 | 0.35 | 0.25 | 5.13 | 7.28 | - | 10-06 07:13 |
  | T3 Egocentric | Panav Raaj (rank 2) | 0.212 | 0.05 | 0.00 | 20.05 | 15.22 | 0.112 cm | 10-05 06:23 |
  Still no Track 3 baseline row (NVIDIA's Track 3 "end-to-end baseline" score is unpublished).
- [V] Leaderboard history since 10-04 (work/14/lbcommits2.json, 6 commits; intermediate copy lbhist/6f5d253355.json,
  generated 2026-10-05T12:29:58Z): at 10-05 12:29 Track 3 had only the Panav Raaj row; FF's Tier 1 row was still the
  first submission (0.527 / 0.70 / 0.50 / 12.48); FF's Tier 2 and Tier 3 rows and SoySauceChicken arrived 10-06 05:34-07:13.
  Submission counts: FF Tier 1 = 2, every other row = 1.
- [V computed from the rows above] What the new Track 2 rows say about e_track (policy-side headroom on CLEAN input):
  | Tier 1 (clean, = e_track only) | AUC | SP-SR | MP-SR | MPPE cm |
  |---|---|---|---|---|
  | CHORD Baseline | 0.510 | 21/30 | 6/30 | 17.74 |
  | FF v1 (10-02) | 0.527 | 21/30 | 15/30 | 12.48 |
  | FF v2 (10-06) | 0.557 | 21/30 | 20/30 | 8.22 |
  (1) Policy-side work alone moved MP-SR +0.47 (6 -> 20 of 30) and MPPE -9.5 cm on identical clean input, so the official
  per-episode recipe leaves a large, REDUCIBLE e_track [V]. (2) SP-SR is stuck at exactly 21/30 in all three Tier 1
  submissions and at exactly 16/30 in both Tier 2 submissions [V]. MP-SR (20/30) is now nearly the SP-SR pass set.
  [H] The 9 Tier 1 SP-SR failures are structural for both recipes (G1 whole-body infeasibility, large-object rotation
  or a reference/timing issue) rather than tracking precision; precision work raises MP-SR within the SP-SR pass set but
  does not fix outright failures. Per-episode rows are not public, so whether the SAME episodes fail is unverified.
  (3) Tier 1 -> Tier 2 (bounded 1.9 cm / 21 deg object noise): baseline -0.137 AUC / -5 SP-SR eps / -4 MP-SR eps;
  FF -0.136 AUC / -5 SP-SR eps / -12 MP-SR eps (0.667 -> 0.267). Both recipes lose the same NUMBER of SP-SR episodes
  (noise alone explains at most 1, ep 17), so the noise-induced extra failures (~4 eps) are recipe-independent so far
  [V counts, H same episodes]. A better policy loses MORE MP-SR to noise in absolute terms, because noise uses ~70 % of
  the 30 deg budget and any policy rotation error then crosses it. => Improving the policy raises the ceiling that
  perception noise caps. On noisy input, FF still gets only 0.267 MP-SR against 1.0 for a perfect tracker of the
  noisy input. [E]
  (4) Tier 3 (own reconstruction): FF 0.153 AUC vs baseline 0.002, both SP-SR = MP-SR = 0: when the reference is a
  real reconstruction, perception error dominates everything a policy can do [V rows, E reading].
- [V rows, E reading] First Track 3 totals (perception + policy composed, scored vs GT after the frame-0 alignment):
  rank 1 0.649 AUC / 0.35 SP-SR (7/20) / 0.25 MP-SR (5/20) / RPE 5.13 / MPPE 7.28; rank 2 0.212 / 0.05 / 0 / 20.05 /
  15.22 (its CD-O 0.112 cm is implausibly small for a reconstructed mesh, so it is not interpreted [H unit or near-exact meshes]).
  Against the Stage C predictions for a PERC_M reference, real speed and 1 seed (total 0.63-0.70 / 0.79-0.90 / 0.18-0.39):
  the leader's AUC and MP-SR fall INSIDE the band, but its SP-SR (0.35) is FAR below it. In our models, SP-SR fails only
  on discrete grasp failures (never-grasp fails it in ~50 % of eps) and our perception models never fail it, yet 13/20
  of the leader's episodes do. [H, ranked] Candidate causes: (a) gross ROTATION errors (> 0.5 rad mean geodesic)
  on small or near-symmetric objects (cups, bowls, pots). On a ~4-5 cm radius object a 90-180 deg error moves vertices
  only ~6-10 cm, so it still earns partial ADD-AUC but fails the geodesic SP-SR test outright; (b) slot-0 frame-0 rotation
  error propagated to every object by the scorer's single rigid alignment; (c) policy drops or no-grasps CANNOT be the sole cause:
  under PERC_M even p = 1 (every episode a never-grasp or freeze-drop) gives SP-SR ~0.66 at AUC ~0.55
  (e_mix_table.txt: never 0.48 / drop 0.85 SP-SR); with the verifier's physical-drop model (55-65 % SP-SR fail per
  dropped ep), failing 15/20 eps (MP-SR 0.25 needs >= 5 held) still leaves SP-SR ~0.5 [E arithmetic]. (a) and (b) are perception
  terms our Stage C perception models (PERC_A/M/B: <= 5 deg anchor, Gaussian jitter) do not contain. The real Track 3
  error distribution therefore has a gross-rotation tail that the models miss, and this tail, not e_track, may set
  SP-SR at today's frontier. Not separable from aggregates; testable on the 20 public GT eps by scoring our own
  perception output alone with the kit (perception-only SP-SR) before any policy training.
- [V code, kit metric_code/track_3/AUC.py:74-82, :130-142, same copy in MP-SR/MPPE/RPE.py] Supports candidate (a): ADD is plain
  vertex-correspondence ADD (R_a - R_r applied to the mesh samples, plus the translation delta). No ADD-S, and no symmetry handling
  anywhere. SP-SR = time-mean root-position error averaged over objects <= 0.10 m AND time-mean full geodesic averaged OVER
  OBJECTS <= 0.5 rad. So yaw about a cup or pot axis counts in full toward SP-SR and MP-SR, while for ADD it costs at most
  about the object diameter. A perception pipeline that is right up to symmetry can therefore score moderate AUC with low
  SP-SR, which is the leader's signature [H]. For the policy term this means e_track rotation (e.g. a cup spinning in hand
  during a lift) is also fully penalised; the FlashCHORD training termination (0.5 rad per frame) already trains against it [V].
- [V, txt:269-271] Section 4.3 (missing from F): over 1,831 runs, the per-sequence-normalised training CWS reward correlates with
  task success at Pearson r ~0.80 (r = 0.76-0.89 within each dataset). The relationship is monotonic and saturating, and OLS
  explains ~2/3 of the variance. [E] For the budget, the CWS reward logged during training is a cheap early indicator of an
  under-trained or failing episode, available before the evaluator runs. Combined with metrics_output it can drive an adaptive
  seed or step budget. It is a correlate under the loose 15 cm / 40 deg completion criterion, not under SP-SR or MP-SR.
- [V] arXiv abs re-checked 2026-10-06 (work/14/abs_1006.html): v2 is still the latest version.

### Stage B re-run verdict (2026-10-06): what changes relative to the 2026-10-05 Stage B verdict
1. [V] Paper priors confirmed, with three additions. (a) Appendix C is the ONLY CHORD number on a video-derived
   reference: one brush task, monocular pipeline (FoundationPose objects, Dyn-HaMR hands), AUC 0.647 vs 0.918 on clean
   mocap (Table 1). That is a ~-0.27 e_track AUC penalty from reference quality alone [E: n = 1, and the reference it is
   scored against is unstated]. (b) For RGB-video references the paper recommends the force-closure reward. The port
   ships it disabled (objective.force_closure); NVIDIA's own G1 recon lane enables it at weight 5. Fig. 9 shows FC
   flat at ~0.5-0.57 AUC under noise, where CWS collapses at contact noise >= 25 mm / 25 deg. (c) Budget: "~2 h per sequence" is
   typical, but harder tasks "generally require longer optimization". The training CWS reward predicts success at r ~0.8,
   so an adaptive budget is supported.
2. [V] Track 2 now shows that e_track on clean input is large and reducible by policy work. FF went 6 -> 15 -> 20 of 30
   MP-SR and MPPE 17.7 -> 8.2 cm on identical Tier-1 input, while SP-SR stayed at exactly 21/30 and Tier-2 SP-SR at
   16/30 for both recipes [H: structural failures that precision work does not fix]. On noisy Tier-2 input the better
   policy keeps only 0.267 MP-SR, so perception noise near the 30 deg budget caps whatever the policy gains.
3. [V rows, E reading] The first Track 3 totals (leader 0.649 / 0.35 / 0.25 / RPE 5.13 / MPPE 7.28) sit inside the
   Stage-C PERC_M band for AUC and MP-SR but far below it for SP-SR. Policy failures alone cannot produce SP-SR 0.35 with
   MP-SR 0.25 under our models. The likeliest driver is a gross-rotation perception tail (symmetric objects; the scorer
   has no symmetry handling) [H]. This shifts the Stage B dominance reading: at the CURRENT Track 3 frontier, the
   perception rotation tail plausibly dominates SP-SR, while e_track still matters for MP-SR and AUC. First check (cheap,
   no GPU): score our perception output alone vs public GT with the kit and count SP-SR failures from rotation versus
   position.
- 2026-10-06 Stage B re-run complete (section H). New artifacts: work/14/lb_live4.json, lbcommits2.json,
  lbhist/6f5d253355.json, abs_1006.html. Stage C not re-run in this pass.

## I. Stage C re-run (2026-10-06, "try again" after outage): e_track re-estimated with the verifier corrections, section H and note 15
- Resume note: section G + Stage C verdict (2026-10-05) and the verifier pass were re-read and kept. This pass (i) adopts the verifier's
  corrected ranges, (ii) adds per-EVAL-episode failure priors from note 15's risk table (only 4/20 eval eps are plain grasp-and-carry),
  (iii) re-checks determinism and upstream state, (iv) reconciles the first Track 3 rows. Scripts: work/14/c2/.
- [V, gh api 2026-10-06 22:18, work/14/c2/commits_1006.tsv, compare_pin_60dd.tsv] Upstream nvidia-isaac/video_to_data head is now
  60dd1aabae (2026-10-05, #195 "Correct metric ranks and add CARI4D baseline note"). The diff 8c778f90...60dd1aabae touches 13 files:
  README, docs/website (leaderboard.js ranks, CARI4D note, FAQ PDF, a re-zipped submission kit), groot_finetune and a leaderboard test.
  NOTHING under robotic_grounding/flash_chord changed -> every code-level Stage A/C finding at the pin still holds; still no published
  Sharpa e_track number and no released actor.
- [V, work/14/c2/faqs.pdf -> faqs.txt; docs/v2d_challenge/assets/v2d_challenge_2026_faqs.pdf @60dd1aabae] Official FAQ, rules relevant to
  e_track and budget: (a) Track 3 "Sharpa Wave is the default embodiment. Other embodiments are welcome, including fixed-base
  arm-and-hand setups and floating hands" -> a non-default controller/embodiment (e.g. the port's stiff-wrist Sharpa variant) is
  explicitly allowed in principle; this downgrades the earlier "[H rules]" blocker on the wrist-headroom lever to [E: allowed, gains
  not named explicitly]. (b) "Policy checkpoints are not required at this time", but a submission must include a git commit link plus
  hashes of the evaluation and submission scripts AND of the policy checkpoint "for later validation"; top solutions must provide code to
  reproduce. -> evaluator nondeterminism is a real VALIDATION risk: an organiser re-run of our checkpoint may not reproduce our
  uploaded trajectory bit-for-bit. (c) Five submissions per week per track/tier. (d) No training-budget, seed-count or wall-clock rule;
  "GPU credits ... under review". (e) The tissue-box example "is intended as a way to verify the workflow ... not necessarily an
  optimized baseline". (f) "Track 3 evaluates the final trajectory. Intermediate outputs are not assessed".
- [V kit] Local kit (work kit/kit.zip) has the same git blob sha 80fe61d9... as the re-zipped upstream kit at 60dd1aabae -> our kit is current.
- [E computed, work/14/c2/eval_prior.py -> eval_prior.txt] EVAL-SET e_track prior with per-episode failure classes. Inputs: kit-scored
  per-outcome rows on the 20 public GT eps (e_mix.csv; verifier c2_kit_surf.csv incl. physical tipped falls) averaged by object count;
  eval eps enter only via object count (kit list: 35/36/37/38 single-object, 16 two-object) and note 15's grasp class: F (plain
  grasp-and-carry: 1, 8, 37, 38), P (partial: stir/tool contact, insertion, drags, asset anchors: 3, 5, 6, 10, 19, 30, 32, 33), L (likely
  fails: hand-overs, flips, frame-0 in-hand cup, plank pivots, spoon twirls: 14, 15, 16, 20, 25, 28, 35, 36). Failure prob per seed-set
  p_N = s + (1-s) r^N, s = structural (seed-independent) [H judgment: F 0-0.05, P 0.25-0.5, L 0.6-0.9], r = random per-seed (real speed
  0.20-0.45; headroom fixed 0.11-0.25, verifier). Ranges = min..max over s, r, fail model (freeze vs tipped fall), continuous term.
  | regime (scored vs the reference it tracked = pure e_track, GT ref) | class-blind s=0 (old Stage C) | note-15 classes | structural s halved by fixes |
  |---|---|---|---|
  | real speed, soft wrist, 1 seed | 0.78-0.85 / 0.81-0.96 / 0.55-0.81 | 0.70-0.79 / 0.69-0.90 / 0.24-0.54 | 0.73-0.82 / 0.74-0.93 / 0.36-0.67 |
  | real speed, soft wrist, best-of-3 | 0.87-0.89 / 0.96-1.00 / 0.91-0.99 | 0.74-0.81 / 0.76-0.93 / 0.39-0.67 | 0.79-0.85 / 0.84-0.96 / 0.60-0.83 |
  | headroom fixed, 1 seed | 0.89-0.94 / 0.90-0.98 / 0.75-0.89 | 0.75-0.84 / 0.72-0.91 / 0.32-0.60 | 0.80-0.89 / 0.79-0.94 / 0.49-0.75 |
  | headroom fixed, best-of-3 | 0.96-0.97 / 0.99-1.00 / 0.98-1.00 | 0.78-0.87 / 0.77-0.93 / 0.42-0.67 | 0.86-0.92 / 0.86-0.96 / 0.65-0.83 |
  Composed with a PERC_M reference (scored vs GT; freeze-drop only, so SP-SR optimistic): real speed 1 seed note-15 0.62-0.68 / 0.79-0.87 /
  0.12-0.22; headroom fixed best-of-3 note-15 0.68-0.74 / 0.84-0.91 / 0.38-0.57; class-blind best case 0.81 / 1.00 / 0.85.
  These PERC_M rows keep p unchanged; raising r by the Track 2 (+0.10-0.17) or CHORD App. C (+0.35-0.5) amount gives, real speed, 1 seed:
  0.61-0.67 / 0.77-0.85 / 0.09-0.20 and 0.58-0.64 / 0.72-0.80 / 0.04-0.14 (work/14/c2/eval_prior_noisy.py -> eval_prior_noisy.txt).
  Readings [E]: (1) once the eval tasks' structural difficulty is priced in, e_track alone costs 0.21-0.30 AUC and 0.46-0.76 MP-SR
  (vs perfect tracking) at real speed with one seed, i.e. as much as or MORE than a middle-quality perception error alone (PERC_M with
  perfect tracking, section G: -0.20 AUC, -0.22 MP-SR).
  (2) Seeds stop helping: best-of-3 recovers ~0.04 AUC under note-15 classes vs ~0.06-0.09 class-blind, because the L/P failures are
  seed-independent by assumption. The levers for structural failures are recipe changes (wrist headroom, hull-aware frame-0 states,
  frame-0 grasp handling, FC reward, per-episode budget), not more seeds. (3) Bound: even if EVERY eval episode failed (p = 1) with
  the harsher tipped-fall model, GT-reference SP-SR stays 0.58 (freeze model 0.78) at AUC 0.64-0.66 and MP-SR 0-0.03.
- [E computed, eval_prior.py at mid parameters: s F/P/L = 0.025/0.375/0.75, r = 0.325, lag30 continuous, 1 seed, GT ref] Where the
  eval-set e_track mass sits: AUC loss ~0.26 total = continuous (soft-wrist lag) 0.107 (~40 %) + L-class failures 0.080-0.088 (~32 %)
  + P-class 0.044-0.049 (~18 %) + F-class 0.020-0.022 (~8 %). MP-SR loss ~0.62 = L 0.32-0.33 (~53 %) + P 0.22-0.23 (~36 %) + F 0.07 (~11 %).
  SP-SR loss 0.12-0.26 = L 0.08-0.15 + P 0.04-0.07 + F 0.02-0.04 (range = freeze vs tipped-fall model). So the AUC mass splits between
  continuous lag (fixable by wrist headroom) and the 8 L-class episodes; MP-SR mass is almost all discrete failures on P/L tasks.
- [V code @8c778f90, fetched to work/14/c2/{sharpa_hands_stiff.yaml, residual_hand_pose_stiff.yaml, sharpa_hands.yaml}; sharpa_hands.py:66-76]
  The wrist-headroom lever exists as Hydra config: embodiment=sharpa_hands_stiff -> SharpaHandsConfig.stiff_tracking (wrist xyz kp 6000 N/m,
  kd 60, effort 2000 N; rotvec same) and action=residual_hand_pose_stiff (wrist_kp 1200, wrist_tau_max 2000 vs default 25 / 45). Docs
  use it only for "kinematic-fidelity replay (collision-free)", "tuned for 200 Hz physics" (our sim: 100 Hz, fps 20 x substeps 5).
  With it mg/kp = 0.5 mm (vs 11.8 cm). Because the evaluator rebuilds the embodiment from the checkpoint's resolved config (Stage A), a
  policy trained with it is evaluated with it, and the FAQ welcomes other embodiments. [H, untested] Risks: at 100 Hz with contact, a
  2,000 N wrist following a noisy video hand reference can crush or eject objects; the soft wrist's compliance is also what lets the
  policy absorb reference errors. [H, new idea] An intermediate gain (kp ~200-600 N/m: 0.3 kg weight = 1.5-0.5 cm of the 20 cm clip) is the
  likelier sweet spot; it needs joint_overrides edits (regex-keyed dict), so it is a small config/code change, not an evaluator change.
- [V doc, work/14/c2/mjw_readme.md, island.py @mujoco_warp 7db3f199] MuJoCo Warp's README never mentions determinism or reproducibility;
  the only "deterministic" in the source is island.py's ascending-DOF ordering "for deterministic solver inputs" (one stage, not a
  global guarantee). Together with the 10-05 Warp/Isaac Lab doc reading: no published run-to-run determinism for the evaluator's physics.
  New consequence from the FAQ (b): the checkpoint hash is recorded "for later validation", so an organiser re-run that drops a
  marginal grasp would not reproduce our uploaded trajectory. Mitigation [E]: prefer policies with margin (no near-threshold holds),
  record the evaluator's own metrics_output and the exact GPU/driver/container per episode, and run the 64-world spread test (E1) to
  measure the flip rate before relying on any marginal episode.
- [V rows, E arithmetic] Track 3 leader reconciliation (lb unchanged since lb_live4: v2d-leaderboard-data head addd68db6f, 2026-10-06T07:44Z,
  checked 22:2x local). Leader 0.649 / 0.35 / 0.25. e_track bound above: SP-SR >= 0.58 even if all 20 eval eps fail physically, so >= ~5
  SP-SR failures (more if the policy holds in most eps) must come from non-policy rotation terms. Two such terms are already quantified
  in other notes and both match the leader's "moderate AUC, low SP-SR" signature: (a) the spoon body-frame roll bit (10/20 eval eps
  contain the spoon; 3 as slot 0): a wrong bit costs SP-SR -0.48 and MP-SR -0.50 on the board but AUC only -0.07..-0.13 (notes 07/13);
  (b) cup spin (6 cup anchors + beige slot 1 in ep 10): a 90-180 deg anchor spin gives AUC ~0.17-0.2 and SP/MP 0 for that episode (notes
  11/12), a non-anchor cup spin costs less AUC but still fails SP-SR when it exceeds ~1 rad. [H] The leader's row is consistent with a
  decent pipeline (e_track + perception ~0.72-0.78 / ~0.83 / ~0.3-0.5, the PERC_M-class rows of the eval prior) minus one of these
  rotation terms (spoon: SP-SR -0.48, MP-SR -0.07 noisy..-0.50 clean, AUC -0.07..-0.13); it says nothing about which spoon bit is
  correct (the leader's choice is unknown) and must not be used as a probe. Conclusion for dominance: at today's Track 3 frontier,
  SP-SR is set by perception/convention ROTATION terms; AUC and MP-SR are shared with e_track.
- [E arithmetic on verifier rows, single-object fail model] Second dose point for "noisy references raise p": CHORD Appendix C (one brush
  task, monocular-video reference, AUC 0.647, section H) vs Table 1 (clean mocap, 0.918). If the loss is discrete failures against a
  good-tracking continuous term (AUC 0.955), the implied failure rate is p ~0.07 on clean mocap and p ~0.56-0.59 on the video reference;
  if the continuous term is lag-like (0.833), p ~0.44-0.47 on video. So a video-derived reference adds roughly +0.35-0.5 to p in that one
  task, versus +0.10-0.17 inferred from Track 2 Tier 1 -> 2 (bounded 1.9 cm / 21 deg noise). n = 1 and the scoring target is unstated,
  so this is a weak point estimate; it says reference quality can matter to the POLICY as much as to the score directly.

### Stage C re-run verdict (2026-10-06): what changes relative to the 2026-10-05 Stage C verdict
1. e_track estimates, floating Sharpa, one frame-0 rollout per episode, scored against the reference it tracked (AUC / SP-SR / MP-SR).
   Labels: [V computed] for timing, [E] for the rest.
   | condition | public-like tasks, class-blind (verifier-corrected) | EVAL set, note-15 task classes |
   |---|---|---|
   | motion_speed 0.5 export packed as-is | 0.415 / 0.30 / 0.00 [V computed], disqualifying (note 06) | same |
   | clean ref, motion_speed 1.0, default soft wrist, 1 seed | 0.75-0.84 / 0.78-0.95 / 0.55-0.81 | 0.70-0.79 / 0.69-0.90 / 0.24-0.54 |
   | same, best-of-3 seeds | 0.84-0.90 / 0.94-1.0 / 0.87-0.99 | 0.74-0.81 / 0.76-0.93 / 0.39-0.67 |
   | clean ref, wrist headroom fixed (stiff/intermediate gains or half-speed-equivalent), 1 seed | 0.87-0.93 / 0.88-0.97 / 0.75-0.89 | 0.75-0.84 / 0.72-0.91 / 0.32-0.60 |
   | same, best-of-3 | 0.94-0.97 / 0.96-1.0 / 0.92-1.0 | 0.78-0.87 / 0.77-0.93 / 0.42-0.67 (0.86-0.92 / 0.86-0.96 / 0.65-0.83 if fixes halve structural failures) |
   | noisy reference (PERC_M-like; Track 2 says p +0.10-0.17, CHORD App. C video ref says +0.35-0.5) | total vs GT 0.63-0.70 / 0.79-0.90 / 0.18-0.39 | total vs GT, 1 seed, real speed: 0.62-0.68 / 0.79-0.87 / 0.12-0.22 with p unchanged; 0.61-0.67 / 0.77-0.85 / 0.09-0.20 with r +0.10-0.17; 0.58-0.64 / 0.72-0.80 / 0.04-0.14 with r +0.35-0.5 (c2/eval_prior_noisy.txt) |
   Clean vs noisy: a noisy reference costs twice, once directly and once by raising the policy's failure rate.
   Real speed vs half speed: the soft wrist saturates per axis on 19-25/27 carried public tracks at motion_speed 1.0 (4.6-6.9 % of moving
   frames, almost all z) and 0-1/27 at 0.5, driven by the 0.3 kg placeholder mass (verifier). Half speed itself cannot be submitted, so the
   fix is wrist headroom (gains or asset mass), not playback speed.
2. Where the mass is [E]: on the eval set at real speed with 1 seed, AUC loss ~0.26 = continuous soft-wrist lag ~40 % + discrete failures
   on the 8 L-class episodes ~32 % + P-class ~18 % + F-class ~8 %; MP-SR loss is ~90 % P/L discrete failures. These structural failures
   (hand-overs, flips, frame-0 in-hand grasp, plank pivots, spoon twirls, tool contact, hull-overlapping frame-0 states) are not fixed by
   more seeds: best-of-3 recovers only ~0.04 AUC on the eval set vs ~0.06-0.09 class-blind.
3. Perception vs policy [E]: (a) For AUC and MP-SR, e_track on the eval set (-0.21..-0.30 AUC, -0.46..-0.76 MP-SR vs perfect tracking, real
   speed, 1 seed) is as large as or LARGER than a middle-quality perception error alone (PERC_M: -0.20 / -0.22). Policy work is first-order, not a finishing step. (b) For SP-SR, e_track
   cannot go below ~0.58 even if every episode fails, while the leader sits at 0.35, so SP-SR at the frontier is set by perception and
   convention rotation terms (spoon roll bit, cup spin; notes 07/11/12/13). (c) The two compose: a better policy raises the ceiling and
   perception noise near the 30 deg budget caps it (Track 2 FF: 0.667 -> 0.267 MP-SR under noise).
4. Determinism [V code/doc, E consequence]: unchanged at the code level (flash_chord identical to the pin at upstream head 60dd1aabae;
   no physics-determinism flags; MJWarp documents no global determinism). New: the FAQ records the checkpoint hash "for later validation",
   so nondeterminism is a validation risk as well as an A/B-noise problem. Keep the first eval per checkpoint, log hardware, and prefer margin.
5. Budget [V rules + E]: no rule on budget or seeds (FAQ); 5 submissions/week/track. Plan [E]: 20 eps x 1 seed at 2-4 GPU-h = 40-80 GPU-h;
   one recipe variant (headroom gains, FC reward, or 1.5-2x steps) for the 16 P/L eps = +32-64; adaptive reseeds where metrics_output
   shows a failure = +10-25 -> ~80-170 GPU-h for a first complete pass. Measuring before committing (below) costs ~25-50 GPU-h.
6. Cheapest experiment that measures e_track and decides the split (replaces item 6 of the 10-05 verdict; no leaderboard use):
   - E-1 (0 GPU, perception side, run first): score our own perception output alone vs public GT with the kit; count SP-SR failures from
     rotation vs position. This decides whether the perception rotation tail or e_track is the next bottleneck.
   - E1 (~1 GPU-h): default recipe with task.motion_speed=1.0 on public ep 44; steps/s, peak memory, then 3 evaluator repeats with
     world_count=1 and one with world_count=64 (explicit reset). Spread across identical worlds directly measures physics nondeterminism.
   - E2 (~12-24 GPU-h): one 250M seed each on public twins that span the classes: 44 (F, single object), 21 (water-can + cup, twin of
     eval 20), 13 (cup in rack, twin of 14), 26 (pot flip into rack, twin of 28, rotation saturation), 23 (planks, twin of 25), 31 (brush and
     rack anchor inside hulls, twin of 30). Object reference = public GT + our video hand retarget. Read metrics_output at every 10M
     checkpoint from 130M; also score the export vs GT with the kit. A second seed only on the failures separates structural from random.
   - E3 (~10-20 GPU-h): (a) intermediate wrist gains (kp ~200-600) and/or the stiff variant on 26, 13 and 44; (b) the same eps with our
     perception reference (or GT + PERC_M noise), and CWS vs force-closure reward on one noisy ep.
   - Falsifiers: if E2 holds every object on 44/21 at default gains with AUC >= 0.95 vs its reference, the soft-wrist lag/saturation
     hypothesis is wrong. If the L-class twins (13/23/26) succeed on the first or second seed, note 15's structural failure rates are too
     pessimistic and the class-blind rows apply (then seeds and perception dominate). If E3a fixes 26/13 but E3b raises p by < 0.05, the
     composition is near-additive and perception can be developed independently.
- 2026-10-06 Stage C re-run complete. New artifacts: work/14/c2/{eval_prior.py, eval_prior.txt, eval_prior_noisy.py, eval_prior_noisy.txt, commits_1006.tsv, compare_pin_60dd.tsv,
  c195.txt, faqs.pdf, faqs.txt, kitzip_meta.tsv, lbc_now.tsv, mjw_readme.md, island.py, sharpa_hands_stiff.yaml,
  residual_hand_pose_stiff.yaml, sharpa_hands.yaml}.

## Verifier pass 2 (2026-10-06/07, independent; claims C1/C2/C3/C5 of the section I re-run; scripts and log in work/14-verify/ v2_*.py, notes.txt "PASS 2")
- [V kit code SP-SR.py:130-155] SP-SR and MP-SR are binary per episode on time-averaged errors (SP-SR also averaged over objects), so an
  "all-fail" SP-SR value is a property of the chosen failure model, not a floor.
- C1 [V reproduced exactly, v2_prior.py]: note-15 rows match eval_prior.txt. Corrections: (a) "s halved" uses s in [S_LO/2, S_LO]; true
  halving [S_LO/2, S_HI/2] gives headroom+best-of-3 0.87-0.92 / 0.88-0.96 / 0.70-0.83. (b) Note 15 rates 36 "borderline", not L (+0.004-0.014).
  (c) Lower ends depend on failure severity (v2_fail.py, v2_prior_harsh.txt): real speed 1 seed becomes 0.64-0.74 / 0.48-0.68 / 0.24-0.53
  with early (20 %) tipped drops and 0.58-0.70 / 0.44-0.65 / 0.24-0.53 when both moving objects fail. (d) s, r (0.20-0.45) and the
  class mapping (note 15 classes were written for our grasp-synthesis hand source, note 10 P9) are judgment, so the ranges are [H]-driven.
- C2 [REFUTED for SP-SR]: all-fail SP-SR on the eval composition is 0.61 (never only), 0.55 (tipped at 50 %), 0.43 (tipped, no good term),
  0.32 (never + early tipped), 0.26 (both objects fail). 0.58 is the mean of two mild one-object models. The leader's 0.35 / 0.25 is
  reachable by policy failures alone under these models, so "SP-SR at the frontier is set by perception/convention rotation" stays [H].
  AUC/MP-SR part reproduces (PERC_M alone, eval composition: 0.797 / 1.00 / 0.764 [V]), but compares class-priced e_track with
  class-blind perception; on the same class-blind basis e_track (0.75-0.84 AUC) is comparable to PERC_M, not larger. Note 12's spin
  figure is the resulting episode AUC (0.165-0.195), a cost of ~0.8 on that episode, not a cost of 0.17-0.2.
- C3 [V arithmetic]: the split (continuous ~40 %, L ~32 %, P ~18 %, F ~8 %) reproduces only with lag-first accounting. Failure-first gives
  continuous 15-16 %, L 47 %, P 26 %, F 11-12 %. lag30 (tau 0.3 s) is about the uncompensated PD lag kd/kp = 0.24 s, so it assumes the
  policy never compensates lag; with tau 0.1 the continuous term is 0.03, not 0.11. "Mostly seed-independent" restates the assumed s.
- C5 [V reproduced]: kp 25 / per-axis 0.2 m clip / 0.3 kg placeholder / hulls density 0 / wrist integral gain 0 (env/rl.yaml) -> mg/kp
  11.8 cm; kin_axis 19-25/27, 4.6-6.9 %, z; s=0.5 0-1/27; s=0.5 packed as-is 0.415 / 0.30 / 0. Corrections: restricted to lifted frames,
  18-23/27 and 3.1-4.6 % (on-table drags inflate the count); saturation means lag, and drops remain [H]. Note 06 step 3 keeps a 1:1-row
  half-speed route [H] (parquet fps 10, sim.fps 10, s 1), so wrist gains are one lever with asset mass and 10 Hz playback.
- Rules note: choosing per-eval-episode recipe variants from note 15's hand classes would be a per-episode hand label. Trigger variants
  automatically instead, for example from a metrics_output failure against our own reference.


---
[← Index](../README.md) · [Summary](../00-summary.md) · [← 13](13-spoon.md) · [15 →](15-eval-video-survey.md)
