# Physics-consistent fit of hand–object trajectories: literature review and v1 design (30 Oct 2026)

Question (owner, 30 Oct): copying the perceived hand–object motion into FlashCHORD drops the objects. Use the inverse
approach instead. For every frame, compute the wrench each object needs from its motion. Ask whether contacts inside
friction cones (fingers, palm, table, other objects) can supply it. Then fit the whole trajectory (object poses, hand
points, contact forces) so that physics violations are small and the result stays close to perception. Build it on CPU
first, as a perception-refinement stage like `pipeline/refine.py`, scored with `pipeline/score_registered.py`.

Labels:
- **[L]**: the paper, or most of it, was read today;
- **[L-abs]**: only the abstract or a summary was read today;
- **[L-repo]**: verified earlier in this repository (file named);
- **[K]**: from background knowledge, not re-read today;
- **[M]**: measured here today;
- **[E]**: estimate;
- **[I]**: inference;
- **[H]**: hypothesis, with the experiment that would falsify it.

No episode data and no ground truth were read for this note. The only measurement is a synthetic benchmark (§4.3).
Cost: $0, no GPU.

## 0. Answer

1. **The owner's approach is an established method family.** Three lines of work do exactly this:
   - *dynamics-consistent state estimation*: optimise positions so that a physics model explains them (Kolev & Todorov
     2015, on MuJoCo's analytically invertible soft contacts);
   - *motion-and-force reconstruction from video*: bodies (Li et al. 2019; Xie et al. 2021) and hands (Pham et al.
     2015/2018; Hu et al. 2022; TactoHand 2026);
   - *contact-implicit trajectory optimisation* in robotics (Posa et al. 2014; Mordatch et al. 2012).

   The reconstruction papers do not use full complementarity. All of them use an object Newton–Euler residual, a
   linearised friction pyramid, and a relaxed (penalty or gated) contact condition, solved as sparse nonlinear least
   squares, a QP, or L-BFGS.
2. **Accuracy gains against ground truth are modest.**
   - Bodies: MPJPE −1 to −13 mm (Li 2019) and 73.6 → 68.1 mm (Xie 2021).
   - Hands: −16 % fingertip pixel error (Hu 2022).
   - Physical plausibility gains are large: frames with fewer than 2 contacts fall from 54.7 % to 2.0 % (Hu 2022), and
     foot height error drops by about 80 % (Xie 2021).

   Our perception already scores 0.89 ADD-AUC. Expect little change in AUC; the payoff is the hand–object relation.
3. **Noisy accelerations.** At 20 fps, 1 cm of frame-to-frame jitter becomes about 1 g of finite-difference
   acceleration noise [I, §2]. Every working method either smooths before it differentiates, or treats poses as the
   variables and takes the accelerations as finite differences of the *optimised* poses. In the second case the physics
   residual and a pose prior do the smoothing.
4. **Does a physics-consistent reference help RL?**
   - The best evidence is SPIDER v3: task progress 0.99 ± 0.01 vs 0.07 ± 0.11 for the kinematic reference (7 seeds, one
     cup task, confounded) [L-repo].
   - Other papers show better open-loop replay or faster convergence, not cleaner RL ablations.
   - None tests an *idealised* (simulator-free) physics fit as the RL reference. That is our hypothesis to test.
5. **Recommended v1** (§6):
   - *Stage 0*: a per-frame force-feasibility LP that measures the "unexplained wrench". This is the owner's question,
     as a diagnostic.
   - *Stage 1*: a trajectory-level sparse least-squares fit. Variables: object pose increments, fingertip and palm point
     offsets, and friction-pyramid weights for fingertips, palm, table support points and object–object pairs. A fixed
     contact-phase schedule comes from GT-free hold labels.
   - Solver: scipy `least_squares` (installed), or CasADi with IPOPT. CasADi's PyPI wheel bundles IPOPT; cyipopt has
     no Linux wheel [M].
   - Runtime [M]: 104 s per object for 300 frames with a finite-difference sparse Jacobian (synthetic; stopped at the
     iteration cap). Expected [E] 2–10 min per two-object episode on 4 CPU cores, or 10–60 s per object with exact
     derivatives.
6. **Falsification test** (§6.4): it must not cost mocap ADD-AUC, and it must raise the *jittered* zero-action
   sim_vs_ref of the frozen grasp-lock reference on the four study episodes.

## 1. Methods (Q1)

### 1.1 Robotics: contact-implicit trajectory optimisation and physics-consistent estimation

| work | variables | physics | contact / friction | solver, runtime | accuracy, code |
|---|---|---|---|---|---|
| **Posa, Cantu, Tedrake 2014**, IJRR 33(1) "A direct method for trajectory optimization of rigid bodies through contact" [L-abs + K] ([pdf](https://posa.seas.upenn.edu/assets/pdf/Posa2014.pdf)) | q, v, u, contact impulses λ per knot (direct transcription) | full rigid-body, time-stepping (Stewart–Trinkle) | complementarity φ(q)·λ = 0, φ ≥ 0, λ ≥ 0 as constraints of a mathematical program with complementarity constraints (MPCC); polyhedral friction with sliding-velocity complementarity; relaxed φλ ≤ ε in practice [K] | SQP (SNOPT, commercial); seconds to minutes for small systems [K] | planning, not estimation; not open-source then. Drake now carries the formulation [K] |
| **Mordatch, Popović, Todorov 2012**, SCA, "Contact-invariant optimization for hand manipulation" [L-abs + K] ([pdf](https://homes.cs.washington.edu/~todorov/papers/MordatchSCA12.pdf)) | hand and object trajectory (splines) + auxiliary contact variables c_i per phase | full dynamics via a soft "physics violation" cost | contact-invariant cost c_i·(distance² + slip²); forces from a small QP in friction cones per step | L-BFGS on a continuation of cost weights; minutes [K] | synthesis, not reconstruction; no code |
| **Kolev & Todorov 2015**, Humanoids, "Physically consistent state estimation and system identification for contacts" [L] ([pdf](https://roboti.us/lab/papers/KolevHumanoids15.pdf)); precursor: Lowrey et al. 2014 IROS [L-abs] | **positions only**, q_1..q_n; **v and a are finite differences of the optimised q**; plus model parameters (contact softness, friction, anchor points) | MuJoCo: forward or **inverse dynamics with soft contacts** (analytic inverse) | MuJoCo soft contacts, remote-contact margin 0.1 mm so that forces exist without penetration; residual cost on the inverse-dynamics generalised force of unactuated DoFs (= 0 for a free object) | Gauss-Newton: H ≈ JᵀJ is **band-diagonal**, J by finite differences (3nk + n dynamics calls), Levenberg–Marquardt damping, Cholesky. 20 s at 200 Hz, 14 DoF = 56,000 variables | robot finger + object with force sensor; sensor predictions match under cross-validation. Code was MATLAB, not released. **Closest template for our Stage 1** |
| MuJoCo docs, [Computation](https://mujoco.readthedocs.io/en/stable/computation/index.html) [L] | — | "The present contact model has a uniquely-defined inverse"; "Inverse dynamics are handled analytically"; not defined in the hard limit R → 0 | pyramidal cones invert trivially; elliptic is the non-trivial case | `mj_inverse` → `qfrc_inverse`; `mjd_inverseFD` gives its derivatives. Both exist in `mujoco` 3.17.0 from PyPI [M] | Apache-2.0 |

### 1.2 Bodies from video

| work | variables | physics | contact / friction | solver, runtime | accuracy vs GT, code |
|---|---|---|---|---|---|
| **Li, Sedlar, Carpentier, Laptev, Mansard, Sivic 2019** CVPR (IJCV 2022) [L] ([arXiv 1904.02683](https://arxiv.org/abs/1904.02683)) | human + **object** configurations and velocities, joint torques, **contact forces**, contact positions, camera/ground | full Lagrangian dynamics M q̈ + b = g + τ (Pinocchio); the object moves only by human contact forces | **contact states from a CNN, fixed during optimisation**; ground: 4-generator friction pyramid; hand–object: unconstrained 6-D wrench | collocation with backward finite differences, **Ceres LM**, penalties for constraints, force coefficients ≥ 0 as hard bounds; 3-stage cascade (kinematics → forces → joint); **3.2 s per frame** | MPJPE 135.7 → 122.1 mm (parkour), 103.5 → 102.4 mm (tools); force errors 108–144 N (74.6 kg body); [project + code](https://www.di.ens.fr/willow/research/motionforcesfromvideo/) |
| **Xie, Wang, Iqbal, Guo, Fidler, Shkurti 2021** ICCV [L] ([arXiv 2109.09913](https://arxiv.org/abs/2109.09913)) | SMPL shape, root and joint rotations, **ground contact forces**, all as **cubic Hermite splines with optimised knot times** | full-body recursive Newton–Euler; only the residual root wrench is penalised (joints free) | smooth contact: c = ½(tanh(10‖f‖ − k₂) + 1) weights distance and velocity at the contact; penetration penalty; friction-cone penalty μ 1.0; force cap 4× body weight | PyTorch L-BFGS: 250 kinematic + 500 physics iterations; **3–4 min per 40 s chunk** | Human3.6M MPJPE 73.6 (kinematic) → 68.1 mm; foot height error 95.7 → 18.9. NVIDIA research |
| Rempe et al. 2020 ECCV [L-abs] ([arXiv 2007.11678](https://arxiv.org/abs/2007.11678)) | reduced (centroidal) body + contact forces | centroidal dynamics | foot-contact timings from a network | NLP [K] | more plausible; small pose changes |
| PhysCap (Shimada 2020), Neural PhysCap (2021), SimPoE (Yuan 2021) [K] | per-frame PD targets / residual forces | full body in a simulator | QP for forces (PhysCap); RL policy + residual root force (SimPoE) | real-time (PhysCap); RL training (SimPoE) | per-frame trackers. Not a whole-trajectory fit, so less suited to an offline refinement |
| OpenSim residual reduction (RRA, MocoTrack, AddBiomechanics); comparison by Fox 2024 R. Soc. Open Sci. [L-abs] ([PMC11061640](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11061640/)) | kinematics + segment masses / COM | full body | measured ground forces | MocoTrack (direct collocation) drives residuals to near zero but is slowest; AddBiomechanics also adjusts segment masses | lesson: mass/COM adjustment is the standard way to absorb residuals *when forces are measured*. We have no measured forces (§5) |

### 1.3 Hands and objects

| work | variables | physics | contact / friction | solver, runtime | accuracy vs GT, code |
|---|---|---|---|---|---|
| **Pham, Kyriazis, Argyros, Kheddar**, CVPR 2015 and TPAMI 2018 [L-abs] ([DOI](https://doi.org/10.1109/TPAMI.2017.2759736), [HAL](https://hal.archives-ouvertes.fr/hal-01356138)) | fingertip contact forces per frame | object Newton–Euler from tracked kinematics (RGB-D model-based tracking) | Coulomb cones; an RNN predicts forces from kinematics, then a **second-order cone program (SOCP)** makes them consistent | per frame | validated against **force sensors**; dataset of 3.2 h, 193 object-grasp configurations. The RNN supplies the internal grip force, which statics leaves undetermined |
| **Hu, Yi, Zhang, Yong, Xu 2022** SIGGRAPH Asia, "Physical Interaction" [L] ([arXiv 2209.10833](https://arxiv.org/abs/2209.10833)) | per fingertip: 4 pyramid weights f_i ≥ 0 and a tip–object distance d̃_i ≥ 0; the object kinematics are kept | object Newton–Euler: ‖ΣA_i f_i + m g − m v̇‖² + ‖Σ(p_i − c)×A_i f_i − τ‖², τ = Iω̇ + ω×Iω (dynamic, not quasi-static) | **fingertips only**; soft complementarity ‖d̃_i f_i‖²; d̃ close to the observed distance; **4-edge pyramid, μ 0.7**; slide prevention: if the normal force exceeds 0.3·m·g and depth confidence is low, the tip is pinned | **Levenberg–Marquardt, 8 ms per frame on CPU** (real time) | 3 sequences; pixel error 11.58 → 9.67 (−16 %); frames with < 2 contacts 54.7 % → 2.0 %; **m = 0.2 kg fixed, hollow-shell inertia**, "mass only a relative value". Accelerations: **3-frame finite differences, no smoothing**. Code not confirmed |
| Kumar, Vaidya, Huth 2021 (EPIC@CVPR) [L-abs] ([arXiv 2105.08196](https://arxiv.org/abs/2105.08196)) | per-vertex object forces (learned), refined hand/object poses | net force matched to finite-difference acceleration | learned | gradient (differentiable) | ContactPose: better poses and contact maps |
| **TactoHand 2026** [L] ([arXiv 2610.39585](https://arxiv.org/abs/2610.39585)) | per-vertex MANO forces (778/hand) + table support force e_t ≥ 0 | object Newton–Euler target wrench w* = [m(a − g); R(Iα + ω×Iω)]; Σ G_i f_i + G_env e_t = w* | candidates: signed distance < 20 mm, soft weight 2/(1 + e^{s/4 mm}); **6-facet pyramid, μ 1.2** | **sparse sequence-level QP in OSQP** (tolerance 1e-6, torque rows scaled by 0.05 N·m, cached factorisations); a differentiable rollout for training | physics supervision lowers rollout error 5.7 → 3.3 cm and 45° → 29° on DexYCB (relative to physics-off). Not checked against measured forces. **m = 1 kg reference mass.** Code "will be released" (github.com/zhenqis123/Tactohand) |
| **Grasp-and-Lift 2026** (Choi, Oh, Lim) [L] ([arXiv 2601.18121](https://arxiv.org/abs/2601.18121)) | hand only: 10 MANO PCA + wrist rotation, keyframes every 5 frames, cubic splines, 4-keyframe sliding window | MuJoCo forward simulation (240 Hz, implicitfast), black box | soft contacts; hand–object and object–table collisions only | **CMA-ES, ~557 s per sequence** (vs ManipTrans 1,987 s) | DexYCB: object rotation error 8.5° → 3.0°, success 45.9 → 71.7 % vs ManipTrans. Measured against the image-aligned reference, not physical GT. No code listed |
| Garcia-Hernando, Johns, Kim 2020 IROS [L-abs] ([arXiv 2008.03285](https://arxiv.org/abs/2008.03285)) | residual corrections to estimated hand poses | simulator | simulator | residual RL + IL | beats "close the hand" and RL/IL baselines in task success and pose accuracy |
| Real2Sim-in-HOI 2026 [L-abs] ([arXiv 2605.14462](https://arxiv.org/abs/2605.14462)); PhysHanDI 2026 (deformable) [L-abs] | human first, then the object fitted to it; then a physics rollout | humanoid-object simulation as teacher | — | — | no numbers on the abstract page |
| SPIDER (arXiv 2511.09484), Do as I Do (arXiv 2606.19333) [L-repo: `physics-solver.md`] | robot controls | full simulator (MuJoCo-Warp) | simulator contacts + virtual contact guidance | annealed sampling on GPU; 1.5–2.5 frames/s (SPIDER, dexterous) | §3 |

Pattern across §1.3 [I]:
- The fits keep the object's kinematics nearly fixed and solve for forces plus hand corrections: the object is the
  better-observed body.
- Contacts come from a small candidate set: fingertips, sometimes the palm, and the table.
- Friction is a 4- to 6-edge pyramid.
- Complementarity is soft: a force × gap penalty, or a sigmoid gate on distance.
- Mass is a nominal constant.
- No paper fits object–object contacts (lid on pot, cup into rack).

## 2. Noisy accelerations (Q2)

Noise amplification [I, derived]. The second difference a_t = (p_{t+1} − 2p_t + p_{t−1})/Δt², with i.i.d. noise σ,
has standard deviation √6·σ/Δt². At 20 fps (Δt 0.05 s):
- σ = 1 cm gives **9.8 m/s² ≈ 1 g**;
- σ = 3 mm gives 0.3 g;
- σ = 3° of rotation noise gives about 51 rad/s² of angular acceleration.

So raw finite differences of perception make the "required wrench" as large as the weight. A physics test on raw poses
would flag nearly every frame. Our 2–3 cm errors are mostly low-frequency bias, which does not enter the acceleration.
The frame-to-frame jitter is what matters, and it is unmeasured: Stage 0 measures it first (§6).

| strategy | used by | settings | notes |
|---|---|---|---|
| Smooth, then differentiate | TactoHand (Gaussian, σ_p 0.075 s, σ_R 0.15 s, intrinsic rotation mean); Xie (Butterworth on the inputs); our `pipeline/task_wrench.py` (Savitzky–Golay, window 9 frames = 0.45 s, cubic) | fixed | simple; it blurs grasp and release onsets and impacts (a placement is a short spike) |
| **Optimise positions; v and a are finite differences of the optimised positions** | Kolev & Todorov; Li 2019 (collocation, backward differences); our benchmark | the pose prior's weight 1/σ_pose sets how far the fit may move | the physics residual is the smoother. No separate filter; the residual is exact and no lag is introduced |
| Spline parameterisation | Xie (cubic Hermite, optimised knot times); Grasp-and-Lift (keyframes every 5 frames); Mordatch (splines) | knots every 0.1–0.25 s | fewer variables. Accelerations are piecewise linear; the knot spacing limits impact timing |
| Explicit acceleration / jerk penalty | Li 2019; Xie | weight relative to pose prior | needed even with physics on free hand points (they have no dynamics) |
| Robust loss on perception | Li 2019 (Huber); Kolev (e^{r²} barrier-like) | — | for tracking outliers (identity swaps, occlusion jumps) |

Recommendation [I]: use joint optimisation, with poses as the variables and finite differences inside the residual.
- A Huber pose prior.
- A small acceleration penalty on the hand points only.
- Pre-smoothing only for Stage 0's diagnostic, with the TactoHand σ values (0.075 s / 0.15 s), equal to 1.5 / 3
  frames at 20 fps.

## 3. Does a physics-consistent reference make RL easier? (Q3)

| evidence | what was compared | result | caveats |
|---|---|---|---|
| SPIDER v3 §4.2.1 [L-repo: `docs/research/work/26/verify/verdicts.json`, `port-recipes-2026-10-21.md`] | PPO on the SPIDER reference vs the kinematic reference; 7 seeds, 4,096 envs, arm + 22-DoF hand, cup grasp | task progress **0.99 ± 0.01 vs 0.07 ± 0.11** | one task; the kinematic reference "lets the cup drift out of the hand" (gross artefact); SPIDER controls also initialise the policy (confound). Not in v1/v2 |
| SPIDER v2 §4.2, Fig. 10 [L] ([html](https://arxiv.org/html/2511.09484v2)) | humanoid pick-and-place (OMOMO), residual PPO on SPIDER vs on human motion | "converged faster, … better object tracking"; on the human motion "the robot fails to grasp the object" | curves only |
| Do as I Do Table 3 [L-repo: `physics-solver.md` §2] | open-loop success on in-the-wild reconstructions | 0.25 (SPIDER sampling) → 0.66 (+ warm-up) → 0.71 (all additions) | open loop, not RL |
| Grasp-and-Lift [L] | physics-in-the-loop refinement vs ManipTrans (RL) | replay success 71.7 vs 45.9 %, 3.6× faster | no RL on top |
| TactoHand [L] | physics supervision on/off | rollout error 5.7 → 3.3 cm | short horizon (0.4 s), not RL |
| PHUMA (arXiv [2510.26236](https://arxiv.org/abs/2510.26236)) [L-abs] | humanoid tracking policies trained on physics-filtered + physics-constrained retargeted data vs Humanoid-X / AMASS | PHUMA policies better | curation and retargeting not isolated |
| Our own [L-repo: README, `physics-solver.md`] | grasp-lock reference, zero action vs after RL | zero action loses the ep12 cup at f37 (0.600); RL reaches 0.885 AUC | RL repairs a physically inconsistent reference, at ~70M steps per episode |

Reading [I]:
- The positive evidence is for references made feasible **in the simulator that later trains the policy** (SPIDER, Do
  as I Do).
- An idealised fit (rigid Coulomb contacts, no actuator limits) is a necessary condition, not a sufficient one. The
  Sharpa's soft fingers (kp 1.7) and FlashCHORD's condim-3 contacts can still lose an object the fit says can be held.
- The fit's value for us is therefore upstream. It removes what we measured as the failure causes:
  - grips that are not geometrically there (ep12: thumb–finger opposition 148° → −86° within 12 frames);
  - fingertips 0.2–1.8 cm outside the held object;
  - lid–pot overlap;
  - boards floating 2–4 cm above the table.
- It also hands `grasp_force.py` the contact points and the normal forces each hold needs.
- **[H-fit-RL]** (open): a physics-consistent reference shortens or improves RL. It is falsified if, under the frozen
  recipe, the GPU AUC vs mocap of fit references is not ≥ +0.03 above base references on ≥ 2 of 4 episodes. This needs
  the owner's go-ahead; it is only worth running after the CPU test in §6.4 passes.

## 4. Practical recipe (Q4)

### 4.1 Tools that install from PyPI (this container, Python 3.13) [M]

| package | wheel | use |
|---|---|---|
| scipy 1.18.1 | yes | `least_squares` (trf, `jac_sparsity`, bounds), `linprog` (HiGHS) |
| casadi 3.8.2 | yes (abi3 manylinux_2_28); **bundles IPOPT** (EPL) + MUMPS. A test NLP solved | exact sparse derivatives by automatic differentiation; NLP with bounds and inequalities, so complementarity can be a relaxed constraint φλ ≤ ε |
| cyipopt 1.7.0 | **no binary wheel** (sdist only; needs a system Ipopt) | skip |
| jax 0.12.0.1 | yes | `jacfwd` with sparsity colouring, or Gauss-Newton by hand |
| osqp 1.1.3, clarabel 0.11.1 | yes | Stage 0 per-frame QP/LP; TactoHand's sequence QP |
| mujoco 3.17.0 | yes; `mj_inverse`, `mjd_inverseFD` present | a Kolev & Todorov-style residual on MuJoCo soft contacts (v2 option, §6.5) |

### 4.2 Variables, residuals and weights (v1)

Per frame t, per object o and per hand h. The units make every residual dimensionless with weight 1/σ.

| block | variables | residual | σ (start values) [E] |
|---|---|---|---|
| object pose | δp_o (3), δr_o (3, rotation vector, right-multiplied on the perceived pose) | pose prior (Huber) | 1.0 cm, 3°: perception's jitter scale, not its bias. Set from Stage 0's measured jitter |
| hand points | δx_c (3) for each contact candidate (5 fingertip pads, 3 palm points) | prior to the perceived keypoint (+ pad offset 6–9 mm along the inward normal) | 1.5 cm (hands are noisier than objects) |
| hand smoothness | — | second difference of x_c | 0.5 m/s² equivalent |
| forces | pyramid weights λ_{c,k} ≥ 0, k = 1..4 (bounds) | small L2 (regulariser, ~0.03 per unit of m·g) | — |
| Newton–Euler | — | Σ_c Σ_k λ_{c,k} e_{c,k} + m g − m a_o (3) and the moment equation (3); a, α from finite differences of the optimised poses | 5 % of m·g; 5 mN·m |
| complementarity | — | λ_c,n · max(gap_c, 0), with the force gated to 0 when gap > d_max (2 cm) | 2 mm × 1 N |
| penetration | — | min(gap, 0) for tip–object, object–table and object–object | 1 mm |
| object–object | λ for each closest-point pair between convex pieces, applied ± to both bodies | in both objects' Newton–Euler | as forces |

- **Contact candidates.**
  - Fingertip pads: MediaPipe 4/8/12/16/20, offset toward the object.
  - Palm: the centroid of 0/5/17 and two points along 5–17, offset along the palm normal.
  - Table: the object's hull vertices within 1 cm of the plane from `table_frame.npz` at rest frames, plus the 4–8
    lowest hull vertices, refreshed per outer iteration.
  - Object–object: closest points between CoACD pieces (`make_assets.py --pieces`) within 1 cm, refreshed per outer
    iteration (an active-set fixed point).
  - Precompute a signed-distance grid per mesh (2 mm voxels) and interpolate trilinearly to get gaps and normals.
- **Friction.** A 4-edge pyramid at μ = 1.0: the same cone family as FlashCHORD (pyramidal, condim 3).
  - Report the margin at a design μ of 0.5–0.7 (note 24: μ/√2 worst case, safety factor 1.5).
  - **No torsional friction terms**: condim 3 has none. Contact patches are several point contacts.
- **Contact phases.** Fixed from GT-free labels: refine.py's hold/rest labels, or `manip_segments`/grasp-lock holds,
  as Li 2019 does with its CNN contact states. The gate lets forces exist only for candidates allowed in that phase.
  - v1 does not discover new contact modes. A mode-discovery pass (Mordatch-style continuation) is v2.
- **Complementarity relaxation.** Penalty form, with continuation of the weight ×10 over 2–3 outer solves.
  - With CasADi/IPOPT the alternative is the Posa-style relaxed constraint λ_n·gap ≤ ε, with ε going 1e-2 → 1e-4 N·m.
  - Start with the penalty: it never makes the problem infeasible.

### 4.3 Runtime: synthetic benchmark [M] and estimates [E]

Script: `docs/research/physics-2026-10-30/physics_fit_bench.py` (md5 `ac6f32db`). Copied from the scratchpad run
`bench/fit_bench.py`.
- Command: `optvenv/bin/python -I fit_bench.py 300 1`.
- Machine: this cloud container, 4 CPUs; scipy 1.18.1 `least_squares` (trf, lsmr, finite-difference Jacobian with
  sparsity colouring).
- Problem: one 0.2 kg box; rest on a table (f0–99), carried by 5 fingertip contacts (f100–199), put back (f200–299).
  - 42 variables per frame: 6 pose + 5 × 4 fingertip + 4 × 4 table pyramid weights; 12,600 variables and 18,288
    residuals.
  - Perceived pose = truth + i.i.d. 1 cm / 3° noise; fingertips + 5 mm noise.

| result | value |
|---|---|
| wall time per object | **104 s**, stopped at the 200-evaluation cap (status 0, not converged) |
| median object position error vs synthetic truth | 1.53 → 0.81 cm (i.i.d. noise, so mostly the smoothing effect; real bias would not shrink this way) |
| median force residual while carried | 3.49 N (raw finite differences; weight 1.96 N) → 0.27 N |

Estimates for a real episode (300 frames, 2 objects, 2 hands, object–object pairs) [E]:
- With the finite-difference Jacobian: about 2.5× the variables, so ~5–10 min per episode.
- With exact sparse derivatives (CasADi, JAX, or hand-written): ~10–60 s per object, 1–3 min per episode.
- Stage 0 (per-frame LP, ~50 variables): < 1 ms per frame with HiGHS or OSQP, about 1 s per episode.
- The 20 public episodes on this container: about 1 h with finite differences, or minutes with exact derivatives.
  No GPU is needed.

## 5. Pitfalls (Q5)

1. **Mass and force scale.** With only hand and table contacts, the Newton–Euler equations and the cones are
   homogeneous in m [I, derived]:
   - scaling m → km and I → kI (same density field) scales every force by k;
   - a cone is a cone, so **feasibility does not depend on the mass**;
   - Hu 2022 says the same ("mass only a relative value").

   Mass matters only through:
   - force or effort limits (finger effort 10 N·m, the wrist's 150 N);
   - the **mass ratio** between objects in contact (lid on pot);
   - the simulator's soft-contact penetration.

   So use the plausible masses of `props_public_scans.json` for reporting and the force design, and never fit mass.
   Video cannot identify it.
2. **Internal (squeeze) forces are not identifiable.** Statics fixes the net wrench; the grip's null-space squeeze is
   free.
   - A minimum-norm solution gives the minimum grip, which is too light for soft contacts and PD fingers (note 24:
     "minimal-force squeezes from the contact-force LP: too light").
   - Pham 2018 needed a learned prior.
   - Set a normal-force floor (preload) per active contact plus a 30–50 % safety margin (Johansson & Westling 1984;
     note 24 §5).
3. **Torsional friction.** FlashCHORD runs condim 3, so no torsion. A fit that relies on torsion (one pad holding a
   handle against roll) yields grasps the simulator cannot hold. Model point contacts only; the cup or spoon roll is
   resisted by force couples (note 24 rule 5). Do as I Do plans with condim 6, one reason its plans do not transfer
   (`physics-solver.md` §3.2).
4. **Table and support.**
   - The table plane comes from `table_frame.npz`, refit by mkref on frame 0.
   - The sim's support is a finite disc (the ep24 audit found it off-centre). Supports outside the sim's prim are
     unusable, so clip the candidates to the sim support.
   - Resting objects that float 1–3 cm above the plane are a low-frequency perception bias that physics *does* fix: an
     unsupported object at rest must come down onto the plane. This is the one place the fit should move an object by
     cm. Cap the drop at a few cm and log it.
5. **Object–object contacts** (cup in rack, lid on pot, boards stacked).
   - Newton's third law couples the two objects' equations, so solve them **jointly**.
   - A rack that never moves can be a fixed environment body, like the table.
   - Use the collision pieces the simulator uses, not the render mesh: the 30 Oct study traced the ep2 lid loss to
     lid–pot collision-shape overlap.
   - Non-convex nesting (lid seat, rack slot) needs the CoACD pieces. Closest-point pairs change discontinuously, so
     refresh the active set between solves, not inside one.
6. **COM and inertia identifiability.**
   - Without measured forces, the COM enters only the moment balance. The contact forces that balance it are themselves
     unknown, so the COM is essentially unidentifiable from video [I].
   - Kolev & Todorov identify intrinsic parameters only from contact-free motion; our episodes have no free flight.
   - Fix COM and inertia from the mesh (shell centroid: median 8.3 mm vs the scans [L-repo]). A 1 cm COM error is
     about 0.02 N·m on a 0.2 kg object, which the fingers absorb.
   - Report sensitivity (fit with ±1 cm COM) instead of fitting it.
   - The 30 Oct chaos result (a 2 mm COM nudge changes zero-action outcomes) is about the simulator's open-loop
     instability, not about the fit.
7. **Bias vs jitter.** The fit removes high-frequency inconsistency and contact-geometry errors. It cannot detect a
   smooth 2–3 cm offset of a carried object: the physics is satisfied either way.
   - Do not expect mocap ADD-AUC to rise much: MPJPE improved by 1–13 mm (Li) and 5.5 mm (Xie).
   - The test (§6.4) guards against loss and measures the downstream effect instead.
8. **Contact events.** Grasp, release and placement make forces jump. Turn force smoothness off across phase
   boundaries, and let the impact frame keep a larger Newton–Euler residual (robust loss). Otherwise the fit smears the
   placement over many frames.
9. **Which side moves.** Objects are better observed than hands (0.89 AUC vs noisier keypoints), so give the hands the
   looser prior. Object-first is the opposite of Real2Sim-in-HOI's human-first choice, which suits full bodies.
10. **Ground-truth hygiene.**
    - The fit reads only perception outputs, meshes and properties.
    - σ start values may be set from *public* development statistics. This is development, not inference: it is
      allowed and must be documented.
    - Eval episodes run with frozen settings.

## 6. Recommended v1 design

### 6.1 Placement
`pipeline/physfit.py`, a perception-refinement stage after `refine.py`, with the same contract.
- **Reads** `poses_world_vo.npz` / `poses.npz`, `hands_refined.npz`, `table_frame.npz`, mesh library + collision
  pieces, `props_public_scans.json` (or plausible properties for generated meshes) and the GT-free hold/rest labels.
- **Writes** the same keys, plus:
  - `physfit.json`: per object and phase, the violations before and after, the moves, the solver log, the code version;
  - `physfit_aux.npz`: per-frame contact forces, gaps, unexplained wrench, and refined hand contact points.
- It reuses refine.py's `assert_inference_input()`, so it refuses any ground-truth path.

### 6.2 Stage 0: inverse feasibility diagnostic (owner's question, ~1 s per episode)
- For each object and frame:
  - smooth the kinematics (σ 0.075 s / 0.15 s);
  - compute w_req = [m(a − g); Iα + ω×Iω] about the COM;
  - solve the LP: min ‖s‖₁ s.t. Σ G_c λ_c + s = w_req, λ ≥ 0, with the candidate set of §4.2 (gaps < 2 cm) and an
    optional preload.
- Output: the **unexplained wrench** |s| per frame (N and N·m, also as a fraction of m·g), its cause class, and the
  jitter of the raw poses (§2).
- Cause classes:
  - no candidate contact;
  - cone violated (needs pull or more friction);
  - moment unbalanced (grip too narrow).
- This is the first deliverable. It says, per episode, *where and why* the perceived scene is not physically
  possible.

### 6.3 Stage 1: trajectory fit
- Variables, residuals and weights as in §4.2. Contact phases are fixed from the labels.
- Solver path:
  - scipy `least_squares` with the FD sparse Jacobian first (working code exists: `physics_fit_bench.py`);
  - then exact derivatives through CasADi (IPOPT, or its Gauss-Newton) once the residuals are settled.
- Order of work:
  1. one object with table and hand on ep12 (cup);
  2. then ep2 (pot + lid: object–object);
  3. then ep18 and ep24 (tools, boards sliding on the table).
- Outputs feed mkref unchanged. The forces per contact and phase go to `grasp_force.py` (Δq = Jᵀf/kp squeeze design,
  with the preload of pitfall 2).

### 6.4 Falsification test (pre-register before running; public episodes only; GT read only by `score_registered.py` after inference)
1. **Synthetic recovery** (unit test, before real data). Recover a known trajectory and contact forces from a perturbed
   one, as in `physics_fit_bench.py` but run to convergence:
   - force residual while carried < 10 % of m·g;
   - table forces > 0 only at rest frames.
   Failing this means a bug, not a finding.
2. **Self-consistency.** On the 20 public episodes, the Stage 0 unexplained wrench on the fitted output falls by
   ≥ 80 % in median over hold frames. Expected to pass, since the fit optimises it; it is a check, not evidence.
3. **No perception loss.**
   - Mean registered ADD-AUC vs mocap over the 20 public episodes ≥ input − 0.005.
   - No episode loses > 0.02.
   - Otherwise falsified: the fit damages poses.
4. **Downstream (the real test) [H-fit-ref].**
   - The frozen grasp-lock + ILC recipe on fit outputs vs on refine outputs, for ep2/12/18/24 (CPU, S1 physics).
   - Score: `jitter_check.py` with ≥ 8 jittered copies. Single replays are chaotic (`physics-solver.md` §4).
   - **Pass:** jittered zero-action sim_vs_ref improves by ≥ +0.03 on ≥ 2 of 4 episodes, and no episode drops by
     > 0.05.
   - Otherwise [H-fit-ref] is falsified: the idealised physical consistency does not survive into FlashCHORD at zero
     action. Then only the force design (§6.3) and RL arms remain.
5. Only after (3) and (4) pass: GPU RL arms for [H-fit-RL] (§3), with the owner's go-ahead and a cost estimate first.

### 6.5 Deliberately not in v1
- **Mass, COM or friction fitting** (pitfalls 1, 6).
- **Contact-mode discovery.**
- **Finger joint angles as variables**: v1 moves contact points; IK to the Sharpa stays in mkref and grasp_lock.
- **The MuJoCo inverse-dynamics residual.** Kolev & Todorov's form: build an MJCF of objects + table + fingertip
  spheres, minimise `qfrc_inverse` on the objects' free joints, and get Jacobians from `mjd_inverseFD`.
  - It has the same soft-contact family as the evaluator, so it is a strong **v2** candidate or an independent check of
    v1.
  - It is not the v1 core: soft-contact forces exist only with penetration or a margin, which makes the fit induce
    millimetre penetrations, and mesh–mesh contacts make it non-smooth.

## Sources
- Posa, Cantu, Tedrake 2014: https://posa.seas.upenn.edu/assets/pdf/Posa2014.pdf ;
  https://dspace.mit.edu/handle/1721.1/90907
- Mordatch, Popović, Todorov 2012: https://homes.cs.washington.edu/~todorov/papers/MordatchSCA12.pdf
- Kolev & Todorov 2015: https://roboti.us/lab/papers/KolevHumanoids15.pdf
- MuJoCo computation docs: https://mujoco.readthedocs.io/en/stable/computation/index.html ;
  API: https://mujoco.readthedocs.io/en/stable/APIreference/APIfunctions.html
- Li et al. 2019: https://arxiv.org/abs/1904.02683 ; https://www.di.ens.fr/willow/research/motionforcesfromvideo/
- Xie et al. 2021: https://arxiv.org/abs/2109.09913
- Rempe et al. 2020: https://arxiv.org/abs/2007.11678
- Fox 2024 (residual reduction comparison): https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11061640/
- Pham et al. 2018: https://doi.org/10.1109/TPAMI.2017.2759736 ; https://hal.archives-ouvertes.fr/hal-01356138 ;
  CVPR 2015: https://openaccess.thecvf.com/content_cvpr_2015/papers/Pham_Towards_Force_Sensing_2015_CVPR_paper.pdf
- Hu et al. 2022: https://arxiv.org/abs/2209.10833
- Kumar et al. 2021: https://arxiv.org/abs/2105.08196
- TactoHand 2026: https://arxiv.org/abs/2610.39585
- Grasp-and-Lift 2026: https://arxiv.org/abs/2601.18121
- Real2Sim in HOI 2026: https://arxiv.org/abs/2605.14462
- Garcia-Hernando et al. 2020: https://arxiv.org/abs/2008.03285
- SPIDER: https://arxiv.org/abs/2511.09484 (v2 html read today; v3 numbers from
  `docs/research/work/26/verify/verdicts.json`)
- PHUMA: https://arxiv.org/abs/2510.26236
