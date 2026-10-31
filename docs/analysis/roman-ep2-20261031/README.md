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
