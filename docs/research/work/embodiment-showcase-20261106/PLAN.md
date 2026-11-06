# Multi-embodiment showcase: one head-camera video, many trained robots (plan, 6 Nov 2026)

**Status: PROPOSAL.** Nothing has been rented or built. The owner decides (section 9).
Labels: [M] measured, [E] estimate, [H] hypothesis, [V] read in code or data today, [R] recalled from the
literature (to be checked before it goes on a slide).

The challenge is over, so its rules no longer bind us. The working rules in `CLAUDE.md` still apply: record every run,
announce spending first, and label shortcuts.

## 1. What the audience sees

- **One grid video per task.**
  - Left: the real head-camera video.
  - Right: a 3 × 3 grid. Each tile shows a different robot doing the same task in physics simulation.
  - All tiles use the same camera and the same clock. Each tile has a label (robot name, fingers, joints) and a small
    live badge: object error against motion capture, in cm, and pass or fail.
- **An ego-view tile for the main ("hero") task.** The simulation is rendered from the person's head-camera path, so
  the robot hands appear where the human hands were.
- **A slide deck with the product story:**
  - the steps: video → task description → robot adapter → trained policy;
  - one results table: each robot's accuracy against the real world, its pass rate and its training cost.

**The claim we can defend:** every tile is a closed-loop policy. It was trained with reinforcement learning (RL) in
physics from one video, with no teleoperation. It runs with the training help switched off: no virtual object
controller (VOC 0), as the official evaluator ran. A tile that does not meet this is labelled.

## 2. Episodes

We use public episodes only. They have motion-capture ground truth, so we can score every robot against what really
happened, with the kit's own metric. We also have the official object scans for them, so the simulation can use the
best meshes. This shortcut is allowed now.

| Pick | Episode | What happens | Why this one | Measured so far (Sharpa hands) |
|---|---|---|---|---|
| **Hero** | ep27 Pan_In_Dishrack | the pot is lifted by its handle and set into the dish rack | clear one-hand pick-and-place into a fixture; any gripper can hold the handle | sim vs mocap AUC 0.965–0.967, MPPE 0.9 cm, pot alone 0.930 [M]; grasp-lock recipe 0.949 [M] |
| 2 | ep2 Pot_with_lid | the lid comes off the pot and goes back on | precise placement, two objects | sim vs mocap 0.925–0.926, SP / MP success 1.0 [M] |
| 3 | ep18 Dust_Brush | sweeping with the mini brush into the dust pan, two hands | two-handed tool use, the most human-looking task | 0.957 ± 0.002 with the grasp-lock recipe [M]; the standard-learner variants of 31 Oct got only 0.60–0.62 [M], so the recipe matters here |
| Stretch | ep22 (or ep21) Water_Can_Blue_Cup | water is poured from the pitcher into the blue cup | pouring is the most impressive task | twin ep21 scored 0.66 because our pitcher mesh lacked half its base and the pitcher fell over [M]; with the official scan this should go away [H] |
| Reserve | ep12 Cup_In_Dish_Rack, ep39 Dustpan_Solo | cup flipped into the rack; dust pan moved | known good | ep12 0.89–0.91, ep39 0.958 [M] |

We already have references for these episodes in the HF store, for example `runs/20261023-glockpub-0f7e3a7/refs/`. Each
reference has the robot-independent "loaded" stage: perceived hand keypoints, object tracks and object-surface contacts.
Every other robot can be retargeted from it.

## 3. The robots

The simulator NVIDIA gave us (FlashCHORD, at our evaluator pin) already ships three robots that can be trained with RL
[V `configs/embodiment/`]:

- **Sharpa Wave**: two floating hands;
- **Dexmate Vega**: a wheeled humanoid upper body, with 7-joint arms and Sharpa hands;
- **Unitree G1**: a humanoid with two Dex3 three-finger hands.

NVIDIA's repository also has retargeters from human hands to Sharpa, Dex3 and Vega
(`scripts/retarget/ego_recon_to_dexmate_sharpa.py`, `taco_to_dex3.py`) [V]. Open-source models and retarget configs
cover the rest:

- **dex-retargeting** (MIT licence) has ready configs for Shadow, Allegro, LEAP, Inspire, Ability, Schunk SVH and the
  Panda gripper [V].
- **dex-urdf** adds Barrett and D'Claw [V].
- **MuJoCo Menagerie** has Shadow DEX-EE (three fingers), Robotiq 2F-85, the UMI gripper, G1, Franka and others [V].

| # | Tile | Type | Fingers / joints per hand | Source | Work needed |
|---|---|---|---|---|---|
| 1 | Sharpa Wave | human-like | 5 / 22 | native | none; baseline, already trained on these tasks |
| 2 | Shadow Hand | human-like research hand | 5 / 24 | dex-urdf, Menagerie | add as a floating hand; ready retarget config |
| 3 | Inspire RH56 | low-cost humanoid hand | 5 / 6 motors, 12 joints, coupled | dex-urdf | add; coupled joints are a risk |
| 4 | Allegro | 4-finger | 4 / 16 | dex-urdf, Menagerie | add; ready config |
| 5 | LEAP Hand | low-cost 4-finger | 4 / 16 | dex-urdf, Menagerie | add; ready config |
| 6 | Unitree Dex3-1 | 3-finger | 3 / 7 | native (G1's hand) | take the floating hand from the G1 model; NVIDIA's MANO → Dex3 IK |
| 7 | Shadow DEX-EE (or Barrett BH8) | 3-finger | 3 / 12 (Barrett: 3 / 4 coupled) | Menagerie (dex-urdf) | add; write a thumb/index/middle retarget config |
| 8 | Parallel gripper (Franka Hand; Robotiq 2F-85 as an option) | 2-finger | 2 / 1–2 | dex-urdf (Menagerie) | add; ready Panda config; grasp from the thumb–index pinch axis |
| 9 | Unitree G1 humanoid + Dex3 | whole-body humanoid | 3 / 7 | native | whole-body reference by IK: pelvis from the head-camera path, arms to the wrists; floating base (no balance) |
| opt. | Dexmate Vega | wheeled humanoid | 5 / 22 | native + NVIDIA's ego-video retargeter | format conversion only |
| opt. | Our 22-joint capsule human hand ("digital human") | human | 5 / 22 | ours, built 30 Oct (`pipeline/human_hand.py`) | none; it already trained [M], 0.161 below Sharpa |

Every floating-hand robot comes as a left and right pair, so the two-handed ep18 works for all of them, including two
grippers.

## 4. How each robot learns the task

The task layer is robot-independent. It is the object's 6-DoF path, the contact patches on the object surface, and the
human hand motion as a hint. The main RL reward (object keypoints, weight 20; our FDR object point-match) only asks
the object to move as it did in the video, so it does not change between robots. Per robot:

1. **Retarget** the perceived hand keypoints to the robot.
   - Hands: dex-retargeting's vector optimiser.
   - Gripper: wrist pose plus the pinch axis and opening.
   - G1: whole-body IK.

   This writes the `robot_*` columns, one reference per robot. MANO contact parts are mapped to the nearest robot
   links for the contact reward.
2. **Grasp search per robot**, with our evolutionary grasp search (64 candidates × 4 jittered copies, 20 generations)
   on that robot's geometry. Copying a human grasp onto a 3-finger hand or a gripper does not work, so the grasp is
   searched, not copied.
3. **RL.** The grasp-lock recipe comes first (70M steps, about 1.1 h and $1.6 per policy [M]). Where it fails the
   bar, the standard FlashSAC learner runs 250M steps (about $2–5 [E]). Hand-imitation reward terms are down-weighted
   for non-human hands.
4. **Evaluate** 5 fresh draws with no assistance and score them against mocap with the kit metric.

**Pass bar per tile, fixed before any rental:** on at least 3 of 5 draws, every object stays within the kit's MP-SR
limits (3 cm, 30°) against mocap. The video shows the median draw. If we use the best draw instead, the slide says
"best of 5".

Prior evidence that object-centric RL with a decaying object-assist force transfers across hands:

- DexMachina (NVIDIA / Stanford, 2025): six dexterous hands from ARCTIC human demonstrations [R];
- SPIDER (FAIR / CMU, 2026): nine embodiments (our note 05 [V]);
- ManipTrans (CVPR 2025): residual RL for two-handed transfer [R].

## 5. Shortcuts (allowed now; every one is labelled on its slide)

- **Official public scans as simulation meshes.** We do not use the meshes we reconstructed for the challenge.
- **Floating hands for most tiles.** This is standard in dexterous-hand research. The G1 has a floating base and no
  balance.
- **The searched grasp** replaces the copied human grasp for grippers and 3-finger hands.
- **Mocap object paths ("oracle reference") are a diagnostic only.** I recommend not putting them in the video,
  because the product is video → policy. If a hero tile needs one, its label says "mocap reference".
- **Best-of-N draw for the video.** Disclosed on the slide.

## 6. Phases, gates and cost

| Phase | What | Where | Cost [E] | Gate to continue |
|---|---|---|---|---|
| 0 | Build: preview strips of the candidate episodes for your approval; a generic `FloatingHands` embodiment class in FlashCHORD (palm, finger and fingertip frames, contact links, gains, limits) plus a config per robot; retargeting from the loaded stage; grasp-search and reward changes for any hand; a kinematic preview video per (robot, episode); a short zero-action physics replay on CPU to catch import errors | this cloud session, CPU (FlashCHORD runs on CPU here; done before, work log line 950) | $0; about 1–2 days of agent work | you approve the previews; at least 7 of 9 robots look right (drop or replace the rest) |
| 1 | Hero smoke run: ep27 × all robots on 3–5 RTX PRO 6000 boxes, two trainings per GPU | Vast | $15–25 | at least 6 tiles pass the bar; you see the first grid video |
| 2 | Scale: ep2 and ep18 (ep22 if you want the stretch) × the surviving robots, retrains for failures, 5 draws each | Vast | $50–90 (+ about $25 for ep22) | — |
| 3 | Visuals and deck: FlashCHORD renders from a fixed side camera and from the ego camera; optional Blender "beauty pass" from the recorded body poses (better materials and shadows, same trajectories); grid composer (ffmpeg, extending `tools/sim_vs_real_video.py`); slides | CPU, optional GPU render | $5–20 | — |

- **Total:** about $110–130 central, range $70–200 [E].
- **Agent time:** about 4–5 days [E].
- **Per-policy cost:** the $1.6 glock figure is measured. The standard learner's $2–5 is an estimate.
- **Machines:** every box destroys itself when its job ends. Results go to the HF store `runs/<run_id>/`; summaries
  and scores go to git.

## 7. Risks and expected outcomes [E]

- **5- and 4-finger hands on the pot and lid:** likely pass. Sharpa is at 0.93–0.97.
- **3-finger hands:** the pot handle and lid are likely fine; the brush is uncertain.
- **Parallel gripper:** fine on the pot handle and lid. The two-gripper sweep (ep18) is the weakest cell. We show it
  honestly or swap it for ep39.
- **G1 humanoid:** the highest risk. The person leans and reaches across the table, and the G1 has joint and reach
  limits. Plan one extra day for it.
- **Inspire:** coupled joints need mimic constraints in the simulator. The fallback is independent joints with a soft
  coupling penalty.
- **FlashCHORD generality:** the action space and the contact reward must read the finger count from the layout. G1's
  7-joint Dex3 hands already train in FlashCHORD, which suggests they do. Checked in phase 0.
- **Licences:** dex-retargeting is MIT. Each robot model has its own licence (mostly Apache-2.0, BSD or MIT). Check
  before any public release. An internal proof of concept is fine.

## 8. Product framing for the deck

- One video gives a robot-independent task description: the object paths, the contact map and the hand motion.
- Adding a robot means one model file, one retarget config and gains, then about 1 GPU-hour per task.
- The table shows the measured cost per policy and the accuracy against the real world, per robot.
- The failures slide is honest: which robot and task pairs fail, and why.

## 9. Decisions for the owner

1. **Episodes:** hero ep27, plus ep2 and ep18; ep22 pouring as a stretch?
2. **Robots:** the 9 tiles above, plus optional Vega and the digital human? Is there a specific robot you want?
3. **Bar:** every tile is a trained policy that runs without help, and fallbacks are labelled? (recommended)
4. **Visual level:** FlashCHORD renders only (free), or a Blender beauty pass as well (+$10–20, +1 day)? Recommended:
   the beauty pass for the hero task only.
5. **Spending:** phase 0 now ($0). Phase 1 (about $15–25) when phase 0 passes. Phase 2 (about $50–90) after you
   have seen the hero video.
