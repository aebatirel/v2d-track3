# 11 — Placement priors, room memory and the mocap-world link (DIG 11, final)

Status: COMPLETE (stages A, B, C), 2026-10-05; stage B re-verified and extended 2026-10-06 (section 12). Agent 11. Research and analysis only; nothing submitted, no evaluator,
physics or SlamDunk code touched. Scripts and outputs: `/Users/aebatirel/Documents/Code/v2d-research/work/11/`
(run as `/Users/aebatirel/Documents/Code/v2d-research/venv/bin/python <script>` inside that directory). The raw,
chronological stage notes that this document consolidates are preserved verbatim in
`work/11/notes_stageAB_C_log_backup.md`.
Tags: [V] verified numerically here, [E] estimate, [H] hypothesis.

## 0. Bottom line

1. [V] Staging is highly repeatable. Within a task, each object's start yaw in the mocap world agrees to <= 4 deg rms
   over the public takes (rack 0.4, Cup_In_Dish_Rack cup 1.4, Water_Can cup 4.0, pitcher 0.8, planks ~1.5, Pot_with_lid
   pot 0.2). Exceptions: lid (17), dust pan (7), and the pot when its resting face changes. Tilt and height follow the
   resting face (sd <= 0.5 deg / 0.5 mm). The rack sits at world yaw 89-93 deg with its tower on the person's left in
   all three public rack tasks. Viewing frame 0 shows the same in all five eval rack episodes.
2. [V] The mocap world is gravity-aligned, has the same yaw in every public session, and is fixed relative to the room
   to <~1 deg. The camera is head-mounted at the same seat: it looks along mocap -x (heading 178 +- 3 deg), and image
   right is mocap +y. The table is small and ROUND, so no table edge exists to give yaw.
3. [V] W can be measured on every eval episode with ~1 deg error. W is the mocap yaw of our frame-0 camera heading,
   i.e. the rotation from "our world" to mocap yaw. Method:
   - Offline: fit the frame-0 camera of public episodes in the mocap world by aligning silhouettes of the GT-posed scans.
   - Online: register each eval frame 0 to those public frames on the static room background (pure rotation).
   Leave-one-out against the GT fits gives 0.65 deg rms (flipped-cx K) / 1.18 deg (K as given). The W values for all 20
   eval episodes are in section 8.6.
   - Asymmetric co-objects give W only for some tasks, with 0.3-3 deg prior error plus their own vision yaw error.
   - The staging line gives W only modulo 180, with 2.4 deg sd and task exceptions.
   - Both are useful as consistency checks, not as the primary source.
4. [V] Value of the priors under the official scorer (kit `score()`; perfect tracking unless noted):
   - Spin-symmetric slot-0 cup anchor set from the task prior instead of a random spin (LOO, 4 public eps):
     AUC 0.277 -> 0.871 (W exact), 0.858 (W +-3), 0.734 (W +-10); SP-SR 0.16 -> 1.0; RPE 27 -> 2.3 cm; MPPE 21 -> 1.6 cm.
   - Two-fold slot-0 anchors (planks, rack, sweeper): AUC 0.616 -> 1.0 with any W <= 10 deg.
   - About 85-90 % of these gains survive 1 cm / 4 deg tracking noise.
   - Projected eval gain: about +0.18 on leaderboard mean AUC (cups +0.08, two-fold +0.10; the two-fold part is an upper
     bound) [E].
5. [V] The measured W unlocks the following priors:
   - absolute world priors for ev10 (Cup_Stack cup), ev15/16 (twin-less rack branch) and ev20 (cup; alternative to the
     bearing prior);
   - the plank side rule that resolves ev25's plank identity;
   - world end-yaw priors (Water_Can cup, Pan_Solo-type pot).
   At ~1 deg, W is no longer the error-limiting term; the twin spread of each prior is.
6. [V] Not solvable by priors: ev8, ev32 and ev33. Their slot-0 cups belong to unseen tasks, so their spin must come
   from vision (the Vicon markers baked into the scan textures; note 12 shows markers fix a cup's spin to ~2 deg on a
   public frame).
7. [V] Other room-memory priors are small but safe:
   - rest snap (stable face + own table plane) on static segments: +0.015 / +0.035 / +0.06 median AUC per episode at
     0.5 / 1 / 2 cm noise, never harmful;
   - anchor tilt snap: +0.01..+0.11 depending on vision tilt error;
   - end-placement snap (lid on pot, plank interlock): +0.01..+0.04, possibly more value physically [H].

## 1. Data, conventions and scorer facts used

- Public GT: `observation.objects` pose = world_T_object in the raw scan (GLB) frame. No Y-up conversion is applied
  (note 07). x,y are re-centred per episode on the all-frame, all-object mean. z is physical (table top 0.6012 m, s8).
- Yaw = heading of a fixed horizontal body axis (HREF in `c11.py`) about world z. Tilt = angle of the resting-up body
  axis (UP) from +z. Spin-symmetric cups and lid: C. Two-fold mini_sweeper, both planks and the (near two-fold) rack: 2.
  Pot, pitcher and dust pan are asymmetric (s5 Chamfer self-similarity).
- Scorer: aligns ONE rigid transform from the slot-0 object's frame-0 pose; no scale. A spin or branch error of a
  symmetric slot-0 anchor therefore rotates the whole scene about the anchor in every frame (s6: 180 deg = AUC
  0.03-0.50, SP 0, MP 0). This is why the anchor's yaw is the main lever for placement priors.
- AUC values here use 500 area-weighted scan samples per object, not the organisers' hidden vertex set [E]. Wrapper
  `sc11.py` reproduces the internal metric functions exactly (ep 12, spin 30: AUC 0.18405, MPPE 7.7947).
- Video: decoded MP4 frames are already upright; do not rotate again (checked here and in notes 12 and 15). Calibration
  K for ego_cam_a: see section 8.5 (principal-point variant matters ~1.9 deg for an absolute W).

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
- Staging line [V]: 8 of 11 separated start pairs (6 tasks) lie at a bearing of 91.8 +- 2.4 deg (mod 180), i.e.
  side by side along mocap y. The exceptions are Cup_In_Dish_Rack (22.5, 156.1) and Pan_In_Dishrack ep 27 (32.6).
- Side rule (object at +y): sweeper (vs pan and vs rack), pitcher (vs cup), piece_2 (vs piece_1), beige (vs blue cup),
  pot (vs rack, ep 26).
- Stage C correction [V]: the table is ROUND, so the staging line is the seated person's left-right axis, not a table
  edge. Mocap +y = image right in every clip viewed.

## 3. The mocap world

- [V] z = gravity in every episode (rest tilts identical to <= 0.5 deg sd).
- [V] Yaw is constant across all public episodes and sessions to ~1-2 deg, from GT alone (`s12_worldyaw.*`):
  - twin static objects agree to 0.1-0.7 deg;
  - the static rack reads 89-93 deg across task indices 5, 10 and 11;
  - only planks 23/24 shift together (~1.2 deg; placement or a tiny re-rotation).
- [V] The x,y origin is re-centred per episode; this is irrelevant to the slot-0-aligned scorer.
- [V, Stage C] The world is fixed in the ROOM to <~1 deg across eps 0, 12, 13 and 21 (task indices 0, 5 and 8;
  section 8.3). Eps 26 and 31 (task indices 10-11) are consistent within their weaker fits. [E] So every world-absolute prior in this document transfers to the eval sessions, which were recorded
  interleaved with the public ones in the same room and seat (s7, s10).

## 4. Eval -> public twin map and slot-0 prior table  [V] `s10_twins.py`, `s13_priortable.py` -> `s13_priortable.{out,json}`

Mapping rule (automatic, no labels):
- same object multiset;
- task_index bracketed by the neighbouring public episodes;
- global parquet `index` gaps equal eval frame counts (0->2: 335 = 335; 18->21: 437; 24->26: 356);
- public `notes` field = within-task take number (Ep_k).
Withheld episodes (neither public nor eval): 4, 7, 9, 17, 29, 34.

Prior types for slot-0 object A with co-object B:
- abs = world yaw of A (needs W);
- rel = yawA - yawB (W-free; needs B's yaw);
- brg = yawA - bearing(A->B) (W-free; positions only).
The table gives mean / rms over twins and the twin pair difference (a leave-one-out error proxy). The "W unlocks"
column is new in stage C.

| eval | task (twins) | slot-0 (sym) | best slot-0 prior | twin spread | what W (section 8) adds |
|---|---|---|---|---|---|
| 1 | Pot_with_lid (0,2) | white_pot (A) | none needed | abs 4.7, rms 0.1 | lid spin prior weak (rel rms 17) |
| 3,5,6 | unknown, task_index 1-3 | white_pot (A) | none needed | pot start yaw bimodal | spoon: no public data |
| 8 | unknown, task_index 1-3 | beige_cup (C) | NONE from GT | - | nothing; needs markers |
| 10 | Cup_Stack (11), REVERSED order | blue_cup (C) | brg -49.0 or abs 41.1 (1 twin) | n=1 | abs 41.1 usable (W ~1 deg) |
| 14 | Cup_In_Dish_Rack (12,13) | blue_cup (C) | rel to rack -25.4 | rms 0.9, diff 1.9 | abs 64.1 (diff 2.7) as cross-check; rack branch by abs 89.5 |
| 15,16 | unknown, task_index 6 | rack (2) | abs 91.0, cross-task, needs W | rms 1.4 (3 tasks) | branch decided, margin ~88 deg |
| 19 | Dust_Brush (18), REVERSED | mini_sweeper (2) | rel to pan 39.2 / brg 105.2 | n=1 | abs branch, sweeper ~0..16 mod 180 |
| 20 | Water_Can (21,22) | blue_cup (C) | brg -164.0 | rms 3.0, diff 6.0 | abs -68.8 (diff 8.0); end yaw -89 +- 0.9 |
| 25 | Planter_Stand (23,24) | wooden_piece_1 (2) | brg 91.2 | rms 0.6, diff 1.3 | abs -177.2 +- 1.5; plank IDENTITY via side rule |
| 28 | Pan_In_Dishrack (26,27) | rack (2) | abs 92.3 or brg 31.9 | abs rms 0.7; brg rms 27 | abs branch with margin ~88 |
| 30 | Brush_Dishrack (31) | mini_sweeper (2) | brg 84.9 (1 twin) | n=1 | abs -3.5 mod 180; rack slot-1 abs 91 |
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

Aggregates [V]:
- Cups (4 eps):
  - random 0.277/0.16/0.04/27.1/20.7;
  - abs W0 0.871/1.0/0.50/2.3/1.55;
  - abs W+-3 0.858/1.0/0.63/2.3/1.59;
  - abs W+-10 0.734/1.0/0.50/3.7/2.84;
  - rel 0.861/1.0/0.50/2.6/1.67;
  - per-task best W-free 0.928/1.0/0.75/1.7/1.15 (optimistic: with 2 twins the selection is the LOO error itself).
- Two-fold (5 eps): random branch 0.616/0.5/0.5/13.9/12.5 -> 1.0/1.0/1.0/0/0 for any W <= 10.

### 5.2 Error budget for the anchor spin (curves)  [V] s16/s17
- AUC >= 0.9 needs |spin error| <= ~5 deg; ~0.7 at 10; ~0.5 at 15.
- SP-SR survives 20-30 deg.
- MP-SR fails beyond ~5-8 deg, because the other object is 17-31 cm from the anchor.
- Only Cup_In_Dish_Rack's prior (1.9-2.7 deg LOO) is tight enough for MP-SR; Water_Can's 6-8 deg spread is not.
- Eval-order proxies (`s17_proxy_tilt.*`):
  - ev10 (ep 11 with the static blue cup in slot 0): random already 0.70/0.32/0.17; |d| <= 20 gives >= 0.89. The stacked
    beige cup ends on the anchor's axis.
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
Constant tilt error of the slot-0 object, mean of 8 azimuths, AUC (2-object eps / 1-object eps):

| tilt error | 2-object eps | 1-object eps |
|---|---|---|
| 1 deg | 1.000 | 1.000 |
| 3 deg | 0.988 | 0.984 |
| 5 deg | 0.952 | 0.957 |
| 8 deg | 0.888 | 0.893 |

- Snapping the anchor to its resting face (~1 deg residual) is worth +0.01 / +0.05 / +0.11 AUC when vision tilt error
  is 3 / 5 / 8 deg.

### 6.2 Rest snap of all on-table static segments (z + tilt)  [V] `s20_rest_snap.py` -> `s20_aggregate.out`
All 20 public eps, 4 seeds. Snap residual z 1 mm, tilt 1 deg [E].

| noise | vision AUC / MP-SR / RPE / MPPE | with prior | dAUC per ep (min / median / max) |
|---|---|---|---|
| 0.5 cm / 2 deg | 0.947 / 0.99 / 0.79 / 1.14 | 0.964 / 1.00 / 0.71 / 0.98 | -0.001 / +0.014 / +0.038 |
| 1 cm / 4 deg | 0.818 / 0.78 / 1.58 / 2.28 | 0.862 / 0.78 / 1.40 / 1.94 | -0.001 / +0.035 / +0.088 |
| 2 cm / 8 deg | 0.562 / 0.13 / 3.15 / 4.56 | 0.624 / 0.28 / 2.80 / 3.86 | +0.004 / +0.058 / +0.136 |

- Never harmful. Needs no W.

### 6.3 Final-placement priors  [V] `s18_endplace.py`, `s19_endsnap_score.py` -> `s18_endplace.out`, `s19_summary.out`
- Consistent across public takes:
  - lid on pot: 0.2 cm translation, 1.1 deg axis, spin free;
  - plank cross-joint: 0.3 cm, 3.8 deg (full 6-DoF).
- World end yaw (needs W): Water_Can cup -88.1 / -89.9 (tilt 1.1); Pan_Solo pot -4.5..0.9 (rms 2.0).
- NOT consistent: cup in rack (15 cm apart, different slot) and pot in rack (21 cm, different face); pitcher pour pose.
- Score value of snapping the placed segment (15-30 % of frames):
  - +0.01..+0.04 AUC at 1-3 cm / 5-15 deg vision error;
  - RPE 0.5-0.9 -> 0.06 cm;
  - SP-SR and MP-SR unchanged.
- [H] The larger value may be physical: a seated lid or interlocked planks in the reference could matter for the
  FlashCHORD policy. Untested.

## 7. Other ambiguities

- Plank identity (ev25) [V]: wooden_piece_1/_2 scans are geometrically identical (Chamfer 2.5-2.6 mm under every flip vs
  a 2.0 mm floor). Combined with two-fold symmetry, the W-free bearing rule cannot separate "swap" from "flip 180".
  A swapped identity anchors on the wrong plank, which starts 28-31 cm away.
  Resolvers:
  - (a) side rule, piece_2 at +y of piece_1 (bearing 92.5 / 90.7). Needs W, which is now available: margin ~88 deg [E].
  - (b) motion order: piece_1 moves first (f22 vs f128 in ep 23; f12 vs f115 in ep 24).
  - (c) marker layout.
  - (d) [H, weak] texture: piece_2's up face is paler (HSV sat 0.41 vs 0.52, `s29_plank_colour.out`). Table lighting
    varies left/right, so this cue is unreliable alone.
- Roles (who moves) [V]:
  - Cup_Stack: beige moves onto a static blue cup.
  - Rack tasks: rack static.
  - Water_Can: pitcher moves first.
  - Pot_with_lid: lid first, pot later.
  - Dust_Brush: pan first.
  These are useful as identity and consistency checks.
- Rack near-two-fold [V]: resolved W-free in ev14 (brg 90.2 +- 23), ev28 (31.9 +- 27) and ev30 (slot-1 brg -0.4). With W,
  every rack branch (including ev15/16) is decided by abs ~91 with margin ~88 deg.
- ev20 caveat [V, viewing]: the slot-0 cup is already lifted in the left hand at frame 0, so the resting-start yaw prior
  is only approximate for its spin [H]. Validate on the ev20 video with marker vision before trusting it for MP-SR.

## 8. Estimating W on eval episodes (Stage C)

### 8.1 Definition
Take our world as gravity-aligned (table plane), with x = the frame-0 optical axis projected on the table, z up and
y = z x x.
- W_e = mocap yaw of that x axis (the "camera heading" psi).
- A mocap-world yaw prior y_m maps to our frame as y_ours = y_m - W_e.
- A bearing or long-axis direction measured in our frame maps the other way.
- Equivalently: W_e is the camera heading psi_e in the mocap world.

### 8.2 What the frames show  [V] viewing frame 0 of public 0/11/12/13/21/22/23/26/31 and eval 10/14/15/16/20/25/28/30
- The table is a small round wooden top, so there is no table-edge cue.
- Fixed room features are visible in every frame 0: black truss straight ahead, yellow/black hazard tape and blue tape on
  the floor, floor arrows, a box and cages.
- The seat and head pose are nearly identical across episodes. s7 gives camera heading changes of -3..+4.8 deg vs ep 12
  from background features.
- Image right = mocap +y (pitcher right of cup; beige right of blue; rack tower on the left with the long axis
  left-right).
- Eval staging matches the twins, including the twin-less rack episodes 15/16.

### 8.3 Method R: GT-silhouette camera fits on public frames + room registration (primary)  [V]
1. `s23_mask.py`: object colour mask. `s24_campose.py`: grid search plus Nelder-Mead over the 6-DoF camera in the mocap
   world. GT-posed scan point splats are scored by IoU against the mask components they touch; dark pixels are
   don't-care, and off-image model area is penalised.
2. `s25_refine.py`: GrabCut mask seeded by the rendering (2 rounds), followed by a heading profile (psi fixed at +-2 and
   +-4, the other 5 DoF re-fit).

   Flipped-cx K, psi / IoU:

   | ep | psi | IoU | note |
   |---|---|---|---|
   | 12 | 177.8 | 0.95 | profile sharp (heading pinned to ~1-2 deg) |
   | 13 | 180.7 | 0.97 | profile sharp |
   | 0 | 181.4 | 0.96 | profile sharp |
   | 21 | 175.1 | 0.89 | profile borderline |
   | 22 | 175.7 | 0.88 | profile flat (heading vs lateral-shift degeneracy) |
   | 26 | 180.9 | 0.91 | profile flat |
   | 31 | 174.8 | 0.87 | profile flat |

   Overlays: `cfr/ref_flipped_<ep>.png`, `cfr/m_ref.png`.

   The first-pass colour mask failed on ep 11 (two spin-symmetric cups), 18 and 39 (yellow pan), 41 (single pot, floor
   glare) and 23 (planks on wood); these were not used.
3. `s26_transfer.py`: SIFT on the top 55 % of frame 0 (room background), pairwise pure-rotation RANSAC. Then
   R_wc,q = R_wc,p R_pq^T, and the heading is read from the optical axis.
4. Validation (`s27_transfer_stats.py`) [V]: leave-one-out (predict q from the OTHER fitted refs, compare with q's own fit).
   - Refs {12,13,21,0}, flipped K: residuals +0.9 / -0.7 / +0.5 / -0.4 -> rms 0.65 deg. Prediction spread across refs
     0.45-0.67 deg for every other frame. `s27_transfer_stats_flipped_best4.out`
   - Same refs, native K (as given): -0.6 / -1.2 / +0.9 / +1.7 -> rms 1.18. Spread 0.8-1.75.
     `s27_transfer_stats_native_best4.out`
   - All 6 refs: the two outliers are exactly the flat-profile fits (22: fit 175.7 vs room 180.6; 26: 180.9 vs 178.0).
     With psi fixed at the room value (`s28_fixedpsi.py` -> `s28_fixedpsi_flipped.json`), IoU is 0.8724 vs 0.8726 (22,
     indistinguishable), 0.9212 vs 0.9075 (26, room value BETTER) and 0.8835 vs 0.8824 (31). All 7 fits are therefore
     consistent with one room-fixed world.
   - Caveat: the {12,13,21,0} reference set was chosen after seeing residuals (21 was borderline by its profile).
   - Gravity (`s27_gravity_loo_flipped.out`): roll transfers to +-1 deg, but pitch only to 2-5 deg (silhouettes pin pitch
     poorly). Use our own table plane for gravity.
5. Conclusion [V]: the mocap world is fixed in the room to <~1 deg, and room registration transfers the mocap heading to
   any frame 0 with [E] ~1 deg error. This holds when the same camera model is used for the fits, the registration and
   our pipeline.

### 8.4 Alternatives for W, compared

| method | coverage of eval | error of W | notes |
|---|---|---|---|
| R: room registration to fitted public frames (8.3) | all 20 | 0.65 (flipped K) / 1.2 (native) deg LOO [V] | independent of object vision; needs the same K as the fits |
| O: asymmetric/branch-resolved co-object with a world prior (W = prior(B) - yaw_ours(B)) | ev1 pot (0.3), ev14/28/30 rack (0.8-2.6 mod 180), ev20 pitcher (1.5), ev25 planks (3.1 mod 180), ev19 pan (1 twin) | twin LOO spread [V] plus B's vision yaw error [E 2-5] | none for ev10 (two C cups) or ev15/16 (W mod 180 only); task-specific |
| S: staging line (bearing of two separated objects, sign from side rule) | two-object eps with separated objects | 2.4 deg sd across 6 tasks plus position noise (1 cm at 17 cm = 3.4 deg) [V/E] | W mod 180 only; fails for Cup_In_Dish_Rack and Pan_In_Dishrack ep 27 |
| P: population prior (same seat, no registration) | all | sd 2.5-2.9 deg around 178.6 (flipped) / 180.5 (native) [V] | enough for every two-fold branch and for ev10; not for MP-SR-grade cup spin |

Recommendation: use R as the primary source of W. Use O as a per-episode consistency check: flag
|prior(B) - (yaw_ours(B) + W)| > ~8 deg as either a vision error on B or an unusual take. Keep P as the fallback when
registration has too few inliers (minimum seen: 145-167 inliers on ev35 / public 41; all eval frames registered).

### 8.5 Camera-model caveat (K principal point)
- Note 15 verified the calibration AS GIVEN for the stored mono pair. For the colour camera, the flipped-cx/cy variant
  gives slightly higher silhouette IoU on all 4 refs (+0.001..+0.013) and a tighter LOO (0.65 vs 1.18 deg).
  [E, weak] The colour intrinsics may describe the raw (unrotated) sensor.
- The two variants differ by a nearly constant ~1.9 deg in heading (the eval W tables below differ by 1.7-2.8).
- Whichever K our pipeline uses, take W from the table fitted with the SAME K. Ideally the rig owner tests cam_a K
  directly (colour<->mono epipolar error with both variants).

### 8.6 W for the 20 eval episodes  [V] `s27_stats_flipped_best4.json`, `s27_stats_native_best4.json`
Camera heading of frame 0 in the mocap world (deg), median over refs {12,13,21,0}, flipped K / native K:

| ev | flipped | native | ev | flipped | native | ev | flipped | native | ev | flipped | native |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 182.5 | 184.2 | 10 | 178.5 | 180.4 | 20 | 176.4 | 178.6 | 33 | 174.9 | 177.1 |
| 3 | 177.6 | 179.5 | 14 | 180.2 | 181.9 | 25 | 180.4 | 182.2 | 35 | 171.4 | 174.1 |
| 5 | 177.3 | 179.3 | 15 | 178.7 | 180.8 | 28 | 177.2 | 179.4 | 36 | 175.9 | 178.1 |
| 6 | 176.6 | 178.5 | 16 | 181.1 | 182.8 | 30 | 180.8 | 183.0 | 37 | 173.7 | 176.1 |
| 8 | 181.8 | 183.8 | 19 | 177.3 | 179.4 | 32 | 182.5 | 184.6 | 38 | 174.6 | 177.2 |

Use: abs prior in our frame = y_m - W_e (section 8.1). Example (ev10, flipped K): the blue cup's spin prior is
41.1 - 178.5 = -137.4 deg relative to the projected optical axis. [E] W error ~1 deg, which is negligible against the
twin spreads (1.4-8 deg).

### 8.7 Falsification tests run / remaining
- Run [V]: the world-room link would have been unusable if the LOO heading residual exceeded ~5 deg. Measured 0.65-1.18
  rms; the max outliers are explained by flat profiles.
- Supporting [V, weaker]: eps 26 (task index 10) and 31 (11) fit as well or better at the room-predicted heading (s28),
  so the link holds at least through task index 11.
- Remaining:
  - only 4 well-conditioned public references; all of them from task indices 0-8;
  - eval sessions with task indices 12-13 (ev32-37) rely on the same room/seat assumption (their registrations have
    167-569 inliers and the same 0.5-1.75 deg ref spread);
  - a direct check would be a well-conditioned GT fit on a late public episode (39-45: single objects, poorly
    conditioned here).

## 9. Recommendations (implementation order)
1. Room-memory W (8.3, 8.6): store the 4 reference frames and their fitted R_wc (both K variants). At inference, register
   eval frame 0 to them (SIFT top 55 %, pure-rotation RANSAC, 0.35 deg threshold) and take the median heading.
   Cost: < 1 s per episode.
2. Slot-0 anchor yaw for symmetric anchors:
   - ev14: rel to rack (cross-check abs);
   - ev20: brg -164 or abs -68.8 via W (cup lifted at frame 0: verify with markers);
   - ev10: abs 41.1 via W (or brg -49);
   - two-fold branches (15, 16, 19, 25, 28, 30): abs world yaw via W;
   - ev25 plank identity: side rule via W plus motion order.
3. Marker-based spin for ev8/32/33, and as an override wherever markers are clearly visible (note 12: ~2 deg on a public
   frame).
4. Rest snap (stable face + own table plane) on static segments, plus anchor tilt snap; small, never harmful.
5. End-placement snaps (lid on pot, plank interlock) mainly for physical consistency of the reference [H].
6. Keep inference automatic: twin selection by object set + task_index bracketing, no per-episode labels. Eval GT is
   never read.

## 10. Limitations
- At most two public takes per task, so every LOO is one comparison. Single-twin priors (ev10, ev19, ev30) are
  unvalidated.
- AUC uses sampled scan points [E]. All score experiments are kinematic; physical (FlashCHORD) effects are untested.
- W reference fits rely on 4 public frames and a colour-mask/GrabCut silhouette fit. Heading is degenerate with lateral
  shift for symmetric or single objects. The K principal-point convention for the colour camera is unresolved (~1.9 deg).
- ev20's anchor is in hand at frame 0. Unknown-task episodes (3, 5, 6, 8, 15, 16, 32, 33, 35-37) have no task prior
  except cross-task object staging.

## 11. Artifacts (all in `/Users/aebatirel/Documents/Code/v2d-research/work/11/`)

| stage | scripts | outputs |
|---|---|---|
| A | `c11.py` (loaders, yaw/tilt), `s1_poses.py`, `s2_relative.py`, `s3_loo.py`, `s4_markers.py`, `s5_symmetry.py`, `s6_twofold.py`, `s7_roomreg.py`, `s8_rest.py`, `s9_stableprior.py`, `s10_twins.py`, `s11_consistency.py`, `s12_worldyaw.py`, `s13_priortable.py`, `s14_layout.py`, `s15_loo_brg.py` | `.json`/`.out`/`.csv` with the same stem; `tex/*.png` |
| B | `sc11.py` (official `score()` wrapper), `s16_anchor_loo.py`, `s17_proxy_tilt.py`, `s18_endplace.py`, `s19_endsnap_score.py`, `s20_rest_snap.py`, `s21_anchor_noise.py` | `.json`/`.out` with the same stem, plus `*_aggregate.out` / `*_summary.out` |
| C | `s22_dump.py` (frame 0 dumps), `s23_mask.py`, `s24_campose.py`, `s24_view.py`, `s25_refine.py`, `s26_transfer.py`, `s27_transfer_stats.py`, `s28_fixedpsi.py` | `s24_campose_{flipped,native}.json`, `s25_refine_{flipped,native}.json`, `s26_transfer_{flipped,native}_s25_refine_*.json`, `s27_*.out`, `s27_stats_{flipped,native}_best4.json`, `s28_fixedpsi_flipped.json`, `s29_plank_colour.out`, frames/overlays in `cfr/`, logs in `logs/` |

Example commands:
- `python s25_refine.py flipped 12 13 21 0`
- `python s26_transfer.py flipped s25_refine_flipped.json`
- `python s27_transfer_stats.py s26_transfer_flipped_s25_refine_flipped.json s25_refine_flipped.json 12,13,21,0`

Downloads: none in stages B/C. A stale `public/.../ego_cam_b/episode_000031.mp4.part.56507` from the stage A outage is
left untouched.

## 12. Stage B retry addendum (2026-10-06, workflow "Try again")
- Resume state [V]: stage B outputs from 2026-10-05 are complete and consolidated above (sections 5-6; raw log
  `work/11/notes_stageAB_C_log_backup.md` lines 211-372). Stage C material (section 8) was also produced by that earlier
  run; it is left as is and is not redone here.
- This retry does only stage B work: (1) reproducibility check of the s16 anchor LOO with the unmodified kit `score()`,
  (2) an extra W = +-1 deg row (the W error measured in stage C) and +-5 deg, (3) split of the rest-snap gain into table
  height (z only) vs tilt only. Findings are appended below as they arrive.

### 12.1 Reproducibility and finer W grid for the cup anchors  [V] `s30_anchor_wgrid.py` -> `s30_anchor_wgrid.{out,json}`
- Re-running the s16 model with the unmodified kit `score()` reproduces the stored abs W0 / W+-3 / W+-10 rows of eps
  12, 13, 21 and 22, and the ep-12 random-spin baseline, exactly (max abs difference 0.0 over all 5 metrics).
- Cups 12/13/21/22, abs (world) prior from the twin, mean over the 4 LOO eps (AUC / SP-SR / MP-SR / RPE cm / MPPE cm):

  | W error | AUC | SP-SR | MP-SR | RPE | MPPE | dAUC vs random (0.277) |
  |---|---|---|---|---|---|---|
  | 0 | 0.871 | 1.0 | 0.50 | 2.31 | 1.55 | +0.59 |
  | +-1 | 0.884 | 1.0 | 0.50 | 2.31 | 1.55 | +0.61 |
  | +-3 | 0.858 | 1.0 | 0.63 | 2.35 | 1.59 | +0.58 |
  | +-5 | 0.846 | 1.0 | 0.75 | 2.59 | 1.87 | +0.57 |
  | +-10 | 0.734 | 1.0 | 0.50 | 3.71 | 2.84 | +0.46 |

  Random spin: 0.277 / 0.16 / 0.04 / 27.1 / 20.7.
- [V] Reading: up to W = +-5 deg the cost is within the noise of a 4-episode LOO. AUC moves by at most +-0.03 and is
  not monotone, because W adds to a prior error of 2.7-8 deg and one sign of W partly cancels it. RPE and MPPE are
  nearly linear in |spin error|, so the +-1 rows equal W0. The prior's own twin spread (2.7 deg in Cup_In_Dish_Rack,
  8 deg in Water_Can) is the limiting term, not W. The stage C W error (0.65-1.2 deg rms, section 8.3) falls in the
  "W perfect" regime.
- [V] MP-SR rises with W in eps 21/22 (0 -> 0.5) for the same reason: one sign brings the 8 deg error under the
  ~5 deg MP-SR budget. This is not a real benefit of W error.

### 12.2 Rest snap split: table height (z) vs stable face (tilt)  [V] `s31_rest_split.py` -> `s31_rest_split.{out,json}`
Same noise model, seeds and RNG stream as s20 (section 6.2); the "both" mode reproduces s20 exactly (max diff 0.0).
All 20 public eps, 4 seeds; mean AUC / SP-SR / MP-SR / RPE cm / MPPE cm and per-episode dAUC (min / median / max).

| noise | mode | AUC | SP-SR | MP-SR | RPE | MPPE | dAUC per ep |
|---|---|---|---|---|---|---|---|
| 1 cm / 4 deg | vision | 0.818 | 1.00 | 0.78 | 1.58 | 2.28 | - |
| | z only (table height) | 0.831 | 1.00 | 0.78 | 1.45 | 2.17 | -0.001 / +0.011 / +0.035 |
| | tilt only (stable face) | 0.849 | 1.00 | 0.78 | 1.53 | 2.06 | -0.002 / +0.024 / +0.079 |
| | both | 0.862 | 1.00 | 0.78 | 1.40 | 1.94 | -0.001 / +0.035 / +0.088 |
| 2 cm / 8 deg | vision | 0.562 | 0.98 | 0.13 | 3.15 | 4.56 | - |
| | z only | 0.584 | 0.99 | 0.21 | 2.91 | 4.35 | -0.001 / +0.022 / +0.050 |
| | tilt only | 0.597 | 1.00 | 0.15 | 3.05 | 4.10 | -0.005 / +0.033 / +0.093 |
| | both | 0.624 | 1.00 | 0.28 | 2.80 | 3.86 | +0.004 / +0.058 / +0.136 |

- [V] The two parts are roughly additive (1 cm: +0.013 z, +0.031 tilt, +0.044 both). The tilt part gives about 2/3 of the
  AUC gain and most of the MPPE gain. The table-height part gives most of the RPE gain and, at 2 cm noise, most of the
  MP-SR gain (0.13 -> 0.21 of 0.28).
- [V] Neither part is harmful beyond -0.005 AUC on any episode. Both need only our own table plane plus the per-object
  stable-face table (s8), not W.
- [E] Caveat: the noise model is isotropic. A stereo pipeline whose depth error lies mostly along the oblique view ray
  puts a larger share of its error into z, so the table-height share would be larger than measured here.

### 12.3 Stage B retry summary
- [V] The stage B anchor results (section 5) and rest-snap results (section 6.2) reproduce exactly with the kit `score()`.
- [V] Symmetric slot-0 cup anchor, task prior vs random spin (LOO, 4 eps): AUC 0.277 -> 0.871 / 0.884 / 0.858 / 0.846 /
  0.734 for W = 0 / +-1 / +-3 / +-5 / +-10 deg; SP-SR 0.16 -> 1.0 at every W; RPE 27 -> 2.3-3.7 cm; MPPE 21 -> 1.6-2.8 cm.
  MP-SR needs the prior spread itself to be <= ~5 deg (only Cup_In_Dish_Rack).
- [V] Two-fold anchors are unaffected by any W <= 10 deg (branch margins 70-89 deg; section 5.1).
- [V] Table height (z) is worth about 1/3 and stable-face tilt about 2/3 of the rest-snap AUC gain; table height carries most
  of the RPE and MP-SR gain.
- [V, unchanged] Cup-in-rack and pot-in-rack end poses are not consistent across public takes (15-21 cm apart), so no
  placement prior exists for them (section 6.3). A rack-slot snap would need the rack's slot geometry, not room memory [H].
- New artifacts in `work/11/`: `s30_anchor_wgrid.{py,out,json}`, `s31_rest_split.{py,out,json}`. No downloads.

## 13. Stage C retry addendum (2026-10-06, workflow "Try again")
- Resume state [V]: stage C (section 8) was completed by the 2026-10-05 run (scripts s22-s29, raw log lines 373-408 of
  `work/11/notes_stageAB_C_log_backup.md`). This retry re-checks it and attacks the open items: (1) sensitivity of the eval
  W table to the reference-set choice, (2) the colour-camera K principal-point convention (~1.9 deg in W), then rewrites
  this document. Findings are appended here as they arrive.

### 13.1 Reference-set sensitivity of the eval W table  [V] `s32_refset.py` -> `s32_refset_{flipped,native}.{out,json}`
- Addresses the caveat that the {12,13,21,0} reference set was chosen after seeing residuals. Three sets compared:
  sharp3 = {12,13,0}, chosen a priori by a sharp heading profile; best4 = {12,13,21,0}; all fitted refs (7 flipped / 6 native).
- LOO rms (deg): sharp3 0.83 (flipped) / 1.55 (native); best4 0.65 / 1.18; all refs 2.32 / 2.85. The all-refs LOO is
  inflated by the flat-profile fits 22 (+5.2) and 26 (-2.9). Those are errors of the GT fits themselves, not of the
  registration (section 8.3, s28).
- Eval W, median over refs: sharp3 - best4 = +0.26 +- 0.06 deg (flipped, max 0.46) and +0.35 +- 0.15 (native, max 0.72).
  all - best4 = +0.23 +- 0.13 (flipped, max 0.46) and 0.00 (native; the two extra refs bracket the median).
- [V] Conclusion: the eval W table (8.6) is robust to the reference choice to <= 0.5 deg (flipped) / <= 0.7 deg (native),
  because the median over refs discards the flat-profile outliers. The selection caveat costs at most ~0.3 deg of bias.

### 13.2 Colour-camera K convention: epipolar test cam_a <-> cam_b  [V, in progress] `s33_kcheck.py` -> `s33_kcheck_b_*.json`
- Method: same ego device, calibrated `extrinsics_to_stereo_left` (X_b = R X_a + t, t_x = -3.74 cm, i.e. b right of a in
  the upright image). SIFT matches (cam_a at half res), model-free fundamental RANSAC inliers, then the Sampson error under
  the calibrated E for K variants n = as given, f = cx,cy flipped by 180 deg (+ odd distortion terms negated), and R as
  given vs conjugated by Rz180. Errors are px at f = 1150 (cam_a full res). The free relative rotation (essential RANSAC)
  is also compared with the calibrated R.
- Ep 12, frames 0/60/120 (preliminary): cam_a AS GIVEN wins every frame. Median |Sampson|: a_n 2.4 / 2.1-10 / 4.9 px vs
  a_f 14-23 px. Free minus calibrated rotation about y: a_n 0.25-0.6 deg; a_f 1.3-3.0 deg. The conjugated R is 25-57 px
  in every combination, so the extrinsics are already expressed in the upright (rotated) image frame. The cam_b variant
  is not decided by this test.
- [E, preliminary] This CONTRADICTS the weak hypothesis of 8.5. The silhouette IoU and LOO tightness favoured flipped,
  but the epipolar geometry favours the colour K as given. Replicating on more episodes next.
- Replication [V] `s33_kcheck_b_multi.out`, `s33_kcheck_b_0-13-21-22-26-27-11.json`: eps 0, 11, 13, 21, 22 and 26, frames
  0/40/100/160/220. Ep 27 was skipped because its cam_a clip is not local, and ep 21 has only 186 frames. With ep 12 that
  makes 26 frame pairs in 7 episodes.
  | cam_a / cam_b K | median abs Sampson (px @ f 1150), 23 pairs | p25-p75 | free - calibrated rotation, median (x, y, z) deg |
  |---|---|---|---|
  | as given / as given | 4.5 | 3.1-6.5 | (-0.10, +0.26, -0.27) |
  | as given / flipped | 6.8 | 4.9-10.8 | (+0.44, -0.42, -0.22) |
  | flipped / as given | 13.7 | 12.2-16.9 | (+0.77, +2.33, -0.22) |
  | flipped / flipped | 20.4 | 18.6-22.1 | (+1.23, +1.88, -0.12) |
  cam_a as given beats cam_a flipped on 22 of 23 frame pairs for both cam_b variants. The R conjugated by Rz180 is worse
  in every case (24-48 px).
- [V] Conclusion: the colour K AS GIVEN is consistent with the calibrated stereo extrinsic. The flipped principal point
  needs a ~2.1 deg rotation about the camera y axis and ~0.9 deg about x, which matches its 37 px / 16 px cx/cy shift at
  f 1150. Images, extrinsics and intrinsics are all expressed in the upright frame. The weak preference for flipped in
  8.5 (IoU +0.001..+0.013, LOO 0.65 vs 1.18 on n = 4) was a fit artefact or noise: the silhouette fit trades principal
  point against lateral shift (8.3).
- [V] Consequence for W: use the NATIVE (as-given K) W table of 8.6 and the native reference fits. The native LOO is
  1.18 deg rms with best4 and 1.55 with the a-priori sharp3 set. The flipped table carries a ~+2 deg bias for a pipeline
  that uses the calibration as given. Per s30, a 2 deg error costs <= ~0.02 AUC on the cup anchors, so the earlier
  ambiguity was harmless, but the native table is now the documented choice.

### 13.3 Ready-to-use anchor priors in OUR frame (as-given K)  [V arithmetic, E transfer] `s34_prior_ours.py` -> `s34_prior_ours.{out,json}`
Our frame: z = own table normal, x = frame-0 optical axis projected on the table, y = z x x (image left). Yaw is the
heading of the `c11.HREF` body axis. For two-fold objects ('180' column) vision measures yaw mod 180; the full-circle
prior picks the branch.
| ev | object | y_mocap | W (native) | y_ours (native) | y_ours (flipped K) | sym | note |
|---|---|---|---|---|---|---|---|
| 10 | blue_cup | 41.1 | 180.35 | -139.3 | -137.4 | C | Cup_Stack, n = 1 |
| 14 | blue_cup | 64.1 | 181.94 | -117.8 | -116.1 | C | rel-to-rack -25.4 preferred |
| 14 | rack | 89.5 | 181.94 | -92.4 | -90.7 | 2 | branch |
| 15 | rack | 91.0 | 180.75 | -89.7 | -87.7 | 2 | cross-task rms 1.4 |
| 16 | rack | 91.0 | 182.79 | -91.8 | -90.1 | 2 | cross-task rms 1.4 |
| 19 | mini_sweeper | 16.3 | 179.38 | -163.1 | -161.0 | 2 | ep 18, n = 1 |
| 20 | blue_cup | -68.8 | 178.57 | +112.6 | +114.8 | C | twin diff 8; cup in hand at f0 |
| 25 | wooden_piece_1 | -177.2 | 182.20 | +0.6 | +2.4 | 2 | rms 1.5 |
| 28 | rack | 92.3 | 179.39 | -87.1 | -84.9 | 2 | rms 0.7 |
| 30 | mini_sweeper | -3.5 | 182.97 | +173.5 | +175.7 | 2 | ep 31, n = 1 |
- Sanity check [V]: the rack's HREF axis at mocap ~90 points to image right (= our -y), giving ~ -90 in our frame,
  which matches the tower-left staging seen in every rack frame 0.

### 13.4 Visual re-check and remaining W error terms
- [V] Re-viewed `cfr/m_ref.png` (public 21/22/26/31 with GT overlays) and `cfr/m_eval_f0.png` (eval 10/14/15/16/20/25/28/30):
  the round wooden table, truss straight ahead, yellow/black hazard tape, blue floor tape and floor arrows are present in
  all; pitcher right of cup, rack tower on the left. Each object carries black dome markers (marker-spin cue). Ev15/16 have
  a wooden spoon (no public data) as co-object. Background people (e.g. ep 22) are rejected by the RANSAC.
- [E] Gravity term: W is defined on our own table plane. A roll error eps of that plane about the optical axis turns the
  projected heading by ~eps * sin(pitch) (pitch 38-53 deg in s27, so 0.6-0.8 eps). Anchor yaws measured in the same
  tilted frame partly cancel this. A table plane good to 1 deg keeps this term below ~0.7 deg.
- [H] Floor tape lines (hazard and blue tape) are straight room-fixed lines. Their vanishing direction on the floor plane
  would give a registration-free heading check (offline: calibrate the tape's mocap yaw on the 4 refs). Not built; the
  SIFT registration already reaches ~1.2 deg.
