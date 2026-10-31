# Delay or noise? And Roman's per-object Kalman filter (public ep2, 31 Oct 2026, CPU, $0)

Owner's questions after the second Roman meeting: is our error a fixed offset; is the "shadow" delay or noise; a video
with the objects separated and as much information as possible. Public ep2 (white pot + lid) only. Mocap is read only
for scoring and plotting (diagnostic). Labels: [M] measured, [I] inference.

Inputs:
- our tracks: store `runs/20261030-orcP1a-87fc869/results/leak_p1/ep2/perc2/` (P_o, library_v3 templates) and
  `hands/hands_refined.npz`;
- public data: `nvidia/video_to_data_challenge` `track_3/public` episode 2 (parquet, ego_cam_a video);
- robot runs: `runs/20261031-rlloop-ccf9058` (ep2, O1 and O3, 5 stored draws each, the runs behind the Embodiment video)
  and `runs/20261030-orcB-38234d1` (ep11/13/31 P arm, 10 draws each).

Commands:
- `lagnoise.py rollouts <dirs>` → `robot_ep2.json`;
- `lagnoise.py perception poses_world_vo.npz ep2.parquet` → `perc_ep2.json`;
- `kfep.py ... ep2` → `ep2_kf.json`;
- `romanvid.py ...` → the video. The video is not in git; it was sent to the owner.

## Robot layer: what the Embodiment ep2 video shows (simulated object vs our reference) [M]
- **No delay:** the best time shift is −0.75 to +0.7 frames on draws that work, and shifting removes only a few mm.
  (±10 = the search bound, on failed or static tracks, where shifting is meaningless.)
- **Little noise:** 0.15–0.6 cm.
- **The error is drift and failure:** 1–14 cm when the robot loses or displaces the object. Example: O1 r1, the
  "left" video, pot drift 12.2 cm (it tips over).

## Perception layer: our track vs mocap, after a world fit and one constant body offset per object [M]

| | pot | lid |
|---|---|---|
| RMS error | 0.60 cm | 0.43 cm |
| constant body offset removed | 0.30 cm | 0.37 cm |
| **delay** (our track lags truth) | **25 ms (0.50 frame)** | **28 ms (0.55 frame)** |
| moving-frame RMS, as is → delay removed | 0.86 → 0.64 cm | 0.71 → 0.32 cm |
| fast noise | 0.25 cm | 0.20 cm |
| slow drift | 0.44 cm | 0.24 cm |
| rotation error median / p90 | 1.7° / 4.3° | 0.9° / 1.8° |

## Roman's per-object Kalman filter
Constant velocity on 6 DoF; process noise small unless a hand keypoint is within 3.5 cm of the tracked surface. ADD on
a 5 cm sphere, mean cm [M]:

| | raw | KF low | KF medium | KF high | offline RTS | **half-frame advance** |
|---|---|---|---|---|---|---|
| pot | 0.429 | 0.427 | 0.428 | 0.435 | 0.416 | **0.343** |
| lid | 0.307 | 0.311 | 0.333 | 0.374 | 0.302 | **0.241** |

Observation-noise sigmas: low 1 mm / 0.2°, medium 3 mm / 0.6°, high 10 mm / 2°.

## Reading
1. **Delay is real in perception, and it is half a frame.** Shifting it back cuts ep2's ADD by about 20 %. The causal
   Kalman filter does nothing, or worse at high assumed noise, because it adds lag. The offline smoother gains 1–3 %.
2. **The half-frame shift is the refine stage's S2.** It was adopted on all 20 public episodes on 30 Oct (+0.006 AUC,
   17 of 20 better). But `pipeline/pipeline_ep.sh` does not call `refine.py`, so the eval references in our packs do not
   carry it [M, code read].
3. **What Roman saw in the robot video is not delay.** It is the robot drifting off the reference.

ep2 is an easy episode (reference AUC 0.987). Offsets are larger on others (pitcher, boards; see the standings
rpe-decomp). This page is about delay vs noise, not about which share dominates the board.

## All 20 public episodes (31 Oct ~21:40 UTC; `all20.py` → `all20.json`, `all20_table.txt`) [M]
Same diagnostic set-up per episode: our P_o track vs mocap after a world fit and one constant body offset per object,
so what remains is the varying error a filter could act on. Rotations are handled as sign-continuous quaternions with
slerp advance. A first run filtered rotation vectors and broke on large rotations (pot flip, pours); that was an
implementation artefact, fixed before this run.

- **The delay is the same everywhere.** Over the 26 moving objects (excluding static racks and the ep23 board swap):
  median 0.50 frame (IQR 0.41–0.55, range 0.20–1.10), i.e. ≈ 25 ms.
- **Noise is small everywhere:** median 0.15 cm. Slow drift is larger: median 0.38 cm; 3.4 cm on the ep18 sweeper;
  1.3–1.6 cm on the ep11/13 blue cup.
- **Fixes, mean ADD on a 5 cm sphere relative to raw** (33 objects / 29 objects without ep0 and ep23):

  | Fix | ADD change | Objects better / worse |
  |---|---|---|
  | **half-frame advance (S2)** | **−4.4 % / −7.9 %** | **32 / 1** (worst +0.01 cm) |
  | causal per-object Kalman, low / medium / high observation noise | +1.3 / +3.5 / +7.8 % (+2.3 / +6.7 / +15.2 %) | mostly worse (adds lag) |
  | delay-aware Kalman (predicts 0.545 frame ahead) | +4.3 % / +8.0 % | 11 / 16 |
  | offline RTS smoother | −0.7 % / −0.8 % | 26 / 3 |
  | advance + RTS | −4.0 % / −6.6 % | 29 / 3 |

- **Reading:**
  - The fix for "tracking vs motion capture" that holds in every episode is the constant half-frame advance. It is
    built and adopted on public data (kit chain: +0.006 AUC, 17 of 20), but not wired into the eval pipeline.
  - A Kalman filter in Roman's causal form makes the tracks worse. The offline smoother is within noise.
  - The remaining drift and offsets need geometry (templates, frame-0 init), not filtering.
- **Board value [E]:** the 30 Oct plan measured an after-the-fact half-frame shift of public rollouts at +0.0004 to
  +0.0028. It pays through retrained references only, so it is worth adding only where eval references are rebuilt
  anyway.

## Zero-lag (offline forward–backward) smoothing, best case (`rtssweep.py` → `rtssweep.json`) [M]
The owner asked whether the Kalman filter's lag can be removed, since processing is offline. Yes: the
Rauch–Tung–Striebel smoother runs the same filter backwards and has no lag.

Swept 96 settings (observation noise 0.5–4 mm, process noise, contact gating, with and without the half-frame advance)
on all 33 objects:
- **smoother alone:** best −1.5 % ADD (31 objects better, 0 worse);
- **with the half-frame advance:** best −5.1 % (32 better, 0 worse), against −4.4 % for the advance alone.

The best cell is at the grid edge (4 mm observation noise, lowest process noise, still objects ×0.01). It was tuned on
these public episodes, so it is an upper bound until a pre-registered test on fresh settings. Scope: these filters act
on perception (our tracked object paths, the robot's training target), not on the policy, which reads exact simulator
state.

Shared page for Roman: https://claude.ai/artifact/6ZSVt1Fz17nXR8gzEKx7mo (private until the owner shares it).

## Cross-validated smoother (`cvsmooth.py` → `cvsmooth.json`) [M]
Settings were chosen on half of the episodes (alternate episodes of the sorted list) and scored on the other half, both
ways, always on top of the half-frame advance. Both halves pick the same cell: observation noise 8 mm, process 4.0 when
a hand is near, ×0.01 when still.
- Held-out gain on top of the advance: −1.2 % (10 better, 2 worse, worst +0.012 cm) and −0.5 % (7 better, 0 worse).
- Advance + smoother vs raw on the held-out halves: −10.5 % and −3.2 %.
- Proposed to focused-pascal as a refine step behind the kit-chain gate.

**Correction (31 Oct ~23:15 UTC).** In `rtssweep.py` and `cvsmooth.py` the rotation channel's observation σ was
`sig / 0.1 * deg2rad(0.3) / 2`. For the chosen 8 mm that is 2.1e-4 in quaternion units (≈ 0.024°), so rotations were
effectively not smoothed. The cross-validated gains are position-only smoothing. The port to the refine stage
(focused-pascal) is positions only. Rotation smoothing at 0.6° (`all20.py` 'med') was not cross-validated.
