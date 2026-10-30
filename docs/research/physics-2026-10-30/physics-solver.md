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

## 5. GPU plan (not started; needs the owner's go-ahead) [E]

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
# v3
solve.py ... --workers 4 --worlds 24 --robust 4 --horizon 16 --knot 4 --ctrl 4 --iters 4 --ramp 1 4 --sig_pos 0.01 --sig_rot 0.05 --sig_fin 0.15 --anneal 0.6 --retries 4 --retry 0.05 --back 3
```

The code versions are in each `run.log` (repo HEAD + `solve.py` md5): v1 `ce3ff4e`+wip md5 `b83827cb`; v2 `d42ae60`+wip
`d9b19f99`; v3 `d42ae60`+wip `daefc58e`; after the clip fix `c41881ae`, and `ad6a7525` with only the docstring updated (the version in the repo now). The runner is `tools/physics_solve/run_solve.sh` (needs `S=` the scratchpad). The diagnostic scripts used are in the scratchpad `ps/`: `bench.py`, `det_test.py`,
`couple_test.py`, `exact_*.py`, `objdiag.py`.
