# Porting recipes for FlashCHORD from seven dexterous-retargeting papers

Research date: 2026-10-21. Read-only research; no repository file was changed.

Labels:
- **[F]** fact from a primary source. Each one cites a paper section or table, or a code file in the authors' repository at the commit cloned today.
- **[I]** my inference or hypothesis. Where possible it names the experiment that would falsify it.
- **[E]** an estimate (cost, time).

"FlashCHORD (ours)" means NVIDIA `video_to_data/robotic_grounding/flash_chord` as dissected in
`docs/research/notes/01-baseline-dissection.md`. I re-checked the key items in the scratchpad source copy
(`src/video_to_data/robotic_grounding/flash_chord`).

---

## 0. What I could and could not open

| Source | Result |
|---|---|
| arXiv HTML for all 7 papers (`arxiv.org/html/<id>`) | Opened. FlashDexRetarget is v2 (04 Oct 2026). Text converted with math alttext kept. |
| `github.com/Holiday-Robot/FlashDexRetarget` | **Full shallow clone** (`git clone` through the proxy works). Configs, rewards, terminations, curriculum, actions, reset and retargeting code were all read. |
| `github.com/malik-group/do-as-i-do` | **Full clone**. Retargeting configs, reward, warmup and transition code, and the sampler were read. |
| `github.com/facebookresearch/spider` | **Full clone** (LFS skipped). Contact-guidance schedule, contact detection and noise schedule were read. |
| `github.com/DexGEM-Lab/real2sim2real` (contact-anchored) | Cloned, but it contains **only a README and GIFs: "Code release coming soon."** No weights or code. |
| Gen2Dex (2610.24392), Morphometric Imitation (2609.28660) | **No code link in the paper.** Morphometric's reward α, termination thresholds and PPO settings sit in a separate supplement that is **not in the HTML**; not read. |
| CHORD (2607.00033) | Paper only (the project page link). For code I used our local FlashCHORD copy, plus FDR's `src/envs/rewards/chord.py`, which states it ports CHORD's wrench maths "1:1 from robotic_grounding". |
| `api.github.com`, `codeload.github.com`, `gh api` | 403, or "repository not enabled for this session". `raw.githubusercontent.com` and `git clone` both work. |

Clones are in `scratchpad/code/{fdr,daid,spider,dexgem}`; paper texts are in `scratchpad/papers/*.txt`.

---

## 1. Baseline: what CHORD specifies and what FlashCHORD actually runs

### 1.1 CHORD paper (2607.00033)

- **Reward [F §3.1]:** `r = r_task + r_imit + r_contact`, with the VOC (DexMachina's virtual object controller).
- **Task reward [F §3.1]:** `r_task = exp(-Σ_k ||x_obj,k ⊖ s_obj,k||² / var_obj) + r_relative`.
- **Relative reward [F App. B]:** `r_relative = m(t) · exp(-(e_p · e_R) / var_rel)`.
  - `e_p` and `e_R` are the inter-object translation error and geodesic rotation error.
  - `m(t)` gates the term on the **demonstration's** inter-object distance; the paper calls this the object-object interaction phase.
  - [I] As printed, the exponent multiplies the two errors, so a perfect match on either one zeroes it. The paper says the form is meant to be "multiplicative" over the two errors; a safer port is `exp(-e_p/σ_p)·exp(-e_R/σ_R)`.
- **Imitation reward [F §3.1]:** `r_imit = exp(-||x_robot - s_robot||² / var_imit)`.
- **Contact wrench support [F §3.1 Eq. 1–3]:**
  - Each contact `i` comes from the human demo in the object frame, with friction-cone edge forces `f_j` (d edges).
  - Primitive wrench: `w = [f_j, p_i × f_j]`.
  - Support function over b unit directions `B`: `σ = max_col(Bᵀ W)`.
  - Reward: `r_cws = exp(-(||max(0,(1-β)σ_h - σ_r)||² + ||max(0, σ_r-(1+β)σ_h)||²)/v_cws)`.
  - Unintended contacts (σ_h = 0 but σ_r > 0) and missed contacts (σ_h > 0 but σ_r = 0) are penalised.
- **Reduced objective for noisy contacts [F §3.2]:** `r_fc = (1/B) Σ_b 1[σ_r,b > ε]`, which is "equivalent to force closure" when maximised.
- **Action [F App. B]:**
  - Residual wrist position, scale 0.05 m.
  - Wrist orientation, 0.15 rad.
  - Fingers, 0.15 rad.
  - EMA 0.3.
  - The wrist runs on a force/torque tracking controller.
- **Reset [F App. B]:**
  - Random frame along the reference.
  - Fingers set to `partially open` with an interpolation factor drawn from U[0, 0.7].
  - VOC scale 1.0 for a 20-step warm-up, then the curriculum value.
  - [F §3.2] Perturbation wrenches are sampled from the human contact-wrench matrix.
- **Termination [F App. B]:**
  - Wrist deviation.
  - Object deviation.
  - Time-out at the end of the reference.
  - Success in the paper: no object termination at 15 cm / 40°, with a completion ratio above 0.7 [F §4.1].
- **Training [F App. B]:**
  - FlashSAC, 2,048 environments, about 2 h per sequence on one L40S.
  - [F §4.1] "Stable training requires the contact wrench reward to converge before decaying the VOC."
- **Evidence [F Table 1, 60 tasks × 3 seeds]:**

  | Method | AUC | SP-SR | MP-SR | RPE | MPPE |
  |---|---|---|---|---|---|
  | CHORD | 0.918 | 0.926 | 0.894 | 5.14 cm | 5.11 cm |
  | SPIDER | 0.804 | 0.911 | 0.789 | — | — |
  | DexMachina | 0.737 | — | — | — | — |
  | ManipTrans | 0.506 | — | — | — | — |

  Ablation [F Table 2]: wrench reward AUC 0.918, position-only contact reward 0.862, no contact reward 0.774. These are clean mocap references.
- **Noise ablation [F App. A.1, Fig. 9]:** noisy contacts degrade performance. At very high noise, force closure beats noisy wrench guidance, but "reduces dexterity".

### 1.2 FlashCHORD (ours) as it runs [F, repo dissection §C; source re-checked]

| Item | FlashCHORD |
|---|---|
| Reward | `frame_dt(0.05) × Σ w·term`, then return normalisation. Kernel `exp(-max(sqrt(SSE)-thr,0)/var)` (Laplacian; `objectives/shaping.py`). |
| object_keypoints | **w 20**. **6 keypoints at ±1 m unit axes** (`objectives/keypoints.py: KEYPOINT_VECS_NP`). Each keypoint `exp(-d/0.1)`, averaged over the 6. |
| hand_keypoints / hand_joint_pos | w 0.25 each. Palm and 5 distal phalanges vs FK of the reference, `exp(-d/0.1)`. Joints `exp(-‖Δq‖/1.0)`. |
| contact_wrench_support | **w 10**. Tolerance 0.1, var 0.1, 512 directions, 8 cone edges, μ 0.1. Labels from 1 cm MANO-object proximity. |
| missed / unintended | −1 / **−10** |
| termination | −100 |
| action_rate / action_l2 | −0.005 / −0.002 |
| force_closure, contact_force | Present but **disabled** (w 0). Force closure has `min_support 0.01`. |
| Relative multi-object reward | **Absent.** The objective list has no relative term, although RPE is scored. |
| Observation | One next-step reference only. Wrist, fingers, object pose, commands, raw and processed action, per-link contacts. The critic adds VOC state and phase. |
| Action | 56-D residual: pos 0.05 (clip 0.2 m), ori 0.15 (clip 1.0 rad), fingers 0.15 (clip 1.0). EMA 0.3. Wrist kp 25 N/m. |
| VOC | `F = m(400Δp − 40v) + mg`, `τ = I(400·rotvec − 40ω)`, clamp ±200 N / ±50 N·m. Fixed schedule 1 → 0.75 → … → 0 by **122.9M of 250M** steps. 1 s hold after every reset. |
| Reset | Uniform frame in [0, N−2]. Fingers `u·q_ref`, `u ~ U(0, 0.7)`. P(frame 0) = 0.1 → 0.5 late in training. |
| Termination | Palm > 15 cm, object > 10 cm or > 0.5 rad (instantaneous). |
| Learner | 4,096 worlds, 250M steps. Actor 256 / critic 512. Replay 4.19M. Batch 2,048, 3-step returns, γ 0.99. |

### 1.3 Two facts that matter when reading the other papers' comparisons

1. **[F FDR Fig. 1 caption, §IV-A]** FlashDexRetarget ran "CHORD … with its released implementation, which trains policies **with PPO**".
   - **[F FDR §IV-C]** In FDR's own ablation, PPO reaches "near-zero cumulative success" where FlashSAC reaches 34–86%.
   - **[I]** FDR's CHORD numbers (Sharpa SR_SPIDER 0.50; ~3,314 GPU-h) therefore probably understate FlashCHORD, which uses FlashSAC.
2. **[I] Rotation is over-weighted in FlashCHORD's object reward.** With keypoints at ±1 m:
   - A 0.05 rad (2.9°) rotation scores 0.738, the same as a 3 cm translation: `(2 + 4·exp(-0.05/0.1))/6` vs `exp(-0.03/0.1)`.
   - The reward bottoms out at 1/3 for rotations beyond about 0.3 rad, because the two on-axis keypoints never move. It gives almost no gradient for large rotation errors.
   - FDR deliberately scales points so that **30° ≈ 3 cm** [F FDR §III-B], which is 10× less rotation-sensitive.
   - **[F FDR Table I b]** on Sharpa: among successful clips, FDR's mean rotation error is 0.32 rad vs CHORD's 0.19 rad, while its position error is 16.5 mm vs 60.1 mm. This fits the weighting difference: FDR trades rotation accuracy for position.

---

## 2. Paper-by-paper extraction

### 2.1 FlashDexRetarget (FDR), arXiv 2610.01849 v2; code Holiday-Robot/FlashDexRetarget

**Setting [F §IV-A]**
- One policy is trained across many references: 50 clips (TACO 10, OakInk2 15, HOT3D 25).
- XHand and Sharpa Wave, Isaac Sim / Isaac Lab 2.3, RTX 3090.
- Control at 60 Hz: `decimation 4 × dt 1/240` (`config/envs/flashdexretarget.yaml`).
- 2,048 environments; episode 20 s, or the end of the clip.

**Results [F Table I]** (SR_SPIDER / SR_MT-Obj / SR_MT / MOPE / MORE / GPU-h)

| Hand | Method | SR_SPIDER | SR_MT-Obj | SR_MT | MOPE | MORE | GPU-h |
|---|---|---|---|---|---|---|---|
| Sharpa | Do as I Do | 0.64 | 0.10 | 0.10 | 58.3 mm | 0.24 rad | 62 |
| Sharpa | CHORD (PPO) | 0.50 | 0.22 | 0.00 | 60.1 mm | 0.19 rad | 3,314 |
| Sharpa | **FDR** | **0.86** | **0.80** | **0.80** | **16.5 mm** | 0.32 rad | **44** |
| XHand | FDR | 0.90 | 0.86 | 0.86 | 10.9 mm | — | 29 |
| XHand | DexMachina | 0.48 | — | — | — | — | 447 |
| XHand | CHORD | 0.46 | — | — | — | — | 2,847 |
| XHand | Do as I Do | 0.36 | — | — | — | — | 66 |

- Sharpa used **400M** environment steps; XHand used 300M [F §IV-B].
- SR_SPIDER is 10 cm / 0.5 rad, averaged over the active hands. SR_MT is 3 cm / 30° on the object, plus fingertips < 6 cm and joints < 8 cm. SR_MT-Obj is the object part only [F §IV-A Metrics].

**Observation [F §III-A; `config/envs/obs/flashdexretarget.yaml`]**

The actor and critic receive the same terms; noise is zero by default.
- Robot: wrist pose, linear and angular velocity (world frame); joint position and velocity; fingertip positions and velocities (wrist frame); the current DOF targets.
- `ref_future_mano_body_delta_w`: next-frame MANO keypoints minus the robot's, position and velocity.
- Object (wrist frame): position, quaternion, linear and angular velocity, **128-point surface cloud**.
- Reference object (wrist frame): next-frame position delta, quaternion delta, **128-point cloud delta**.
- Contact: per-link contact wrench and position (wrist frame).
- **SDF distance plus normal** at palm and 5 tips. The SDF is pre-baked on a 128³ grid; the paper says the grid covers a 60 cm cube, the config uses `grid_extent 0.30`.
- **Future window K = 10 at stride 1** (60 Hz, so about 0.17 s). Per step and per side:
  - object position (3), object rot6d (6), object linear and angular velocity (3 + 3);
  - MANO wrist position (3), wrist rot6d (6), 5 MANO tips (15).

  That is **39 values × 2 sides × 10 steps = 780**, all relative to the current wrist frame. A Conv1d encoder (hidden 128, 2 layers) maps them to a **128-D** latent, trained jointly with actor and critic [F §III-A Eq. 4; `runner/flashsac.yaml traj_encoder`].

**Reward** [F §III-B; `config/envs/rewards/flashdexretarget.yaml`; `src/envs/rewards/motion_tracking.py`]
- Built per hand `h`. With `per_hand_actor_critic` each side's twin terms get **half the weight**; the termination penalty keeps full weight and is charged to the side at fault.
- The mjlab reward manager multiplies by dt (1/60 s), and FlashSAC normalises rewards (`normalize_reward: true`, `normalized_G_max 5`).

| Term | Weight | Definition |
|---|---|---|
| `tracking_obj_pcd_match_error_exp` | **1.0** | 128 object-frame surface points, **rescaled so the max radius is ρ = 0.058 m**. Error `e` = **mean of the 3 largest** point distances between sim and reference pose. `r = exp(-10·e)`, so σ_obj = 0.1 m. |
| `tracking_ref_mano_tip_distance_bound_exp` | **0.3** | Per tip: `ε = max(0, d_robot_SDF − d_ref_unsigned)`; `r = mean_5 exp(-ε/0.01)`. The reference distance is MANO tip to nearest object vertex (unsigned), so the robot need not reproduce penetrations. No binary contact label. |
| wrist translation | 0.15 | `exp(-10·‖Δp‖)` vs the MANO wrist |
| wrist rotation | 0.15 | `exp(-3·angle)` |
| MANO fingertip translation | 0.3 | `exp(-20·‖Δp‖)` per tip, averaged |
| joint BC | 0.3 | `exp(-500 · mean(0.5·(q_target − q_ref)²/range))` on the commanded targets |
| action penalty | −0.01 | mean a² |
| termination penalty | **−50** | bad terminations only; time-out and clip end are not penalised |

- The configured shares are: object 1.0 of a positive maximum of 2.2 (45%); hand tracking 0.9 (41%); interaction 0.3 (14%).
- For comparison, FlashCHORD gives the object 20 of 30.5 (66%) and hand tracking 0.5 (1.6%).
- Unused terms also exist in the code: `tracking_obj_rel_pcd_match_error_exp` (object-object relative point match in the other object's frame, with a `gate_dist`), `tracking_contact_chamfer_match`, `force_penalty`, and a 1:1 port of CHORD's wrench terms (`chord.py`, defaults tol 0.1, var 0.1, μ 0.1, 8 edges, 512 basis vectors).

**Action** [F `config/envs/actions/flashdexretarget.yaml`, `src/envs/actions/residual.py`]
- Wrist translation target = `ref + 0.1·a` (±10 cm). Wrist rotation = `ref + 1.0·a` (±1 rad).
- Fingers are **absolute**: `a ∈ [-1,1]` mapped onto the joint limits, kept near the reference only by the BC reward.
- A 5 Hz low-pass filter on the wrist channels. PD position targets.

**Learner** [F `config/runner/flashsac.yaml`]
- FlashSAC, γ 0.98, **n-step 5**, 2 updates per environment step, batch 4,096.
- **Replay 50M** (fp16, compact, about 88 GB). With CPU pinned memory it needs about 16 GB of GPU.
- **Actor 2 blocks × 128; critic 2 blocks × 1024**, distributional with 101 bins in ±5.
- Learning rate 3e-4 → 1.5e-4. Entropy temperature target σ 0.15.
- **Per-hand actor-critic** (`side_actors: true`). Each actor sees the full observation and outputs only its own hand's action.
- AMP plus torch.compile.

**Ablations [F §IV-C, Fig. 3]** (50 clips, 300M steps, cumulative SR_MT-Obj)
- Off-policy and capacity, the only ablation quoted in numbers:
  - PPO ≈ 0.
  - Default FlashSAC (10M buffer, critic 256) ≈ **34%**.
  - Plus 50M buffer ≈ **60%**.
  - Plus critic 1024 = **86%**.
- K-future encoding, the point-cloud reward and observation, the interaction reward, and per-hand actor-critic each help. These are reported only qualitatively: "removing either reduces learning speed and success; removing both is largest"; "the larger drop without PCD matching".
- Scaling to 200, 500 and 1,000 clips gives more conversions per GPU-hour [F §IV-D].

**Curriculum (object assist)** [F `config/envs/curriculum/flashdexretarget.yaml`, `src/envs/curriculum/assist.py`]

This is an **adaptive, performance-gated** xfrc PD on the object (a DexMachina-style VOC):
- Initial gains: kp 80, kv 5, force/torque clamp 50; rotation kp ×96 and kv ×√96.
- Per-environment gains are drawn uniformly from [lower, upper].
- Every epoch (32 environment steps) it checks the gates. It decays when the 30-epoch means show:
  - task reward ≥ 0.6;
  - imitation ≥ 0.01;
  - BC ≥ 0.01;
  - completion (time-outs over all resets) ≥ 0.65;
  - and it is past `wait_epochs` 100 and `decay_cooldown_epochs` 40.
- Decay: upper ×0.9, lower = 0.8 × upper.
- Fully released when kp < 0.05.
- Dial-back: if completion falls below 0.5 more than 500 epochs after the last decay, return to the previous gains ×0.98.

**Reset** [F `commands/motion_tracking.yaml`, `motion_tracking.py`]
- Uniform start frame in [0, 0.99·T]; the robot is set to the reference joint state and the object to the reference pose.
- Tiny noise: base σ (wrist 1 cm, 10°, 12.5% of finger range) × `noise_to_initial_level 0.1`, so about 1 mm, 1° and 1.25%.
- No hold.
- Evaluation every 20M steps, deterministic from frame 0 of each clip, with the assist off.
- Options present but off by default: reference-noise RSI (2 cm / 6°), object perturbation (start 0.05, continue 0.95, 0.5 s lag, only when lifted), a static offset, and support disks.

**Termination** [F `config/envs/termination/flashdexretarget.yaml`, `terminations/motion_tracking.py`]
- `object_dropped`: object z more than 10 cm below the reference z.
- **`task_reward_early_reset`**: checked every 5 steps; terminates if the *cumulative* object reward since reset is below 0.6 × elapsed steps. That is a running-mean object reward < 0.6, roughly a top-3 point error above 5.1 cm on average.
- Fingertip diverged: any tip more than 20 cm from its MANO tip, after a 15-step grace period.
- Velocity and NaN sanity checks.
- **No instantaneous object-pose threshold.**

**Kinematic reference (retargeting)** [F `config/retarget/kinematic_retargeting.yaml`, `src/retarget/robot_hand/ik.py`; docs]

This is **physics IK in MuJoCo with the objects and tables in the scene**:
- A palm weld (torque 10, solref 0.02) and 5 tip connects (torque 1, solref 0.01; ring and pinky width ×3).
- The object follows its reference through a stiff weld (solref 0.002).
- Elliptic cone, implicitfast integrator, 20 solver iterations.
- Start pose: best of 48 random finger guesses, then a 60-step settle.
- Recovery restart when the 15-frame mean tip error exceeds 4.5 cm (cooldown 30).
- **6 attempts per clip; keep the one minimising mean tip error + 0.5 × max penetration.** Then a 3-frame moving-average smooth.
- Quality flags: palm acceleration > 60 m/s², tip error > 3 cm on > 35% of frames, hand-object penetration > 2 cm.
- Reference contact labels: tip-object distance < 1.5 cm.
- Clip filters: wrist acceleration spike > 60 m/s², shorter than 2.5 s.

### 2.2 Do as I Do (2606.19333; code malik-group/do-as-i-do; `launch.py --robot-type sharpa` is the default)

**Pipeline [F §3.1, App. A]**
- SAM 3 masks, MoGe pointmaps, SAM 3D mesh, HaWoR hands.
- Object tracking by **guided flow-matching in SAM 3D**: the shape is fixed at an anchor frame and the pose is blended toward the previous frame.
  - Pose guidance `α_p(k) = max(0.1, 0.7 − 0.09|Δθ_k|)`, with Δθ from 20 BootsTAPIR points and a 2-D rigid fit.
  - Shape guidance α_s ∈ [0.9, 1].
  - N = 25 candidates per frame, chosen by SE(3) clustering plus mask IoU.
- Hand-object scale alignment: `k = z_hand^H / z_hand^M`; `s* = tᵀ(obj_target − c_mesh)/tᵀt`.
- GeoCalib gravity alignment.

**Retargeting [F §3.2, App. B Table 4; `retargeting/config/override/do_as_i_do.yaml`; `utils/mjwp.py`]**
- First a kinematic reference: mink IK on fingertips, with several random initialisations.
- Then **MPPI-style annealed sampling** (SPIDER) in **MuJoCo Warp**:
  - sim_dt 0.005; replanning every 0.5 s over a 3.0 s horizon; knots every 0.2 s;
  - **1,024 samples × 32 iterations**; temperature 1.0;
  - weights are a softmax over the **top 10%** of z-normalised rewards (`utils/sampling.py`);
  - early stop when improvement < 0.01 for 2 checks.
- Noise:
  - per-component: position 0.01, rotation 0.01, joints 0.1;
  - along the horizon: log-spaced from 1.0 to 4.0;
  - across iterations: ×β^i with β = 0.01^(1/32).
- **Reward**: `r = −‖W ⊙ (q_sim ⊖ q_ref)‖₂` (one weighted L2 norm, not exp), plus penalties. Weights:
  - object position 1.0, object rotation 0.3;
  - wrist position 0.1, wrist rotation 0.03;
  - finger joints 0.01;
  - terminal reward ×10.
- **Penetration** `3000·max(pen − 5 mm, 0)²` (maximum over contacts).
- **Transition penalty 0.5 (constant)**, from `_rest_surface_penalty`:
  - If the reference is *in hand* (reference hand-object distance < **0.1 m**) and not near a rest surface (object-surface distance < **0.01 m**), penalise worlds with no hand-object contact.
  - If the reference is *resting* and not in hand, penalise worlds with no object-surface contact.
  - Transition frames are left unpenalised.
- **Warmup**:
  - Prepend 3.0 s. The object is **welded** in place; the hand starts **backed off along −palm-normal until ≥ 10 cm clearance**, with fingers open.
  - The reference is interpolated from that start to frame 0 over 3 s; reward ×0.1 during warmup.
  - The weld then drops.
- **Perturbation**:
  - 4 perturbed copies per candidate (common random numbers), reward averaged.
  - Force 0.5·m·g, torque 0.5, start probability 0.05/step, continue 0.95.
  - Gated to "held and lifted", eroded by a 0.5 s lag.
- **Meshes**: CoACD hulls, **thickened and dilated by 2 mm**; a flat "base plate" under objects that start in non-flat poses.

**Ablation [F Table 3]** (success at 10 cm / 0.5 rad mean error)

| Variant | In-the-wild reconstructions (655) | OakInk2 (1,352) |
|---|---|---|
| Annealed sampling (SPIDER) | 0.25 | 0.72 |
| + Warmup | **0.66** | 0.77 |
| + Perturbation | 0.67 | 0.79 (position 0.06 → 0.03 m; rotation 0.25 → 0.14 rad) |
| + Transition reward | **0.71** | **0.81** |

- Third-party results:
  - [F FDR Table I] On FDR's 50-clip benchmark, Do as I Do reaches SR_SPIDER 0.64 on Sharpa but only 0.10 SR_MT, with 58 mm mean object error.
  - [F Gen2Dex Table II] With Do as I Do perception fixed, its MPC solved 1/6 tasks and Gen2Dex's residual RL 2/6.

### 2.3 Contact-anchored retargeting and residual RL (2609.24093; DexGEM-Lab/real2sim2real, code not released)

- **Stage 1, physics refinement [F §3.2]:**
  - Residual RL on a simulated MANO hand (22 finger joints, 6-DoF wrist, PD) in Isaac Gym.
  - `Δq_t = γ·Δq_{t−1} + s ⊙ a_t; q_cmd = q_ref + Δq_t`, clipped per dimension.
  - Reward: object tracking plus "contact-achievement" terms. Weights are not given.
  - **One policy per setting** across all trajectories, conditioned on task id, object geometry, and current and future reference object motion. Produces contact labels, object-surface contact locations and forces.
- **Stage 2, contact-anchored retargeting [F §3.3]:** per frame, optimise wrist SE(3) and active finger controls.
  - Multi-contact frames: `E = w_tgt E_tgt + w_pen E_pen + w_h2o E_h2o + w_spen E_spen + w_j E_joint + w_g E_ground + smoothness(base, ctrl, rot)`.
  - `E_tgt = Σ_i [max(‖c_i(u) − p_i‖ − δ, 0)]²` with **δ = 1 cm**. Each `c_i` is the robot surface point whose direction from the link centre best matches the MANO contact direction.
  - Sparse frames (0–1 contacts): finger controls only, wrist frozen.
  - Weights are not given.
- **Stage 3, residual RL on the robot [F §3.4]:** same residual form; wrist orientation follows the reference with no residual. **After the final demonstrated contact, the finger decay γ = 1, so grasp corrections persist.** PPO, one policy per setting.
- **Evidence:**
  - Single hand [F Table 1]: replay 7.26% → residual 59.31% (14 objects).
  - Dual hand [F Fig. 3]: task-level **16.0% → 62.4%**, attempt-level 8.4% → 43.9%.
  - Four hands [F Table 3]: 17.1% → 79.5%.
  - Retargeting quality [F Table 5]: fidelity 14.7 mm, jitter 0.53 rad/s, 3.2% joint-limit violations. SPIDER's default got 49.9 mm and 0.73 rad/s.
  - Success criterion: object within 3 cm throughout, 30° at the final frame [F §4.1].

### 2.4 Morphometric Imitation (2609.28660; no code)

- **Kinematic retargeting, MMO [F §IV]:**
  - **Morphology matching:** a scaled MANO with 6 scales (palm plus each finger), initialised from URDF ratios. Levenberg–Marquardt on `w_j L_joints + w_f L_tips`, done once per robot.
  - **Contact matching per frame:** contact vertices are MANO vertices within **τ = 4.5 mm** of the object. Non-contact frames reuse the most-contacted frame's vertex set, so the pre-grasp is preserved.
  - Contact-matching loss: `w_c L_c + w_d L_coupled + w_table L_table + w_p L_pose` (LM, warm-started from the previous frame).
  - **Linear blend retargeting:** heat-diffusion skinning weights on a 1-D skeleton give dense 6-DoF targets per link. Then PyRoki IK with self-collision, joint limits, velocity and table costs.
  - Runs at 180 fps on an RTX 4090, excluding IK.
- **Residual RL [F §V]:** PPO in ManiSkill, `q_cmd = q_ref + Δq`.
  - Observation includes current and future reference joints, future reference contact states, observed contact booleans, object properties, table clearance, and previous action.
  - Reward is **multiplicative**: `r = exp(−α·ADD) · (1 − |N_goal − N_obs| / N_max)`.
    - ADD uses mesh points, unnormalised.
    - `N_goal = min(N_human_contacting_fingers, N_robot_fingers)`.
    - α is in the supplement, not read.
  - **Termination when an EMA of ADD error or of contact mismatch exceeds a threshold**; immediate on table collision or excessive force.
  - Domain randomisation: PD gains, friction, mass, CoM, anisotropic scale; object ±5 cm (a 10×10 cm region) and ±15° yaw; random start timestep; random external wrenches.
  - 60–90 min per policy on an RTX 4090.
- **Evidence:**
  - Sharpa SR, best competing reference vs MMO [F Table III]: **56.5% → 91.8%** (C-ADD 5.76 → 3.41 cm).
  - Contact and object-pose ablation on Sharpa [F Table IV]:

    | Contact | Object pose | SR |
    |---|---|---|
    | ✓ | ✓ | **91.8%** |
    | ✗ | ✓ | 76.6% |
    | ✓ | ✗ | 54.3% |

    Dex3 82.5 / 51.2 / 42.5; Allegro 69.9 / 47.6 / 41.6.
  - Sharpa real-world: 89.3% over 300 trials.

### 2.5 Gen2Dex (2610.24392; no code)

- Perception: SAM 3, an optimisation tracker (DINOv3 templates, PnP, feature refinement), RollingDepth, HaWoR, depth-mediated Chamfer alignment with one global depth scale `s` [F §III-C].
- **Residual RL [F §III-D]:** PPO in Genesis, batch 2,048, RTX 4090.
  - Wrist residual on the reference: `p = p_ref + S_p a`, `R = R_ref ∘ ΔR(S_r a)`.
  - **Fingers are delta-integrated and independent of the reference**: `q_t = q_{t−1} + S_f a`.
  - Reward `w_obj r_obj + w_hand r_hand + w_reg r_reg`. Weights and scales are not given.
- **Backward curriculum [F §III-D]:** start near the end of the demonstration and move the start backward once the policy "reliably succeeds". The thresholds and step sizes are not given.
- **Reset-state cache [F §III-D]:** for each reference frame:
  1. Sample hand configurations near the reference, plus hand-surface-to-object-surface contact correspondences.
  2. Gradient-optimise `λ_c L_contact + λ_p L_penetration(SDF) + λ_r L_reg`.
  3. **Validate in simulation**; keep only states with negligible penetration and a stable object.
- **Evidence:**
  - Reset and curriculum ablation over 10 tasks [F Table IV]:

    | Reset states | Start | Tasks solved |
    |---|---|---|
    | Valid | Backward | **9/10** |
    | Valid | Random frame | 5/10 |
    | Initial state | First frame only | 2/10 |
    | **Raw reference poses** | Backward | **0/10** |

  - ADD-AUC [F Table III]:

    | Method | ARCTIC (Sharpa) | Generated-video references |
    |---|---|---|
    | Gen2Dex | 65.75 | **76.18** |
    | SPIDER | 63.51 | 67.06 |
    | DexMachina | 62.40 | 38.20 |
    | CHORD | 56.30 | 41.15 |

### 2.6 SPIDER (2511.09484; code facebookresearch/spider)

- **Optimiser [F §3.2 Eq. 2–3]:**
  - `U ← U + Σ_j exp(−J_j/λ) W_j / Σ exp(−J_j/λ)`.
  - Covariance `Σ_h^i = exp(−(N−i)/(β₁N) − (H−h)/(β₂H)) I`.
  - In code: noise(i, h) = log-space(first → last over the horizon) × `β^i`, with `β = final_noise^(1/N)`. Table 5: β 0.931 without guidance, 0.963 with.
  - Early stop.
  - "Automatic difficulty boosting": a failed step is retried with ×2 iterations and ×√2 noise [F App. A.3].
- **Cost [F §3.1 Eq. 1]:** `Σ ‖x ⊖ x_ref‖²_Q + ‖u‖²_R`, with SE(3) differences taken by log-map.
- **Virtual contact guidance [F §3.3, App. C; code `examples/run_mjwp.py`, `spider/preprocess/detect_contact.py`]:**
  - **Contact labels:** MuJoCo contact sensors on MANO fingertips during kinematic replay (1-frame smoothing window). Contact positions are stored in the object frame and averaged over contact frames. **A contact is disabled if its position std exceeds 0.1 m** ("t_c,min / d_c,max" filter in the paper).
  - **Mechanism:** the object's free joint is replaced by 6 actuated slide and hinge joints (`scene_act.xml`), each with PD gains:
    - OakInk: pos kp 10, rot 0.3.
    - GigaHands: pos 2.0, rot 0.3.
    - Code defaults: pos kp/kd 10/10, rot 0.1/0.1.
  - The object actuator target = reference object position **+ clip(mean over active contacts of [current robot contact site − reference contact position], ±1 cm)**. The object is pulled toward where the hand actually is, which is a **relative** hand-object constraint (Eq. 5/7).
  - **Annealing:** gains ×`γ_g^i` per optimisation iteration (γ_g = 0.8 OakInk, 0.5 GigaHands), and **exactly 0 at the last iteration**, so the final rollout is unassisted.
  - With guidance on: smaller sim_dt (0.005) and ctrl_dt (0.05–0.2 s), more noise (first 1.0), and the early stop disabled.
- **Evidence:**
  - ADD-AUC on OakInk [F Table 1]: kinematic 11.0, SPIDER 48.8, **SPIDER + contact guidance 56.9**. GigaHands: 24.1 / 56.9 / 57.7.
  - Throughput drops from 6.1 to 0.4 FPS with guidance.
  - **RL from a SPIDER reference [F §4.2.1, App. A.6]:** task progress **0.99 ± 0.01 vs 0.07 ± 0.11** with the kinematic reference (7 seeds, PPO, 4,096 environments). Settings:
    - Rewards `exp(−s·e)`: object position s 30, w 0.065; rotation s 1.9, w 0.065; wrist 20 / 1.9 at w 0.039; fingers s 10, w 0.039; **hand landmarks in the object frame s 60, w 0.279** (the largest weight); action penalty −0.1.

### 2.7 Contact definitions compared

| Method | Robot contact | Reference contact |
|---|---|---|
| FlashCHORD | 17 links per hand, simulator contacts, wrench support | MANO-object proximity < 1 cm |
| CHORD benchmark | — | HOT3D segmentation: fingertip distance < 2 cm, gaps up to 15 frames bridged [F App. D] |
| FDR | No binary label: SDF distance at the 5 tips | Unsigned distance of MANO tip vertex to nearest object vertex. Labels for statistics: < 1.5 cm |
| SPIDER | Fingertip contact sites | Contact sensors in replay; unstable contacts (std > 0.1 m) dropped |
| Do as I Do | — | Hand-object < 0.1 m means "in hand"; object-surface < 1 cm means "resting" |
| Morphometric | Fingers with non-zero contact force | MANO vertices within 4.5 mm of the object |
| Contact-anchored | — | Physics-refined MANO contacts; anchor tolerance δ = 1 cm |

---

## 3. Side-by-side: FlashCHORD vs FDR (same hand, same learner family)

| Axis | FlashCHORD (ours) | FDR | Direction to test |
|---|---|---|---|
| Object reward | 6 keypoints at ±1 m, mean `exp(-d/0.1)`; rotation-dominated, floors at 1/3 | 128 surface points at ρ 5.8 cm, top-3 mean, `exp(-e/0.1)` | Object-scaled points (T1) |
| Contact term | Wrench support 10, missed −1, unintended −10 (labels needed) | One-sided tip distance 0.3/1.0 (no labels) | Label-free term; soften unintended (T2) |
| Hand tracking share | ~1.6% | ~41% (wrist, tips, BC) | Raise if references are clean (T10) |
| Future reference | Next frame only | K = 10 Conv1d → 128-D | Add (T4) |
| Object geometry and SDF observations | None | 128-point clouds, SDF + normals at palm and tips | Optional (T4b) |
| Actor-critic | Single | One per hand | Per hand for bimanual (T6) |
| Critic / replay / n-step / γ | 512 / 4.19M / 3 / 0.99 | 1024 / 50M / 5 / 0.98 | Test (T5) |
| Assist curriculum | Fixed schedule, VOC 0 at 122.9M of 250M | Adaptive, reward- and completion-gated, with dial-back | Adaptive (T3) |
| Reset | Uniform frame; open fingers U(0, 0.7); 1 s VOC hold | Uniform frame; ~1 mm / 1° noise; no hold | Valid-state cache plus backward (T3) |
| Termination | Instant: object 10 cm / 0.5 rad, wrist 15 cm | Cumulative object reward < 0.6; drop 10 cm; tip 20 cm | Cumulative / EMA (T7) |
| Action | Residual 5 cm / 0.15 rad / 0.15 rad, EMA 0.3, wrist kp 25 | Wrist ±10 cm / ±1 rad, LPF 5 Hz, absolute fingers + BC | Wider finger residual (T11) |
| Reference generation | E2S fingertip IK, no collisions | MuJoCo physics IK with object collisions, 6 attempts, penetration-aware pick | Physics IK (T10) |
| Multi-object relative reward | Absent | Available but off | Add (T8) |
| Multi-reference training | One policy per episode | One policy for all clips | Big change (T12) |

---

## 4. Porting guide (ranked by expected value per unit effort)

### 4.0 Common A/B protocol (applies to every test below)

- **Windows.** Use three public-episode frame windows, chosen from our own reference and video (never from mocap):
  - **W1, ep18** (sweeper + dustpan): pick-up plus the first sweep, where the sweeper currently falls.
  - **W2, ep24** (planter boards): the lift, which is currently never achieved.
  - **W3, control:** ep12 cup or ep21 pour, which already work.
  - Window length about 80 source frames (~4 s; ~160 control steps at `motion_speed 0.5`). Use the same windows in every arm.
- **Budget.** About 20 min per run on one RTX PRO 6000.
  - **[E]** At the ~21k steps/s per policy in STATUS, that is about 25M environment steps.
  - **Compress the VOC schedule identically in both arms**: same stage fractions, so VOC reaches 0 at about 49% of the steps, as now.
  - **[E]** About $0.25 per run (from STATUS: ≈ $2.4 per 3.5-h policy, two per box).
- **Seeds.** 3 per arm. STATUS measured policy-to-policy AUC spread of ±0.03 and single-policy rollout noise of 0.13–0.41 on hard episodes. Evaluate each policy **8 times** and use the mean.
- **Metrics.**
  - **Primary (no ground truth):** FlashCHORD's internal sim-vs-reference ADD-AUC (1–9 cm), SP-SR, MP-SR and RPE over the window, with the evaluator's frame-0, VOC-0 start. STATUS reports a 0.98 correlation with mocap.
  - **Secondary:** environment steps until the first deterministic evaluation passes SP-SR and MP-SR on the window. This is FDR's "cumulative conversion" idea.
  - **Diagnostic only**, after training and on public episodes only: mocap AUC with our registered scorer.
  - Report cost alongside: wall-clock and steps per second, because some arms are slower.
- **Decision rule.** Adopt if, paired by seed:
  - mean primary AUC gain ≥ 0.05 on W1 or W2;
  - the sign is positive in ≥ 2/3 seeds;
  - and W3 does not regress by more than 0.02.

  Otherwise record the arm as falsified in `docs/work-log.md`, keep the run, and do not re-tune it on eval episodes.
- **Integrity.** All the new reward and observation inputs below are computed from **our** reconstructed references and meshes: MANO tips, object points, contact distances. Mocap is never read during training or selection.

### T1. Object reward in object-scaled geometry (highest value, smallest change)

- **Change**, in `objectives/keypoints.py` / `configs/objective/tracking.yaml` / curriculum weights:
  - **Arm B (one line):** scale the 6 axis keypoints by each body's `object_mesh_radius` (already a required Reference field) instead of 1 m. Keep w 20 and var 0.1.
  - **Arm C (FDR port):** a new `object_points` term.
    - 128 points sampled uniformly on our simulation mesh surface, in the object frame.
    - Rescaled to max radius ρ = 0.058 m.
    - Error = mean of the top-3 per-point distances (sim vs reference pose).
    - `exp(−e/0.1)`, w 20, replacing `object_keypoints`.
  - **Arm D (metric-matched):** like C but with the **true radius** (no rescale) and **σ = 0.05 m**, closer to ADD-AUC's 1–9 cm band [I].
- **Evidence.**
  - [F FDR §IV-C Fig. 3b] Replacing the point reward with DexMachina's object reward was the largest reward-side drop (stated qualitatively).
  - [F FDR Table I] FDR reaches 16 mm position error vs CHORD's 60 mm, but 0.32 vs 0.19 rad rotation error.
- **Expected effect [I].**
  - Better position tracking (AUC, MPPE, RPE).
  - Gradient restored for rotation errors beyond 0.3 rad, which the ±1 m keypoints flatten.
  - **Risk:** rotation tracking degrades. That affects SP-SR (0.5 rad) and MP-SR (30°); compare B vs C vs D.
- **Falsifier.** No arm beats A by ≥ 0.05 AUC on W1 or W2, or MP-SR falls.

### T2. Contact supervision that tolerates noisy egocentric labels

- **Change.**
  - **Arm B:** add FDR's one-sided tip-distance term.
    - `r = mean_5 exp(−max(0, d_sim_tip − d_ref_tip)/0.01)`.
    - `d_sim_tip` is the SDF or closest-point distance from robot tip sites to the object mesh (Newton/Warp mesh query, or a pre-baked 128³ SDF).
    - `d_ref_tip` is the unsigned distance of **our reconstructed MANO tip** to our mesh. Compute it in mkref and store it as a new reference field `mano_{side}_tip_object_distance (T,5)`.
    - Weight **6** = 0.3 × object weight 20, the FDR ratio.
  - **Arm C:** B plus `contact_wrench_support` 10 → **3** and `unintended_contact` −10 → **−2**.
  - **Arm D:** C plus `force_closure` w 3 (min_support 0.01), **only on frames whose reference is in hand**: Do as I Do's gate, reference hand-object < 0.1 m and object not within 1 cm of the support.
- **Evidence.**
  - [F FDR Fig. 3b] The interaction reward gives a complementary gain.
  - [F CHORD Table 2] On clean mocap, wrench guidance gives AUC 0.918 vs 0.862 for position-only and 0.774 for none. So do not drop wrench guidance outright.
  - [F CHORD App. A.1] Noisy contacts hurt; force closure wins at high noise.
  - [F Morphometric Table IV] Sharpa SR 76.6% → 91.8% when a label-light contact-count term is added to the object reward.
- **Expected effect [I].** Fewer "avoid touching" policies on ep24 and ep18, where our 1 cm MANO labels on monocular geometry are unreliable.
- **Falsifier.** B/C/D ≤ A on W1/W2, or the unintended-contact count rises without any AUC gain.

### T3. Reset and assist curriculum for hard windows (Gen2Dex + FDR + Do as I Do)

- **Change.**
  - **Arm B (adaptive VOC, FDR):** replace the fixed VOC stages with gating.
    1. Every 32 steps, compute the 30-epoch mean of the object reward (normalised per step, in [0, 1]) and the completion rate (time-outs over all resets).
    2. If reward ≥ **0.6** and completion ≥ **0.65**, at least 100 epochs have passed, and 40 epochs have passed since the last decay: VOC scale ×**0.9** (per-environment scale drawn in [0.8, 1.0] × upper).
    3. Release to 0 below 0.05.
    4. Dial back ×0.98 to the previous level if completion < 0.5 more than 500 epochs after a decay.
  - **Arm C (Gen2Dex):** B plus a **backward curriculum with a valid reset-state cache**.
    1. Precompute per-frame start states from our reference. Start from the reference state, run with VOC = 1 and fingers closing from `0.7·q_ref` for 0.5 s, then VOC = 0 for 0.5 s.
    2. Keep a state if object drift < 1 cm / 0.1 rad and hand-object penetration < 2 mm; otherwise mark the frame invalid [I thresholds].
    3. Start-frame range = [s, N−2], with s initially at 0.8·W.
    4. Move s back by 0.1·W whenever the windowed completion from s is ≥ 0.7 over the last ~2k episodes [I].
    5. Keep P(frame 0) = 0.1 so the evaluation start is still seen.
  - **Option (Do as I Do warmup, reference side):** extend `mkref --lead_in` to a 1–3 s pre-roll at the start. The object rests on its support and the hand starts ≥ 10 cm back along −palm-normal with open fingers, interpolated to frame 0. Before using it, check that the scorer and kit map rows to source frames correctly with a lead-in.
- **Evidence.**
  - [F Gen2Dex Table IV] 9/10 tasks (valid states + backward), 5/10 (random frame), 2/10 (first frame only), 0/10 (raw-reference resets + backward).
  - [F CHORD §4.1] The VOC must be decayed only after the contact reward converges.
  - [F Do as I Do Table 3] Warmup took in-the-wild success from 0.25 to **0.66**, the largest single gain.
- **Expected effect [I].**
  - Lift and sweep phases get explored with valid grasps before the earlier phases must reach them.
  - Within 25M steps the fixed schedule probably decays VOC too fast for W2 and too slowly for W3; adaptive gating fixes both.
- **Falsifier.** C ≤ B ≤ A on W1/W2 in the steps-to-first-success metric.

### T4. Future-reference conditioning (FDR K = 10)

- **Change** (`envs/observation.py`; actor and critic):
  - Append the next **10** reference steps at stride 1 (20 Hz, so 0.5 s of simulation). Per hand:
    - object position delta (3), rot6d (6), linear and angular velocity (6);
    - reference wrist position (3), rot6d (6);
    - 5 fingertips (15).

    All in the current wrist frame: 39 × 2 × 10 = **780-D**.
  - Arm B: flatten into the MLP input. Arm C: FDR's Conv1d encoder (h 128, 2 layers, 128-D latent), trained with the critic loss.
  - **T4b (optional):** 128-point object clouds (current and next reference) plus SDF distance and normal at palm and 5 tips.
- **Evidence.** [F FDR Fig. 3a] Faster conversion and more clips converted; qualitative, multi-reference setting.
- **Expected effect [I].** The policy anticipates lifts and rotations, which matters at ep24's lift and ep18's sweep onset. Point clouds add little for a single fixed object (low priority).
- **Falsifier.** No gain in steps-to-first-success on W1/W2.

### T5. Critic capacity and replay (cheap configuration change)

- **Change** (`configs/experiment/sharpa_flash_sac.yaml`):
  - Arm B: critic 512 → **1024**.
  - Arm C: B plus replay 4.19M → **16M** and n-step 3 → **5**.
- **Evidence.** [F FDR §IV-C] In the multi-reference setting: default 34% → 50M buffer 60% → plus critic 1024 86%.
- **Expected effect [I].** Smaller gains with one reference (narrow state distribution). Memory cost grows with the replay size.
- **Falsifier.** Equal AUC and equal steps-to-success.

### T6. Per-hand actor-critic with per-hand rewards (bimanual episodes)

- **Change.**
  - Two actors and two critics. Each sees the full observation and outputs its own 28-D action.
  - Rewards split by side; object terms use the object assigned to that hand.
  - Termination penalty charged to the side at fault, both sides if unknown. This is FDR's `_termination_penalty_side`.
- **Evidence.** [F FDR §III-C, Fig. 3c] Faster and higher cumulative success than a unified actor-critic (qualitative).
- **Expected effect [I].** Better credit assignment where the hands do different jobs: ep18 sweeper vs dustpan; ep21 pitcher vs cup.
- **Falsifier.** W1 not improved. This change needs FlashSAC code work; run it after T1–T3.

### T7. Termination on sustained rather than instantaneous error

- **Change** (`lifecycle/termination.py`):
  - Arm B: drop the instantaneous object 10 cm / 0.5 rad check and keep wrist 15 cm. Add:
    - FDR's `task_reward_early_reset`: running mean of the object reward since reset < **0.6**, checked every 5 steps;
    - `object_dropped`: more than 10 cm below the reference z.
  - Arm C: terminate when an **EMA (α = 0.1) of position error > 0.10 m or of rotation error > 0.5 rad**, as in Morphometric [F §V], with thresholds borrowed from ours.
- **Evidence.**
  - [F FDR config]; [F Morphometric §V]. Neither paper ablates this.
  - [I] Our dissection (§C.12) flags that roll of thin objects is weakly observable, while the 0.5 rad instantaneous termination is harsh.
- **Falsifier.** Learning gets slower or AUC drops. If so, keep A.

### T8. Multi-object relative reward (missing in FlashCHORD; RPE is scored)

- **Change.**
  - `r_rel = m(t) · exp(−e_p/0.05) · exp(−e_R/0.5)` [I scales], weight 5.
  - `m(t) = 1` while the **reference** inter-object distance < 0.10 m. CHORD gates on the demo distance, not the policy's [F CHORD App. B].
  - Alternative: FDR's relative point match (object points expressed in the other object's frame, top-k, `gate_dist`).
- **Evidence.** [F CHORD §3.1, App. B] Part of CHORD's own formulation; motivated for insertion, pouring and tool use. No ablation numbers.
- **Expected effect [I].** Lower RPE on ep18 and ep21; little elsewhere.
- **Falsifier.** RPE unchanged on W1 or ep21.

### T9. Disturbance training for robustness (reduces evaluation variance)

- **Change.**
  - A random object wrench while the reference is in hand and lifted: start probability 0.05/step, continue 0.95, force 0.5·m·g, torque 0.5 N·m, 0.5 s gate lag, only after VOC reaches 0.
  - Values from Do as I Do Table 4 and FDR's `perturb` defaults. Or CHORD's version: wrench sampled from the demo contact-wrench matrix [F §3.2].
- **Evidence.**
  - [F Do as I Do Table 3] OakInk2 success 0.77 → 0.79, position 0.06 → 0.03 m, rotation 0.25 → 0.14 rad.
  - [F Morphometric §V] Random external wrenches are part of its domain randomisation.
- **Expected effect [I].** Smaller spread across the 8 evaluation rollouts; STATUS measured 0.13–0.41 on one policy.
- **Falsifier.** Evaluation spread not reduced.

### T10. Better kinematic references (larger effort, potentially largest gain)

- **Arm B (FDR physics IK):** port `retarget/robot_hand/ik.py` to our mkref.
  - MuJoCo scene with our meshes and support.
  - Palm weld (torque 10, solref 0.02) and tip connects (torque 1, solref 0.01).
  - Object welded to our track.
  - 6 attempts, keeping min(mean tip error + 0.5 × max penetration); recovery restart when the 15-frame tip error exceeds 4.5 cm; 3-frame smooth.
  - **Expected:** no hand-object penetration in the references, so cleaner reset states and contact labels.
- **Arm C (contact-preserving retargeting):** MMO-style contact matching on our MANO, or a contact-anchor objective.
  - Contact vertices within 4.5 mm; anchor tolerance 1 cm; non-contact frames reuse the most-contacted frame's vertex set.
- **Arm D (physics-feasible reference):** run Do as I Do / SPIDER MPC (`--robot-type sharpa`, MuJoCo Warp) on the hard windows and use its output as the reference and the reset states.
  - Settings: 1,024 samples × 32 iterations, 3 s horizon, warmup 3 s, transition penalty 0.5, penetration 3000 with a 5 mm margin.
- **Evidence.**
  - [F Morphometric Table III] Sharpa SR 56.5% → 91.8% from the reference alone.
  - [F SPIDER §4.2.1] Task progress 0.99 vs 0.07.
  - [F Gen2Dex Table II] Do as I Do MPC alone 1/6 tasks: use it as a **reference**, not as the final policy.
  - [F FDR Table I] Do as I Do ≈ 62 GPU-h per 50 Sharpa clips.
- **Expected effect [I].** The biggest lever for W2 (boards). It costs 1–2 GPU-h per window for MPC [E].

### T11. Finger action freedom when references penetrate

- **Change.**
  - Arm B: finger residual scale 0.15 → **0.5 rad** (clip 1.0 unchanged).
  - Arm C: Gen2Dex-style delta-integrated fingers `q_t = q_{t−1} + S_f a` with `S_f` = 0.05 rad per step, plus a BC reward toward the reference (w 0.25).
  - Option from the contact-anchored paper [F §3.4]: accumulated residual with decay `γ`, and `γ = 1` for fingers after the last reference contact, so grasps persist.
- **Evidence.** Design rationale only: [F Gen2Dex §III-D]; [F FDR action config] uses absolute fingers.
- **Falsifier.** No gain on W2 or W1.

### T12. Multi-reference training (strategic; after T1–T5)

- **Change.** One FlashCHORD policy over all public and eval episodes, with per-episode meshes in object slots and references from our perception.
- **Evidence.**
  - [F FDR Table I, §IV-D] 50 Sharpa clips at 400M total steps (≈ 8M per clip) in 44 GPU-h, vs our ≈ 3.3 h per episode at 250M steps.
  - Larger collections convert more clips per GPU-hour.
- **Expected effect [I].** 5–10× cheaper per episode; cross-episode transfer for recurring objects. Large engineering cost (object slots, per-hand heads, a large replay).
- **A/B.** Train one policy on 6 public episodes for the same total GPU-hours as 6 per-episode policies; compare the mean primary AUC.

### Hypothesis to test later: a "relative VOC" inspired by SPIDER

- **[I]** Replace the VOC target `x_obj_ref` with `x_obj_ref + clip(mean_k(p_robot_contact,k − p_ref_contact,k), ±1 cm)`, summed over active reference contacts, with SPIDER's annealing.
- The assist would then pull the object toward where the robot's hand actually holds it, not toward an absolute pose the current grasp cannot reach.
- **Evidence:** [F SPIDER Table 1] Guidance adds 8 AUC points on OakInk inside the MPC. Untested in RL.
- **Falsifier:** no gain over the adaptive VOC (T3-B) on W1.

---

## 5. Suggested order and batch [E]

1. Batch 1, configuration-only or small changes:

   | Test | Arms |
   |---|---|
   | T1 | A, B, C, D |
   | T2 | A, B, C |
   | T5 | A, B |
   | T7 | A, B |

   Arm A is shared across tests. That is 9 distinct arms × 3 seeds × 3 windows = **81 runs × 20 min ≈ 27 GPU-h**. At two runs per box, about 14 box-hours, **≈ $20–25 [E]**.
2. Batch 2, code changes: T3 (B, C), T4 (B), T8, T9, on the best batch-1 configuration. About 50 runs, **≈ $15 [E]**.
3. Batch 3, references: T10-B on W1/W2, then T10-D MPC on W2 if T10-B is not enough.
4. Then T6 and T12.

Before each batch: state the plan and cost to the owner and get approval (CLAUDE.md). Commit the exact code per run; record commands, machines, output paths and results, including failures.

---

## 6. Sources

- Papers (arXiv HTML): 2610.01849 (FlashDexRetarget, v2); 2606.19333 (Do as I Do); 2609.24093 (contact-anchored, DexGEM); 2609.28660 (Morphometric Imitation); 2610.24392 (Gen2Dex); 2511.09484 (SPIDER); 2607.00033 (CHORD).
- Code (shallow clones, 2026-10-21):
  - github.com/Holiday-Robot/FlashDexRetarget: `config/envs/*`, `config/runner/flashsac.yaml`, `src/envs/{rewards,terminations,curriculum,actions,commands}`, `src/retarget/robot_hand/ik.py`, `config/retarget/kinematic_retargeting.yaml`, `docs/guide/*.md`.
  - github.com/malik-group/do-as-i-do: `retargeting/config/{default,override/do_as_i_do}.yaml`, `retargeting/retargeting/{config.py,utils/mjwp.py,utils/sampling.py,utils/in_hand.py}`.
  - github.com/facebookresearch/spider: `spider/config.py`, `examples/run_mjwp.py`, `spider/simulators/mjwp.py`, `spider/preprocess/detect_contact.py`.
  - github.com/DexGEM-Lab/real2sim2real: README only.
- Ours: `docs/research/notes/01-baseline-dissection.md`; FlashCHORD source `src/flash_chord/objectives/{keypoints,shaping}.py` and `configs/objective/tracking.yaml`; `STATUS.md` (throughput, hard-episode results).
