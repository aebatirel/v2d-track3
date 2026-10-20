[← Index](../README.md) · [Summary](../00-summary.md) · [← 05](05-alternatives.md) · [07 →](07-mesh-frame-convention.md)

# 06 - Track 3 timing and row-alignment audit (FlashCHORD Sharpa policy to kit packer)

Status: COMPLETE (2026-10-04). This audit is based on reading code. No installs, no repo edits and no
FlashCHORD runs. The numeric mappings come from executing FlashCHORD's own `resampling.py` functions
in a scratch venv against the kit's Track 3 row roster.

Source pins:
- FlashCHORD: `nvidia-isaac/video_to_data @ 8c778f905cb35f76f8e6cd6e2ea486da4fb9e0ef`, path
  `robotic_grounding/flash_chord/` (abbreviated `fc/` below). The kit's evaluator copy
  (`flash_chord/scripts/evaluate_policy.py`, `evaluate_policy.yaml`, `evaluation/flash_sac.yaml`) is
  byte-identical to this pin: script sha256 `160d24f5...fdf1`. `KIT_MANIFEST.json` names the same commit.
- Kit: local copy `scratchpad/kit_v2/v2d_submission_kit` (`pack_submission.py` sha256 `47a45895...`).
- Track 3 public data: `scratchpad/t3/public`. Numeric check script:
  `scratchpad/analysis_timing_map.py`, run with `scratchpad/venv-mf/bin/python`.

## Verdict

**The bug is real and silent under the default Sharpa recipe.** Each exported row is one CONTROL
STEP of a RESAMPLED reference, not one source frame. With `motion_speed: 0.5`, an episode with N
source frames produces about 2N control steps. The packer then keeps the rows labelled
`reference_frame` 0..N-1, which are the first half of the rollout, and drops the rest without a
message. Packed row `f` therefore holds the pose for source frame ~`0.5 f`, and the second half of
every motion is never submitted. Nothing in the kit detects this for Track 3.

## 1. How a source frame becomes a control step (evidence)

1. The checkpoint fixes the timing. `harness.py:377-381` builds the evaluation config from the
   checkpoint's saved config. Only `motion_start_frame` and `motion_end_frame` can be overridden
   (`:384-387`). `motion_speed`, `source_frame_playback` and `sim.fps` are inherited from training
   (`:405-417`). **The official evaluator cannot correct timing; it must be set at training time.**
2. Default Sharpa recipe settings:
   - `experiment/sharpa_flash_sac.yaml:5` uses `sim: rl`, and `:19-23` sets `motion_speed: 0.5`,
     `source_frame_playback: false`, frames 0..-1.
   - `sim/rl.yaml:2-3` sets `fps: 20.0` and `substeps: 5`.
   - `task/default.yaml:4-5` uses the same defaults.
   - `experiment/sharpa_ppo.yaml` and `dexmate_sharpa_flash_sac.yaml` also use 0.5.
3. Resampling:
   - `scene/setup.py:53-59` calls `load_reference(control_fps=sim.fps, motion_speed, source_frame_playback)`
     and then `frame_window`.
   - For the floating-Sharpa format (unversioned `ManoSharpaData`), `mano_sharpa.py:175` reads `fps`.
     `:236` calls `playback_times`, and `:238` sets `resample = control_fps != src_fps or motion_speed != 1`.
     The reference's `fps` is then set to `control_fps` (`:334`).
   - `resampling.py:21-41` (`playback_times`): with speed != 1, `duration=(N-1)/fs`,
     `M=int(duration*fc/speed)` (`:35`), and target source-times `linspace(0, duration, M)` (`:41`).
     With speed == 1 it uses `resample_times` (`:11-18`): `M=round(duration*fc)+1`, times
     `clip(k/fc, 0, duration)`.
4. The environment steps once per resampled frame:
   - `envs/base.py:118-122` requires `reference.fps == sim.fps`.
   - `_transition` gathers targets at `timestep` (`:290`; `command.py:174-179`), simulates `substeps`,
     evaluates termination and reward at the same `timestep` (`:323-325`), then increments `timestep`
     (`:57-66`).
5. Export:
   - `harness.py:423` sets `step_count = reference.num_frames - start_frame`, where `num_frames` is
     the RESAMPLED count M.
   - `rollout.py:392-402` records `body_q` after each `jax_env.step`.
   - `rollout.py:189-190` writes `reference_frame = step + start_frame` and `time_s = step / control_fps`.
   - The metadata records `control_fps`, `start_frame` and `step_count` (`:63-74`), but not
     `motion_speed` or the source fps.
6. Floating Sharpa cannot use `source_frame_playback`. `SharpaHands.bind_reference` requires a
   `HandPoseReference` (`embodiments/sharpa_hands.py:291-293`), which only the ManoSharpa loader
   provides. `loader.py:63-65` raises if `source_frame_playback` is set for ManoSharpa. That flag is
   motion_v1 only (`motion_v1.py:187-190,272-276`), meaning Dexmate/Vega or G1.
7. Kit packer, Track 3 path:
   - `submission_parquet.py:145-149` reads `frame = reference_frame` and `slot = object_body_id`.
   - `pack_submission.py:301-310` builds `wanted` from the roster and `got` from the export.
   - `:322-338` errors only on ABSENT keys.
   - `:340-342` uses `lookup.loc[wanted]`, which silently discards extra steps and extra worlds.
   - The reference-pose cross-check (`:366`) runs only when `public_grid is None`, so it is SKIPPED
     for Track 3.
   - `tools/preflight.py:166-216` has no timing check.
   - Track 2 is protected: `convert_track2_frame` (`:82-130`) requires the evaluator reference to be
     one rigid transform away from the released reference, which a time warp breaks.
8. Scorer: `metric_code/track_3/MPPE.py:189-205` reshapes rows by `frame_index`, and `:113-127`
   aligns world-frame poses using frame 0, slot 0 only. It has no time alignment, so a time warp is
   scored as a pose error.

## 2. Exact control-step to source-frame mapping

Notation: N is the number of source frames, equal to the number of roster frames. The roster is
contiguous 0..N-1 for all 20 scored episodes, with 1 world (w000) and 1-2 slots. `fs` is the `fps`
written into the reference Parquet, `fc` is `sim.fps`, and `s` is `motion_speed`. Row k of the export
maps to source position `p_k = t_k * fs`.

| Case | Mapping row k to source frame | Steps M | Packer outcome |
|---|---|---|---|
| **A default**: s=0.5, fc=20, fs=20.2541 (meta nominal) | p_k = k(N-1)/(M-1), about 0.508k | M=int(2(N-1)·20/20.254) ≈ 1.975(N-1) | **SILENT**: keeps k=0..N-1, so frame f receives source ~0.508f. Ep1: N=335, M=659, row 334 = src 169.5. Ep35: N=421, M=829, row 420 = src 213.0 |
| A' s=0.5, fc=20, fs=20.0 | p_k = k(N-1)/(M-1), about 0.5007k | M=2(N-1) | **SILENT**: ep1 M=668, row 334 = src 167.25 |
| B s=1, fc=20, fs=20.2541 | p_k = k·1.0127 (`resample_times`) | M=round((N-1)·20/20.254)+1 < N | **ERROR**: missing last 2-5 frames (ep1 M=331) |
| **B' s=1, fc=20, fs=20.0 exactly** | p_k = k (no resample: `mano_sharpa.py:238` is False) | M=N | **EXACT** |
| B'' s=1, fc=20, fs≈19.99 (a "measured" value) | p_k = k·fs/fc (lerp) | M=N here; M>N if fs is lower | Silent drift of 0.1-0.2 frames, or more if fs is further below fc |
| C s=1, fc=fs=20.2541... (bit-identical floats) | p_k = k | M=N | EXACT. Changes physics dt; must also be the training config |
| D s=0.5, fc=fs/2 (the "obvious" fix) | linspace(0,D,M) with M=int(N-1) | M=N-1 | ERROR: missing the last frame. Any s!=1 goes through `int()`/`linspace`, so an exact match needs per-episode tuning |
| E `source_frame_playback: true`, s=1 (motion_v1 only) | p_k = k; reference fps forced to fc | M=N | EXACT, but not available for floating Sharpa |
| G1 Track 2 baseline (`g1_recon_body_flash_sac.yaml:15-19`, `sim/recon_body.yaml:2-3`) | s=1, `source_frame_playback: true`, fc=50 | M=N | EXACT rows. Track 2 tier-1 meta fps=30 (HF), so the sim plays 1.67x faster than real time |

NVIDIA's G1 (Track 2) recipe is frame-locked through `source_frame_playback`. Its Sharpa recipe is
not frame-locked, because it was built for training-speed playback and not for leaderboard export.

Track 3 timing facts, from all 20 public episodes:
- `timestamp` is exactly uniform at 1/20.2541 s.
- `capture_time` averages 20.00 fps, with 12-93 ms outliers. Note 02 records the same.
- `frame_index` is contiguous from 0.
- The Track 3 README says video is frame-exact with the Parquet rows.
- Therefore `fs = 20.0` is both the real rate and the value that avoids resampling at `sim.fps = 20`.

Off-by-one convention (consistent; not a bug): the row-k pose is recorded after the transition that
targeted reference frame k (`base.py:290-326`). Reward and termination are computed against the same
frame, so the policy learns to place the object at the frame-k pose by the end of step k. The exact
reset pose is never exported, and row 0 is one physics step after reset. The scorer's frame-0
alignment absorbs this. Uncertainty: a physical lag of about 1 control tick (50 ms) is inherent but is
symmetric with training.

## 3. Correct Track 3 procedure (floating Sharpa)

1. Write each episode's reference as ManoSharpaData with exactly N frames. Frame i must equal video
   frame i, from frame 0 to frame N-1, using the same N as the roster. Do not trim or pad. Write
   `fps = 20.0` as an exact float.
2. Train with `task.motion_speed=1.0`, keep `sim=rl` (`fps: 20.0`), and leave
   `source_frame_playback=false`. The result is no resampling and step k = frame k. Leave
   `motion_start_frame=0`, `motion_end_frame=-1` and `evaluation.start_frame=0`. When resampling
   is active, `frame_window` is applied AFTER it (`setup.py:59`), so these windows count control
   steps, contrary to the docstring at `reference.py:215-216`.
3. Option (HYPOTHESIS) to keep the training-friendly half-speed playback with 1:1 rows: write
   `fps=10.0` in the Parquet and train with `sim.fps=10.0` and s=1. Rows stay exact. The motion plays
   at 0.5x real time with a 10 Hz control rate, which changes dt and stability. The constraint
   is fundamental: rows equal control steps, so half speed with 1:1 rows forces 10 Hz control.
   Rewriting a s=0.5 export by slerp-resampling rows to source frames would produce a file the
   evaluator did not output, even though it keeps the evaluator hashes. Do not do this without
   organizer confirmation.
4. Note 01 recommended not changing `motion_speed`. This audit overrides that: for Track 3,
   `motion_speed=0.5` is disqualifying unless the ~10 Hz approach in step 3 is used. The training
   difficulty of real-time playback is a separate measurement.
5. Use `examples/run_policy_evaluation.py`, which defaults to `world_count=1` and `reset_mode=explicit`.

### Check to add (our own pre-pack validator; blocking)

For each `episode_XXXXXX.parquet`:
- **(a)** Read the checkpoint config and assert either `source_frame_playback`, or
  (`motion_speed == 1.0` and `sim.fps == ref.fps` with bit-identical floats).
- **(b)** Assert metadata `flash_chord.step_count == N_roster` and `flash_chord.start_frame == 0`.
  The packer only checks `>=`.
- **(c)** Assert `reference_frame` equals `step`, and `time_s * fs ≈ reference_frame` within 1e-6.
  For the s=1 or fs==fc case only, `time_s * fc == step`.
- **(d)** Strongest check: compare the exported `reference_position_*` and `reference_quaternion_*`
  (xyzw) at row f with our input Parquet's `object_body_position` and `object_body_wxyz` at source
  frame f, converted to xyzw, for every f and slot. Tolerance: max 1e-5 m and 1e-5 rad. This catches
  resampling, start offsets, quaternion order and slot order in one step. Under case A it fails at
  f=1. This reproduces for Track 3 the check the kit applies to Track 2.
- **(e)** Assert `flash_chord.episode_index` metadata equals the file stem's episode (see 4.6).
- **(f)** Assert the rows for world 0 have `environment_valid` true.

## 4. Other silent-failure modes in export and pack

1. **Quaternion order.**
   - Export is xyzw: Warp `transform_get_rotation`, `rollout.py:207-227`, metadata `:66`. The kit
     honours `flash_chord.quaternion_order` (`submission_parquet.py:126-134,195-199`). The packer
     and scorer use xyzw. This path is safe.
   - Risk at INPUT: ManoSharpa needs `object_body_wxyz` in w-first order. The Track 3 Parquet `pose`
     is `[x,y,z,qw,qx,qy,qz]`, so `pose[3:7]` can be copied as-is. The loader checks only the unit
     norm (`mano_sharpa.py:183-190`), so an xyzw/wxyz swap passes silently. Check (d) catches it.
2. **Object slot order.**
   - The slot is `object_body_id`, in the reference `object_body_names` order (`rollout.py:441-447`).
   - The packer compares `object_body_name` with `track_3_evaluation_objects.json` (`:344-357`) and
     errors on a mismatch. The check is skipped if the names column is absent, as in a legacy layout.
   - The roster order is NOT alphabetical for ep10 (`blue_cup`, `beige_cup`) and ep19
     (`mini_sweeper`, `mini_dust_pan`), while public episodes are sorted by name.
   - Body names must be exactly these strings.
   - Slot 0 drives the scorer's world alignment and RPE.
3. **Object local frame (largest non-timing risk).**
   - Scored poses are `world_T_object` in the SCAN mesh frame (t3 README :61), and ADD and MPPE use
     scan-mesh vertices and keypoints.
   - The scorer removes only one world rigid transform, taken from slot 0 at frame 0
     (`MPPE.py:113-127`). A constant LOCAL offset between our URDF link frame and the scan frame is
     not removed, and its error grows with rotation away from frame 0.
   - Use the public scan meshes and URDFs (`t3/public/mesh`, `urdf`) as is for the 10 known
     objects.
   - `wooden_spoon` appears in 9 scored episodes, including single-object ep35-37, and has NO
     public scan. Its frame cannot be matched exactly (UNCERTAIN; see note 01 open question).
4. **World count.** The roster has w000 only (`tracks.json` `worlds_per_episode: 1`). Extra worlds
   are dropped silently and harmlessly. Any invalid world fails the whole episode (`:311-318`).
5. **Scale randomisation.** Evaluation keeps the checkpoint's `scene.object_scale_*`. World 0 stays
   nominal only if the range contains 1.0 (`builder.py:279-299`). Keep `[1,1]`.
6. **Episode attribution.**
   - `harness.py:154` takes the FIRST `episode_(\d+)` in the reference Parquet path and stores it as
     `flash_chord.episode_index`.
   - The kit prefers this metadata over the file name (`submission_parquet.py:89-108`).
   - If reference paths are mixed up, two episodes can swap silently. Check (e) catches this.
7. **Gravity, frame and support.**
   - ManoSharpa `coord_frame` is not validated, unlike motion_v1 (`motion_v1.py:202-208`). A non-z-up
     reconstruction world silently gets wrong gravity.
   - The scorer's alignment fixes the output frame but not the physics.
   - The support USDA is resolved from reference metadata (`assets/registry.py:147-160`). If it is
     missing, an error is raised; this is not silent. A wrong table height degrades physics
     silently.
8. **Hidden timing in time_s.** Under case A, `time_s` runs to about 2N/20 s and is not
   source time. Neither the packer nor the scorer reads it, so a wrong `time_s` cannot be seen
   downstream.

## Open uncertainties
- Whether organizers accept post-processed (re-timed) evaluator exports. Assumed NO.
- Whether real-time (s=1) Sharpa training at 20 Hz reaches tracking quality comparable to s=0.5.
  This needs measurement on a public episode with check (d) enabled.
- Track 2 baseline motion_v1 fps was not opened. The mapping is exact by `source_frame_playback`
  regardless of fps.


---
[← Index](../README.md) · [Summary](../00-summary.md) · [← 05](05-alternatives.md) · [07 →](07-mesh-frame-convention.md)
