# 15 — Eval video survey (agent 15, 2026-10-05) — IN PROGRESS

Work dir: /Users/aebatirel/Documents/Code/v2d-research/work/15/ (dl.sh, sheet.py, sheets/*.png)
Videos: /Users/aebatirel/Documents/Code/v2d-research/data/track_3/evaluation/videos/chunk-000/observation.images.ego_cam_a/ (all 20, sizes match tree.json)

## Early findings
- [V] Stored ego_cam_a eval video is ALREADY upright (hands enter from image bottom, floor/horizon at top).
  Rotating it 180 deg makes it upside down. calibration.json marks ego devices rotation_deg=180 and the
  ego stereo pair entry says left=ego_cam_c, right=ego_cam_b ("a 180 degree rotation mirrors the baseline
  direction"), i.e. the file describes the rotated (stored) orientation. Whether intrinsics cx/cy are
  for the raw or rotated image is still unverified. Sheet: sheets/e1_norot.png vs e1_even (rotated, wrong).
- [V] Eval frame counts (ego_cam_a, 20 fps): 1:335 3:313 5:288 6:243 8:219 10:161 14:158 15:166 16:173 19:235
  20:202 25:356 28:220 30:263 32:259 33:348 35:421 36:407 37:151 38:263.

## Progress 1 (12-frame sheets for all 20 viewed; sheets/e<ep>_even.png, sheets/f0_a.png, f0_b.png)
- [V] Eval 20 frame 0: slot-0 blue_cup already held in the air by the left hand (tilted, off-table, sheets/e20_f0.png).
  Public twins 21/22 start with the cup resting on the table (GT z0 0.687 = resting; p21_start.png). Zero static prefix.
- [V] Eval 32 frame 0: left hand already wrapped around slot-0 blue_cup (on table); lifted by ~f23.
- [V] Second person visible in background in 15, 16 (seated, green shirt, hands/arms) and 25 (standing legs).
- Notes per episode being written below.

## Progress 2 (onset sheets sheets/e<ep>_onset.png viewed for all except 20; calibration test)
- [V] Calibration convention (work/15/rectcheck2.py): stored ego mono frames rectify best with the
  calibration AS GIVEN (left=ego_cam_c, right=ego_cam_b, K/D unchanged, no extra 180 flip):
  median |dy| 1.2-2.2 px after rectification (eval 3, 20, 35) vs 3.3-12 px for flipped-K or conjugated
  variants. So intrinsics/extrinsics in camera_calibration.json already describe the stored upright images.
  Residual 1-2 px median |dy| (p90 3-5 px) is larger than ideal (<0.5 px) -> possible small calibration
  drift / rolling-shutter / ORB noise; [H] a per-recording self-calibration refinement of the stereo
  rotation may be worth checking for depth accuracy.
- [V] colour(a)->mono(b) extrinsic: the 'extrinsics_to_stereo_left' of ego_cam_a fits matches with
  inv=0 (median epipolar 3-4 px with ORB on a half-res colour); inverse is 22-34 px. Rotation from
  essential-matrix estimate agrees with calibration to ~0.7-1.3 deg. [E] good enough to reproject stereo depth.

## Progress 3 (resumed 2026-10-05 after outage)
- [V] All 20 eval ego_cam_a clips present; eval ego_cam_b for 3,8,15,20,25,35,36,37 and ego_cam_c for 3,20,35,36.
- [V] Re-made UPRIGHT (no rotation) 12-frame sheets: work/15/up/e<ep>_even12.png (older sheets/e*_even.png are rotated 180 = upside down).
- [V] Mocap marker balls (black/grey spheres, ~1 cm) are visible on the pot lid and pot in eval 1 (sheets/e1_norot.png).
- [V] Public GT static prefixes (work/15/gt_start.out): slot-0 1 cm onset 10-114 frames when slot 0 moves; slot 0 never moves in 11 (blue_cup), 26/27/12?/13? (rack is slot 1 in 12/13; rack is slot 0 in 26/27/31).

## Progress 4 (resumed again 2026-10-05; Stage A per-episode descriptions, eps 1-16)
- [V] Stage-A instruction says "rotate 180"; per Progress 1/2 the stored ego_cam_a is already upright, so
  descriptions below use the UPRIGHT sheets work/15/up/e<ep>_even12.png (12 evenly spaced frames, 400 px wide each)
  plus onset sheets. Eval object slots from kit data/track_3_evaluation_objects.json.

### Eval 1 (335 f, 16.7 s; slots: 0 white_pot, 1 white_pot_lid; twin task Pot_with_lid = public 0/2)
- [V] Sequence: f0-16 both hands raised open, pot (handle toward camera) + lid closed on round wooden table;
  ~f24-32 LEFT hand grips pot handle, RIGHT hand grips lid knob; lid lifted ~f44-48 and set on table right of
  pot (~f60); pot slides/repositioned on table while held f60-125; pot LIFTED off table by left hand ~f127-132,
  waved/tilted in air f132-182 (interior visible, strong motion blur f152/f172, pot above table edge against
  floor background), set down ~f187-213; right hand lifts lid again ~f243, re-lids pot ~f273, hands release by f334.
- [V] Head (camera) moves a lot: table shifts ~1/4 image height between frames; table never leaves view.
- [V] Occlusion: pot handle mostly covered by left hand f28-300; lid knob covered by right fingers while held.
  Pot never leaves view; lid partly occludes pot rim when re-lidding. Mocap marker balls on pot/lid visible.
- [V] Lighting: bright even overhead industrial lighting, specular floor; white objects near saturation on
  the lid top (low texture). [E] slot-0 static start: pot may be nudged at lid removal (~f48-60, uncertain due
  to head motion); unambiguous lift at ~f127. So static prefix >= ~45 frames, likely ~45-125. Public twins: 112-114.
- Risks [H]: white low-texture pot+lid of similar colour (lid/pot confusion in segmentation), symmetric
  pot body (yaw from handle only, handle occluded by hand), fast airborne motion with blur.

### Eval 3 (313 f, 15.6 s; slots: 0 white_pot, 1 wooden_spoon; no public twin - spoon has no scan/GT, cf. 10/13)
- [V] Task looks like "stir pot with spoon": f0-20 both hands raised open; spoon lies on table right of pot,
  pot handle toward camera. RIGHT hand picks spoon ~f32-56 (lifted vertically ~f56); LEFT hand grips pot
  handle ~f50-56 and holds it the rest of the clip. Spoon dipped into pot ~f96-104 and stirred / waved above
  and inside the pot rim f96-255 (repeated in-out strokes, spoon often vertical, bowl up), returned to table
  ~f284, hands open at f312.
- [V] Pot appears to stay on the table, held by its handle (stabilising); [E] only small slides/jostles,
  no lift visible in 12+16 sampled frames. So slot 0 (frame alignment anchor) is near-static, but its handle
  is hand-occluded from ~f50 to ~f300.
- [V] Spoon motion: fast, large rotations (vertical<->horizontal), motion blur on spoon at f104/f199; spoon
  bowl inside the pot is occluded by the pot wall/rim at times; spoon handle partly hidden in right fist.
  Spoon goes above the table edge against the floor background but stays in frame.
- [V] Lighting bright/even; black mocap balls on spoon handle tip and pot visible.
- [E] slot-0 static start >= ~50 frames (until left-hand grasp); pot possibly static (+-1-2 cm) all clip.
- Risks [H]: spoon thin/elongated with symmetric bowl -> roll ambiguity; spoon-in-pot occlusion; no mesh.

### Eval 5 (288 f, 14.4 s; slots: 0 white_pot, 1 wooden_spoon; same scene layout as eval 3)
- [V] f0-8 hands open; LEFT hand grips pot handle already ~f16-20 (early), pot handle angle on table changes
  f24-40 ([E] pot rotated/slid while held). RIGHT hand lifts spoon ~f40-48, stirs inside pot on table f56-72;
  pot LIFTED off table (left hand) ~f80-104, raised close to camera (pot fills ~1/3 image width, strong
  blur f88/f96/f104, rim toward camera so interior dominates), lowered ~f112; stirring in pot f112-209
  with repeated lifts (f157/f183 pot again close to camera, spoon inside, blurred); pot back on table ~f235,
  spoon back on table ~f261; hands released f287.
- [V] Occlusion: handle in left fist; spoon bowl inside pot (occluded by wall) during stirring; right
  forearm crosses over pot during stirring. Neither object leaves frame in samples.
- [E] slot-0 static start ~16-24 frames only (grasp at ~f16-20, motion soon after). Short anchor window.
- Risks [H]: pot near camera -> large scale change + defocus/blur; pot interior (uniform white) dominates
  view -> few features; frame-0 anchor pose must be estimated from <1 s of static data.

### Eval 6 (243 f, 12.1 s; slots: 0 white_pot, 1 wooden_spoon; same layout as 3/5)
- [V] f0-8 hands open; LEFT hand on pot handle by f16, pot rotated/slid on table by ~f24-32 ([E] handle
  direction changes ~20-30 deg). RIGHT hand lifts spoon ~f32-40 (blur), stirs inside pot f48-176 while
  left hand holds/tilts pot; pot raised a little off the table toward the camera at ~f80 and ~f110
  ([E] tilt + lift of a few cm, larger in image, blurred); spoon returned ~f198-220, hands open f242.
- [V] Occlusion: spoon bowl hidden inside pot most of f48-176; right forearm over pot; pot handle in fist.
  Strong motion blur on spoon in most stirring frames (stirring is fast, ~1 stroke per 8-16 frames [E]).
- [E] slot-0 static start ~16-24 frames.
- Pattern [V] eps 3/5/6 are the same "pot + spoon stirring" task with varying pot motion: 3 = pot stays
  on table, 5 = pot lifted high, 6 = pot lifted slightly. Method must not assume either.

### Eval 8 (219 f, 11.0 s; slots: 0 beige_cup, 1 white_pot; no public twin task "pour cup into pot")
- [V] Task looks like "pour from beige cup into pot" (twice): f0-8 hands open; LEFT hand grips pot handle
  ~f16-24 and holds it all clip; RIGHT hand reaches cup ~f32-40, grasps ~f44, lifts ~f52-56 (cup high above
  table, near horizon line), tilts it to ~upside-down over pot f64-80 (pour), back upright ~f88-96 near
  table, second pour ~f139, cup held up again ~f159, set down ~f178-198 near its start spot; hands open f218.
- [V] Pot (slot 1) is also moved by the left hand: rotated/slid early and lifted/tilted toward camera ~f104-120.
- [V] Occlusion: cup body largely inside right fist during carrying (fingers wrap the cylinder); cup mouth
  inside/over pot rim during pours; pot handle in left fist.
- [E] slot-0 (cup) static start ~44-50 frames. Cup is a plain cylinder: yaw about its axis is
  observable only from the small black marker balls / subtle texture [H].
- Risks [H]: inverted-cup pose (bottom up) far from any public cup trajectory prior; two moving objects
  simultaneously (bimanual); cup partially above the table against cluttered background.

### Eval 10 (161 f, 8.0 s; slots: 0 blue_cup, 1 beige_cup; twin task Cup_Stack = public 11)
- [V] f0-8 hands open; BOTH hands grasp at ~f16-24: LEFT hand on blue cup (slot 0), RIGHT on beige cup.
  Beige cup lifted ~f40 (blurred), raised high and over the blue cup ~f48-56 (near image top, against
  floor/background), lowered INTO the blue cup f56-88 (nested stack); right hand releases ~f104,
  left hand releases ~f120-131; final stack stands near the blue cup's start spot (f131-160).
- [V] Left hand wraps the blue cup during stacking (f24-120): blue cup heavily occluded by fist plus the
  beige cup inserted from above. [E] blue cup mainly held for stabilisation (displacement <~2-3 cm,
  head motion makes it hard to judge); public twin 11 had blue cup never moving >=1 cm.
- [V] Nested state: beige cup bottom hidden inside blue cup; only the beige rim/upper body visible.
- [E] slot-0 static start: at least ~16-24 frames (until grasp); possibly near-static all clip.
- Risks [H]: nested cylinders (blue mostly occluded by beige + hand at end), cup axial-yaw ambiguity,
  short clip (8 s) so little multi-view of each object.

### Eval 14 (158 f, 7.9 s; slots: 0 blue_cup, 1 plastic_dish_rack; twin task Cup_In_Dish_Rack = public 12/13)
- [V] Blue cup upright on table in front of the white rack (rack long axis left-right, drainer tower at left).
  f0-8 hands open; LEFT hand grasps cup ~f16, lifts + tilts it ~f24-32; HAND-OVER to right hand f40-56
  (both hands on cup at f40-48, cup horizontal); right hand carries it high over the rack ~f56 (cup
  horizontal, against floor background), rotates it bottom-up f64-80, places it INVERTED on a rack slot at
  the rack's right end ~f88-112 (left hand guides with watch-wrist hand), releases ~f120; static after.
- [V] Rack (slot 1) appears static throughout (consistent with public 12/13 where rack never moved >=1 cm).
- [V] Background: a seated person's leg/arm visible at left image edge f0-f40.
- [E] slot-0 static start ~16 frames. Total ~180 deg flip of the cup within ~2 s; brief blur f80.
- Risks [H]: hand-over (contact switches hands), cup inside rack slot partially occluded by rack walls
  at end, cylinder yaw ambiguity; final pose depends on exact rack-slot geometry (sim must place cup on peg).

### Eval 15 (166 f, 8.3 s; slots: 0 plastic_dish_rack, 1 wooden_spoon; no public twin with spoon)
- [V] Task looks like "put spoon into the rack's utensil tower": spoon lies flat on table in front of the
  rack; f0 hands open; RIGHT hand picks spoon by the handle ~f15-30; HAND-OVER to LEFT hand ~f45 (both
  hands on spoon); left hand raises spoon high toward upper-left ~f60 (spoon near left image edge, in front
  of the seated second person), turns it handle-down and inserts handle into the drainer tower at the rack's
  left end ~f75-105; released ~f110-120; spoon then stands bowl-up in the tower, static to f165.
- [V] Right hand rests on / steadies the rack front ~f60-105. Rack (slot 0) [E] static or nearly static all clip
  (contact only); public rack trajectories never moved >=1 cm.
- [V] Occlusion: spoon handle hidden inside tower at end (only bowl + top of handle visible); during the
  carry the spoon crosses the second person's arm/torso (distractor skin + green shirt behind).
- [E] slot-0 static start: >= ~60 frames, likely whole clip. Static anchor is good here.
- Risks [H]: second person in background (hand/arm distractors for hand pose); spoon end pose is set by the
  tower geometry (sim needs accurate rack collision to keep spoon upright); spoon roll ambiguity.

### Eval 16 (173 f, 8.6 s; slots: 0 plastic_dish_rack, 1 wooden_spoon; same task/scene as eval 15)
- [V] Spoon flat on table in front of the rack; f0 hands open; RIGHT hand grasps spoon handle ~f16-31;
  both hands on spoon ~f47-63 (spoon rotated to vertical, regrasp); RIGHT hand carries it vertically above
  the tower ~f78 and inserts handle-down ~f94-125 (fine adjustment, fingers around tower top); released
  ~f135-141; spoon stands bowl-up in tower to f172. Head turns left ~f47-125 (rack at image centre/right).
- [V] Second person (green shirt, jeans, seated) occupies most of the LEFT third of the image f47-172
  with his own hands visible in his lap -> strong hand/skin distractor next to the workspace.
- [E] Rack (slot 0) static or nearly static all clip (touched by insertion only); static start >= ~90 frames.
- [V] Variation vs 15: in 15 the LEFT hand inserts after a hand-over, in 16 the RIGHT hand inserts after a
  two-hand regrasp. Method must handle either hand and hand-overs.

- [V] Grasp-window crops (up/e5_grasp_crop.png, up/e6_grasp_crop.png, frames 8-44, table region): in 5 and 6
  the left hand closes on the pot handle at ~f16-20; any pot motion f20-40 is at most a few cm / ~20 deg and
  cannot be resolved by eye under head motion. Treat only f0-~16 as certainly static for 5/6.
- [V] All 20 eval ego_cam_a clips present and complete, 15-45 MB each (not ~11 MB); no .part leftovers.

## Stage A synthesis: eval 1,3,5,6,8,10,14,15,16 (design needs; no per-episode labels for inference)
| ep | slot0 (anchor) | slot1 | task (inferred) | slot-0 static start [E] | hands | hard parts |
|---|---|---|---|---|---|---|
| 1 | white_pot | lid | lid off, pot lifted+waved, lid back | ~45-125 f (lift ~f127) | L pot, R lid | white-on-white, pot airborne+blur |
| 3 | white_pot | spoon | stir, pot held on table | >=50 f, maybe all clip | L pot, R spoon | spoon inside pot, blur |
| 5 | white_pot | spoon | stir, pot lifted high near camera | ~16-20 f | L pot, R spoon | short anchor, near-camera pot |
| 6 | white_pot | spoon | stir, pot tilted/raised slightly | ~16-20 f | L pot, R spoon | short anchor, spoon blur |
| 8 | beige_cup | white_pot | pour cup into pot x2 | ~44-50 f | R cup, L pot | cup inverted, both objects move |
| 10 | blue_cup | beige_cup | stack beige into blue | >=16-24 f, maybe ~static | L blue, R beige | nested cups, heavy occlusion |
| 14 | blue_cup | dish_rack | cup flipped into rack slot | ~16 f | L->R hand-over | hand-over, 180 deg flip |
| 15 | dish_rack | spoon | spoon into rack tower | likely all clip | R->L hand-over | 2nd person distractor |
| 16 | dish_rack | spoon | spoon into rack tower | likely all clip | R (two-hand regrasp) | 2nd person fills left third |

Cross-episode findings and design needs:
1. [V] Every clip starts with both hands raised open for ~0.4-0.8 s and ends with hands open/released. [H] An
   automatic "hands-open" detector (or first-contact detector) can bound the guaranteed static prefix per
   object; but in 5/6/10/14 the anchor object is grasped by ~f16-20, so the frame-0 anchor pose must come from
   <=1 s of static frames (or from the end-state/back-propagated track).
2. [V] Large, continuous head motion (table shifts up to ~1/4 image height between samples) -> camera ego-motion
   must be solved per frame; static background is feature-rich (truss, hazard tape, floor markings, cages).
3. [V] Bimanual manipulation is the norm (1,3,5,6,8,10); hand-overs in 14, 15, 16. Contact/hand assignment must be
   per segment, not per episode, and the policy reference must tolerate grasp switches.
4. [V] Objects stay inside the frame in eps 1-16 (no full exits seen in samples), but often move above the table
   edge against floor/cage background, and come close to the camera (5, 6) -> large scale change + defocus.
5. [V] Motion blur is frequent on fast objects (spoon strokes, lifted pot, lifted cups) at 20 fps; [H] tracking
   should use temporal smoothing/interpolation across blurred frames rather than per-frame re-detection only.
6. [V] Occlusion types: hand-in-fist (pot handle, cup body), object-in-object (spoon in pot, cup in cup, spoon handle
   in rack tower), forearm across object. End states of 14/15/16 are partially hidden by rack walls.
7. [V] Extreme orientations: inverted cup (8 pour, 14 flip), vertical spoon (3,5,6,15,16). Priors from public
   twins only cover pot/lid (1), cup stack (10), cup-in-rack (14); spoon tasks (3,5,6,15,16) and pour (8) have no
   public twin (spoon also has no scan; cf. 10-synthesis, 13-spoon).
8. [V] Background people: a seated second person (green shirt) in 14 (edge), 15 and 16 (large) -> hand detector
   must reject non-ego hands (e.g. by arm entry from image bottom / ego-arm continuity).
9. [V] Lighting is uniform bright overhead across all nine; specular floor; white pot/lid/rack are low-texture and
   near-saturated on top surfaces; mocap marker balls (black/grey, ~1 cm) are visible on all objects
   ([H] usable as automatic texture, but they are not on the public scans' textures? to check).
   -> [V] checked sheets/mesh_cups.png (earlier point-sample render of public scans): the marker spheres ARE part
   of the scanned geometry (blue cup: 4 spheres, 2 near rim + 2 near base at different azimuths; beige cup: 3-4
   spheres near base/rim; lid: 4 spheres on top). So cup/lid yaw is in principle observable from marker
   positions; [H] marker-aware template matching (small dark spheres) could break the cylinder/lid symmetry.
10. [V] The task context says "rotate 180"; for the stored files this is WRONG (Progress 1/2): stored ego_cam_a
   frames are already upright and the calibration matches them as stored. Any pipeline must not re-rotate.

Stage A status: COMPLETE for eps 1,3,5,6,8,10,14,15,16 (artifacts: work/15/up/e<ep>_even12.png,
up/e<ep>_onset.png (f0-120 step 8), up/e1_mid.png (f112-187 step 5), up/e5_grasp_crop.png, up/e6_grasp_crop.png).
Next stage (not done here): same survey for 19,20,25,28,30,32,33,35,36,37,38 (12-frame sheets already exist in up/).

## Progress 5 (Stage B started 2026-10-05: eval 19,20,25,28,30,32,33,35,36,37,38)
- Slots (kit json): 19 mini_sweeper,mini_dust_pan | 20 blue_cup,water_pitcher | 25 wooden_piece_1,wooden_piece_2 |
  28 plastic_dish_rack,white_pot | 30 mini_sweeper,plastic_dish_rack | 32/33 blue_cup,wooden_spoon |
  35/36/37 wooden_spoon (solo) | 38 mini_dust_pan (solo).
- Public twins: 19<->18 Dust_Brush; 20<->21/22 Water_Can_Blue_Cup; 25<->23/24 Planter_Stand; 28<->26/27
  Pan_In_Dishrack; 30<->31 Brush_Dishrack; 38<->39/40 Dustpan_Solo; 32/33 (cup+spoon) and 35/36/37 (spoon solo): NO twin.
  Public ego_cam_a already local: 0,11,12,13,18,21,22,23,26,31,39,41 (no download needed for twins).

### Eval 19 (235 f, 11.7 s; slots: 0 mini_sweeper, 1 mini_dust_pan; twin Dust_Brush = public 18)
- Sheets: up/e19_even12.png, up/e19_onset.png (f0-120 step 8, upright).
- [V] Scene: round wooden table; yellow-green triangular dustpan (ring handle toward camera, grey rubber lip
  away) left/centre; small wooden mini sweeper (ring-shaped wooden handle + short bristles) standing on its
  bristles at table right. Same truss/hazard-tape background as Stage A.
- [V] NO raised-open-hands prefix: at f0 both hands are already moving in (left hand blurred at lower left).
  LEFT hand grips the dustpan ring handle at ~f8; RIGHT hand grips the sweeper at ~f12-16 and lifts it by f24;
  dustpan is yawed ~45 deg on the table f16-32 while held.
- [V] Sweeping: f40-106 repeated brush strokes toward/into the dustpan (sweeper blurred, mostly inside the
  right fist; bristles occasionally on the dustpan surface); dustpan lifted and tilted toward the left image
  edge ~f112-128 and ~f149 (dump/tilt gesture, the dustpan partly leaves the table region), back on the table
  ~f170; sweeper still held in the right hand at the last frame f234 (not released; the left hand is open).
- [E] slot-0 (sweeper) static start only ~10-15 frames (grasp ~f12-16). Public twin 18 GT onset is 39 f.
- Risks [H]: tiny sweeper mostly hidden in the fist (handle ring + bristles visible only as a few pixels
  between fingers) -> pose of slot 0, the alignment anchor, is weakly observed during the whole manipulation;
  frame-0 anchor pose from <1 s of static frames; the end state has the object still in hand.
- [V] Public twin 18 (up/p18_even12.png): same table layout; hands raised open at f0 (unlike eval 19); right hand
  grasps sweeper ~f32 (GT onset 38); dustpan tilted toward left ~f128 (dump); sweeper held/re-stood at table right
  for f192-352 with the hand still on it. GT (work/15/twin_motion.py -> twin_motion.out): sweeper dmax 13.9 cm,
  end 2.6 cm from start, lift 7.9 cm, rot max 46 deg; dustpan dmax 19.5 cm, lift 15.9 cm, rot max 67 deg, end 2.4 cm.
  [E] Eval 19 looks like the same script but faster/earlier (grasp ~f12-16 vs f32-38, 235 vs 353 frames).
- [V] Twin GT motion summary (twin_motion.out; dmax/lift/rotmax per object): 21/22 blue_cup 9.9/8.2 cm/39 deg,
  water_pitcher 32/32 cm/92 deg; 23/24 wooden pieces dmax 16-27 cm, lift 13-24 cm, rot ~100 deg, end ~15-18 cm away
  (placed, not returned); 26/27 rack static (<=0.4 cm, 1 deg), white_pot dmax 20-39 cm, lift 18-30 cm, rot 180 deg
  (pot flipped into rack); 31 sweeper dmax 15.6 cm/rot 34 deg, rack static; 39/40 dustpan dmax 27-39 cm, lift 27 cm,
  rot 89-109 deg.

### Eval 20 (202 f, 10.1 s; slots: 0 blue_cup, 1 water_pitcher; twin Water_Can_Blue_Cup = public 21/22)
- Sheets: up/e20_even12.png, up/e20_onset.png.
- [V] f0: LEFT hand already holds the blue cup (slot 0, the anchor) in the air at the table's left edge, tilted;
  white watering-can "water_pitcher" stands upright on the table centre. RIGHT hand reaches ~f8, grips the
  pitcher handle ~f16-24, lifts it ~f32-40, raises it HIGH and CLOSE to the camera f48-96: pitcher fills 1/3-1/2
  of the image and is TRUNCATED by the top/right image border (the gripping hand itself is out of frame);
  spout tilted down toward the cup (pour gesture) f56-96; pitcher lowered ~f104-112 and set back upright at
  the table's right ~f128-146 (right hand releases ~f150). Cup held in the left hand until ~f150-160, then set
  on the table's left edge; both hands open f164-201 (static end ~40 frames).
- [V] Cup is moved/tilted in hand all the way through f0-150 (it is the pour target, held up to the spout).
- [E] slot-0 static start: ZERO (in hand at f0). The only static window of the anchor is the END (~f160-201).
- [V] Pitcher: large, white, low-texture, with black marker balls; near-camera -> strong perspective/defocus
  and blur f48, f96; partial out-of-frame (top edge) f48-96. Spout is thin and long (accurate yaw from spout).
- Risks [H]: (1) frame-0 anchor pose must come from an in-hand, moving, partially fist-occluded cup -> any
  frame-0 error propagates to all frames via the scorer's single rigid alignment; consider estimating the
  cup's pose on the static END segment and propagating back through the track (backward smoothing);
  (2) pitcher truncation at the image border needs a tracker that accepts partial silhouettes / does not
  re-initialise when the object is cut; (3) cup yaw from markers only.
- [V] Twin 21 (up/p21_even12.png): same script, but f0 has hands raised open and the cup RESTING on the table
  (cup grasp ~f33, GT onset 33-37); the pitcher is also truncated by the top border f50-84 and the gripping hand
  is out of frame there -> public 21/22 are good development cases for partial-view pitcher tracking with GT.
  [H] Eval 20 looks trimmed at the start (begins ~1.5-2 s later in the script than 21); so an eval clip can
  begin mid-manipulation, and the method must not assume a resting anchor at f0.

### Eval 25 (356 f, 17.8 s; slots: 0 wooden_piece_1, 1 wooden_piece_2; twin Planter_Stand = public 23/24)
- Sheets: up/e25_even12.png, up/e25_onset.png.
- [V] Two flat bamboo boards (each with a half-length slot and 4 black marker balls at the corners) lie flat
  side by side on the table. f0-24 hands raised open. LEFT hand grips the LEFT board ~f32, slides it over the
  table's left edge ~f48-56, lifts and tilts it f64, both hands turn it on edge (vertical) f72-129 -> board seen
  nearly EDGE-ON (a thin line) for long stretches; it is stood upright on the table ~f129-161. RIGHT hand takes
  the RIGHT board ~f161, lifts/rotates it f194, and the two boards are slotted together into a cross
  (halving joint) f226-323 with many fine adjustments; hands open at f355 with the cross standing on the table.
- [V] Background people: a standing person (jeans, top-left, legs/feet) and a seated person (green shirt) at
  the left image edge for the whole clip; the standing person's legs move.
- [E] Right board static until ~f155-160; left board static until ~f30.
- Risks [H]: (1) IDENTITY: the two boards look almost identical in the video -> slot assignment must use a
  rule (e.g. which board moves first / board-specific geometry); a swap would give a large error on both slots;
  (2) thin planar boards seen edge-on -> silhouette degenerate; (3) final interlocked state with ~0 clearance
  needs exact sim placement (penetration/instability risk in physics); (4) moving background person.
- [V] Twin 23 (up/p23_even12.png): same script and layout (left board picked first ~f29, stood on edge, right
  board slotted in ~f177-265, cross standing at end). GT: piece_1 onset f19, piece_2 onset f125 -> [E] left
  board = wooden_piece_1 = slot 0 in both 23 and eval 25.
- [V] Identity is resolvable (up/boards_f0_e25_p23.png full-res f0 crops; work/15/board_ascii.py on the scans):
  boards are I-shaped with notched ends and a half slot; the LEFT board has 4 corner marker balls and a stamped
  circled "1" near its lower right corner; the RIGHT board has an asymmetric 3-ball layout (top-middle, right side,
  bottom) and a circled "2". The scans agree: piece_1 has 4 corner balls, piece_2 an asymmetric ball layout.
  Eval 25 f0 layout is identical to public 23 f0 (board 1 left, board 2 right). [H] Use the marker-ball layout
  (from the scan) to fix identity automatically; never assign by image position.

### Eval 28 (220 f, 11.0 s; slots: 0 plastic_dish_rack, 1 white_pot; twin Pan_In_Dishrack = public 26/27)
- Sheets: up/e28_even12.png, up/e28_onset.png.
- [V] White dish rack (slot 0) at the back of the table, long axis left-right, utensil tower at its LEFT end;
  white pot (slot 1) in front of it, handle toward lower-left. f0 hands open (left hand already moving in).
  LEFT hand grips pot handle ~f8, lifts it toward the camera f24-40 (pot large in image, blur f32); HAND-OVER
  L->R f48-64 (both hands on the handle); RIGHT hand raises the pot to the upper right f72-120 (against the
  floor background, pot touches/crosses the TOP image border ~f96-120), rotates it ~180 deg (interior ->
  bottom facing camera) f104-139, places it UPSIDE DOWN on the rack's right half ~f150-160, adjusts it
  f160-200, releases ~f210; hands open f219.
- [E] Rack (slot 0, anchor) static all clip (only the pot touches it); public 26/27 rack moved <=0.4 cm/1 deg.
  So the anchor has a long static window -> good alignment case, provided the rack pose itself is accurate.
- Risks [H]: white rack + white pot (white-on-white, low texture; pot rests ON the rack at the end so their
  silhouettes merge); 180-deg flip in mid-air with border truncation; hand-over; final inverted pot on rack
  slats needs correct sim contact (the scored trajectory is simulated, the pot must stay on the rack).
- [V] Twin 26 (up/p26_even12.png) is the REVERSE direction: pot starts inverted on the rack, is lifted off,
  flipped upright and placed on the table (GT pot z 0.688 -> 0.645), with the LEFT hand steadying the rack's
  tower. Twin 27 is the same direction as eval 28 (GT pot z 0.645 -> 0.688, table -> rack); only its ego_cam_b
  is local. Both twins: pot rot 180 deg, lift 18-30 cm; rack <=0.4 cm.
- [V] Twin 27 via ego_cam_b (up/p27b_even12.png; the stored mono cam_b frames are also upright): same
  table->rack direction as eval 28, but single-handed (RIGHT hand grips ~f22, lifts f67-134, flips, sets the
  pot inverted on the rack's right half ~f156-200, release ~f223); a standing second person at the left edge.
  In cam_b the lifted pot stays inside the frame (cam_b has a wider vertical view) [E] -> [H] when the colour
  view truncates an object at the top border, the mono stereo views may still see it; use them as fallback.
  Variation vs eval 28: eval 28 adds a L->R hand-over.

### Eval 30 (263 f, 13.1 s; slots: 0 mini_sweeper, 1 plastic_dish_rack; twin Brush_Dishrack = public 31)
- Sheets: up/e30_even12.png, up/e30_onset.png.
- [V] Rack fills the table width (tower at LEFT end); the mini sweeper (slot 0, the anchor) stands upright
  between the rack's plate dividers near the middle (bristles down, wooden ring up; lower half hidden by the
  dividers). f0 hands open; LEFT hand grips the rack tower ~f8-16 and holds it for the whole clip; RIGHT hand
  reaches ~f24, grips the sweeper ~f32, lifts it out f40-56, scrubs the rack's RIGHT end (slats/drain lip)
  with repeated short strokes f64-170 (sweeper mostly in the fist, bristles against white rack), returns it
  between the dividers near its start slot ~f190-240, releases ~f250; hands open f262.
- [E] slot-0 static start ~28-32 frames; the rack is held (stabilised) by the left hand -> [E] static or <1 cm.
- Risks [H]: sweeper start/end poses are inside the divider comb (partial occlusion by thin white fins;
  sim placement must not interpenetrate the fins); during scrubbing the sweeper is in the fist and touching
  the rack (contact-rich, small motions, little visual evidence of orientation); white rack low texture.
- [V] Twin 31 (up/p31_even12.png) is nearly the same clip: left hand on the tower from ~f26, right hand
  takes the sweeper from between the dividers, scrubs the rack's right end f53-184, re-inserts it between the
  dividers ~f210-263 (GT: end 9.2 cm from start, i.e. a different divider gap; rot max 34 deg; rack <=0.2 cm).
  [E] Eval 30 is the closest-matching eval/public pair in Stage B -> best holdout-style check for sweeper tracking.

### Eval 32 (259 f, 13.0 s; slots: 0 blue_cup, 1 wooden_spoon; NO public twin (cup+spoon "stir in cup"))
- Sheets: up/e32_even12.png, up/e32_onset.png.
- [V] f0: LEFT hand already wrapped around the blue cup (slot 0) standing at the table's left edge; right hand
  open. Cup LIFTED by ~f16 and tilted toward the camera (interior visible, near camera, larger in image);
  held in the air at the table's left edge for f16-~185. RIGHT hand grips the spoon (lying flat at table right,
  bowl up/away) ~f32-40, raises it vertical f56-64, brings it horizontally to the cup f72 (blur), stirs with the
  bowl INSIDE the tilted cup f80-160 (spoon handle across the image, cup mouth turned toward the spoon),
  withdraws it ~f164, cup back on the table ~f185-190 (left hand stays on it), spoon laid back on the table
  ~f211-235, hands open f258.
- [V] The spoon carries 3 black marker balls (bowl-handle junction, mid-handle, handle tip) -> [H] usable to
  resolve spoon roll/yaw and to measure its length automatically (the spoon has no public scan).
- [E] slot-0 static start: 0 frames (cup in hand at f0, lifted ~f10-16). Static END ~f190-258 (hand on cup
  until ~f240).
- Risks [H]: anchor never free at f0 (same issue as eval 20); spoon bowl hidden inside the cup; cup held
  tilted off the table edge (sim must hold a cup in mid-air via the hand policy from frame 0).

### Eval 33 (348 f, 17.4 s; slots: 0 blue_cup, 1 wooden_spoon; same task as eval 32, no public twin)
- Sheets: up/e33_even12.png, up/e33_onset.png.
- [V] f0-8 hands raised open, cup RESTING upright at the table's left edge, spoon flat at table right.
  LEFT hand grips the cup ~f16, lifts and tilts it toward the camera ~f24-40 and holds it in the air over the
  table's left edge until ~f300; RIGHT hand grips the spoon ~f40-48, raises it ~f56-64, stirs/taps with the
  bowl INSIDE the tilted cup in several in-out cycles f72-252 (spoon horizontal, blurred in many frames,
  waved above the table between cycles e.g. f112-126, f189, f252); spoon laid back ~f284-315, cup back on the
  table ~f300-315, hands open f347.
- [E] slot-0 static start ~12-16 frames (grasp ~f16). Static end ~f315-347.
- [V] Variation 32 vs 33: 32 starts with the hand already on the cup (no free start), 33 has a ~0.8 s free start.
  Cup orientation in the air varies a lot (tilted 30-60 deg toward the camera, mouth facing the spoon).
- Risks [H]: same as 32; additionally, long clip with many fast spoon strokes (blur) -> spoon-track continuity.

### Eval 35 (421 f, 21.0 s; slot: 0 wooden_spoon (solo); no public twin, spoon has no scan)
- Sheets: up/e35_even12.png, up/e35_onset.png.
- [V] Spoon lies flat on the table (bowl upper-left, handle lower-right, 3-4 black marker balls on handle/neck).
  f0-8 hands open; RIGHT hand grips the handle end ~f16-24, lifts ~f32; both hands f40-56 (hand-over R->L);
  LEFT hand holds it near the bowl with the handle pointing up/away f64-104 (spoon nearly along the viewing
  direction, foreshortened, handle above the table against the floor); two-hand regrasp f112-120; then
  repeated hand-to-hand passes and in-hand reorientations (vertical bowl-up in R hand f153, horizontal in both
  hands f191-229, diagonal R f267-305, both f344), set down by the LEFT hand ~f382; static f400-420 with the
  spoon rotated ~120-150 deg in yaw relative to its start (bowl now at left).
- [E] slot-0 static start ~16 frames; static end ~20-35 frames. Task = "spoon hand-to-hand reorientation" [E].
- Risks [H]: (1) >=4 hand-overs / regrasps -> grasp-switch handling dominates the policy; (2) spoon often seen
  end-on (foreshortened) -> depth/axis ambiguity, use stereo; (3) symmetric bowl -> roll ambiguity resolved only
  by marker balls; (4) frame-0 pose of the ONLY object = the alignment anchor; mesh frame convention for our own
  spoon reconstruction must match what the scorer expects (cf. note 07).

### Eval 36 (407 f, 20.3 s; slot: 0 wooden_spoon (solo); no public twin)
- Sheets: up/e36_even12.png, up/e36_onset.png.
- [V] Spoon flat near the table's back edge (bowl left, handle right). f0-8 hands open; RIGHT hand grips the
  handle ~f24-32, lifts ~f40 (blur), turns it bowl-up vertical f48-64, then waves/twirls it: horizontal and
  pointing AWAY from the camera f72-120 (strongly foreshortened, bowl beyond the table edge against the floor,
  sometimes nearly end-on); left hand idle and open f0-~200. Hand-over R->L ~f210-225; LEFT hand holds it
  vertical bowl-up f221-258; both hands f295; RIGHT hand vertical f332; laid on the table ~f360-370 (yaw ~30 deg
  different from start, closer to the camera); hands open f406.
- [E] slot-0 static start ~20-24 frames; static end ~30-40 frames.
- Risks [H]: long single-object clip with fast twirls (blur) and end-on views; hand-over; same spoon-mesh issue.

### Eval 37 (151 f, 7.5 s; slot: 0 wooden_spoon (solo); no public twin)
- Sheets: up/e37_even12.png, up/e37_onset.png.
- [V] Simplest Stage-B clip: spoon flat across the table (bowl left, handle right). f0-8 hands open; RIGHT hand
  touches ~f16, grips the handle ~f24-32, lifts ~f40 (blur), holds it roughly level and high above/behind the
  table's back edge f48-64 (spoon against the floor/truss background, [E] ~20-30 cm above the table), lowers and
  lays it back ~f72-88 close to its start pose, keeps the hand on it to ~f104 (small slide/adjust [E]), releases
  ~f108-112; static f112-150. Left hand idle/open the whole clip; no hand-over, no large rotation.
- [E] slot-0 static start ~16-24 frames; static end ~40 frames; end pose within a few cm/deg of the start [E].
- Risks [H]: low; good "sanity" case for the spoon pipeline (mesh, scale, lift height from stereo).

### Eval 38 (263 f, 13.1 s; slot: 0 mini_dust_pan (solo); twin Dustpan_Solo = public 39/40)
- Sheets: up/e38_even12.png, up/e38_onset.png.
- [V] Dustpan lies flat at the table centre (ring handle toward the camera, grey lip away). f0-16 hands open;
  RIGHT hand reaches f24-32, grips the ring handle ~f36-40, lifts f48-56 and holds it HIGH above/behind the
  table's back edge f56-80, rotating it (lip turned to the left, nearly edge-on/vertical at f80); lowers it at
  the table's right f88-96 (lip left), slides/sets it ~f96-120; a second lift/tilt (scoop-like) f143-191 above
  the back edge; final placement ~f214-238 rotated ~90 deg in yaw from the start (lip left, handle right);
  release ~f240; static to f262. Left hand idle/open throughout; single-hand.
- [E] slot-0 static start ~32-36 frames; static end ~20 frames.
- [V] The dustpan is bright yellow-green, strongly textured relative to the table -> easy segmentation; the
  thin plate seen edge-on (f80) and the hand around the ring are the main pose risks.
- [V] Twin 39 (up/p39_even12.png): same start layout (dustpan at table centre, ring toward camera) but a
  different script: LEFT hand grips ~f40 (GT onset 48), hand-over L->R ~f87, several lifts, the dustpan is
  carried to the RIGHT image border and partly TRUNCATED at f231, then returned near its start (GT end 8.5 cm,
  28 deg). Eval 38 is right-hand-only and ends ~90 deg yawed -> same objects/scene, different trajectory; the
  public twin is useful for appearance/tracking checks, not as a trajectory prior.
- [V] Eval 20 truncation vs mono cameras (up/e20_cama_lift.png, e20_camb_lift.png, e20_camc_lift.png, frames
  48-104): in ego_cam_b/c the lifted pitcher is much less truncated and the RIGHT hand gripping its handle is
  visible at the top right (f56-f88), whereas in ego_cam_a the handle and hand are cut off. The mono views also
  show a SEATED SECOND PERSON at the left (on a chair, own hands visible) who is outside the colour view.
  Pinhole FOV from the calibration K (distortion ignored, [E]): cam_a ~83 x 67 deg (fx 1150 @2028x1520),
  cam_b/c ~97 x 70 deg (fx ~565 @1280x800). [H] Track lifted/near objects in the stereo pair whenever the colour
  view truncates them, and apply the non-ego-hand rejection to the mono views too.

## Stage B synthesis: eval 19,20,25,28,30,32,33,35,36,37,38 (design needs; no per-episode labels for inference)
| ep | frames | slot0 (anchor) | slot1 | task (inferred) | f0 state | slot-0 static start [E] | static end [E] | hands | public twin | hard parts |
|---|---|---|---|---|---|---|---|---|---|---|
| 19 | 235 | mini_sweeper | mini_dust_pan | sweep into dustpan, dump | hands already moving in | ~10-15 f | none (sweeper still in hand) | L pan, R sweeper | 18 (same script, slower) | tiny anchor in fist |
| 20 | 202 | blue_cup | water_pitcher | pour pitcher into held cup | cup IN HAND, tilted | 0 f | ~40 f | L cup, R pitcher | 21/22 (start trimmed) | anchor never free at f0; pitcher cut by top border |
| 25 | 356 | wooden_piece_1 | wooden_piece_2 | slot two boards into a cross | hands open | ~30 f | ~30 f | L then R, both | 23/24 (same) | twin boards identity; edge-on; interlock |
| 28 | 220 | dish_rack | white_pot | pot flipped upside-down onto rack | L hand moving in | all clip (rack) | all clip | L->R hand-over | 27 (same dir.), 26 (reverse) | white-on-white; mid-air 180 deg flip; top-border cut |
| 30 | 263 | mini_sweeper | dish_rack | scrub rack with sweeper, re-stand it | hands open | ~28-32 f | ~15-25 f | L holds rack, R sweeper | 31 (near-identical) | sweeper among divider fins |
| 32 | 259 | blue_cup | wooden_spoon | stir spoon in held cup | L hand ON cup | 0 f (lift ~f10-16) | ~20-70 f | L cup, R spoon | none | anchor never free at f0 |
| 33 | 348 | blue_cup | wooden_spoon | stir spoon in held cup | hands open | ~12-16 f | ~30 f | L cup, R spoon | none | many fast strokes |
| 35 | 421 | wooden_spoon | - | hand-to-hand spoon reorientation | hands open | ~16 f | ~20-35 f | R->L, many passes | none | >=4 regrasps; foreshortening |
| 36 | 407 | wooden_spoon | - | spoon twirl + hand-over | hands open | ~20-24 f | ~30-40 f | R, R->L, R | none | twirls, end-on views |
| 37 | 151 | wooden_spoon | - | lift spoon and lay it back | hands open | ~16-24 f | ~40 f | R only | none | low (sanity case) |
| 38 | 263 | mini_dust_pan | - | lift/turn dustpan, place yawed ~90 deg | hands open | ~32-36 f | ~20 f | R only | 39/40 (same objects, other script) | edge-on plate |

Cross-episode findings and design needs (Stage B; extends the Stage A list):
1. [V] 3/11 Stage-B clips start mid-action: 19 (hands already reaching, grasp ~f8-16), 20 (cup already lifted in
   the left hand), 32 (left hand already on the cup). Combined with Stage A, the "hands raised open at f0" pattern
   holds in 16-17/20 clips, not all (28 is borderline: right hand open, left hand already moving in at f0;
   grasp ~f8). In 20 and 32 the alignment anchor has NO static start at all. [H] Design need:
   estimate the anchor's frame-0 pose from the tracked trajectory (best-observed or static END segment, propagated
   backward), not from an assumed resting start; quantify on public twins by artificially trimming their starts.
2. [V] Anchor (slot 0) categories: large static rack all clip (28; also 15/16) = easiest; small hand-hidden sweeper
   (19, 30); in-hand cup (20, 32, 33); the spoon itself (35, 36, 37, also anchor-free spoon in 3/5/6/15/16/32/33 as
   slot 1); dustpan solo (38); board 1 (25). Anchor accuracy needs differ by category.
3. [V] Out-of-frame truncation appears in Stage B (unlike Stage A): eval 20 pitcher (top/right border, f48-96, its
   gripping hand outside cam_a), eval 28 pot touches the top border f96-120; twin 39 dustpan at the right border.
   The mono pair sees more (wider horizontal FOV) -> [H] multi-camera tracking as a fallback for truncation.
4. [V] Two near-identical objects (25: wooden_piece_1/2) are distinguishable by marker-ball layout (4 corners vs
   asymmetric 3) and stamped numerals; [H] assign identity via scan-specific marker layout, never by image position.
5. [V] Hand-overs/regrasps: 28 (L->R), 35 (>=4 passes), 36 (R->L); stabilising holds: 30 (left on rack), 19/20/32/33
   (one object per hand). Single-hand: 37, 38.
6. [V] Background people: 25 (standing person with moving legs at top-left + seated person at left edge, whole clip);
   20 (seated person visible only in the mono views); 27 twin (standing person). [H] non-ego-hand rejection is needed
   in both colour and mono streams.
7. [V] Degenerate views: thin boards edge-on (25), dustpan plate edge-on (38 f80), spoon end-on/foreshortened (35, 36).
   [H] stereo depth and temporal priors are required where the silhouette collapses.
8. [V] (kit json) The wooden_spoon appears in 10/20 eval episodes (3,5,6,15,16,32,33,35,36,37) and is the ONLY
   object/anchor in 35/36/37; it has no public scan and no public twin trajectory. It carries 3-4 black marker balls
   (neck, mid-handle, tip). The spoon mesh (sim asset + CD-O) and its frame convention are the largest single
   dependency of the eval set.
9. [V] Contact-critical end states for the simulated policy: 25 interlocked cross, 28 inverted pot on rack slats, 30
   sweeper standing between divider fins, (Stage A: 14 cup on rack slot, 15/16 spoon in tower, 10 nested cups).
10. [V] Twin usefulness ranking for Stage B: 30<->31 (near-identical) > 25<->23/24, 28<->27, 20<->21/22, 19<->18 (same
   scripts, timing differs) > 38<->39/40 (same objects, different script) > none for 32/33/35/36/37.
11. [V] Durations 151-421 frames; 35/36 are the longest clips of the eval set (~21 s), with continuous manipulation.

Stage B status: COMPLETE for eps 19,20,25,28,30,32,33,35,36,37,38. Artifacts in work/15/up/: e<ep>_even12.png,
e<ep>_onset.png (f0-120 step 8), twin sheets p18/p21/p23/p26/p31/p39_even12.png and p27b_even12.png (ego_cam_b),
boards_f0_e25_p23.png, e20_cam{a,b,c}_lift.png; scripts work/15/twin_motion.py (+ twin_motion.out),
work/15/board_ascii.py. Next stage (not done here): stage C.

## Progress 6 (Stage C started 2026-10-05: per-episode risk table -> pipeline components)
- Inputs reused: Stage A/B tables above; notes 10 (architecture P1-P12), 11 (placement priors), 12 (spin
  observability), 13 (spoon), 14 (e_track: discrete grasp failure/drop dominates, 0.3 kg sim mass, soft wrist).
- [V] Public URDFs (public/urdf/*_rigid.urdf) use the visual GLB itself as the collision mesh, mass 0.3 kg placeholder
  ("Track 3 supplies no measured physical properties"); FlashCHORD eval.yaml decomposes collision with CoACD (note 14).
  There is NO spoon URDF/mesh: the spoon sim asset (collision + inertia) is entirely ours.
- [V] Scan sizes (work/15/c/dims.py -> dims.out, thin.py -> thin.out; scan frame extents, markers included):
  cups ~100-111 x 170 mm (rim dia ~88 mm); white_pot 132x189x357 mm with a stick handle reaching 242 mm from the body
  centroid, handle end cross-section ~24x33 mm; water_pitcher 141x272x415 mm; lid 190 mm dia x 47 mm; dish rack
  117x175x510 mm; mini_sweeper 48x114x142 mm; mini_dust_pan 45x170x178 mm with a ~3-4 mm plate [E from vertex histogram];
  wooden boards 139x227 mm, plate ~8-9 mm thick [E] (26 mm incl. marker spheres). Sharpa Wave is human-sized
  (208x90x50 mm, note 04, secondary source).
- [V] Evaluator start state (note 01 C.7/C.10): frame 0, joints and object exactly at the reference, EXACT reference
  fingers, VOC 0, no hold. => whatever the hand reference does at frame 0 must already be a physically valid state.
- [V] Public-GT support classes (work/15/c/support.py -> support.out; frame "on table" = lowest scan vertex within 1 cm
  of the table plane, "moving" = >2 cm/s): substantial ON-TABLE moving (slide/pivot, non-prehensile-like) segments in
  23/24 wooden_piece_1 (68/87 and 30/97 moving frames; runs up to 7 cm), 23/24 piece_2 (runs 8-10 cm), 18 sweeper
  (64/154; 13.5 cm run = sweeping strokes on the table), 18 dustpan (57/110), 39 dustpan (45/223; one 18.6 cm slide),
  42 pot (45/165; 4 cm). Cups, pitcher and the pot in 0/2/26/27/41/43-45 are mostly airborne when moving.
  Note 01 C.8 [V code]: sim friction is 1.0 EVERYWHERE (hand-object = object-table). [E physics] So a "press on top and
  drag" slide cannot work in sim (hand friction mu*N_h < table friction mu*(mg+N_h)); slides need a lateral push on an
  edge or a full grasp, and the soft wrist (kp 25 N/m) needs ~12 cm of residual to supply the 2.9 N table friction of a
  0.3 kg object (same size as the gravity term in note 14).
- Tooling: CoACD 1.0.14 installed ONLY into work/15/c/pylib (uv --target; shared venv untouched) to test whether the
  evaluator's collision decomposition (CoACD threshold 0.05, unlimited hulls, note 01 C.8) keeps the cavities that
  eval end states need (cup interiors, rack tower/dividers/slats, board slots).
- [V] CoACD run (work/15/c/coacd_run.py -> hulls/*.npz, coacd_run.out; threshold 0.05, seed 0, other params default;
  [E] FlashCHORD's own wrapper may pass other params - assets/mesh.py not fetched): 9-73 hulls per object, 6-23 s each.
  Top-down height maps scan vs hull union at the public frame-0 rest pose (coacd_fill.py -> coacd_fill.out,
  fill_<obj>.txt; 4 mm cells): cups keep their cavity (centre cells |Delta|<=5 mm) but wall hulls bulge inward 10-25+ mm
  at some rim azimuths (18 % of plan cells >25 mm); white_pot basin floor raised 5-25 mm over most of the interior;
  dish rack: 57 % of plan cells raised >5 mm, 37 % >10 mm, 10 % >25 mm (max 74 mm), concentrated in the divider
  rows and one end; boards: slot mostly kept but partly closed near its inner end (needs finer check); dustpan/lid/
  sweeper small (<=10 mm on >90 % of cells); water_pitcher 42 % >25 mm (its opening/interior filled - irrelevant, no
  insertion into the pitcher).
- [V] Rack tower under CoACD (rack_heights.py -> rack_heights.out 12 mm blocks, rack_tower_6mm.out 6 mm): the utensil
  tower is a >10 cm walled box whose scan interior floor is 4-5 cm above the rack base (~6 cm deep cavity, ~30 mm x ~95 mm
  opening [E]); in the hull union the cavity survives but each wall is ~6 mm thicker inward and the floor 0.5-1 cm higher,
  so the opening narrows to ~18-24 mm [E] in the short direction. Basket floor raised ~1 cm, its holes closed (harmless).
  [H] For 15/16 (spoon handle ~16-20 mm into the tower) the collision tower may jam or tilt the spoon or stop it 1-2 cm
  higher than the video shows; the reference must be checked against the HULLS, not the scan.
- [V] Boards under CoACD (board_thick.py -> board_thick.out; rack_heights.py -> board1_3mm.out, board2_3mm.out): plate
  thickness 7.5 mm (piece_1) / 9.1 mm (piece_2); the halving slot is ~19 mm wide in the scan and ~16 mm in the hulls,
  ~5 mm shorter => [E] the cross interlock (eval 25) is NOT blocked by the collision decomposition (>=7 mm clearance).
- [V] GT contact states vs CoACD hulls (pen.py -> pen.out; hull-of-A surface samples inside hulls of B, every 4th frame):
  lid on pot 7.6-8.4 mm deep (eps 0/2, start and end), sweeper in rack dividers 10-15 mm (ep 31, 76 % of frames >5 mm),
  blue cup on rack 6-8 mm (12/13 end), pot on rack 7-10 mm (26 start, 27 end), beige-in-blue nest 4.6-4.9 mm (11),
  boards cross 1.3-2.9 mm (23/24), sweeper vs dustpan <=3.4 mm (18). Baseline: separated pairs give 0.0 mm. Next: a
  scan-vs-scan control to separate CoACD inflation from mocap/scan error.
- [V] Control (pen_ctrl.py -> pen_ctrl.out; A-scan points vs B-scan by KD-tree + face normals): for the RACK pairs the scan
  states are clean (cup-on-rack ep 12 f160: 1.0 mm max / p99 0.0; pot-on-rack ep 27 f216: 1.2 / 0.0; sweeper-in-dividers
  ep 31 f160: 1.3 / 0.6; ep 31 f0: 3.8 / 0.6) while the same scan points sit 5-15 mm (p99 5-8 mm) inside the rack HULLS
  => the rack interpenetration is CoACD inflation, not mocap/scan error. For lid-on-pot and nested cups the normal-sign
  control is unreliable (thin unwelded walls; reported 26-30 mm = artefact), so those two stay [E] CoACD-caused.
- [E] Consequences: (a) frame-0 states that are already in contact start INSIDE the collision model: eval 30 slot-0
  sweeper standing between the rack dividers (twin 31 f0: 10 mm) and eval 1 lid on pot (twins 0/2 f0: 7.6-7.9 mm). With
  VOC 0 and exact reset (note 01) the contact solver ejects the object at step 1 -> a slot-0 settle error in eval 30
  (note 14: 5 deg + 3 mm persistent -> AUC -0.04; 10 deg + 5 mm -> AUC 0.84, MP-SR 0.76). (b) placed end states on the
  rack (14 cup, 28 pot, 30 sweeper), lid re-seat (1) and nest (10) cannot be reached exactly; the object rests 5-15 mm
  off or wedges. [H] Fix: make references hull-aware - reproduce FlashCHORD's exact convex_decompose call offline and
  project every reference pose to non-penetration against the hulls (or supply collision meshes whose decomposition
  matches the scan, if organisers allow); verify with a frame-0 drop test in the evaluator physics.
- [V] Nest geometry (nest.py -> nest.out, public 11 = twin of eval 10): at the end the beige cup sits 30-31 mm higher than
  the blue cup (top of beige 30 mm above blue top, incl. rim markers). [E] To finish the insertion while holding it, a hand
  can only use the top ~2-3 cm band of the beige cup (rim/marker pinch), or must release above and drop it in.
