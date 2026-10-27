# Critic report on note 23 (carry-aware control, force feedback, Kalman filtering)

I did not modify any file in /home/user/v2d-track3. I checked these myself:
- FlashCHORD source at 7eb9721. The flash_chord tree is identical to the evaluator pin 8c778f90.
- The kit (config/tracks.json, metric_code, tools/pack_submission.py).
- pipeline/mkref.py and hands_mp.py.
- One new computation on public ground truth (diagnostic only). Script: /tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/verify/critic/rotdamp.py. Output: /tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/verify/critic/rotdamp.txt.

## 1. Corrections the note needs (claim → corrected text)

### §A What the hand senses
1. L25, "Critic and actor get the same observation (symmetric FlashSAC). No privileged critic inputs."
   → "FlashSAC as shipped is asymmetric. The critic also gets:
   - applied VOC, target VOC and settling progress;
   - the reference phase t/(T−1);
   - each object body's world linear and angular velocity.
   Sources: train_flash_sac.yaml:26-31; envs/rl.py:66-112; flash_sac/learner.py:568,709-710. Only the actor lacks object velocity. Confirm this in our checkpoint's resolved config." Three checkers refuted the original line independently.
2. L22, "no look-ahead; only frame t" → "Command terms read one reference frame. The clock advances before the observation is built, so that frame is the one the next action targets: the actor sees ref(t+1) − state(t). There is no multi-frame window."
3. Add: the contact slots are zeroed at episode step 0, including the evaluator's first step (observation.py:665-667).

### §B Config levers
4. L30-32, gains. Add these facts:
   - The stiff variant also sets effort 2000 N and action.wrist_tau_max 2000 Nm.
   - Its docstring says it was tuned for 200 Hz physics and collision-free replay. RL runs at 100 Hz. Its prismatic ζ ≈ 0.31.

   Add these traps:
   - A joint_overrides entry replaces the whole default dict, so all five entries must be listed. If `wrist_rotvec$` is left out, the ball wrist falls back to position_velocity with kp 1.7 / kd 0.1.
   - A `wrist_[xyz]$` entry without `effort_limit` falls to 10 N. That is below the 12.2 N hand weight, which actgravcomp routes through the same actuator force range.
   - The 45 N limit binds for kp above about 165 with the 0.2 m clip.
   - Overlapping regexes resolve differently in training and evaluation, because the saved config is JSON with sort_keys.
   - The `stiff_tracking` classmethod target cannot be extended with extra keys.
   - Ball torque is clamped at action.wrist_tau_max (45 Nm). Ball k 100 therefore needs tau_max ≥ about 80–100 Nm.
5. L39-40, "gravity-only assist schedule would need code" → "A gravity-only VOC is config-only: set env.voc.k_lin = d_lin = k_ang = d_ang = 0. Only running the PD assist and the gravity assist on separate schedules needs code."
6. L55-58, "The evaluator overrides only VOC, reset mode/seed, world count, auto-reset and terminations" → add:
   - it loads the policy deterministically (mean action);
   - it re-applies the checkpoint's curriculum stage with VOC forced to 0;
   - physics knobs are replayed from the checkpoint without any check: all of `sim` (cone, impratio, substeps, fps, iterations), scene.contact_friction, object_free_joint_damping, object_scale_min/max/seed and action.delay;
   - `sampled_settled` raises a TypeError with the Sharpa ReferenceReset, so it is not an option.
7. L48-54, reset hold. Add: the final curriculum stage (from 200.0M steps) starts 50 % of episodes at frame 0, so frame 0 is trained. Those starts always carry the 20-step hold at VOC 1.0, zero velocities, and fingers at U(0, 0.7) of reference flexion. No ReferenceResetConfig setting reproduces the exact eval start: even openness 1.0 gives U(0, 1) < 1.

### §C Carry model
8. The kp 50 row ("0/27") → "Marginal. It is 0/27 only at SG-9 smoothing and nominal assumptions. It is 1–9/27 with SG-5/7, +30 % hand mass, or 0.15–0.18 m of usable clip. kp ≥ 100 gave 0/27 in every rerun."
9. The advance-only row (1/27) and gravity-only row (2/27) → "Fragile: 7–21/27 under the same alternatives. Only the combination is robust (0–5/27)."
10. Rotation "k 100 / d 12 saturates 0/27" → "With the default wrist_tau_max of 45 Nm it saturates 2/27, the same tracks as the default (effective clip 0.45 rad). 0/27 needs tau_max ≥ about 80 Nm." Also replace I ≈ 0.011 with I_eff ≈ 0.012–0.025 kg m², which includes armature and the object. The value does not matter because the damping term dominates.
11. Reading 1, "Removing either alone almost removes saturation" → "Either alone cuts saturated frames 5–20× at nominal assumptions. It still leaves 7–21/27 tracks saturating with less smoothing, +30 % mass or a 0.18 m usable clip."
12. Reading 2:
    - "kp 50–100 removes saturation on every public track" → "kp ≥ 100 does; 50 is marginal."
    - "overshoots what is needed by ~60×" → "exceeds, by about 60×, the minimum gain that avoids clip saturation in a lower-bound model. The model does not measure tracking precision, noise rejection or contact behaviour."
13. Reading 4 → add: "Advance plus gravity together, the only robust variant, puts the wrist 18.6 cm (median-track p95) to 26.7 cm (peak) from its own reference. Every track exceeds the 0.15 m wrist termination, in about 18 % of moving frames. Training it needs termination.wrist_position.threshold ≥ about 0.3 m."
14. Reading 5:
    - "0.84–1.25" → "per-track p05–p95 band 0.84–1.17; frame extremes 0.73–1.25 at SG-9 and 0.65–1.28 at SG-7."
    - The pinch estimate ignores off-COM torque (handles) and the pyramidal diagonal μ/√2 (2.6 N at μ 1).
    - The wrench-support reward assumes μ 0.1, which would mean about 18 N.
15. §C header. Add:
    - "Lower bound: the ground-truth object frame stands in for the wrist; only moving frames count; reach phases are excluded; SG-9 smoothing (ground-truth jitter < 0.4 mm, so SG-5/7 is as defensible and gives more saturation); perception references are noisier."
    - "NVIDIA's canonical recipe runs motion_speed 0.5. We must run 1.0, which doubles the lag term and quadruples the inertial term relative to the regime the default gains were validated in."

### D1 Control literature
16. VICES → "Fixed low impedance failed both path following and door opening. 'Cannot exert high enough forces' is stated only for the door (door friction); the paper gives no reason for the path-following failure. Fixed medium impedance learned the door faster than variable impedance and matched it at convergence. It was not shown to be fastest overall." Add that VICES's main result is variable impedance as an action, which would be a code change for us.
17. BeyondMimic → "kp = Iω², kd = 2Iζω, with ω = 2π·10 rad/s, ζ = 2 and I = reflected armature inertia. 10 Hz beat 5 Hz and ASAP's gains on global tracking. 25 Hz had lower local pose error but was rejected for hardware oscillation and gearbox wear. Applied to our 1.54 kg hand plus object, the heuristic gives kp ≈ 6.1e3 N/m and kd ≈ 390 N s/m. That is the stiff variant's stiffness with about 6× its damping, not an intermediate gain."
18. SPIDER → "The MANO model (base kp 1000, dampratio 1, armature 1.0, palm gravcomp, finger kp 300) belongs to SPIDER's sampling-based retargeting optimizer. 'u = u_SPIDER + π(o)' is eq. 6 of v1/v2 and applies only to humanoid tracking. v3 removed it and says the dexterous policy does not use SPIDER control as a residual term." Drop "40× softer than SPIDER's" or say it compares against an optimizer model.
19. DexMachina:
    - Rotation kp is 60–80 on 6 of 7 hands and 200 on Dex3.
    - The tighter-bounds result (±0.04–0.1 m, ±0.5–1.0 rad) is a Fig. 8 bar chart, run without curriculum on a subset of tasks and hands with 3 seeds. Replace "[V, curves]".
    - Those bounds sit on stiff wrists: kp × bound ≈ 12–35 N, against our 25 × 0.2 = 5 N. The lesson is "stiff gains plus a narrow residual", not "don't widen the clip".
    - The "ManipTrans-style" curriculum was DexMachina's own reimplementation. It decayed thresholds, gravity and friction on its own exponential schedule. Result: "no clear improvements", less stable training.
    - DexMachina's VOC gating rules (reward, slope, epoch, episode-length gates; per-env gains) were not verified.
20. ManipTrans → "Gravity is disabled on the whole hand asset, with rigid-body damping 20. The privileged inputs go to a shared actor-critic, so the actor sees object weight, COM, velocities and tip forces."
21. Tune to Learn → add: "The per-gain tuning was mostly action scale and mode (Optuna, 50 trials). PPO settings were shared. 99 % is the best trial per gain. So a gain change must come with an action scale/clip change."
22. Residual RL:
    - Silver: the 10× fewer samples is to reach 0.9 success on Push. Time to perfect success on Push was about the same as DDPG+HER, and the authors credit exploration.
    - Johannink: 15/20 vs 2/20 compares residual RL with the base controller alone, not with RL from scratch.

### D2 Force and tactile
23. "Touch helps most when the policy cannot see the object" → soften. Melnik 2021's state includes object pose and velocities, yet touch raised Block 0.30 → 0.43/0.44 and Pen 0.27 → 0.32. TacBPM's policy also receives the target orientation.
24. Yin 2023 → "369 vs 919 is the unseen-physics case; seen physics is 689 vs 964. On the real robot, binary sensing beat continuous sensing."
25. TacBPM → "Single right 22-DoF SharpaWave hand. 192-D state of 3 stacked frames: joints, previous targets, 5 smoothed fingertip contact magnitudes and 5 3-D contact positions. Success 40.05 % with tactile zeroed vs 60.38 % (±17), averaged over unseen sphere scales and novel shapes." There is no "per hand".
26. "Force magnitude worth ~0–6 %" → "No cited study isolates magnitude:
    - RotateIt: full continuous contact vs 8-bin location, +1.9 % on x, inside the std.
    - Koenig: +2.9 points is normal force vs binary; full vs normal is not significant; every framework also gets touch through the reward.
    - AnyRotate: +6 % on OOD mass only, +2.3 % on OOD shape.
    - Melnik: binary 0.85/0.44/0.31 vs continuous 0.83/0.43/0.32 (Egg, Block, Pen), so binary is slightly higher on Egg and Block."
27. Hora → "The drop from T3 176 to T20 43 is the DR baseline, which feeds flattened history into the PPO MLP. Hora's supervised adaptation module improves with longer history."
28. Grip-load:
    - Flanagan & Wing 1997 is precision grip on a servo-driven manipulandum (simulated loads). Median GF/LF is 2.95–3.07 under the inertial load (m ≈ 1.41 kg) and 2.25–3.07 across all loads. GF rate leads LF rate by 14 ms on average (−3 to 21 ms); peak GF leads peak LF by about 11 ms.
    - PMC4574045 is Hiramatsu et al. 2015 (PLoS One), an experimental study, not a review. It cites a 20–50 % safety margin of grip force and measured about 40–50 % for objects of 100 g or more.
29. MuJoCo contact physics:
    - "Elliptic cones + large impratio (+ Newton with a very small tolerance)" is one remedy, not two separate ones; NoSlip is the second.
    - impratio's "harder friction" effect is defined for elliptic cones. With pyramidal cones, impratio scales every edge row (normal and friction mixed), which stiffens the whole contact.
    - NoSlip raises NotImplementedError in the pinned mujoco-warp 3.8.1.
    - #562 is a feature request; the replica divergence is a user comment (2026-10-10). A GPU determinism option was merged on 2026-10-22, after the pin.
    - flash_chord sets no condim, so default 3 is assumed.
30. Force closure → "Flatter across noise levels, but below contact-wrench guidance at levels 1–3 (≈0.52 vs 0.58–0.61) and above it only at levels 4–6, with overlapping bands. Fig. 9 is a different setting from Table 2 (absolute AUC about 0.5–0.6). 'Reduces dexterity' is unquantified."
31. CHORD perturbations → "One sentence in the paper: wrenches sampled from the human contact wrench matrix. No magnitude, schedule or ablation. Observation corruption was off in the large-scale runs. No mass, friction or gain randomisation."
32. Sharpa Wave:
    - Upgrade the Dynamic Tactile Array to [V] from the official page sharpa.com/pages/wave: fingertip 6-axis F/T, 0–30 N, 20 ms latency.
    - Per-finger torque sensing stays [U] (press coverage only).
33. "No paper reports drop rate as a function of touch" → [unverifiable]. TacBPM says it reports drop rate; I found no tactile vs no-tactile drop table. Check Sec. IV before keeping the sentence.

### D3 Kalman filtering and references
34. Heading "Offline smoothing beats causal filtering" → "Windowed (fixed-lag) estimation beats per-frame estimates."
    - Zorina is an online, causal 1 s factor graph.
    - Yu & Rodriguez's iSAM is a realtime fixed-history smoother, and both their EKF and iSAM fuse touch and a motion model.
    - Neither compares offline smoothing with causal filtering. The only offline evidence is Hasson's batch fit and the agent's toy, whose script is not in the repo.
35. Zorina's 3-frame window: no change on YCB-V and +0.01/+0.02 on HOPE-Video. On the synthetic sets it added +0.05/+0.06 precision and cost 0.04 recall on the dynamic set. The paper is arXiv 2605.02708 (posted May 2026, accepted Oct 2024).
36. Yu & Rodriguez: the baseline is unfiltered AprilTag. The vision+touch EKF worsened rotation from 3.4° to 6.4°. iSAM 1-step was also worse (3.7°). The 1000-step result is 6.1 mm / 1.8°.
37. Hasson's 7.7 → 3.8 cm belongs to the smoothness term (only removing it moves object ADD-S). Move it out of the hand-object coupling bullet.
38. ComPose: the default model is 19.5° (Table 1); 19.9° is the HaWoR variant.
39. GMR → "Ground penetration (PHC Dance 1/2, up to 60 cm) gave 0 % vs 100 %. Waist-roll jumps (GMR Dance 5) gave 96 % in sim and 51 % sim2sim. Self-intersections gave 20–40 %. This is a cross-method comparison (confounded) on G1 whole-body tracking."
40. SPIDER 0.99 vs 0.07:
    - one tabletop cup task with a fixed-base arm in PhysX;
    - the kinematic reference let the cup drift out of the hand;
    - SPIDER's control initialises the policy targets, which confounds the comparison;
    - the numbers are in v3 only;
    - 48.8 vs 11.0 measures open-loop retargeting quality.
41. CHORD QC: the 300-step replay is a crash/initialisation check. There is no QC-versus-success measurement, so drop it from "Cleaner references raise RL success".
42. "A causal KF on FoundationPose (2026) gave only 1–17 %" → [U]; not verified.

### §E Rules and integrity
43. "Simulator code changes … alter the evaluator code digest" → wrong.
    - eval_code_sha256 hashes only flash_chord/evaluation/{__init__,harness,metrics,rollout}.py (harness.py:123-135). eval_script_sha256 hashes the kit script.
    - The kit's accepted-digest allowlists are empty (config/tracks.json).
    - So changes to observation.py, control.py or reset.py would not show in any digest.
    - The real constraints are re-validation on the official build and fairness. A new config key fails instantiate_typed with "unexpected keyword"; a changed observation layout changes the policy input.
    - Config-only levers re-run identically on the official build, because the evaluator rebuilds from the checkpoint config.
44. Add the unchecked physics replay from item 6 to §E.

## 2. Gaps

### Kalman filters
- The note never says plainly that the actor observes noise-free simulator state. The port has no observation-noise code, and CHORD disabled corruption. A policy-side Kalman filter or observer therefore has no job except unobserved derivatives, and object velocity is one config flag away. Kalman filtering belongs only in perception and reference building.
- No measured perception number backs smoothing. The free test is still undone: smooth perc2 object paths and score them against public ground truth with the kit metric (CPU).
- The note does not plan joint consistency. The wrist path is SG-smoothed in hands_mp.py, while the object path from perc2 is raw. Two independently filtered signals give spurious hand-object relative motion during carry.
- The disturbance observer (estimating external force from the PD error), the classical answer to "a heavy object pushes back", is not discussed. In this simulator the observed PD error already plays that role, but only while the wrist is not saturated.
- The toy RTS results cannot be reproduced: the script is not in the repo, which breaks the record-every-run rule.

### Control theory
- Not covered:
  - why a memoryless actor can still hold a constant-load residual (processed_action gives one-step memory, and the sag is visible in command_wrist);
  - gain scheduling and variable impedance (code);
  - co-tuning the clip and action scale with gains (DexMachina, Tune to Learn);
  - the stiff variant's 200 Hz tuning against our 100 Hz physics.
- **New [C], my computation:** the ball wrist is strongly overdamped. With d 6, k 25 and I_eff 0.012–0.025, ζ ≈ 3.8–5.5 and the lag d/k is 0.24 s.
  - At k 25, lowering only the ball damping to d 3 gives 0/27 saturating tracks (median p95 0.215 rad). d 1.5 (ζ ≈ 1–1.4) gives 0.107 rad.
  - The result is the same at SG-7 and does not depend on the tau_max clamp.
  - This is a config lever (`wrist_rotvec$` kd) that the note misses.
  - It is an exact-tracking lower-bound model; contact stability with lower damping is untested.
  - Files: /tmp/claude-0/-home-user-v2d-track3/68c88876-77c0-55d9-bea4-03de8a3f6ee7/scratchpad/verify/critic/rotdamp.txt and rotdamp.py.

### Physics-based path following while carrying
- The note analyses wrist demand but does not treat physical feasibility of the reference as a lever. Not covered:
  - kinematic replay of the reference to check penetration, hover or overlap at frame 0;
  - objects moving with no hand contact;
  - SPIDER-style physics retargeting on the data side.
- The reset sets object and hand q to reference frame 0 with zero velocity (reset.py:79-123). A frame-0 penetration or hover therefore causes a pop at t = 0 in the scored rollout.
- The note also misses what mkref.py already does:
  - a per-object frame-0 z snap (constant shift, ≤ 2 cm);
  - "ride-along" filling of hand gaps;
  - contact recomputation (16 probes, 18 mm threshold).

### Carry-aware methods
- Not analysed (code [V], effect [H]): the reference contact labels drive missed_contact (−1) and unintended_contact (−10). The unintended term is binary per object body plus the mean squared support on bodies the reference marks inactive.
  - If the MediaPipe hand drifts more than 18 mm from the object during carry, the reference says "no contact". The policy is then penalised, in proportion to support squared, for exactly the force that carrying needs.
  - That penalty can rival the object-keypoint reward (weight 20).
- Any carry gate (gravity offset, attachment) must come from perception on eval episodes, never from ground truth.
- The model covers neither the spoon (10 of 20 eval episodes, thin handle) nor two-object, hand-over or two-hand carries.
- Gains could legitimately be chosen per episode from carry demand predicted on our own eval references. The note does not discuss this.

### Force feedback when the object is heavy
- State plainly: every sim object is 0.3 kg in both training and evaluation. "Heavy" here is a soft-wrist problem with a known load, so feed-forward or stiffness is the answer, not estimation.
- Finger grip capacity is unchecked. Fingers use the JointControlSpec defaults: kp 1.7 Nm/rad, effort 10 Nm [V code]. That looks ample for a 1.8–3.7 N pinch [E, order of magnitude].
- The PD-error "sensor" mixes table contact with object load and is ambiguous at the clip.

### Claims with no verification
- Omnigrasp's 20 future frames.
- InterMimic's offsets {1, 2, 4, 16}.
- DexTrack next-frame only.
- The PHC quote.
- RMA's 0.5 s history and 12 kg payload.
- Della Santina 2017 and "Keep soft robots soft".
- Yu, Turk & Liu 2018.
- DexMachina's gate conditions.
- Khandate 2022 and Sievers 2022.
- The 74 ms slip reflex.
- KF on FoundationPose (2026).
- van der Laan 2024, and the manif/GTSAM licences.
- Wahlström & Skog 2020.
- 100DOH.
- OmniRetarget.
- MaskedManipulator's 10 cm rule.
- "NVIDIA CHORD hardware runs are state-based with mocap".
- The agent's toy.
- perc2 "no smoothing" and hands_mp SG-7: I confirmed both by grep, but the note's bullet omits mkref's snap.

### Sources and modalities not checked
- **No simulator rollout evidence at all.** Every policy-side effect is unmeasured.
- The kit FAQ and organiser text on embodiment variants (note 14 cites it; note 23 does not).
- Classical literature on disturbance and momentum observers, adaptive payload control (Slotine–Li) and gain scheduling.
- TacBPM's drop tables.
- Carry demand on our eval-episode references.

### Integrity and rules risks
- **Ground truth:**
  - The carry model on public ground truth is fine as a diagnostic.
  - Carry gates, the advance τ, offsets and smoother settings must be computed from perception, tuned only on public episodes, and frozen before eval.
  - Oracle-reference training arms are public-only diagnostics.
- **Physics replays silently into the scored rollout:** sim.cone, impratio, substeps, contact_friction, object damping, object scale and action delay. The evaluator accepts all of them without a check.
  - Treat them as off-limits.
  - Never use object scale or delay as training domain randomisation: it would also apply to the scored eval rollout.
- **Code changes:** they would not change the digest (see item 43). They would break or alter an official re-run, so they stay off-limits for submissions without organiser approval.
- **Custom gains:** the embodiment yaml must be committed (provenance), and the organisers should be asked (note 05).
- **GPU non-determinism:** keep the first evaluation of each checkpoint.

## 3. Recommended ranked levers

Shared assumptions:
- Cost basis: measured 45,300 steps/s, so one 250M-step run takes about 1.7–2 GPU-h. On-demand PRO 6000 ($1.45–1.65/h) is about $2.5–3.3 per run. Interruptible (from $0.54/h) is about $1 per run, but only after the resume test passes.
- Every effect below is a hypothesis.
- **Batch G1** (one rental), on public episodes 11, 23, 13 and 42, which saturate most under default gains and have usable perception, plus episode 27 as a low-demand control. Use perception references.
- **Metrics:** evaluator AUC/SP/MP against our own reference, kit AUC against public ground truth, drop events, wrist-to-reference gap and clip saturation from the exported rollout, and error in the first 2 s.
- **Decision rule:** keep a lever only if its sign is consistent on at least 3 of 4 carry episodes. Then run a second seed on the top two arms.

1. **Wrist translation gains, plus companion settings**
   - Type: config.
   - Arms:
     - A0: kp 25 (default);
     - A1: kp 100 / kd 12, all five overrides, effort 45, ball k 100, tau_max 100;
     - A2: kp 300 / kd 30, effort ≥ 100 N, ball k 300, tau_max 300;
     - A3: the shipped stiff variant.
   - Mechanism: removes clip saturation and lag, so the residual becomes nearly kinematic. This matches the regime of every comparable system (DexMachina, BeyondMimic).
   - [H] AUC against our own reference rises on carry-heavy episodes.
   - Falsifier: A1–A3 fail to beat A0 on at least 3 of 4 episodes. Separately, if A3 ≥ A1 on perception references, the "soft wrist forgives reference error" [E] is rejected and the official stiff variant is preferred (lower rules exposure).
   - Rules: organiser question.
   - Batch: G1 (the core 4 arms).
2. **Reference feasibility and contact-label audit**
   - Type: reference data; CPU only.
   - Checks on public references:
     - frame-0 hand-object and object-table penetration or hover;
     - hand-object overlap > 2 cm (CHORD QC);
     - object jumps > 10 cm;
     - carry frames (object moving per perception) with no reference contact on any hand;
     - spread of the wrist-to-object relative pose during carry.
   - [H] Flags predict discrete failures and the unintended-contact penalty during carry.
   - Falsifier: the flags are near zero, or they do not correlate with G1 failures.
   - Cost: about $0. Runs before G1, and it decides how much G1 is worth.
3. **Robust offline smoothing of object paths, plus per-segment rest/tilt snap**
   - Type: reference data; CPU.
   - Mechanism: a Lie-group Student-t smoother; static segments held to a constant pose and placed on the table, extending mkref's frame-0 snap.
   - [H] Kit AUC against ground truth rises, and the policy failure rate drops.
   - Falsifier: on all 20 public episodes, smoothed vs raw perc2 changes kit AUC by ≤ +0.005 → stop. GPU follow-up only if it passes: raw vs smoothed on 2 episodes in batch G2.
4. **Hand-object attachment during carry**
   - Type: reference data.
   - Mechanism: rebuild the wrist reference as object pose × a per-segment grasp transform, taken from perception; blend at grasp onset and release; recompute contacts.
   - [H] Fewer residual-budget losses, terminations and false unintended-contact penalties.
   - Falsifier: the lever-2 audit shows relative-pose spread under about 1 cm / 5° and no contact gaps, or a G2 arm gives no drop or termination reduction.
5. **Ball-wrist damping to near-critical**
   - Type: config (`wrist_rotvec$` kd 2–3 at k 25).
   - Evidence: [C] 0/27 rotational saturation; see §2.
   - [H] Better rotation tracking (SP/MP-SR) without extra stiffness.
   - Falsifier: arm A4 in G1 does not reduce rotation error on episode 13, or it oscillates.
   - Batch: G1.
6. **Reset/start alignment**
   - Type: config.
   - Settings: final-stage reset_to_first_frame_probability 0.8 and reset_finger_openness 1.0.
   - Diagnostic first: compare the evaluator's first-2-s error with the rest of the clip on any G1 checkpoint.
   - [H] It matters mainly when the object is already in hand at frame 0 (eval 20, 32).
   - Falsifier: the first-2-s error is not elevated in evaluation, and the bundle arm gains nothing.
   - Batch: G1, in the A5 bundle.
7. **Actor object velocity**
   - Type: config (observation.object_body_velocity.enabled=true).
   - [H] Earlier slip response.
   - Falsifier: no change in drops.
   - Batch: G1 bundle A5 = A1 + lever 6 + lever 7. Isolate it in G2 only if A5 wins.
8. **Reference-side feed-forward**
   - Type: data plus config. Advance τ = kd/kp together with a gravity offset while carried (gate from perception), and wrist termination ≥ 0.3 m in training.
   - Role: the fallback if the organisers reject non-default gains.
   - Falsifier: arm A6 (kp 25) is no better than A0.
   - Batch: G1.
9. **Contact rewards**
   - Type: config (force_closure enabled with a small weight, or a higher contact_wrench_support weight). Low prior.
   - Falsifier: no drop reduction.
   - Batch: G2.
10. **Code-level levers, not for submission without organiser approval**
    - force-magnitude and TacBPM-shaped observations (Innovation and hardware story);
    - a 5-frame look-ahead;
    - CHORD-style wrench perturbations;
    - an exact-start reset mode;
    - a wrist feed-forward wrench.
    - Each new config key breaks the official re-run.

**G1 cost estimate:**
- 4 carry episodes × 7 arms (A0–A6) = 28 runs, plus the control episode 27 on A0/A1 = 30 runs.
- About 50–60 GPU-h: about $75–100 on demand, or $30–35 interruptible after the resume test.
- Optional oracle-reference arms for A0/A1/A3 add 12 runs (about $30–40). They test the stiffness × reference-error interaction.
- G1 depends on the day-1 smoke test and resume test passing, and on hands_mp → mkref producing references.

## 4. Stated with more confidence than the evidence supports
- §A "symmetric critic": refuted by code.
- §C "kp 50–100 removes saturation on every track", "either alone almost removes saturation", and rotation "k100 0/27" all fail sensitivity reruns or the torque clamp.
- §C3 / §E "an intermediate kp is the likelier sweet spot": the only support is the unmeasured [E] force argument, and it ignores that the policy sees contact and can cancel δ. The literature (DexMachina 300–350 with a narrow residual; the BeyondMimic heuristic ≈ 6000) points stiffer. Decide by the G1 sweep.
- "The stiff variant overshoots by ~60×": that is a saturation-only lower-bound model.
- §C5 / D2 "anticipatory grip modulation is second-order": plausible, but untested in simulation, and it ignores the reference contact-label penalty and the spoon.
- D2 "force magnitude worth ~0–6 %": no isolated ablation exists.
- D2 "touch helps most when the policy cannot see the object": counterexamples exist.
- D3 "offline smoothing beats causal filtering": the evidence is online fixed-lag work.
- D3 "cleaner references raise RL success": confounded cross-method studies, a single task, and a crash check counted as evidence.
- §E "code changes alter the evaluator digest": factually wrong.
- "Look-ahead needs code" is right, but the gains cited (GMT −8.6 %, UniTracker best at 5) come from whole-body humanoids. UniTracker's MPKPE is lowest at 10 frames and was measured on its training set.