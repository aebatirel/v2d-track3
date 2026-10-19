import json, os
C = '/Users/aebatirel/Documents/Code/v2d-research/colab'
cells = []
def md(t): cells.append({"cell_type": "markdown", "metadata": {}, "source": t.strip("\n").splitlines(True)})
def code(t): cells.append({"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": t.strip("\n").splitlines(True)})
def wf(path, local): code(f"%%writefile {path}\n" + open(f'{C}/{local}').read())

md(r"""
# V2D Challenge, Track 3: what we ran on Google Colab (explained)

**Short version.** NVIDIA's *Video-to-Data (V2D) Challenge, Track 3* gives you head-camera videos of a person handling everyday objects (cups, a pot, a dish rack, a dustpan...). You must make a **simulated pair of robot hands** reproduce what happened to the objects. The leaderboard scores how close the **simulated** object motion is to the real motion, which was recorded with motion capture (mocap).

So far on Colab we have:
1. Rented a strong GPU (NVIDIA RTX PRO 6000, 98 GB) and installed NVIDIA's robot simulator. We checked that it trains and evaluates.
2. Built our own **perception pipeline**, which recovers the 3-D position and rotation of every object in every video frame from the stereo cameras alone.
3. Measured it on all 20 public episodes, which come with mocap ground truth: **mean AUC 0.809** from video alone. For scale, the current leaderboard leader scores **0.765** after simulation, and a robot that does nothing scores about **0.446**.

The robot part (training a policy per video) is the next step and is not in this notebook yet.

> **How to read this notebook.** Text cells explain, code cells do. Section 4 is runnable end to end on a Colab **G4** GPU (Runtime → Change runtime type → G4). It re-creates our result on public episode 12. The other sections document what we ran and what we saw.
""")

md(r"""
## 0. The challenge and how it is scored

**Input per episode.** About 7-18 s of video from a head-mounted camera rig with three cameras:
- `ego_cam_a`: a colour camera, 2028×1520.
- `ego_cam_b` and `ego_cam_c`: two black-and-white cameras 7.5 cm apart, a *stereo pair*. Like two eyes, they let us measure depth.

We also get 3-D scans (meshes) of the objects, except the wooden spoon, which has no scan.

**What must come out.** For each episode, a trained robot **policy**: a neural-network controller for two simulated *Sharpa* robot hands in NVIDIA's **FlashCHORD** simulator. The organisers' evaluator runs the policy once, records where the simulated objects go, and compares that with mocap.

**The pipeline we are building:**
```
video ──► (1) PERCEPTION: camera + every object's 3-D pose per frame   ◄── this notebook
      ──► (2) HANDS: where the person's hands and fingers are
      ──► (3) REFERENCE: turn (1)+(2) into a target motion for the robot hands
      ──► (4) TRAIN a policy in the simulator (reinforcement learning, ~1.5-2 h per video)
      ──► (5) OFFICIAL EVALUATOR replays the policy ──► simulated object trajectories
      ──► (6) SCORE vs mocap (leaderboard)
```

**Metrics.** The scorer first lines up one object's first pose (one rigid alignment) and never fixes scale. Then:

| metric | meaning | better |
|---|---|---|
| **ADD** | average distance between predicted and true object surface points (cm) | lower |
| **AUC** (main ranking) | for thresholds 1…9 cm, the share of frames with ADD below the threshold, averaged; 0 to 1 | higher |
| **SP-SR** | success if the average position error is ≤ 10 cm and the average angle error ≤ 0.5 rad | higher |
| **MP-SR** | strict success: **every** object within 3 cm and 30° on average | higher |
| **MPPE** | mean error of 6 points placed 5 cm around each object (cm) | lower |

Reference points: leaderboard leader **0.765 AUC** (12 Oct 2026). Every other team is between 0.23 and 0.37. A robot that leaves everything where it started scores about **0.446**.
""")

md(r"""
## 1. What machine did we get?
This cell prints the GPU, CUDA version, OS, CPU and RAM, and checks for Docker.

**What we saw.** The free tier gave a Tesla **T4** (16 GB), too small. With Colab Pro we switched to **G4 = NVIDIA RTX PRO 6000 Blackwell, 98 GB**, plus 48 CPUs and 176 GB RAM, on Ubuntu 24.04 with driver 580 / CUDA 13.0 and Python 3.13. G4 costs about **8.9 compute units per hour** (a T4 is about 1.1).

**No Docker.** NVIDIA's own reconstruction pipeline runs as Docker containers, so on Colab we install the pieces we need one by one instead. Colab machines are also **not persistent**: when the runtime is recycled, all installs are lost. That is why section 4 has a one-shot `setup.sh`.
""")
code(r"""
!nvidia-smi
!nvcc --version || true
!cat /etc/os-release | head -2; python --version; nproc; free -g | head -2; df -h / | tail -1
!which docker || echo 'no docker'
""")

md(r"""
## 2. NVIDIA's code and the robot simulator
- We download NVIDIA's `video_to_data` repository at **the exact commit the official evaluator uses** (`8c778f90…`). Scores must come from that version.
- Large files (robot-hand meshes, example data) are stored with **Git LFS**, so we pull only the folders we need (about 400 MB).
- The simulator (**FlashCHORD**: JAX + NVIDIA Warp + Newton + MuJoCo-Warp) goes into its own Python 3.11 environment, created with `uv`.

**What we saw.** Everything installed. JAX sees the GPU (`CudaDevice(id=0)`), with warp 1.14.0, newton 1.2.0 and mujoco 3.8.1. This takes about 5 minutes.
""")
code(r"""
%cd /content
!apt-get -qq install -y git-lfs > /dev/null
!rm -rf v2d && git init -q v2d && cd v2d && git remote add origin https://github.com/nvidia-isaac/video_to_data.git && GIT_LFS_SKIP_SMUDGE=1 git fetch -q --depth 1 origin 8c778f905cb35f76f8e6cd6e2ea486da4fb9e0ef && GIT_LFS_SKIP_SMUDGE=1 git checkout -q FETCH_HEAD && git log --oneline -1
%cd /content/v2d
!git lfs pull --include 'robotic_grounding/flash_chord/src/flash_chord/assets/**,robotic_grounding/source/robotic_grounding/robotic_grounding/assets/human_motion_data/ego_recon/**'
!pip -q install uv
%cd /content/v2d/robotic_grounding/flash_chord
!uv python install 3.11 && uv venv -q --python 3.11 .venv && UV_LINK_MODE=copy uv sync --frozen --extra train 2>&1 | tail -3
!.venv/bin/python -c 'import jax, warp, newton, mujoco; print(jax.__version__, jax.devices()); print(warp.__version__, newton.__version__, mujoco.__version__)'
""")

md(r"""
## 3. Simulator smoke test: can we train a robot policy here, and how fast?
We train on NVIDIA's own example (a person moving a tissue box) for 20 million simulation steps, about 8% of a full training run.

- **Reinforcement learning (RL):** the policy controls the two robot hands. It is rewarded for making the simulated object follow the target motion. **4,096 copies of the scene** run in parallel on the GPU.
- A full policy is **250 million steps**.

**What we saw.**
- **~45,300 simulation steps per second**, **40.5 GB** of GPU memory, 100% GPU use.
- 20M steps took 7.4 minutes, so **one full policy takes about 1.5-2 hours (about 15-18 Colab units)**.
- We also ran the **official evaluator** on that policy (1 world, trajectory export). It works. Against the policy's own target it scored AUC 0.918, MP-SR 1.0, MPPE 1.63 cm.
""")
code(r"""
%cd /content/v2d/robotic_grounding/flash_chord
!export A=/content/v2d/robotic_grounding/source/robotic_grounding/robotic_grounding/assets P=/content/v2d/robotic_grounding/source/robotic_grounding/robotic_grounding/assets/human_motion_data/ego_recon/processed/sequence_id=tissue_box_simple/robot_name=sharpa_wave && export V2D_ASSETS_DIR=$A XLA_PYTHON_CLIENT_PREALLOCATE=false MUJOCO_GL=egl && .venv/bin/python scripts/train_flash_sac.py experiment=sharpa_flash_sac task.parquet=\'$P\' reset.seed=42 logging.mode=disabled output_dir=outputs/smoke training.total_environment_steps=20004864 2>&1 | grep -E 'progress|completed' | tail -3
""")
md(r"""
Running the **official evaluator** on that policy (one simulated world, exporting the object trajectories):
""")
code(r"""
%cd /content/v2d/robotic_grounding/flash_chord
!CK=$(ls -v outputs/smoke/policy_*.safetensors | tail -1); MUJOCO_GL=egl XLA_PYTHON_CLIENT_PREALLOCATE=false .venv/bin/python scripts/evaluate_policy.py evaluation.checkpoint=$CK evaluation.world_count=1 evaluation.reset_mode=explicit evaluation.metrics_output=/content/smoke_eval.json evaluation.object_trajectories_output=/content/smoke_traj.parquet hydra.run.dir=/content/smoke_eval logging.mode=disabled 2>&1 | tail -3; cat /content/smoke_eval.json | head -40
""")

md(r"""
## 4. Our perception pipeline: from stereo video to 3-D object motion
This is the part we built and measured. For every frame we want each object's **6-D pose**: 3-D position plus 3-D rotation, in one fixed world frame. The pipeline:

1. **Rectify the stereo pair.** We warp the two black-and-white cameras so that matching points sit on the same image row. That makes depth estimation a 1-D search.
2. **Depth from stereo:** NVIDIA's **FoundationStereo** network gives a depth map per frame. Depth = focal length × baseline / disparity (focal ≈ 600 px, baseline 7.5 cm). This takes about 0.27 s per frame.
3. **Find each object in the first frame** (section 5 explains why we don't use text prompts):
   - **SAM2** (Meta) cuts the image into candidate regions.
   - We render each object's 3-D scan from 42 viewpoints in grey, to match the black-and-white cameras.
   - **DINOv2** (Meta) image features compare every region with those renders.
   - A **3-D size check** from the depth rejects regions that are too big or too small.
   - Objects are matched to regions with a one-to-one assignment (Hungarian algorithm). Brightness breaks ties between twin objects, e.g. a dark blue cup versus a light beige one.
4. **Track each object:** NVIDIA's **FoundationPose** registers the scan to the first frame, then tracks it frame by frame using image + depth. It runs at about 20 fps.
5. **Track the camera:** the head moves. We match image features (SIFT) to earlier frames, lift them to 3-D with the depth, and solve for the camera pose (PnP with RANSAC). This is called *visual odometry*.
6. **Combine:** object pose in the world = camera pose × object pose seen by the camera.
7. **Score.** Only now do we read the mocap ground truth, using the official kit's metric code. The pipeline itself never sees ground truth.

**Cost.** About 1-3 minutes per episode on the G4 after setup. Setup (next cell) takes about 15 minutes.
""")
md(r"""
### 4a. One-shot setup
This installs everything perception needs and downloads public episode 12 plus the official scoring kit. Each step prints a marker such as `SAM2-OK`. It also installs the simulator environment from section 2 in the background.
""")
wf('/content/setup.sh', 'setup.sh')
code(r"""
!bash /content/setup.sh > /content/setup.log 2>&1; grep -aE '[A-Z0-9]+-OK|DONE' /content/setup.log
""")
md(r"""
### 4b. The perception script
`perc.py` implements steps 1-7 above. It writes `result.json` (the scores), `poses.npz` (all poses) and `masks_f0.jpg` (which region was picked for each object) to `/content/perc/ep<N>/`.

It scores several *world* variants:
- `vo`: camera from visual odometry. This is the real method.
- `anchor:<object>`: treats one object as static and uses it as the world. This is for analysis only.
""")
wf('/content/perc.py', 'perc2.py')
md(r"""
### 4c. Run it on public episode 12 (a blue cup put into a dish rack)
**What the log lines mean:**
- `rectified focal … baseline …` is the stereo geometry: about 600 px and 0.0755 m.
- `depth ready` means stereo depth is done for all frames. It is cached, so re-runs skip it.
- `vo keyframes … median inliers …` comes from camera tracking. More inliers is better; many keyframes means longer chains and more drift.
- `det <object> …` lists the best candidate regions with their scores and 3-D sizes, and `assignment` is the final pick.
- `tracked <object>` reports FoundationPose tracking time.
- The last lines are the **scores**. Look at the `vo` line.

**What we got on episode 12:** `vo AUC 0.995, SP 1.00, MP 1.00, MPPE 0.59 cm`, with a cup AUC of 1.00 and a rack AUC of 0.99. The cup moved 22 cm, and our median position error was about 1 cm.
""")
code(r"""
!cd /content && EP=12 python /content/perc.py 2>&1 | grep -a '^\['
""")
code(r"""
from IPython.display import Image, display
display(Image('/content/perc/ep12/masks_f0.jpg', width=800))   # first frame: picked regions (blue = slot 0 object, green = slot 1)
""")
md(r"""
### 4d. Diagnostics: frame-by-frame error and overlay
`diag.py` prints the position and rotation error per object every N frames, after the same alignment the scorer uses. It also draws the tracked scan (**green dots**) and the mocap truth (**red dots**) on 8 frames. When tracking is good the two coincide. This is how we found the failures in section 5.
""")
wf('/content/diag.py', 'diag.py')
code(r"""
!python /content/diag.py 12 /content/perc 20
display(Image('/content/perc/ep12/diag.jpg', width=1000))
""")
md(r"""
### 4e. Optional: all 20 public episodes (about 45 minutes)
This downloads the other 19 public episodes (black-and-white cameras + mocap) and all object scans, runs `perc.py` on each, and prints the summary table. Section 5 shows what we got.
""")
wf('/content/run_public.sh', 'run_public.sh')
wf('/content/summ.py', 'summ.py')
code(r"""
!bash /content/run_public.sh > /content/run_public.log 2>&1; grep EP /content/run_public.log | tr '\n' ' '
!python /content/summ.py /content/perc
""")

md(r"""
## 5. Results on the 20 public episodes (perception only, camera from visual odometry)

| ep | objects | AUC | note |
|---|---|---|---|
| 12 | blue cup, dish rack | **0.995** | |
| 13 | blue cup, dish rack | **0.998** | |
| 23 | wooden piece 1, 2 | **0.995** | |
| 27 | dish rack, white pot | **0.994** | |
| 40 | dustpan | **0.986** | |
| 22 | blue cup, water pitcher | 0.962 | |
| 18 | hand broom, dustpan | 0.935 | |
| 44 | white pot | 0.887 | |
| 31 | hand broom, dish rack | 0.885 | |
| 11 | blue cup, beige cup | 0.871 | twin cups; the static cup drifts with camera tracking |
| 21 | blue cup, water pitcher | 0.858 | |
| 45 / 42 / 43 / 41 | white pot | 0.836 / 0.817 / 0.807 / 0.795 | long camera-tracking chains, so drift |
| 24 | wooden piece 1, 2 | 0.820 | |
| 39 | dustpan | 0.550 | about a 5 cm offset once it moves |
| 0 | white pot, pot lid | 0.179 | lid is 180°-symmetric, so its rotation is wrong |
| 26 | dish rack, white pot | 0.031 | white pot inside a white rack, so detection fails |
| 2 | white pot, pot lid | ≈0.98 | not read individually; inferred from the mean |
| **mean (20)** | | **0.809** | SP-SR 0.90, MP-SR 0.85, MPPE 4.8 cm |

**What this means:**
- When an object is found correctly, tracking is **almost perfect**: about 1 cm error even on fast motions.
- Our mean **from video alone** (0.809) is above the leader's **final** score (0.765). That is a strong sign, but **not yet a leaderboard result**: the robot still has to reproduce the motion in simulation, and that always loses some accuracy.
- The failures are specific and fixable:
  - **Symmetric lid:** use the small mocap markers on the lid to tell its rotation. Our earlier research did this with a marker-only lid tracker, which scored AUC 0.977.
  - **White-on-white pot and rack:** a render-and-compare check (built, being tested).
  - **Camera drift on long pot videos:** improved camera tracking (built, being tested).

**Lessons from the way there:**
- **Text prompts don't work on these cameras.** A text-prompted detector (OWLv2, e.g. "a cup") misses the pot on black-and-white images and swapped the two cups (AUC 0.10 → 0.87 after the switch to scan-based matching).
- **FoundationPose's internal score cannot compare different regions.** A piece of the rack outscored the real cup, 143 vs 73. So we pick regions with our own checks, not with that score.
""")

md(r"""
## 6. Hands (step 2): first test
The robot needs to know where the person's hands and fingers are. Several popular hand models need the licensed **MANO** hand model, so we use Google's **MediaPipe Hands** instead, which is free. We then lift its 21 points per hand to 3-D with our stereo depth.

**What we saw.** MediaPipe almost never finds hands in the black-and-white cameras: 0 two-hand frames on episodes 0 and 12. On the **colour** camera it finds both hands in **173 of 181** frames (episode 12) and **338 of 373** (episode 0). So hands come from the colour camera, projected into the stereo depth through the factory calibration.

The cell below repeats the detection count. It needs a small extra environment with MediaPipe 0.10.14.
""")
code(r"""
!uv venv -q --python 3.11 /content/mpvenv && uv pip install -q --python /content/mpvenv/bin/python 'mediapipe==0.10.14' opencv-python-headless numpy
!for c in a c; do f=/content/t3/v/ep12_$c.mp4; [ -s $f ] || curl -fsSL -o $f https://huggingface.co/datasets/nvidia/video_to_data_challenge/resolve/main/track_3/public/videos/chunk-000/observation.images.ego_cam_$c/episode_000012.mp4; done
""")
code(r"""
%%writefile /content/mptest.py
import sys, numpy as np, cv2, mediapipe as mp
EP, CAM = int(sys.argv[1]), sys.argv[2]
H = mp.solutions.hands.Hands(static_image_mode=False, max_num_hands=2, model_complexity=1, min_detection_confidence=0.3, min_tracking_confidence=0.3)
cap = cv2.VideoCapture(f'/content/t3/v/ep{EP}_{CAM}.mp4'); cnt = []
while True:
    ok, f = cap.read()
    if not ok: break
    cnt.append(len(H.process(cv2.cvtColor(f, cv2.COLOR_BGR2RGB)).multi_hand_landmarks or []))
cnt = np.array(cnt); print(f'episode {EP} camera {CAM}: frames with 0/1/2 hands =', [int((cnt == k).sum()) for k in range(3)])
""")
code(r"""
!/content/mpvenv/bin/python /content/mptest.py 12 a 2>/dev/null; /content/mpvenv/bin/python /content/mptest.py 12 c 2>/dev/null
""")

md(r"""
## 7. What's next, and what it costs
1. **Reference + robot training on public episodes.** We turn our object and hand tracks into the simulator's target format, train a policy, run the official evaluator, and score against mocap. **This is the decisive test**: it tells us how much accuracy the robot stage loses. It takes about 2-3 GPU hours.
2. **The wooden spoon** is in 10 of the 20 eval episodes and has **no scan**. We built a parametric spoon model (about 30 cm, 95×52 mm bowl, three mocap markers). Its exact coordinate convention is close to a coin flip, so we will ask the organisers.
3. **Pot and lid** (6 eval episodes): lid symmetry via markers, plus the fixes above.
4. **First submission:** 20 eval policies at about 2 h each, so about 40 GPU hours. On a rented RTX PRO 6000 (about $2/h) the first full leaderboard submission costs roughly **$150-200**.

**Hardware notes:**
- The full training recipe needs a GPU with **≥ 48 GB** of memory: we measured 40.5 GB.
- Perception needs much less.
- Everything runs on Linux, with an NVIDIA driver ≥ 580 (CUDA 13).

**Deadline:** leaderboard freeze is 4 Nov 2026.

---
### Glossary
- **6-D pose**: an object's position (x, y, z) plus rotation (3 angles).
- **Stereo / disparity**: two cameras side by side. How far a point shifts between the two images (disparity) gives its depth.
- **Rectification**: warping the stereo images so matching points lie on the same row.
- **Mocap**: motion capture. Small reflective markers on the objects are tracked by external cameras; this is the "true" motion.
- **Visual odometry (VO)**: estimating how the camera moved from the images themselves.
- **Policy**: the neural-network controller that drives the robot hands. **RL** (reinforcement learning) trains it by trial and error in simulation.
- **Reference**: the target motion (objects + hands) the policy is trained to reproduce.
- **AUC / SP-SR / MP-SR / MPPE**: the leaderboard metrics; see section 0.
""")

nb = {"cells": cells, "metadata": {"accelerator": "GPU", "colab": {"provenance": [], "gpuType": "G4"},
      "kernelspec": {"display_name": "Python 3", "name": "python3"}, "language_info": {"name": "python"}},
      "nbformat": 4, "nbformat_minor": 0}
out = '/Users/aebatirel/Documents/Code/v2d-research/package/V2D_Track3_Colab_Explained.ipynb'
json.dump(nb, open(out, 'w'), indent=1, ensure_ascii=False)
print(out, len(cells), 'cells', os.path.getsize(out), 'bytes')
