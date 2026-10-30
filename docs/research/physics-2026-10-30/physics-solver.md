# Physics solver: a sampling optimiser in the scored simulator (30 Oct 2026)

Question (owner, 30 Oct): copying the perceived motion into FlashCHORD does not carry the objects. The Sharpa hand,
a human capsule hand, extra squeeze and a locked grasp all fail. Only RL (FlashSAC, ~70M steps, GPU) fixes it.
Would a sampling optimiser that searches **in the simulator** for hand actions (SPIDER, Do as I Do) do it? How would
it fit our references and our simulator, and can we try it on CPU?

Labels:
- **[M]** measured or read in code here today; commands are in §7;
- **[L]** literature, from the papers or our earlier notes;
- **[I]** inference;
- **[H]** hypothesis, with the experiment that would falsify it.

No ground truth was read. The solver and its scoring use only our reference parquet: our perceived object poses, the
retargeted Sharpa targets, object names and URDFs, and the support. No GPU was rented. Cost: $0.

RESULTS_PLACEHOLDER

## 1. The two codebases [M]

Both were cloned into the scratchpad (`src/do-as-i-do`, `src/spider`; `GIT_LFS_SKIP_SMUDGE=1 git clone`). The GitHub
API was not needed.

| | Do as I Do | SPIDER |
|---|---|---|
| Paper | arXiv 2606.19333 | arXiv 2511.09484 |
| URL | https://github.com/malik-group/do-as-i-do | https://github.com/facebookresearch/spider |
| Commit read | `824591b808c3` (2 Aug 2026, "Bundle MANO + IK reference assets for whisking replay demo") | `44717007de41` (22 Sep 2026, "Release full lifted dataset conversion and Viser inspection tools") |
| Licence (LICENSE file) | **MIT**, "Copyright (c) 2026 malik-group". Built on SPIDER, whose code it vendors and modifies. | **CC BY-NC 4.0**, "Copyright (c) Meta Platforms, Inc. and affiliates": no commercial use |
| Physics | MuJoCo Warp, pinned to git commit `5d5a645` + `mujoco==3.4.0` + `warp-lang==1.10.1` | `mujoco==3.7.0`, `mujoco-warp==3.7.0.1`, `warp-lang==1.12.1`; also Genesis, IsaacGym, HDMI back-ends |
| Other deps | torch (sampling maths), mink (IK), coacd, trimesh, viser; Python ≥ 3.12; no JAX | torch, hydra, mink, pymeshlab, open3d, rerun, viser; Python ≥ 3.12; no JAX |
| GPU | "An NVIDIA GPU with CUDA is required for the physics-optimization stage" (README); `device: cuda:0`; CUDA graph capture of `mjwarp.step` | same (`device: cuda:0`) |
| Robot models | `assets/robots/sharpa/{left,right,bimanual}.xml` (Sharpa Wave MJCF), MANO | ability, allegro, inspire, metahand, schunk, xhand, MANO, humanoids; **no Sharpa MJCF in the public repo** |
| Size | 94 MB | 442 MB (LFS skipped) |

Consequences for us:
- SPIDER code must not enter our Apache-2.0 repository. Nothing from it was copied.
- Do as I Do is MIT. It may be adapted with its copyright notice. Its `retargeting/` package descends from SPIDER, so
  before copying any file we would check that the file is not a verbatim SPIDER file (CC BY-NC) [I].
- The prototype below copies no code from either. It re-implements the published idea (annealed sampling MPC) inside
  FlashCHORD and cites both.

## 2. What they optimise [M from code, L from papers]

Do as I Do `retargeting/`. Its stages: `process_dataset` → CoACD → MJCF scene → mink IK → pedestal →
`optimize_physics`. The values below come from `config/default.yaml`, `config/override/do_as_i_do.yaml`,
`utils/sampling.py`, `utils/mjwp.py` and `pipeline/optimize_physics.py`.

- **Decision variables:** position-actuator targets (`ctrl`) for every robot DoF. That is **6 wrist DoF** (3 slide +
  3 hinge joints, `kp 1000`) plus **the finger joints** (`kp 300`, armature 1.0), for each hand. They are absolute
  targets, warm-started from the IK trajectory. They are not residuals on a policy.
- **Parameterisation:** knots every 0.2 s (`knot_dt`), linearly interpolated to `sim_dt` 5 ms. Noise:
  - per component: wrist position 0.01, wrist rotation 0.01, joints 0.1;
  - along the horizon: a log ramp from ×1 to ×4;
  - across iterations: annealed by β = 0.01^(1/32).
- **Horizon and replanning:** 3.0 s horizon, re-planned every 0.5 s (`ctrl_dt`). The first 0.5 s of the plan is
  executed. The warm start is the plan shifted by 0.5 s, plus the IK reference with the splice offset decaying
  linearly to zero.
- **Samples:** 1,024 per iteration, 32 iterations, early stop below 0.01 improvement for 2 checks. Each sample runs 4
  times with random object pushes (0.5 m·g force, 0.5 torque; start probability 0.05 per step, continue 0.95; only
  while the reference holds the object lifted). Rewards are averaged over the 4 runs, so **4,096 worlds per
  iteration**.
- **Update:** softmax (temperature 1) over the **top 10 %** of z-normalised rewards. The new plan is the weighted mean.
- **Cost** (negated reward, per step, averaged over the horizon, terminal step ×10):
  - `‖W ⊙ (q_sim ⊖ q_ref)‖₂` with W: object position 1.0, object rotation 0.3, wrist position 0.1, wrist rotation
    0.03, finger joints 0.01;
  - velocity term 1e-4;
  - hand-object penetration `3000 · max(pen − 5 mm, 0)²`;
  - a **contact-state term 0.5**: while the reference is "in hand" (hand-object < 10 cm) and the object is off its
    support, penalise worlds with no hand-object contact; while the reference rests (< 1 cm from the support) and is
    not in hand, penalise worlds with no object-support contact.
- **Warm-up:**
  - 3 s prepended;
  - the object is **welded** in place and gravity is off;
  - the hand starts backed off along −palm-normal to ≥ 10 cm clearance, with open fingers;
  - the reference is interpolated to frame 0; reward ×0.1;
  - then the weld drops.
- **Inputs:**
  - the reconstruction folder: MANO hand tracks (`all_hand_meshes.npz`), the object mesh, per-frame object poses, a
    camera layout and gravity;
  - stage 1 turns these into fingertip and wrist keypoint trajectories; stage 4 (mink IK) into robot `qpos`/`ctrl`;
  - **at most one free object per hand** (`qpos_obj_right`, `qpos_obj_left`; a bimanual demo shares one object);
  - contacts are optional (`contact_rew_scale` 0 by default).
- **Output:** `trajectory_mjwp.npz`, the executed `qpos`, `qvel` and `ctrl` per sim step, per replan chunk. It is an
  **open-loop target trajectory** in their simulator: wrist 6-DoF targets plus finger targets, and the resulting
  object poses.

SPIDER (`examples/config/default.yaml`, `override/*`; read, not copied):
- the same MPPI/DIAL-style annealed sampler. Defaults: 1,024 samples, 32 iterations, 1.6 s horizon, knots 0.4 s,
  `sim_dt` 0.01. The "fast" overrides: 4 iterations, 3 s horizon, `ctrl_dt` 1.5 s;
- cost `Σ‖x ⊖ x_ref‖²_Q + ‖u‖²_R` [L];
- optional **virtual contact guidance** [L, our notes `port-recipes-2026-10-21.md` §2.6]. The object's free joint
  becomes 6 actuated joints pulled toward the reference plus the hand-contact offset. Their gains decay per iteration
  and are exactly 0 in the last one;
- SPIDER has no warm-up, perturbations or contact-state term. Those are Do as I Do's additions;
- reported effect of the additions [L, Do as I Do Table 3]: success on in-the-wild reconstructions 0.25 (SPIDER
  sampling) → 0.66 with warm-up → 0.71 with all three.

## 3. Feeding our reference, and the physics mismatch [M]

### 3.1 Mapping a ManoSharpaData parquet into Do as I Do

- **Objects:** `object_body_position` / `_wxyz` give the object `qpos` directly. The URDF meshes go to their CoACD
  stage, and our masses replace their density 1000.
  - Their data model has one free object per hand. ep2 (pot left, lid right), ep18 and ep24 fit as a right and a left
    object.
  - ep12's static rack would have to become a fixed obstacle. That is a scene-generator change.
- **Hands:** we already have Sharpa wrist poses and 22 finger targets per frame (`robot_<side>_*`). Their stages 1–4
  (keypoints → mink IK) can be skipped by writing their `trajectory_kinematic.npz` (`qpos` = 6 wrist DoF + 22 fingers
  per hand + object `qpos`; `ctrl` = the same robot part). The wrist parameterisation differs: they use 3 slides + 3
  Euler hinges; FlashCHORD uses 3 prismatic joints + a ball joint. The conversion is a few lines [I].
- **Joint names** match: their MJCF uses the same Sharpa names (`right_thumb_CMC_FE`, …).
- **Back to us:** their output (wrist pose and finger targets per sim step, at 200 Hz) would be resampled to 20 Hz and
  written into `robot_<side>_wrist_position/_wxyz/_finger_joints`. Then comes the FlashCHORD replay.

### 3.2 Their simulator vs the scored one

| | Do as I Do (generated scene + `sharpa/*.xml`) | FlashCHORD (scored) |
|---|---|---|
| Engine | MuJoCo Warp `5d5a645`, mujoco 3.4.0, warp 1.10.1 | MuJoCo-Warp 3.8.1 via **Newton 1.2.0** `SolverMuJoCo`, mujoco 3.8.1, warp 1.14.0 |
| Time step | 5 ms (`sim_dt`), control every step | 10 ms (20 Hz × 5 substeps) |
| Solver | implicitfast, 100 iterations, 200 line-search | implicitfast, Newton, 100 iterations, 50 line-search |
| Contacts | explicit pairs, **condim 6** (torsional and rolling friction), friction (1, 1, 0.1), hand-object solimp (0.998, 0.998, 0.001), solref 0.01; cone default (pyramidal) | condim 3, μ 1.0 everywhere, **pyramidal cone, impratio 20**; Newton shape material (`ke` 1e3 on the robot) mapped to solref |
| Wrist | 6 position actuators, kp 1000, on a 0.1 kg massless base | prismatic xyz position servo **kp 400**, kd 20, 150 N (`sharpa_hands_mid`); ball joint **effort PD kp 25**, kd 6, 45 N·m |
| Fingers | position actuators **kp 300**, armature 1.0, dampratio 1 | **kp 1.7 N·m/rad**, kd 0.1, armature 0.01, effort 10 N·m |
| Gravity on the hand | not compensated (stiff servo) | gravity compensation on every robot DoF |
| Objects | density 1000 (mass from volume), frictionloss 1e-4; meshes thickened and dilated 2 mm | our URDF masses (S1: cup 128 g, rack 387 g); CoACD hulls of the NVIDIA scans |
| Warm-up | 3 s with the object welded and no gravity | none: the evaluator starts at frame 0 |

The two simulators differ in timestep, contact dimensionality (condim 6 vs 3), finger stiffness (×176) and wrist
control. Do as I Do's MJCF and options could be edited toward these values. The wrist ball-effort controller, Newton's
contact conversion and gravity compensation would remain different code paths. So a trajectory optimised there would
still need adaptation in FlashCHORD (RL or a second, FlashCHORD-native pass) [I].

A plan that holds a cup with torsional friction (condim 6) and a 300 kp finger can lose it under condim 3 and a 1.7 kp
finger. That is why I built the prototype to sample **in FlashCHORD itself**, with no second simulator.

The FlashCHORD source supports this design: `envs/base.py` calls itself the "Shared device-native environment
transition for RL and sampling workflows", and `runtime/sim.py` says "Both the replay and the RL/MPPI env consume one
SimConfig". The MPPI workflow itself is not in our port.
