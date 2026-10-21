# V2D Track 3: who the top two teams are, and what the literature offers

Research date: 2026-10-21. This is a read-only research note; no repository files were changed.
Labels used throughout:
- **[F]** fact taken from a primary source, with its link.
- **[I]** inference or hypothesis (mine), with the experiment that would falsify it where possible.
- **[M]** a number measured in a source (leaderboard JSON, paper table). Paper numbers are the authors' claims; I have not reproduced them.

---

## 0. Corrections to the brief

1. **[F] The two homepages in the brief probably belong to different people with the same names.**
   - **Zihan Gao at www.zihangao.com** is a 5th-year PhD candidate in Information Science at UW-Madison. Their work is on HCI, LLM "localness" and geographic bias, with no robotics. **[F]** Kaggle user `zihangao2001`, on the leaderboard team SoySauceChicken, lists **organization "Duke University"** and GitHub `Papaercold`.
   - **Zihao Guo at zihao-guo.github.io** is an Institut Polytechnique de Paris PhD in operations research and transport. His own site links his Kaggle account `zeio99guo` (display name "Zeio", Nantes, France, GitHub `zeio99`). **[F]** The leaderboard row "Zihao Guo" is Kaggle user **`hideinpoopoo`**, a separate account with no organisation listed.
   - **[I]** Both are therefore very likely name collisions. For Zihao Guo the confidence is medium-high: someone could hold two Kaggle accounts, but nothing links them.
2. **[F/M] The leaderboard has moved again** (`leaderboard.json`, `generated_at` 2026-10-21 15:25 UTC, source Kaggle; https://raw.githubusercontent.com/MVerghese/v2d-leaderboard-data/main/leaderboard.json):

| Rank | Team (Kaggle members) | AUC | SP-SR | MP-SR | RPE cm | MPPE cm | CD-O cm | Subs | Last |
|---|---|---|---|---|---|---|---|---|---|
| 1 | SoySauceChicken (`zeraol` = Danyang Yan, `zihangao2001` = Zihan Gao) | **0.848** | 0.85 | 0.75 | 2.80 | **2.13** | **0.065** | 4 | 10-21 05:03 |
| 2 | Zihao Guo (`hideinpoopoo`) | 0.831 | **0.95** | 0.75 | **2.10** | 3.51 | 0.313 | 3 | 10-20 23:58 |
| 3 | SRL (`kyounginbaik`) | 0.694 | 0.80 | 0.45 | 5.18 | 5.13 | 0.239 | 3 | 10-21 14:14 |

   Earlier snapshots, from this repository's `docs/work-log.md` and `STATUS.md` **[M]**:
   - **SoySauceChicken:**
     - 10-06: 0.649 / SP 0.35 / MP 0.25
     - 10-12: 0.765 / SP 0.80 / MP 0.50 / CD-O 0.583
     - 10-21 00:55: 0.823 / CD-O 0.065
     - 10-21 05:03: 0.848
   - **Zihao Guo:**
     - 10-12: 0.229
     - by 10-21: 0.831, with only 3 submissions in total.

   **[F]** Kaggle badge timestamps add some timing:
   - `zihangao2001` made a first community-competition submission on 2026-10-06; the account was created that day.
   - `hideinpoopoo` made a first submission on 2026-10-11; the account dates from 2022-12.
   - `zeraol` made a first submission on 2026-10-19.
   - **[I]** Danyang Yan's account first submitted on 10-19. Between the 10-12 and 10-21 snapshots, SoySauceChicken's CD-O fell from 0.583 to 0.065. One possible reading: Yan joined late and brought a mesh or geometry change. The evidence is weak; a team can submit from either account.

---

## 1. People: facts found

### 1a. Zihan Gao, www.zihangao.com (UW-Madison). Not the competitor.
- **[F]** 5th-year PhD in Information Science, UW-Madison, advised by **Jacob Thebault-Spieker** (MadCollab). B.S. in Information Science and Psychology from Peking University (with Pengyi Zhang). On the 2026 job market.
- **[F]** Papers, all HCI or NLP:
  - "Is Your Chatbot a Tourist or a Townie?" (CSCW 2026, Method Recognition Award)
  - "The Labor of Language" (FAccT 2026)
  - PlaceWeave (CHI 2026)
  - LocalBench (AAAI 2026; arXiv 2511.10459; code github.com/MadCollab/LocalBench)
  - Collective Narrative Grounding (NeurIPS 2025 workshop)
  - Two CSCW 2025 items
  - "A Turing Test for Localness" (arXiv 2505.07282)
  - Two CSCW 2024 papers
  - CIKM 2021
  - ASIS&T 2021
- **[F]** None of this concerns hand-object interaction, robotics, 3D reconstruction or RL.

### 1b. Zihao "Eric" Guo, zihao-guo.github.io (IP Paris). Almost certainly not the competitor.
- **[F]** PhD student or pre-doc at Institut Polytechnique de Paris, 2023–2026, supervised by **Andrea Araldo** and **Mounîm El Yacoubi** (Télécom SudParis). Also a research scientist on contract at IMT.
- **[F]** Topic: optimization under uncertainty for transport networks, using column generation, DRL, GNNs and LLM-based heuristic discovery.
- **[F]** Earlier work and training:
  - Internships: Huawei (3D point cloud plus wireless-channel contrastive learning, 2025), EMBL-EBI (phylogenetics), IFP Energies nouvelles, Tencent.
  - Degrees: Centrale Nantes / Nantes Université; mechanical-engineering B.Eng.
- **[F]** Publications:
  - arXiv 2608.11405 (predict-then-optimize transit redesign)
  - LION 2025
  - TRB 2025 / TRR
  - Nature Methods co-author (phylogenetics)
  - Biomimetics
  - ACM EITCE 2022
- **[F]** No robotics, HOI, retargeting or pose tracking.

### 1c. The actual SoySauceChicken members
**Zihan Gao (Kaggle `zihangao2001`, GitHub `Papaercold`)**
- **[F]** Kaggle profile: organization "Duke University", pronouns he/him, account created 2026-10-06, active in 6 competitions (the six Track-3 metric competitions).
- **[F]** Public repositories (https://github.com/Papaercold):
  - `KuroKun_Biped_Robot`: a fully 3D-printed 8-servo biped. Locomotion was trained in **NVIDIA Isaac Sim** with **sim-to-real** transfer, and the robot model ships as URDF and USD. This was a **Duke University "Robot Studio" course project, Spring 2026**.
  - `dl685`: a class repository; **[I]** probably Duke ECE 685, deep learning.
  - `RoboticsJobInterview`: a robotics interview knowledge base.
  - `AnimeMaster`: a web app.
- **[I]** He is probably a Duke master's student in robotics or ECE, born around 2001 judging by the handle, with Isaac Sim RL and sim-to-real experience.
- **Possible but unconfirmed identity link: [F] a robotics "Zihan Gao" at Tsinghua (`gaozihanthu@gmail.com`, group of Haoqian Wang, Tsinghua Shenzhen International Graduate School)** has written directly relevant papers:
  - **RoboWheel** (arXiv 2512.02729, Dec 2025, co-first author; work done during an internship at Synapath; project page https://zhangyuhong01.github.io/Robowheel). A data engine for HOI video to cross-embodiment robot data.
  - **DexCast: Learning Real-World Dexterous Control from Human Videos** (arXiv 2610.14691, 2026-10-10, first author; affiliation Tsinghua).
  - **M²-VLA** (arXiv 2604.24182, co-author).

  **[I]** Nothing links `Papaercold`/Duke to `gaozihanthu`/Tsinghua. A Tsinghua affiliation in Oct 2026 and Duke coursework in Spring 2026 point to two different people, unless the Tsinghua affiliation reflects earlier work. A third "Zihan Gao" (Xidian University, Licheng Jiao group) wrote NeRF / 3D-segmentation papers (arXiv 2407.01220, 2406.04961). Treat the Tsinghua link as a possibility, not a finding.

**Danyang Yan (Kaggle `zeraol`)**
- **[F]** First author of **"Robot Learning to Communicate through Projected Visual Abstractions"** (arXiv 2607.22434, Jul 2026; Danyang Yan, Boyuan Wang, Jiaxun Liu, **Boyuan Chen**; Duke ECE / MEMS / CS; project page generalroboticslab.com/shadow). Methods:
  - A **21-DoF dexterous hand** with soft skin.
  - A **differentiable self-model** learned from random "motor babbling" in simulation.
  - **Gradient-based search** over hand configurations.
  - A second **collision-aware search inside a physics simulator** to make the poses feasible.
  - **Temporal-smoothness regularisation** and **keyframe-based optimisation** for imitating videos.
- **[F]** Kaggle account created 2025-11-07; no organisation listed. A GitHub user `danyangyan` has repositories `fingerdance` (Jupyter, Sep 2025) and `TensorTonic-Solutions`. **[I]** "fingerdance" plausibly relates to the hand-shadow work. I could not open the repository: the session's GitHub access is restricted.

### 1d. The leaderboard "Zihao Guo" (Kaggle `hideinpoopoo`): unidentified
- **[F]** Single-member team. Kaggle account since 2022-12-16, with a "Python Coder" notebook badge from 2024-09 and no profile details.
- **[F]** arXiv lists several robotics-adjacent authors named Zihao Guo. **None is confirmed:**
  - **King's College London (Yali Du group):** JAX multi-agent RL (SocialJax 2503.14576; OpenSocialJax 2610.13710); safe hierarchical MARL with G. Loianno (2606.24010). Strong RL-infrastructure profile.
  - **Manchester Metropolitan University:** co-author of "Dense-Jump Flow Matching … for Robotic Policies" (2509.13574).
  - **Xi'an Jiaotong (Jihua Zhu group):** point-cloud PEFT and Mamba work (2605.03438, 2607.29048).
- **[I]** The only way to identify this team is the technical report or code they must release for prize eligibility, or the CoRL 2026 tutorial.

---

## 2. Supervisors' and labs' research lines

### Boyuan Chen, Duke General Robotics Lab (Danyang Yan's lab) **[F]**
Main lines: robot self-modelling, new robot and hand morphologies, humanoids, sim-to-real, and learning from video. Relevant papers from 2024 to 2026:
- **CoDance** (2610.05324): learns reactive human–humanoid interaction **from a single video**. Motions are retargeted to a robot reference, and a "multi-link compliance augmentation" turns kinematic demonstrations into force-aware training data.
- **Online Sim-to-Real Adaptation via Closed-Loop System Modeling (OSRAM)** (2609.28878): adapts the *reference commands* sent to a fixed policy, using a learned closed-loop model.
- **Temporal Self-Imitation Learning** (2606.19752): mines fast successful rollouts during RL and replays them as self-imitation targets. Tested on 30 long-horizon tasks.
- **Time as a Control Dimension in Robot Learning** (2511.07654): adds remaining-time and time-ratio inputs to RL policies.
- **Sym2Real** (2509.15412): residual learning on symbolic dynamics. **RAFL** (2603.22039): residual acceleration fields for soft-robot sim-to-real.
- **The Cartesian Hand** (2609.25696): two parallel grippers plus linear fingertips for in-hand manipulation.
- **CEER / CEER2** (2605.19981, 2609.38709, with Xianyi Cheng): compliant end-effector and root control for humanoid loco-manipulation. **Duke Humanoid** (2409.19795).
- **SonicSense** (2406.17932): object perception from in-hand acoustic vibration. **WildFusion** (2409.19904): implicit 3-D reconstruction.
- Also at Duke: **Xianyi Cheng** (contact-rich manipulation; e.g. CoPRE 2609.27381). No link to the team was found.

### Haoqian Wang, Tsinghua SIGS (relevant only if the Tsinghua Zihan Gao is the competitor) **[F]**
3-D human and hand perception and data engines: Motion-X / Motion-X++ (2501.05098), whole-body mesh recovery (OSX 2303.16160), GUAVA Gaussian avatars, stereo category-level object pose (2407.06984). Since 2025 also robot learning from human video: RoboWheel, DexCast, M²-VLA.

**RoboWheel pipeline [F]** (arXiv 2512.02729, §3):
- **Hand estimation:** HaMeR for hand-only clips; Motion-X++ SMPL-H for whole-body clips.
- **Depth:** UniDepthV2, or the camera's RGB-D.
- **Object mesh:** Hunyuan3D 2.0, rescaled by the ratio of bounding-box diagonals against the depth point cloud.
- **Object tracking:** FoundationPose on that mesh. **Camera:** DROID-SLAM.
- **Penetration fix:** TSDF penalties, optimising the palm and then the wrist pose to remove penetration.
- **Physics refinement:** a **ManipTrans-style residual RL policy**. Its reward combines geometric tracking, velocity tracking and contact force.
- **Retargeting:** to grippers, dexterous hands and humanoids.
- **Gripper mapping:** a kNN gesture classifier chooses between palm-frame (whole hand) and index–thumb-chord (fingertip) end-effector frames. **Open/closed state** comes from CoTracker keypoint displacement on the object: stationary means open, moving means closed.
- **Arm IK:** cuRobo GPU IK for 5 arms in Isaac Sim, with Qwen2.5-VL as success judge.

**DexCast [F]** (2610.14691):
- RoboWheel reconstruction plus ManipTrans residual RL produces the demonstrations.
- Augmentation: object pose shifted within 20×20 cm and ±60°.
- Policy: a SIM(3)-equivariant point-cloud diffusion policy with a skeleton-graph VAE motion prior (DMPM), pretrained on 5M HOI frames.
- Hardware: UR5 with XHAND.
- Deployment perception: Hunyuan3D mesh plus FoundationPose.

### Not relevant to this problem
Jacob Thebault-Spieker (UW-Madison: HCI, geographic bias). Andrea Araldo and Mounîm El Yacoubi (Télécom SudParis: transport optimization, pattern recognition).

---

## 3. Literature we may be missing

The repository notes already cover SPIDER, ManipTrans, DexMachina, DexTrack, REGRIND, C2Dex, CORN, SAM 3D, BundleSDF and others (`docs/research/notes/`). Items marked **NEW** below do not appear there by name.

### 3A. The organisers' own method
- **[F] CHORD**: "Learning Dexterous Manipulation Using Contact Wrench Guidance From Human Demonstration", arXiv **2607.00033**, NVIDIA.
  - Authors include **Mrinal Verghese**, who owns the leaderboard repository, plus Bowen Wen, Zhengyi Luo, Linxi Fan and Yuke Zhu.
  - **[F]** The challenge page says Track-3 metrics AUC, SP-SR, MP-SR and MPPE are "as defined in the CHORD manuscript".
  - **[M]** 82.12% success on 1,831 benchmark tasks.

### 3B. RL tracking and retargeting, closest to our setup (Sharpa Wave, FlashSAC)
- **NEW, highest priority. FlashDexRetarget** (arXiv **2610.01849**, KAIST AI and Holiday Robotics, the FlashSAC authors). **Code: https://github.com/Holiday-Robot/FlashDexRetarget** (Isaac Lab 2.3, `rsl_rl_flashsac`, ships **Sharpa Wave** and XHAND USDs).
  - **[F]** One FlashSAC policy is trained jointly over many references.
  - **[M]** On a 50-motion TACO/OakInk2/HOT3D benchmark with Sharpa Wave: SR_SPIDER **86%**, versus **Do as I Do 64%** and **CHORD 50%**. On XHand it uses about 30 GPU-hours, versus about 3,000 for CHORD. Sharpa needed 400M environment steps.
  - **[F] Design choices, each ablated in the paper:**
    1. A **K=10 future-reference encoder**: a 128-d latent, expressed in the wrist frame.
    2. **Object reward from corresponding surface points.** 128 points are normalised to radius 0.058 m, so 30° of rotation is about 3 cm of displacement. The reward is the **mean of the 3 largest point errors**, `exp(-e/0.1 m)`. This is an ADD-like unit, close to our scoring metric.
    3. **One-sided fingertip-distance reward** `max(0, d_robot − d_ref)`, using unsigned reference distances and `σ = 1 cm`. The robot can close reconstruction gaps without reproducing penetrations, and no binary contact threshold is needed.
    4. **Separate actor-critic pairs for left and right hands**; each sees the full observation but has its own reward.
    5. **Observations:** SDF fingertip and wrist distances plus normals, from a 128³ grid over a 60 cm cube; object points at the current and reference poses.
    6. **Success criteria:** **SR_SPIDER** is 10 cm / 0.5 rad, averaged over active hands. **SR_MT** (ManipTrans) is 3 cm / 30° plus fingertip and wrist thresholds.
- **ManipTrans** (2503.21860, CVPR 2025; code github.com/ManipTrans/ManipTrans). A pretrained hand imitator plus a per-task residual; the source of the MP-SR criterion.
- **DexMachina** (2505.24853; code github.com/MandiZhao/dexmachina). The virtual-object-controller curriculum we already use.
- **DexTrack** (2502.09614, ICLR 2025; code github.com/Meowuu7/DexTrack). A neural tracker trained with a data flywheel and **homotopy optimisation** for hard references.
- **ObjDex** (2411.04005). A high-level wrist-trajectory generator conditioned on object goals, plus a low-level RL finger controller.
- **Human2Sim2Robot** (2504.12609; code github.com/tylerlum/human2sim2robot). Uses only the **object pose trajectory** as an embodiment-agnostic reward and the **pre-manipulation hand pose** to initialise RL. Arm plus hand. Covers grasping, non-prehensile and multi-step tasks.
- **NEW. Gen2Dex** (2610.24392). Residual RL with a **backward curriculum and a cache of physically valid reset states**, to fix imperfect video-derived references. Directly relevant to long-horizon hard episodes.
- **NEW. OATH** (2610.14379). An object-agnostic residual policy whose observation is a **per-link contact-error vector to target points on the object surface**. **[M]** 0.4 s of compute per second of reference; 54–58% success on DexYCB.
- **NEW. Contact-anchored retargeting plus residual RL** (2609.24093; **code github.com/DexGEM-Lab/real2sim2real**). Retargets the *contact structure* (which finger regions touch which object locations) rather than joint angles. One shared residual policy. **[M]** Dual-hand success rises from 16% to 62%.
- **NEW. Morphometric Imitation** (2609.28660; Malik and Tomlin groups). Contact-preserving kinematic retargeting across hand morphologies, then residual RL. **[M]** On a **Sharpa** hand: 89.3% zero-shot real-world success over 300 trials.
- **NEW. DexSynRefine** (2605.05925): task-space residual RL. **EgoCPT** (2610.17572): contact-aware iterative optimisation from noisy egocentric hand poses. **ADEPT** (2608.19182, NVIDIA): pre-training plus post-training RL on Flexiv-Sharpa.
- **REGRIND** (2607.11874; Haozhi Qi and Preston Culbertson). A minimal residual-RL recipe tracking **object keypoints**; scissors and screwdriver tool use. Already in our notes.

### 3C. Sampling-based MPC and trajectory optimisation ("sampling-based MPC for dexterous retargeting")
- **SPIDER** (2511.09484; **code github.com/facebookresearch/spider**). Annealed sampling with **temporary virtual contact forces** guiding toward the demonstrated contacts. Covers 9 embodiments and 3 simulators. The output can be replayed open-loop or used as a **feasible reference for RL**.
- **NEW. Do as I Do** (2606.19333, Malik group; **code github.com/malik-group/do-as-i-do**). Built on SPIDER, targeting **Sharpa Wave** (real hardware: dual UR3e with Sharpa).
  - Reconstruction: SAM3 → **SAM 3D Objects** mesh (Fast-SAM3D fork) → MoGe pointmaps → **HaWoR** world-frame hands → TAPIR → guided-diffusion object tracking.
  - Retargeting: clean and gravity-align → CoACD convex decomposition → MJCF scene (with a "UR3 wrist cylinder") → mink IK → **sampling-based MPC in MuJoCo Warp** (`launch.py --robot-type sharpa`).
  - **[I]** MuJoCo Warp is the challenge's simulator family, so this is the most directly portable optimiser for our hard episodes.
- **NEW. DexForge** (2610.06331). A differentiable simulator with spherical-Gaussian objects; contact-aware kinematic retargeting plus force-aware dynamics retargeting. **[M]** Object orientation error falls 71–78%.
- Infrastructure: **Judo** (2506.17184), predictive sampling (MJPC, 2212.00541), DROP (online dexterous planning).

### 3D. Kinematic retargeting that preserves interaction (better references than fingertip IK)
- **NEW. DexOAK** (2610.26762; Katzschmann and Schmid). An interaction-graph Laplacian over the joint hand–object graph, amortised by a network with contact, non-penetration and self-collision fine-tuning.
  - **[M]** It raises downstream **ADD-AUC from 62.7% to 77.9% on ARCTIC** (Inspire hand) **by improving only the kinematic reference**.
- **OmniRetarget** (2509.26633). The interaction-mesh Laplacian idea, for humanoids.
- **C2Dex** (2608.07045). Stable object-side contacts aggregated in the canonical object frame. Already in our notes.
- **Lakshmipathy et al.**, "Kinematic motion retargeting for contact-rich anthropomorphic manipulations", ACM TOG 2025.

### 3E. Pipelines from egocentric or monocular video to robot hands
- **NEW. EgoMatrix** (2610.18822) and **OmniHOI** (2610.10855), both from Yao Mu's group.
  - EgoMatrix reconstructs egocentric HOI "with emphasis on relative geometry and contact rather than exact metric scene recovery", then retargets and refines with RL. **[M]** 54.8% versus 14.5% end-to-end success in simulation.
  - OmniHOI corrects each stage with stage-specific evidence (image, contact geometry, physics-in-the-loop). **[M]** 53% success on 60 monocular clips versus 28%.
- **NEW. Hand2Robot** (2610.15769). For object tracking it picks a **globally consistent trajectory from per-frame pose candidates**, using observation confidence plus temporal constraints. Hand refinement is object-local.
- **NEW. DexAgent** (2609.35318; Li Fei-Fei and Jiajun Wu). An agentic Human2Sim2Robot pipeline:
  - **VLM-driven semantic understanding of the video**, property-specific simulation reconstruction, trajectory optimisation and verifiers.
  - A self-growing tool library with articulated and deformable support.
  - Starts from a single egocentric video.
- **RoboWheel / DexCast** (see §2). **DexMan** (2510.08475): humanoid, contact-based rewards for noisy video poses. **ViViDex** (2404.15709). **DexMV** (2108.05877). **HOP** (2409.08273).

### 3F. Detecting manipulation type and primitives from video
- **[F]** RoboWheel: a **kNN gesture classifier** (palm-dominant versus fingertip-dominant) chooses the retargeting frame, and **CoTracker object keypoint motion** gives grasp/release timing. This follows Kjellström, Romero and Kragić, IROS 2008 (grasp recognition for human-to-robot mapping).
- **[F]** DexAgent: a VLM classifies object properties and task phases, then selects stage tools and verifiers.
- **[F]** HACMan++ (2407.08585): spatially grounded motion primitives (grasp, push, place) chosen by RL.

### 3G. Non-prehensile pre-grasp (the thin-board episode)
- **Learning to Grasp the Ungraspable with Emergent Extrinsic Dexterity** (Zhou and Held, arXiv **2211.01500**, CoRL 2022). RL learns to **push a thin object against a wall or edge, rotate it, and then grasp**.
- **HACMan** (2305.03942). **CORN** (2403.10760). **DexDiff** (2409.05493), extrinsic dexterity for ungraspable objects.

### 3H. Grasp synthesis on reconstructed meshes
- BODex (2412.16490). **Dexonomy** (2504.18829, all grasp types in a taxonomy).
- DexGrasp Anything (2503.08257). **HUGS** (2607.04554, human-prior-guided, across modes and scales).
- For parallel grippers: **GraspGen** (2507.13097, NVIDIA).

### 3I. Gripper and arm–hand embodiments for imitating object trajectories
- RoboWheel: gripper retargeting with the open/close rule above, executed on a UR5.
- **Phantom** (2503.00779). **Point Policy** (2502.20391).
- Human2Sim2Robot and Do as I Do: arm plus hand.
- DexCast: UR5 with XHAND.
- ADEPT: Flexiv with Sharpa.

### 3J. Write-ups about the V2D challenge
- **[F]** Challenge page (https://nvidia-isaac.github.io/video_to_data/v2d_challenge/):
  - Winners are announced at a **CoRL 2026 tutorial**.
  - Prize eligibility requires a final submission, **a code release and a short technical report**.
  - Awardees become core authors of a post-challenge report.
  - Track 3 is "method-agnostic … reconstruct-then-retarget or end-to-end VLA/WAM".
- **[F]** NVIDIA's `video_to_data` v0.4.0 contains FlashCHORD (per the README of zjifan121-source/NVIDIA_V2D_Egocentric).
- **[F]** No write-up from a top team was found.
- **[F]** Public Track-3 repositories from low-ranked teams show nothing new:
  - civicW/v2d-challenge-asap (ASAP, AUC 0.23)
  - tianny0078/v2d-track3 (Tony, 0.22: WiLoR hands, TSDF and SAM3D meshes, Sharpa IK, CHORD wrench references, hollow-cup colliders)
  - zjifan121-source/NVIDIA_V2D_Egocentric (CMU/PSC)
  - shehiin/v2d
  - furqazaheervi6/v2d-challenge
  - Thatspacegirl/egony
  - Punyajain-cmd (a Track 1 repository)

---

## 4. Hypotheses about each competitor's approach, and what to borrow (all [I])

### SoySauceChicken (Duke: Zihan Gao and Danyang Yan)
Facts they rest on: Isaac Sim RL and sim-to-real coursework; Duke GRL's dexterous-hand, self-model and optimisation work; **best CD-O by far, 0.065 cm** (about 0.65 mm Chamfer); best MPPE (2.13 cm); 4 submissions; steady climb since 10-06.

1. **H-S1: they run NVIDIA's default stack** (FlashCHORD, floating Sharpa Wave hands) and gain mainly through perception and geometry.
   - Support: their first submission (0.649) came out on 10-06 and they improved gradually with few submissions, which fits iterating on a working baseline rather than a new embodiment.
   - Falsifier: their technical report or code. Separately, a rerun of our own baseline perception with FlashCHORD defaults on public episodes, to see whether about 0.65 is the "baseline" level.
2. **H-S2: their meshes are near-exact, either reused public scans of recurring objects or retrieval of matching CAD/scan assets.**
   - CD-O fell from 0.583 to 0.065 between 10-12 and 10-21. That is better than any reconstruction we have seen (our damaged-scan test shows even 3 mm noise costs much), so it is unlikely to come from TSDF or SAM 3D alone.
   - The official scorer ICP-registers submitted meshes to hidden scans, so exact meshes also lift AUC, MPPE and RPE (our STATUS: "Mesh quality is now first-order").
   - Falsifier: compare our CD-O when submitting public-scan meshes for the eval "twin" objects. This needs the rules answer we already asked v2d_challenge@nvidia.com about.
3. **H-S3: kinematic retargeting is optimisation-based and collision-aware with temporal smoothness and keyframes** (Danyang Yan's toolkit), possibly the DexMachina-style curriculum the baseline provides.
4. **H-S4 (only if the Tsinghua Zihan Gao is this person):** a RoboWheel-like front end (HaMeR/HaWoR, depth-scaled generated mesh plus FoundationPose, TSDF penetration fix), then a ManipTrans-style residual RL refinement. That would put their strength in **physical plausibility of the reference before RL**.

**Borrow:** a pre-RL HOI plausibility pass, with SDF penetration removal on the wrist and palm and object-relative contact preservation (RoboWheel §3.2, DexOAK). This targets their MPPE advantage.

### Zihao Guo (`hideinpoopoo`, unidentified)
Facts: **best SP-SR (0.95 = 19/20 episodes)** and **best RPE (2.10 cm)**; CD-O 0.313 (reconstructed meshes, not exact); jumped from 0.229 to 0.831 within about 9 days and 3 submissions.

1. **H-G1: their policies succeed (10 cm / 0.5 rad) even on the tool-use and thin-board episodes**, which our policies fail. 19 of 20 SPIDER successes implies that.
   - Candidate mechanisms:
     - (a) A stiffer or stronger embodiment or controller: a fixed-base arm with hand, or high-gain wrist tracking. The FAQ allows this.
     - (b) An object-centric reward that dominates hand tracking (Human2Sim2Robot, FlashDexRetarget point reward).
     - (c) References produced by a physics optimiser (SPIDER / Do as I Do in MuJoCo Warp) before RL.
   - Falsifier: per-episode results are not public. Proxy test: on our public twins of the hard episodes, run (b) and (c) and check whether SP rises toward 1 without hurting the easy episodes.
2. **H-G2: their low RPE but higher MPPE suggests temporally smooth, correctly shaped motion with an absolute offset.** That pattern fits a reconstruction or anchoring offset (CD-O 0.313 cm) rather than policy failure.
3. **H-G3: a large single jump with only 3 submissions suggests offline validation on public episodes** and probably an existing RL code base. If the KCL Zihao Guo is this person, a JAX/RL-infrastructure background would fit well with multi-reference or massively parallel training. Not confirmed.

**Borrow:**
- Make object tracking the dominant reward with ADD-like point errors (FlashDexRetarget top-3 point error).
- Generate physically feasible references for the hard episodes with SPIDER / Do as I Do sampling MPC before RL.

---

## 5. Most actionable takeaways (ranked; all hypotheses until tested)

1. **Port FlashDexRetarget's reward and observation design into our FlashCHORD/FlashSAC runs. [H]**
   - The pieces: top-3 surface-point object reward in ADD units, the one-sided fingertip-distance reward, the K=10 future-reference encoder, and per-hand actor-critic.
   - It is released code for the *same hand and the same RL algorithm*. It reports CHORD at 50% versus its own 86% on Sharpa Wave.
   - Falsifying experiment: on the hard public twins (sweeper with dustpan; board), equal 250M-step budget, compare ADD-AUC against the current reward.
   - Also test *multi-reference* training across all 20 eval plus public references derived from our own perception (no ground truth).
2. **Run SPIDER / Do as I Do sampling-MPC (MuJoCo Warp, `--robot-type sharpa`) on the hard episodes. [H]**
   - Use the result as a physically feasible reference, or a BC/initial-state source, for RL (SPIDER §: "serve as feasible reference motion for efficient RL").
   - Falsifier: SP and ADD-AUC on hard public twins with versus without MPC references.
3. **Improve kinematic references before RL. [H]**
   - Interaction-graph Laplacian (DexOAK, OmniRetarget) or contact-anchored retargeting (DexGEM code) in place of plain E2S fingertip IK.
   - DexOAK's ARCTIC ADD-AUC rose 62.7% → 77.9% from references alone.
4. **Hard long-horizon episodes: backward curriculum plus a cache of valid reset states (Gen2Dex). [H]**
   - For the thin board, adopt extrinsic-dexterity shaping: slide to the edge, then lift (Zhou and Held 2211.01500).
   - Consider a phase-aware embodiment change (fixed-base arm and hand, or a stiffer wrist variant) where the FAQ allows it. Confirm with the owner and organisers first.
5. **Phase detection:** use RoboWheel's object-keypoint-motion rule (CoTracker) to time grasp and release and to split references into phases. It is cheap, and it suits the sweeper and board episodes.
6. **Geometry:** SoySauceChicken's CD-O (0.065 cm) is the clearest measured gap.
   - Settle the public-scan rules question with the organisers.
   - Otherwise follow Do as I Do: SAM 3D Objects, MoGe and guided-diffusion tracking.
7. **Competitor identity:** both homepages in the brief are very likely the wrong people.
   - SoySauceChicken is a Duke team: a Duke student with Isaac Sim sim-to-real experience, plus a Duke General Robotics Lab dexterous-hand researcher.
   - "Zihao Guo" is unidentified. Their code and technical report become public only for prize eligibility.

---

## Sources (primary)
- Leaderboard JSON: https://raw.githubusercontent.com/MVerghese/v2d-leaderboard-data/main/leaderboard.json
- Kaggle profiles (via the Kaggle `users.ProfileService/GetProfile` endpoint): kaggle.com/zihangao2001, kaggle.com/zeraol, kaggle.com/hideinpoopoo, kaggle.com/zeio99guo
- https://www.zihangao.com/ ; https://zihao-guo.github.io/pages/aboutME.html ; https://zihao-guo.github.io/pages/project.html
- https://github.com/Papaercold (KuroKun_Biped_Robot README)
- Challenge page: https://nvidia-isaac.github.io/video_to_data/v2d_challenge/
- arXiv abstracts and HTML:
  - People and teams: 2607.22434, 2610.14691, 2512.02729, 2604.24182, 2606.24010, 2509.13574, 2610.13710
  - RL tracking and retargeting: 2607.00033 (CHORD), 2610.01849 (FlashDexRetarget), 2604.04539 (FlashSAC), 2503.21860, 2505.24853, 2502.09614, 2411.04005, 2504.12609, 2610.24392, 2610.14379, 2609.24093, 2609.28660, 2605.05925, 2610.17572, 2608.19182, 2607.11874
  - Sampling MPC and kinematic retargeting: 2511.09484, 2606.19333, 2610.06331, 2610.26762, 2509.26633, 2608.07045
  - Video pipelines: 2610.18822, 2610.10855, 2610.15769, 2609.35318, 2510.08475, 2404.15709, 2108.05877, 2409.08273
  - Non-prehensile and grasp synthesis: 2211.01500, 2305.03942, 2407.08585, 2403.10760, 2409.05493, 2412.16490, 2504.18829, 2503.08257, 2607.04554, 2507.13097
  - Perception and gripper imitation: 2511.16624, 2503.00779, 2502.20391
- Code:
  - https://github.com/Holiday-Robot/FlashDexRetarget ; https://github.com/Holiday-Robot/FlashSAC ; https://github.com/Holiday-Robot/rsl_rl_flashsac
  - https://github.com/facebookresearch/spider ; https://github.com/malik-group/do-as-i-do
  - https://github.com/ManipTrans/ManipTrans ; https://github.com/MandiZhao/dexmachina ; https://github.com/tylerlum/human2sim2robot
  - https://github.com/Meowuu7/DexTrack ; https://github.com/DexGEM-Lab/real2sim2real
- Duke GRL papers: 2610.05324, 2609.28878, 2606.19752, 2511.07654, 2609.25696, 2509.15412, 2603.22039
