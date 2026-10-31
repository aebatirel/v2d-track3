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

## 0. Answer

1. **Code.**
   - Do as I Do (MIT, github.com/malik-group/do-as-i-do @ 824591b) and SPIDER (CC BY-NC 4.0, facebookresearch/spider
     @ 4471700) are cloned and read.
   - Both are GPU-only MuJoCo-Warp annealed-sampling MPCs.
   - Do as I Do ships a Sharpa MJCF. Its simulator differs from FlashCHORD in timestep, contact dimension (condim 6 vs
     3), finger stiffness (kp 300 vs 1.7) and wrist control. Plans made there would not transfer as they are (§1–3).
2. **Prototype.** I built the same idea **inside FlashCHORD** (`tools/physics_solve/solve.py`, Apache-2.0-compatible:
   no code copied).
   - The rollouts are FlashCHORD worlds. The output is a reference parquet.
   - Its zero-action replay is **bit-identical** to the solver's committed trajectory (checked over all 181 frames).
3. **Results on public ep12, CPU, < 21 min per run** [M].
   - **Nominal zero-action sim_vs_ref** (our reference, no ground truth): 0.600 (grasp lock + ILC) → **0.6485**
     (solver v1) → **0.6899** (v3: robust copies + rollback). The floor is 0.605. The cup is now carried in-hand to
     ~f84 instead of being lost at f37.
   - **These gains are not robust.** Under 0.5 mm / 0.005 rad target noise, all three references score the same
     (0.556 ± 0.031 / 0.559 ± 0.025 / 0.564 ± 0.039, 8 copies). Under 10 µm / 1e-4 rad noise they also score the
     same (0.570 / 0.574 / 0.564).
   - The pre-registered robust-gain bar (jittered ≥ 0.586) is **not met**: [H-robust] is falsified at this budget.
   - So at ~1/500 of Do as I Do's sample budget, the solver finds lucky trajectories of a chaotic system, not
     grasps that hold. A GPU evaluator or an RL residual would not reproduce them.
4. **Side result.** A single zero-action replay is a noisy estimate of a reference's quality.
   - Jittered GL+ILC: ep2 0.260 ± 0.071 (nominal 0.141), ep12 0.556 ± 0.031 (nominal 0.600), ep18 0.219 ± 0.075
     (nominal 0.279), ep24 0.200 ± 0.006 (nominal 0.203).
   - CPU gates that compare single replays (step 2 of the physics study, `cpu_glock_zero.sh`) should use
     `jitter_check.py` means instead [I].
5. **Next step: GPU G1** (§5). The method needs a ~100–1,000× larger search than the CPU allows, with ≥ 4 robust copies.
   - Cost: one RTX PRO 6000 box, ~1 h, **~$1–1.5**.
   - Runs: G1 scale on ep2/12/18/24, then a 32-copy jitter check.
   - Pre-registered bar: jittered mean ≥ GL+ILC jittered + 0.03 on ≥ 2 of 4 episodes.
   - Only if G1 passes: Do as I Do scale (~5 h, ~$6–8), then RL from the solved references (~$6.5).
   - Before G1: the CUDA port of `solve.py` (§5 step 1, ~half a day, testable on CPU).

## 1. The two codebases [M]

Both were cloned into the scratchpad (`src/do-as-i-do`, `src/spider`; `GIT_LFS_SKIP_SMUDGE=1 git clone`). The GitHub
API was not needed.

| | Do as I Do | SPIDER |
|---|---|---|
| Paper | arXiv 2606.19333 | arXiv 2511.09484 |
| URL | https://github.com/malik-group/do-as-i-do | https://github.com/facebookresearch/spider |
| Commit read | `824591b808c3` (2 Aug 2026, "Bundle MANO + IK reference assets for whisking replay demo") | `44717007de41` (22 Sep 2026, "Release full lifted dataset conversion and Viser inspection tools") |
| Licence (LICENSE file) | **MIT**, "Copyright (c) 2026 malik-group". README: "This codebase is built on SPIDER". Its `retargeting/` modules mirror SPIDER's layout [I]. | **CC BY-NC 4.0**, "Copyright (c) Meta Platforms, Inc. and affiliates": no commercial use |
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

## 4. CPU prototype: `tools/physics_solve/solve.py` [M]

### 4.1 Design

The solver is written from scratch. It copies no code from either repository, and its docstring cites both.

- **The rollouts are FlashCHORD worlds.** The settings are those of the evaluator replay (`tools/trace_rollout.py
  zero`): our `sharpa_hands_mid` embodiment, VOC 0, no termination, no auto-reset, S1 object URDFs, the scan meshes and
  the support. So there is **no sim-to-sim gap**: a plan is evaluated in the physics that scores it.
- **Decision variables:** FlashCHORD's own residual channels (`runtime/actions/hand_pose.py`). Per frame and per active
  hand: a wrist position offset (m), a wrist rotation offset (rpy rad, composed as `ref ⊗ quat_rpy`) and 22 finger
  target offsets (rad). Planner worlds take them through the action buffer, with raw input and EMA 0, so the action
  equals the offset divided by the scale. Finger targets are kept no further outside the joint limits than the
  reference itself, so a zero offset stays exactly zero.
- **Sampler** (Do as I Do / SPIDER style):
  - knots every 4 frames (0.2 s), linear interpolation;
  - per-dimension noise of 1 cm wrist, 0.05 rad wrist rotation, 0.15 rad fingers;
  - a log ramp from ×1 to ×4 along the horizon; ×0.6 annealing per iteration;
  - sample 0 is the current plan;
  - softmax with temperature 1 over the top 10 % of z-normalised costs.
- **Committed window:** the **lowest-cost sequence evaluated** in any iteration. Sample 0 of iteration 0 is the warm
  start, so a commit never predicts worse than the warm start.
- **Cost per frame:**
  - Σ over objects of the ADD distance of 64 points on a 5 cm sphere, clipped at 10 cm (the metric's 1–9 cm AUC);
  - plus regularisation 0.1·|Δp| + 0.03·|Δr| + 0.01·|Δf|;
  - mean over the horizon, terminal frame ×3.
- **Gate:** a hand is optimised while any of its reference frames is within 10 cm of the bounding sphere of an object
  that moves in the reference (> 2 cm or > 10°). ep12: the right hand at frames 8–166. The left hand never qualifies.
- **Receding horizon:** commit 4 frames (0.2 s), shift the plan, and append the last offset decaying to zero.
- **Processes:**
  - the master holds a 1-world **truth** env: the zero-action replay with the committed offsets patched into its target
    buffers;
  - 4 worker processes hold W-world planner envs. Before every rollout batch, every planner world is set to the truth
    state: `joint_q`/`qd`, `body_q`/`qd`, MuJoCo `qacc_warmstart`, timestep.
- **Rollback** (`--retries`; SPIDER's "difficulty boosting", here with an exact restore): if a moving object goes from
  ≤ 5 cm to > 5 cm ADD within one commit, the truth env is restored to its snapshot 3 chunks back. Those chunks are
  re-planned with (1 + boost)× the iterations and √2^boost × the noise.
- **Robust objective** (`--robust K`, v3; cf. Do as I Do's 4 perturbed copies per sample):
  - each candidate runs as K worlds. Copy 0 is nominal. Copies 1..K−1 add fresh per-frame target noise (0.5 mm on the
    wrist, 0.005 rad on the fingers), with the same draws for every candidate of an iteration;
  - J is the mean over the K copies;
  - the nominal sequence is committed.
- **Output:** the input parquet with the offsets folded into `robot_<side>_wrist_position` / `_wrist_wxyz` /
  `_finger_joints`. Frames with zero offset keep their original values. Also written: `_solve.json` (per-replan log),
  `_solve.npz` (offsets; the truth trajectory in the `trace_rollout` npz layout) and `_solve.log`.

### 4.2 Exactness checks (all passed) [M]

| check | result |
|---|---|
| Planner world restored from a truth snapshot, zero offsets, vs the truth (frames 8, 12, 16, 24; 8–12 steps) | max \|Δ body_q\| **0.0** |
| World 0 of a 4-world planner (zero action) while worlds 1–3 run random actions, vs the truth | **0.0**: worlds are independent in MuJoCo-Warp |
| A 3-world env stepped from its own `reset()` vs the 1-world truth | 3.1 mm after 8 frames. Only restore-from-snapshot is exact; reset in a multi-world env is not |
| Patched truth target buffers vs a fresh load of the written parquet | **bit-identical** (wrist pos, quat, fingers) |
| Truth trajectory vs official `trace_rollout.py zero` replay of the written parquet (v1, 181 frames; rollback test, 49 frames) | max \|Δq\| **0.0** |
| `jitter_check.py` copy 0 vs `trace_score.py` | 0.6000 / 0.6485, identical |

Bugs found and fixed on the way. Each one changed results:
1. **Quaternion rounding.** FlashCHORD's loader passes the wrist quaternion through float32 storage, a float64
   normalisation, Newton FK on a robot-only model, and a float32 re-normalisation (`binding._bind_hand`). Patching the
   truth with my own float64 → float32 conversion differed by one float32 ulp (6e-8) on 39/181 frames. That was enough
   to change the cup outcome. `ExactTargets` now replays the loader's exact path.
2. **Finger limits.** The reference's own finger targets sit slightly outside the joint limits on some frames, so
   clipping turned a zero offset into a nonzero one. The clip is now relative to the reference.
3. **Reset hold.** A never-`reset()` FlashCHORD env starts every world with VOC 1 and a reset hold that freezes the
   reference frame for `voc_decay_steps` (`lifecycle/reset.py`: `applied_voc_scale` initialised to ones). The planner
   predicted with the object assist on during its first ~20 steps. v1 had this bug, but it affected only its first
   replan (frames 0–3, hand still far from the cup). Fixed: workers call `env.reset(frame_id=0)`.

### 4.3 Runs on public ep12 (cup → rack), CPU [M]

Machine: this cloud container (4 CPUs, no GPU), FlashCHORD at the evaluator pin, scratchpad `fcvenv`.
- Input: the S1 CPU grasp-lock + ILC reference (`phys/S1/out/ep12/.../ref_gl_ilc.parquet`; zero action 0.600, floor
  0.605).
- Outputs: scratchpad `phys/solve/<tag>/` (`run.log`, `solve.out`, `zero_ps.npz`,
  `processed/.../ref_ps{.parquet,_solve.json,_solve.npz,_solve.log,_jitter.npz}`, `solve_used.py`).
- Code: `tools/physics_solve/solve.py`. Each run directory holds the exact copy used (`solve_used.py`, md5 in
  `run.log`).
- "Jittered" below means `jitter_check.py --k 9`: copy 0 plus 8 copies with N(0, 0.5 mm) wrist-position and
  N(0, 0.005 rad) finger target noise on every frame, seed 0.

| run | settings | wall | zero-action sim_vs_ref (nominal) | jittered (8 copies) mean ± sd [min, max] | cup within 3 cm / lost |
|---|---|---|---|---|---|
| floor (do nothing) | — | — | 0.605 | — | — |
| plain Sharpa copy (base ref) | — | 15 s | 0.556 | not run | 20 % / f37 |
| grasp lock + ILC (baseline) | recipe, CPU | 567 s | **0.600** | **0.556 ± 0.031** [0.516, 0.614] | 21 % / f38 |
| solver v1 | 64 samples × 4 iterations, H 16, commit 4, no rollback, no robustness | 695 s | **0.6485** (+0.049) | **0.559 ± 0.025** [0.510, 0.589] | 28 % / f37 (held at 2–4 cm until f56, lost at the fast carry f57–60) |
| solver v2 | v1 + H 20 + rollback (6, back 3) | stopped after t=40 (superseded by the jitter result) | — | — | — |
| solver v3 | 24 candidates × 4 robust copies × 4 iterations, H 16, rollback 4 | 1,203 s (+26 s replay and score) | **0.6899** (+0.090) | **0.564 ± 0.039** [0.514, 0.622] | 33 % / f37. It slips to 2–5 cm at f37–56, then is carried at 1–4 cm through f84 after all 4 rollbacks (at f52, f52, f64, f68). Lost at f86–92, then 25–28 cm off to the end |

Readings:
- **v1 beats the grasp lock on the exact replay (+0.049, above the floor), but not under 0.5 mm of noise.** Jittered,
  v1 scores 0.559 ± 0.025 and the grasp lock 0.556 ± 0.031: the same. The sampler optimised one exact chaotic
  trajectory. The gain does not survive the perturbations that a GPU evaluator, a different machine or an RL residual
  will add. Even 10 µm / 1e-4 rad noise (`--sig_pos 1e-5 --sig_fin 1e-4 --seed 1`) evens them out: grasp lock
  0.570 ± 0.016, v1 0.574 ± 0.015.
- This matches the parent's finding today (commit 86f15fe, "zero-action replays are chaotic"). It is also why Do as I
  Do scores every sample on 4 perturbed copies. A nominal-only solver is not worth porting.
- v1 offsets reached 5.1 cm on the wrist, 0.19 rad wrist rotation and 1.0 rad on the fingers (at the residual clip),
  on 70 of 181 frames.
- Sampling beat the warm start in 9 of 42 replans, mostly in the lift (f20–56). In the carry (f57+) no sample in 64
  saved the cup, and once lost it is never recovered.
- Predicted and realised commit costs agree exactly in 38 of 42 replans. The 4 exceptions are rounding differences
  between the action path and the folded parquet on contact-sensitive frames; the truth is exact either way.
- **v3** (robust copies + rollback) carries the cup further in the nominal replay: 0.6899, the cup within 3 cm on 33 %
  of frames, in-hand to f84. The pre-registered jitter reading is **0.564 ± 0.039 < 0.586: no robust gain**. Its 3
  noisy copies per candidate (24 candidates) were too few to make the selection robust. Tiny (10 µm / 1e-4 rad) noise
  gives 0.564 ± 0.040 for v3 vs 0.570 ± 0.016 for the grasp lock.
- v3's offsets reached 11.8 cm on the wrist, 0.42 rad rotation and **1.29 rad on the fingers, beyond FlashCHORD's
  1.0 rad residual clip**. The planner's action path clipped those samples while the folded parquet did not, so 9 of
  54 v3 replans had predicted ≠ realised commit cost. The truth and the scores are unaffected; the planner was simply
  less accurate on those frames. Fixed after v3: the sampler now clips offsets to the residual clips (solve.py md5
  `c41881ae`, smoke-tested, not re-run on the full episode).
- Rollbacks re-planned the lift and early carry 4 times. Each boosted re-plan took 31–50 s. The rollback budget ran
  out at f68, and the cup was lost at f86–92 with no budget left.

### 4.4 Cost of the CPU prototype [M]

- v1: 172,032 planner world-frames in 695 s on 4 cores shared with two niced `wrist_ilc.py` jobs of the parent
  session. That is **15.5 ms per world-frame per core**.
- Uncontended benchmark: 72 ms per frame at 1 world, 10 ms per world-frame at 32 worlds, 8 ms at 128 worlds, single
  threaded (Warp CPU kernels).
- At these speeds:
  - one ep12 solve at v1 scale: ~12 min;
  - the 4 public episodes (1,152 frames, three of them bimanual): ~1.5–2.5 h of CPU;
  - but only at a sample budget ~500× below Do as I Do's (64 × 4 × 16 vs 4,096 × 32 × 60 world-frames per replan).
- **CPU is enough to develop and verify the solver, not to search at the scale the method needs.**

## 5. GPU plan (G1 pre-registered in §5.1 and passed; G2 + G3 pre-registered in §5.2) [E]

Throughput assumption: **~50k world-frames/s** on an RTX PRO 6000 at ≥ 1,024 worlds [E]. That is below our measured
RL training rate of 55–63k env steps/s at 4,096 worlds (work log, 23–26 Oct), which includes the learner.

Formula: world-frames per episode = frames × (N·K·I·H) / C. Episodes: ep2 343 frames, ep12 181, ep18 353, ep24 275
(1,152 frames in total).

| scale | N × K (worlds) | iterations | horizon | commit | world-frames, 4 episodes | GPU time [E] | cost at $1.2–1.5/h |
|---|---|---|---|---|---|---|---|
| CPU v3 equivalent | 24 × 4 (96) | 4 | 16 (0.8 s) | 4 | 1.8M | < 5 min (latency bound) | < $0.2 |
| **G1 middle** | 256 × 4 (1,024) | 8 | 40 (2 s) | 5 | 75M | ~25 min + ~15 min setup | **~$1–1.5** |
| G2 Do as I Do | 1,024 × 4 (4,096) | 32 | 60 (3 s) | 10 | 906M | ~5 h | **~$6–8** |

Each episode's references and object assets are already built (S1, `phys/S1/out/ep*`). The four GL+ILC baselines at
zero action are 0.141 / 0.600 / 0.279 / 0.203.

Steps:
1. **Port to CUDA** (CPU-testable first):
   - one process and one env with N·K worlds; no worker processes;
   - restore = tile the snapshot to the W worlds and `assign` (≈ 14 MB per restore at 4,096 worlds);
   - ADD cost computed in a Warp kernel instead of copying poses to the host each frame;
   - `capture_step` CUDA graphs;
   - keep the 1-world truth env on the box CPU, so the committed trajectory stays bit-identical to our CPU replay and
     scorer.
   - [H-gpu] GPU planning vs CPU truth adds float-level mismatch; the K robust copies should absorb it. Falsified if
     the realised commit cost exceeds the GPU-predicted one by > 50 % on most active replans.
2. **G1** (one box, ~1 h, ~$1.5):
   - G1 scale on ep2, ep12, ep18, ep24;
   - then `jitter_check.py` with 32 copies per output, on the box (GPU) and on CPU here;
   - pre-registered reading: **robust gain** if the jittered mean beats the GL+ILC jittered mean by ≥ 0.03 on ≥ 2 of 4
     episodes, with no episode ≤ −0.05. GL+ILC jittered baselines (8 copies, 0.5 mm / 0.005 rad, seed 0; measured
     here): ep2 0.260 ± 0.071, ep12 0.556 ± 0.031, ep18 0.219 ± 0.075, ep24 0.200 ± 0.006. Re-measure with 32 copies
     on the box;
   - outputs to the HF store, summaries to git.
3. **G2** (only after a G1 robust gain): Do as I Do scale on the episodes that gained (≤ ~5 h, ≤ ~$8).
4. **G3, the use that matters:** RL (the frozen recipe, 70M steps; ≈ $6.5 per 4-episode box today) from the solved
   reference vs from GL+ILC, same seed.
   - [H-RL] a physically consistent reference lets FlashSAC reach the S1 score faster. ep12 S1 reached 0.885 only at
     70M; its curve was 0.55–0.62 until 60M. Falsified if the solved-reference run is not ≥ 0.03 higher at 30M on ≥ 2
     of 4 episodes.
   - Integration decision before G3: the reference's `robot_<side>_frames` (the RL hand-tracking target) stay the
     intended hand, as in `wrist_ilc.py`, or are replaced by the solved hand's FK. To be decided with the owner.

### 5.1 G1 pre-registration (written 30 Oct 2026 ~17:20 UTC, before any GPU result)

The owner approved option 3 ("go nuts with all"); the coordinator set a GPU cap of ~$2 for this step. Nothing below
is changed after a GPU result. The settings differ from the G1 row of the table above: the iterations and horizon
were cut to fit ~1 h of box time, and the rollbacks and robust copies of CPU v3 were kept.

**Code.** These versions are committed in `09e59d2` (solve.py from `cec6208`, unchanged). Launch that commit or any
later one with the same md5s:
- `tools/physics_solve/solve.py` md5 `07e3755e`: the CUDA port, CPU-verified as in the table below;
- `tools/physics_solve/jitter_check.py` md5 `3522b860`: CUDA-capable, adds `--json`;
- `ops/jobs/physics_solve.sh` md5 `d2f3d701` (includes the log-grep fix made during the dry run).

CPU checks of the port [M]:

| check | result |
|---|---|
| assign-based restore vs the 1-world truth (frames 8, 12, 16, 24) | bit-identical |
| world 0 while the other worlds run random actions | bit-identical |
| in-process planner (the CUDA code path, `--workers 0`) vs the 2-process worker path, same seed | identical offsets, decisions and truth trajectory |
| in-process truth vs official `trace_rollout.py zero` replay of its output | max \|Δq\| 0.0 |
| `--deadline_s 25` | stops optimising at t=16 and still writes a complete, bit-identical reference |
| `jitter_check.py` after the port | reproduces 0.5594 for v1 |
| `ops/jobs/physics_solve.sh` dry run (ep12, `/content` replaced by a scratch root, store stubbed, CPU) | completes; writes `summary.json` |
| the same dry run with a missing input episode | falls back as designed and skips the episode |

**Inputs.**
- Episodes ep2, ep12, ep18, ep24.
- References: the stored S1 grasp-lock + ILC + EVOLVE references, store run `20261030-physS1-6a814df`
  `refs/glockt/ep<N>`. Their zero action on the S1 box was 0.601 / 0.604 / 0.542 / 0.194.
  - Fallback 1: the S0 run's references (`20261030-physS0-6a814df`).
  - Fallback 2: rebuilt on the box (grasp lock + ILC, no EVOLVE).
  - The input actually used for each episode is logged in `summary.json`.
- Objects: NVIDIA's public scans with the S1 plausible masses (`make_assets --physics props_public_scans.json`, as in
  `physics_arms.sh`).
- The baseline and the solver use the **same input file and assets**.

**Settings** (the job defaults):
- `solve.py --device cuda --worlds 1024 --robust 4 --horizon 20 --knot 4 --ctrl 4 --iters 4 --ramp 1 4 --sig_pos 0.01
  --sig_rot 0.05 --sig_fin 0.15 --anneal 0.6 --retries 6 --retry 0.05 --back 3 --rob_pos 0.0005 --rob_fin 0.005
  --seed 0`. That is 256 candidates × 4 robust copies, 1 s horizon, 0.2 s commits, 4 iterations, and at most 6
  rollbacks back 0.6 s each. The truth env is on the same GPU.
- `--deadline_s` = 4 s × episode frames: ep2 1,372 s, ep12 724 s, ep18 1,412 s, ep24 1,100 s.
- Jitter check: `jitter_check.py --device cuda --k 64 --seed 0`. That is copy 0 plus 63 copies with N(0, 0.5 mm) wrist
  position and N(0, 0.005 rad) finger target noise on every frame. Both references of an episode get the same noise
  draws.

**Reading** (primary; decides the next step):
- Δ_e = mean over the 63 jittered copies (solved reference) − the same mean for the grasp lock + ILC input.
- **PASS iff Δ_e ≥ +0.03 on at least 2 of the 4 episodes.** An episode with no result (input missing, solve failed)
  counts as not beating the baseline.
- Reported but not part of PASS: a **harm flag** for any Δ_e ≤ −0.05.
- PASS → propose G2 (Do as I Do scale on the episodes that gained, ≤ ~$8) and G3 (RL from the solved references),
  each with its own go-ahead.
- No PASS → no further GPU spend on this solver as it stands. The write-up then records [H-scale] as falsified at G1
  scale.

**Secondary readouts** (no decision attached):
- the nominal zero-action sim_vs_ref of both references (copy 0, and `trace_rollout.py zero` + `trace_score.py`);
- the solver's own truth trajectory vs the official replay. GPU MuJoCo-Warp may not be bit-deterministic, so this
  measures it;
- solve wall time, whether the deadline was reached, the rollbacks used, and the per-copy score distributions;
- afterwards on CPU here ($0): `jitter_check.py --k 9` of the solved parquets, to see device sensitivity.

**Expected time and cost** [E]:
- Four episodes run concurrently on one RTX PRO 6000. Estimate ~0.1 s per frame at 1,024 worlds with 4 processes
  sharing the GPU, so ~2–3 s per committed frame. ep18 (353 frames) then takes ~15 min, and the deadlines cap each
  episode at 12–24 min.
- Job ~25–35 min: assets + pulls ~3 min, CUDA kernel compile ~3–5 min, solves ≤ 24 min, replays + jitter ~3 min,
  push ~2 min.
- Box setup ~10–20 min. Total ~40–55 min ≈ **$0.8–1.4** at $1.2–1.5/h. The deadline bounds the solve whatever the
  throughput.

### 5.2 G2 + G3 pre-registration (written 30 Oct 2026 ~18:40 UTC, before any G2 or G3 result)

G1 passed (§5.1; `gpu/psolve_G1_summary.json`). Jittered Δ vs GL+ILC: ep2 +0.080, ep12 +0.063, ep18 −0.004,
ep24 +0.005. The owner approved G2 and G3 together (cap ≈ $14.5). Both run in one box job,
`ops/jobs/physics_solve_rl.sh`: G2 first, then G3. They are not overlapped: two 4,096-world solvers (~8 GB each [E],
from ~1.9 MB per world measured on CPU) plus two FlashSAC trainings (40 GB each) would crowd the 96 GB card, and
training would take GPU time from G2. Nothing below is changed after a result.

**Code** (working tree on `a434363`; the coordinator commits it):
- `tools/physics_solve/solve.py` md5 `be1dabb1`. New since G1:
  - `--early_rel/--early_n/--min_iters`: Do as I Do's early stop. Stop a replan's iterations once the best sample beats
    sample 0 by less than 2 % of J0 in 2 consecutive iterations, after at least 6 iterations;
  - `--pace_s`: behind schedule, a replan runs only `min_iters` iterations and no boosted iterations;
  - knot interpolation as one matrix product (equal to the old loop to 4e-16).
- `jitter_check.py` `3522b860` (unchanged since G1).
- `ops/jobs/physics_solve_rl.sh` `179ac592`.
- `ops/jobs/glock_public.sh` `a2733085`, unchanged and used as is.

CPU checks [M]:
- early stop fired as designed (3–5 iterations of 8);
- pacing cut replans to `min_iters`;
- truth vs official replay 0.0 after rollbacks;
- dry run of the whole job in a scratch root with a fake store and a stub `glock_public.sh`:
  - G2 ran;
  - the G3 reference choice worked;
  - each G3 task directory held exactly one parquet, plus `rest_check.json` and the support stage;
  - the stub received exactly round 1's recipe environment;
  - the summary verdicts evaluated.

**G2 (episodes ep2, ep12; run concurrently).**
- Input: the same S1 GL+ILC(+EVOLVE) references as G1. Fallbacks as in G1.
- Settings: `--worlds 4096 --robust 4 --horizon 60 --knot 4 --ctrl 10 --iters 32 --ramp 1 4 --sig_pos 0.01 --sig_rot
  0.05 --sig_fin 0.15 --anneal 0.9518 --retries 3 --retry 0.05 --back 1 --rob_pos 0.0005 --rob_fin 0.005 --early_rel
  0.02 --early_n 2 --min_iters 6 --seed 0`. That is:
  - 1,024 candidates × 4 robust copies;
  - 3 s horizon, 0.2 s knots, 0.5 s commits;
  - up to 32 iterations. The annealing is rescaled so that iteration 32 has G1's final noise factor (0.6³ = 0.216 =
    0.9518³¹);
  - at most 3 rollbacks of one commit (0.5 s) each.
- Pace 14.4 s per committed frame; hard deadline 18 s × frames (ep2 6,174 s = 1.7 h; ep12 3,258 s).
- Jitter checks on this box: 64 copies, seed 0, the same noise draws for each of the GL+ILC input, G1's solved
  reference (store run `20261030-psolve-eecd18a`) and G2's output.
- **G2 reading** (primary): Δ_scale,e = jittered mean(G2) − jittered mean(G1), both measured on this box.
  - **scale helps** iff the mean of Δ_scale over ep2 and ep12 is ≥ +0.03 and neither is ≤ −0.05;
  - **scale hurts** iff the mean is ≤ −0.03 or either is ≤ −0.10;
  - otherwise **no scale effect**;
  - an episode without a G2 output is left out and flagged.
- Secondary (reported only): G2 − GL+ILC per episode, i.e. whether G2 keeps G1's +0.03 bar; nominal replays; solve
  wall time, deadline, pacing, mean iterations and rollbacks.

**G3 (RL, all four episodes, seed 42).** The frozen round-1 recipe through `glock_public.sh` with `REUSE_REF=1`:
- settings as `physics_arms.sh ARM=S1`: `LIB=/content/scanlib`, S1 props, `SF=0`, FDR + VOC fix, 70M steps,
  `CURVE_REP 3`, `NREP 5`, the same PAIRS base runs;
- the scoring is round 1's: the checkpoint is chosen by sim_vs_ref only; NREP official evaluations scored by
  sim_vs_ref and by registered AUC vs mocap (evaluation only).

References (no ground truth in the choice):
- **ep2, ep12:** G2's output if its jittered mean ≥ G1's on this box, else G1's (`G3_PICK=best`). `G3_PICK=g2` uses
  G2's output whenever it exists (the coordinator's literal wording; it is not the default because it would train on a
  reference our own metric ranks lower).
- **ep18, ep24:** G1's output.
- Each reference is placed as the only parquet in `refs/glockt/ep<N>/<hive>/`. Its `rest_check.json` comes from its own
  zero-action replay on the box.
- `robot_<side>_frames`, the RL hand-tracking target, stay the **intended** hand: the solver edits only the wrist and
  finger targets (the `wrist_ilc.py` convention). Decided, 30 Oct.

Readings:
- **[H-RL] (learning speed):** the curve's sim_vs_ref at the 30M checkpoint (3 official evaluations) vs round-1 S1
  seed 42 at 30M (ep2 0.483, ep12 0.549, ep18 0.529, ep24 0.112).
  - **Supported** iff ≥ +0.03 on ≥ 2 of 4 episodes; otherwise **falsified**. No 30M result counts as not.
  - The comparison is fair: the solved references keep the input's object trajectory, so sim_vs_ref is against the
    same object reference.
- **Final** (registered AUC vs mocap, NREP 5, the checkpoint chosen by sim_vs_ref) vs round-1 S1 seed 42 (ep2 0.736,
  ep12 0.885, ep18 0.625, ep24 0.232):
  - **signal** iff mean Δ ≥ +0.03 and no episode ≤ −0.05;
  - **harm** iff mean Δ ≤ −0.03 or any ≤ −0.10;
  - otherwise **inconclusive**.
  - One seed: a signal buys a second seed, not adoption.
- Reported only: ep2 against round 2's S1 seeds 43 / 44 (0.979 / 0.980; same recipe, reference rebuilt on that box),
  which bound seed noise on ep2.

**Expected time and cost** [E]:

| stage | time |
|---|---|
| setup | ~15 min |
| prep (assets, pulls, CUDA kernel compile, 4 jitter checks) | ~10 min |
| **G2** | ≤ 1.7 h by construction (deadline); expected ~1.2–1.7 h. In G1, 4 processes at 1,024 worlds ran ~0.13 s per planner frame each; at 4,096 worlds × 2 processes the pace allows ~10 iterations per replan on average |
| G3 references | ~7 min |
| **G3** | ~2–2.3 h (round 1: about 1 h per pair of episodes for training, curves and NREP evaluations, two at a time) |
| **total box** | **~3.7–4.5 h ≈ $4.5–6.8** at $1.2–1.5/h, within the ≈ $14.5 cap |

Not recommended: running Do as I Do or SPIDER themselves.
- They plan in a different contact model (condim 6, finger kp 300) and their data model allows one object per hand.
- SPIDER's code is non-commercial.
- Their output would still need this FlashCHORD-native pass or RL to work in the scored simulator.

## 6. Hypotheses and what would falsify them

- [H-robust] (v3, CPU): with 4 robust copies per candidate, the solver's gain survives 0.5 mm / 0.005 rad noise.
  Falsified if the v3 jittered mean is < 0.586. Pre-registered in `phys/solve/ep12_v3/prereg.txt` before the run.
  Result: **falsified at the CPU budget** (0.564 ± 0.039). It remains open at GPU scale (G1).
- [H-scale]: the search budget, not the method, limits the carry (v1 found no sample in 64 that kept the cup at f57).
  Test: G1 on ep12. Falsified if the cup is still lost before f70 in most jittered copies at G1 scale.
- [H-gpu] and [H-RL]: §5.

### 6.1 Option 3: solver and RL taking turns, plus the option-1 control (pre-registered 31 Oct 2026 ~05:30 UTC, before any GPU result)

**Why.**
- G2 found plans that hold in the scored physics (jittered 0.763 / 0.832 vs 0.524 / 0.578).
- G3's RL from those plans was far ahead at 30M (0.965 / 0.761 / 0.523 / 0.191 vs 0.483 / 0.549 / 0.529 / 0.112), but
  the final AUC vs mocap was no better (0.584 / 0.892 / 0.622 / 0.244 vs 0.736 / 0.885 / 0.625 / 0.232). ep2 collapsed
  after 30M, as round-1 seed 42 also did.
- Two things are missing:
  - **keeping** the head start, which needs checkpoint choice and the curriculum length (option 1);
  - **teaching** the policy where it fails, from its own states (option 3: cf. Guided Policy Search, Levine & Koltun
    2013; DAgger, Ross et al. 2011; PHC fail-state recovery, Luo et al. 2023).
- FlashCHORD's rules hold: the scored run is the learned policy in the unchanged evaluator, and every change is on the
  training side.

**Design (per episode; `ops/jobs/physics_rl_loop.sh`).**
1. **Where RL fails.**
   - The newest checkpoint is played like the evaluator: frame 0, VOC 0, no termination, deterministic policy.
     The tool is `tools/trace_rollout.py policy` with `STATE=1`, which now also stores the full simulator state per
     frame: joint_q/qd, body_qd, MuJoCo warm start.
   - `tools/physics_solve/failures.py` marks the first frame at which an object stays more than 3 cm ADD off our
     reference for at least 8 frames, while the reference moves it or a hand is near it.
   - A solver window then runs from 0.5 s before that frame to 3 s after it. At most 2 windows are kept, the earliest
     failure first; overlapping windows are merged.
2. **Solver from those states.**
   - `solve.py --start_state <trace> --t0 <window start> --stop <window end> --record`: the truth env is restored to
     the **policy's own state**, and planning continues from there on the current training reference.
   - Settings: 1,024 worlds = 256 candidates × 4 robust copies, 2 s horizon, 0.4 s commits, ≤ 16 iterations with
     early stop, annealing to G1's final noise (0.903¹⁵ ≈ 0.216), ≤ 2 rollbacks, 15 min deadline per window.
   - It records its own states and contacts.
3. **Into training** (`tools/physics_solve/merge_ref.py`):
   - (a) **reference segment:** the solver's wrist and finger targets replace the reference's inside the window and
     return to it over 6 frames afterwards. `robot_<side>_frames` (the hand-tracking target) and the object reference
     stay unchanged;
   - (b) **contact targets:** inside the window, the solver's simulated contacts (`tools/sim_contacts.py`);
   - (c) **reset-state bank:** the policy's states from the window start to its failure, and the solver's states along
     the window where every object is within 3 cm (every 5 frames). The bank accumulates over rounds.
   - Training draws 25 % of its resets from the bank through **`ops/box/patch_flashchord_states.py`**, a training-only
     FlashCHORD patch kept as a separate file like `patch_flashchord_drop.py`.
     - It is inert unless `FC_STATE_RESET` is set, and it adds no config field.
     - What it edits in `lifecycle/reset.py`:
       - `reset_kernel` loads a banked joint_q / joint_qd, adding the world's object offsets;
       - `sample_reference_reset` draws from the bank, with no extra random draws while no bank is loaded;
       - a bank reset sets the reference timestep to the banked frame, keeps the fingers as stored and skips the
         settling hold;
       - `prepare_explicit_reset` clears the flag, so every explicit evaluation reset is untouched;
       - the bank is allocated in `ReferenceResetTable.build`, before graph capture.
4. **Rounds:** one FlashSAC run with seed 42, `CURR_SCALE 0.4`, the FDR rewards + VOC fix and S1 masses.
   - Round A runs 0 → 30M on the solved reference R0.
   - Diagnose → R1 + bank; round B **resumes** the same run (actor, critic, optimiser; the replay buffer refills)
     30M → 50M on R1 with the bank.
   - Diagnose → R2 + bank; round C runs 50M → 70M.
   - FlashCHORD's resume checks only the object articulation contract, so a merged parquet of the same episode is
     accepted (code read: `checkpoint_metadata.validate_resume_reference_config`).
5. **Keeping the head start:** as in rounds 1–3, every checkpoint from 10M to 70M is scored by 3 official evaluations
   (sim_vs_ref against our reference, whose object trajectory is the same in every round). The best gets 5 evaluations
   with registered AUC vs mocap, so a 30M peak is kept even if later rounds lose it.

**Option-1 control (O1)**, on the same box:
- `glock_public.sh` with REUSE_REF on the same solved references and the same frozen recipe, seed 42;
- plus early stopping: `ES=1`, target 0.9, patience 20M, from 20M;
- plus `CURR_SCALE 0.4`: assist 0 from 49M instead of 123M;
- O1 and O3 share the two GPU training slots.

**CPU evidence** (this container; FlashCHORD at the evaluator pin; JAX CPU installed in the scratchpad venv for the
policy path) [M]:

| check | result |
|---|---|
| `trace_rollout.py policy` with `STATE=1` on a stored ep12 checkpoint (CPU: Warp graph capture is skipped on the CPU, eager step) | 182 records with state |
| `failures.py` on the GL+ILC zero-action trace | cup onset f38 (earlier diagnostics: f37/38) |
| `failures.py` on the CPU test policy | cup onset f35, window 25–95 |
| solve from the zero-action trace's state at f28 → f48: the official replay of the output from frame 0 vs the solver's committed trajectory | max \|Δq\| **0.0** |
| same: frames before f28 vs the input's replay | 0.0 |
| same: offsets confined to the window | yes |
| `merge_ref.py` | targets change only in the window + 6 blend frames; window = segment; contact targets replaced on in-window frames; FlashCHORD loads the result (joint-limit validation passes) |
| bank filter | keeps only the solver states that hold |
| state patch on a patched copy: inert (no bank) | sampled resets identical to the original package (frames, finger scales, joint states) |
| state patch, bank share 1.0 | every world loads its banked state bit-exactly, at the banked frame, no hold |
| state patch, share 0.5 | a mix of bank and reference resets |
| state patch, explicit resets | always the reference; flag cleared |
| `physics_rl_loop.sh` dry run in a scratch root (store, training, evaluations and `glock_public.sh` stubbed; real CPU policy rollouts, failure finder, start-state solves, merges, patch) | three rounds with resume and bank (18 → 36 states), one parquet per task dir, O1 got the intended settings, summary verdicts evaluated |

Not testable on CPU: FlashSAC training (its graph capture crashes on the CPU), hence resuming on a merged reference and
the bank under graph capture (allocated before capture, like the drop patch's arrays).

**Code** (HEAD `1b5a1d4` plus the uncommitted `merge_ref.py` bank filter):

| file | md5 |
|---|---|
| `solve.py` | `fa511432` |
| `failures.py` | `8fb670c9` |
| `merge_ref.py` | `82635b68` |
| `trace_rollout.py` | `c35f053e` |
| `patch_flashchord_states.py` | `ecb4ef52` |
| `physics_rl_loop.sh` | `078d2550` |
| `glock_public.sh` | `a2733085` (unchanged) |

**Readings** (registered AUC vs mocap of the checkpoint chosen by sim_vs_ref, 5 evaluations; one seed):
- **Primary, O3 − O1** (the loop's own value):
  - **signal** iff the mean over the 4 episodes is ≥ +0.03 and no episode is ≤ −0.05;
  - **harm** iff the mean is ≤ −0.03 or any episode is ≤ −0.10;
  - otherwise **inconclusive**;
  - an episode without a result is left out and flagged.
- **Secondary, same rule:**
  - O1 − G3: does early stopping plus a shorter curriculum keep the head start?
  - O3 − G3.
- Reported only: O3 vs round-1 S1 seed 42 (0.736 / 0.885 / 0.625 / 0.232) and vs round 3's realistic-mass seed means.
- **[H-teach] (mechanism):** the final O3 policy's first failure frame is later than after round A on ≥ 2 of 4
  episodes; otherwise not supported.
- Also reported: windows per round, solver results per window, bank sizes, and the policy-rollout sim_vs_ref per round.
- One seed, and ep2 seed 42 collapsed twice: a signal buys more seeds, not adoption.

**Expected time and cost** [E]:
- Training: 8 runs of ≤ 70M (O1 may stop early) in 2 slots at ~55–60k env steps/s in total, ≈ 2.7–3.3 h.
- O3 diagnosis + solves: ~10–30 min per round per episode, overlapped by the other runs' training.
- About 300 one-world official evaluations, mostly overlapped with training.
- Setup + references ~25 min; tail ~30 min.
- **Total ≈ 4–5 h ≈ $5.5–7.5** at $1.3–1.5/h; worst case ~5.5 h ≈ $8.3, within the ~$10 cap.


### 6.1 Results (run `20261031-rlloop-ccf9058`, code ccf9058, 31 Oct 05:18–10:02 UTC, ≈ $6.48 [E]) [M]
Summary: `gpu/rlloop_summary.json`. Registered AUC vs mocap of the chosen checkpoint, 5 evaluations, mean ± sd:

| episode | O3 (loop) | its checkpoint | O1 (control) | its checkpoint | O3 − O1 | G3 |
|---|---|---|---|---|---|---|
| ep2 | 0.835 ± 0.189 | 20M (round A) | 0.585 ± 0.237 | 10M | +0.251 | 0.584 |
| ep12 | 0.904 ± 0.036 | 50M (end of round B) | 0.893 ± 0.026 | 40M (ES at 50M) | +0.011 | 0.892 |
| ep18 | 0.620 ± 0.007 | 10M (round A) | 0.579 ± 0.095 | 40M (ES at 60M) | +0.041 | 0.622 |
| ep24 | 0.224 ± 0.004 | 20M (round A) | 0.254 ± 0.037 | 50M | −0.030 | 0.244 |

Pre-registered readings: **primary O3 − O1 = +0.068 → "signal"** (no episode ≤ −0.05); O1 − G3 −0.008 inconclusive;
O3 − G3 +0.060 signal; O3 vs round-1 S1 +0.026 (report only); H-teach "supported" (first failure later on 3 of 4: ep12
f124 → none, ep18 f20 → f40, ep24 f16 → f19; ep2 f62 → f61).

O3 sim_vs_ref per checkpoint (3 evaluations; rounds: A = 10–30M on R0, B = 40–50M on R1, C = 60–70M on R2):
ep2 0.944 0.966 0.488 | 0.473 0.498 | 0.422 0.493; ep12 0.723 0.756 0.888 | 0.946 0.949 | 0.941 0.938;
ep18 0.587 0.436 0.339 | 0.490 0.400 | 0.378 0.418; ep24 0.199 0.229 0.168 | 0.193 0.162 | 0.149 0.214.
Loop mechanics on the GPU: resume worked (round B starts at 30,003,200 steps), the reset-state bank loaded (ep2 round B:
4 states, share 0.25), one window per round per episode, solves + merges 5–8 min each.

**Reading (post-hoc, labelled as such): the "signal" is not the loop's.**
1. 3 of 4 chosen O3 checkpoints come from round A, before any solver feedback. Only ep12 chose a post-loop checkpoint
   (+0.011 over O1, within the 0.03 bar).
2. **Confound found after the run (design flaw):** FlashSAC's learning rate follows a cosine 3e-4 → 1.5e-4 over the run's
   own `total_environment_steps` (`reference_flash_sac.yaml` `learning_rate_schedule_updates: null` → total optimiser
   updates, `training/flash_sac/config.py` `learning_rate_schedule_updates`, `update.py` cosine). Round A was a 30M run, O1 a 70M run, so at
   10M / 20M / 30M round A's LR was ≈ 2.63e-4 / 1.88e-4 / 1.5e-4 against O1's ≈ 2.93e-4 / 2.72e-4 / 2.42e-4.
   If the resumed schedule step is kept, each resume also re-stretches the schedule (LR back up to ≈ 2.0e-4 at the
   start of round B). So round A is not "the control's first 30M"; the ep2 gap
   (sim_vs_ref 0.944 vs 0.729 at 10M) may be this schedule, or ep2's usual run-to-run chaos (one seed).
3. After the loop rounds, O3 never beat its own round-A best on ep2, ep18 or ep24 (ep2 stays 0.42–0.50 after the 30M
   collapse; ep18 0.38–0.49 vs 0.587 at 10M). ep12 rose 0.888 → 0.946–0.949, but O1 reached 0.918 by 40M as well.
4. The bank was tiny (4 states on ep2) and each round gave one window, so the loop acted weakly. The solver changed
   0 frames in 4 of 8 turns (ep2 after 30M, ep18 both, ep24 after 30M; edited frames 0/47, 67/40, 0/0, 0/72 for
   ep2/12/18/24): from the policy's already-slipping state its best plan scored no better than the incumbent
   (J_best ≈ J_warm), so it early-stopped at the 6-iteration minimum (seg_solve.json mean_iters 6.0–6.7, 2 rollbacks).
Verdict for the record: rule "signal" (more seeds, not adoption); interpretation: **no evidence that the loop helps**;
new hypothesis **[H-lr]: a shorter LR horizon (LR reaching 1.5e-4 by ~30M) keeps the early peak** — falsified if O1 with
`training.optimization.learning_rate_schedule_updates` set to the 30M-run value does not beat O1 on ep2 over ≥ 3 seeds.
Not run; needs the owner's go-ahead.

## 7. Commands (exact)

From the FlashCHORD dir (`scratchpad/src/video_to_data/robotic_grounding/flash_chord`), with
`EMB=sharpa_hands_mid OMP_NUM_THREADS=1` and the scratchpad `fcvenv/bin/python`:

```bash
# clones
GIT_LFS_SKIP_SMUDGE=1 git clone https://github.com/malik-group/do-as-i-do.git    # 824591b
GIT_LFS_SKIP_SMUDGE=1 git clone https://github.com/facebookresearch/spider.git   # 4471700
# one run = solve + official zero-action replay + sim_vs_ref (scratchpad phys/solve/run_solve.sh, reproduced here)
python tools/physics_solve/solve.py REF_IN.parquet REF_PS.parquet <args>
DEV=cpu python tools/trace_rollout.py zero zero_ps.npz REF_PS.parquet 181
KIT=scratchpad/dl/kit/x/v2d_submission_kit scratchpad/venv/bin/python tools/trace_score.py REF_PS.parquet zero_ps.npz:zero_ps REF_PS_solve.npz:truth
KIT=... python tools/physics_solve/jitter_check.py REF.parquet --k 9                                          # 0.5 mm / 0.005 rad, seed 0
KIT=... python tools/physics_solve/jitter_check.py REF.parquet --k 9 --sig_pos 1e-5 --sig_fin 1e-4 --seed 1     # float-level
# v1
solve.py ... --workers 4 --worlds 16 --horizon 16 --knot 4 --ctrl 4 --iters 4 --ramp 1 4 --sig_pos 0.01 --sig_rot 0.05 --sig_fin 0.15 --anneal 0.6
# v2 (stopped after t=40)
solve.py ... v1 args with --horizon 20 --retries 6 --retry 0.05 --back 3
# Option 3 loop + option-1 control on one GPU box (pre-registered in section 6.1)
ops/vast.sh V2D_COMMIT=<sha> ENV_SNAPSHOT=pt2.11-cu130-py313-20261020 create <offer> <run> 'bash ops/jobs/physics_rl_loop.sh'
# G2 + G3 on one GPU box (pre-registered in section 5.2)
ops/vast.sh V2D_COMMIT=<sha> ENV_SNAPSHOT=pt2.11-cu130-py313-20261020 create <offer> <run> 'bash ops/jobs/physics_solve_rl.sh'
# G1 on a GPU box (pre-registered in section 5.1; the coordinator launches it)
ops/vast.sh V2D_COMMIT=<commit with 09e59d2's job> ENV_SNAPSHOT=pt2.11-cu130-py313-20261020 create <offer> <run> 'bash ops/jobs/physics_solve.sh'
# v3
solve.py ... --workers 4 --worlds 24 --robust 4 --horizon 16 --knot 4 --ctrl 4 --iters 4 --ramp 1 4 --sig_pos 0.01 --sig_rot 0.05 --sig_fin 0.15 --anneal 0.6 --retries 4 --retry 0.05 --back 3
```

The code versions are in each `run.log` (repo HEAD + `solve.py` md5): v1 `ce3ff4e`+wip md5 `b83827cb`; v2 `d42ae60`+wip
`d9b19f99`; v3 `d42ae60`+wip `daefc58e`; after the clip fix `c41881ae`, and `ad6a7525` with only the docstring updated (the version in the repo now). The runner is `tools/physics_solve/run_solve.sh` (needs `S=` the scratchpad). The diagnostic scripts used are in the scratchpad `ps/`: `bench.py`, `det_test.py`,
`couple_test.py`, `exact_*.py`, `objdiag.py`.

## G1 result (box `20261030-psolve-eecd18a`, commit eecd18a, 30 Oct 17:20–18:10 UTC, ≈ $1.29) [M]
Jittered sim_vs_ref (64 copies, 0.5 mm / 0.005 rad target noise, common random numbers), our reference, no ground truth:
| episode | grasp lock + ILC | solved | Δ | solve wall / deadline / rollbacks |
|---|---|---|---|---|
| ep2 | 0.528 ± 0.081 | 0.608 ± 0.095 | **+0.080** | 1294 s / none / 4 |
| ep12 | 0.581 ± 0.021 | 0.643 ± 0.087 | **+0.063** | 757 s / hit at f152 / 4 |
| ep18 | 0.553 ± 0.042 | 0.549 ± 0.047 | −0.004 | 1418 s / hit at f288 / 6 |
| ep24 | 0.188 ± 0.017 | 0.193 ± 0.014 | +0.005 | 1113 s / hit at f92 / 6 |
2 of 4 episodes ≥ +0.03 → **PASS** by the pre-registered rule (§5.1); no harm flag. On CUDA a fresh zero-action replay
does not reproduce the solver's own trajectory (ep2 truth 0.948 vs replay 0.558; ep12 0.889 vs 0.848): chaos plus
GPU non-determinism, which is why the jittered means are the measure. Summary: `gpu/psolve_G1_summary.json`.
By §5.1, PASS means proposing G2 (full Do as I Do scale, ≈ $8) and RL from the solved references (≈ $6.5), each with the
owner's go-ahead.

## G2 + G3 results (box `20261030-psolverl-04301a2`, commit 04301a2, 18:40–23:05 UTC, ≈ $6.48) [M]
**G2** (jittered sim_vs_ref, 64 copies): ep2 GL+ILC 0.524 / G1 0.600 / **G2 0.763**; ep12 0.578 / 0.656 / **0.832**.
G2 − G1 mean +0.170 → **"scale helps"**; G2 − GL+ILC +0.239 / +0.254. Solve wall 3,952 s (ep2) and 2,471 s (ep12) run
together on one GPU (≈ 7.6 s of box time per frame), no deadline hit; mean iterations 7.0 / 10.8 (early stop).
**G3** (frozen S1 recipe from the solved references: G2 for ep2/ep12, G1 for ep18/ep24; seed 42; AUC vs mocap, 5 evals):
| episode | round 1 (GL+ILC) | G3 (solved) | Δ | sim_vs_ref at 30M: round 1 → G3 |
|---|---|---|---|---|
| ep2 | 0.736 | 0.584 ± 0.339 (30M ckpt) | −0.152 | 0.483 → **0.965** |
| ep12 | 0.885 | 0.892 ± 0.037 (60M) | +0.007 | 0.549 → **0.761** |
| ep18 | 0.625 | 0.622 ± 0.004 (20M) | −0.003 | 0.529 → 0.523 |
| ep24 | 0.232 | 0.244 ± 0.025 (10M) | +0.012 | 0.112 → **0.191** |
- **[H-RL] not falsified:** at 30M the solved-reference runs are ≥ 0.03 higher on 3 of 4 → RL learns much faster.
- **Final readout: harm** by the pre-registered rule (mean −0.034; ep2 −0.152 ≤ −0.10). ep2 collapsed after 30M (curve
  0.884 / 0.610 / 0.965 / 0.495 / 0.478 / 0.469 / 0.474; pot no longer lifted), the same pattern as round-1 S1 seed 42;
  its chosen 30M policy is unstable (5 evals 0.197–0.968). Round-2 seeds 43/44 on the GL+ILC reference reached 0.979.
- Reading [H]: the solved plan gives RL a large head start that the frozen schedule (assist decay to 0 by 123M of the
  scaled curriculum, mixed resets) does not preserve. Testable: early stopping / shorter curriculum from the solved
  reference, and seeds 43/44 on ep2 (seed 42 collapsed in both reference types).
