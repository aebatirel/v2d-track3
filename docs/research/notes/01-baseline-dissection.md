# 01 — NVIDIA V2D baseline dissection (Track 3)

Status: COMPLETE (2026-10-04). Research only: no repo code modified, nothing executed, no SlamDunk code read.
All code was read via `gh api` at the pin below. Section C and E were dissected by two helper agents and
the load-bearing C claims were re-read by me (marked "re-checked"); other C/E line numbers are the
helpers' readings. Uncertain claims are marked UNVERIFIED; untested ideas are marked HYPOTHESIS.

**Top findings (details and evidence below):**
1. Every metric quantity in the baseline (object size, object/hand translation, camera translation) comes
   from monocular MoGe-2 depth; the calibrated 75 mm stereo pair is never used, and NVIDIA's own demo needed
   manual scaling/leveling (A.2). Scale error is scored directly.
2. The ego path supports exactly one object and assumes 30 fps (A.0, B.2). Track 3 has 1-2 objects at
   ~20.25 fps.
3. The scored object trajectory is the FlashCHORD rollout tracking our reconstructed reference, unassisted,
   from exact frame 0 (C.10). Score error = reference error + policy tracking error; the reference error
   is a floor no policy can beat.
4. FlashCHORD plays references at `motion_speed: 0.5` (half speed) and resamples from the Parquet `fps`
   (C.11, re-checked). Wrong `fps` changes simulated dynamics.
5. Reward is dominated by object keypoints (w=20) using ±1 m lever arms (orientation-heavy), plus contact
   terms (+10/−1/−10) derived from our MANO contact labels; unlabelled sim contacts are penalized hard (C.2).
6. Evaluation starts from a state training rarely sees (exact fingers, no VOC hold, frame 0) (C.7).

Source pin: `nvidia-isaac/video_to_data@7c0d3b94ce97b28deb571b4e7fdfeb5b2158df80` (2026-10-02, #191).
This SHA is 4 commits ahead of the evaluator pin `8c778f90` and the diff touches only docs/kit and
`robotic_grounding/groot_finetune/*` (checked with `gh api .../compare/8c778f90...7c0d3b94`), so
`reconstruction/` and `robotic_grounding/flash_chord/` are identical to the evaluator pin.

Citation format: `path:line`. Abbreviations:
`RE` = `reconstruction/modules/v2d_pipelines/run_ego_reconstruction.py`,
`RW` = `reconstruction/modules/v2d_pipelines/run_ego_wilor.py`,
`E2E` = `reconstruction/modules/v2d_pipelines/run_v2d_ego_e2e.py`,
`RB` = `reconstruction/modules/v2d_common/result_bundle.py`,
`M/` = `reconstruction/modules/`, `RG/` = `robotic_grounding/`.

---------------------------------------------------------------------------------------------------

## A. Ego reconstruction

### A.0 Entrypoint and control flow

- `RE` is a thin CLI over two legacy runners (RE:3-16): `--hand_tracking dynhamr` -> `E2E.run_v2d_ego_e2e`
  (RE:703-728); `--hand_tracking hamer|hawor` -> `RW.run_ego_wilor` (RE:731-826). The HaMeR/HaWoR runner is
  the "new full pipeline" in `reconstruction/docs/ego_e2e_setup.md:108-124`.
- `RE` defaults differ from `RW` defaults (important when reproducing): RE sets gsplat
  `epochs=10, batch_size=4, lr_object_scale=1e-3, lr_hand_articulation=1e-3, lr_hand_shape=1e-3,
  lr_hand_scale=1e-3, w_relative_depth=1.0, w_perceptual=1.0, w_vertex_smoothness=100,
  w_smooth_camera_*=100, w_smooth_object/hand_*=0, lr_schedule=cosine` (RE:27-66), while `RW` defaults are
  `epochs=20, batch=16, lr_object_scale=0.0, w_relative_depth=0.0, w_smooth_*=0.1` (RW:602-637).
  `sam2_hand_prompt_source` default is `wilor_mask` in RE (RE:614-616) vs `box` in RW (RW:537).
- Stage caching: every stage is skipped if its output exists (`_step`, RE:149-154, RW:274). Re-runs after
  changing upstream inputs need manual deletion of downstream folders (failure mode for experimentation).
- Single object only. Grounding DINO's top detection on the reference frame is taken (`obj_dets[0]`,
  RW:941) and assigned SAM2 id 1 (RW:942). Hands are ids 2.. (RW:950). The result bundle, loader and URDF
  path all assume one rigid body (see B). **Two-object Track 3 episodes are not supported as shipped.**
- Reference frame default 0 (RE:589). Registration of hands (WiLoR), object box (DINO), object mesh
  (SAM3D), object scale and FoundationPose all happen on this one frame (RW:880-1151). If either hand or
  the object is not visible in frame 0 the run raises (RW:893-904, RW:936-940).

### A.1 Stage table (HaMeR/HaWoR path, `RW`)

| # | Stage | Model / upstream (pin) | Inputs -> outputs | Frame | Where it is | Notes / failure modes |
|---|---|---|---|---|---|---|
| 0 | Undistort (opt `--undistort`) | AnyCalib | video -> `anycalib/undistorted.mp4`, intrinsics | image | RW:800-813 | Learned single-image calibration; our OAK has factory intrinsics, so this is unnecessary. |
| 0b | GeoCalib (opt) | GeoCalib, `git+https://github.com/cvg/GeoCalib.git` **unpinned** (`M/v2d_geocalib/lib/pyproject.toml:15`) | 8 uniformly sampled frames (`M/v2d_geocalib/lib/video_to_calibration.py:23-28`) -> intrinsics (median), gravity (normalized mean, `M/v2d_geocalib/lib/_geocalib.py:149-202`, mean at :168) | camera (OpenCV) | RW:816-836; RE:193-219 | Only used for gravity alignment unless `--use_geocalib_intrinsics`. Single-image gravity, 8 samples. |
| 1 | Frame extraction | ffmpeg/cv2 | video -> `frames/*.png` | image | RW:839-840 | |
| 2 | Depth + intrinsics | MoGe-2 ViT-L normal (`Ruicheng/moge-2-vitl-normal`, `M/v2d_moge/lib/download_weights.py:11`; code pinned `MoGe@925b8ed8`, `M/v2d_moge/lib/pyproject.toml:16`) | per-frame RGB -> metric depth PNG + per-frame intrinsics (`M/v2d_moge/lib/video_to_depth.py:120-141`) | camera | RW:845-858 | Independent per frame (no temporal consistency). If intrinsics are supplied, only FoV(fx) is passed as prior (`video_to_depth.py:94-98,121`); cx,cy remain image centre. Depth stored as uint16 `65535/(d+1)` (`M/v2d_common/datatypes.py:14-20`), quantization ~0.03 mm at 0.5 m (not an issue). |
| 2b | Stabilise intrinsics | median of per-frame fx,fy,cx,cy (`M/v2d_depth/lib/stabilize_intrinsics.py:67-70`) | -> `intrinsics_stable.json` | | RW:859-860 | Depth maps were produced with per-frame focal; downstream uses the median focal -> per-frame depth/intrinsics inconsistency (UNVERIFIED magnitude). |
| 2c | Camera trajectory (opt `--run_droid_slam`) | DROID-SLAM, `git clone` of princeton-vl/DROID-SLAM **unpinned** (`M/v2d_droid_slam/docker/Dockerfile:31`) | video + stable K -> `slam_poses/*.json` cam-to-world, TUM traj | world = DROID first keyframe | RW:868-878; `M/v2d_droid_slam/lib/_slam.py:206-320` | **Monocular** (`stereo=False`, `_slam.py:261`), input resized to 384x512 (`_slam.py:213`). Metric scale = global median over keyframes of per-keyframe median(MoGe depth / DROID depth) over all valid pixels (`_slam.py:83-116`), i.e. hands/objects not masked. The supported "metric depth prior inside BA" path (`video_to_slam.py:12-22`, `input_depth_folder`) is **not used** by the ego pipeline (only `align_to_depth_folder`, RW:875). |
| 3 | Hand detection + MANO | WiLoR (per frame) | frames -> `wilor_raw/*.json` | virtual cam | RW:881-889 | Must detect >=1 hand at reference frame (RW:893-904). |
| 4 | Object detection | Grounding DINO Swin-T OGC (`M/v2d_grounding_dino/lib/download_weights.py:9-12`), box/text thr 0.35/0.25 (`.../image_to_object_bboxes.py:58-59`) | ref frame + text prompt -> boxes sorted by confidence (`:90`) | image | RW:925-942 | One frame, one box; wrong box = wrong object for the whole episode. |
| 5-6 | Video masks | SAM2.1 Hiera-L (`M/v2d_sam2/lib/download_weights.py:10`; config `sam2.1_hiera_l.yaml`, `video_to_masks.py:47`) | prompts at ref frame -> `masks/{id}/*.png`; propagates reverse then forward (`video_to_masks.py:111-112`) | image | RW:944-1050 | Hand prompt from rendered WiLoR MANO silhouette (RE default) or box. No re-prompting on drift. |
| 8a | Object mesh | SAM 3D Objects (`facebook/sam-3d-objects`, gated; repo cloned **unpinned** `M/v2d_sam3d/docker/Dockerfile:27`) | ref RGB + object mask + MoGe depth pointmap masked to object (`M/v2d_sam3d/lib/image_to_mesh.py:221-226`) -> textured OBJ + rot/trans/scale (`:244-248`) | camera at ref frame | RW:1096-1115 | Single view: back side hallucinated; layout grounded on monocular depth. Texture baking + mesh postprocess on (RW:1106-1107). |
| 8b | Object scale | FoundationPose register + render score; log-space grid in [0.5,2.0], 9 samples x 4 levels, score = mask IoU + exp(-median abs ratio error vs MoGe depth) (`M/v2d_foundation_pose/lib/foundation_pose_tracker.py:478-535,621-694`) | ref frame RGB, MoGe depth, mask -> scaled mesh | camera | RW:1117-1136 (provided mesh: RW:1076-1095; `--skip_object_scale_estimation` skips) | **Object metric size is tied to one MoGe depth map of one frame.** Thin objects give few depth pixels; IoU term dominated by mask quality. |
| 8c | 6-DoF tracking | FoundationPose (vendored under `M/v2d_foundation_pose/lib/FoundationPose/`; default backend TensorRT, `.../backends.py:16`) | RGB + MoGe depth + SAM2 mask, register@ref (10 it), track (5 it), re-register when rendered-mask IoU < 0.3 (`run_video_to_poses.py:130-161`; RE:598) | object->camera | RW:1138-1151 | Depth input is monocular MoGe (not sensor); `mask_depth=True` zeros depth outside SAM2 mask (RW:1148). Symmetry handling exists (`symmetry.py`) but is not wired in. Particle mode exists (`n_particles>1`, `run_video_to_poses.py:142-151`) but unused. |
| 8d | Smoothing | ESKF + RTS, random-walk model, IoU-scaled measurement noise (`run_ekf_smoothing.py:1-30,106-208`); noises xy 0.01, z 0.04, r 0.02 (RW:1161-1166) | -> `poses_smoothed/` | **camera frame** | RW:1153-1168 | Smooths object-to-camera poses, so head motion is smoothed together with object motion. No outlier gating. **Bypassed when gsplat refinement runs**: refinement re-starts from raw `poses/` (RW:1908) and its output takes priority (RW:2013-2018). |
| 9-14 | Hands to metric camera frame | WiLoR (default), HaMeR (`--hand_tracking hamer`), HaWoR (`hawor`) | per-track MANO -> `*_aligned/` -> `*_aligned_filled/` | camera | RW:1179-1547 | Depth alignment = per-frame translation-only shift along the centroid ray by median(MoGe depth - rendered MANO depth) on hand-mask minus object-mask pixels (`M/v2d_hamer/lib/align_hands.py:1-25,374-378`). Gaps <=15 frames interpolated (RE:629). HaWoR is run with its own SLAM internally, but only its camera-space chunks are exported (`M/v2d_hawor/lib/run_hawor.py:3-7`). |
| 15 | Joint refinement (opt `--run_gsplat_refinement`) | "simple" 2DGS (`M/v2d_gsplat_refinement/lib/refine_simple.py:1-20`) | frames, MoGe depth, masks, raw FP poses, hand poses, SLAM seed -> refined object poses, wrist poses, camera poses, optional global object scale | world = **camera at reference frame** (`refine_simple.py:282-305,339-343,1364-1367`) | RW:1838-1979 | Optimizes per-frame object pose, wrist root, camera pose, Gaussian appearance; losses: L1 RGB, mask, optional MoGe depth-gradient, smoothness. With RE defaults also learns object scale (RE:33). Background Gaussians initialized from MoGe depth (refine_simple.py:1380-1400). |
| P | Bundle | `write_result_bundle` (RB:673-793) | see A.3 | camera_to_world | RW:2006-2109 | |
| G | Gravity align (opt) | GeoCalib | rotates all `*_to_world` keys (RB:446-562) | z-up | RW:2111-2118; RE:262-308 | See A.2. |

The DynHaMR path (`E2E`) replaces stages 3/9-14 with ViPE + Dyn-HaMR (`E2E:427-445`) and keeps MoGe as the
only downstream depth (RE:718). Its base bundle has **no camera trajectory** (`camera_to_world_dir=None`,
`E2E:699-707`): ViPE camera poses are computed but discarded; world poses exist only with
`--run_droid_slam` (RE:222-249).

### A.2 Where metric scale and the world/gravity frame come from

- **Metric scale: entirely MoGe-2 monocular depth.** Hands: per-frame shift to MoGe depth (align_hands).
  Object: mesh scale grid search against one MoGe frame (8b), then FP tracking on MoGe depth. Camera
  translation: DROID scale = median MoGe/DROID depth ratio (`_slam.py:83-116`). Background in gsplat:
  MoGe depth. No stereo, IMU or known-size cue anywhere.
- Evidence the baseline's scale/gravity need manual fixing: NVIDIA ships `reconstruction/scripts/
  scale_result_bundle.py` (manual global `--scale`, `:137-219,244-270`) and
  `M/v2d_task_library_loader/lib/level_result_bundle.py` whose docstring says the shipped
  `tissue_box_simple` "needed an 8.4 degree correction" and was loaded from
  `result_slam_gravity_aligned_scaled` (`level_result_bundle.py:4-34`). (Inference: the demo bundle was
  hand-scaled; magnitude not stated.)
- **World frame.** Without `--run_droid_slam`: `camera_to_world` = identity for every frame and
  `camera_is_valid` all True (RB:704-708), so "world" is the moving head camera; object/hand world
  trajectories then contain head motion. With DROID: world = DROID's first-frame camera (scaled).
  With gsplat refinement: world = camera at `--reference_frame` and camera poses are saved
  world-to-camera then inverted (RW:2066-2070; RB:139-140).
- **Gravity.** `gravity_align_result_bundle` (RB:446-562): GeoCalib up-vector per sampled frame is negated
  to gravity (RB:315-323), rotated to world with that frame's `camera_to_world` (RB:339-346), averaged
  (RB:353), and the world is rotated (no translation) so +Z is up and +Y is mean horizontal camera-forward
  (RB:368-389, RB:547-553). Without SLAM the 8 samples are averaged in a moving camera frame (error grows
  with head pitch changes). Rotation only: floor height/origin is not set here (the robot loader does it,
  see B.2).

### A.3 `result.npz` schema (RB:736-761; manifest RB:766-791)

Per-episode, N = number of frames (inferred from frames dir, RB:99-116). OpenCV camera axes.

| Key | Shape | Meaning |
|---|---|---|
| `camera_to_world_transform` | (N,4,4) f32 | identity if no camera source (RB:704-708) |
| `camera_is_valid` | (N,) bool | |
| `camera_intrinsics` | (4,) | fx,fy,cx,cy of `intrinsics_stable.json` |
| `object_to_camera_transform` | (N,4,4) | rigid; any pose scale stripped and baked into mesh (RB:146-167) |
| `object_to_world_transform` | (N,4,4) | c2w @ o2c (RB:713-715) |
| `object_scale` | scalar | always 1.0 (scale baked into `mesh.obj`, RB:717,743) |
| `object_is_valid` | (N,) bool | |
| `hand_{left,right}_betas` | (10,) | first frame's betas only (RB:191-193) |
| `hand_*_wrist_orient_in_camera` | (N,3) | MANO global_orient axis-angle (left hand stored in right-hand param space, see B.2) |
| `hand_*_wrist_trans_in_camera` | (N,3) | MANO `cam_t` (root translation, not the wrist joint) |
| `hand_*_wrist_to_camera_transform`, `hand_*_wrist_to_world_transform` | (N,4,4) | built from orient + cam_t (RB:207-210, 721-726) |
| `hand_*_finger_pose` | (N,15,3) | full 45-DoF axis-angle |
| `hand_*_scale` | (N,) | per-track `hand_scale` diagnostic (align_hands `_aggregate_hand_scales`) |
| `hand_*_is_valid` | (N,) bool | invalid frames hold zeros/identity |
| after gravity alignment | | `gravity_alignment_transform`, `gravity_in_world_before_alignment`, `gravity_target_world`, `gravity_alignment_applied` (RB:516-519) |

Plus `mesh.obj` (+ mtl, textures) with object scale baked into vertices (RB:607-670) and `manifest.json`.
Only one object and at most one hand per side (duplicate-handedness tracks are dropped, RW:1851-1864).

### A.4 Failure modes most relevant to Track 3

1. Metric scale error (MoGe) propagates into object size, object translation and camera translation;
   the Track 3 scorer does not correct scale (see track3-requirements.md).
2. Frame-0 registration dependence (DINO box, SAM3D mesh, scale, FP init all on one frame).
3. FoundationPose with monocular depth on thin/symmetric objects; re-registration at IoU<0.3 can flip
   pose (no symmetry awareness). The IoU compares the **full** rendered silhouette with the **visible**
   SAM2 mask (`foundation_pose_tracker.py:213-218,369-393`), so heavy hand occlusion during a grasp lowers
   IoU even for a correct pose and triggers a from-scratch re-registration on the occluded mask; there is
   no empty-mask/occlusion guard (inference from code; UNVERIFIED on data).
4. EKF in camera frame, and EKF bypass when gsplat runs.
5. One object only.
6. Unpinned upstreams (DROID-SLAM, GeoCalib, sam-3d-objects) -> reproducibility risk for the winners'
   "reproducible single command" requirement.
7. Cache-by-existence (`_step`) silently reuses stale outputs.

### A.5 Repo modules not used by the ego path

See section E (FoundationStereo, cuSFM, BundleSDF, HOI object reconstruction, multi-view FoundationPose,
depth-alignment helpers). The single most useful swap is metric depth from the mono pair (E.1).

---------------------------------------------------------------------------------------------------

## B. Ego -> robot (Sharpa)

### B.1 Flow (`RG/README.md:214-275`)

`result/` bundle -> **loader** (`M/v2d_task_library_loader/lib/ego_recon_loader.py`, runs in the loader
image) writes `ManoSharpaData` "loaded" Parquet -> `RG/scripts/retarget/ego_recon_to_sharpa.py` (per-frame
IK to Sharpa Wave) -> `RG/scripts/generate_rigid_urdfs.py --dataset ego_recon` ->
`RG/scripts/reconstruct_support_surfaces.py --dataset ego_recon --sequence_id <seq>`.

README's three listed "properties of monocular reconstruction" (`RG/README.md:259-275`):
1. Fingers routinely start inside the object -> project penetrating MANO keypoints onto the object OBB
   (`retarget/object_collision.py`). **Code note:** this is opt-in (`--surface_project`, default False,
   `ego_recon_to_sharpa.py:156-163`), not automatic as the README implies.
2. Contact positions/normals are noisy -> default `contact_wrench_support_reward` is a poor signal; use
   the `force_closure` reward (C.2).
3. Gravity alignment can leave a residual tilt (object on an edge); diagnose via 5 mm contact footprint;
   neither loader flag fixes it reliably; level once with `level_result_bundle`, then load with
   `--no_ground_align`. Shipped `tissue_box_simple` needed 8.4 deg.

### B.2 Loader (`ego_recon_loader.py`)

- Expects `<clip>/outputs/result/result.npz` (`:88-91`, override `--result_subpath`, `:613-619`).
- **Single rigid object**: `object_body_names=[safe_object]` (`:272`), one pose stream from
  `object_to_world_transform` (`:424-436`).
- **FPS hard-coded to 30** (`EGO_FPS = 30.0`, `:86`, returned by `get_fps`, `:465-467`; registry
  `fps=30.0`, `RG/source/robotic_grounding/robotic_grounding/retarget/dataset_registry.py:250-252`).
  Track 3 video is ~20.25 fps, so the reference would play ~1.48x too fast unless overridden.
  (How FlashCHORD consumes fps: see C.)
- World re-pose: hands converted from camera to world with `trans_world = R_c2w (J0+cam_t) + t_c2w - J0`
  (`:25-33,334-337`), checked by a 1e-4 m FK gate (`:362-422`). Left hand mirrored from right-hand param
  space by negating y,z axis-angle components (`:309-321`).
- Ground alignment `_scene_align` (`:150-220`): default (no `--no_ground_align`) takes the object's
  **thinnest PCA extent at frame 0** as "up" (`:187-201`), sign chosen to point toward the camera
  (`:193-196`); then centres the object in xy and puts its lowest vertex at `z = ground_z_offset`
  (default 0, `:211-218`). Assumes the object rests on a table at frame 0. With `--no_ground_align` the
  GeoCalib rotation is kept but the position normalization still happens (`:180-185`). Optional yaw
  offset (`:203-210`).
  - For a spoon, the thinnest extent is roughly the table normal if it lies flat (OK); for a pot/cup it is
    arbitrary (README caveat).
- Contacts: proximity of MANO vertices to object surface points < 1 cm (`dataset_loader_base.py:741-754`;
  `contact_utils.py:11-80`), reduced to per-link averages; stored as `mano_*_link_contact_*`,
  `mano_*_object_contact_*` columns (`dataset_loader_base.py:843-929`).

### B.3 Retargeting (`ego_recon_to_sharpa.py`)

- Per-frame IK (warm-started from previous frame) on MANO joint positions/orientations with
  `mano_to_robot_scale=1.2` (`:93`, `:521-535`; `run_frame_ik` in
  `RG/source/robotic_grounding/robotic_grounding/retarget/retarget_utils.py:86-151`, max_iter 100).
- Object trajectory is **copied unchanged** into the processed Parquet (only robot_* columns are added,
  `:572-612`). The policy's object reference is therefore exactly the reconstruction.
- Opt-in de-penetration / jitter tools, all default off: `--hand_object_offset` (constant outward,
  `:94-102,224-243`), `--adaptive_offset` (`:103-131,246-294`), `--smooth_reference` (Savitzky-Golay window
  9, order 2, documented finger-velocity spikes up to ~50 rad/s on WiLoR, `:132-155,190-221`),
  `--surface_project` (OBB push-out, margin 5 mm, `:156-185`).

### B.4 Rigid URDF (`RG/scripts/generate_rigid_urdfs.py`)

- One link, **mass 0.3 kg, inertia diag 0.001** fixed for every object (`:103-131`), `balanceinertia`.
  Collision mesh = the visual mesh converted to STL (`:99-101,380-397`). No convex decomposition here
  (the simulator replaces it with CoACD convex hulls and reads mass/inertia from this URDF: C.8).
- A 0.3 kg box-like inertia is far from a ~20-40 g wooden spoon (UNVERIFIED real mass). Whether mass is
  ours to set (asset) or fixed by the evaluator is an organizer question.

### B.5 Support surfaces (`RG/source/robotic_grounding/robotic_grounding/retarget/support_recon.py`)

- Finds runs of >=5 frames where the object moves <1 mm and <0.01 rad per frame
  (`support_recon.py:228-283`), places a flat disk (1 cm thick, radius = half max XY extent of the mesh
  footprint, top at the mesh's minimum z) under each run (`:35-39,377-392`), merges overlapping disks
  (`:418+`), drops disks below z=0.05 m as "on the ground" (`:39`), writes USD.
- Hand-release gate exists but is opt-in (h2o only, `:41-47,611-633`): a held-still object can be
  mistaken for a supported one.
- Monocular jitter above 1 mm/frame breaks still detection -> missing support -> object falls at reset
  (inference from thresholds; UNVERIFIED on our data).

---------------------------------------------------------------------------------------------------

## C. FlashCHORD (`sharpa_flash_sac`)

Paths below are relative to `FC/` = `robotic_grounding/flash_chord/src/flash_chord/`.

### C.1 Config composition

Root `FC/configs/train_flash_sac.yaml:1-17` (experiment after `_self_`, so it overrides); root adds
`env.capture_terminal_state: true` and critic context `reference_phase`, `object_body_velocity` (`:26-31`).

| Group | File | Key values |
|---|---|---|
| experiment | `configs/experiment/sharpa_flash_sac.yaml` | 4096 worlds (`:25-26`); action normalized/rational (`:28-30`); 250,003,456 env steps; 8 updates/collection; actor 256 / critic 512; init std 0.1; `log_std_max` ln 0.15; residual-mean LR x0.1; replay 4.19M / min 409,600; target sigma 0.1; checkpoint every 10,000,384 steps (`:32-52`) (re-checked) |
| task | `configs/task/default.yaml` | `parquet` required; **`motion_speed: 0.5`**; `source_frame_playback: false`; frames 0..-1 (`:3-7`) (re-checked) |
| sim | `configs/sim/rl.yaml` | 20 Hz control, 5 substeps (100 Hz physics); Newton solver, implicitfast, pyramidal cone; njmax 512, nconmax 256; impratio 20; 100 iters / 50 line-search (`:2-12`) |
| scene | `configs/scene/train.yaml` | support true; **`decompose_objects: true`**; object scale 1.0-1.0 (no randomization); friction 1.0; free-joint damping 0 (`:1-8`) (re-checked) |
| collision | `configs/collision/training.yaml` | robot-robot (self) on, robot-object on, **robot-support off**, ground on (`:2-6`) |
| embodiment | `configs/embodiment/sharpa_hands.yaml` -> `embodiments/sharpa_hands.py:46-64` | two floating SharpaWave hands, 22 finger joints each |
| action | `configs/action/residual_hand_pose.yaml` | residual: pos scale 0.05 / clip 0.2 m; ori 0.15 / clip 1.0 rad; fingers 0.15 / clip 1.0; EMA 0.3; wrist kp 25, tau max 45; delay 0 (`:4-17`) |
| objective | `configs/objective/tracking.yaml` | contact support 10 (tol 0.1, var 0.1); missed −1; unintended −10; termination −100; action rate −0.005; action L2 −0.002; contact force and force closure 0; 512 wrench directions, 8 cone edges, mu 0.1 (`:1-65`) |
| termination | `configs/termination/tracking.yaml` | wrist pos 0.15 m; wrist ori off; object pos 0.10 m; object ori 0.50 rad; reference end on (`:1-20`) (re-checked) |
| reset | `configs/reset/reference.yaml` | finger openness 0.7; first-frame prob 0.1; first-frame VOC threshold 0.1; `voc_decay_steps` 20 (step); seed 42 (`:1-8`) (re-checked) |
| env | `configs/env/rl.yaml` | VOC k_lin = k_ang = 400, d = 40, max force 200 N, max torque 50 N·m, g 9.81; voc_scale 1; auto_reset (`:4-26`) |
| curriculum | `configs/curriculum/tracking_250m_mixed_reset.yaml` | 11 stages, identical weights each stage (`:6-22`) (re-checked) |
| training | `configs/training/reference_flash_sac.yaml` | C.9 |

### C.2 Reward (what the policy is optimized for)

`r = frame_dt * sum_i w_i * term_i`, `frame_dt = 0.05` (`objectives/composition.py:119-122`); learner recomputes
from raw terms with the current stage's weights (`training/flash_sac/learner.py:816,1058,1069-1081`), then
normalizes by `max(sqrt(return var), max|return|/5)` (`training/flash_sac/reward_normalization.py:114-140`).
Kernel `exp(-max(sqrt(SSE)-thr,0)/var)`, thr 0 (`objectives/shaping.py:22-30`).

| Term | Weight | Definition |
|---|---|---|
| `object_keypoints` | **20.0** | 6 keypoints per body at **±1 m unit axes** in the object frame (`objectives/keypoints.py:18-21`, re-checked), each `exp(-‖d‖/0.1)`, averaged over 6·B (`objectives/tracking.py:199-200`); target = reference pose at current frame (`runtime/command.py:183-192`) |
| `hand_keypoints` | 0.25 | palm + 5 distal phalanges per hand vs FK of reference joints, `exp(-‖d‖/0.1)` (`keypoints.py:51-77`) |
| `hand_joint_pos` | 0.25 | per hand `exp(-‖Δq‖/1.0)` over 22 joints (`objectives/joints.py:17-40`) |
| `contact_wrench_support` | **10.0** | 512 directions on the 6-D wrench sphere; reference support from **MANO contact labels**, sim support from 17 contact links per hand; `exp(-loss/0.1)` outside a ±10% band (`objectives/wrench.py:21-235`; `objectives/contact.py:119-164`; `runtime/contact.py:240-386`); torque normalized by `object_mesh_radius` |
| `missed_contact` | −1.0 | fraction of reference-active directions not covered (`contact.py:167-202`) |
| `unintended_contact` | **−10.0** | contact on bodies the reference marks no-contact; summed over hands (`contact.py:205-242`) |
| `termination` | −100 | on termination only (`composition.py:113`) |
| `action_rate_l2` / `action_l2` | −0.005 / −0.002 | on mapped residual input (`runtime/hand_pose.py:245-261`) |
| `contact_force_l2`, `force_closure` | 0 | disabled (README recommends `force_closure` for noisy ego contacts, `RG/README.md:265-267`) |

Curriculum changes only VOC scale and first-frame reset probability, never weights (re-checked).

### C.3 Observation (policy; 504-D for one body, helper's count)

No observation noise; exactly one reference frame (the next target), no future horizon
(`envs/observation.py:290-370,496-500,522-671`): wrist pose/velocities (world / wrist frame), finger q
(normalized) and q̇, object pose (world), wrist command (reference relative to current), finger command
(q_ref − q), object command (reference in object frame), raw (56) + processed (58) action, per-link contact
position/force direction (204·B, zeroed at step 0). Critic additionally gets applied/target VOC, settling
progress, reference phase, object world velocity (`envs/rl.py:66-113`).

### C.4 Action

56-D = 2 × (3 pos + 3 RPY + 22 fingers), **residuals on the retargeted reference** (`runtime/hand_pose.py:172-186,
263-307`; mapping `runtime/residual.py:61-100`). Wrist: prismatic position targets kp 25 N/m, kd 6, 45 N
(soft; a `sharpa_hands_stiff` variant uses kp 6000, `embodiments/sharpa_hands.py:56,67-75`); ball wrist via
effort tau = 25·rotvec err, ±45 N·m. Fingers kp 1.7, kd 0.1, effort 10 (`embodiments/base.py:34-39`).
Gravity compensation on hand bodies. 20 Hz policy, 5 substeps.

### C.5 Assistance: virtual object controller (`runtime/object_control.py`)

Per substep wrench on each object root (`envs/base.py:294-307`): `F = m(400Δp − 40v) + m g ẑ`,
`τ = I_eff(400·rotvec(q_ref q⁻¹) − 40ω)` with `I_eff = trace(I)/3`, all × scale, clamped ±200 N / ±50 N·m
(`object_control.py:116-134`, re-checked). Gravity compensation is scaled too. After every sampled reset the
VOC is 1.0 for 20 control steps (1 s) with the reference frame held, then drops to the stage value
(`lifecycle/reset.py:376-381,415-433`).

| Stage start (M steps) | 0 | 19.7 | 34.4 | 49.2 | 63.9 | 78.6 | 93.4 | 108.1 | 122.9 | 137.6 | 200.0-250.0 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| VOC scale | 1 | .75 | .5 | .25 | .1 | .05 | .025 | .01 | 0 | 0 | 0 |
| P(start at frame 0) | – | – | – | – | – | .1 | .1 | .1 | .1 | .1 | **.5** |

(First-frame probability applies only once VOC < 0.1.) Fully unassisted training is the last ~127M steps.

### C.6 Termination

Per world (`lifecycle/termination.py:136-221`): palm position error > 0.15 m, object position error > 0.10 m,
object geodesic orientation error > 0.5 rad; wrist orientation off; truncate at reference end
(`:328-343`). No other time limit.

### C.7 Reset

Uniform reference frame in [0, N−2] (frame 0 with prob p when VOC < 0.1) (`reset.py:365-373`); joints and
object exactly at reference, zero velocity (`:78-122`); fingers opened to `u·q_ref`, `u~U(0,0.7)` (`:111-119`).
No domain randomization. **Evaluation instead uses frame 0, exact fingers, no hold, VOC 0** (`reset.py:385-400`),
a start state training almost never produces.

### C.8 Simulation and object assets

MuJoCo-Warp via Newton `SolverMuJoCo` (`runtime/sim.py:1-69`; newton 1.2.0, mujoco-warp 3.8.1, warp 1.14.0,
`robotic_grounding/flash_chord/pyproject.toml:11-25`). dt 0.01 s. Contact ke 1e3 / kd 1e2, margin 0, gap 0
(`embodiments/sharpa_hands.py:200-203`; copied to objects `scene/objects.py:110-116`) -> soft contacts
(~0.02 s time constant, helper's derivation from Newton source). Friction 1.0 everywhere
(`scene/builder.py:266-269,507`). Object: URDF floating root, **mass/inertia from the URDF `<inertial>`**
(`scene/objects.py:387-393`, re-checked `ignore_inertial_definitions=False` at :392) — with the baseline URDF
that is 0.3 kg for every object (B.4). Each collision mesh is replaced by **CoACD** hulls (threshold 0.05,
unlimited hulls; `assets/mesh.py:62-96`, `scene/objects.py:159-210`, re-checked); parameters not exposed to
Hydra (`scene/setup.py:68-73`). Support: USDA Cube/Cylinder prims as kinematic shapes, **prim rotation ignored**
(identity quaternion, `scene/support.py:66-119`, re-checked :102,107), support file mandatory (`setup.py:61-66`).

### C.9 Training

FlashSAC (JAX port of Holiday-Robot/FlashSAC @87edc906, `training/flash_sac/NOTICE`); distributional double
critic, 101 atoms (`network.py:366-426`). 4096 worlds, 250M env steps (61,036 collections, 488,288 updates),
batch 2048, 3-step returns, gamma 0.99, LR 3e-4 -> 1.5e-4 cosine, fp16. README asks for a 48 GiB GPU;
wall-clock UNVERIFIED (CHORD paper reports ~2 h/sequence at 2048 envs on L40S, per track3-requirements.md).

### C.10 Evaluation (what the official evaluator changes)

`apply_evaluation_composition` (`evaluation/harness.py:216-251`, re-checked): `auto_reset=False`,
`voc_scale=0`, VOC `max_force=max_torque=0`, `always_reset_to_first_frame=True`, `voc_decay_steps=0`, seed 42,
failure terminations disabled, reference-end truncation required; curriculum stage VOC forced to 0
(`:265-272`). Policy deterministic `tanh(mean)` (`harness.py:457-465`). Everything else (friction,
substeps, CoACD, `motion_speed`) comes from the checkpoint config (`harness.py:377-420`).
Recording: object body origin `body_q` after each step paired with reference frame k (`evaluation/rollout.py:
283-290,392-402`). Export schema `flash_chord_object_trajectories_v1` (`rollout.py:59-105`, re-checked):
per row `step`, `reference_frame` (index into the **resampled** reference), `time_s` (= step/20, sim time),
achieved and reference position/quaternion (xyzw); metadata has control fps and start frame but **not
`motion_speed` or source fps**. How the kit maps rows back to source video frames/mocap is UNVERIFIED here
(read `metric_code/track_3` in the kit).
Internal metrics (`evaluation/metrics.py`, vs **reference**, not mocap): ADD over 500 visible-mesh vertices;
AUC over 0.01-0.09 m; SP-SR (≤0.1 m and ≤0.5 rad mean); MP-SR (<3 cm and <30 deg per object); RPE (cm, 0
for one object); MPPE (±5 cm keypoints). Useful as a GT-free self-check of policy tracking.

### C.11 Embodiments and required reference fields

Embodiments: `sharpa_hands` (default, floating), `sharpa_hands_primitive`, `sharpa_hands_stiff`,
`dexmate_sharpa` (Vega, motion_v1), `g1_dex3` (motion_v1). ManoSharpaData validation in
`data/mano_sharpa.py:175-310` (loader dispatch `data/loader.py:14-66`) requires: `fps`; `object_name`;
`object_body_names[B]`; `object_body_position (T,B,3)`; `object_body_wxyz (T,B,4)`; `object_mesh_paths[B]`;
`object_mesh_radius[B] > 0`; `object_urdf_paths[B]`; both hands' `robot_{side}_wrist_position/wxyz`,
`robot_{side}_finger_joints (T,22)` + joint names, `robot_{side}_frames` + names; per side
`mano_{side}_object_contact_positions/normals (T,K,3)` and `..._part_ids (T,K)` (1-indexed, 0 inactive,
unit inward normals). **Multiple rigid bodies (B>1) are supported by the format**; the ego loader only
emits B=1. Hive partition `sequence_id=…/robot_name=…` locates `reconstructed_stage/<seq>[_<robot>]_support.usda`
(`assets/registry.py:114-160`). Resampling: duration `(N−1)/fps`, `int(duration·20/0.5)` samples, lerp/slerp,
contacts nearest (`data/resampling.py:21-41`, re-checked; `mano_sharpa.py:235-300`).

### C.12 Fragility for a thin wooden spoon (helper analysis; mostly inference)

Zero margin/gap with soft contacts at 100 Hz -> thin hulls can tunnel or be squeezed out; CoACD at 0.05 may
fill the bowl or poorly wrap a ~5-10 mm handle; roll about the long axis is weakly observable in video yet
heavily weighted by the 1 m keypoints and the 0.5 rad termination; large bounding radius down-weights the
torque part of the wrench reward; support prims cannot be tilted. All UNVERIFIED in simulation.

## D. Track 3 data fit

Data facts are from the task statement and `reports/v2d-challenge/track3-requirements.md` (head-mounted
OAK; colour `ego_cam_a` 2028x1520 mounted 180 deg; mono stereo pair `ego_cam_b/c` 1280x800, 75 mm
baseline; ~20.25 fps; ~262 frames; 1-2 objects; factory calibration with inter-camera extrinsics; no
IMU stream; `wooden_spoon` unscanned, in 10/20 eval episodes).

| Data property | What the baseline does | Consequence | Fix direction |
|---|---|---|---|
| Colour image upside down (180 deg mount) | Feeds the raw MP4 to every learned model (RW:839-1151) | MoGe, GeoCalib, WiLoR/HaMeR, DINO, SAM3D and FP are trained on upright imagery; a 180 deg roll is outside GeoCalib's typical roll prior (UNVERIFIED) and likely degrades hand detection/handedness (UNVERIFIED) | Rotate frames 180 deg before any model; transform K (`cx'=W-1-cx`, `cy'=H-1-cy`) and compose `diag(-1,-1,1)` into camera extrinsics; rotate results back only if a consumer needs the native frame. |
| Factory intrinsics + distortion available | Estimates K per frame with MoGe (median-stabilized) or AnyCalib/GeoCalib (A.1 #0,#2) | Focal error -> depth/scale error and per-frame inconsistency | Undistort with factory calibration; pass fixed K everywhere. Note MoGe accepts only an FoV prior and assumes centred principal point (`video_to_depth.py:94-98,126-133`), so either crop/pad to a centred principal point or replace MoGe depth. |
| Calibrated 75 mm mono stereo pair | Unused; all metric scale from monocular MoGe | Scale error is scored directly (AUC/SR thresholds 1-10 cm; scorer does not correct scale) | Metric stereo depth (repo has `v2d_foundation_stereo`, see E), registered into the colour camera via factory extrinsics; use it for FP depth, object-scale search, hand alignment, and DROID metric prior (`input_depth_folder`) or DROID stereo mode. Expected depth noise ~1.5-3 mm per 0.25 px disparity error at 0.5-0.7 m (track3-requirements.md estimate, fx ~562 px). |
| ~20.25 fps | Loader/registry assume 30 fps (`ego_recon_loader.py:86,465-467`; `dataset_registry.py:252`) | FlashCHORD derives duration `(N−1)/fps` from the Parquet `fps` and plays at 0.5x (C.11). At 30 fps the simulated motion runs ~1.48x faster than intended (faster object motions, different dynamics); whether the kit's row-to-mocap mapping also uses this fps is UNVERIFIED | Write the measured fps (OAK timestamps) into the Parquet; check the kit conversion. |
| Evaluation starts at exact frame 0 (C.10) | Frame-0 object pose from one-shot FP registration; MANO fingers often inside the object (B.1) | Initial penetration or a floating/tilted object at frame 0 is resolved by the contact solver at step 1 with no VOC; the Kaggle scorer also aligns each episode with slot 0's frame-0 pose (track3-requirements.md) | Make frame 0 the best-estimated, physically valid state (resting on support, no penetration). |
| Contact labels drive +10/−1/−10 reward terms (C.2) | 1 cm MANO-object proximity (B.2) on monocular geometry | Noisy labels make the policy avoid useful contacts or pay unintended-contact penalties | Derive contacts from refined, metric hand-object geometry; temporally filter; consider `force_closure` (README). |
| ~262 frames (~13 s) | Online-style components (FP forward from frame 0, DROID frontend) | Short clips favour offline global optimization (batch smoothing in world frame, bidirectional tracking) | Offline world-frame smoother with object-static priors. |
| 1-2 objects | One object (RW:941-942; loader single body `ego_recon_loader.py:272,435`) | Second object missing entirely from reference/sim | Run object branch per object (one SAM2 id per object), extend bundle and loader to N bodies (C tells whether FlashCHORD scene supports multiple bodies). |
| Thin, unscanned wooden spoon | SAM3D single-view mesh (8a) + scale search on one MoGe frame (8b) + FP with monocular depth | Thin geometry yields few depth pixels; SAM3D likely mis-estimates thickness/length; near-rotational symmetry about the long axis makes FP re-registration flips likely; CoACD hulls (threshold 0.05) may fill the bowl or poorly wrap the handle (C.8, C.12) | Multi-view model-free reconstruction over the clip (BundleSDF-type, see E) with stereo depth; or best-frame SAM3D + stereo-metric scale + silhouette refinement; symmetry-aware tracking; physical mass prior for a spoon. |
| Kaggle rule: no hand labeling on test records | NVIDIA's shipped sample used human scene-alignment corrections (`RG/.../ego_recon/datacard.md`, Labeling Method "Hybrid: Automated, Manually-Labeled"; `level_result_bundle.py:30-34`) | Manual leveling/scaling as done for the demo is not allowed on eval episodes | Every correction must be automatic and identical across episodes. |

## E. Repo modules the ego path does not use (swap-in candidates)

Helper survey; citations under `M/`. Never imported by the ego path: foundation_stereo, bundlesdf, cusfm,
all `mv*`, hoi_object_reconstruction, cari4d, unidepth, depth_anything, mesh, sam3d_body, detectron2,
rosbag. Partly used: `v2d_foundation_pose` (depth-alignment and multi-view tools unused), `v2d_depth`
(`align_depth_sequence` unused).

| Module | Upstream / pin | Entry | Track 3 use | Caveats |
|---|---|---|---|---|
| **v2d_foundation_stereo** (E.1) | NGC TAO ONNX `deployable_foundationstereo_small_576x960_v2.0` (`v2d_foundation_stereo/lib/download_weights.py:11-15`), TRT 24.12 | `image_list_to_depth` (`lib/image_list_to_depth.py:78`); `FoundationStereoInference.infer` (`lib/trt_inference.py:30,238`) | Metric depth on the rectified 1280x800 mono pair; then register into the (rotated) colour frame | Expects pre-rectified pairs paired by filename; calibration JSON `fx,fy,cx,cy,baseline` (m) (`:53-75,203-210`); fixed 576x960 input (1280x800 -> 921x576 + pad, `trt_inference.py:17-19,167-207`); FP32 engine; **grey mono PNGs must be written as 3-channel** (RGB2BGR call, `image_list_to_depth.py:158-159`); trained on RGB (grey performance UNVERIFIED). Output: inverse-depth PNG in left-rectified frame. No repo code reprojects mono depth into the colour camera: must be written. |
| v2d_mv_preprocess | OpenCV | `image_proc_build_rectify` (`lib/image_proc/proc_cv2.py:52`) | Rectification (`cv2.stereoRectify(alpha=0)`, `:65-110`) | Expects EDEX/ROS-style R,P; 8-coeff rational distortion (`v2d_mv/rig/edex.py:53,110-113`) vs DepthAI's 14 (UNVERIFIED zeros). Simpler to rectify from OAK calibration directly. |
| v2d_foundation_pose helpers | in-repo | `run_align_depth_to_reference_depth` (`lib/run_align_depth_to_reference_depth.py:21`; `lib/depth_alignment.py:23`) | Per-frame scale/shift of dense MoGe depth to stereo depth on background pixels (hands/object masked) | Keeps MoGe density, inherits stereo metric scale. |
| v2d_foundation_pose multi-view | in-repo | `MultiViewTracker` (`lib/multiview_tracker.py:124`), `mv_videos_to_poses` (`lib/mv_videos_to_poses.py:219-262`) | HYPOTHESIS: colour + left mono as a fixed 2-camera rig for object pose | FP on grey images UNVERIFIED. |
| v2d_cusfm | pyCuSFM HEAD **unpinned** (`docker/Dockerfile:18-22`) | `create_cusfm_runner(...).run_all()` (`lib/image_list_to_sfm.py:23-47`) | Metric stereo camera trajectory (cuVSLAM init) to replace/check DROID | `cfg_max_frame_delta_s: 0.034` (`configs/cuvslam_config/default.yaml:15`) vs our 0.05 s frame gap (risk UNVERIFIED); preflight rejects Blackwell (`docker/gpu_compatibility.py:15`). |
| v2d_bundlesdf | NVIDIA/3DObjectReconstruction `e7aa98d` + NVlabs/BundleSDF `56f2119` (`docker/Dockerfile:160,250`) | `run_reconstruct` (`docker/run_reconstruct.py:31`) | Fused metric mesh from known object poses + depth + masks (CD-O mesh) | Not online tracking; needs poses first; trains at 0.2x resolution (thin spoon handle ~1-3 px, HYPOTHESIS); HOI README warns thin geometry goes missing or thickened (`v2d_hoi_object_reconstruction/README.md:611,650`). |
| v2d_hoi_object_reconstruction | cuSFM + FS + SAM2 + BundleSDF/SAM3D | `estimate_srt_for_frame` (`lib/scale_mesh_srt.py:1198`) | Multi-view similarity fit of a SAM3D mesh with silhouettes + stereo depth (per-axis scale option, `:1313-1342`) for spoon size when it rests | Full pipeline expects a dedicated static scan (orbit ≥600 deg, `README.md:446-458`); assumes static object. |
| v2d_mesh | trimesh | `mesh_align_depth` (`lib/mesh_align_depth.py:10`) | One-frame metric mesh scale from stereo depth | Unmasked least squares (`:36-49`): occlusion bias. |
| v2d_hawor (already used) | HaWoR `main` **unpinned** (`docker/Dockerfile:13-17`) | `run_hawor` (`lib/run_hawor.py:494`) | World-frame hands + SLAM scale as a cross-check | World output (`world_space_res.pth`) discarded (`:283,341`). |
| v2d_depth_anything | DA3 unpinned | `video_to_depth` (`lib/video_to_depth.py:53-66`) | Multi-view-consistent depth accepting known K | Monocular scale still. |
| v2d_unidepth | unpinned | `video_to_depth` (`lib/video_to_depth.py:37,62`) | Alternative mono depth | Ignores known K without a patch. |
| v2d_rosbag | `rosbags` | `rosbag_to_edex` (`lib/rosbag_to_edex.py:19-42`) | OAK mono-pair config exists (`oak6.yaml:4-15`) | Only if data were bags (Track 3 ships videos, per requirements note). |
| v2d_detectron2 | `a1ce2f9` | `run_detectron2_vitdet` (`lib/build_detector.py:105-131`) | Possible spoon detector (COCO "spoon", UNVERIFIED id) | |
| v2d_cari4d, v2d_sam3d_body, v2d_mv_calibration | | | Skip: full-body / chessboard assumptions | |

Pipeline templates: `run_video_object_tracking.py:3-16` (SAM2 + MoGe + SAM3D + `mesh_align_depth` + FP:
swap MoGe for registered stereo depth); `run_ego_wilor_with_obj.py:3-35` (ego pipeline with a trusted mesh);
`run_mv_hoi_reconstruction.py` + `docs/mv_hoi_local_pipeline.md` (4 static Hawk stereo rigs; template only).
Practical shortcut found by the helper: stages are cache-by-existence, so pre-filling `<out>/depth/*.png`
(16-bit inverse depth, rotated colour frame) and `<out>/intrinsics_stable.json` makes the existing chain
(DROID scale, FP scale search, FP tracking, hand alignment) consume metric stereo depth without code edits
(`RW:716-718,850,859-860,870-877,1077-1143`). HYPOTHESIS until run.

---------------------------------------------------------------------------------------------------

## F. Ranked weaknesses / upgrade opportunities

Ranking = expected effect on the scored object trajectory (AUC 1-9 cm, SP-SR, MP-SR 3 cm/30 deg, RPE, MPPE)
× confidence. All effects are HYPOTHESES until measured on the 20 public episodes with mocap.

### F.1 Reconstruction (A)

1. **Metric depth from stereo instead of MoGe** (A.2, E.1). Feeds object size, object/hand translation,
   camera scale. Falsifier: on public episodes, scanned-object size from our pipeline vs scan (should be
   within ~2%) and object-trajectory ADD vs mocap before/after.
2. **Camera trajectory in a fixed, metric, gravity-aligned world.** Baseline: none (identity) unless DROID
   monocular with unmasked MoGe-ratio scale (`_slam.py:83-116,261`). Upgrade: stereo SLAM/VO (DROID stereo
   mode, cuSFM/cuVSLAM, or DROID with `input_depth_folder` metric prior), hands/objects masked; gravity from
   table-plane fit + GeoCalib on correctly rotated frames.
3. **Object 6-DoF tracking robustness.** FP on monocular depth; occlusion-unaware IoU re-registration
   (`foundation_pose_tracker.py:213-218`); single anchor frame; EKF in the camera frame and bypassed by gsplat.
   Upgrade: FP on stereo-registered depth, occlusion-aware recovery (exclude hand-mask pixels from IoU or use
   amodal rendering), bidirectional tracking from several anchors, offline world-frame smoother with
   "static unless touched" and "rests on support" priors, symmetry handling for the spoon.
4. **Frame-0 pose of object slot 0.** Scorer aligns each episode with it; evaluation starts from it. Use
   multi-frame registration over the initial static span.
5. **Multi-object support** (A.0): one SAM2 track + mesh + FP track per object; extend bundle/loader to B
   bodies (FlashCHORD format already supports B>1, C.11).
6. **Object mesh (sim collision and CD-O).** SAM3D single view on frame 0; scale from one MoGe frame.
   Upgrade: best-frame selection + stereo-metric similarity fit (`estimate_srt_for_frame`) + multi-view
   refinement; for CD-O, Sim(3)-registered Chamfer means shape matters more than scale.
7. **Input conditioning:** rotate the 180-deg colour stream, use factory K/distortion (D).
8. **Hands:** translation-only per-frame depth alignment and WiLoR/HaMeR jitter (finger velocity spikes ~50
   rad/s, `ego_recon_to_sharpa.py:136-141`). Matters through the residual action base and contact labels.
9. **Reproducibility:** pin DROID-SLAM, GeoCalib, sam-3d-objects, HaWoR, cuSFM, IsaacTeleop vendor sync.

### F.2 Ego -> robot (B)

1. **fps** (30 hard-coded vs ~20.25).
2. **Ground/gravity:** thinnest-PCA-axis "up" at frame 0 (`ego_recon_loader.py:187-201`) is arbitrary for
   pots/cups; replace with estimated table plane + gravity; place support at the measured table height.
3. **Support surfaces from still-runs** with 1 mm/frame threshold (`support_recon.py:228-283`): jitter
   drops supports; held-still objects create false supports. Use the measured table plane (horizontal prims
   only, since prim rotation is ignored, C.8).
4. **Contact labels** (1 cm proximity) feed +10/−1/−10 reward terms (C.2): recompute from refined geometry,
   temporally filter, correct handedness.
5. **De-penetration/smoothing off by default** (`--surface_project`, `--smooth_reference`,
   `--adaptive_offset`): enable/tune so the reference is physically feasible, especially at frame 0.
6. **Object inertial:** 0.3 kg / 0.001 inertia for all objects (`generate_rigid_urdfs.py:103-131`), used by
   the sim (C.8). Mesh-volume × density prior is more plausible; whether this counts as "our asset" or
   "physics" needs organizer confirmation.

### F.3 FlashCHORD training (C) — free to change (only `evaluation/{__init__,harness,metrics,rollout}.py` are digested, per track3-requirements.md)

1. **Train for the evaluation start:** raise frame-0 reset probability earlier than 200M steps, set
   `voc_decay_steps=0` and finger openness near 1 in late stages (C.5, C.7).
2. **More unassisted training** (VOC hits 0 at 122.9M of 250M steps) and **several seeds per episode**,
   selected by FlashCHORD's own internal metrics vs our reference (GT-free; C.10).
3. **Reward-metric alignment:** object keypoints at ±1 m weight rotation ~20x more than the ±5 cm MPPE
   keypoints or ADD on real object size (C.2). HYPOTHESIS: size-scaled keypoints track position better.
4. **Contact terms:** consider `force_closure` (README) or down-weighting `unintended_contact` when labels
   are noisy.
5. Not recommended: changing `motion_speed`, friction, substeps, termination thresholds or CoACD parameters
   (they are read from the checkpoint and change the evaluated physics/timing; likely disallowed).

### F.4 Levers most likely to raise object-tracking scores without touching the evaluator/physics

In order of expected impact (HYPOTHESES, to be tested on public episodes):

1. **Reference accuracy vs mocap** (metric stereo depth, fixed gravity-aligned world, robust object
   tracking). The policy tracks our reference; reference error is a floor on every metric.
2. **Correct timing**: true fps in the Parquet; verify the kit's frame mapping.
3. **Frame-0 state**: accurate slot-0 frame-0 pose; object resting on a support; no hand-object
   penetration; fingers consistent with contact labels.
4. **Physically feasible reference**: static objects static, on supports; smooth wrist/finger reference;
   contact labels consistent with geometry.
5. **Train-eval start matching and longer unassisted training, multi-seed selection** by self-evaluation
   against our own reference.
6. **Object asset quality**: collision mesh that CoACD can decompose faithfully (watertight, correct
   thickness for the spoon), plausible mass/inertia in the URDF (organizer question).
7. **Multi-object episodes**: include the second object so RPE/MP-SR count it.

Open questions for organizers: whether URDF mass/inertia and CoACD-friendly collision meshes are
participant-controlled; how the kit maps exported `reference_frame`/`time_s` to mocap frames when
`motion_speed=0.5`; how the spoon's (unpublished) scan frame is reconciled with our mesh frame when the spoon
is not object slot 0; whether public scans may be used as tracking priors on eval episodes.
