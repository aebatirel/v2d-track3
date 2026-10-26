# 23 — Carry-aware control, force feedback and Kalman filtering for the policy stage (2026-10-26)

Status: COMPLETE (2026-10-26). Code study, carry model, three literature reviews, and an adversarial verification pass
(six checkers + a critic; verdicts in `docs/research/work/23/verify/`). Nothing was run in the simulator: every
policy-side effect below is a hypothesis until a GPU batch measures it.

Owner's question: can Kalman filters, control theory, physics-based path following while carrying, carry-aware methods,
or force feedback from the hand (a heavy object pushes back on the hand) help policy generation?

Labels: [V] read in source code or primary text, [C] computed here, [E] estimate, [H] hypothesis, [U] abstract or
secondary source only. Code: nvidia-isaac/video_to_data @ 8c778f905cb3 (evaluator pin),
`robotic_grounding/flash_chord/src/flash_chord/`. Model and reruns: `docs/research/work/23/` (README there).

## Summary (read first)
1. **The biggest lever is control theory, and it is config-only [C, H].** The floating wrist is a very soft spring
   (kp 25 N/m, natural frequency ≈ 0.64 Hz with the object). At real playback speed it spends its 0.2 m action range on
   two predictable terms: the object's weight (11.8 cm of sag) and damping lag (0.24 s × speed). On the 27 moving public
   object tracks it saturates on 23. kp ≥ 100 (with companion settings, §B) removed saturation in every sensitivity
   rerun. Comparable systems run much stiffer wrists (DexMachina 300–350 N/m). Which stiffness tracks best on
   video references is open and needs the G1 sweep (§E).
2. **The ball wrist is heavily over-damped** (damping ratio ≈ 4–5.5). Lowering only its damping to 1.5–3 N m s/rad
   removed rotation saturation in the model (config-only) [C].
3. **Force feedback: the hand already feels a lot [V].** The policy sees where each finger link touches the object and
   which way the contact force pushes (unit direction, not magnitude). With the soft wrist, the weight shows up as an
   11.8 cm wrist position error the policy observes, so the PD error acts as a weight sensor. The literature finds force
   magnitude adds little over location or direction, though no study isolates it. Exposing magnitude needs simulator
   code, so it is not for submissions. It does make a good Innovation story: the real Sharpa Wave has fingertip 6-axis
   force sensing, and Sharpa's own TacBPM policy uses 5 contact magnitudes + 5 contact points.
4. **Cheap slip sense [V, H]:** the actor does not see object velocity, but the critic does. Turning it on for the actor
   (`observation.object_body_velocity.enabled=true`) gives a slip signal at no code cost.
5. **Carry-aware: the load is known [V].** Every object is 0.3 kg in training and in evaluation. That calls for
   feed-forward or stiffness, not estimation. The felt weight during human-paced carrying stays within 0.73–1.25 g [C].
6. **Kalman filtering belongs in the reference, not the policy [V].** The simulator gives the actor exact, noise-free
   state, so a policy-side filter has nothing to do. Our object paths from `perc2.py` are raw per-frame poses with no
   smoothing. A robust smoother over the whole clip is promising: windowed estimators beat per-frame ones in the
   literature (Zorina 2024 YCB-V ADD(-S) 0.84 → 0.90). Rest segments should be held fixed on the table and carried
   segments tied to the hand. Smoothing removes jitter only: drift, wrong detections and symmetric flips need their own
   fixes (notes 17, 18).
7. **Physics-based path following while carrying: the reference itself can sabotage the carry [V code, H effect].**
   - Contacts in our reference are recomputed from the retargeted hand with an 18 mm threshold. If the MediaPipe hand
     drifts more than 18 mm from the object during a carry, the reference says "no contact". The −10
     unintended-contact penalty then punishes exactly the grip the carry needs.
   - Frame 0 is reset with zero velocity, so any penetration or hover in frame 0 pops at t = 0 of the scored rollout.
   - Tying the wrist reference to the object during carries (object pose × a fixed grasp transform) addresses both.
8. **Start mismatch [V].** Training resets hold the reference still for 1 s with full assist and partly opened fingers.
   The evaluator starts at frame 0 with no hold, no assist and exact fingers. No reset setting reproduces the eval
   start exactly.
9. **Simulator physics caveat [V].** FlashCHORD uses a pyramidal friction cone with impratio 20. MuJoCo's docs advise
   against high impratio with pyramidal cones and warn that soft contacts can slowly slip. Physics settings replay
   unchecked into the scored rollout, so they are off-limits without organiser approval. Measure slip, don't tune it.
10. **Plan (§E).**
    - Step 1, CPU, ≈ $0: a reference feasibility and contact-label audit.
    - Step 2, a smoothing test on perc2 outputs. These need regenerating on the first box: they are not in the repo.
    - Step 3, GPU batch G1: wrist gains, ball damping and a policy bundle on 4 public carry episodes.
      - Full design: 30 runs, ≈ 50–60 GPU-h, ≈ $75–100 on demand.
      - Smaller first slice: 16 runs, ≈ $35–55.
      - Needs the owner's go-ahead and the day-1 smoke and resume tests.

## A. What the simulated hand can already sense [V code]
- **Policy observation** (`envs/observation.py`, `configs/observation/policy.yaml`):
  - wrist pose and velocity;
  - finger joint positions and velocities;
  - object pose;
  - reference minus current state for the wrist, fingers and object (one reference frame; the clock advances before
    the observation is built, so the actor sees ref(t+1) − state(t), the frame its next action targets);
  - previous raw and processed action;
  - **live contact slots**.
- **Live contact slots** (`runtime/contact.py`): for every (hand link, object body) pair, the mean contact point in the
  wrist frame and the **unit direction** of the summed contact force. The simulator computes the magnitude
  (`contact_force_w`), but the observation keeps only the direction. The slots are zeroed at episode step 0, including
  the evaluator's first step (`observation.py:665-667`).
- **The PD error is a load sensor.** The soft wrist (kp 25 N/m) sags 11.8 cm under the 0.3 kg object, and the policy
  sees the gap in `command_wrist`. `processed_action` gives one step of memory, so a memoryless MLP can still hold the
  constant residual this needs. The signal scales as 1/kp: 2.9 cm at kp 100, 0.05 cm with the stiff variant. It also
  mixes table contact with object load, and it is ambiguous once the residual is clipped.
- **Not in the actor's observation:**
  - future reference frames beyond the next one;
  - object velocity (the term exists, `object_body_velocity`, but is disabled);
  - force magnitudes;
  - slip;
  - frame history beyond the previous action.
- **The critic is asymmetric** (`configs/train_flash_sac.yaml:26-31`, `envs/rl.py:66-112`,
  `training/flash_sac/learner.py:568,709-710`). It also gets:
  - applied VOC, target VOC and settling progress;
  - the reference phase t/(T−1);
  - each object body's world linear and angular velocity.
  Confirm this in our checkpoint's resolved config.
- **No observation noise** exists in the port (CHORD also disabled corruption). The actor reads exact simulator state.

## B. Levers in config, and their traps [V code]
The evaluator rebuilds the environment from the checkpoint's own resolved config. It overrides only:
- VOC (scale 0, max force/torque 0);
- the reset (frame 0, `voc_decay_steps` 0, seed 42);
- world count and auto-reset;
- terminations;
- deterministic (mean) actions;
- the checkpoint's curriculum stage, re-applied with VOC 0.

Everything else is replayed unchecked: embodiment, action, observation, objective, and also all of `sim`,
`scene.contact_friction`, object damping, object scale and `action.delay` (`evaluation/harness.py:216-272,377-465`).
`sampled_settled` evaluation raises a TypeError with the Sharpa reset, so it is not an option.

- **Wrist translation gains:** `embodiment.config.joint_overrides["wrist_[xyz]$"]` (default kp 25, kd 6, effort 45 N).
  Verified recipe (Hydra composition and evaluator rebuild tested with the pinned hydra-core 1.3.2 / omegaconf 2.3.1):
  - Commit an embodiment yaml in our repo and pass `--config-dir <dir>` (before or after all overrides, never between
    them) with `embodiment=<name>`. The checkpoint stores the resolved dict, so the evaluator needs no extra file.
    Example:
    ```yaml
    _target_: flash_chord.embodiments.sharpa_hands.SharpaHands
    config:
      _target_: flash_chord.embodiments.sharpa_hands.SharpaHandsConfig
      joint_overrides:
        'wrist_[xyz]$': {kp: 100.0, kd: 12.0, effort_limit: 45.0}
        'right_wrist_y': {default_pos: 0.25}
        'left_wrist_y': {default_pos: -0.25}
        'wrist_z$': {default_pos: 0.5}
        'wrist_rotvec$': {mode: effort, kp: 100.0, kd: 12.0, effort_limit: 45.0}
    ```
    plus `action.wrist_kp=100.0 action.wrist_tau_max=100.0`.
  - **Traps:**
    - The dict replaces the whole default, so list all five entries. Without `wrist_rotvec$` the ball wrist silently
      becomes position-controlled at kp 1.7 / kd 0.1.
    - Without `effort_limit` the axis falls to 10 N, below the 12.2 N hand weight that gravity compensation routes
      through the same actuator range.
    - At effort 45 N, z headroom is ≈ 33 N, so kp above ≈ 165 needs a higher effort limit.
    - Never use overlapping regexes that set the same field: the saved JSON sorts keys, so training and evaluation
      would resolve different gains (demonstrated).
    - The `stiff_tracking` classmethod target cannot be extended.
    - After training, read `embodiment.config.joint_overrides` and `env.action.wrist_kp` back from the checkpoint
      metadata.
- **Ball wrist:**
  - Spring gain is `action.wrist_kp` (25). The embodiment `wrist_rotvec$` kp is ignored.
  - Torque is clamped per axis at `action.wrist_tau_max` (45 Nm), so k 100 needs tau_max ≥ ≈ 80–100.
  - Passive damping is the embodiment `wrist_rotvec$` kd (6).
  - The shipped stiff variant: prismatic kp 6000 / kd 60 / effort 2000, ball wrist_kp 1200 / tau_max 2000. Its
    docstring says it was tuned for 200 Hz physics and collision-free replay; RL runs at 100 Hz. Its prismatic damping
    ratio is ≈ 0.31.
- **Actor object velocity:** `observation.object_body_velocity.enabled=true`. The CLI override survives into evaluation.
- **Rewards:**
  - These terms follow `objective.*.weight`: `force_closure` (wrench-direction coverage; disabled),
    `contact_force_l2` (L2 or log-RMS contact force; disabled; log mode rewards *lower* force at positive weight),
    `contact_wrench_support`, and the action terms. Both `enabled` and `weight` must be set.
  - The curriculum hard-codes object_keypoints 20, hand_keypoints 0.25, hand_joint_pos 0.25, missed_contact −1,
    unintended_contact −10 and termination −100, overriding the objective weights at start. Change those through
    `curriculum.stages.N.objective_weights.*`.
  - The wrench-support model uses friction 0.1, while the scene uses 1.0.
- **Terminations (training only):** `termination.wrist_position.threshold` 0.15 m (Euclidean), object 0.10 m / 0.5 rad.
- **Assist (VOC):** `env.voc.{k_lin,d_lin,k_ang,d_ang}` are config. Zeroing them gives a gravity-only assist on the
  same schedule. Separate schedules for the PD and gravity parts would need code.
- **Reset:**
  - `reset.voc_decay_steps` (20; global, not per stage) holds the reference clock with VOC 1.0 after every training
    reset.
  - `reset_finger_openness` (0.7) opens the fingers by U(0, 0.7).
  - The last stage starts 50 % of episodes at frame 0, but with that hold.
  - No setting reproduces the exact eval start (finger scale is always U(0, openness) < 1).
- **Object mass** comes only from the object URDF. All organiser URDFs say 0.3 kg, called a placeholder. Our spoon
  URDF is also 0.3 kg.
- **Reference contents** (the parquet is ours): wrist/finger paths, contacts and object paths. The residual is added to
  the reference, so shifting the wrist path in time or offsetting it in z changes the PD targets. Translation residuals
  are in the world frame. Rotation residuals are RPY in the reference wrist's local frame.
- **Needs code:**
  - wrist feed-forward wrench;
  - PD target velocities (the `arm_position_integral` path covers only arm joints, not Sharpa);
  - force-magnitude observations;
  - multi-frame look-ahead (the only future-frame code is the G1 SONIC encoder);
  - frame stacking;
  - CHORD-style wrench perturbations;
  - an exact-start reset mode.

## C. Carry model on the public GT paths [C]
`work/23/carry_model.py` gives the per-axis residual the policy must hold so the wrist follows the object path exactly:
- the PD law is F = kp·e − kd·v;
- the hand is 1.243 kg and gravity-compensated; a 0.3 kg object is added on moving frames;
- the clip is 0.20 m per axis;
- 27 moving object tracks, real speed (20 fps);
- the gain sweep keeps the default damping ratio ζ = 0.48;
- sensitivity reruns are in `work/23/verify/`:
  - Savitzky-Golay smoothing window 5–13;
  - hand mass ±30 %;
  - usable clip 0.15–0.18 m;
  - wrist pivot offsets 5–15 cm;
  - hand-COM coupling.

**It is a lower bound on wrist demand:**
- the GT object frame stands in for the wrist;
- only moving frames count, and reach phases are excluded;
- perception references are noisier than GT.

NVIDIA's canonical recipe runs `motion_speed` 0.5. We must run 1.0 (note 06), which doubles the lag term and
quadruples the inertial term relative to the regime the default gains came from.

| variant | kp / kd | tracks saturating (nominal SG-9) | under sensitivity reruns | median p95 z residual | static sag | lag kd/kp |
|---|---|---|---|---|---|---|
| default | 25 / 6 | 23 / 27 (5.8 % of moving frames) | 22–27 / 27 | 20.5 cm | 11.8 cm | 0.24 s |
| hand reference advanced 0.24 s | 25 / 6 | 1 / 27 | 7–21 / 27 | 15.1 cm | 11.8 cm | 0.24 s |
| + m·g/kp offset on reference z while carried | 25 / 6 | 2 / 27 | 7–18 / 27 | 9.9 cm | (offset) | 0.24 s |
| advance + gravity offset | 25 / 6 | 0 / 27 | 0–5 / 27 | 4.3 cm | (offset) | 0.24 s |
| kp 50 | 50 / 8.5 | 0 / 27 | 1–9 / 27 (marginal) | 11.4 cm | 5.9 cm | 0.17 s |
| **kp 100** | 100 / 12 | 0 / 27 | **0 / 27 in every rerun** | 6.6 cm | 2.9 cm | 0.12 s |
| kp 200 (needs effort > 45 N) | 200 / 17 | 0 / 27 | 0 / 27 | 3.8 cm | 1.5 cm | 0.085 s |
| stiff (shipped) | 6000 / 60 | 0 / 27 | 0 / 27 | 0.3 cm | 0.05 cm | 0.01 s |

The object-mass row (0.15 kg: 10/27) is in `carry_model.txt` for reference only. Mass is physics, not a lever (§F).

**Rotation.** The ball wrist needs a spring torque of I·α + d·ω, with I_eff ≈ 0.012–0.025 kg m² (the damping term
dominates, so I barely matters):

| ball wrist k / d / tau_max | damping ratio | tracks saturating | median p95 residual |
|---|---|---|---|
| default 25 / 6 / 45 | ≈ 3.8–5.5 | 2 / 27 (ep 13 blue cup, ep 26 pot flip) | 0.43 rad |
| 25 / 3 / 45 | ≈ 1.9–2.7 | 0 / 27 | 0.21 rad |
| 25 / 1.5 / 45 | ≈ 0.95–1.4 | 0 / 27 | 0.11 rad |
| 100 / 12 / 45 | ≈ 3.8–5.5 | 2 / 27 (torque clamp → effective clip 0.45 rad) | 0.21 rad |
| 100 / 12 / 100 | ≈ 3.8–5.5 | 0 / 27 | 0.21 rad |
| 100 / 4 / 45 | ≈ 1.3–1.8 | 0 / 27 | 0.07 rad |

**Readings:**
1. [C] The default soft wrist spends its range on two predictable terms, weight and damping lag. Either feed-forward
   alone cuts saturated frames 5–20× at nominal assumptions but stays fragile. Only the combination is robust.
2. [C] kp ≥ 100 removes clip saturation robustly; kp 50 is marginal. This is a saturation-only model: it does not
   measure tracking precision, noise rejection or contact behaviour, so it cannot pick the best gain above 100.
3. [E] **Stiffness trade-off.** A reference error δ pointing into the table or object becomes a force kp·δ:
   - 0.25 N/cm at kp 25;
   - 1 N/cm at kp 100;
   - 60 N/cm stiff;
   - for scale, the object weighs 2.9 N.

   A soft wrist may therefore forgive cm-level video errors that a stiff one turns into pushes. But the policy sees
   contacts and can cancel δ, and the literature points stiffer: DexMachina runs 300–350 N/m with a narrow residual,
   and BeyondMimic's heuristic applied to this hand gives ≈ 6000 N/m. "Intermediate is best" is unproven; the G1 sweep
   decides.
4. [C] **Reference-side feed-forward conflicts with the wrist termination.** The hand-keypoint reward (weight 0.25)
   and the 0.15 m wrist termination are measured against the shifted reference:
   - advance alone puts the wrist 5–13 cm (per-track p95) from its reference;
   - gravity offset alone puts it 11.8 cm away;
   - the combination puts it 18.6 cm (median-track p95) to 26.7 cm (peak) away. That exceeds 0.15 m on every track,
     in ≈ 18 % of moving frames, so it needs `termination.wrist_position.threshold` ≥ ≈ 0.3 m in training.
5. [C] **Grip/load.** The specific force a held object needs, |a − g|/g, has a per-track p05–p95 band of 0.84–1.17.
   Frame extremes are 0.73–1.25 (SG-9) or 0.65–1.28 (SG-7). Holding 0.3 kg at the worst load in a two-sided pinch
   needs:
   - 1.8 N normal force at μ 1.0, or 2.6 N on the pyramid's μ/√2 diagonal;
   - 3.7 N at μ 0.5;
   - this ignores off-COM torque (pot handles).

   Finger joints default to kp 1.7 Nm/rad and effort 10 Nm [V], which looks ample [E]. [H] Anticipatory grip
   modulation is second-order for these clips, but this is untested in simulation and the spoon (thin handle, 10 of
   20 eval episodes) is not modelled.

## D. Literature (corrected after verification)

### D1. Control theory and carry-aware tracking
- **Feed-forward under a residual policy.**
  - Residual RL speeds learning:
    - Silver 2018: ≈ 10× fewer samples to reach 0.9 success on Push, but about the same time to perfect success as
      DDPG+HER; the authors credit exploration [V].
    - Johannink 2019: 15/20 vs 2/20 on hardware insertion, compared with the base controller alone, not with RL from
      scratch [V].
  - Low-gain feedback plus model feed-forward keeps compliant robots compliant: Della Santina 2017 [U]; "Keep soft
    robots soft" [U].
  - **No study measures gravity or m·a feed-forward under an RL residual on a soft floating wrist.**
- **How others drive the floating wrist.**
  - DexMachina:
    - wrist translation kp 300–350 N/m (kv 4–20);
    - rotation kp 60–80 on 6 of 7 hands and 200 on Dex3;
    - hand gravity compensation 0.8 [V code];
    - its tighter wrist residual bounds (±0.04–0.1 m) beat looser ones (Fig. 8, no curriculum, task/hand subset,
      3 seeds) [V]. Those bounds sit on stiff wrists (≈ 12–35 N of residual force vs our 5 N), so the lesson is
      "stiff gains plus a narrow residual".
  - ManipTrans: gravity is disabled on the whole hand (damping 20); the policy outputs a 6-DoF wrench; object weight,
    COM, velocities and tip forces go to a shared actor-critic [V code].
  - SPIDER: its kp-1000 MuJoCo base with palm gravcomp belongs to the sampling-based retargeting optimizer. v3 says the
    dexterous policy does *not* use SPIDER control as a residual [V].
  - CHORD: the paper names a "wrist force/torque tracking controller" with 0.05 m / 0.15 rad scales and EMA 0.3, but
    gives no gains [V].
- **Gains in RL tracking.**
  - VICES (Martín-Martín 2019): fixed low impedance failed both path following and door opening. "Cannot exert high
    enough forces" is stated only for the door (door friction). Fixed medium impedance learned the door faster than
    variable impedance [V].
  - BeyondMimic: kp = Iω², kd = 2Iζω with ω = 2π·10 rad/s and ζ = 2. 10 Hz beat 5 Hz on global tracking; 25 Hz had
    lower local error but was rejected for hardware wear [V]. Applied to our 1.54 kg hand + object, this gives
    kp ≈ 6.1e3 N/m, the stiff variant's stiffness [C].
  - "Tune to Learn" (2026): RL reached 99 % at all four corners of a 100× Kp/Kd grid, given per-gain tuning of mostly
    action scale and mode [V]. So a gain change should come with an action-scale/clip check.
- **Look-ahead (code for us).**
  - GMT: immediate + 2 s of future frames cut AMASS MPKPE 46.0 → 42.1 mm (−8.6 %) [V].
  - UniTracker: a 5-frame window best balanced success (91.8 %; MPKPE lowest at 10), measured on its training set [V].
  - Both are whole-body humanoid results.
  - Omnigrasp (20 future object frames) and InterMimic ({1, 2, 4, 16}): [U, not re-verified].
- **Payload awareness.** RMA estimates payload from history when mass varies [U, not re-verified]. With one fixed,
  known mass per policy, estimation adds nothing.
- **Assist curricula.**
  - CHORD: VOC "can introduce local optima"; the contact-wrench reward must converge before VOC decays. Every reset
    restores VOC 1.0 with a 20-step warm-up [V].
  - DexMachina's own reimplementation of a ManipTrans-style decaying curriculum (thresholds, gravity, friction) showed
    "no clear improvements" and dropped as gravity returned [V]. Its VOC gating rules: not re-verified.
  - No paper reports the final unassisted drop rate as a function of the anneal schedule.

### D2. Force and tactile feedback
- **Touch helps most when the object state is poor, but not only then.**
  - Rotating without Seeing, sim, unseen physics: no sensors 369 vs binary touch 919 rotation reward (seen physics
    689 vs 964). On the real robot, binary beat continuous [V].
  - RotateIt: binary adds nothing over proprioceptive history; contact location ≈ full contact [V].
  - Counterexample: Melnik 2021, where the state already includes object pose and velocity, still gains from touch
    (Block 0.30 → 0.43/0.44, Pen 0.27 → 0.32) [V].
  - TacBPM (Sharpa 2026, single 22-DoF SharpaWave hand):
    - input is 3 stacked frames of joints, previous targets, 5 smoothed fingertip contact magnitudes and 5 contact
      positions;
    - success 40.05 % with tactile zeroed vs 60.38 %, on unseen shapes/scales [V];
    - whether it reports drop rate with vs without touch: unchecked.
- **Force magnitude.** No cited study isolates magnitude:
  - RotateIt: full vs location, +1.9 % on x, inside the std;
  - Koenig 2022: normal force vs binary +2.9 points; full vs normal not significant;
  - AnyRotate: +6 % on OOD mass only;
  - Melnik: binary ≈ continuous [V].
  - ManipTrans uses fingertip forces as privileged inputs and reward [V].
- **History.** Hora's drop from T3 176 to T20 43 is the domain-randomisation baseline feeding flattened history to the
  PPO MLP; Hora's adaptation module improves with history [V]. Enabling object velocity is the cheaper slip signal.
- **Human grip-load coupling.**
  - Flanagan & Wing 1997 (precision grip, simulated loads): GF/LF 2.95–3.07 under the 1.41 kg inertial load,
    2.25–3.07 across loads; GF rate leads LF rate by 14 ms (−3 to 21 ms) [V].
  - Hiramatsu 2015 (PLoS One): typical safety margin 20–50 % of grip force, ≈ 40–50 % for objects ≥ 100 g [V].
  - No RL paper uses a GF/LF or friction-margin reward [not found].
- **Simulator contact physics.**
  - FlashCHORD uses `cone: pyramidal`, `impratio: 20.0` [V config].
  - MuJoCo docs [V]: impratio's "harder friction" is defined for elliptic cones; high impratio is not recommended with
    pyramidal cones; gradual slip cannot be fully avoided with soft contacts. The remedy is elliptic cones + large
    impratio + a small Newton tolerance, then NoSlip.
  - In code, pyramidal impratio scales every edge row, which stiffens the whole contact rather than friction relative
    to normal [V].
  - NoSlip raises NotImplementedError in the pinned mujoco-warp 3.8.1 [V].
  - Pyramid edges inscribe the cone, so diagonal friction capacity is μ/√2 [C; condim 3 assumed, none is set].
  - Contacts are read once per 20 Hz step after the last substep [V].
  - GPU MuJoCo-Warp is not deterministic [V]. A determinism option was merged into main on 2026-10-22, after the pin.
- **Rewards.**
  - CHORD Table 2: contact-wrench 0.918 AUC vs position-only 0.862 vs none 0.774 (Isaac Lab, not the port) [V].
  - Force closure is flatter across noise but below wrench guidance at low noise (Fig. 9); "reduces dexterity" is
    unquantified [V].
  - CHORD trains with object-wrench perturbations sampled from the human contact wrench matrix (one sentence, no
    magnitude); the port lacks them [V].
- **Real hardware (Innovation story).**
  - Sharpa Wave fingertip "Dynamic Tactile Array": 6-axis fingertip F/T, 0–30 N, 20 ms latency (official spec,
    sharpa.com/pages/wave) [V]. Per-finger torque sensing: press only [U].
  - NVIDIA's CHORD hardware runs are state-based [U].
  - [H] Contact channels shaped like TacBPM's would make our policy interface deployable on real Wave hardware.

### D3. Kalman filtering and physically consistent references
Our state [V code]:
- `perc2.py` applies **no temporal smoothing** to object poses.
- `hands_mp.py` smooths hand keypoints (zero-phase Savitzky-Golay, window 7).
- `mkref.py` snaps resting objects onto the table at frame 0 (constant per-object z shift ≤ 2 cm), fills hand gaps
  (hold, or ride along with an object), and recomputes contacts (16 probes, 18 mm).
- The wrist and object paths are filtered independently, so they can show spurious hand-object relative motion during
  carries.

Literature:
- **Windowed estimation beats per-frame estimates.**
  - Zorina 2024 (online, causal 1 s factor graph; outlier gate 100 mm / 10°; view-ray covariance): YCB-V ADD(-S)
    0.84 → 0.90 over per-frame CosyPose; a 3-frame window gave no change on the real datasets; constant-pose beat
    constant-velocity on static scenes; code BSD-2 [V].
  - Yu & Rodriguez 2018 (vision + touch + pushing model): a one-step EKF worsened rotation vs raw AprilTag
    (3.4° → 6.4°); a 1000-step history reached 6.1 mm / 1.8° [V].
  - The only offline evidence: Hasson 2021, where removing the temporal smoothness term raised HO-3D object ADD-S
    3.8 → 8.3 cm [V], plus a toy run (white noise + outliers: causal KF −25 % RMSE, offline RTS −55 %, Student-t
    RTS −70 %; `work/23/toy/smooth_sim2.py`) [toy].
  - Since our clips are offline, a full-clip smoother is available; no published study compares it with causal
    filtering on egocentric clips.
- **Smoothing removes jitter, not bias.** Over-smoothing lags fast lifts: 30–44 mm worst case on a 0.25 s lift with
  too little process noise [toy]. Unroll quaternion signs and the object's symmetry group before filtering.
- **Rest and carry modes.**
  - No IMM application to rest/carry of video objects was found.
  - ZUPT practice (zero-velocity updates stop drift growth) [U].
  - Hand-object coupling:
    - ComPose 2026: DexYCB rotation 35° → 19.5° by blending object and hand cues [V];
    - EgoGrasp 2026: contact/no-slip term cut H2O translation error 107 → 78 mm [V].
  - The 100DOH detector labels portable vs stationary contact [U].
- **Cleaner references and RL success** (confounded, cross-method):
  - SPIDER: a policy trained on the physics-retargeted reference reached task progress 0.99 vs 0.07 on the kinematic
    one. This is one tabletop cup task; the kinematic reference let the cup drift out of the hand; SPIDER's control
    also initialised the policy [V].
  - GMR 2025: ground penetration gave 0 % vs 100 % success on specific G1 motions; joint jumps 96 % / 51 %;
    self-intersection 20–40 % [V].
  - CHORD's QC (reject > 2 cm hand-object/hand-hand overlap; a 300-step crash check) has no QC-vs-success measurement.
  - **No study varies object-reference smoothness and measures dexterous RL success**; our Track 2 analysis (note 14)
    is the closest.

## E. Ranked plan
All effects are hypotheses. Develop on public episodes only; carry gates, offsets and smoother settings must come from
perception, be tuned on public episodes and be frozen before eval.

**Batch G1 design:**
- Episodes: public 11, 23, 13 and 42 (the most saturated under default gains), plus 27 as a low-demand control.
  Perception references.
- Metrics:
  - evaluator AUC/SP/MP against our own reference;
  - kit AUC against public GT;
  - drop events, wrist-to-reference gap and clip saturation from the exported rollout;
  - error in the first 2 s.
- Decision rule: keep a lever only if its sign is consistent on ≥ 3 of 4 carry episodes, then run a second seed on the
  top two arms.

| # | Lever | Type | Mechanism | Falsifier | Cost / batch |
|---|---|---|---|---|---|
| 1 | **Wrist gains**. A0 default kp 25; A1 kp 100 / kd 12 + ball k 100, tau_max 100 (all five overrides, effort 45); A2 kp 300 / kd 30 + effort ≥ 100 N, ball 300 / tau_max 300; A3 shipped stiff | config | Removes clip saturation and lag, so the residual becomes near-kinematic | A1–A3 fail to beat A0 on ≥ 3/4 episodes. If A3 ≥ A1 on perception references, prefer the official stiff variant (lower rules exposure) | G1 core |
| 2 | **Reference feasibility and contact-label audit**: frame-0 penetration/hover; > 2 cm hand-object overlap; object jumps > 10 cm; carry frames with no reference contact; wrist-object relative-pose spread during carry | reference, CPU | Finds references that force drops or penalise the grip | Flags near zero, or they do not predict G1 failures | ≈ $0, before G1 |
| 3 | **Robust offline object smoother + per-segment rest/table snap** (Lie-group, Student-t; extends mkref's frame-0 snap) | reference, CPU | Removes jitter and resting creep | Kit AUC vs GT changes by ≤ +0.005 over the 20 public episodes, so stop. Needs perc2 poses regenerated on the first box | CPU; GPU only if it passes (G2) |
| 4 | **Hand-object attachment during carry**: wrist reference = object pose × per-segment grasp transform from perception; blend at grasp and release; recompute contacts | reference | Consistent hand and object references, no false "no contact" labels | Lever-2 audit shows spread < 1 cm / 5° and no contact gaps, or no drop reduction in G2 | G2 |
| 5 | **Ball-wrist damping** to near-critical (`wrist_rotvec$` kd 1.5–3 at k 25) | config | Removes rotation lag without extra stiffness | No rotation-error drop on ep 13, or oscillation | G1 (A4) |
| 6 | **Start alignment**: final-stage `reset_to_first_frame_probability` 0.8, `reset_finger_openness` 1.0 | config | Trains closer to the scored start | First-2-s eval error not elevated, and no gain in the bundle | G1 (A5) |
| 7 | **Actor object velocity** (`observation.object_body_velocity.enabled=true`) | config | Slip signal for the actor (the critic already has it) | No change in drops | G1 (A5 = A1 + 6 + 7) |
| 8 | **Reference-side feed-forward**: advance τ = kd/kp + gravity offset while carried (gate from perception), wrist termination ≥ 0.3 m | reference + config | Fallback if the organisers reject non-default gains | A6 at kp 25 no better than A0 | G1 (A6) |
| 9 | **Contact rewards**: force closure at a small weight, or a higher wrench-support weight | config | Grasps that resist all wrench directions | No drop reduction | G2, low prior |
| 10 | **Code-level, not for submission without organiser approval**: force-magnitude / TacBPM-shaped observations (Innovation story), 5-frame look-ahead, wrench perturbations, exact-start reset, wrist feed-forward wrench | code | — | — | later |

**Cost (estimates).** One 250M-step run takes ≈ 1.7–2 GPU-h at the measured 45,300 steps/s, i.e. ≈ $2.5–3.3 on demand.
| Batch | Runs | GPU-h | On demand | Interruptible (after the resume test) |
|---|---|---|---|---|
| G1 full (4 carry episodes × 7 arms + control episode 27 × A0/A1) | 30 | ≈ 50–60 | ≈ $75–100 | ≈ $30–35 |
| G1 first slice (A0, A1, A3, A4 on 4 episodes) | 16 | ≈ 27–32 | ≈ $40–55 | — |
| Optional oracle-reference arms (A0/A1/A3) | +12 | — | ≈ $30–40 | — |

The oracle arms test the stiffness × reference-error interaction on public episodes only. G1 needs the owner's
go-ahead, the day-1 smoke and resume tests, and working `hands_mp` → `mkref` references.

**Physics-first screen before any training (added 2026-10-26 after the owner asked to use physics to cut training).**
- FlashCHORD ships a zero-residual replay (`runtime/replay.py` `ReplayRunner`; `scripts/debug/replay.py` is a viewer
  wrapper). It drives the hands along our reference with no policy and an optional VOC.
- Replaying each public reference with VOC 0 under the default wrist, kp 100 and the stiff variant (at `sim=rl`,
  `motion_speed` 1.0) measures how much of each episode physics alone already carries, with no learning [H]. It needs a
  small headless wrapper of our own (diagnostic only, not a submission path) and seconds of GPU per episode.
- Then train only where replay fails, and test a shorter schedule where the controller already does most of the work.
  Residual RL learns faster when the base controller is good (Silver 2018: ≈ 10× fewer samples to reach 0.9 on Push),
  so a compressed curriculum is plausible with a stiffer wrist [H].
- Warm-starting from another episode's policy is native (same observation layout needed) [V note 05; effect H].
- RL cannot be skipped entirely: the evaluator accepts only trained FlashSAC or PPO checkpoints [V note 05].
- Why the standard recipe needs this: NVIDIA's recipe plays references at `motion_speed` 0.5, where the default soft
  wrist saturates on 0/27 public tracks (note 14). We must play at 1.0 (note 06), where it saturates on 23/27 (§C).
  Stiffening the controller restores the regime NVIDIA validated; everything else in the recipe stays standard.

**Staged alternative (preferred after the owner's cost question, 2026-10-26).** Per-policy costs come from the
2026-10-20 Vast snapshot [E]: ≈ $2.2–3.3 on demand, ≈ $0.6–1.0 interruptible.
1. CPU audit (lever 2): $0.
2. Ride on day 1: add one arm (A1 + ball damping) next to the planned default runs on eps 12, 22 and 27. That is +3 runs,
   ≈ $7–10 on demand.
3. Only if step 2 shows a signal, or is ambiguous: 2–4 episodes × 2–3 arms = 6–12 runs, ≈ $15–40 on demand or ≈ $5–12
   interruptible.
4. Run the full G1 only if the results are mixed.

Each run must train from scratch to at least the unassisted phase: VOC is off only after 122.9M of the 250M steps. A
compressed curriculum (all thresholds × 0.5, ≈ 1 h per run) could halve screening cost. That is an untested
hypothesis: the arm ranking may not carry over to the full schedule.

## F. Rules and integrity
- Gains, observation toggles, reward weights and terminations are training config that the evaluator replays from the
  checkpoint. The stiff variant ships in the official repo; non-default gains are the same kind of choice. Ask the
  organisers before submitting with them, and commit the embodiment yaml (provenance).
- **Physics settings replay unchecked:** `sim` (cone, impratio, substeps), `scene.contact_friction`, object damping,
  object scale and `action.delay`. Treat them as off-limits. Never use object scale or delay as training domain
  randomisation: it would also apply to the scored rollout.
- Object mass is physics. Keep the organiser placeholder (0.3 kg) unless they give real masses.
- The evaluator code digest hashes only `flash_chord/evaluation/{__init__,harness,metrics,rollout}.py`, and the kit's
  accepted-digest allowlists are empty. So changes elsewhere (observation, control, reset) would not show in a digest,
  but they would break or alter an official re-run, and a new config key fails `instantiate_typed`. Code-level levers
  stay off-limits for submissions without organiser approval.
- Ground truth: the carry model and the audits use public GT for diagnostics only. Any carry gate, advance or smoother
  setting used on eval episodes must come from perception.
- GPU physics is non-deterministic: keep the first evaluation of each checkpoint.

## G. Verification record (2026-10-26)
- **Six checkers** (control literature, CHORD/SPIDER, touch, Kalman + MuJoCo docs, simulator code, carry model) each
  tried to refute the draft. A critic then reviewed the draft against all verdicts.
  - Verdicts: `work/23/verify/verdicts.json`. Critic report: `work/23/verify/critic-report.md`.
  - Reruns: `work/23/verify/*.py` and `*.txt`. The simulator code was checked at video_to_data 7eb9721, whose flash_chord
    tree is identical to the pin.
- **Main corrections to the draft:**
  - the critic is asymmetric, not symmetric;
  - kp 50 is marginal and either feed-forward alone is fragile;
  - ball k 100 needs `wrist_tau_max` raised;
  - advance + gravity offset breaks the 0.15 m wrist termination;
  - SPIDER is not residual RL over its kp-1000 base;
  - BeyondMimic's heuristic points to the stiff variant, not an intermediate gain;
  - the D3 evidence is windowed (online), not offline-vs-causal;
  - the code digest covers only the evaluation modules;
  - a gravity-only VOC is config.
- **New from the critic:** the ball wrist is over-damped; the unintended-contact penalty can fire during carries; and
  the list of physics knobs that replay unchecked.
- **Not verified** (marked [U] above): Omnigrasp/InterMimic horizons, RMA details, DexMachina VOC gates, Khandate,
  Sievers, the slip reflex, the KF-on-FoundationPose paper, the 100DOH numbers, OmniRetarget, MaskedManipulator's
  10 cm rule, Wahlström & Skog, and whether TacBPM reports drop rates with vs without touch.
