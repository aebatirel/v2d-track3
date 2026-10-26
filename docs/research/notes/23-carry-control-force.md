# 23 — Carry-aware control, force feedback and Kalman filtering for the policy stage (2026-10-26)

Status: IN PROGRESS. Code study and carry model done; literature review running. Owner's question: can Kalman filters,
control theory, physics-based path following, carry-aware methods or force feedback from the hand (a heavy object
pushes back on the hand) help policy generation?

Labels: [V] read in source code or primary text, [C] computed here, [E] estimate, [H] hypothesis.
Code: nvidia-isaac/video_to_data @ 8c778f905cb3 (evaluator pin), `robotic_grounding/flash_chord/src/flash_chord/`.
Model: `docs/research/work/23/carry_model.py` → `carry_model.txt`, `carry_model.csv` (public GT, diagnostics only).

## A. What the simulated hand can already sense [V code]
- The policy observation (`envs/observation.py`, `configs/observation/policy.yaml`) holds: wrist pose and velocity;
  finger joint positions and velocities; object pose; the current-frame reference minus current state for the wrist,
  fingers and object; the previous raw and processed action; and **live contact slots**.
- Live contact slots (`runtime/contact.py`): for every (hand link, object body) pair, the mean contact point in the
  wrist frame and the **unit direction** of the summed contact force. The simulator computes the force magnitude
  (`contact_force_w`), but the observation keeps only its direction. So the policy has a touch sense (where, and which
  way it pushes) but no force-magnitude sense.
- Weight is still observable indirectly. The wrist is a soft PD spring (kp 25 N/m), so a carried 0.3 kg object pulls
  the wrist 11.8 cm below its target, and the policy sees that gap in `command_wrist` (reference minus current). In
  this simulator the hand's position error **is** a load sensor.
- Not observed: future reference frames (no look-ahead; only frame t), object velocity (the term exists,
  `object_body_velocity`, but is disabled in config), force magnitudes, slip. The actor is a memoryless MLP (no
  frame history beyond the previous action).
- Critic and actor get the same observation (symmetric FlashSAC). No privileged critic inputs.

## B. Levers that exist in config today [V code]
The evaluator rebuilds the environment from the checkpoint's own resolved config (note 05 §0), so these are ours to set
without touching simulator code (rules caveats in §E):
- **Wrist gains.** Prismatic gains come from `embodiment.config.joint_overrides["wrist_[xyz]$"]` (default kp 25,
  kd 6, effort 45 N). Ball-wrist gain is `action.wrist_kp` (25 Nm/rad) with passive damping from the embodiment
  (6 Nm s/rad). The shipped stiff variant uses kp 6000 / kd 60 (prismatic) and 1200 (ball).
- **Observation toggles.** `observation.object_body_velocity.enabled` (off by default).
- **Unused reward terms.** `objective.force_closure` (wrench-direction coverage on reference-active hands; disabled),
  `objective.contact_force_l2` (L2 or log-RMS contact-force term with a 3-step history; disabled). The wrench-support
  reward models friction with mu = 0.1 while the scene uses contact friction 1.0.
- **Terminations.** `termination.wrist_position.threshold` 0.15 m, object 0.10 m / 0.5 rad (training only; the
  evaluator turns them off).
- **Assist (VOC).** `env.voc` gains and limits; the gravity-compensation force is scaled by the same `voc_scale` as the
  PD part, so a "gravity-only" assist schedule would need code.
- **Object mass.** Comes only from the object URDF (all organiser URDFs say 0.3 kg, called a placeholder; our spoon
  URDF too). No config knob.
- **Reference contents.** The parquet is ours: wrist/finger paths, contacts, object paths. A wrist path shifted in time
  or offset in z changes the PD targets (the residual is added to the reference).
- Not available without code: wrist feed-forward force (gravity or inertia), target velocities for the PD,
  force-magnitude observations, look-ahead observations, frame stacking. The only future-frame code in FlashCHORD is the
  G1 SONIC action encoder (`runtime/actions/sonic.py`), not usable for the Sharpa hands.
- **Reset hold (train/eval mismatch).** Every training reset (`lifecycle/reset.py` `sample_reference_reset`,
  `advance_reference_reset`) freezes the reference clock for `reset.voc_decay_steps` = 20 steps (1 s) with VOC = 1.0,
  and opens the fingers by a random factor up to 0.7, then releases at the curriculum VOC (0 after 122.9M). The
  evaluator (`evaluation/harness.py` `apply_evaluation_composition`) forces `voc_decay_steps = 0`, VOC 0,
  `always_reset_to_first_frame`, seed 42 and fingers at the exact reference: no hold and no assist. So the policy never
  trains the exact start it is scored on (frame 0, unassisted, no settle). `reset.voc_decay_steps` is config, but it is
  global (not per curriculum stage), and setting it to 0 would also remove the hold for mid-carry resets.
- [V] The evaluator overrides only VOC, reset mode/seed, world count, auto-reset and terminations. Embodiment, action,
  observation and objective settings come from the checkpoint's resolved config, so the config levers above reach the
  scored rollout. A `sampled_settled` evaluation reset mode with a settling preamble also exists; the kit uses
  `explicit`.

## C. Carry model on the public GT paths [C, `work/23/carry_model.txt`]
Per-axis residual the policy must hold so the wrist follows the object path exactly, F = kp·e − kd·v with the hand
(1.243 kg, gravity-compensated) plus a 0.3 kg object on moving frames; clip 0.20 m per axis, 1.0 rad. 27 moving
object tracks, real speed (20 fps). The gain sweep keeps the default damping ratio (ζ = 0.48).

| variant | kp / kd | tracks saturating | % moving frames saturated | median p95 z residual | static sag | lag kd/kp |
|---|---|---|---|---|---|---|
| default | 25 / 6 | 23 / 27 | 5.8 % | 20.5 cm | 11.8 cm | 0.24 s |
| hand reference advanced 0.24 s (velocity feed-forward) | 25 / 6 | 1 / 27 | 0.04 % | 15.1 cm | 11.8 cm | 0.24 s |
| + m·g/kp gravity offset on reference z while carried | 25 / 6 | 2 / 27 | 0.27 % | 9.9 cm | (offset) | 0.24 s |
| advance + gravity offset | 25 / 6 | 0 / 27 | 0 % | 4.3 cm | (offset) | 0.24 s |
| object mass 0.15 kg | 25 / 6 | 10 / 27 | 1.2 % | 14.2 cm | 5.9 cm | 0.24 s |
| kp 50 | 50 / 8.5 | 0 / 27 | 0 % | 11.4 cm | 5.9 cm | 0.17 s |
| kp 100 | 100 / 12 | 0 / 27 | 0 % | 6.6 cm | 2.9 cm | 0.12 s |
| kp 200 | 200 / 17 | 0 / 27 | 0 % | 3.8 cm | 1.5 cm | 0.085 s |
| kp 400 | 400 / 24 | 0 / 27 | 0 % | 2.3 cm | 0.7 cm | 0.06 s |
| stiff (shipped) | 6000 / 60 | 0 / 27 | 0 % | 0.3 cm | 0.05 cm | 0.01 s |

Rotation (ball wrist, residual = (I·α + d·ω)/k, I ≈ 0.011 kg m²): default k 25 / d 6 saturates 2/27 tracks (ep 13
blue cup, ep 26 pot flip), median p95 0.43 rad; k 100 / d 12 saturates 0/27 (0.21 rad); stiff 1200 / 60: 0.09 rad.

Readings:
1. [C] The default soft wrist spends most of its range on two predictable terms: the object's weight (11.8 cm) and
   damping lag (kd/kp = 0.24 s × speed). Both are known in advance from the reference, which is the textbook case for
   feed-forward. Removing either alone almost removes saturation; removing both leaves a 4 cm median demand.
2. [C] Raising kp to 50–100 (same damping ratio) removes saturation on every public track. The stiff variant overshoots
   what is needed by ~60×.
3. [E] Stiffness has a price that the residual model does not show. A reference error δ that points into the table
   or object becomes a force kp·δ: 0.25 N/cm at kp 25, 1 N/cm at kp 100, 2 N/cm at kp 200, 60 N/cm stiff (object
   weight is 2.9 N). Video references carry cm-level errors, so a soft wrist forgives them and a stiff one pushes
   objects. This is why feed-forward (exact for predictable loads, no extra stiffness) is attractive, and why an
   intermediate kp is the likelier sweet spot than the stiff variant [H].
4. [V+C] Reference-side feed-forward (time advance, gravity offset) is data-only but not free: the hand-keypoint reward
   (weight 0.25) and the 0.15 m wrist termination are measured against the shifted reference, so the wrist would sit
   up to v·τ ≈ 8–13 cm (advance) or 11.8 cm (gravity offset) away from its reference. Loosening the wrist termination
   in training is config; the evaluator has terminations off.
5. [C] Grip/load: the specific force a held object needs, |a − g|/g, stays within 0.84–1.25 on every moving track
   (median p05 0.90, p95 1.10). Human-paced carrying changes the felt weight by only ±10–25 %. Holding 0.3 kg at the
   worst load in a two-sided pinch needs a normal force of 1.8 N (mu 1.0) to 3.7 N (mu 0.5). [H] So anticipatory grip
   modulation from force feedback is unlikely to be the bottleneck in these clips; a steady grip with margin is enough,
   and the wrist range (above) is the first-order problem.

## D. Literature review

### D1. Control theory and carry-aware tracking (review agent, 2026-10-26; [V] = read in primary text or code)
- **Residual RL over a base controller** speeds learning and helps exploration: Silver 2018 (~10× fewer samples on
  Push with an MPC base), Johannink 2019 (hardware insertion 15/20 vs 2/20). SPIDER uses u = u_SPIDER + π(o) with
  MuJoCo position actuators at kp 1000 and `gravcomp` on the palm [V]. Low-gain feedback plus model feed-forward keeps
  compliant robots compliant (Della Santina 2017 [U]; "Keep soft robots soft" [V]). **No study measures gravity or
  m·a feed-forward under an RL residual on a soft floating wrist**; the case is first-principles plus residual-RL
  sample-efficiency results.
- **Gains.** Our kp 25 N/m is 12–14× softer than DexMachina's wrist (translation kp 300–350, rotation 60–80, hand
  gravity compensation 0.8) and 40× softer than SPIDER's [V code]. ManipTrans applies a policy-output 6-DoF wrench to
  a gravity-disabled wrist [V code]. VICES (Martín-Martín 2019): a fixed low impedance never solved path following
  because it "cannot exert high enough forces"; medium impedance learned fastest [V]. BeyondMimic: a 10 Hz natural
  frequency beat 5 and 25 Hz [V]. "Tune to Learn" (2026): RL reached 99 % at all corners of a 100× gain grid, but each
  gain needed its own hyperparameter tuning [V]. DexMachina found tighter wrist residual bounds learned better than
  looser ones, which argues against simply widening the 0.2 m clip [V, curves].
- **Look-ahead.** GMT: immediate frame + 2 s of future frames cut MPKPE 8.6 % (46.0 → 42.1 mm) [V]. UniTracker: 1 / 5
  / 10 / 20-frame windows give success 90.6 / 91.8 / 91.3 / 90.3 %, so the gain saturates near 5 frames [V].
  Omnigrasp feeds 20 future object frames (~1.3 s); InterMimic uses offsets {1, 2, 4, 16} [V]. Dexterous trackers
  (DexTrack, ManipTrans `obsFutureLength: 1`) use the next frame only; PHC calls that a limitation for fast motion [V].
  In FlashCHORD this needs code (§B).
- **Payload awareness.** RMA estimates payload from a 0.5 s history when mass is unknown (12 kg carried) [V].
  ManipTrans's privileged observation includes object weight, centre of mass, object velocities and fingertip forces
  [V code]. With one fixed, known mass per policy, estimation adds nothing; what transfers is a gravity term gated on
  grasp state, plus fast slip cues (object velocity, contact state). No paper conditions on an explicit carry phase.
- **Assist curricula (VOC analogues).** CHORD: VOC "can introduce local optima"; the contact-wrench reward must
  converge before VOC decays [V]. DexMachina decays VOC gains only when reward, slope, epoch and episode-length gates
  pass, spreads gains per environment, and found a fixed ManipTrans-style gravity ramp "no clear improvement" [V].
  Yu, Turk & Liu 2018: stepping assistance down within each rollout prevents overfitting to one assist level [V].
  No paper reports the final unassisted drop rate as a function of the anneal schedule.

### D2. Force and tactile feedback
Pending (review agent running).

### D3. Kalman filtering and physically consistent references
Pending (review agent running).

## E. Rules and integrity notes
- Gains, observation toggles, reward weights and terminations are training config that the evaluator replays from the
  checkpoint. Note 05 already treated non-default embodiment variants as a rules question; the stiff variant ships in
  the official repo. [H] An intermediate gain is the same kind of choice. Ask the organisers before submitting with it.
- Object mass is physics. Lowering it to make carrying easier would be gaming; leave the organiser placeholder (0.3 kg)
  unless they give real masses.
- Simulator code changes (force-magnitude observations, look-ahead, feed-forward wrench) alter the evaluator code
  digest. Treat them as off-limits for submissions unless the organisers allow them.
