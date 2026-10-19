# MANO-free reference build for FlashCHORD (Track 3)

Pipeline per public episode N:
`perc.py` poses + depth  ->  `hands_mp.py` (MediaPipe on colour cam_a, lifted with stereo depth)  ->
`mkref.py` (table frame, Sharpa IK through the unchanged `ego_recon_to_sharpa.py`, contacts, validation)  ->
`train_flash_sac.py`  ->  `run_policy_evaluation.py`.

Copy `hands_mp.py` and `mkref.py` to `/content/` (or adjust the paths below).

## Environments (already present on the Colab VM; listed for rebuilds)

```bash
# MediaPipe venv (CPU)
uv venv --python 3.11 /content/mpvenv
uv pip install --python /content/mpvenv/bin/python mediapipe==0.10.14 opencv-python-headless numpy scipy pyarrow

# Retarget venv (CPU). E2S needs scipy>=1.14 (Rotation(..., scalar_first=True)).
uv venv --python 3.11 /content/rtvenv
uv pip install --python /content/rtvenv/bin/python pin pin-pink daqp qpsolvers "viser>=0.2.11,<0.3" \
    loop-rate-limiters trimesh rtree "scipy>=1.14" pyarrow pandas tqdm opencv-python-headless
uv pip install --python /content/rtvenv/bin/python torch --index-url https://download.pytorch.org/whl/cpu
# check
/content/rtvenv/bin/python -c "import scipy, pinocchio, pink, qpsolvers, viser, torch, trimesh, loop_rate_limiters; \
print(scipy.__version__, pinocchio.__version__, qpsolvers.available_solvers)"   # must list 'daqp'
```

`robotic_grounding` is not installed. `mkref.py` adds
`/content/v2d/robotic_grounding/source/robotic_grounding` to `sys.path`, and passes it as `PYTHONPATH` to its E2S
subprocess. It also installs three shims before E2S imports anything:
- `hppfcl` is aliased to `coal`, or replaced by a stub. It is only used by the unused viser visualizer.
- `RobotWrapper.BuildFromMJCF` builds the kinematic model only, so the Sharpa STL meshes, which may be LFS
  pointers, are never loaded.
- `ManoSharpaData` gets a schema patch if pin 4.x reports a frame, finger-joint or task count other than the
  67 / 22 / 11 hard-coded in `data_logger.py`.

E2S itself is not modified.

## Per episode

```bash
EP=12
# 1) hands: cam_a video /content/t3/v/ep${EP}_a.mp4, depth /content/perc/ep${EP}/depths_fs0.5.npy,
#    world_T_cam from /content/perc2/ep${EP}/poses.npz
/content/mpvenv/bin/python /content/hands_mp.py --ep $EP            # --a_offset 1 (default; set 2 for k+2 clips)
#    -> /content/refs/ep$EP/{hands.npz, hands_overlay.jpg, hands_log.json}

# 2) reference
PYTHONPATH=/content/v2d/robotic_grounding/source/robotic_grounding \
  /content/rtvenv/bin/python /content/mkref.py --ep $EP              # --table_z 0.60 --fps 20.0 (defaults)
#    -> /content/refs/ep$EP/processed/sequence_id=t3_ep012/robot_name=sharpa_wave/<uuid>-0.parquet
#       /content/refs/ep$EP/reconstructed_stage/t3_ep012_support.usda
#       /content/refs/ep$EP/ref_summary.json  (table fit, hand fill/park, contacts, IK errors, validation)
```

Useful `mkref.py` flags:
- `--e2s_args "--smooth_reference"` passes flags through to E2S. `"--surface_project"` is also available.
- `--skip_e2s` redoes contacts and validation from `e2s_raw/`.
- `--snap none|lowest|per_object` controls how objects are snapped onto the table.
- `--gap_fill hold|attach` controls how hand gaps are filled.
- `--no_motion_gate`, `--contact_thr 0.018`.
- `--no_scene_check` skips the Newton scene build in validation.

**Support surface: no env var is needed.** `flash_chord.assets.registry.support_usda_for_parquet`
(`registry.py:114-134`) looks for the support next to the parquet. For a parquet under
`.../sequence_id=<seq>/robot_name=<robot>/`, it looks in `<that dir>/../../../reconstructed_stage/` for
`<seq>_<robot>_support.usda`, then `<seq>_support.usda`. `mkref.py` writes the second name there.
Object URDF and mesh paths are stored as absolute `/content/t3/...` paths. `resolve_asset_path` returns any path
that exists unchanged. `V2D_ASSETS_DIR` is not read by flash_chord at this pin.

## Train (timing rule: fps 20, N frames, motion_speed 1.0, sim=rl at 20 fps)

```bash
cd /content/v2d/robotic_grounding/flash_chord && \
MUJOCO_GL=egl XLA_PYTHON_CLIENT_PREALLOCATE=false .venv/bin/python scripts/train_flash_sac.py \
  experiment=sharpa_flash_sac \
  "task.parquet='/content/refs/ep12/processed/sequence_id=t3_ep012/robot_name=sharpa_wave'" \
  task.motion_speed=1.0 reset.seed=42 logging.mode=disabled \
  output_dir=/content/runs/ep12 training.total_environment_steps=250003456
```

- The inner single quotes make Hydra treat the path, which contains `=`, as a string.
- `experiment=sharpa_flash_sac` already selects `sim: rl` (fps 20) and `scene.world_count=4096`. Its YAML sets
  `task.motion_speed: 0.5`, and the command-line override replaces it.
- Checkpoints are written as `/content/runs/ep12/policy_<env_steps>.safetensors` (plus `state_*`).

## Evaluate (official evaluator, world_count 1, trajectory parquet export)

```bash
echo '{"12": "/content/runs/ep12/policy_<env_steps>.safetensors"}' > /content/runs/checkpoints.json
cd /content/v2d/robotic_grounding/flash_chord && \
MUJOCO_GL=egl XLA_PYTHON_CLIENT_PREALLOCATE=false .venv/bin/python \
  /content/kit/v2d_submission_kit/examples/run_policy_evaluation.py \
  --checkpoints /content/runs/checkpoints.json --results /content/results --world-count 1 \
  --runtime-root /content/v2d/robotic_grounding/flash_chord
#  -> /content/results/episode_000012.parquet (object trajectories) + episode_000012.json (metrics)
```

The runner calls the kit copy of `flash_chord/scripts/evaluate_policy.py`, which is byte-identical to the pin.
It passes `evaluation.reset_mode=explicit` and `logging.mode=disabled`. The environment, including `task.parquet`
and `motion_speed`, is rebuilt from the checkpoint's stored config, so leave `/content/refs/...` in place, or add
`--source-root` if the files move. The equivalent single call is:

```bash
.venv/bin/python scripts/evaluate_policy.py evaluation.checkpoint=/content/runs/ep12/policy_<steps>.safetensors \
  evaluation.world_count=1 evaluation.reset_mode=explicit \
  evaluation.metrics_output=/content/results/episode_000012.json \
  evaluation.object_trajectories_output=/content/results/episode_000012.parquet \
  hydra.run.dir=/content/results/hydra/episode_000012 logging.mode=disabled
```

## Conventions written by mkref.py

- One row. `fps = 20.0`, and T equals `len(world_T_cam)`, the perception / video frame count. Partition columns are
  `sequence_id`, then `robot_name=sharpa_wave`.
- World is the table frame: z up, table top at `TABLE_Z`, x along the camera's forward direction projected onto
  the table, origin under the objects' frame-0 centroid. Units are metres; quaternions are wxyz.
- `object_body_*` follows the episode's slot order. `object_urdf_paths` is `/content/t3/urdf/<n>_rigid.urdf`.
  `object_mesh_paths` is `<n>.glb`, or `<n>_visual.glb` if that is missing. `object_mesh_radius` is the max vertex
  distance from the vertex mean.
- `robot_{s}_*` come from E2S. `mano_{s}_joints` holds MediaPipe joints in the table frame, in the same index order
  as MANO. `mano_{s}_joints_wxyz` holds anatomical frames.
- Contacts use 16 slots: 5 tip sites, 5 DP sites, thumb MCP_VL plus 4 MP sites, and a palm point.
  - A slot is active when the probe-to-surface distance is under 18 mm (28 mm for the palm), the object is inside
    its motion window (±20 frames of motion), and the contact lasts at least 2 frames.
  - The position is the closest surface point. The normal points into the object. The part id is body index + 1.
- A side with fewer than 10% valid frames is parked 30 cm toward the person and 35 cm or more to its side of the
  objects, 25 cm above the table, palm down, with no contacts.
