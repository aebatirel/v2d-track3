# 02 — Track 3 error budget (public mocap + official scorer)

Research-only. No SlamDunk code was read or reused. All numbers below come from the
public Track 3 mocap parquets, which were perturbed and then scored with the official
`metric_code/track_3/*.py` functions.

- Scripts and raw outputs: `/private/tmp/claude-501/-Users-aebatirel-Documents-Code-SlamDunk/ad61ecbd-403d-49a3-817f-1f8b688b5549/scratchpad/analysis/`
  (`common.py`, `verts.py`, `stats.py`, `budget.py`, `thresholds.py`, `extras.py`, `combined.py`, `stereo.py`, `verify.py`;
  outputs `stats.txt/json`, `budget_box.txt/json`, `budget_mesh.txt/json`, `thresholds.txt/json`, `extras.txt`, `combined.txt`, `stereo.txt`).
- Interpreter: `/Users/aebatirel/Documents/Code/SlamDunk/.venv-aria/bin/python` (numpy 2.5.3, pandas 3.0.6, scipy). To reproduce, run `cd analysis && $PY budget.py box` and repeat for each script. Total run time is about 2 min.

## 0. Scorer facts that drive the budget (read from the kit code)

- Each metric is computed per episode and then averaged over episodes. Every episode has equal weight regardless of length.
- **Alignment**: one rigid transform maps the submission's slot-0 frame-0 pose onto the reference slot-0 frame-0 pose. It has no scale and no fitting over time, and it is applied to every object and every frame. Any error in that single anchor pose therefore spreads to the whole episode.
- **AUC**: ADD is the mean distance over the embedded vertex samples. It is not symmetry-aware (ADD, not ADD-S). The 9 thresholds run from 1 to 9 cm and are integrated with the trapezoid rule on [0,1], then averaged over objects. For a constant error *a* cm, AUC = 1 for a < 1 and 1 − (⌊a⌋ − 0.5)/8 for 1 ≤ a < 9. This means:
  - there is a dead zone below 1 cm;
  - each extra centimetre of ADD costs about 12.5 AUC points;
  - an error of 9 cm or more scores 0.
- **SP-SR**: the mean over objects of the time-mean position error must be ≤ 10 cm, and the mean over objects of the time-mean geodesic angle must be ≤ 0.5 rad (28.6°).
- **MP-SR**: for every object, the time-mean position error must be < 3 cm and the time-mean angle < 30°. Both success rates are binary per episode for a single world. The submission's multiple worlds are averaged.
- **RPE**: for each object pair (i < j), the position of j expressed in i's frame. It is the mean over time and pairs, in cm. A single-object episode returns 0.0, and 7 of the 20 public episodes have one object, so the 20-episode mean is diluted by a factor of 13/20.
- **MPPE**: 6 keypoints at ±5 cm along the body axes, mean distance in cm. It is roughly the translation error plus the rotation error times a 5 cm lever.
- None of the metrics is symmetry-aware. Quaternions are normalised, and the geodesic angle ignores quaternion sign.
- `verify.py` builds full solution/submission DataFrames and calls each module's `score()`. The results are bit-identical to the tensor path used here: GT gives 1/1/1/0/0, and a mixed perturbation gives AUC 0.73709, SP 1.0, MP 0.65, RPE 2.312702, MPPE 2.890149 on both paths.

**AUC point approximation.** Each object uses 500 points sampled on the surface of a box (seed 0). The box dimensions are solved so that its surface second moments match the URDF inertia (0.3 kg uniform-surface estimate), with the box oriented along the inertia eigenvectors and offset by the URDF COM.
- Validation on the two meshes available locally: the URDF second moments match the real `white_pot`/`white_pot_lid` GLB surface samples to within 1%. Box E|v| vs mesh E|v| is 9.8 vs 9.3 cm for the pot and 6.6 vs 6.4 cm for the lid.
- Rerunning the whole budget with real-mesh points for the pot and lid changed AUC by ≤ 0.003 in every case (`budget_mesh.txt`).
- The official vertex payload and its point count are not released, so the absolute AUC values here are approximations.

**Observed frame convention (inference, high confidence).**
- All 10 URDFs have Ixx ≥ Iyy ≥ Izz, zero or near-zero products of inertia, and COM within 2 mm of the origin.
- In the pot and lid GLBs, the surface centroid sits at the origin (< 0.5 mm) and the off-diagonal covariance is about 0.

Together this indicates the scanned-mesh frames are canonical: origin at the surface centroid, axes along the principal axes in ascending variance (x smallest, z largest). The sign convention is unresolved. The pot shows positive skew on +z and +x and the lid positive skew on +x, but two objects are too few to confirm a rule (hypothesis).

## 1. Per-episode statistics (public set: 20 episodes, 5246 frames)

| Aspect | Observation |
|---|---|
| Frame rate | Nominal 20.254 fps (`timestamp`). The actual `capture_time` interval is 50.0 ms (20.00 fps), with ±3 ms jitter and 3 isolated 80–93 ms gaps. Because of this, `timestamp` drifts from `capture_time` by up to 0.28 s per episode. Associate by `frame_index`, never by nominal time. |
| Visibility | `visible` is True for 100% of frames and objects, so there are **no visibility gaps** in the public GT. |
| Held frames | Episodes 0/12/27/2 have 13/12/9/6 frames where the pose is bit-identical to the previous frame (mocap hold), at normal capture intervals. |
| Glitches | One genuine fast flip: episode 26, white_pot, 180° over about 10 frames, with alternating 10°/24° per frame (up to 446°/s). |

Columns in the per-object table:
- **maxdisp/end**: maximum displacement from the start, and displacement at the end.
- **maxrot/end**: the same for rotation.
- **mov%**: share of frames where the 5-frame smoothed speed exceeds 3 cm/s or 15°/s.
- **onset**: first frame with displacement > 3 cm or rotation > 10°.
- **lever**: mean/max distance from the slot-0 start position. This is the lever arm for anchor-rotation error.

| ep | task | T (s) | slot:object | maxdisp/end cm | maxrot/end ° | mov% | onset | lever cm |
|---|---|---|---|---|---|---|---|---|
| 0 | Pot_with_lid | 373 (18.4) | 0 white_pot | 17.2/2.6 | 14/2 | 28 | 114 | 3.5/17 |
| | | | 1 white_pot_lid | 23.1/2.6 | 14/1 | 22 | 58 | 13.8/22 |
| 2 | Pot_with_lid | 343 (16.9) | 0 white_pot | 12.7/3.9 | 13/2 | 29 | 117 | 3.6/13 |
| | | | 1 white_pot_lid | 26.7/4.0 | 31/5 | 29 | 61 | 16.5/26 |
| 11 | Cup_Stack | 137 (6.8) | 0 beige_cup | 25.2/17.9 | 26/22 | 36 | 26 | 15.2/25 |
| | | | 1 blue_cup | 0.5/0.2 | 5/2 | 14 | – | 17.2/17 |
| 12 | Cup_In_Dish_Rack | 181 (8.9) | 0 blue_cup | 22.2/18.5 | 180/179 | 57 | 37 | 13.9/22 |
| | | | 1 plastic_dish_rack | 0.4/0.1 | 2/0 | 1 | – | 19.0/19 |
| 13 | Cup_In_Dish_Rack | 190 (9.4) | 0 blue_cup | 28.1/18.1 | 179/173 | 64 | 27 | 16.5/28 |
| | | | 1 plastic_dish_rack | 0.1/0.0 | 1/0 | 0 | – | 17.8/18 |
| 18 | Dust_Brush | 353 (17.4) | 0 mini_dust_pan | 19.5/2.4 | 67/2 | 32 | 18 | 4.0/20 |
| | | | 1 mini_sweeper | 13.9/2.6 | 46/5 | 61 | 40 | 21.1/27 |
| 21 | Water_Can_Blue_Cup | 186 (9.2) | 0 blue_cup | 9.9/2.8 | 39/23 | 45 | 39 | 4.8/10 |
| | | | 1 water_pitcher | 32.0/11.0 | 91/18 | 44 | 42 | 38.9/50 |
| 22 | Water_Can_Blue_Cup | 189 (9.3) | 0 blue_cup | 9.4/1.9 | 29/17 | 41 | 46 | 3.4/9 |
| | | | 1 water_pitcher | 32.3/5.5 | 92/16 | 42 | 44 | 30.8/49 |
| 23 | Planter_Stand | 325 (16.0) | 0 wooden_piece_1 | 15.9/15.8 | 101/96 | 29 | 24 | 12.8/16 |
| | | | 1 wooden_piece_2 | 23.0/15.0 | 105/102 | 34 | 130 | 23.7/38 |
| 24 | Planter_Stand | 275 (13.6) | 0 wooden_piece_1 | 24.0/15.5 | 105/100 | 34 | 13 | 15.2/24 |
| | | | 1 wooden_piece_2 | 27.3/17.6 | 101/100 | 31 | 116 | 25.6/42 |
| 26 | Pan_In_Dishrack | 158 (7.8) | 0 plastic_dish_rack | 0.4/0.4 | 1/1 | 3 | – | 0.4/0.4 |
| | | | 1 white_pot | 20.5/20.4 | 180/180 | 31 | 53 | 19.6/28 |
| 27 | Pan_In_Dishrack | 246 (12.1) | 0 plastic_dish_rack | 0.3/0.1 | 1/1 | 0 | – | 0.1/0.3 |
| | | | 1 white_pot | 38.9/18.2 | 180/179 | 65 | 24 | 25.3/41 |
| 31 | Brush_Dishrack | 290 (14.3) | 0 mini_sweeper | 15.6/9.2 | 34/5 | 72 | 47 | 8.7/16 |
| | | | 1 plastic_dish_rack | 0.2/0.1 | 1/1 | 0 | – | 11.4/12 |
| 39 | Dustpan_Solo | 319 (15.7) | 0 mini_dust_pan | 39.1/8.5 | 109/28 | 73 | 53 | 16.4/39 |
| 40 | Dustpan_Solo | 260 (12.8) | 0 mini_dust_pan | 27.3/1.8 | 89/2 | 61 | 43 | 12.8/27 |
| 41 | Pan_Solo | 299 (14.8) | 0 white_pot | 20.5/2.5 | 72/4 | 65 | 35 | 9.7/21 |
| 42 | Pan_Solo | 257 (12.7) | 0 white_pot | 18.0/2.9 | 98/95 | 63 | 39 | 5.7/18 |
| 43 | Pan_Solo | 326 (16.1) | 0 white_pot | 23.7/5.8 | 180/179 | 70 | 30 | 9.9/24 |
| 44 | Pan_Solo | 249 (12.3) | 0 white_pot | 21.9/2.3 | 24/5 | 39 | 79 | 7.0/22 |
| 45 | Pan_Solo | 290 (14.3) | 0 white_pot | 28.9/1.7 | 94/5 | 64 | 52 | 12.8/29 |

Summary:
- Episodes run 137–373 frames (6.8–18.4 s). 13 have two objects and 7 have one.
- Peak speeds reach 26–75 cm/s and 50–450°/s. Rotations up to 180° are common, including flips in episodes 12, 13, 26, 27 and 43.
- **Slot-0 motion**: slot 0 is the alignment anchor. It is static only in episodes 26 and 27 (dish rack). In the other 18 episodes it moves 10–39 cm.
  - Before slot 0 starts moving there is a static window of 13–117 frames (median 39, about 1.9 s), which can be used to average the anchor estimate.
  - In 5 episodes slot 0 is a near-rotationally-symmetric cup (11, 12, 13, 21, 22): the cups' principal moments differ by less than 1% around their long axis.
- **Lever arms** from the slot-0 start reach 50 cm (water pitcher episodes).

## 2. Error budget (official metric functions; mean over the 20 public episodes)

Perturbation definitions (xyz in m, quaternions xyzw):
- **Scale**: applied about the slot-0 start. After anchor alignment, every scale centre is equivalent.
- **Slot-0 init rot/trans**: only the slot-0 frame-0 pose is changed. This is a pure anchor error.
- **Lag k**: `ach[t] = ref[max(t−k, 0)]`.
- **Jitter**: iid N(0, σ²) per axis on every frame, including the anchor. The "anchor exact" variant restores the slot-0 frame-0 pose.
- **Drift**: a linear ramp from 0 to the stated end-point in a random direction. "Common" means all objects share it (world-frame drift); "per-object" means independent directions.
- **Body offsets**: a constant right-multiplied rotation, or a body-frame translation, on every frame.
- **Drop**: an object freezes at its onset pose (first motion > 3 cm or > 10°), or after its first motion segment (ends after 10 still frames).
- Random cases are averaged over 8 seeds and random axes.
- `[multi]` means only the 13 two-object episodes are included. Single-object episodes are unaffected by slot-1 perturbations.

| Perturbation | AUC | SP-SR | MP-SR | RPE cm | MPPE cm |
|---|---|---|---|---|---|
| GT (no error) | 1.000 | 1.00 | 1.00 | 0.00 | 0.00 |
| scale +1% | 1.000 | 1.00 | 1.00 | 0.13 | 0.13 |
| scale +3% | 0.998 | 1.00 | 1.00 | 0.38 | 0.40 |
| scale +5% | 0.983 | 1.00 | 1.00 | 0.64 | 0.66 |
| scale +10% (−10% identical) | 0.923 | 1.00 | 0.90 | 1.27 | 1.33 |
| slot-0 init rot 2° (random axis) | 0.997 | 1.00 | 1.00 | 0.00 | 0.42 |
| slot-0 init rot 5° | 0.948 | 1.00 | 0.96 | 0.00 | 1.05 |
| slot-0 init rot 10° | 0.813 | 1.00 | 0.68 | 0.01 | 2.10 |
| slot-0 init rot 10° (yaw about world z) | 0.819 | 1.00 | 0.60 | 0.01 | 1.94 |
| slot-0 init trans 1 cm (sits on AUC step) | 0.966 | 1.00 | 1.00 | 0.00 | 1.00 |
| slot-0 init trans 3 cm | 0.740 | 1.00 | 0.63 | 0.01 | 2.99 |
| lag 1 frame (49 ms) | 0.990 | 1.00 | 1.00 | 0.38 | 0.30 |
| lag 3 frames | 0.933 | 1.00 | 1.00 | 1.09 | 0.88 |
| lag 5 frames | 0.872 | 1.00 | 1.00 | 1.73 | 1.41 |
| jitter 0.5 cm/axis | 0.958 | 1.00 | 1.00 | 0.73 | 1.14 |
| jitter 1 cm/axis | 0.836 | 1.00 | 0.91 | 1.47 | 2.27 |
| jitter 2 cm/axis | 0.558 | 1.00 | 0.00 | 2.94 | 4.55 |
| jitter 0.5 / 1 / 2 cm, anchor exact | 0.984 / 0.914 / 0.725 | 1.00 | 1.00 / 1.00 / 0.01 | 0.73 / 1.47 / 2.93 | 0.80 / 1.59 / 3.18 |
| rotation jitter 1 / 3 / 5°/axis | 0.997 / 0.939 / 0.847 | 1.00 | 1.00 / 0.96 / 0.83 | 0.28 / 0.84 / 1.40 | 0.35 / 1.04 / 1.73 |
| drift 1 cm common | 1.000 | 1.00 | 1.00 | 0.00 | 0.50 |
| drift 3 cm common | 0.916 | 1.00 | 1.00 | 0.00 | 1.50 |
| drift 5 cm common | 0.799 | 1.00 | 1.00 | 0.00 | 2.50 |
| drift 1 / 3 / 5 cm per-object | 1.000 / 0.916 / 0.799 | 1.00 | 1.00 | 0.43 / 1.29 / 2.15 | 0.50 / 1.50 / 2.50 |
| rotational drift 1 / 3 / 5° common (about slot-0 start) | 1.000 / 0.998 / 0.988 | 1.00 | 1.00 | 0.00 | 0.10 / 0.31 / 0.52 |
| slot-1 body rot 5° (all eps / multi) | 0.997 / 0.995 | 1.00 | 1.00 | 0.00 | 0.11 / 0.17 |
| slot-1 body rot 15° (all / multi) | 0.961 / 0.940 | 1.00 | 1.00 | 0.00 | 0.33 / 0.51 |
| slot-1 body trans 1 cm (all / multi) | 0.990 / 0.984 | 1.00 | 1.00 | 0.65 / 1.00 | 0.33 / 0.50 |
| slot-1 body trans 3 cm (all / multi) | 0.918 / 0.875 | 1.00 | 0.65 / 0.46 | 1.95 / 3.00 | 0.98 / 1.50 |
| slot-0 body rot 5° (every frame) | 0.953 | 1.00 | 0.97 | 0.88 | 0.94 |
| slot-0 body rot 15° (every frame) | 0.721 | 1.00 | 0.44 | 2.65 | 2.82 |
| drop most-moving object at onset (78% of frames frozen) | 0.550 | 0.55 | 0.05 | 7.61 | 6.97 |
| drop most-moving after 1st motion (32% frozen) | 0.943 | 0.95 | 0.90 | 0.32 | 0.78 |
| drop slot 1 at onset [multi] | 0.772 | 0.85 | 0.31 | 8.40 | 4.29 |
| drop all objects at onset | 0.442 | 0.45 | 0.00 | 11.17 | 8.76 |
| **static predictor (everything frozen at frame 0)** | **0.446** | **0.45** | **0.00** | **10.87** | **9.31** |

Symmetry-axis spin (`extras.py`), constant body rotation on every frame:

| Case | AUC | SP-SR | MP-SR | RPE | MPPE |
|---|---|---|---|---|---|
| slot-0 cup spin 10° about body z (5 cup-anchor eps) | 0.714 | 1.00 | 0.40 | 3.15 | 2.81 |
| … 30° | 0.279 | 0.60 | 0.00 | 9.34 | 8.34 |
| … 90° / 180° | 0.195 / 0.165 | 0.00 | 0.00 | 25.5 / 36.1 | 22.7 / 32.0 |
| slot-1 lid spin 30° / 90° about body x (eps 0, 2) | 0.844 / 0.500 | 1.00 / 0.00 | 1.00 / 0.00 | 0.00 | 0.86 / 2.36 |

The spin of a symmetric anchor object about its axis is close to invisible in images, yet the scorer turns it into a rotation of the whole scene.

### SP-SR / MP-SR breakpoints (`thresholds.txt`, fine sweeps)

The first-failure column gives the value at which MP-SR first falls below 1; the 50% column gives the value at which it falls to about 0.5.

| Error family | MP-SR first < 1 | MP-SR ≈ 0.5 | SP-SR first < 1 | SP-SR ≈ 0.5 |
|---|---|---|---|---|
| constant global/anchor translation | 3.0 cm (cliff; 3.5 cm → 0) | 3.0 cm | 12 cm (cliff) | 10–12 cm |
| position white noise σ/axis (with anchor) | 1.0 cm (0.95) | ≈1.35 cm | 3 cm | ≈4.5 cm |
| scale | 10% (0.90) | ≈18% | 60% | ≈75% |
| slot-0 init rotation | 5° (0.96) | ≈12° | 30° (cliff → 0) | 28.6° |
| slot-0 body rotation | 5° (0.97) | ≈14° | 20° | ≈45° |
| non-anchor body rotation | 30° (cliff; 32° → 0) | 30° | 60° (averaged over objects) | 45–60° |
| non-anchor body translation | 3.0 cm (cliff) | 3.0 cm | > 15 cm | – |
| lag | 8 frames (0.80) | ≈10 frames (0.5 s) | 15 frames | > 40 frames |
| common linear drift (end-point) | 6 cm (= 3 cm time-mean) | ≈6 cm | 20 cm | ≈20 cm |
| camera rotational drift, pivot 0.6 m | 5° (0.92) | ≈6–7° | 15° | > 20° (0.69 at 20°) |

How each metric is driven:

**AUC**
- Lost or frozen objects dominate: −45 to −55 points.
- Next is any common position bias of 1 cm or more: anchor translation, world drift, and noise that reaches the anchor.
- Anchor/slot-0 orientation comes next, with error proportional to lever arm.
- Then lag.
- Cheap errors: scale ≤ 5%, non-anchor orientation ≤ 15°, rotation jitter ≤ 2°.

**SP-SR**
- SP-SR is very lenient: the static predictor still scores 0.45.
- It moves only on lost tracking, an average orientation error of 28.6° or more (anchor rotation of 30° fails every episode), or position errors around 10 cm.

**MP-SR**
- The hard thresholds are 3 cm and 30° per object, time-mean. Breakpoints are in the table above.
- Every perturbation that touches the anchor is amplified, because the error reaches every object.

**RPE**
- RPE is invariant to every common rigid error: anchor rotation and translation, common drift and camera drift all give 0.00.
- It is driven by independent per-object errors (noise, per-object drift, lag between objects that move differently, the second object's position offset), by scale, and by slot-0 orientation, which rotates the pair frame.
- It ignores the second object's orientation entirely.

**MPPE**
- MPPE is linear with no dead zone: translation error plus rotation error times 5 cm.
- Orientation is therefore cheap in MPPE (15° ≈ 0.3–0.5 cm), while translation counts 1:1.

### Combined hypothetical pipelines with leave-one-out (`combined.txt`)

**A: careful stereo**
- Components: anchor 0.5 cm and 2°, jitter 0.5 cm/axis with the anchor exact, rotation jitter 2°, common drift 2 cm, scale 1%, slot-1 body rotation 5°.
- Result: AUC 0.889, SP 1.00, MP 0.97, RPE 0.98, MPPE 1.71.
- Biggest leave-one-out gains: removing drift +0.040 AUC, removing rotation jitter +0.029 (it also perturbs the anchor), removing jitter +0.020.

**B: rough monocular/learned**
- Components: anchor 1.5 cm and 5°, jitter 1 cm, rotation jitter 3°, drift 5 cm, scale 10%, lag 2 frames, slot-1 body rotation 15°.
- Result: AUC 0.531, MP 0.01, RPE 2.59, MPPE 4.57.
- Biggest leave-one-out gains: removing drift +0.135 AUC and MP-SR 0.01 → 0.24; removing scale +0.067; removing jitter +0.048; removing anchor translation +0.042.
- With several moderate errors stacked, MP-SR is near 0 unless the total time-mean error per object stays below about 2 cm.

The tolerances are shared between perception and policy/simulation tracking. Track 3 scores the final rolled-out trajectory, so any control tracking error uses up the same 3 cm / 30° and AUC margin.

## 3. Stereo depth error vs distance (ego pair from `camera_calibration.json`)

The ego pair is `ego_cam_c` (left, fx 563.2) and `ego_cam_b` (right, fx 567.3), 1280×800, 127° HFOV, baseline 7.50 cm. This gives f·B = 42.24 px·m, and δZ = Z²·δd/(f·B).

| Z (m) | disparity (px) | δZ @0.25 px (mm) | δZ @0.5 px (mm) | δZ/Z @0.5 px | δX @0.25 px (mm) |
|---|---|---|---|---|---|
| 0.3 | 140.8 | 0.53 | 1.07 | 0.36% | 0.13 |
| 0.4 | 105.6 | 0.95 | 1.89 | 0.47% | 0.18 |
| 0.5 | 84.5 | 1.48 | 2.96 | 0.59% | 0.22 |
| 0.6 | 70.4 | 2.13 | 4.26 | 0.71% | 0.27 |
| 0.7 | 60.3 | 2.90 | 5.80 | 0.83% | 0.31 |
| 0.8 | 52.8 | 3.79 | 7.58 | 0.95% | 0.36 |
| 0.9 | 46.9 | 4.79 | 9.59 | 1.07% | 0.40 |
| 1.0 | 42.2 | 5.92 | 11.84 | 1.18% | 0.44 |

Notes:
- At half resolution (640×400, f·B = 21.1) every δZ doubles: 0.5 px gives 5.9 mm at 0.5 m and 23.7 mm at 1.0 m.
- At 0.3 m the disparity is 141 px, so full-resolution SGBM needs `numDisparities` ≥ 144.
- The effective f after rectification depends on the chosen output FOV. The lenses are strongly distorted (rational model, k1 ≈ 4.7–6.4).
- `ego_cam_a` (RGB 2028×1520, fx 1150) sits 3.74 cm from the stereo-left camera and is not part of the stereo pair.
- The 7.4 ms cross-device skew (0.15 frame) concerns exo vs ego only. The ego pair is on one device.
- The public mocap has no camera pose, so the actual camera-object distances were not measured here. The 0.3–1.0 m range is an assumption.

Interpretation:
- Pure disparity noise gives depth error of ≤ 1.2% at ≤ 1 m. As a scale error that is free in this budget: 1–3% scale costs ≤ 0.002 AUC.
- As per-point noise it is 1.5–6 mm at 0.5–1 m with 0.25 px. Fitting a model to many object pixels drives the random part well below the 0.5 cm/axis jitter level that keeps MP-SR at 1.
- The stereo risk is systematic bias rather than noise. Likely sources (hypotheses, not measured):
  - textureless white pot and lid;
  - hand occlusion;
  - edge fattening at object boundaries;
  - rectification of the wide-FOV lenses.

## 4. Conclusions: where accuracy effort pays most

1. **Never lose a manipulated object.** Freezing the most-moving object at its first motion collapses the score to roughly the static predictor: AUC 0.55, SP 0.55, MP 0.05. Tracking continuity and re-acquisition through grasp and occlusion is worth more than any refinement of sub-centimetre accuracy.
2. **Hold one consistent world frame for the whole episode.** Drift was the largest leave-one-out gain in both combined scenarios.
   - A 5 cm linear world drift costs 0.20 AUC on its own.
   - Camera rotational drift is amplified by camera-object distance: 5° → MP-SR 0.92, 8° → 0.22.
   - Static scene objects (dish rack, table) and offline global optimisation are the natural anchors.
   - RPE will not reveal this problem, because it is blind to common-mode error.
3. **Make the slot-0 frame-0 pose excellent.** That pose defines the scorer's alignment for every object and frame.
   - Translation error passes through 1:1: 3 cm → MP-SR 0.63. Rotation error is multiplied by lever arms up to 50 cm: 10° → MP 0.68.
   - Estimate the anchor from the static pre-motion window (≥ 13 frames, median 39) rather than from frame 0 alone. Keeping per-frame noise out of the anchor alone lifts 1 cm/axis jitter from AUC 0.836 to 0.914.
   - **Highest-risk case: a symmetric cup as slot 0** (5/20 public episodes). A 10° spin about the cup axis gives AUC 0.71 and MP-SR 0.40 on those episodes, and 30° gives MP-SR 0.
4. **Per-frame noise and latency.** Target ≤ 0.5 cm/axis position noise (AUC 0.96–0.98) and ≤ 2° rotation noise. Smooth offline with a zero-phase (bidirectional/RTS) smoother, since causal lag also costs: −1% AUC per frame at 1 frame, −7% at 3 frames.
5. **Low return:**
   - Metric scale below 5%, which stereo already provides.
   - Orientation of non-anchor objects within ±15°: at most −0.06 AUC, invisible to SR and RPE.
   - Pushing ADD below about 1 cm: AUC dead zone, though MPPE still improves linearly.
6. **Hard cliffs to avoid:**
   - Any single object above 3 cm time-mean position error or 30° time-mean rotation fails MP-SR for the whole episode.
   - Non-anchor symmetry flips of ≥ 30° (e.g. lid spin of 90°) fail MP and SP.
   - Errors of 9 cm ADD or more score 0 AUC for that object.
7. **Frame-convention risk (hypothesis).** The GT object frame appears to be canonical: centroid plus ascending-variance principal axes. If the submitted object frame comes from our own reconstructed mesh, any mismatch acts as a body offset. That is tolerable up to about 15° / 1 cm for non-anchor objects but rotates the whole scene for slot 0. Canonicalising reconstructed meshes the same way and resolving the sign ambiguity should be checked against the kit before relying on it.

## Limitations

- AUC uses moment-matched box points. They were validated on 2 of the 10 objects; the official vertex count and payload are unknown.
- Perturbations are idealised: linear drift, iid noise, constant offsets. Real estimator errors are correlated and heavier-tailed.
- 20 public episodes only. The hidden test set may differ in object mix, slot-0 identity and visibility handling. The public GT has no invisible frames, so how the reference treats occluded frames is not observable here.
- Camera-object distance is assumed at 0.3–1.0 m. No camera trajectory is released in the public mocap.
- Policy/simulation tracking error (Track 3 scores rollouts) is not modelled. It shares the same budget.
