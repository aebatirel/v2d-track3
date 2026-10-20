# 11 — Placement priors and "room memory" (agent 11, 2026-10-05)

Status: Stage A complete ~12:30; Stage B (official-scorer LOO of anchor-yaw priors and room-memory priors) complete ~14:00 (see "Stage B summary" at end); stage C not started. Scripts/outputs: `/Users/aebatirel/Documents/Code/v2d-research/work/11/`.
Tags: [V] verified numerically, [E] estimate, [H] hypothesis.

## Progress log
- 10:xx Loader `c11.py`; `s1_poses.py` (per-object start/end yaw/tilt, `s1_poses.csv`); `s2_relative.py`
  (pair-relative poses); `s3_loo.py` (official scorer functions, cup-anchor spin LOO, `s3_loo.json`).
- Found: scanned textures of every object show the Vicon marker bases (black rings, white spheres) ->
  cups/lid are NOT appearance-symmetric (`tex/*.png`).

## Early findings (to be expanded)
- [V] Mocap world x,y are centred so the mean over all frames and all objects is 0 (per episode); z physical.
- [V] Rack yaw (body z long axis heading) 89.9/89.1/93.0/91.6/91.2 deg in eps 12/13/26/27/31 (3 tasks).
- [V] Cup_In_Dish_Rack: cup-vs-rack relative yaw 24.4 / 26.3 deg (1.9 deg apart) although cup position differs 13 cm.
- [V] Water_Can: pitcher-vs-cup relative yaw 102.1 / 111.6 (9.5 deg apart).
- [V] LOO with the official scorer functions (perfect tracking otherwise, 4 eps with a twin):
  random spin AUC 0.277 SP 0.16 MP 0.04 RPE 27.1 MPPE 20.7; abs prior W exact AUC 0.871 SP 1.0 MP 0.50;
  W±3 0.858/1.0/0.625; W±10 0.735/1.0/0.50; relative prior 0.861/1.0/0.50.

## Checkpoint 2 (~11:05)
- [V] Decoded MP4 frames (ffmpeg and OpenCV, no display-matrix side data) are ALREADY UPRIGHT for ego_cam_a/b/c
  (public 12/21/26/31, eval 8/10/32/35): floor at bottom, hands at bottom. Applying a further 180 deg rotation makes
  them upside down. Calibration says ego rotation_deg 180 and "left=ego_cam_c, right=ego_cam_b"; in the decoded
  frames cam_c is indeed the left camera (ORB disparity on near objects: x_b - x_c median -78 px). Which K variant
  (native cx,cy or W-1-cx,H-1-cy) applies to the decoded frames is NOT verified here -> rig owner must check.
- [V] Vicon marker bases/spheres are baked into every scan texture and visible in the videos (cups: 3-4 grey
  spheres on black bases; spoon in eval 35: two markers sticking out sideways near the neck + one at the handle end).
- [V] s4_markers.py: markers are 1.5-13 % of scan surface area; removing them rotates the cups' in-plane PCA axes by
  9-10 deg and the lid's by 7 deg and flips fragile skew signs (blue cup y, wooden_piece_2 y). [H] The organisers'
  spoon frame sign (note 07 coin flip) is likely decided by its markers -> reconstruct spoon WITH markers.
- [V] s5_symmetry.py (Chamfer of scan vs rotated scan, noise floor ~1.5 mm): cups and lid ~continuous spin symmetry;
  mini_sweeper and both wooden pieces 2-fold (spin180 1.7-2.1 mm); rack near-2-fold (15 mm at 180 vs 70 at 90);
  pot/pitcher/dust pan asymmetric.
- [V] s6_twofold.py: 180-deg error of a slot-0 anchor = AUC 0.03-0.50, SP 0, MP 0 (perfect tracking otherwise).

## Checkpoint 3 (~11:25)
- [V] s7_roomreg.py: frame 0 of 9 public + 20 eval episodes registered to public ep 12 frame 0 with a RANSAC
  pure-rotation fit on SIFT background features (top 55 % of frame): 183-1848 inliers (70-95 %). Camera heading
  about (approx.) gravity relative to ep 12: -3.0..+4.8 deg (std ~2.2); total rotation 0.4-16 deg (mostly pitch).
  Same seat, same pillar/box/tape view in every episode (public and eval).
- [V] s8_rest.py: table top z = 0.6012 m (lowest scan point over 104 on-table rests, IQR 0.6003-0.6019).
  Stable poses are tight: pot upright origin z 0.6452+-0.5 mm tilt 12.1+-0.3; rack 0.6271+-0.3 / 4.2+-0.3;
  blue cup 0.6875+-0.4 / 1.6+-0.5; pitcher 0.7382+-0.3 / 37.8+-0.2; planks flat 0.605-0.607, on edge 0.671-0.672.
- [E] s9_stableprior.py: removing z+tilt error on static on-table segments (stable-pose prior) under a
  1 cm / 4 deg per-segment error model: AUC 0.813->0.842, MP-SR 0.767->0.825, RPE 1.63->1.48, MPPE 2.34->2.07.
- [V] s10_twins.py: eval->public twins (object set + task_index bracketing). Global 'index' gaps equal eval colour
  video frame counts where no withheld episode intervenes (0->2: 335=335; 18->21: 437; 24->26: 356).
  Withheld (neither public nor eval) episodes: 4, 7, 9, 17, 29, 34.

## Checkpoint 4 (resumed after outage, ~11:40)
- Reused s1-s10 outputs (verified present). Next: direct test of mocap-world yaw constancy relative to the room
  (stereo point cloud at frame 0 registered to GT-posed scans -> camera pose in mocap per public episode, compared
  with the background room registration s7), consolidated consistency tables, 2-fold prior LOO, final placements.

## Checkpoint 5 (resumed after 2nd outage, ~12:10) -- Stage A consolidation (GT only)
Outage note: the cam_b/cam_c fetch for the stereo world-yaw test died (DNS failures, `work/11/logs/fetch_bc.log`;
stale `public/.../ego_cam_b/episode_000031.mp4.part.56507` left untouched). Public cam_c exists only for ep 12, so the
video-based test is deferred to stage B; Stage A uses GT-only tests below.

### A1. Start/end pose consistency per (task, object)  [V] `s11_consistency.py` -> `s11_consistency.{out,json}`
Yaw = heading of a fixed horizontal body axis (HREF in `c11.py`) about world z; tilt = angle of the rest-up body axis
from world +z; rms = circular rms about the circular mean.

| task (public eps) | object | start yaw (deg) | start rms | end yaw | end rms | notes |
|---|---|---|---|---|---|---|
| Cup_In_Dish_Rack (12,13) | blue_cup | 65.5, 62.8 | 1.4 | 13.1, -8.5 | 10.8 | upright start, flipped end (tilt 179/162) |
| Cup_In_Dish_Rack | plastic_dish_rack | 89.9, 89.1 | 0.4 | 89.5, 89.1 | 0.2 | static |
| Water_Can_Blue_Cup (21,22) | blue_cup | -64.8, -72.8 | 4.0 | -88.1, -89.9 | 0.9 | |
| Water_Can_Blue_Cup | water_pitcher | 37.3, 38.8 | 0.8 | 19.5, 53.9 | 17.2 | tilt 37.8 at rest (handle side) |
| Pan_In_Dishrack (26,27) | plastic_dish_rack | 93.0, 91.6 | 0.7 | 92.9, 91.0 | 0.9 | static |
| Pan_In_Dishrack | white_pot | 43.7 (upside down), 91.4 | 23.9 | 28.7, 33.6 (one upside down) | 2.4 | rest face differs between eps |
| Brush_Dishrack (31) | plastic_dish_rack | 91.2 | - | 92.1 | - | |
| Brush_Dishrack | mini_sweeper | -3.5 | - | -2.9 | - | |
| Dust_Brush (18) | mini_dust_pan / mini_sweeper | -22.9 / 16.3 | - | -20.8 / 12.0 | - | |
| Dustpan_Solo (39,40) | mini_dust_pan | -16.5, -2.8 | 6.8 | 10.9, -0.6 | 5.8 | |
| Pot_with_lid (0,2) | white_pot | 4.9, 4.6 | 0.2 | 6.6, 6.1 | 0.2 | |
| Pot_with_lid | white_pot_lid | -127.0, -161.5 | 17.2 | -127.7, -157.0 | 14.6 | lid spin NOT consistent |
| Planter_Stand (23,24) | wooden_piece_1 | -175.7, -178.8 | 1.6 | 147.8, 132.7 (on edge) | 7.6 | |
| Planter_Stand | wooden_piece_2 | -179.3, 178.0 | 1.4 | -121.7, -136.4 (on edge) | 7.4 | |
| Pan_Solo (41-45) | white_pot | 2.4, 95.6, 63.6 (upside down), 0.9, -4.5 | 40.6 | -2.1, 0.3, 0.9, -4.5, 0.3 | 2.0 | start varies, END tight |
| Cup_Stack (11) | beige_cup / blue_cup | 179.2 / 41.1 | - | -158.5 / 43.1 | - | single twin |

Same object across tasks (start, same rest face): rack 89.9/89.1/93.0/91.6/91.2 (3 tasks, rms 1.4) [V];
blue cup 41.1 / 65.5, 62.8 / -64.8, -72.8 (task-specific, rms 62.5 across tasks) [V]; pot upright start 4.9/4.6 (Pot_with_lid)
and 2.4/0.9/-4.5 (3 of 5 Pan_Solo) but 91.4 (ep 27) and 95.6 (ep 42) [V] -> pot start yaw is bimodal {~0, ~90}.
Tilt is set by the stable rest face and is tight (s8: <=0.5 deg sd), so the prior content is in yaw and position.
Takeaway [V]: the start yaw is consistent to <=4 deg rms for every (task, object) pair with >=2 public eps EXCEPT the
lid (17 deg), dust pan (7 deg), and the pot when its rest face/handle direction changes. End yaws are tight only for
static objects, Pan_Solo pot (2 deg), and Water_Can cup (0.9 deg).

### A2. Relative placement (pair frame) [V] `s2_relative.py` -> `s2_relative.out`
Start-frame offset of object B from slot-0 object A, in world axes (cm) and relative yaw (yawB - yawA):
- Cup_In_Dish_Rack: rack at (-16.7,-6.9) / (-15.3,+6.8) from cup; rel-yaw 24.4 / 26.3 (1.9 apart); horiz distance
  18.0 vs 16.7 cm. The cup sits ~16 cm on the -x side of the rack, lateral offset varies 13.7 cm.
- Water_Can: pitcher at (-3.5,+32.3) / (-2.1,+28.5); rel-yaw 102.1 / 111.6 (9.5 apart). Bearing 96.2 / 94.2 deg.
- Planter_Stand: piece 2 at (-1.2,+27.9) / (-0.4,+30.6) from piece 1; rel-yaw -3.6 / -3.2; bearing 92.5 / 90.7.
- Pot_with_lid: lid on pot (|d| 5.6-5.7 cm along pot body x) in both; rel-yaw -131.9 / -166.1 (34 apart).
- Pan_In_Dishrack: rel-rot differs by 180 (pot rest face differs); positions differ 18 cm -> no usable pair prior.
- Single-twin tasks: Cup_Stack beige->blue (0.0,-17.4), rel-yaw -138.0; Dust_Brush pan->sweeper (-0.4,+22.1),
  rel-yaw 39.2; Brush_Dishrack sweeper->rack (+0.3,-10.7), rel-yaw 94.7.
Pattern [V]: in 5 of 6 two-object tasks with separated objects the second object lies along world +-y from the first
(bearings 90-96 or ~-90 deg; Water_Can, Planter, Dust_Brush, Cup_Stack, Brush_Dishrack); Cup_In_Dish_Rack is the
exception (rack along -x from the cup, bearing -158 / +156).

### A3. Is the mocap world yaw constant across episodes? GT-only test [V] `s12_worldyaw.py` -> `s12_worldyaw.{out,json}`
Logic: a per-episode re-rotation w_e of the mocap world would shift EVERY start yaw and every inter-object bearing of
episode e by the same w_e. Per-twin-pair deviations from the task mean (deg; the pair is +-d):
- Pot_with_lid 0/2: pot 0.1 (lid 17.3 = placement). -> |w_0 - w_2| <= ~0.2 deg.
- Cup_In_Dish_Rack 12/13: rack 0.4, cup 1.3 (bearing 23 = placement). -> |w_12 - w_13| <= ~0.8.
- Pan_In_Dishrack 26/27: rack 0.7. Brush_Dishrack 31 rack 91.2. Rack across 3 tasks: 89.9, 89.1, 93.0, 91.6, 91.2 (rms 1.4).
- Planter 23/24: piece1 1.5, piece2 1.3, bearing 0.9 -> the only pair whose quantities shift TOGETHER (common ~1.2,
  sd 0.2): either a ~2.4 deg world rotation between 23 and 24 or the two planks staged as a unit.
- Water_Can 21/22: cup 4.0, bearing 1.0 (not common -> placement noise). Pan_Solo end pot: rms 2.0 over 5 eps.
Verdict [V]: world z is gravity in every episode (rest tilts identical to <=0.5 deg sd, s8) and the world yaw is the
same across all public episodes and sessions to within ~1-2 deg (bounded by static-object agreement; rack spans task
indices 5, 10, 11). The translation origin is NOT constant: x,y are re-centred per episode on the all-frame, all-object
mean (rack static xy differs by up to 7 cm between eps), which is irrelevant to the slot-0-aligned scorer.
Not tested in Stage A: whether this world is fixed relative to the ROOM/camera (needs stereo or PnP on public video;
s7 already shows the same seat and camera heading -3.0..+4.8 deg vs ep 12). That link is only needed for priors that are
absolute in the world (ev 10, ev 15/16, and any no-twin cup); pairwise priors below are world-free.

### A4. Automatic eval -> public twin map and slot-0 prior table [V] `s10_twins.py`, `s13_priortable.py` -> `s13_priortable.{out,json}`
Mapping rule (automatic, no labels): same object multiset AND task_index bracketed by the nearest public episodes
(public task_index is monotone in episode_index; global parquet `index` gaps equal eval frame counts, so eval episodes
are interleaved in recording order). Public `notes` field is the within-task take number (`Ep_k`), giving take bounds.
Priors for the slot-0 object A with co-object B, from twins: abs = world yaw of A (needs world link); rel = yawA - yawB
(world-free, needs B's yaw); brg = yawA - bearing(A->B) (world-free and B-frame-free; only positions). Values are
mean / rms over twins and |twin1 - twin2| (LOO error proxy). Sym: C = continuous spin, 2 = two-fold, A = asymmetric,
M = mirror/roll-sign (spoon). Effect sizes from s3/s6 (official scorer functions, perfect tracking otherwise).

| eval | task (twins, takes) | slot order vs twin | slot 0 (sym) | best available slot-0 prior | twin spread / pair diff | note |
|---|---|---|---|---|---|---|
| 1 | Pot_with_lid (0,2; Ep_0,Ep_2 -> ev1 = Ep_1) | same | white_pot (A) | none needed | pot abs 4.7 / 0.3 | slot-1 lid (C): rel 149.0, rms 17.1, diff 34 -> weak |
| 3,5,6 | unknown, task_index 1-3 (no twin) | - | white_pot (A) | none needed | pot upright start yaw is bimodal {~0, ~90} across tasks | spoon (M): no public data |
| 8 | unknown, task_index 1-3 (no twin) | - | beige_cup (C) | NONE from GT | - | anchor spin must come from vision (Vicon markers in texture) |
| 10 | Cup_Stack (11; Ep_3 -> ev10 Ep_0-2) | REVERSED | blue_cup (C) | brg -49.0 (1 twin) or abs 41.1 (needs world link) | n=1, spread unknown [E 3-22] | both objects C: rel unusable |
| 14 | Cup_In_Dish_Rack (12,13; Ep_0,1 -> Ep_2+) | same | blue_cup (C) | rel to rack -25.4 | rms 0.9 / diff 1.9 | rack 180 resolved by rack brg 90.2 +-23 (margin >=67) |
| 15,16 | unknown, task_index 6 (no twin) | - | plastic_dish_rack (2) | abs 91.0 cross-task (needs world link) | rms 1.4 over 3 tasks, 5 eps | else geometry/markers (180 err costs AUC to ~0.5) |
| 19 | Dust_Brush (18; Ep_2 -> Ep_3+) | REVERSED | mini_sweeper (2) | rel to pan 39.2 / brg 105.2 (1 twin) | n=1; only <90 needed | cross-task sweeper abs 16.3, -3.5 (both ~0 mod 180) |
| 20 | Water_Can_Blue_Cup (21,22; Ep_3,6 -> Ep_0-2) | same | blue_cup (C) | brg -164.0 (or abs -68.8, rel -106.9) | brg rms 3.0 / diff 6.0; abs 8.0; rel 9.5 | LOO s3: abs/rel prior AUC 0.68-0.81, MP 0 |
| 25 | Planter_Stand (23,24; Ep_1,2 -> Ep_3+) | same | wooden_piece_1 (2) | brg 91.2 | rms 0.6 / diff 1.3 | rel to piece 2 is mod-180 only (piece 2 also 2-fold) |
| 28 | Pan_In_Dishrack (26,27; Ep_1,6 -> Ep_7+) | same | plastic_dish_rack (2) | brg 31.9 (world-free) or abs 92.3 | brg rms 27 / diff 54; abs 0.7 / 1.4 | brg still resolves 180 (margin >=36) |
| 30 | Brush_Dishrack (31; Ep_3 -> Ep_0-2) | same | mini_sweeper (2) | brg 84.9 (1 twin) | n=1; only <90 needed | rack slot 1: brg -0.4 resolves its 180 |
| 32,33 | unknown, task_index 12 (no twin) | - | blue_cup (C) | NONE from GT | blue cup abs is task-specific (41, 64, -69) | vision (markers) required |
| 35,36,37 | unknown, task_index 13 (no twin) | - | wooden_spoon (M) | none (single object) | - | roll-sign/body-frame choice still matters under rotation |
| 38 | Dustpan_Solo (39,40; Ep_1,2 -> ev38 = Ep_0) | same | mini_dust_pan (A) | none needed | abs rms 6.9 | single object |

Unknown-task grouping [E]: eval eps 3,5,6 (pot+spoon) and 8 (beige cup+pot) occupy task_index 1-3 together with
withheld 4,7,9; 15,16 (rack+spoon) = task 6 (17 withheld); 32,33 (cup+spoon) = 12 and 35-37 (spoon) = 13 (34 withheld).
Withheld episodes (neither public nor eval): 4, 7, 9, 17, 29, 34.
Coverage [V]: of the 6 eval eps with a cup in slot 0, a GT twin prior exists for 14 (strong), 20 (moderate) and 10
(single twin, needs either a world link or the bearing rule); 8, 32, 33 have NO GT prior. 2-fold slot-0 anchors
(19, 25, 28, 30) are all resolved by world-free bearing/relative rules with >=36 deg margin; 15/16 need a world link
or object geometry.

### A5. Staging line = mocap y axis [V] `s14_layout.py` -> `s14_layout.{out,json}`
Bearing (mod 180) of the start inter-object vector, 11 separated public pairs: 8 lie at 88.1-96.2 deg (mean 91.8,
sd ~2.4: Cup_Stack 11, Dust_Brush 18, Water_Can 21/22, Planter 23/24, Pan_In_Dishrack 26, Brush_Dishrack 31 -> 6 tasks,
task indices 4-11); exceptions are Cup_In_Dish_Rack 12/13 (22.5, 156.1) and Pan_In_Dishrack 27 (32.6).
Side rule (which object is at +y): sweeper (vs pan, vs rack), pitcher (vs cup), piece_2 (vs piece_1), beige (vs blue
cup), pot (vs rack, ep 26). [E] Objects are staged side by side along the table edge and the mocap y axis is parallel to
that edge within ~2 deg in every session -> independent support for A3 (world yaw constant) and a world-free way to read
the world yaw off two separated objects in our reconstruction (sign from the side rule). [H] The table edge itself (visible
in every video) is a third, object-free cue for the world yaw; testing needs video (stage B).

### A6. LOO of the world-free priors for slot-0 cups [V] `s15_loo_brg.py` -> `s15_loo_brg.{out,json}`
Held-out ep, prior from its single twin, cup spin error applied in every frame, official metric functions, perfect
tracking otherwise (AUC / SP-SR / MP-SR / MPPE cm; random spin baseline from s3: AUC 0.17-0.40, SP 0.12-0.21, MP <=0.07):
- ep 12 / 13 (Cup_In_Dish_Rack): rel err 1.9 -> 1.00/1.0/1.0/0.5; abs 2.7 -> 0.97/1.0/1.0/0.7; brg 43.7 -> 0.11-0.15/0/0/11-12.
- ep 21 / 22 (Water_Can): brg err 6.0 -> 0.84-0.87/1.0/0-1/1.6-2.0; abs 8.0 -> 0.74-0.81/1.0/0/2.1-2.7; rel 9.5 -> 0.68-0.77/1.0/0/2.5-3.2.
- Averaging rel and brg did not help (rack-task brg is wild). [V] No single prior type wins in both tasks; [E] rule for
  eval: choose the prior type with the smallest twin spread (ev14 -> rel, ev20 -> brg; abs is a close alternative when a
  world link exists). With only two twins per task this selection is itself noisy; expect ev20's anchor spin error
  ~5-10 deg (MP-SR still ~0 for that episode) and ev14 ~2 deg.

### A7. Other ambiguities and behavioural (motion-order) priors [V] (inline checks, GT + scans)
- Plank identity: wooden_piece_1 and _2 scans are geometrically identical (extents 2.7x13.9x22.7 vs 2.6x13.9x22.7 cm;
  Chamfer 2.5-2.6 mm under identity, all three 180 flips and a mirror, vs 2.0 mm self-noise floor). Combined with their
  2-fold symmetry, the world-free bearing rule cannot separate "swap identity" from "flip 180" -> identity must come from
  (a) side rule (piece_2 at +y of piece_1, bearing 92.5/90.7; needs world link), (b) motion order: piece_1 moves first
  (f22 vs f128 in ep 23; f12 vs f115 in ep 24), or (c) Vicon marker layout in the textures (stage B). A swapped identity
  makes the slot-0 anchor the wrong plank (start separation 28-31 cm) -> catastrophic for ev25.
- Roles (who moves): Cup_Stack beige moves onto a STATIC blue cup (ev10 slot 0 = blue = static anchor); Cup_In_Dish_Rack
  cup moves, rack static; Pan_In_Dishrack pot moves, rack static; Brush_Dishrack sweeper moves, rack static; Water_Can
  pitcher moves first (f42/43), cup also moves (31-38 cm path, net 2-3 cm); Pot_with_lid lid first (f57/60), pot later
  (f113/116); Dust_Brush pan first (f20), sweeper f40. Usable as identity/consistency checks, not as pose priors.
- Rack near-2-fold (15 mm Chamfer at 180, s5): resolved world-free by the rack bearing rule in ev14 (rack yaw - bearing
  rack->cup = 90.2 +-23), ev28 (31.9 +-27) and ev30 (slot-1 brg -0.4); NOT in ev15/16 (no twin; needs world link: rack
  world yaw 91.0 +-1.4 in 3 tasks).

## Stage A summary (complete, ~12:30)
1. [V] Start yaw per (task, object) is consistent to <=4 deg rms for every pair with >=2 public eps except the lid
   (17), dust pan (7) and the pot when its rest face changes; rest tilt/z are set by the stable face (<=0.5 deg sd).
2. [V] Mocap world: z = gravity in every episode; yaw constant across all public episodes/sessions to ~1-2 deg (static
   rack 89-93 deg across task indices 5/10/11; twin static objects agree to 0.1-0.7 deg); x,y origin re-centred per
   episode (irrelevant to the slot-0-aligned scorer). [E] the mocap y axis is the table-edge staging line (8/11 pairs at
   91.8 +-2.4 deg). Link of this world to the room/camera is NOT yet measured (stage B; needs public stereo/PnP).
3. [V] Eval -> twin map is automatic (object multiset + task_index bracketing + global index gaps). Slot-0 cups:
   ev14 rel-to-rack prior (LOO err 1.9 deg, AUC 1.0), ev20 bearing prior (LOO err 6 deg, AUC 0.84-0.87, MP-SR mostly 0),
   ev10 single-twin bearing/abs prior (unvalidated), ev8/32/33 NO GT prior -> need vision (marker layout in textures).
   2-fold anchors 19/25/28/30 resolved world-free with >=36 deg margin; 15/16 need a world link or geometry;
   ev25 additionally has a plank-identity ambiguity (identical scans) -> motion-order or marker cue.
Proposed stage B (not started): (i) measure world<->room link on public eps with video (stereo cam_b/cam_c needs
downloads; only ep 12 has cam_c locally) and transfer to eval via s7 room registration; (ii) marker-layout spin
estimation for cups/lid/planks from eval video; (iii) falsification test: if the world<->room yaw spread across
public eps exceeds ~5 deg, abs priors for ev10/15/16 are not usable and only marker vision remains.
Artifacts: `work/11/s11_consistency.*`, `s12_worldyaw.*`, `s13_priortable.*`, `s14_layout.*`, `s15_loo_brg.*`
(plus earlier s1-s10). All runs: `/Users/aebatirel/Documents/Code/v2d-research/venv/bin/python <script>` in `work/11/`.

## Stage B (official scorer, CPU) -- started ~13:00 (resumed run; workflow-defined scope)
Scope as assigned: LOO on public eps of the score gain from setting a symmetric slot-0 anchor's yaw from the task prior
vs random yaw, with world-yaw knowledge W exact / +-3 / +-10 deg (AUC, SP-SR, MP-SR, RPE, MPPE); plus other room-memory
priors (table height, final placements, stable rest poses) where measurable. (The world<->room video test proposed at the
end of Stage A is NOT part of this stage and needs downloads; not attempted.)
Method: the kit's own `score()` entry points (AUC/SP-SR/MP-SR/RPE/MPPE.py) on synthetic solution/submission frames
(dummy provenance, AUC vertex payload = 500 area-weighted scan surface samples per object, seed 0 -> AUC is [E] w.r.t.
the organisers' hidden vertex set). Reference = public GT; "achieved" = GT with the modelled error (perfect tracking
otherwise unless stated). Error model for a symmetric anchor: constant body-frame spin d about its rest-up symmetry axis
in every frame -> the scorer's frame-0 warp rotates the rest of the scene about the anchor by -d.

### B1. Slot-0 symmetric-anchor yaw prior, LOO, official score() [V] `sc11.py`, `s16_anchor_loo.py` -> `s16_anchor_loo.{out,json}`, `s16_summary.out`, `s16_aggregate.out`
Wrapper check [V]: official `score()` equals the internal-function path of s3 to all printed digits (ep 12, spin 30:
AUC 0.18405, MPPE 7.7947), and the s16 cup aggregates reproduce s3 exactly. Sign check: spin about UP by +20 raises the
anchor yaw by 20.0 in every case. Values are AUC / SP-SR / MP-SR / RPE cm / MPPE cm; one world, so SP/MP per condition are
0/1 and the +-W rows average both signs (0.5 = one sign passes).
Per-episode LOO (prior from the twin(s) only; 2-fold racks/sweeper use every other public ep holding that object):

| ep (anchor, sym) | prior err (deg) | random | abs W=0 | abs W+-3 | abs W+-10 | world-free best |
|---|---|---|---|---|---|---|
| 12 (blue cup, C) | abs -2.7, rel -1.9, brg 43.7 | 0.19/0.12/0.04/23.5/18.9 | 0.97/1/1/0.9/0.7 | 0.94/1/1/1.0/0.8 | 0.72/1/0.5/3.2/2.6 | rel 1.00/1/1/0.6/0.5 |
| 13 (blue cup, C) | abs 2.7, rel 1.9, brg -43.7 | 0.17/0.12/0.07/12.6/20.2 | 0.96/1/1/0.5/0.7 | 0.93/1/1/0.5/0.8 | 0.73/1/0.5/1.7/2.8 | rel 1.00/1/1/0.3/0.5 |
| 21 (blue cup, C) | abs -8.0, rel -9.5, brg -6.0 | 0.35/0.18/0.01/40.4/24.3 | 0.74/1/0/4.4/2.7 | 0.74/1/0/4.4/2.6 | 0.73/1/0.5/5.5/3.3 | brg 0.84/1/0/3.3/2.0 |
| 22 (blue cup, C) | abs 8.0, rel 9.5, brg 6.0 | 0.40/0.21/0.04/32.1/19.2 | 0.81/1/0/3.5/2.1 | 0.82/1/0.5/3.5/2.1 | 0.76/1/0.5/4.4/2.6 | brg 0.87/1/1/2.6/1.6 |
| 23 / 24 (plank 1, 2-fold) | abs -3.1 / 3.1 (margin 87) | 0.52, 0.51 / 0.5 / 0.5 / 10-12 / 17-18 | 1/1/1/0/0 | same | same | - |
| 26 / 27 (rack, 2-fold, cross-task prior n=4) | -2.5 / -0.8 (margin 88-89) | 0.75 / 0.5 / 0.5 / 17-19 / 9 | 1/1/1/0/0 | same | same | - |
| 31 (sweeper, 2-fold, prior from ep 18 only) | 19.8 (margin 70) | 0.55 / 0.5 / 0.5 / 11.9 / 9.6 | 1/1/1/0/0 | same | same | - |
| 11 (beige cup, C; no twin) | - | 0.20/0.21/0.07/6.3/19.4 | - | - | - | - |

Aggregates (mean over LOO eps) [V]:
- Cups (12, 13, 21, 22): random 0.277/0.16/0.04/27.1/20.7 -> abs W0 0.871/1.0/0.50/2.3/1.55; W+-3 0.858/1.0/0.63/2.3/1.59;
  W+-10 0.734/1.0/0.50/3.7/2.84. World-free: rel 0.861/1.0/0.50/2.6/1.67; brg 0.493/0.5/0.25/6.8/6.7 (fails in the rack
  task); per-task best world-free (rel for 12/13, brg for 21/22) 0.928/1.0/0.75/1.7/1.15 [optimistic: with 2 twins the
  selection rule is the LOO error itself].
  Gain of the abs prior over random yaw: dAUC +0.59 (W0), +0.58 (W3), +0.46 (W10); SP-SR +0.84 at every W; RPE -24.8 cm;
  MPPE -19 cm. MP-SR gain only +0.46..+0.58 and is fragile (see curve).
- 2-fold anchors (23, 24, 26, 27, 31): random branch 0.616/0.5/0.5/13.9/12.5 -> any abs prior with W <= 10 (margins 70-89
  deg) 1.0/1.0/1.0/0/0 (assuming geometry gives the axis exactly). Gain dAUC +0.38, SP/MP +0.5, RPE -13.9, MPPE -12.5.
Spin-error curves (+-d mean) [V] give the error budget for any prior/vision estimate (cup anchors 12/13/21/22, 11):
AUC >= 0.9 needs |d| <= ~5 deg; AUC ~0.7 at 10; ~0.5 at 15; <=0.35 at 20 (rack/plank tasks) or ~0.48 (Water_Can, close
pitcher). SP-SR survives to 20-30 deg (fails at 45 everywhere; 30 in rack/plank tasks). MP-SR fails already at
10 deg in 12, 21, 22, 23, 24, 27 (other object 17-31 cm from the anchor -> >3 cm displacement) and at 15-20 in 13/26/31.
-> [V] The task prior pays almost all of its AUC/SP-SR/RPE/MPPE value even at W = +-10, but MP-SR needs the anchor
spin within ~5-8 deg, i.e. a W of <= ~3 deg AND a tight prior (only Cup_In_Dish_Rack qualifies; Water_Can's 8 deg twin
spread already kills MP-SR at W=0).

### B1b. Eval-slot-order proxies (no LOO possible: single twin) [V] `s17_proxy_tilt.py` -> `s17_proxy_tilt.{out,json}`
Public twin re-ordered to the eval slot order, spin curve (+-d mean) and random baseline (AUC/SP/MP/RPE/MPPE):
- ev10 proxy = ep 11 with blue cup (static base, C) in slot 0: random 0.70/0.32/0.17/6.4/4.7; d=10 0.96/1/1; d=20 0.89/1/1;
  d=30 0.84/1/0.5; d=45 0.79/1/0; d=180 0.56/0/0. The stacked beige cup ends ON the anchor's axis, so the anchor spin
  only hurts while the beige cup is still apart (17 cm) -> max prior gain dAUC ~+0.27, SP +0.68, MP +0.83 with |d|<=20.
  A single-twin prior (unknown error, [E] 3-22 deg) is enough for ev10 even at W=+-10.
- ev19 proxy = ep 18 with sweeper (2-fold) in slot 0: random branch 0.61/0.5/0.5/20.1/13.4 -> correct branch 1/1/1/0/0
  (gain dAUC +0.39). The branch prior (rel to pan 39.2 / brg 105.2, or abs sweeper ~0 mod 180) has >=70 deg margin.

### B2a. Anchor TILT error vs stable-rest-pose + table-plane prior [V] `s17_proxy_tilt.py` (tilt section)
Constant body-frame tilt error of the slot-0 object about a world-horizontal axis (mean of 8 azimuths), all 20 public eps:
| anchor tilt err | 2-object eps (13): AUC/SP/MP/RPE/MPPE (min AUC) | 1-object eps (7) |
|---|---|---|
| 1 deg | 1.000/1/1/0.26/0.19 (1.00) | 1.000/1/1/0/0.18 |
| 2 | 0.997/1/1/0.52/0.39 (0.98) | 0.999/1/1/0/0.36 |
| 3 | 0.988/1/1/0.78/0.58 (0.97) | 0.984/1/1/0/0.54 |
| 5 | 0.952/1/0.98/1.29/0.97 (0.90) | 0.957/1/1/0/0.90 |
| 8 | 0.888/1/0.83/2.07/1.55 (0.80) | 0.893/1/1/0/1.44 |
Stable-pose residuals (s8, LOO-free since one value per object/face): tilt sd <= 0.5 deg, origin z sd <= 0.5 mm; the
table plane from our own reconstruction is the remaining error ([E] ~1 deg). -> [V] snapping the anchor to its stable
rest face (tilt ~1 deg) is worth dAUC ~+0.01 if vision tilt error is 3 deg, +0.05 at 5 deg, +0.11 at 8 deg (MP-SR
+0.02 / +0.17 at 5 / 8 deg). It is cheap insurance, not a large win, unless the anchor tilt is poorly observed (cups seen
from above, partial occlusion). Pairs with the yaw prior: both are frame-0 anchor terms that the scorer's warp multiplies
by inter-object distance.

### B2b. Final-placement priors, twin-to-twin (LOO) consistency [V] `s18_endplace.py` -> `s18_endplace.{out,json}`
Mover pose in the receiver's body frame at the end (median of the mover's last static segment; ep 12's cup is static
from ~f145 but missed by the s8 detector, so the final frame is used). dt = translation diff, drot = full rotation diff,
daxis = angle between the mover's rest-up (symmetry) axes, i.e. ignoring spin.
| task (eps) | mover -> receiver | end rel. translation (cm) | dt cm | drot deg | daxis deg | verdict |
|---|---|---|---|---|---|---|
| Pot_with_lid (0, 2) | lid -> pot | (5.6, 0.0, -0.2) / (5.6, 0.1, -0.1) | 0.2 | 28.6 (spin) | 1.1 | STRONG (pos + axis); lid spin free |
| Planter_Stand (23, 24) | piece_1 -> piece_2 | (0.1,0.1,0) / (-0.2,0.2,0) | 0.3 | 3.8 | 0.6 | STRONG interlock (full 6-DoF) |
| Planter_Stand (23, 24) | piece_2 -> piece_1 | ~0 | 0.3 | 3.9 | 3.8 | STRONG |
| Cup_In_Dish_Rack (12, 13) | cup -> rack | (7.9, 1.3, 16.9) / (7.4, -0.4, 2.0) | 15.0 | 26.7 | 16.8 | NONE: different rack slot (tilt 179 vs 162) |
| Pan_In_Dishrack (26, 27) | pot -> rack | (2.8, 20.5, 9.0) / (7.4, 1.5, 15.8) | 20.7 | 180 | 155 | NONE: pot face differs |
| Water_Can (21, 22) | pitcher -> cup | | 10.5 | 37.5 | 23.9 | NONE (pour pose varies) |
| Water_Can (21, 22) | cup -> pitcher | | 22.8 | 37.2 | 0.8 | world end yaw -88.1/-89.9, tilt 1.1/1.1 (world prior only) |
| Pan_Solo (41-45) | pot -> own start | | 1.2-8.5 | 1-180 | 0.4-178 | relative NONE; world end yaw -4.5..0.9 (rms 2.0), tilt 12.0+-0.1 -> world prior only |
| Dustpan_Solo (39, 40) | pan -> own start | | 8.4 | 25.2 | 5.1 | weak |
| Cup_Stack (11 only) | beige -> blue | (-0.1, 0.5, -3.2) | - | - | - | nested coaxial (geometry/physics prior [H], 1 twin) |
| Brush_Dishrack (31 only) | sweeper -> rack | (4.0, -0.4, 1.1) | - | - | - | 1 twin |
-> [V] Fixed end-placement priors exist for the interlocking/fitting tasks (lid on pot 2 mm / 1 deg axis; plank cross-joint
3 mm / 4 deg) and for world end yaw of the Water_Can cup and Pan_Solo pot (needs the world link). The cup-in-rack slot
is NOT a fixed prior (15 cm apart in the two public takes); a rack-slot snap would need rack geometry (slot set), not
room memory. Eval relevance: ev1 (lid), ev25 (planks), ev20 (cup end yaw, world), ev28 (pot-in-rack: none).

### B2b-2. Score value of snapping a final placement to the twin's relative pose [V] `s19_endsnap_score.py` -> `s19_endsnap_score.{out,json}`, `s19_summary.out`
"Placed" segment = final run where the mover's pose in the receiver frame stays within 0.5 cm / 3 deg of its final
value (GT-based segmentation; a first version using s8 static segments gave 1-frame segments for the lid because the pot
still moves with the lid on it; replaced). Segments: lid 29 % (ep 0) / 15 % (ep 2) of frames; plank piece_2 22 % / 21 %.
LOO prior residual: lid 0.33 cm + axis ~1 deg (spin kept from "vision"); planks 0.26 cm / 3.1 deg (full 6-DoF snap).
Constant vision error on that segment, mean of 8 random directions (AUC / SP / MP / RPE / MPPE), perfect tracking elsewhere:
| vision err | lid ep 0: vision -> snap | lid ep 2 | plank ep 23 | plank ep 24 |
|---|---|---|---|---|
| 0.5 cm / 2 deg | 1.000 -> 1.000; RPE 0.15 -> 0.06 | 1.000 -> 1.000 | 1.000 -> 1.000 | 1.000 -> 1.000 |
| 1 cm / 5 deg | 0.991 -> 1.000 | 0.995 -> 1.000 | 0.993 -> 1.000 | 0.993 -> 1.000 |
| 2 cm / 10 deg | 0.973 -> 1.000; RPE 0.58 -> 0.06 | 0.986 -> 1.000 | 0.980 -> 1.000 | 0.980 -> 1.000 |
| 3 cm / 15 deg | 0.954 -> 0.995; RPE 0.88 -> 0.06; MPPE 0.45 -> 0.08 | 0.976 -> 0.998 | 0.966 -> 1.000 | 0.967 -> 1.000 |
SP-SR and MP-SR stay 1.0 in every variant (an error on <=30 % of frames of one object cannot move the episode means
past 10 cm / 3 cm). -> [V] Under the scorer, an end-placement snap is worth only dAUC +0.01..+0.04 per affected episode
(ev1, ev25) and a few mm of RPE/MPPE, because the placed state covers 15-30 % of frames. [H] Its larger value is probably
physical: a reference with the lid not seated / planks not interlocked (interpenetration or a gap) may make the
FlashCHORD policy fail or knock objects, which this kinematic test cannot see; test in sim (stage C).

### B2c. Table height + stable rest pose on static on-table segments (s9 redone with official score(), 3 noise levels) [V] `s20_rest_snap.py` -> `s20_rest_snap.{out,json}`, `s20_aggregate.out`
All 20 public eps, 4 seeds. Vision model: constant error per static on-table segment (pos sigma per axis / rotation sigma),
i.i.d. noise of the same sigmas on moving frames. Prior: z and tilt parts of each static-segment error replaced by the
snap residual (z 1 mm, tilt 1 deg [E] own table-plane fit; GT rest spread <=0.5 mm / 0.5 deg), x/y/yaw errors kept.
| noise | vision AUC/SP/MP/RPE/MPPE | with rest prior | dAUC per ep (min/median/max) |
|---|---|---|---|
| 0.5 cm / 2 deg | 0.947/1.00/0.99/0.79/1.14 | 0.964/1.00/1.00/0.71/0.98 | -0.001 / +0.014 / +0.038 |
| 1 cm / 4 deg | 0.818/1.00/0.78/1.58/2.28 | 0.862/1.00/0.78/1.40/1.94 | -0.001 / +0.035 / +0.088 |
| 2 cm / 8 deg | 0.562/0.98/0.13/3.15/4.56 | 0.624/1.00/0.28/2.80/3.86 | +0.004 / +0.058 / +0.136 |
Static on-table share of frames 20-64 % per episode. -> [V] The rest prior is a consistent, never-harmful gain of about
+0.015 / +0.04 / +0.06 AUC at 0.5 / 1 / 2 cm vision noise, -10..-15 % RPE/MPPE, and some MP-SR at high noise (+0.15).
It needs only our own table plane plus the per-object stable-face table (s8), no world link. Largest where objects rest
longest (13, 23, 27: +0.07..+0.14 at 2 cm). Consistent with s9 (1 cm/4 deg, exact snap: 0.813 -> 0.842).

### B1c. Does the anchor-yaw prior gain survive tracking noise? [V] `s21_anchor_noise.py` -> `s21_anchor_noise.{out,json}`, `s21_aggregate.out`
Anchor spin (random vs abs prior W+-3 from s16) composed with the s20 noise model (1 cm / 4 deg, rest prior on), 4 seeds:
- Cups 12/13/21/22: random 0.255/0.16/0.03/27.4/21.2 -> abs W+-3 0.772/1.0/0.53/3.5/2.6 (dAUC +0.52; noiseless +0.58).
- 2-fold 23/24/26/27: random 0.549/0.5/0.38/15.6/14.3 -> 0.857/1.0/0.75/2.0/2.0 (dAUC +0.31; noiseless +0.38).
-> [V] About 85-90 % of the noiseless gain remains; SP-SR gain is unchanged (+0.84 / +0.5).

## Stage B summary (~14:00)
Method: kit `score()` for all 5 metrics on synthetic frames (wrapper `sc11.py`, matches the internal-function path
exactly); AUC vertices = 500 scan surface samples per object [E vs hidden set]; perfect tracking unless stated.
1. [V] Symmetric slot-0 anchor yaw from the task prior vs random yaw (LOO, 4 cup eps): AUC 0.277 -> 0.871 / 0.858 / 0.734 for
   W exact / +-3 / +-10; SP-SR 0.16 -> 1.0 at every W; MP-SR 0.04 -> 0.50 / 0.63 / 0.50; RPE 27.1 -> 2.3 / 2.3 / 3.7 cm;
   MPPE 20.7 -> 1.6 / 1.6 / 2.8 cm. World-free relative prior (no W needed): 0.861/1.0/0.50/2.6/1.7. With 1 cm / 4 deg
   tracking noise the gain is +0.52 AUC (B1c). 2-fold anchors (planks, rack, sweeper; 5 eps): branch prior margin 70-89 deg
   -> robust to W <= 10 (any W < ~70): AUC 0.616 -> 1.0, SP/MP 0.5 -> 1.0, RPE 13.9 -> 0, MPPE 12.5 -> 0 (noisy: +0.31 AUC).
2. [V] Error budget for the cup anchor spin (curves): AUC >= 0.9 needs <= ~5 deg, 0.7 at 10, ~0.5 at 15; SP-SR tolerates
   20-30 deg; MP-SR needs <= ~5-8 deg (other object 17-31 cm away). Only Cup_In_Dish_Rack's prior (1.9-2.7 deg LOO) is tight
   enough for MP-SR; Water_Can's (6-8 deg) is not. ev10 (Cup_Stack, stacked cup ends on the anchor axis) is insensitive:
   random 0.70, |d| <= 20 gives >= 0.89.
3. [V] Other room-memory priors are small under the scorer: anchor tilt snap (stable face + table plane) dAUC +0.01 at 3 deg
   vision tilt error, +0.05 at 5, +0.11 at 8; rest-pose (z + tilt) snap of all on-table static segments +0.015 / +0.035 / +0.06
   AUC (median per ep) at 0.5 / 1 / 2 cm noise, never harmful; end-placement snap (lid on pot 2-3 mm / 1 deg axis, plank
   interlock 3 mm / 3-4 deg) +0.01..+0.04 AUC at 1-3 cm / 5-15 deg vision error, SP/MP unchanged. Cup-in-rack slot and
   pot-in-rack end pose are NOT consistent across public takes (15-21 cm apart) -> no prior. Table height itself is irrelevant
   to the slot-0-aligned scorer except through relative z (covered by the rest snap); measured 0.6012 m (s8).
4. [E] Projected eval impact (per-episode dAUC vs random/coin-flip anchor yaw, perfect tracking otherwise; leaderboard mean
   is the sum / 20): ev14 +0.82 (rel prior), ev20 +0.45 (brg/abs), ev10 +0.2..0.27, ev8/32/33 0 (no GT prior; need vision);
   2-fold branch: ev19 +0.39, ev25 +0.49 (if plank identity is right), ev28 +0.25, ev30 +0.45, ev15/16 ~+0.25 each (only with
   a world link; co-object is a spoon, so distance and gain differ). Sum ~3.6 -> leaderboard AUC about +0.18 (cups +0.08,
   2-fold +0.10). Under 1 cm / 4 deg noise, about 85 % of that. The 2-fold gain is an upper bound: vision may already pick
   the right branch from residual asymmetry (rack 15 mm Chamfer at 180).
Limitations: two twins per task at most (LOO = one comparison); W was not measured (needs the world<->room video test,
deferred); kinematic only: physical effects of the priors (seated lid, interlocked planks, rest contacts) on the FlashCHORD
policy are untested [H]. Next (stage C): sim-side or vision-side checks, as assigned.
Artifacts (all in `work/11/`): `sc11.py`, `s16_anchor_loo.*` (+ `s16_summary.out`, `s16_aggregate.out`), `s17_proxy_tilt.*`,
`s18_endplace.*`, `s19_endsnap_score.*` (+ `s19_summary.out`), `s20_rest_snap.*` (+ `s20_aggregate.out`), `s21_anchor_noise.*`
(+ `s21_aggregate.out`). Run: `/Users/aebatirel/Documents/Code/v2d-research/venv/bin/python <script>` in `work/11/`.

## Stage C (W = our-world -> mocap yaw on eval eps) -- started ~(resumed run)
- Scope: estimate W from (i) asymmetric co-objects with consistent priors, (ii) table edges / room features; view frames of
  3-4 public colour clips (reuse local downloads: public cam_a 0,11,12,13,18,21,22,23,26,31,39,41; cam_b 0,11,12,13,21,22,26,27;
  cam_c 12 only; all 20 eval cam_a). No new downloads planned.
- C0 [V] (viewing frame 0 of public 0/11/12/13/21/22/23/26/31; `work/11/cfr/`): the table is a small ROUND wooden top
  (no straight table edge exists -> the "table edge" cue of A5 is void; the staging line is the seated person's
  left-right axis instead). Fixed room features visible in every frame 0: black truss pillar straight ahead, yellow/black
  hazard tape and blue tape on the floor, floor arrow markers, box + cages. Image right = mocap +y in every clip
  (pitcher right of cup, beige right of blue, rack long axis left-right), i.e. the camera looks roughly along mocap -x.
- C1 method `s23_mask.py` + `s24_campose.py <native|flipped> eps`: camera pose of frame 0 IN THE MOCAP WORLD from GT-posed
  scans (30k-pt splats) vs a white/blue colour mask, IoU over the touched fg components, grid (psi 140-220, pitch 25-65,
  offsets) at 1/8 res then Nelder-Mead at 1/4 and 1/2 res. Ep 12 (flipped K): IoU 0.74, heading psi 177.7, pitch 31.8 down,
  roll 5.5, camera 0.30 m behind (+x) and 0.44 m above the object centroid; overlay `cfr/fit_flipped_12.png` matches.
- C1 first pass (flipped K, colour-mask IoU; `s24_campose_flipped.json`): heading psi = 177.7 (12), 181.4 (13), 175.8 (21),
  176.3 (22, after adding an off-image penalty; the first run converged to an off-screen solution), 176.4 (26), 173.7 (31:
  poor fit, IoU 0.54, the shadowed rack tower is missing from the colour mask). Visual check `cfr/view_flipped_26_31.png`,
  `cfr/m_fit1.png`. Against the s7 room registration (camera heading change vs ep 12 from background features):
  psi_e - psi_12 = +3.6 / -1.9 / -1.3 / -4.0 for 13/21/26/31 vs s7 -dh = +1.0 / -3.0 / -0.2 / -4.5 -> residual rms ~1.6 deg
  with sign s7_heading = -(change of psi). [E, first pass] The mocap world looks fixed in the room to ~2 deg. Refinement
  with a GrabCut mask + heading profile (`s25_refine.py`) next.
- C1 batch 2 (`logs/s24_batch2.log`): good fits (visual, `cfr/view_flipped_0_22_11_18_39_41.png`) for ep 0 (psi 178.0, IoU 0.84)
  and 22 (176.3); FAILED fits for 11 (two spin-symmetric cups, mask dominated by floor glare), 18 and 39 (yellow dust pan
  not in the white/blue mask), 41 (single pot, fit snapped to a floor reflection), 23 (planks: wood-on-wood mask). Lesson:
  object silhouettes pin the camera heading only with an asymmetric object or two separated objects AND a usable mask.
  Next: GrabCut refine (`s25_refine.py`) on the 7 good eps, then room-registration transfer (`s26_transfer.py`).
- C2 GrabCut-refined fits (s25, flipped K) psi/IoU: 12 177.8/0.95, 13 180.7/0.97, 21 175.1/0.89, 22 175.7/0.88, 26 180.9/0.91,
  0 181.4/0.96, 31 174.8/0.87; heading profiles sharp for 12/13/0, flat for 21/22/26/31. Raw psi sd 2.8; with s7 (sign -1) sd 2.4.
- C3 room transfer (s26/s27): refs {12,13,21,0} LOO residuals +0.9/-0.7/+0.5/-0.4 (rms 0.65); all-6 refs: outliers 22 (fit 175.7 vs
  room 180.6) and 26 (180.9 vs 178.0) = the flat-profile fits. Ref-set selection made after seeing residuals (21 borderline).
- C3b s28 fixed-heading IoU at room value: 22 0.8724 vs 0.8726; 26 0.9212 vs 0.9075 (room better); 31 0.8835 vs 0.8824.
- C4 gravity via room transfer: roll LOO +-1 deg, pitch 2-5 deg -> heading only.
- C5 eval frame-0 viewing (design-time): staging matches twins (10, 14, 25, 28, 30) and rack tower-left in 15/16; ev20 cup in hand at f0.
- C6 plank texture: piece_2 up face paler (sat 0.41 vs 0.52) -> weak identity cue [H].
- C7 native K: psi 12 180.6 / 13 183.0 / 21 177.0 / 0 181.4; LOO rms 1.18 (flipped 0.65); IoU flipped >= native on all 4 refs.
- C8 eval W table (flipped/native): see final document section 8.6 (`s27_stats_{flipped,native}_best4.json`).
- Final rewrite of 11-placement-priors.md done after C8 (this backup holds the raw chronological log).
