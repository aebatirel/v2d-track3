# 11 — Placement priors, room memory and the mocap-world link (DIG 11, final)

Status: COMPLETE. Stages A, B and C ran on 2026-10-05. On 2026-10-06, stage B was re-verified and extended and stage C
was re-checked and extended; that retry resolved the colour-camera K convention. Agent 11. Research and analysis only:
nothing was submitted, and no evaluator, physics or SlamDunk code was touched.

Scripts and outputs are in `/Users/aebatirel/Documents/Code/v2d-research/work/11/`. Run them as
`/Users/aebatirel/Documents/Code/v2d-research/venv/bin/python <script>` inside that directory.

Raw notes preserved verbatim:
- the chronological stage A-C log: `work/11/notes_stageAB_C_log_backup.md`;
- the pre-rewrite document with the 2026-10-06 addenda: `work/11/notes_pre_final_rewrite_2026-10-06.md`.

Tags: [V] verified numerically here, [E] estimate, [H] hypothesis.

## 0. Bottom line

1. [V] Staging is highly repeatable.
   - Within a task, each object's start yaw in the mocap world agrees to <= 4 deg rms over the public takes (rack 0.4,
     Cup_In_Dish_Rack cup 1.4, Water_Can cup 4.0, pitcher 0.8, planks ~1.5, Pot_with_lid pot 0.2).
   - Exceptions: the lid (17), the dust pan (7), and the pot when its resting face changes.
   - Tilt and height follow the resting face (sd <= 0.5 deg / 0.5 mm).
   - The rack sits at world yaw 89-93 deg with its tower on the person's left in all three public rack tasks. Viewing
     frame 0 shows the same in all five eval rack episodes.
2. [V] The mocap world is gravity-aligned, has the same yaw in every public session, and is fixed relative to the room
   to <~1 deg.
   - The camera is head-mounted at the same seat. It looks along mocap -x (heading 180 +- 3 deg), and image right is
     mocap +y.
   - The table is small and ROUND, so no table edge exists to give yaw.
3. [V] W can be measured on every eval episode with ~1-1.5 deg error. W is the mocap yaw of our frame-0 camera heading.
   Method R:
   - Offline: fit the frame-0 camera of 4 public episodes in the mocap world from GT-posed scan silhouettes.
   - Online: register each eval frame 0 to those frames on the static room background (pure rotation, SIFT).
   - Leave-one-out against the GT fits: 1.18 deg rms (K as given; 1.55 with the a-priori reference set).
   - The eval table moves by <= 0.7 deg when the reference set changes.
4. [V] Settled in the 2026-10-06 retry: use the colour K AS GIVEN. An epipolar test against the calibrated cam_a ->
   cam_b extrinsic was run on 26 frame pairs in 7 episodes:
   - Sampson error: 4.5 px median with K as given vs 13.7 px with the 180-deg-flipped principal point.
   - As given wins on 22 of 23 pairs.
   - So the W table to use is the "native" one (section 8.7). The flipped variant would add a ~2 deg bias.
5. [V] Value of the priors under the official scorer (kit `score()`; perfect tracking unless noted).
   - Symmetric slot-0 cup anchor set from the task prior instead of a random spin (LOO, 4 public eps):
     - AUC 0.277 -> 0.871 / 0.884 / 0.858 / 0.846 / 0.734 for W error 0 / 1 / 3 / 5 / 10 deg;
     - SP-SR 0.16 -> 1.0;
     - RPE 27 -> 2.3 cm; MPPE 21 -> 1.6 cm.
   - Two-fold slot-0 anchors (planks, rack, sweeper): AUC 0.616 -> 1.0 for any W error <= 10 deg.
   - About 85-90 % of these gains survive 1 cm / 4 deg tracking noise.
   - Projected eval gain: about +0.18 leaderboard mean AUC (cups +0.08, two-fold +0.10; the two-fold part is an upper
     bound) [E].
6. [V] The measured W unlocks:
   - absolute world priors for ev10 (Cup_Stack cup), ev15/16 (twin-less rack branch) and ev20 (cup; alternative to the
     bearing prior);
   - the plank side rule that resolves ev25's plank identity;
   - world end-yaw priors (Water_Can cup, Pan_Solo-type pot).
   At ~1 deg, W is no longer the error-limiting term; each prior's twin spread is. Section 8.8 gives the priors already
   converted into our frame.
7. [V] Priors cannot solve ev8, ev32 or ev33. Their slot-0 cups belong to unseen tasks, so their spin must come from
   vision: the Vicon markers baked into the scan textures. Note 12 shows that markers fix a cup's spin to ~2 deg on a
   public frame.
8. [V] Other room-memory priors are small but safe:
   - rest snap (stable face + own table plane) on static segments: +0.014 / +0.035 / +0.058 median AUC per episode at
     0.5 / 1 / 2 cm noise; never harmful. Stable-face tilt gives about 2/3 of the gain, table height about 1/3.
   - anchor tilt snap: +0.01..+0.11.
   - end-placement snap (lid on pot, plank interlock): +0.01..+0.04, possibly more value physically [H].

## 1. Data, conventions and scorer facts used

- Public GT: the `observation.objects` pose is world_T_object in the raw scan (GLB) frame. No Y-up conversion is applied
  (note 07).
- x,y are re-centred per episode on the all-frame, all-object mean. z is physical (table top 0.6012 m, s8).
- Yaw = heading of a fixed horizontal body axis about world z. The axis is `c11.HREF`, e.g. +x for cups, +z for the rack,
  pot and planks, +y for the sweeper and pitcher.
- Tilt = angle of the resting-up body axis (`c11.UP`) from +z.
- Symmetry classes (s5 Chamfer self-similarity):
  - spin-symmetric (C): cups and lid;
  - two-fold (2): mini_sweeper, both planks and the near-two-fold rack;
  - asymmetric (A): pot, pitcher and dust pan.
- Scorer: aligns ONE rigid transform from the slot-0 object's frame-0 pose, with no scale. A spin or branch error of a
  symmetric slot-0 anchor therefore rotates the whole scene about the anchor in every frame (s6: 180 deg gives AUC
  0.03-0.50, SP 0, MP 0). This is why the anchor's yaw is the main lever for placement priors.
- AUC values here use 500 area-weighted scan samples per object, not the organisers' hidden vertex set [E]. The wrapper
  `sc11.py` reproduces the kit's internal metric functions exactly (ep 12, spin 30: AUC 0.18405, MPPE 7.7947).
- Video: decoded MP4 frames are already upright; do not rotate again (checked here and in notes 12 and 15).
- Calibration [V, section 8.4]: the published `ego_cam_*` intrinsics and extrinsics are all expressed in the upright
  stored-image frame. Use them as given.

## 2. What is consistent in the staging

### 2.1 Start/end pose per (task, object)  [V] `s11_consistency.py` -> `s11_consistency.{out,json}`
| task (public eps) | object | start yaw (deg) | start rms | end yaw | end rms | notes |
|---|---|---|---|---|---|---|
| Cup_In_Dish_Rack (12,13) | blue_cup | 65.5, 62.8 | 1.4 | 13.1, -8.5 | 10.8 | upright start, flipped end (tilt 179/162) |
| Cup_In_Dish_Rack | plastic_dish_rack | 89.9, 89.1 | 0.4 | 89.5, 89.1 | 0.2 | static |
| Water_Can_Blue_Cup (21,22) | blue_cup | -64.8, -72.8 | 4.0 | -88.1, -89.9 | 0.9 | |
| Water_Can_Blue_Cup | water_pitcher | 37.3, 38.8 | 0.8 | 19.5, 53.9 | 17.2 | tilt 37.8 at rest |
| Pan_In_Dishrack (26,27) | plastic_dish_rack | 93.0, 91.6 | 0.7 | 92.9, 91.0 | 0.9 | static |
| Pan_In_Dishrack | white_pot | 43.7 (upside down), 91.4 | 23.9 | 28.7, 33.6 | 2.4 | rest face differs |
| Brush_Dishrack (31) | rack / mini_sweeper | 91.2 / -3.5 | - | 92.1 / -2.9 | - | |
| Dust_Brush (18) | dust pan / sweeper | -22.9 / 16.3 | - | -20.8 / 12.0 | - | |
| Dustpan_Solo (39,40) | mini_dust_pan | -16.5, -2.8 | 6.8 | 10.9, -0.6 | 5.8 | |
| Pot_with_lid (0,2) | white_pot | 4.9, 4.6 | 0.2 | 6.6, 6.1 | 0.2 | |
| Pot_with_lid | white_pot_lid | -127.0, -161.5 | 17.2 | -127.7, -157.0 | 14.6 | lid spin NOT consistent |
| Planter_Stand (23,24) | wooden_piece_1 | -175.7, -178.8 | 1.6 | 147.8, 132.7 | 7.6 | end on edge |
| Planter_Stand | wooden_piece_2 | -179.3, 178.0 | 1.4 | -121.7, -136.4 | 7.4 | |
| Pan_Solo (41-45) | white_pot | 2.4, 95.6, 63.6, 0.9, -4.5 | 40.6 | -2.1, 0.3, 0.9, -4.5, 0.3 | 2.0 | start varies, END tight |
| Cup_Stack (11) | beige / blue cup | 179.2 / 41.1 | - | -158.5 / 43.1 | - | single twin |

- Same object across tasks (same resting face):
  - rack 89.9 / 89.1 / 93.0 / 91.6 / 91.2: 3 tasks, rms 1.4 [V];
  - blue cup 41.1 / 64 / -69: task-specific;
  - the pot's upright start yaw is bimodal {~0, ~90}.
- Stable rest poses (s8) [V]:
  - pot upright: origin z 0.6452 +- 0.5 mm, tilt 12.1 +- 0.3;
  - rack: 0.6271 +- 0.3 mm, tilt 4.2 +- 0.3;
  - blue cup: 0.6875 +- 0.4 mm, tilt 1.6 +- 0.5;
  - pitcher: 0.7382 +- 0.3 mm, tilt 37.8 +- 0.2;
  - planks: flat 0.605-0.607, on edge 0.671-0.672.

### 2.2 Relative placement and the staging line  [V] `s2_relative.py`, `s14_layout.py` -> `s14_layout.{out,json}`
- Pair offsets at the start (B from slot-0 A):
  | task | offset of B (cm) | relative yaw (deg) | note |
  |---|---|---|---|
  | Cup_In_Dish_Rack | rack at (-16.7,-6.9) / (-15.3,+6.8) | 24.4 / 26.3 | rack farther from the person |
  | Water_Can | pitcher at (-3.5,+32.3) / (-2.1,+28.5) | 102.1 / 111.6 | |
  | Planter_Stand | piece_2 at (-1.2,+27.9) / (-0.4,+30.6) | -3.6 / -3.2 | |
  | Pot_with_lid | lid on pot | -131.9 / -166.1 | |
  | Cup_Stack (1 twin) | beige -> blue (0.0,-17.4) | -138.0 | |
  | Dust_Brush (1 twin) | pan -> sweeper (-0.4,+22.1) | 39.2 | |
  | Brush_Dishrack (1 twin) | sweeper -> rack (+0.3,-10.7) | 94.7 | |
- Staging line [V]: 8 of 11 separated start pairs (6 tasks) lie at a bearing of 91.8 +- 2.4 deg (mod 180), i.e. side by
  side along mocap y. The exceptions are Cup_In_Dish_Rack (22.5, 156.1) and Pan_In_Dishrack ep 27 (32.6).
- Side rule (object at +y = image right): sweeper (vs pan and vs rack), pitcher (vs cup), piece_2 (vs piece_1), beige
  (vs blue cup), pot (vs rack, ep 26).
- [V, stage C viewing] The table is ROUND, so the staging line is the seated person's left-right axis, not a table edge.

## 3. The mocap world

- [V] z = gravity in every episode (rest tilts identical to <= 0.5 deg sd).
- [V] Yaw is constant across all public episodes and sessions to ~1-2 deg, from GT alone (`s12_worldyaw.*`):
  - twin static objects agree to 0.1-0.7 deg;
  - the static rack reads 89-93 deg across task indices 5, 10 and 11;
  - only planks 23/24 shift together (~1.2 deg; placement or a tiny re-rotation).
- [V] The x,y origin is re-centred per episode; this is irrelevant to the slot-0-aligned scorer.
- [V, stage C] The world is fixed in the ROOM to <~1 deg across eps 0, 12, 13 and 21 (task indices 0, 5 and 8;
  section 8.3). Eps 22, 26 and 31 (up to task index 11) fit as well or better at the room-predicted heading (s28).
- [E] Every world-absolute prior in this document therefore transfers to the eval sessions, which were recorded
  interleaved with the public ones in the same room and seat (s7, s10).

## 4. Eval -> public twin map and slot-0 prior table  [V] `s10_twins.py`, `s13_priortable.py` -> `s13_priortable.{out,json}`

Mapping rule (automatic, no labels):
- same object multiset;
- task_index bracketed by the neighbouring public episodes;
- global parquet `index` gaps equal eval frame counts (0->2: 335 = 335; 18->21: 437; 24->26: 356);
- public `notes` field = within-task take number (Ep_k).
Withheld episodes (neither public nor eval): 4, 7, 9, 17, 29, 34. Eval 10 and 19 list their objects in the opposite
slot order to their public twin.

Prior types for slot-0 object A with co-object B:
- abs = world yaw of A (needs W);
- rel = yawA - yawB (W-free; needs B's yaw);
- brg = yawA - bearing(A->B) (W-free; positions only).
The table gives the mean and rms over twins and the twin pair difference (a leave-one-out error proxy).

| eval | task (twins) | slot-0 (sym) | best slot-0 prior | twin spread | what W adds |
|---|---|---|---|---|---|
| 1 | Pot_with_lid (0,2) | white_pot (A) | none needed | abs 4.7, rms 0.1 | lid spin prior weak (rel rms 17) |
| 3,5,6 | unknown, task_index 1-3 | white_pot (A) | none needed | pot start yaw bimodal | spoon: no public data |
| 8 | unknown, task_index 1-3 | beige_cup (C) | NONE from GT | - | nothing; needs markers |
| 10 | Cup_Stack (11), REVERSED order | blue_cup (C) | brg -49.0 or abs 41.1 (1 twin) | n=1 | abs 41.1 usable (W ~1 deg) |
| 14 | Cup_In_Dish_Rack (12,13) | blue_cup (C) | rel to rack -25.4 | rms 0.9, diff 1.9 | abs 64.1 (diff 2.7) as cross-check; rack branch by abs 89.5 |
| 15,16 | unknown, task_index 6 | rack (2) | abs 91.0, cross-task, needs W | rms 1.4 (3 tasks) | branch decided, margin ~88 deg |
| 19 | Dust_Brush (18), REVERSED | mini_sweeper (2) | rel to pan 39.2 / brg 105.2 | n=1 | abs branch 16.3 (ep 18) |
| 20 | Water_Can (21,22) | blue_cup (C) | brg -164.0 | rms 3.0, diff 6.0 | abs -68.8 (diff 8.0); end yaw -89 +- 0.9 |
| 25 | Planter_Stand (23,24) | wooden_piece_1 (2) | brg 91.2 | rms 0.6, diff 1.3 | abs -177.2 +- 1.5; plank IDENTITY via side rule |
| 28 | Pan_In_Dishrack (26,27) | rack (2) | abs 92.3 or brg 31.9 | abs rms 0.7; brg rms 27 | abs branch with margin ~88 |
| 30 | Brush_Dishrack (31) | mini_sweeper (2) | brg 84.9 (1 twin) | n=1 | abs branch -3.5; rack slot-1 abs 91 |
| 32,33 | unknown, task_index 12 | blue_cup (C) | NONE from GT | blue-cup abs is task-specific | nothing; needs markers |
| 35,36,37 | unknown, task_index 13 | wooden_spoon | single object | - | W irrelevant to the scorer |
| 38 | Dustpan_Solo (39,40) | mini_dust_pan (A) | single object | abs rms 6.9 | W irrelevant to the scorer |

In single-object episodes the scorer's frame-0 alignment absorbs any global yaw, so W is irrelevant there.

## 5. Score value of slot-0 anchor priors (official `score()`)

### 5.1 Leave-one-out on public episodes  [V] `s16_anchor_loo.py` -> `s16_anchor_loo.{out,json}`, `s16_summary.out`, `s16_aggregate.out`
Values are AUC / SP-SR / MP-SR / RPE cm / MPPE cm. The prior comes from the twin(s) only. For racks and the sweeper it
uses every other public episode holding that object.

| ep (anchor) | prior error (deg) | random spin | abs W=0 | abs W+-10 | best W-free |
|---|---|---|---|---|---|
| 12 (blue cup) | abs -2.7, rel -1.9, brg 43.7 | 0.19/0.12/0.04/23.5/18.9 | 0.97/1/1/0.9/0.7 | 0.72/1/0.5/3.2/2.6 | rel 1.00/1/1/0.6/0.5 |
| 13 (blue cup) | abs 2.7, rel 1.9, brg -43.7 | 0.17/0.12/0.07/12.6/20.2 | 0.96/1/1/0.5/0.7 | 0.73/1/0.5/1.7/2.8 | rel 1.00/1/1/0.3/0.5 |
| 21 (blue cup) | abs -8.0, rel -9.5, brg -6.0 | 0.35/0.18/0.01/40.4/24.3 | 0.74/1/0/4.4/2.7 | 0.73/1/0.5/5.5/3.3 | brg 0.84/1/0/3.3/2.0 |
| 22 (blue cup) | abs 8.0, rel 9.5, brg 6.0 | 0.40/0.21/0.04/32.1/19.2 | 0.81/1/0/3.5/2.1 | 0.76/1/0.5/4.4/2.6 | brg 0.87/1/1/2.6/1.6 |
| 23 / 24 (plank 1) | abs -3.1 / 3.1 (margin 87) | 0.51-0.52/0.5/0.5/10-12/17-18 | 1/1/1/0/0 | same | - |
| 26 / 27 (rack, cross-task n=4) | -2.5 / -0.8 (margin 88-89) | 0.75/0.5/0.5/17-19/9 | 1/1/1/0/0 | same | - |
| 31 (sweeper, from ep 18) | 19.8 (margin 70) | 0.55/0.5/0.5/11.9/9.6 | 1/1/1/0/0 | same | - |

Cup aggregates (4 eps) against W error [V] (`s30_anchor_wgrid.py` re-ran the stored model with the unmodified kit
`score()`; the stored rows reproduce exactly, max difference 0.0):

| cup anchor prior | AUC | SP-SR | MP-SR | RPE cm | MPPE cm |
|---|---|---|---|---|---|
| random spin | 0.277 | 0.16 | 0.04 | 27.1 | 20.7 |
| abs, W exact | 0.871 | 1.0 | 0.50 | 2.31 | 1.55 |
| abs, W +-1 | 0.884 | 1.0 | 0.50 | 2.31 | 1.55 |
| abs, W +-3 | 0.858 | 1.0 | 0.63 | 2.35 | 1.59 |
| abs, W +-5 | 0.846 | 1.0 | 0.75 | 2.59 | 1.87 |
| abs, W +-10 | 0.734 | 1.0 | 0.50 | 3.71 | 2.84 |
| rel (W-free) | 0.861 | 1.0 | 0.50 | 2.6 | 1.67 |
| per-task best W-free | 0.928 | 1.0 | 0.75 | 1.7 | 1.15 |

- The per-task best W-free row is optimistic: with 2 twins, the selection is the LOO error itself.
- Up to W = +-5 deg, the cost is within the noise of a 4-episode LOO. AUC is not monotone because W adds to a prior
  error of 2.7-8 deg and one sign partly cancels it.
- The limiting term is each prior's own twin spread (2.7 deg Cup_In_Dish_Rack, 8 deg Water_Can), not W.
- MP-SR rising with W in eps 21/22 (0 -> 0.5) is the same cancellation, not a real benefit.
- Two-fold anchors (5 eps): a random branch gives 0.616/0.5/0.5/13.9/12.5; the prior gives 1.0/1.0/1.0/0/0 for any
  W error <= 10 deg.

### 5.2 Error budget for the anchor spin  [V] s16/s17
- AUC >= 0.9 needs |spin error| <= ~5 deg; AUC is ~0.7 at 10 deg and ~0.5 at 15.
- SP-SR survives 20-30 deg.
- MP-SR fails beyond ~5-8 deg, because the other object is 17-31 cm from the anchor.
- Only Cup_In_Dish_Rack's prior (1.9-2.7 deg LOO) is tight enough for MP-SR; Water_Can's 6-8 deg spread is not.
- Eval-order proxies (`s17_proxy_tilt.*`):
  - ev10 (ep 11 with the static blue cup in slot 0): random already gives 0.70/0.32/0.17; |d| <= 20 gives >= 0.89. The
    stacked beige cup ends on the anchor's axis.
  - ev19 (ep 18 with the sweeper in slot 0): random branch 0.61 -> 1.0 with the correct branch.

### 5.3 Robustness to tracking noise  [V] `s21_anchor_noise.py` -> `s21_aggregate.out`
1 cm / 4 deg noise on every object, rest prior on:
- cups 0.255 -> 0.772 AUC (+0.52; +0.58 noiseless), SP-SR 0.16 -> 1.0;
- two-fold 0.549 -> 0.857 (+0.31).
About 85-90 % of the gain survives.

### 5.4 Projected eval impact [E]
Per-episode dAUC against a random or coin-flip anchor yaw:

| eval | dAUC | condition |
|---|---|---|
| 14 | +0.82 | |
| 20 | +0.45 | |
| 10 | +0.2..0.27 | |
| 19 | +0.39 | |
| 25 | +0.49 | only with the right plank identity |
| 28 | +0.25 | |
| 30 | +0.45 | |
| 15, 16 | ~+0.25 each | needs W; available now |
| 8, 32, 33 | 0 | no prior |

The sum (~3.6) / 20 gives a leaderboard AUC of about +0.18. The two-fold part is an upper bound: vision may already pick
the right branch from residual asymmetry (rack Chamfer 15 mm at 180).

## 6. Other room-memory priors

### 6.1 Anchor tilt (stable face + own table plane)  [V] `s17_proxy_tilt.py`
Constant tilt error of the slot-0 object, mean of 8 azimuths, AUC:

| tilt error | 2-object eps | 1-object eps |
|---|---|---|
| 1 deg | 1.000 | 1.000 |
| 3 deg | 0.988 | 0.984 |
| 5 deg | 0.952 | 0.957 |
| 8 deg | 0.888 | 0.893 |

Snapping the anchor to its resting face (~1 deg residual) is worth +0.01 / +0.05 / +0.11 AUC when vision tilt error is
3 / 5 / 8 deg.

### 6.2 Rest snap of all on-table static segments  [V] `s20_rest_snap.py`, `s31_rest_split.py` -> `s20_aggregate.out`, `s31_rest_split.{out,json}`
All 20 public eps, 4 seeds, isotropic vision noise. Snap residual: z 1 mm, tilt 1 deg [E]. The s31 "both" mode
reproduces s20 exactly.

| noise | mode | AUC | SP-SR | MP-SR | RPE | MPPE | dAUC per ep (min / median / max) |
|---|---|---|---|---|---|---|---|
| 0.5 cm / 2 deg | vision | 0.947 | | 0.99 | 0.79 | 1.14 | - |
| | z + tilt | 0.964 | | 1.00 | 0.71 | 0.98 | -0.001 / +0.014 / +0.038 |
| 1 cm / 4 deg | vision | 0.818 | 1.00 | 0.78 | 1.58 | 2.28 | - |
| | z only (table height) | 0.831 | 1.00 | 0.78 | 1.45 | 2.17 | -0.001 / +0.011 / +0.035 |
| | tilt only (stable face) | 0.849 | 1.00 | 0.78 | 1.53 | 2.06 | -0.002 / +0.024 / +0.079 |
| | z + tilt | 0.862 | 1.00 | 0.78 | 1.40 | 1.94 | -0.001 / +0.035 / +0.088 |
| 2 cm / 8 deg | vision | 0.562 | 0.98 | 0.13 | 3.15 | 4.56 | - |
| | z only | 0.584 | 0.99 | 0.21 | 2.91 | 4.35 | -0.001 / +0.022 / +0.050 |
| | tilt only | 0.597 | 1.00 | 0.15 | 3.05 | 4.10 | -0.005 / +0.033 / +0.093 |
| | z + tilt | 0.624 | 1.00 | 0.28 | 2.80 | 3.86 | +0.004 / +0.058 / +0.136 |

- Never harmful beyond -0.005 AUC on any episode. Needs only our own table plane plus the stable-face table (s8), not W.
- The two parts are roughly additive. Tilt gives ~2/3 of the AUC gain and most of the MPPE gain; table height gives most
  of the RPE gain and, at 2 cm, most of the MP-SR gain.
- [E] A stereo pipeline whose depth error lies along the oblique view ray puts more error into z, so the table-height
  share would be larger than measured with isotropic noise.
- Table height itself (0.6012 m) does not matter to the scorer, which aligns on the slot-0 object, except through
  relative z.

### 6.3 Final-placement priors  [V] `s18_endplace.py`, `s19_endsnap_score.py` -> `s18_endplace.out`, `s19_summary.out`
- Consistent across public takes:
  - lid on pot: 0.2 cm translation, 1.1 deg axis, spin free;
  - plank cross-joint: 0.3 cm, 3.8 deg (full 6-DoF).
- World end yaw (needs W): Water_Can cup -88.1 / -89.9 (tilt 1.1); Pan_Solo pot -4.5..0.9 (rms 2.0).
- NOT consistent: cup in rack (15 cm apart, different slot), pot in rack (21 cm, different face) and the pitcher pour
  pose. A rack-slot snap would need the rack's slot geometry, not room memory [H].
- Score value of snapping the placed segment (15-30 % of frames):
  - +0.01..+0.04 AUC at 1-3 cm / 5-15 deg vision error;
  - RPE 0.5-0.9 -> 0.06 cm;
  - SP-SR and MP-SR unchanged.
- [H] The larger value may be physical: a seated lid or interlocked planks in the reference could matter for the
  FlashCHORD policy. Untested.

## 7. Other ambiguities

- Plank identity (ev25) [V]: the wooden_piece_1/_2 scans are geometrically identical (Chamfer 2.5-2.6 mm under every flip
  vs a 2.0 mm floor). Combined with two-fold symmetry, the W-free bearing rule cannot separate "swap" from "flip 180".
  A swapped identity anchors on the wrong plank, which starts 28-31 cm away.
  Resolvers:
  - (a) side rule: piece_2 at +y (image right) of piece_1 (bearing 92.5 / 90.7). Uses W; margin ~88 deg [E].
  - (b) motion order: piece_1 moves first (f22 vs f128 in ep 23; f12 vs f115 in ep 24).
  - (c) marker layout.
  - (d) [H, weak] texture: piece_2's up face is paler (HSV sat 0.41 vs 0.52, `s29_plank_colour.out`). Table lighting
    varies left/right, so this cue is unreliable alone.
- Roles (who moves) [V], useful as identity and consistency checks:
  - Cup_Stack: beige moves onto a static blue cup.
  - Rack tasks: rack static.
  - Water_Can: pitcher moves first.
  - Pot_with_lid: lid first, pot later.
  - Dust_Brush: pan first.
- Rack near-two-fold [V]: resolved W-free in ev14 (brg 90.2 +- 23), ev28 (31.9 +- 27) and ev30 (slot-1 brg -0.4). With
  W, every rack branch (including ev15/16) is decided by abs ~91 with margin ~88 deg.
- ev20 caveat [V, viewing]: the slot-0 cup is already lifted in the left hand at frame 0, so the resting-start yaw prior
  is only approximate for its spin [H]. Validate on the ev20 video with marker vision before trusting it for MP-SR.

## 8. Estimating W on eval episodes (stage C)

### 8.1 Definition
Our world: gravity-aligned (own table plane), x = the frame-0 optical axis projected on the table, z up, y = z x x
(image left).
- W_e = the mocap yaw of that x axis, i.e. the camera heading psi_e in the mocap world.
- A mocap-world yaw prior y_m maps to our frame as y_ours = y_m - W_e.
- A bearing or long-axis direction measured in our frame maps the other way: y_m = y_ours + W_e.

### 8.2 What the frames show  [V] frame 0 of public 0/11/12/13/21/22/23/26/31 and eval 10/14/15/16/20/25/28/30 (`cfr/`)
- The table is a small round wooden top, so there is no table-edge cue.
- Fixed room features are visible in every frame 0: a black truss straight ahead, yellow/black hazard tape and blue tape
  on the floor, floor arrows, a box and cages. Background people are sometimes present (ep 22).
- The seat and head pose are nearly identical across episodes. Headings vary by a few degrees (sd ~2.7).
- Image right = mocap +y: pitcher right of cup, beige right of blue, rack tower on the left with its long axis
  left-right.
- Eval staging matches the twins, including the twin-less rack episodes 15/16 (co-object: a wooden spoon).
- All objects carry black dome markers, a usable spin cue.

### 8.3 Method R: GT-silhouette camera fits on public frames + room registration (primary)  [V]
1. Fit.
   - `s23_mask.py`: object colour mask.
   - `s24_campose.py`: grid search plus Nelder-Mead over the 6-DoF camera in the mocap world. GT-posed scan point
     splats are scored by IoU against the mask components they touch; dark pixels are don't-care, and off-image model
     area is penalised.
   - `s25_refine.py`: GrabCut mask seeded by the rendering (2 rounds), followed by a heading profile (psi fixed at +-2
     and +-4, the other 5 DoF re-fit).
   - Heading / IoU per episode (K as given; flipped-K values in brackets):

     | ep | psi (K as given) | psi (flipped K) | IoU as given / flipped | heading profile |
     |---|---|---|---|---|
     | 12 | 180.6 | (177.8) | 0.951 / 0.952 | sharp, pinned to ~1-2 deg |
     | 13 | 183.0 | (180.7) | 0.969 / 0.971 | sharp |
     | 0 | 181.4 | (181.4) | 0.953 / 0.961 | sharp |
     | 21 | 177.0 | (175.1) | 0.874 / 0.887 | borderline |
     | 22 | 176.8 | (175.7) | 0.872 / 0.877 | flat: heading vs lateral-shift degeneracy |
     | 26 | 182.6 | (180.9) | 0.912 / 0.907 | flat |
     | 31 | - | (174.8) | - / 0.874 | flat |

   - Overlays: `cfr/ref_{native,flipped}_<ep>.png`, `cfr/m_ref.png`.
   - The colour mask failed on ep 11 (two spin-symmetric cups), 18 and 39 (yellow pan), 41 (single pot, floor glare) and
     23 (planks on wood); these were not used. Lesson: silhouettes pin the heading only with an asymmetric object or two
     separated objects and a usable mask.
2. Transfer (`s26_transfer.py`): SIFT on the top 55 % of frame 0 (room background), pairwise pure-rotation RANSAC with a
   0.35 deg threshold. Then R_wc,q = R_wc,p R_pq^T, and the heading is read from the optical axis. Every public and eval
   frame 0 registered (min inliers 167-192 per pair on ev35/ev32).
3. Validation (`s27_transfer_stats.py`, `s32_refset.py`): leave-one-out, predicting each reference from the OTHER
   references (median) and comparing with its own fit.

   | reference set | how chosen | LOO rms, K as given | LOO rms, flipped K |
   |---|---|---|---|
   | sharp3 {12,13,0} | a priori (sharp profile) | 1.55 | 0.83 |
   | best4 {12,13,21,0} | after seeing residuals | 1.18 | 0.65 |
   | all fitted (6 / 7) | - | 2.85 | 2.32 |

   - The all-refs LOO is inflated by the flat-profile fits 22 (+5.2 / +5.7) and 26 (-2.9 / -3.3).
   - Those are errors of the GT fits themselves. With psi fixed at the room value (`s28_fixedpsi.py`), the IoU is
     0.8724 vs 0.8726 for ep 22 (indistinguishable), 0.9212 vs 0.9075 for ep 26 (room value BETTER) and 0.8835 vs 0.8824
     for ep 31.
   - So all 7 fits are consistent with one room-fixed world.
4. Robustness of the eval table to the reference choice (`s32_refset_{native,flipped}.out`) [V]:
   - sharp3 - best4 = +0.35 +- 0.15 deg (native, max 0.72) / +0.26 +- 0.06 (flipped, max 0.46);
   - all - best4 <= 0.46.
   - The median over references discards the flat-profile outliers, so the post-hoc selection costs <= ~0.3 deg of bias.
5. Gravity (`s27_gravity_loo_flipped.out`): roll transfers to +-1 deg, but pitch only to 2-5 deg (silhouettes pin pitch
   poorly). Take gravity from our own table plane, not from the transfer.
6. Conclusion [V]: the mocap world is fixed in the room to <~1 deg, and room registration transfers the mocap heading to
   any frame 0 with ~1.2-1.6 deg error [V on the refs, E on eval], provided the fits, the registration and our pipeline
   share one camera model (section 8.4).

### 8.4 Colour-camera K convention: resolved  [V] `s33_kcheck.py` -> `s33_kcheck_b_12.json`, `s33_kcheck_b_multi.out`, `s33_kcheck_b_0-13-21-22-26-27-11.json`
- Question: does the published ego_cam_a principal point (cx 994.8, cy 767.5) describe the upright stored image, or the
  raw sensor? The flipped variant is cx 1032.2, cy 751.5, with the odd distortion terms negated. The two differ by
  ~1.9 deg of heading. The stage C silhouette fits weakly preferred flipped (IoU +0.001..+0.013, LOO 0.65 vs 1.18 on
  n = 4).
- Test: cam_a and cam_b are on the same ego device with a calibrated `extrinsics_to_stereo_left` (X_b = R X_a + t,
  t_x = -3.74 cm, so b is right of a in the upright image).
  - SIFT matches (cam_a at half resolution), then model-free fundamental-RANSAC inliers.
  - Sampson error under the calibrated E (px at f = 1150).
  - Free essential-matrix rotation vs the calibrated R.
  - Data: eps 0, 11, 12, 13, 21, 22 and 26, frames 0-220, 26 frame pairs. Ep 27 was skipped (no local cam_a).

  | cam_a / cam_b K | median abs Sampson (px), 23 pairs | p25-p75 | free - calibrated rotation, median (x, y, z) deg |
  |---|---|---|---|
  | as given / as given | 4.5 | 3.1-6.5 | (-0.10, +0.26, -0.27) |
  | as given / flipped | 6.8 | 4.9-10.8 | (+0.44, -0.42, -0.22) |
  | flipped / as given | 13.7 | 12.2-16.9 | (+0.77, +2.33, -0.22) |
  | flipped / flipped | 20.4 | 18.6-22.1 | (+1.23, +1.88, -0.12) |

  - Ep 12 alone (3 frames): as given 2.4-10 px vs flipped 14-23 px.
  - cam_a as given wins on 22 of 23 pairs for both cam_b variants.
  - Conjugating R by Rz180 makes every combination worse (24-48 px).
- [V] Conclusion: images, extrinsics and intrinsics are all expressed in the upright frame, and the colour K is right AS
  GIVEN. The flipped principal point needs a ~2.1 deg rotation about the camera y axis and ~0.9 deg about x, which
  matches its 37 px / 16 px cx/cy shift. The silhouette preference for flipped was a fit artefact (principal point traded
  against lateral shift) or n = 4 noise.
- Consequence: use the native (as-given) W table below. Per 5.1, the old ~2 deg ambiguity cost <= ~0.02 AUC, so earlier
  conclusions stand.

### 8.5 Alternatives for W, compared

| method | coverage of eval | error of W | notes |
|---|---|---|---|
| R: room registration to fitted public frames (8.3) | all 20 | 1.18 deg LOO (best4) / 1.55 (sharp3), K as given [V] | independent of object vision |
| O: asymmetric or branch-resolved co-object with a world prior (W = prior(B) - yaw_ours(B)) | ev1 pot (0.3), ev14/28/30 rack (0.8-2.6, mod 180), ev20 pitcher (1.5), ev25 planks (3.1, mod 180), ev19 pan (1 twin) | twin LOO spread [V] plus B's vision yaw error [E 2-5] | none for ev10 (two C cups) or ev15/16 (W mod 180 only); task-specific |
| S: staging line (bearing of two separated objects, sign from the side rule) | two-object eps with separated objects | 2.4 deg sd across 6 tasks, plus position noise (1 cm at 17 cm = 3.4 deg) [V/E] | W mod 180 only; fails for Cup_In_Dish_Rack and Pan_In_Dishrack ep 27 |
| P: population prior (same seat, no registration) | all | sd 2.7 deg around 180.3 (K as given) [V] | enough for every two-fold branch and for ev10; not for MP-SR-grade cup spin |
| T: floor-tape vanishing direction [H] | all (tape visible in every frame 0) | untested | registration-free check; calibrate the tape's mocap yaw offline on the refs |
| table edge | none | - | the table is round |

Recommendation: use R as the primary source of W.
- O is a per-episode consistency check: flag |prior(B) - (yaw_ours(B) + W)| > ~8 deg as either a vision error on B or an
  unusual take.
- P is the fallback when registration has too few inliers.

### 8.6 Error terms in W [E]
- Registration and reference fits: ~1.2-1.6 deg rms [V on references].
- Reference-set choice: <= 0.7 deg [V].
- Gravity: a roll error eps of our table plane about the optical axis turns the projected heading by ~eps * sin(pitch).
  Pitch is 38-53 deg (s27), giving 0.6-0.8 eps. Anchor yaws measured in the same tilted frame partly cancel this.
- Total: ~1.5 deg. For comparison, the twin spreads of the priors are 1.4-8 deg, and the cup budget is flat to +-5 deg
  (5.1).

### 8.7 W for the 20 eval episodes  [V] `s27_stats_native_best4.json` (primary), `s27_stats_flipped_best4.json`
Camera heading of frame 0 in the mocap world (deg), median over refs {12,13,21,0}. Columns: K as given (USE THIS) /
flipped K (for reference only) / spread over refs (as given).

| ev | as given | flipped | spread | ev | as given | flipped | spread |
|---|---|---|---|---|---|---|---|
| 1 | 184.2 | 182.5 | 0.9 | 20 | 178.6 | 176.4 | 1.2 |
| 3 | 179.5 | 177.6 | 1.0 | 25 | 182.2 | 180.4 | 0.9 |
| 5 | 179.3 | 177.3 | 1.1 | 28 | 179.4 | 177.2 | 1.2 |
| 6 | 178.5 | 176.6 | 1.0 | 30 | 183.0 | 180.8 | 1.2 |
| 8 | 183.8 | 181.8 | 1.0 | 32 | 184.6 | 182.5 | 1.1 |
| 10 | 180.4 | 178.5 | 0.9 | 33 | 177.1 | 174.9 | 1.3 |
| 14 | 181.9 | 180.2 | 0.8 | 35 | 174.1 | 171.4 | 1.8 |
| 15 | 180.8 | 178.7 | 1.1 | 36 | 178.1 | 175.9 | 1.3 |
| 16 | 182.8 | 181.1 | 0.9 | 37 | 176.1 | 173.7 | 1.4 |
| 19 | 179.4 | 177.3 | 1.1 | 38 | 177.2 | 174.6 | 1.5 |

### 8.8 Ready-to-use anchor priors in OUR frame (K as given)  [V arithmetic, E transfer] `s34_prior_ours.py` -> `s34_prior_ours.{out,json}`
y_ours = y_m - W_e. For two-fold objects (sym 2), vision measures yaw mod 180 and the full-circle prior picks the
branch. For cups (C), the prior IS the spin.

| ev | object | y_mocap | W | y_ours | sym | note |
|---|---|---|---|---|---|---|
| 10 | blue_cup | 41.1 | 180.35 | -139.3 | C | Cup_Stack, n = 1 |
| 14 | blue_cup | 64.1 | 181.94 | -117.8 | C | rel-to-rack -25.4 preferred; this as cross-check |
| 14 | rack | 89.5 | 181.94 | -92.4 | 2 | branch |
| 15 | rack | 91.0 | 180.75 | -89.7 | 2 | cross-task rms 1.4 |
| 16 | rack | 91.0 | 182.79 | -91.8 | 2 | cross-task rms 1.4 |
| 19 | mini_sweeper | 16.3 | 179.38 | -163.1 | 2 | ep 18, n = 1 |
| 20 | blue_cup | -68.8 | 178.57 | +112.6 | C | twin diff 8; cup in hand at f0 |
| 25 | wooden_piece_1 | -177.2 | 182.20 | +0.6 | 2 | rms 1.5 |
| 28 | rack | 92.3 | 179.39 | -87.1 | 2 | rms 0.7 |
| 30 | mini_sweeper | -3.5 | 182.97 | +173.5 | 2 | ep 31, n = 1 |

Sanity check [V]: the rack's HREF axis at mocap ~90 points to image right (our -y), giving ~ -90 in our frame. This
matches the tower-left staging seen in every rack frame 0.

### 8.9 Falsification tests run / remaining
- Run [V]: the world-room link would have been unusable if the LOO heading residual exceeded ~5 deg. Measured 0.65-1.55
  rms over K variants and reference sets; the largest outliers are explained by flat profiles.
- Run [V]: K convention. If the flipped principal point had been right, its epipolar error would have been the lower
  one. It was 3x higher.
- Supporting [V, weaker]: eps 26 (task index 10) and 31 (11) fit as well or better at the room-predicted heading (s28).
- Remaining:
  - only 4 well-conditioned public references, all from task indices 0-8;
  - eval sessions with task indices 12-13 (ev32-37) rely on the same room/seat assumption (their registrations have
    167-568 inliers and a 1.1-1.8 deg ref spread);
  - a direct check would be a well-conditioned GT fit on a late public episode (39-45 are single objects and poorly
    conditioned here; marker-based or edge-based fits may work).

## 9. Recommendations (implementation order)
1. Room-memory W (8.3, 8.7). Store the 4 reference frames and their fitted R_wc (K as given). At inference:
   - register eval frame 0 to them (SIFT on the top 55 %, pure-rotation RANSAC, 0.35 deg threshold);
   - take the median heading;
   - take gravity from our own table plane.
   Cost: < 1 s per episode. Use the as-given calibration everywhere.
2. Slot-0 anchor yaw for symmetric anchors (8.8):
   - ev14: rel to rack (cross-check with abs);
   - ev20: brg -164 or abs -68.8 via W (cup lifted at frame 0: verify with markers);
   - ev10: abs 41.1 via W (or brg -49);
   - two-fold branches (15, 16, 19, 25, 28, 30): abs world yaw via W;
   - ev25 plank identity: side rule via W, plus motion order.
3. Marker-based spin for ev8/32/33, and as an override wherever markers are clearly visible (note 12: ~2 deg on a public
   frame).
4. Rest snap (stable face + own table plane) on static segments, plus the anchor tilt snap. Small, never harmful.
5. End-placement snaps (lid on pot, plank interlock), mainly for physical consistency of the reference [H].
6. Consistency checks: method O per episode (flag > 8 deg) and population prior P as the fallback.
7. Keep inference automatic: twin selection by object set + task_index bracketing, no per-episode labels. Eval GT is
   never read.

## 10. Limitations
- At most two public takes per task, so every LOO is one comparison. Single-twin priors (ev10, ev19, ev30) are
  unvalidated.
- AUC uses sampled scan points [E]. All score experiments are kinematic; physical (FlashCHORD) effects are untested.
- W reference fits rely on 4 public frames and a colour-mask/GrabCut silhouette fit. Heading is degenerate with lateral
  shift for symmetric or single objects.
- The K test resolves the principal point only to the extent the factory extrinsic is right. The free rotation agrees
  with it to ~0.3 deg under K as given.
- ev20's anchor is in hand at frame 0. Unknown-task episodes (3, 5, 6, 8, 15, 16, 32, 33, 35-37) have no task prior
  except cross-task object staging.

## 11. Artifacts (all in `/Users/aebatirel/Documents/Code/v2d-research/work/11/`)

| stage | scripts | outputs |
|---|---|---|
| A | `c11.py` (loaders, yaw/tilt, UP/HREF), `s1_poses.py`, `s2_relative.py`, `s3_loo.py`, `s4_markers.py`, `s5_symmetry.py`, `s6_twofold.py`, `s7_roomreg.py`, `s8_rest.py`, `s9_stableprior.py`, `s10_twins.py`, `s11_consistency.py`, `s12_worldyaw.py`, `s13_priortable.py`, `s14_layout.py`, `s15_loo_brg.py` | `.json`/`.out`/`.csv` with the same stem; `tex/*.png` |
| B | `sc11.py` (official `score()` wrapper), `s16_anchor_loo.py`, `s17_proxy_tilt.py`, `s18_endplace.py`, `s19_endsnap_score.py`, `s20_rest_snap.py`, `s21_anchor_noise.py`, `s30_anchor_wgrid.py`, `s31_rest_split.py` | `.json`/`.out` with the same stem, plus `*_aggregate.out` / `*_summary.out` |
| C | `s22_dump.py`, `s23_mask.py`, `s24_campose.py`, `s24_view.py`, `s25_refine.py`, `s26_transfer.py`, `s27_transfer_stats.py`, `s28_fixedpsi.py`, `s32_refset.py`, `s33_kcheck.py`, `s34_prior_ours.py` | `s24_campose_{flipped,native}.json`, `s25_refine_{flipped,native}.json`, `s26_transfer_{flipped,native}_s25_refine_*.json`, `s27_*.out`, `s27_stats_{flipped,native}_best4.json`, `s28_fixedpsi_flipped.json`, `s29_plank_colour.out`, `s32_refset_{native,flipped}.{out,json}`, `s33_kcheck_b_*.json`, `s33_kcheck_b_multi.out`, `s34_prior_ours.{out,json}`; frames/overlays in `cfr/`, `frames/`; logs in `logs/` |

Example commands:
- `python s25_refine.py native 12 13 21 0`
- `python s26_transfer.py native s25_refine_native.json`
- `python s27_transfer_stats.py s26_transfer_native_s25_refine_native.json s25_refine_native.json 12,13,21,0`
- `python s32_refset.py native`
- `python s33_kcheck.py 0,13,21,22,26,27,11 0,40,100,160,220 b`
- `python s34_prior_ours.py`

Local clips used:
- public cam_a 0, 11, 12, 13, 18, 21, 22, 23, 26, 31, 39, 41;
- public cam_b 0, 11, 12, 13, 21, 22, 26, 27;
- public cam_c 12;
- all 20 eval cam_a.

No downloads were made in stages B/C or the retries. A stale `public/.../ego_cam_b/episode_000031.mp4.part.56507` from
the stage A outage is left untouched.

## 12. Change log
- 2026-10-05: stages A, B and C (raw log `notes_stageAB_C_log_backup.md`).
- 2026-10-06, stage B retry: s16 results reproduced exactly with the kit `score()`. Added the W +-1/+-5 rows (s30) and the
  rest-snap z/tilt split (s31).
- 2026-10-06, stage C retry:
  - reference-set robustness (s32);
  - colour K convention resolved by the cam_a<->cam_b epipolar test (s33), which flipped the earlier weak preference
    for flipped K and made the as-given W table primary;
  - priors in our frame (s34);
  - visual re-check of `cfr/m_ref.png` and `cfr/m_eval_f0.png`;
  - full rewrite.
  The verbatim pre-rewrite text is in `notes_pre_final_rewrite_2026-10-06.md`.
