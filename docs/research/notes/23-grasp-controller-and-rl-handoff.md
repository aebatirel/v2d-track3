# 23. Non-RL grasp controller, written into the reference, then RL fine-tuning (2026-10-23)

Owner (10:00 UTC): "can't we translate what we've done into a FlashCHORD policy and fine-tune it with RL? Research a grasp
controller." Two literature agents plus code checks. R = reported (source), I = inferred, V = verified in our code.

## Facts that shape the design
- V The policy acts as a residual on the reference (`configs/action/residual_hand_pose.yaml`: wrist 0.05 gain / 0.2 m
  clip, 0.15 / 1.0 rad, fingers 0.15 / 1.0 rad, EMA 0.3). Zero action = PD tracking of the reference's
  `robot_*_wrist_position/_wxyz/_finger_joints`, which are ours. So "translating a controller into the policy" = writing
  its PD targets into the reference; a near-zero actor then reproduces it.
- V Measured today (`tools/hand_object_gap.py`): zero action brings the right fingers to 1.5–3.3 cm of the spoon at the
  grasp, wrist within 1–3 cm, but nothing grips; the spoon stays on the table.
- V `configs/collision/training.yaml`: `robot_support_collision: false` → the hands pass through the table (the
  checkpoint's saved config, so also at evaluation). Fingers can wrap under a flat spoon handle.
- V (note 14) soft wrist kp 25 N/m: a held 0.3 kg placeholder object sags the wrist ≈ mg/kp = 11.8 cm unless the
  reference / residual lifts it (12 of the 20 cm residual clip).
- I The reference finger targets sit at or outside the surface → almost no normal force. Finger kp ≈ 1.7 N·m/rad:
  ~3 N at a 5 cm lever needs the target ≈ 0.09 rad past contact. Not yet checked: contact condim (no torsional friction
  at condim 3 → a two-finger pinch on a long spoon pivots; needs ≥ 3 spread contacts or palm contact).

## Grasp controllers (agent 1)
- R Squeeze targets: DexGraspNet moves touching links along the contact normal as PD targets; BODex executes a pre-grasp
  1 cm off the surface and a squeeze target x_s = 2x − x_p; SpringGrasp drives fingertips with impedance springs to
  points inside the object (84 % real, 78 % without pre-grasp). All tested on static grasps, not long trajectories.
- R Sampling trajectory optimisation from human demos:
  - SPIDER (CC BY-NC): ADD-AUC 11.0 kinematic → 48.8 → 56.9 with contact guidance (OakInk); 0.4 frames/s with guidance
    on an L40S; Sharpa is its weakest hand (44.5 vs 66–68); open-loop, valid near the start.
  - Do as I Do (arXiv 2606.19333, MIT code with a Sharpa model): success 25 → 71 % in the wild; 1024 samples × 32 iters.
  - OmniHOI (2610.10855): CMA-ES keyframe offsets, Sharpa success 89 % vs SPIDER 19 % in their benchmark; 19 min per
    trajectory on a 4090; their wrist is welded and finger kp 500 (much stiffer than ours); no code found.
  - EgoEngine (2606.12604): on egocentric video, MPC unreliable for grasp stages (0.20 vs RL 0.90).
- R Grasp synthesis (DexGraspNet, BODex, Dexonomy, FRoGGeR, Grasp'D): static grasps, no Sharpa model; BODex filters
  flat objects and fails more on thin ones. Thin-object strategies in the literature (slide to edge, pivot) need
  hand–table contact, which our physics turns off.

## Handing a controller to RL (agent 2)
- R The pattern works with PPO: SPIDER reference → task progress 0.99 ± 0.01 vs 0.07 ± 0.11 kinematic (7 seeds);
  DexTrack re-bases the reference on the optimised actions; InterMimic distils teacher rollouts into the reference
  and resets from simulated states (resets in imperfect reference states cause "contact floating" failures);
  ManipTrans zero-initialises the residual and terminates when the demo grasps firmly but sim contact force is zero.
  No study found with SAC.
- R Off-policy dip comes from the critic: Residual Policy Learning zeroes the residual's last layer and still dips
  until a critic burn-in (actor frozen until critic loss < β); AWAC: BC-pretrained SAC dips to scratch level; WSRL:
  warm-up rollouts from the frozen policy prevent divergence; RLPD: 50/50 demo/online batches + LayerNorm critic;
  Jacta: a fixed 25 % planner-demo share beat pure RL; Policy Decorator: bound the residual, ramp it in.
- R DAgger distillation alone often fails on contact-rich tasks (InterMimic needed DAgger → PPO); not first choice.

## Plan (I), gated on the VOC-fixed rehearsal (seed 42 ≈ 11:10 UTC)
1. **Reference repair = grasp controller in the reference (≈ 1–2 days, GPU ≈ $1–5 for all episodes):** remove the PD
   lag (iterative correction over zero-action replays); in held frames push finger targets 3–8 mm into the object
   along a flexion synergy, wrap under thin parts (table is not collidable); add wrist feed-forward +mg/kp. Keep the
   achieved states (not the squeezed targets) for resets. Develop and tune on PUBLIC episodes (ep24 thin boards, ep12,
   ep18); apply the frozen rule to the eval spoon episodes and check only with sim_vs_ref (no ground truth).
   Gate E0: zero-action replay, many worlds with noise: the object lifts ≥ 5 cm and is held ≥ 1 s in ≥ 3/5 seeds and
   zero-action sim_vs_ref clearly above the floor.
2. **If 1 is not enough: sampling refinement in FlashCHORD's own env** (Do-as-I-Do / OmniHOI style, our perceived object
   trajectory only, contact-gap and opposing-force terms, robust over friction/mass), ≈ 15–20 GPU-min per episode
   (estimate), 3–5 days of work.
3. **RL fine-tune:** zero the actor mean's last layer, critic burn-in with the actor frozen, lower initial finger
   noise, 25–50 % controller rollouts in each batch, resets from simulated controller states, checkpoint 0 as a
   fallback; A/B whether VOC is still needed. E1: ep35 2 seeds ≈ $4.
