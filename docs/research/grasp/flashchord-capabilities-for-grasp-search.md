# FlashCHORD and repository capabilities for designed grasps and an evolutionary grasp search

2026-10-24, CPU only. No rentals, no spending, no commits. This is the workflow step "FlashCHORD capabilities for grasp
search" of the owner's option 2: one recipe, grasp-lock, with designed grasps; research evolutionary algorithms vs RL.

The repository is at `aeca669` (branch `main-bsky37`). An evolutionary grasp search already exists
(`tools/grasp_evolve.py`, CMA-ES / GA, work log 24 Oct 08:15–10:40 UTC) and is being validated on two GPU boxes. This
report maps what FlashCHORD and the repository can do today, what is missing, and the cheapest way to add
(i) designed grasp primitives and (ii) a ground-truth-free evolutionary search (CMA-ES and MAP-Elites). It also flags
the risks.

Evidence labels:
- **[C]** read in code or config (file:line);
- **[M]** measured by me today, or a measurement recorded in the work log or a stored log (cited);
- **[L]** literature I opened (URLs in §12);
- **[I]** inference;
- **[H]** hypothesis, with the experiment that would falsify it.

FlashCHORD paths are relative to `scratchpad/src/video_to_data/robotic_grounding/flash_chord/src/flash_chord/`. That is
the local CPU copy, video_to_data `7eb9721` (20 Oct), with our VOC patch (`runtime/object_control.py`, `runtime/v2d_voc.py`)
and `configs/embodiment/sharpa_hands_mid.yaml` added. The evaluator pin is `8c778f90`. I could not diff the two
commits: GitHub API access to that repository is not enabled in this session. Earlier work found the pin and local
copies reproduce each other on CPU, e.g. `audit-starts-ep21-ep2-ep26.md` [M-CPU] (ep2 lid displacement 3/8/16 mm CPU vs
3/8/15 mm GPU).

Ground truth: none was read for this report.

---

## 0. Answer in brief

1. **Action semantics [C].**
   - The policy action is a residual on our reference: wrist position + Δp (world frame), wrist orientation
     = ref · rpy(Δ) (wrist frame), fingers + Δq.
   - The residual is filtered by an EMA (0.3) and clipped at 0.2 m / 1 rad / 1 rad.
   - The experiment's "normalized rational" input mapping has a gain of 5 cm or 0.15 rad per unit near zero.
   - **Zero action reproduces the reference exactly.** The PD targets are our parquet's `robot_*_wrist_position`,
     `_wrist_wxyz` and `_finger_joints`.
   - The untrained FlashSAC actor also outputs exactly zero, because its residual mean head is zero-initialised. So an
     RL fine-tune starts exactly from the zero-action replay of whatever reference we write.
2. **Hand [C/M].**
   - Two floating hands, each with 6 wrist DoF (3 prismatic + 1 ball) and 22 finger joints.
   - All 22 finger joints are PD: kp 1.7 N m/rad, kd 0.1, effort 10 N m. These override the URDF limits of
     0.19–3.3 N m.
   - Wrist translation: kp 25 N/m by default, 400 N/m in `sharpa_hands_mid`.
   - Wrist rotation: kp 25 N m/rad in both. That gain comes from the ACTION config, not the embodiment.
   - Rigid convex collision pieces, including 17.7 × 14.3 × 12.4 mm fingertip pads.
   - μ = 1.0 on every shape, condim 3 (no torsional friction), pyramidal cones.
   - Every object weighs 0.3 kg, with a thin-shell inertia.
   - The hands pass through the table.
3. **Per-world candidates [C/M].**
   - The robot and object references are shared by all worlds of a process.
   - But every world has its own residual action, every step, so one batched simulation can already evaluate N
     different candidate references within ±0.2 m / ±1 rad of the shared one. `grasp_evolve.py` does this.
   - No FlashCHORD patch is needed. The two cheap upgrades are:
     - raw input mode with exact EMA inversion, for time-varying candidates;
     - re-centring the shared reference on the search mean each generation, for larger moves.
   - Per-world physics changes (mass, friction, gains) are supported by Newton's solver (`notify_model_changed`), but
     are untested here.
   - Per-world reset offsets and object-scale randomisation already exist.
4. **Cost [M].**
   - One zero-action replay on CPU, 1 world, ep39 (319 frames): **0.068 s per frame** (median 0.060), 21.8 s for the
     steps plus 11.2 s of start-up. It was bit-identical to an earlier replay of the same reference (sim_vs_ref
     0.8770 both times).
   - CPU batched (stored logs): 10–34 ms per world-frame.
   - GPU (stored logs): a 300-world, ≤ 105-frame search ran in 11 s including setup. Training runs 55–63k env steps/s.
   - A robust CMA-ES on the GPU (256 worlds × 20 generations × ~300 frames ≈ 1.5M env steps per hold) should take
     roughly 3–10 min per hold [I]. That is about 2 % of the env steps of a 70M fine-tune (18.7 min measured).
5. **Checkpoints [C].**
   - The evaluator accepts only FlashSAC or PPO checkpoints (`training._target_`).
   - A FlashSAC policy file is a safetensors "learner_state" v1 file: the flattened actor params + batch-norm stats
     (1,219,008 values, 32 leaves for our 256-wide actor) plus the resolved config, the policy schema, the curriculum
     stage and the env-step metadata.
   - Any network with the same leaf shapes loads and runs. An ES-trained network could therefore be written in this
     format and would pass the evaluator mechanically.
   - **Rule risk:** the FAQ requires trajectories "from learned policies". A zero or step-0 actor is not learned. An
     ES-trained network would carry FlashSAC metadata it did not earn.
   - The clean path: ES designs the reference, then FlashSAC (RL) learns the closed-loop residual on top of it.
6. **What exists [C/M].**
   - Grasp-lock: hold phases, a copied, snapped or wrapped grasp, onset anchor, early approach, re-plan, lift
     feed-forward, anatomic closing, staged release.
   - `wrap_grasp.py`: hull-axis power grasp, close-to-contact.
   - `grasp_force.py`: friction-cone LP squeeze. It failed at minimal force (ep3 0.309 vs 0.658).
   - `task_wrench.py`.
   - `grasp_search.py`: grid search. **It has a hand-index bug: its "right hand" variants moved the LEFT hand.**
   - `grasp_evolve.py`: CMA-ES / GA over a 28-dim constant edit, with K jittered copies.
   - Measured search behaviour: rugged or noisy fitness.
     - ep39's per-generation best jumps 0.17–0.86 with no trend.
     - On ep18, a search best of 0.584 replays at 0.374.
     - A 1e-5 jitter moves an ep18 score from 0.37 to 0.18–0.44.
     - The ep39 evolved grasp holds under 1e-3 jitter (mean 0.841), not under 1e-2 (mean 0.46).
7. **Cheapest path** (§8).
   - (i) A `grasp_primitives.py` module that returns the five quantities grasp-lock already consumes at one slot
     (`grasp_lock.py:195–236`). First primitives:
     - key pinch on a rim (the grasp the successful RL found on the ep18 dust pan);
     - plate clamp, thumb on top and fingers under (ep24 boards, ep18 brush);
     - wrap (exists);
     - knob/rim pinch for the lid.
   - (ii) Evolve the primitives' low-dimensional parameters, plus small residual offsets, with robust CMA-ES. Then
     MAP-Elites (pyribs CMA-ME) for diverse fallbacks.
   - Re-score finalists in fresh single-world GPU processes (evaluator conditions), bake, and fine-tune with
     FlashSAC.

---

## 1. Action semantics: how the reference drives the hands

### 1.1 Facts [C]

| item | value | where |
|---|---|---|
| policy action | 56 = right (wrist pos 3, wrist rot 3, fingers 22) then left (same) | `runtime/actions/hand_pose.py:162-186`; checkpoint schema (right 0–27, left 28–55) [M] |
| residual composition | wrist target = ref pos + Δp (world frame); wrist quat = ref quat · `quat_rpy(Δr, Δp, Δy)` (local frame); finger target = ref q + Δq | `hand_pose.py:275-307` |
| reference indexing | `ref_wrist_pos_w[frame * num_hands + hand]`: **no world index**, every world reads the same reference at its own timestep | `hand_pose.py:263-273` |
| mapping | `map_residual_input` (identity / linear / rational) → `filter_residual`: y ← 0.3·y + 0.7·x·scale, then clipped | `runtime/residual.py:83-100` |
| scales / clips / EMA | wrist pos 0.05 m, rot 0.15 rad, finger 0.15 rad per unit; clips 0.2 m / 1 rad / 1 rad; EMA 0.3 | `configs/action/residual_hand_pose.yaml:4-10`, `hand_pose.py:107-119` |
| experiment mapping | `input_mode: normalized`, `normalized_mapping: rational`: slope 1 near 0; at \|n\| = 1 the steady state reaches the clip (input_scale s = clip / (0.7·scale) = 5.71 for position, 9.52 for rotation and fingers) | `configs/experiment/sharpa_flash_sac.yaml:29-30`, `residual.py:61-69` |
| zero action | `env.step(None)` uses the zero `action_input`; map(0) = 0, so the PD targets are exactly our reference columns | `envs/rl.py:476-479`, `envs/base.py:240-244` |
| wrist translation | prismatic x/y/z position PD from `joint_target_pos` | `runtime/control.py:88-92` |
| wrist rotation | ball joint in EFFORT mode: τ = clamp(kp·rotvec(cur⁻¹·tgt), ±τmax); **kp, τmax = ActionConfig `wrist_kp` 25 / `wrist_tau_max` 45**; damping = the embodiment's `wrist_rotvec.kd` (6, passive) | `runtime/control.py:20-56`, `hand_pose.py:551-558`, `embodiments/sharpa_hands.py:170-175` |
| fingers | position PD on the 22 revolute joints | `sharpa_hands.py:176-179` |
| evaluator start | explicit reset to frame 0, fingers exactly at the reference (finger_scale 1), VOC 0 and VOC max force/torque 0, terminations off, 1 world by default | `evaluation/harness.py:216-251, 449-451`; `lifecycle/reset.py:386-400`; kit `examples/run_policy_evaluation.py:42,74` |
| which parquet columns drive the hands | `robot_{side}_wrist_position`, `_wrist_wxyz`, `_finger_joints` → joint_q / joint_target; hand keypoints for rewards = FK of that joint_q | `data/mano_sharpa.py:254-256`, `embodiments/sharpa_hands.py:294-311`, `embodiments/binding.py:320-366` |
| `robot_*_frames` columns | parsed and validated, but used only by the Vega arm embodiment, not by `sharpa_hands` | `data/mano_sharpa.py:301-310`; only consumer `embodiments/vega_sharpa.py:452-501` |

### 1.2 Consequences [I]

- **A designed controller is written into the reference.** Grasp-lock, ILC and evolved edits all end up as PD target
  columns. A zero policy, or the fresh FlashSAC actor (§5.3), replays them exactly.
- **The target columns are also the reward targets.** The lift feed-forward and the ILC lead (up to 12 cm,
  `pipeline/wrist_ilc.py:50`) go into `robot_*_wrist_position`, and FlashCHORD's hand-keypoint and FDR fingertip
  rewards are FK of those same columns.
  - So the fine-tune's hand rewards aim at the ILC-shifted targets, not at the kinematic grasp pose.
  - The docstrings of `grasp_lock.py:13-17` and `wrist_ilc.py:7` say the frames keep the intended pose. That is true
    of the parquet, but `sharpa_hands` does not read the frames.
  - The lift offset is small with kp 400 (m g / kp = 0.74 cm).
  - The ILC part is not measured (H6).
- **Exploration noise.** FlashSAC's exploration noise (target σ 0.1 normalized, zeta-repeated ≤ 16 frames, mean repeat
  length 2.1 frames; `configs/experiment/sharpa_flash_sac.yaml:49`, `training/flash_sac/exploration.py`) is roughly
  3–5 mm on the wrist and 0.01–0.015 rad on fingers and wrist rotation after the EMA [I, back-of-envelope]. The robust
  search jitters by 0.005 (m and rad, `tools/grasp_evolve.py:36`). That is comparable on position and about 3 times
  smaller on fingers (H2).

---

## 2. Hand model and object facts

### 2.1 Sharpa Wave hand (per hand) [C]

| quantity | value | where |
|---|---|---|
| DoF | 6 wrist (3 prismatic x/y/z + 1 ball) + 22 fingers. The 22: thumb 5 (CMC_FE, CMC_AA, MCP_FE, MCP_AA, IP); index, middle, ring 4 each (MCP_FE, MCP_AA, PIP, DIP); pinky 5 (CMC, MCP_FE, MCP_AA, PIP, DIP) | `assets/urdfs/sharpawave/right_sharpawave.urdf` (parsed), `sharpa_hands.py:96-146` |
| joint limits (rad) | MCP_FE [−0.175, 1.571]; MCP_AA ±0.349; PIP [0, 1.745]; DIP [0, 1.396]; thumb CMC_FE [−0.175, 1.920], CMC_AA ±0.349, MCP_FE [−0.524, 1.396], MCP_AA ±0.349, IP [0, 1.745]; pinky CMC [0, 0.262] | URDF |
| URDF effort limits (real hardware) | CMC 3.3, MCP 1.864, PIP 0.638, DIP 0.189, pinky CMC 0.529 N m. **Overridden in the sim to 10 N m** (`JointControlSpec` default) | URDF; `embodiments/base.py:34-41`, `sharpa_hands.py:180-181` |
| finger PD (all 22) | kp 1.7 N m/rad, kd 0.1, armature 0.01, effort 10 N m; no URDF joint friction (`<dynamics>` absent) | `embodiments/base.py:34-41` |
| wrist translation, default `sharpa_hands` | kp 25 N/m, kd 6, 45 N | `sharpa_hands.py:56` |
| wrist translation, `sharpa_hands_mid` | kp 400 N/m, kd 20, 150 N | `flashchord_conf/embodiment/sharpa_hands_mid.yaml` |
| wrist rotation (both) | effort controller kp 25 N m/rad, clamp 45 N m (ActionConfig), passive damping 6 | §1.1. Stiffer: `configs/action/residual_hand_pose_stiff.yaml` (`wrist_kp` 1200, 2000 N m) |
| sag from a 0.3 kg object | translation mg/kp = 11.8 cm (kp 25), 0.74 cm (kp 400); rotation 0.3·9.81·0.1 m / 25 = 0.012 rad (0.7°) per 10 cm of lever [I] | |
| gravity compensation | every robot DoF and body | `sharpa_hands.py:190-196` |
| link masses | palm 0.651, thumb MC 0.136, pinky MC 0.125, PP 0.047, MP 0.018, DP 0.0046 kg (hand ≈ 1.24 kg, work log 12:19 UTC 23 Oct) | URDF |
| collision geometry | every link is a convex hull (`right_cvx/*.STL`): palm `hand_C_MC_cut` 86 × 84 × 46 mm; PP 45 × 22 × 19; MP 37 × 19 × 17; DP 26 × 15 × 14; **finger pad (elastomer) 17.7 × 14.3 × 12.4 mm, convex, rigid**; thumb pad 19.0 × 16.4 × 15.5 mm; thumb DP 29 × 17 × 17 mm. Pads are fixed-joint children folded into the DP body | [M] `capability-scripts/hand_geom_output.txt`; URDF fixed joints |
| links allowed to touch objects | palm, thumb MC/PP/DP, finger PP/MP/DP, pinky MC | `embodiments/sharpa_collision.py:87-105` |
| contact material | ke 1e3, kd 1e2, margin 0, gap 0 (default shape config); μ = scene `contact_friction` 1.0 applied to **every** colliding shape; condim default 3 → **no torsional friction** (MuJoCo: torsional friction needs condim 4, "can substantially improve the stability of simulated grasping" [L]); pyramidal cone; torsional 0.005 / rolling 1e-4 coefficients unused at condim 3 | `sharpa_hands.py:200-203`; `scene/builder.py:266-269`; `configs/scene/train.yaml:7`; Newton `solver_mujoco.py:623-632`; `configs/sim/rl.yaml:6` |
| table | **hands do not collide with the support** (`robot_support_collision: false`); objects do | `configs/collision/training.yaml:5` |
| sim timing / buffers | 20 fps × 5 substeps, implicitfast, Newton solver, 100 iterations, impratio 20; `njmax` 512 constraints per world (strict), `nconmax` 256 contacts per world (a world may exceed it in a batch if the total fits, MJWarp docs [L]) | `configs/sim/rl.yaml:2-8` |

Implications for primitives [I]:
- **Thin parts and plates need preload.** A thin handle pivots under a two-point pinch (no torsion), and soft contacts
  creep. Use at least three spread contacts or palm opposition, and a firm squeeze (the minimal-force LP failed, §6).
- **The table is not an obstacle for the hand.** Fingers can wrap under a plate or board lying flat: the board clamp
  in the boards audit is physically possible. But closing from below flicks the plate (plates audit), so the fingers
  should arrive at their under-plate pose before contact and close slowly.
- **The orientation drive is soft** (25 N m/rad) and the same in both embodiments. A stiffer rotation would come from
  `action.wrist_kp`, which the checkpoint stores and the evaluator rebuilds. It is untested and a config-level change
  to discuss with the owner.

### 2.2 Objects as built by `pipeline/make_assets.py` [C/M]

- Mass 0.3 kg for every object, as the public placeholder (`make_assets.py:52,64-66`).
- COM and inertia come from a uniform thin-shell estimate over 20,000 surface samples (`make_assets.py:41-47`), with
  MuJoCo `balanceinertia`.
- FlashCHORD splits each collision mesh into convex pieces with CoACD, and the pieces of one object do not collide with
  each other (`scene/objects.py:159-213`).

Principal moments, library_v3 [M] (`capability-scripts/object_inertia_output.txt`):

| object | extents (cm) | principal inertia (1e-4 kg m²) | min / mean |
|---|---|---|---|
| mini_dust_pan | 16.9 × 15.9 × 3.9 | 4.0 / 6.7 / 10.3 | 0.57 |
| mini_sweeper | 14.7 × 11.0 × 3.4 | 1.9 / 5.8 / 7.4 | 0.38 |
| wooden_piece_1 | 22.9 × 13.3 × 3.1 | 4.0 / 13.6 / 17.4 | 0.34 |
| wooden_piece_2 | 22.9 × 13.8 × 2.7 | 4.3 / 14.0 / 18.1 | 0.36 |
| water_pitcher | 41.2 × 26.1 × 14.8 | 13.8 / 24.5 / 30.9 | 0.60 |
| white_pot | 36.2 × 19.0 × 13.1 | 11.7 / 22.7 / 28.2 | 0.56 |
| white_pot_lid | 18.9 × 18.5 × 5.2 | 5.9 / 7.1 / 12.5 | 0.70 |
| blue_cup | 16.7 × 9.6 × 9.5 | 4.2 / 8.8 / 9.2 | 0.57 |
| plastic_dish_rack | 49.6 × 15.9 × 10.9 | 8.2 / 72.0 / 77.1 | 0.16 |
| wooden_spoon | 32.2 × 5.2 × 2.9 | 0.46 / 25.8 / 26.0 | 0.026 |

The spoon's 1/38 ratio is the VOC-explosion case (`ops/box/fc_v2d_voc.py`, training only). For design, use the sim
masses, not the real ones: the evaluator uses exactly these assets.

---

## 3. Can one batched simulation evaluate N different candidate references?

### 3.1 What is shared and what is per world [C]

| component | per world? | where |
|---|---|---|
| robot reference (wrist pos/quat, finger q) used by the action | **shared** | `hand_pose.py:263-307` (`DeviceRobotReference`) |
| object reference / command (VOC targets, termination, rewards) | shared | `runtime/command.py` (`CommandBuffers.build(scene, reference)`), `envs/base.py:154` |
| reset table `ref_joint_q[F, q]` | shared, **plus a per-world `reference_joint_q_offset[W·q]`** added to every coordinate at reset (hands and object free joints) | `lifecycle/reset.py:78-123` (line 104); buffer `envs/base.py:147-153` |
| per-world object root offsets and scales | yes (object-scale randomisation; world 0 nominal) | `scene/builder.py:279-299, 347-418` |
| timestep / reset frame | yes (`reset(reset_frame=wp.array[W])`) | `envs/base.py:247-270`, `envs/rl.py:348-366` |
| **residual action** | **yes, per world and per step** | `hand_pose.py:241-307` (`world = wp.tid()`) |
| model physics (mass, inertia, friction, gains, joint limits) | Newton expands MJWarp model fields per world when nworld > 1 and refreshes them with `solver.notify_model_changed(flags)` | Newton `solver_mujoco.py:5798-5880, 3444-3500` |
| `ReferenceOffsetAction` (per-world offsets in the action) | protocol exists, **not implemented by `ResidualHandPoseAction`** (only the humanoid "sonic" action binds it) | `hand_pose.py:97-103`, `runtime/actions/sonic.py:927-935` |

### 3.2 Answer

- **Yes, within bounds, without patching FlashCHORD.** Each world's residual action makes its own candidate
  reference: candidate_w(f) = shared(f) ⊕ Δ_w(f), within ±0.2 m (world frame), ±1 rad (wrist frame) and ±1 rad per
  finger. `grasp_evolve.py` already does this.
  - Its edit is a constant θ, rotated from the object frame to the world frame each frame and ramped in and out
    (`tools/grasp_evolve.py:122-131`).
  - It inverts the rational mapping at steady state (`grasp_evolve.py:104-111`).
  - The bake writes the same edit into the parquet (`grasp_evolve.py:285-302`, with the action's own `quat_rpy`
    convention).
  - The work log records that bake and action paths agree [M]: ep18 baked-without-edit 0.396 vs action path 0.396;
    ep39 window 0.854 baked vs 0.810 searched.
- **Smallest upgrade for time-varying candidates** (closure profile, approach path, hold timing; no FlashCHORD patch):
  - set the search env to `action.input_mode=raw`, a Hydra override that `grasp_search.py:69` already used;
  - drive each world with the exact EMA inverse x_t = (Δ_t − 0.3 Δ_{t−1}) / (0.7 · scale), taken from
    `filter_residual`;
  - this reproduces any per-world target stream exactly unless the 0.2 m / 1 rad clip binds;
  - about 20 lines in `grasp_evolve.py`.
- **For larger moves (re-centring):** bake the current search mean into the shared reference at each generation.
  `grasp_evolve.py` already rebuilds the env per generation unless `--keep_env` (`:174-178`), so this costs one
  scene build (4–7 s CPU [M]).
- **Only if a candidate must leave the clip box around every common base:** a FlashCHORD patch.
  - The smallest one: an optional device array `ref_delta[W, F, 6 + nf]` added to the targets inside
    `process_residual_action` (`hand_pose.py:275-307`), before the reference is composed. About 25 lines.
  - Training and search only, never in the evaluator (the evaluator runs 1 world on the baked reference).
  - I do not recommend it: re-centring covers the need.
- **Per-world physics** (robust fitness against mass, friction or gain perturbations): write the Newton model arrays
  for world w's bodies or shapes (world-major) and call `solver.notify_model_changed(BODY_INERTIAL_PROPERTIES |
  SHAPE_PROPERTIES | JOINT_DOF_PROPERTIES)`. The source supports it; it is **untested here**. Note that the evaluator's
  physics is fixed and known (§9, H5).
- **Per-world start perturbations:** `env.reference_joint_q_offset` (position offsets of the object free joints or the
  wrist) is applied at reset. Quaternion coordinates are added, not composed: use only position offsets, or tiny
  ones.

### 3.3 Does a candidate score the same in a batch as alone? [M]

- **CPU, fresh single world: deterministic.** My replay of the evolved ep39 reference is bit-identical to the lead's
  earlier replay (max |Δq| = 0.0; sim_vs_ref 0.8770 both). MuJoCo: "deterministic … within a single version, on the
  same architecture"; contacts have high Lyapunov exponents [L].
- **GPU: not deterministic.** MJWarp: "Is MJWarp on GPU deterministic? No … non-deterministic atomic operations on
  GPU" [L]. Measured examples:
  - three zero-action GPU replays of the same ep35 reference scored 0.150 / 0.172 / 0.185 (work log 12:19 UTC 23 Oct);
  - one policy, 8 official evaluations, scored 0.13–0.41 vs mocap (STATUS, 21 Oct).
  - The official evaluator runs on CUDA.
- **Batch vs alone (CPU).** Identical edits score identically in every world of one batch. But a search's best can
  differ from its fresh single-world replay:
  - ep18: search 0.584, replay 0.374;
  - ep39: search 0.865, full replay 0.877.
  - A 1e-5 jitter moves the ep18 score from 0.37 to 0.18–0.44 (work log 10:05–10:40 UTC). The working explanation is
    chaos amplifying tiny numeric differences. The exact mechanism is not established.
  - Also: in a batch, one world may borrow contact slots beyond `nconmax` 256 (MJWarp docs [L]). The evaluator's
    single world cannot. Contacts measured 296 of 2048 over 8 worlds, so this is low risk.
- **Process state across generations (CPU):** it survived `env.reset` and remained after the warm start was zeroed.
  A fresh env per generation fixed it (`72d60cb`). **The GPU validation job runs with `--keep_env`**
  (`ops/jobs/glock_public.sh:149`), so its per-generation fitness may again depend on history.

Consequence for (ii) [I]:
- treat fitness as a random variable;
- use a robust objective (the K-jittered copies already exist);
- re-score finalists in fresh single-world GPU processes (evaluator conditions, ≥ 8 repeats);
- select by mean (and minimum), never by the search's single best.

---

## 4. Cost of a zero-action replay and of a search

| run | device | worlds × frames | wall time | per world-frame | source |
|---|---|---|---|---|---|
| zero-action replay, evolved ep39 reference (`sharpa_hands_mid`) | CPU, 4 shared cores, load ~1–1.5 | 1 × 319 | 21.8 s steps + 6.4 s imports + 4.1 s scene + 0.7 s env = 33.2 s | **68 ms** (median 60, p95 96, first step 1.0 s) | [M] `capability-scripts/timed_zero_output.txt` |
| wrist ILC iteration (one replay incl. scene build + update), ep39 | CPU | 1 × 319 | 22–25 s per iteration | ≈ 45–75 ms | [M] `scratchpad/evo/oa/ilc_ep39.log` |
| CMA-ES ep39 round 1 | CPU | 16 × 101 | 15.7–21.2 s per generation | 10–13 ms | [M] `evo/oa/cma_ep39.log` |
| CMA-ES ep39 round 2 | CPU | 8 × 291 | 41.6–76.3 s per generation | 18–33 ms | [M] `evo/oa/cma2_ep39.log` |
| CMA-ES ep18 sweeper (fresh env per generation) | CPU | 8 × 334 | 37.8–47.2 s per generation | 14–18 ms | [M] `evo/oa18/cma_p1f.log`, `cma_p1g.log` |
| CMA-ES ep24 board 1 (two boards) | CPU | 8 × 261 | 54–72 s per generation | 26–34 ms | [M] `evo/oa24/cma_p0.log` |
| grasp grid search, eval ep3 | GPU RTX PRO 6000 WS | 300 × ≤ 105 | **11 s including scene build** | ≤ 0.35 ms | [M] HF store `runs/20261023-spoon3R-4c31271/glock/ep3_search1.log` |
| wrist ILC iteration, eval ep3 | GPU | 1 × 313 | ~11 s per iteration | ~35 ms | [M] `…/glock/ep3_ilc.log`, `run_k400.log` |
| FlashSAC training alone | GPU PRO 6000 | 4096 worlds | 55–63k env steps/s; 250M in 71–79 min; 70M fine-tune 18.7 min | ~0.017 ms (incl. learning) | work log (23 Oct 13:29–13:49 UTC; 21 Oct) |
| memory of `grasp_evolve` on CPU | | 8 worlds | ~0.66 GB | | work log 08:45 UTC 24 Oct |

Estimates [I] (the GPU validation run will measure them):
- **Robust CMA-ES, one hold:** 256 worlds × ~300 frames × 20 generations = 1.54M env steps. At the measured GPU batch
  rate (≤ 0.1 s per batched frame for 300 worlds), that is ≤ 30 s per generation and ≤ 10 min per hold, ≈ $0.25 at
  $1.5/h. That is 2.2 % of the env steps of a 70M fine-tune and 0.6 % of a 250M standard training.
- **On the 4 shared CPUs:** an 8-world robust search gives only 2 candidates per generation (K = 4). The CPU is for
  development and gating, not for the robust search (as the lead concluded).

---

## 5. Checkpoint constraints: which learners, which format, can an ES network pass?

### 5.1 What the evaluator accepts [C]

- **Learners.** `checkpoint_training_algorithm` accepts only `flash_chord.training.flash_sac.config.TrainingConfig` and
  the PPO `TrainingConfig`; anything else raises an error (`evaluation/harness.py:293-303`).
- **The environment is rebuilt from the checkpoint's own resolved config** (`harness.py:376-427`): task parquet, scene
  (world count forced), collision, embodiment, env (action, sim), training network. On top of that, the evaluation
  composition is forced (`harness.py:216-251`).
- **FlashSAC** loads only an actor (`training/flash_sac/evaluation.py:128-157`). Its template is built from
  `training.network`, and the leaves must match shape and dtype exactly (`training/checkpoint.py:90-119`).
- **Metadata required:**
  - `user.algorithm = flash_sac` and `user.checkpoint_kind = policy` (`training/flash_sac/checkpoint.py:149-169`);
  - `user.resolved_config_json` (`training/checkpoint_metadata.py:19,231-233`);
  - `user.curriculum_stage` when a curriculum is configured (`harness.py:429-438`);
  - `user.policy_schema_json`.
- **File format.** safetensors with `format = learner_state`, `version = 1` and a JSON manifest of flattened leaves
  (`training/checkpoint.py:17-58`).
- **Our 40M ep35 policy [M].** 32 leaves, 1,219,008 values; obs 504, action 56, `normalized/rational`; actor 256-wide,
  2 blocks, `actor_head_mode: residual`, `residual_mean_head: unit_gain`.
- **The kit's packer** records the per-episode checkpoint sha256 and the evaluator code digests. It does not check how
  the checkpoint was trained (kit `tools/pack_submission.py:289-308`).

### 5.2 Could an externally optimised (ES) network be written and pass? [C/I]

- **Mechanically, yes.** Build the actor template with `create_actor_template` (same `NetworkConfig`), overwrite
  `params`, and call `save_actor_checkpoint(path, ActorInferenceState(params, batch_stats), metadata=…)`. The metadata
  would be copied from a real FlashSAC checkpoint of the same configuration, with `task.parquet` pointing at our
  reference. The evaluator would load and run it.
- **Is it worth it? Probably not:**
  - **Search size.** Full-weight ES over 1.2M parameters: Salimans et al. matched TRPO on MuJoCo "using no more than
    10x as much data" with 1,440 CPU workers [L]. Our fine-tunes need 40–70M env steps, so weight-space ES would be
    of order 10⁸–10⁹ env steps [I, rough extrapolation across algorithms and tasks]. That is not cheaper than
    FlashSAC.
  - **Low-dimensional variant** (`mean_bias` 56 + head `gain` 56 on a frozen trunk) [H, untested]. It could adjust a
    learned policy, but `mean_bias` alone is a constant action over the episode, which grasp edits are not.
  - **Honesty and rules.** The metadata would say FlashSAC, and the FAQ asks for "learned policies"
    (`docs/forensics-2026-10-21.md:77`). An ES network is learned, but needs the organisers' confirmation and a truthful
    trainer record.

### 5.3 The useful fact: the fresh FlashSAC actor is the zero-action controller [C]

- `GainedUnitLinear` initialises its per-output gain to 0 (`training/flash_sac/network.py:72-88`), and `mean_bias` is
  zero-initialised (`:351`). So mean = 0 and the deterministic action = tanh(0) = 0 (`:487-498`) at step 0.
- So a FlashSAC fine-tune begins exactly at the zero-action replay of the reference we design. ES and grasp design go
  into the reference, and RL starts from them with no distribution shift at initialisation.
  - Mechanism, not measured here: ep3 and ep35 fine-tunes reached 0.94–0.98 from zero-action 0.41–0.66.
- **Rule risk.** A step-0 or zero policy is not "learned". Do not submit one unless the organisers allow it. The
  submitted checkpoint should be a trained FlashSAC policy (e.g. ≥ 10M steps), chosen by sim_vs_ref over repeated
  evaluations.

---

## 6. What the repository already implements, and what was learned

### 6.1 Code [C]

| file | what it does | notes |
|---|---|---|
| `pipeline/hold_phases.py` | holds from MANO contacts (≥ 2 contacts, object off rest > 1.5 cm, PRE 8 / POST 4 frames, gaps ≤ 12 frames bridged, min 6 frames) | `:14` constants |
| `pipeline/grasp_lock.py` | per hold: grasp frame g* (most distal links within 5 mm), wrist pose locked in the object frame, fingers closed + squeeze; options: wrap, snap, single-hand carry, MCP-first anatomy, anatomic squeeze profile, force design, re-plan against a sim trace, early approach, **onset anchor**, lift feed-forward, staged release (relax → unroll distal first → withdraw along the separating direction) | **the slot for designed grasps: `:195-236`**: (R_ow, T_ow_p) wrist in the object frame, qf (touch), qs (squeezed), qpre (pre-open), back (back-off). Everything downstream (approach `:294-327`, hold `:329-341`, release `:342-353`, lift `:332-333, 367-375`) consumes only these |
| `pipeline/wrap_grasp.py` | handle axis and radius from the hull PCA; the longest narrow run (≤ 3.5 cm) is the handle; palm normal closest to the human's; `close_fingers` curls each finger group (FE, PIP, DIP proportionally) to contact on the hull SDF, then squeezes | thumb closes CMC_FE, MCP_FE, IP only: **no thumb abduction / opposition** (`:73-76`); hand frame: +z along fingers, +x palm, palm surface x ≈ 2.2 cm (`:6-8, 24`) |
| `pipeline/contact_retarget.py` | `FK` (Newton, CPU), `HullSDF` (exact convex-piece SDF on a 2.5 mm grid), `hand_geometry` (collision-surface samples per link), `MjPen` (CPU MuJoCo penetration as the simulator sees it, 0.3–0.7 ms per query), `write_robot` | building blocks for primitives and for a kinematic pre-filter (reject penetrating candidates before simulating, as DexEvolve does) |
| `pipeline/grasp_force.py` | per-frame LP: 8-edge pyramids with μ/(√2·SF), Σ G f = SF·W(t), finger preload ≥ F_MIN, torques Jᵀf within kp × room; squeeze Δq = Jᵀf / kp; separating direction LP | `:25` (μ 1, SF 1.5, F_MIN 1.5 N); used only with `--force_design` |
| `pipeline/task_wrench.py` | F = m(a − g), τ = I_w α + ω × I_w ω from Savitzky–Golay derivatives of OUR object path; grip-point torque; support flag | ep35 spoon: \|F\| ≤ 3.4 N, COM torque ≤ 0.04 N m (notes 24) |
| `pipeline/wrist_ilc.py` | zero-action replays, wrist targets += 0.8 × error 2 frames ahead (cap 12 cm / 0.6 rad), 4 iterations | ep39 right wrist error 2.41 → 0.42 cm in 4 iterations [M log] |
| `pipeline/grasp_search.py` | grid of (along, down, roll, squeeze, approach side / below) × trials with smooth wrist noise, raw-mode constant residuals, slip in the hand frame | **BUG (§9 R8):** `ho = 0 if hand == 'left' else A_dim // 2` (`:83`), but FlashCHORD orders the action right-then-left (schema [M]). A "right" search moved the LEFT hand. No current job calls it |
| `tools/grasp_evolve.py` | per hold: θ = [wrist offset in the object frame 3, wrist rpy 3, finger offsets 22], ramped over 8 frames from the approach start; one candidate per world; fitness = kit ADD AUC (1–9 cm, 500 sphere points) vs OUR reference over [approach − 6, hold end + 20], optionally all objects; CMA-ES (rank-μ + rank-one) or GA; `--robust K --jitter`; fresh env per generation (or `--keep_env`); warm start zeroed; `--init`, `--repeat_best`, `--bake` | the evaluation window starts with an explicit reset at its first frame (`:180`), **not at frame 0** like the evaluator; θ clipped at ±4σ (`:254`); hand index correct (`:95`) |
| `ops/jobs/glock_public.sh` | `EVOLVE=1`: per hold, `grasp_evolve` on CUDA with 256 worlds = 64 candidates × 4 copies, 20 generations, σ_pos 0.03, σ_fin 0.3, jitter 0.005, `--all_objects`, **`--keep_env`**, baked before the zero replay and the fine-tune | `:143-151` |
| `tools/trace_rollout.py`, `trace_score.py`, `rest_check.py`, `sim_settle.py`, `hand_object_gap.py` | evaluator-like zero / policy traces (q, frame, labels; optional per-pair contact forces, uncalibrated); sim_vs_ref with qa.py's metric; rest check (5 mm / 2° until the first hold − 6); settle the start (VOC on 20 steps, off 30) | GT-free gates for any candidate |

### 6.2 What was learned (notes 23 and 24, work log 23–24 Oct)

- **[M] Designed beats copied on graspables.**
  - Wrap + ILC + kp 400 on eval ep3: zero action 0.462 (kp 25) → 0.658 (kp 400); fine-tune 0.965–0.981.
  - ep35 single-hand wrap with MCP-first closing: 0.521 at zero action, fine-tune 0.94–0.98.
  - The stiff wrist is essential for the fine-tune: the kp 25 fine-tune stayed at 0.23–0.42.
- **[M] Minimal-force squeezes fail.**
  - Force-designed minimum normal force on ep3: 0.309 vs 0.658 with the uniform 0.4 rad squeeze. On ep35 the force
    design gave no gain (0.175 vs 0.150–0.185).
  - Lesson: in this simulator, robustness (preload) beats force economy.
  - An oblique 25° handle reduced roll but tipped the bowl up to 112° (0.093).
- **[M] What helped:** anatomy closing (MCP first, IPs second, thumb last) and palm pressing 1 mm on ep35. But the same
  rule costs ep3 0.2 at zero action (0.658 → 0.43); which part is responsible is not isolated.
- **[M] Release:** opening all joints at once hooks a thin handle and flicks it; sliding off with the fingers wrapped
  drags it. Relax to the touching pose, unroll the distal joints first, then withdraw.
- **[M] Copied human hand switches drop the spoon** (0.07–0.18). Single-hand carry is the safe default.
- **[M] Audits (this workflow).** Of the 7 failed public episodes, the grasp is the first failure in:
  - the ep18 dust pan (no thumb opposition; closing from below flicks it);
  - the ep24 boards (neither board acquired; counterfactual 0.803);
  - the ep2 lid (flicked at lift onset in all 5 variants).

  The rest are not grasp failures:
  - the ep18 sweeper: hold timing;
  - ep39: the carrier merge deleted the pick-up;
  - ep21: the pitcher mesh lacks half its base;
  - ep26: the pot sits 29 mm too deep in the rack;
  - ep31: first-step ejection from the rack hulls.

  So designed grasps must come with the reference fixes (onset anchor, carrier choice, start settling and meshes).
- **[M] What the successful standard RL found on ep18** (0.889): a lateral key pinch on the dust pan's ring band (thumb
  on top, index under, palm up, sliding in low; hook through the ring for the long lift); and a whole-plate clamp on
  the brush head (thumb column on one face, four fingers flat on the other, palm against the edge; 10–13 links in
  contact).
- **[M] Evolutionary search so far** (CPU, the lead's runs):
  - ep39: onset anchor + CMA-ES (pop 16 × 8, then 8 × 12) took zero-action sim_vs_ref **0.176 → 0.877**. Standard RL
    on the same reference reached 0.826.
  - ep18: 0.135 → 0.354 (pan hold), not reproduced for the sweeper.
  - ep24: board 1 hold 0.194 → 0.513 (a generation-0 sample).
  - **Search dynamics:** the per-generation best on ep39 round 2 runs 0.28, 0.51, 0.39, **0.86**, 0.79, 0.31, 0.36,
    0.57, 0.65, 0.76, 0.23, 0.17. The generation mean stays at 0.11–0.34 and σ shrinks only 0.95 → 0.82. That is
    fitness noise or ruggedness that dominates the covariance adaptation: the search behaves close to "random sampling
    + keep the best" [I] (H3).

---

## 7. Capability map

| need | status | where | gap / cheapest addition |
|---|---|---|---|
| reference = PD targets; zero action = replay | ✔ | §1 | — |
| per-hold grasp slot (object-frame wrist pose, fingers, squeeze, pre-open, back-off) | ✔ | `grasp_lock.py:195-236` | primitives plug in here |
| copied / snapped / wrap grasps | ✔ | `grasp_lock.py`, `wrap_grasp.py` | — |
| key pinch on a rim or band, plate clamp, hook, knob or rim pinch, bimanual clamp | ✘ | — | `pipeline/grasp_primitives.py` (§8.1) |
| thumb opposition (AA joints) | ✘ | `wrap_grasp.py:73-76` closes FE/IP only | add AA targets to the primitive constructors |
| per-finger subsets (only some digits close) | ✘ | `close_fingers` closes all groups | a `digits=` argument |
| kinematic feasibility pre-filter | ✔ (building block) | `contact_retarget.MjPen`, `HullSDF` | call it before simulating a candidate |
| task wrench / force design | ✔ (squeeze sizing failed when minimal) | `task_wrench.py`, `grasp_force.py` | use only as a lower bound or for a diagnostic margin |
| hold timing from the object's motion (onset anchor) | ✔ (off by default) | `grasp_lock.py:184-194` | — |
| re-plan against the simulated world; start settle; rest check | ✔ | `grasp_lock --sim_trace`, `tools/sim_settle.py`, `tools/rest_check.py` | — |
| one candidate per world in a batch | ✔ | `grasp_evolve.py:122-131` | — |
| time-varying candidates (closure profile, approach path, timing) | ◐ | residual channel | raw mode + EMA inversion (~20 lines) |
| candidates beyond ±0.2 m / ±1 rad | ◐ | — | re-centre per generation (bake the mean) |
| robust fitness (jittered copies) | ✔ | `--robust K --jitter` | jitter shaped like the fine-tune's exploration noise (H2) |
| per-world physics perturbation | ◐ (solver supports it) | Newton `notify_model_changed` | ~30 lines; probably unnecessary (H5) |
| CMA-ES / GA | ✔ | `grasp_evolve.py` | IPOP restarts, mean learning rate c_m < 1 on noise (Hansen tutorial [L]) |
| MAP-Elites / CMA-ME | ✘ | — | `pip install ribs` (pyribs [L]); descriptors from the simulated hand pose (§8.2) |
| finalist re-scoring under evaluator conditions | ◐ | `--repeat_best` (in-batch); `trace_rollout zero` + `trace_score` (1 world) | a GPU loop: N fresh 1-world processes per finalist |
| bake into the reference | ✔ | `--bake` | — |
| RL fine-tune from the designed reference | ✔ | FlashSAC (actor starts at exactly zero residual) | lower exploration for narrow grasps (H2) |
| evaluator compatibility of the result | ✔ | the reference is ours; the checkpoint is FlashSAC | — |
| ES-trained network as the submitted policy | ◐ (mechanically possible) | §5.2 | rules and honesty risk; not recommended |

---

## 8. Cheapest implementation path

### 8.1 (i) Designed grasp primitives inside grasp-lock (CPU, ≈ 1–1.5 days of work, $0)

1. **`pipeline/grasp_primitives.py`.** Each constructor takes the object's convex pieces (`HullSDF`, PCA axes of the
   hull vertices), the hand FK, the side and a small parameter vector p. It returns `GraspSpec(R_ow, T_ow_p, qf, qs,
   qpre, back, close_order, digits, meta)`, all in the object frame, as `wrap_grasp.wrap_pose` + `close_fingers` do
   today.

   | primitive | for | geometry | parameters p |
   |---|---|---|---|
   | `wrap` (exists) | spoon handle, pot handle, sweeper handle | narrow hull run, axis + radius | grip point s, palm roll ψ, oblique α, squeeze σ |
   | `key_pinch` | dust pan ring band (ep18, ep39), plate rims | thinnest local slab near the human contact (hull SDF thickness), its normal n | location s along the rim, approach azimuth φ (palm up / down), thumb pad on +n, index radial side on −n, σ |
   | `plate_clamp` | boards (ep24), brush head (ep18 sweeper), lid rim | smallest PCA axis = plate normal; edge nearest the hand | edge point s, depth d into the plate (2–6 cm), φ, σ; fingers under (through the table), thumb on top |
   | `hook` | ring handles for long lifts, pitcher handle | opening found as an SDF-free channel through the hull | channel point, curl depth |
   | `rim_pinch` | lid knob or rim (ep2) | highest small feature or the rim | s, tripod vs pinch, σ |
   | `bimanual_clamp` | wide plates, rack | two opposite faces | both hands' p; shared lift (`n_hold` exists) |

   - Thumb opposition: set CMC_AA / MCP_AA from the primitive (today only FE/IP close).
   - Digit subsets: a `digits=` argument for close_fingers.
   - Squeeze level: ≥ the 0.4 rad uniform level that worked. The force LP gives only a lower bound (§6.2).
2. **`grasp_lock.py --primitive auto|wrap|key_pinch|plate_clamp|…`** at the existing wrap slot (`:209-234`). The `auto`
   choice comes from the hull shape class and the MANO contact location:
   - elongated (PCA ratio ≥ 3) with a narrow run → wrap;
   - plate (smallest/middle extent ≤ 0.3) → key_pinch where the human holds a rim or band, else plate_clamp;
   - otherwise snap the human grasp.

   The copied or snapped human grasp is always also evaluated as a seed. Keep the reference fixes from the audits
   on: onset anchor; the carrier = the hand that picks the object up first (not the hand with the most frames, the ep39
   lesson); approach 15 cm; start settling where hulls overlap.
3. **CPU gates per primitive** (per episode, GT-free):
   - one zero-action replay (≈ 33 s, §4);
   - `rest_check` until the hold;
   - `trace_score` window and full sim_vs_ref;
   - slip in the hand frame < 2 cm and < 10° over the hold.

   Develop on public ep18 (pan + brush), ep39, ep24 and ep2. Score against mocap only afterwards, for reporting.

### 8.2 (ii) Evolutionary search with a GT-free fitness (CPU development; GPU run after a costed plan)

1. **Genome = primitive parameters p (≤ 6–10 dims) + an optional small residual edit** (the current 28-dim θ, with
   σ_fin ≤ 0.1). CMA-ES default λ = 4 + ⌊3 ln n⌋ (Hansen [L]): 10 for n = 10, 13 for n = 28. A 256-world GPU batch
   holds 64 candidates × K = 4 copies.
2. **Per-world realisation without patching FlashCHORD:**
   - compute each world's target stream on the host from its candidate primitive;
   - send it as a raw-mode residual against the shared reference, with the exact EMA inverse;
   - re-centre the shared reference on the CMA mean each generation (bake + fresh env, already the default when
     `--keep_env` is off).
3. **Fitness (no ground truth):**
   - Primary: the kit ADD AUC of the simulated objects vs OUR reference over the window (exists).
   - Robustness: the mean over K = 4 copies.
     - Copy 0 exact.
     - Copy 1: 1e-4 numeric jitter (models GPU non-determinism).
     - Copies 2–3: jitter shaped like FlashSAC exploration (≈ 5 mm wrist, 0.015 rad fingers and rotation,
       piecewise-constant over 1–16 frames) (H2).
   - Penalties:
     - in-hand slip and rotation drift after closure (hand-frame object pose, as `grasp_search.py` measured);
     - penetration at the pre-grasp (`MjPen`, before simulating);
     - per-world constraint count near `njmax` 512.
   - Start the window from **frame 0** for the first hold of each object (the evaluator's start), or reset at least
     from the last quiescent frame. The current window reset at f0 can hide start transients (R4).
4. **Search loop:** CMA-ES with c_m < 1 and IPOP restarts on stagnation [L: Hansen tutorial §B, Auger & Hansen
   restarts], 20 generations per hold. Then **MAP-Elites / CMA-ME** (pyribs `EvolutionStrategyEmitter` × 4,
   batch 16, K = 4) with descriptors computed from the simulated hand at closure:
   - grip location along the object's principal axis;
   - palm-normal azimuth in the object frame;
   - primitive id (a separate archive per primitive).

   This yields a repertoire of diverse good grasps, the DexEvolve idea of a diversity-gated archive [L], for
   fallbacks.
5. **Finalist protocol (evaluator conditions):**
   - take the top 5 robust candidates;
   - bake each, then 8 fresh **1-world GPU** zero-action replays from frame 0;
   - pick the highest mean, with a minimum ≥ 0.6 as a safety rule;
   - then the full-episode zero replay + rest check, then the FlashSAC fine-tune (70M, kp 400, checkpoint by the mean
     of ≥ 3 evaluations).
6. **Budget estimate [I]:**
   - ≤ 10 min GPU per hold for the search (≈ 1.5M env steps);
   - ≈ 2 min for 40 finalist replays;
   - + 18.7 min fine-tune;
   - ≈ 35–40 min per episode with 1–2 holds, about $1 at $1.5/h, vs the standard recipe's 71–79 min.
   - To be confirmed by the running GPU validation (`20261024-ev3-2c1e4dd`, `ev2`).

### 8.3 ES vs RL: where an edge is plausible [I, with measured anchors]

- **Open-loop grasp acquisition is a low-dimensional, non-smooth, contact-rich search.** ES finds it with ~10⁵–10⁶
  env steps:
  - ep39: 0.877 zero action after ≈ 41k CPU env steps (round 1: 16 worlds × 8 gens × 101 frames; round 2: 8 × 12 ×
    291);
  - standard RL on the same reference: 0.826 after 250M steps.
- **But the evolved grasp is open-loop and its basin is narrow** (ep39 fails at 1e-2 jitter). Closed-loop correction
  still needs RL, and the submission needs a learned policy anyway.
- **The combination is the cheapest credible recipe:** ES designs the reference, then the RL fine-tune. The fresh
  actor starts exactly at the ES result (§5.3).
- **The danger is the fine-tune's own exploration destroying a narrow grasp** (ep18: 0.446 at 10M → 0.060 at 70M). H2
  is the test.

---

## 9. Risks

| # | risk | evidence | mitigation |
|---|---|---|---|
| R1 | Rules: the trajectory must come from a learned policy; a zero or step-0 actor or an ES network with FlashSAC metadata may not qualify; changing `scene.contact_friction`, `sim.njmax` or `action.wrist_kp` changes evaluator physics or control through the checkpoint config | FAQ (`docs/forensics-2026-10-21.md:77`); `harness.py:376-427` | submit only fine-tuned FlashSAC policies; ask the organisers before any physics or config change (the mid wrist already needs the owner's confirmation) |
| R2 | CPU-found grasps may not transfer to the CUDA evaluator; GPU fitness is noisy | MJWarp FAQ [L]; ep35 GPU replays 0.150–0.185 | search and re-score on GPU; 8 repeats per finalist |
| R3 | Winner's curse / chaos: the search best overstates the replay | ep18 0.584 → 0.374; 1e-5 jitter → 0.18–0.44 | robust mean; fresh 1-world re-scoring; choose by mean and minimum |
| R4 | The window reset at its first frame ≠ the evaluator's frame-0 start | `grasp_evolve.py:180`; ep18 brush tips at f12–20 on CPU | first hold of each object: start at frame 0; always gate on the full frame-0 replay |
| R5 | The fine-tune's exploration destroys narrow-basin grasps | ep18 curve 0.446 → 0.060 | exploration-shaped jitter in the fitness (H2); repeated-evaluation checkpoint choice; lower `exploration.target_sigma` for fine-tunes (config only) |
| R6 | Residual clip (0.2 m / 1 rad) and θ clip (±4σ) bound the search | `hand_pose.py:111-113`, `grasp_evolve.py:254` | re-centre per generation; primitive parameters span large moves by construction |
| R7 | `--keep_env` in the GPU job re-admits cross-generation state | work log 10:05 UTC (CPU) vs `glock_public.sh:149` | prefer fresh env per generation (scene build ~6 s CPU, less on GPU), or rely on finalist re-scoring |
| R8 | **`pipeline/grasp_search.py` applies "right" variants to the left hand** (and vice versa) | `grasp_search.py:83` vs action schema right 0–27, left 28–55 [M] | the 23 Oct ep3 grid results (366 pinch variants "hold rate 0"; 34/36 wrap variants and 8/8 disturbed trials "hold") **did not vary or disturb the right (spoon) hand**. Treat them as one unperturbed grasp each. Fix to `lay.hand_action_starts` if the tool is used again |
| R9 | Hand rewards follow FK of the target columns (lift, ILC), not the kinematic grasp | §1.1 | measure the offset (H6); fold large ILC leads into the frames used by FDR if needed |
| R10 | No torsional friction (condim 3); rigid convex pads; hands pass through the table | §2.1 | spread contacts or palm opposition; slow under-plate closure; firm squeeze |
| R11 | `njmax` 512 per world is strict: power wraps with many contacts can overflow constraints in the evaluator | training logs "nefc overflow" (work log 23 Oct); MJWarp docs [L] | log `nefc` per world in the search; penalise candidates near the limit |
| R12 | Placeholder mass 0.3 kg: grasps tuned for it | `make_assets.py:52` | none needed for the score (the evaluator uses the same assets) |
| R13 | Local FlashCHORD (`7eb9721`) vs evaluator pin (`8c778f90`) not diffed here | §header | earlier CPU/GPU agreement; final checks on the pristine evaluator worktree (`ops/jobs/submit_pack.sh`) |

---

## 10. Hypotheses, with the experiment that would falsify each

| id | hypothesis | falsifying experiment | cost (estimate) |
|---|---|---|---|
| H1 | A primitive-parameter genome (≤ 10 dims, seeded per object class) reaches a higher robust fitness per evaluation than the raw 28-dim edit | same budget (256 worlds × 20 generations, K = 4) on the ep18 pan, ep39 pan and ep24 board 1; compare finalists' mean of 8 fresh 1-world GPU replays; **falsified if the raw genome ≥ the primitive genome on ≥ 2 of 3** | ~1 GPU-h incl. replays, ≈ $1.5 |
| H2 | Robustness jitter shaped like FlashSAC exploration (≈ 5 mm / 0.015 rad, held 1–16 frames) gives evolved references whose fine-tune does not degrade | ep18 references evolved with jitter 0.005 vs exploration-shaped; 70M fine-tune each, curve at 10/30/50/70M with 3 evaluations per checkpoint; **falsified if the shaped version's 70M sim_vs_ref is not higher than both its own 10M value and the unshaped 70M value** | 2 × (search + fine-tune) ≈ 1.2 GPU-h, ≈ $2 |
| H3 | On these holds, CMA-ES with K = 1 is no better than random sampling with the same number of evaluations | random search (same σ, same evaluations) vs CMA-ES on ep39 / ep18 / ep24 holds, each finalist re-scored 8× fresh; **falsified if CMA-ES beats random by > 0.05 on ≥ 2 of 3** | CPU possible (slow) or ~0.5 GPU-h |
| H4 | GPU-evolved grasps transfer to the evaluator better than CPU-evolved ones | the ep39 CPU result (0.877) vs a GPU-evolved ep39 grasp, both baked, 8 GPU 1-world replays each; **falsified if CPU ≥ GPU** | part of the running validation |
| H5 | Per-world physics randomisation (μ ±20 %, mass ±30 %) is unnecessary because the evaluator's physics is fixed | robust search with vs without physics randomisation, finalists scored 8× in exact physics; **falsified if the randomised search's exact-physics mean is higher** | ~0.5 GPU-h |
| H6 | The ILC/lift offsets in the target columns move the reward's hand keypoints far from the locked grasp | measure the distance between FK(target) and the locked grasp pose over the holds of ep3 / ep35 / ep39 (CPU, minutes); **falsified if < 1 cm p95** | CPU, 10 min |
| H7 | A MAP-Elites repertoire gives a usable fallback: when the top grasp's fine-tune fails, the best grasp from a different cell succeeds | fine-tune top-1 and top-2-from-another-cell on ep18 and ep24; **falsified if top-2 never beats top-1** | ~1 GPU-h |
| H8 | A stiffer wrist rotation (`action.wrist_kp` 100–200 instead of 25) reduces in-hand tipping on long-lever carries (spoon bowl, pitcher) | zero-action ep35 / ep21 with `wrist_kp` 25 vs 150 (CPU); **falsified if the bowl tipping and sim_vs_ref do not improve**; needs an owner/rules decision before any use | CPU, 10 min per variant |

---

## 11. Open questions

- The GPU timing and transfer of the robust search, from the running boxes `20261024-ev3-2c1e4dd` and
  `20261024-ev2-2c1e4dd`.
- Will the organisers accept an ES-trained policy network, or physics/control settings other than the defaults
  (`action.wrist_kp`, `njmax`)? The mid wrist embodiment already needs the owner's confirmation.
- Are the evaluator pin `8c778f90` and the local `7eb9721` identical in `runtime/`, `envs/`, `scene/` and
  `evaluation/`? A diff needs GitHub access to `nvidia-isaac/video_to_data` in this session.
- Contact condim: does the evaluator's MJWarp model really run all hand–object contacts at condim 3? This follows
  from Newton's default (`solver_mujoco.py:623-632`); I did not read the compiled `geom_condim` array.

---

## 12. Sources

Literature (opened):
- Hansen, N. *The CMA Evolution Strategy: A Tutorial* (2016). https://arxiv.org/abs/1604.00772 (PDF read):
  - λ = 4 + ⌊3 ln n⌋;
  - "Increasing λ usually improves the global search capability and the robustness … Independent restarts with
    increasing population size … are a useful policy";
  - "Choosing c_m < 1 can be advantageous on noisy functions".
- Hansen, N., Niederberger, A., Guzzella, L., Koumoutsakos, P. *A method for handling uncertainty in evolutionary
  optimization with an application to feedback control of combustion*. IEEE TEC 13(1):180–197 (2009). Abstract at
  https://researchportal.ip-paris.fr/en/publications/a-method-for-handling-uncertainty-in-evolutionary-optimization-wi/
- Mouret, J.-B., Clune, J. *Illuminating search spaces by mapping elites* (2015). https://arxiv.org/abs/1504.04909
- Fontaine, M. C., Togelius, J., Nikolaidis, S., Hoover, A. K. *Covariance Matrix Adaptation for the Rapid Illumination
  of Behavior Space* (CMA-ME, 2019/2020). https://arxiv.org/abs/1912.02400. Pyribs (implements CMA-ME):
  https://github.com/icaros-usc/pyribs (README read).
- Salimans, T., Ho, J., Chen, X., Sidor, S., Sutskever, I. *Evolution Strategies as a Scalable Alternative to
  Reinforcement Learning* (2017). https://arxiv.org/abs/1703.03864 (PDF read): 1,440 workers, 3-D humanoid in < 10
  min; "no more than 10x as much data" as TRPO on MuJoCo; 3–10x vs A3C on Atari.
- Lange, R. T. *evosax: JAX-based Evolution Strategies* (2022). https://arxiv.org/abs/2212.04180
- Zurbrügg, R., Cramariuc, A., Hutter, M. *DexEvolve: Evolutionary Optimization for Robust and Diverse Dexterous Grasp
  Synthesis* (2026). https://arxiv.org/abs/2602.15201 (HTML read):
  - fitness = lifetime under axis-wise disturbance forces − contact-distance and penetration penalties;
  - novelty-gated archive; tournament selection; Gaussian mutation of the wrist Euler angles and joints.
- Yuan, H. et al. *DemoGrasp: Universal Dexterous Grasping from a Single Demonstration* (2025).
  https://arxiv.org/abs/2509.22149: the edit-one-demonstration (wrist pose + joint angles) idea.
- MuJoCo documentation, Computation:
  - Reproducibility: "entirely deterministic … within a single version, on the same architecture"; contacts have
    high Lyapunov exponents;
  - condim: torsional friction needs condim 4 and "can substantially improve the stability of simulated grasping".

  https://mujoco.readthedocs.io/en/stable/computation/index.html
- MuJoCo Warp documentation and README:
  - "Is MJWarp on GPU deterministic? No … Set device to CPU … for deterministic results";
  - nworld / nconmax / njmax semantics.

  https://mujoco.readthedocs.io/en/latest/mjwarp/index.html,
  https://github.com/google-deepmind/mujoco_warp

Code and data (local):
- FlashCHORD source: as cited (local copy, see the header).
- Newton (`fcvenv/lib/python3.12/site-packages/newton/_src/solvers/mujoco/solver_mujoco.py`).
- Kit `scratchpad/kit/v2d_submission_kit`.
- Repository files as cited.
- Stored logs: `scratchpad/evo/**` (the lead's CPU searches) and the HF store `runs/20261023-spoon3R-4c31271/glock/*.log`.

Scripts and outputs of this report, all CPU:
- `docs/research/grasp/capability-scripts/hand_geom.py` → `hand_geom_output.txt`: collision mesh extents, convexity,
  volumes. Run: `venv/bin/python -I hand_geom.py <flash_chord>/src/flash_chord/assets`.
- `docs/research/grasp/capability-scripts/object_inertia.py` → `object_inertia_output.txt`: mass, inertia and extents
  exactly as `make_assets.py` builds them.
- `docs/research/grasp/capability-scripts/timed_zero.py` → `timed_zero_output.txt`: one timed zero-action replay. Run
  from the flash_chord dir: `EMB=sharpa_hands_mid DEV=cpu fcvenv/bin/python -I timed_zero.py <ref_gl_ilc.parquet> 319
  <out.npz>`. Then `KIT=… venv/bin/python tools/trace_score.py <ref> <out.npz>`.
- Trace: `scratchpad/grasp_work/capability/zero_ep39_evolved.npz`. Web copies: `scratchpad/grasp_work/capability/web/`.
