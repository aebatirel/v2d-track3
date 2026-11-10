# Pitch-deck assets: what we have (as of 10 Nov 2026)

Product: one egocentric (head-camera) video → a trainable robot policy, for many robot embodiments.
Everything below exists today. Labels: [M] measured, [E] estimate. "Physics" means a closed-loop policy trained
with RL and run in simulation with no assistance (VOC 0, as the official evaluator runs). "Kinematic / no physics"
means an animation of a reference; never present one of these as a result.

**Where the files are:**
- **Bundle** (all files below, ready to drop into slides): `pitch_assets_ep27.zip` (55 MB).
  - Sent in chat.
  - HF store: `showcase/outputs/20261106/pitch_assets_ep27.zip`.
  - The folder paths in this document are paths inside the bundle.
- **Repo** (stills, tables, code): `docs/research/work/embodiment-showcase-20261106/`, branch `claude/charming-goldberg-glc1xi`.
- **HF store** (private dataset `aebatirel/v2d-store`):
  - grid videos and tiles: `showcase/outputs/20261106/ep27/`;
  - raw run outputs: `runs/20261106-sc{A,B,C,D,E}-*`.

---

## 1. Hero videos (lead slide)

| File (bundle) | What it shows | Specs | Suggested caption |
|---|---|---|---|
| `videos/01_hero_side_9robots.mp4` | Real head-camera clip (left) next to 9 robot hands (3×3), all doing the same task: lift the pot by its handle, flip it, set it upside-down on the dish rack. Each tile shows the robot name, fingers / joints and its score vs motion capture. | 1920×1080, 20 fps, 12.3 s, H.264, 4.0 MB | "One video in. Nine robots out. Each tile is a separate policy trained in physics from the same 12-second clip." |
| `videos/02_hero_headcam_9robots.mp4` | The same 9 physics rollouts, each rendered from the person's own head-camera path. Every robot holds the pot where the real hand did, in the same view as the footage. | 1920×1080, 20 fps, 12.3 s, 7.1 MB | "Same viewpoint, different bodies: the robot takes the human's place." |
| `videos/03_real_input_ep27.mp4` | The input: NVIDIA V2D Track 3 public episode 27, colour camera (ego_cam_a), re-encoded. | 1280×960, 20 fps, 12.3 s | "The only input: a head-mounted camera recording." |

Stills at three key moments (PNG, 1920×1080):
- `stills/hero_side_{grasp,flip,place}.png`;
- `stills/hero_headcam_{grasp,flip,place}.png`;
- the matching input frames `stills/real_input_{grasp,flip,place}.png`.

## 2. Per-robot clips (one slide per robot family, or a custom layout)

`videos/tiles_side/<robot>.mp4` (side camera) and `videos/tiles_headcam/<robot>.mp4` (head-camera path): 772×680,
20 fps, 12.35 s, physics rollouts with no labels.

| Robot | Type | Fingers / joints per hand | AUC vs mocap, 5 runs [M] | Runs within 3 cm [M] |
|---|---|---|---|---|
| Unitree Dex3-1 (`dex3`) | 3-finger humanoid hand | 3 / 7 | 0.982 ± 0.005 | 5/5 |
| Shadow Hand (`shadow`) | 5-finger research hand | 5 / 22 | 0.977 ± 0.003 | 5/5 |
| Allegro Hand (`allegro`) | 4-finger | 4 / 16 | 0.975 ± 0.002 | 5/5 |
| Inspire RH56 (`inspire`) | 5-finger, low-cost humanoid hand | 5 / 12 | 0.973 ± 0.006 | 5/5 |
| LEAP Hand (`leap`) | 4-finger, low-cost | 4 / 16 | 0.970 ± 0.005 | 5/5 |
| Barrett BH8 (`barrett`) | 3-finger industrial | 3 / 8 | 0.969 ± 0.006 | 5/5 |
| Sharpa Wave (`sharpa`) | 5-finger (NVIDIA's challenge hand) | 5 / 22 | 0.966 ± 0.006 | 5/5 |
| D'Claw (`dclaw`) | 3-finger claw | 3 / 9 | 0.958 ± 0.008 | 5/5 |
| Franka gripper + rubber pads (`franka_pads`) | 2-finger parallel gripper | 2 / 2 | 0.947 ± 0.011 | 5/5 |
| Franka gripper, before the fix (`tiles_side/franka_FAILED_before_fix.mp4`) | 2-finger | 2 / 2 | 0.648 ± 0.066 | 0/5 |

**How to read the numbers:**
- AUC is the challenge kit's object-tracking score: 1.0 means within 1 cm all the time; 0 means 9 cm or more off.
- Ceiling: the reference every robot was asked to follow, i.e. our perception of the video, scores 0.997 vs mocap.
- Floor: leaving the objects where they are scores 0.560.
- Source: `data/ep27_results_table.md` (repo: `results/ep27_results_table.md`).

## 3. "What we fixed" slide

| File | What it shows |
|---|---|
| `videos/04_franka_before_after.mp4` (1544×680, 12.35 s) and `stills/franka_before_after.jpg` | Left: the first Franka policy drops the pot off the table mid-flip (AUC 0.65, 0/5). Right: after modelling the gripper's rubber pads and rated grip it completes the task (AUC 0.95, 5/5). |
| `stills/physics_franka_failure_frames.jpg` | Six frames of the failed run (diagnosis view). |

Message: failures are visible, measured and fixable; the fix held on 3 of 3 independent trainings (0.947, 0.959,
0.940) [M].

## 4. How it works (process slides)

| Step | File | What it shows |
|---|---|---|
| Input | `stills/real_input_*.png`, `stills/candidate_episodes.jpg` | Raw head-camera frames. The episode strip shows 4 public tasks: pot into rack, lid on pot, two-hand sweep, pouring. |
| Perception: hands | `stills/perception_hands_ep27.jpg` (2028×1012) | Hand keypoints detected on the real ep27 frames (MediaPipe, lifted to 3-D with stereo depth). |
| Perception: objects | `stills/perception_objects_ep27.jpg` (1600×1000) | Rack (red) and pot (green) found in the first frame; then tracked in 6-D (FoundationPose + stereo + visual odometry). |
| Same pipeline on unseen video | `videos/05_eval25_real_vs_sim_overlay.mp4` (1920×480, 17.8 s), `stills/eval25_real_vs_sim_overlay.png` | Hidden challenge eval episode 25 (two wooden boards). Left: real camera. Middle: the submitted policy's simulated rollout drawn onto the camera. Right: 3-D view. Shows the pipeline on video it was never developed on. No mocap exists for eval episodes. |
| Robot adapters | `stills/retarget_kinematic_NO_PHYSICS_{1,2}.jpg` | Each robot's hand fitted to the human-derived hand motion, before training. **Kinematic, no physics**: label it "starting point for training". |
| View alignment | `stills/headcam_alignment_KINEMATIC_no_physics.jpg` | Sim rendered from the head-camera path next to the real frames: the reconstruction lines up with reality. Kinematic. |
| Training result | `stills/physics_sharpa_frames_scanmesh.jpg` | Sharpa physics rollout frames (official scan meshes, earlier look). |
| Diagrams | `stills/diagram_pipeline_architecture.png` (1344×1258, clean), `stills/diagram_recipe_flow_detailed.png` (1203×1546, dense, for the appendix) | Our challenge pipeline: stereo perception and clean references → one policy per episode. The product slide should redraw it as video → task → robot adapter → policy. |

## 5. Data and asset quality slide (optional)

| File | What it shows |
|---|---|
| `stills/mesh_pot_scan_holes.png` | The official pot scan has 11 open holes (red rims); automatic repair caps the pot's opening. |
| `stills/mesh_scan_vs_clean.jpg` | Holed scan (top) vs our clean closed meshes (bottom), as rendered in the videos. |

## 6. Numbers for the slides

- **9 embodiments from one 12 s video:** 2- to 5-finger hands, 2 to 22 joints per hand, all 5/5 within 3 cm on the
  task [M].
- **Cost per trained policy [M]:**
  - training takes 70–90 min on one RTX PRO 6000 (250M simulation steps at 45–62k steps/s);
  - this whole experiment trained 12 policies (9 + the failed Franka + 2 extra Franka checks) for $28.90 of GPU
    rental, i.e. **≈ $2.40 per policy, all-in**.
- **Adding a new robot:**
  - one model file plus one config entry;
  - fitting the robot to the hand motion takes 7–26 s on a laptop-class CPU [M];
  - no robot-specific code: one generic class serves all 8 non-native hands.
- **Challenge credentials** (NVIDIA V2D Challenge Track 3, hidden evaluation set; Kaggle boards, read 6 Nov) [M]:
  - best AUC 0.886;
  - best mesh accuracy CD-O 0.239 cm, 5th on that board;
  - 26 scored submissions.
  - Use as "validated on NVIDIA's benchmark", not as a ranking claim: the final rank was 8th by rank-sum on 6 Nov.

## 7. Footnotes to show on or under the slides

1. Hands are simulated as floating hands, i.e. robot hands without arms, as is standard in dexterous-manipulation
   research. Physics: NVIDIA FlashCHORD (Newton / MuJoCo-Warp).
2. Scores are vs motion capture on a public development episode (ep27). The challenge's hidden eval videos have no
   public ground truth; they are scored by NVIDIA.
3. The videos draw clean closed object meshes (our own, aligned to the official scans within about 1–2 mm). The
   physics used the official scans.
4. Each robot's starting hand motion comes from the human motion via NVIDIA's Sharpa retargeter and our
   robot-to-robot fit. Each robot then learns its own grip with RL in physics, and only the object's motion is
   required to match the video.
5. The Franka gripper is shown with rubber-pad contact modelling (twist friction, rated grip force); without it, it
   failed (slide 3).
6. One episode (one task) so far. More tasks (lid, two-hand sweep, pouring) are planned (phase 2), not yet done.

## 8. Credits and licences (required attribution)

| Asset | Source | Licence | What to do |
|---|---|---|---|
| Input video, scans, mocap scores | NVIDIA Video to Data (V2D) Challenge Dataset, huggingface.co/datasets/nvidia/video_to_data_challenge | CC BY 4.0 | Credit "NVIDIA V2D Challenge Dataset (CC BY 4.0)" on slides that show the footage. |
| Simulator, Sharpa hand, G1 / Dex3 description | NVIDIA video_to_data / FlashCHORD (github.com/nvidia-isaac/video_to_data) | Apache-2.0 (code) + CC BY 4.0 (docs); G1 / Dex3 meshes BSD-3-Clause (Unitree Robotics) | Credit NVIDIA FlashCHORD; Unitree for G1 / Dex3. |
| Shadow Hand model | dex-urdf (dexsuite) | Apache-2.0 | Credit. |
| Allegro Hand model | dex-urdf (SimLab) | BSD-style | Credit. |
| LEAP Hand model | dex-urdf (A. Agarwal et al.) | MIT | Credit. |
| Barrett BH8 model | dex-urdf (Barrett Technology) | BSD-style | Credit. |
| D'Claw model | dex-urdf (ROBEL authors) | Apache-2.0 | Credit. |
| Inspire RH56 model | dex-urdf; derived from Inspire's own CAD download | **Unclear** (no explicit licence) | Fine for an internal pitch. Check with Inspire before a public release. |
| Franka gripper model | dex-urdf panda_gripper | **No licence file in the source** (Franka's own descriptions are Apache-2.0) | Same as Inspire: check before public release. |
| Robot names | — | Trademarks of their makers | Descriptive use only; no logos without permission. |
| Hand keypoints | Google MediaPipe | Apache-2.0 | Optional credit. |
| Object tracking | NVIDIA FoundationPose, FoundationStereo | NVIDIA licences, research use | **Check terms before commercial use of the pipeline itself.** |

All rendering, retargeting, training jobs and compositing are our own code (`showcase/`, `ops/jobs/showcase.sh`;
commits on `claude/charming-goldberg-glc1xi`).
