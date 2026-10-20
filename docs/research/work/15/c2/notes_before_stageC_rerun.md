# 15 — Eval video survey: risks and design needs for the 20 eval episodes (agent 15, 2026-10-05) — COMPLETE

Stages A (eval 1-16), B (eval 19-38) and C (risk table, grasp-synthesis flags, collision-asset checks) are done.
Labels: [V] verified (seen in frames, computed or read in code/data), [E] estimate, [H] hypothesis.
Rules kept: research only; eval videos viewed for method design only (no per-episode labels for inference);
public GT used only for analysis/priors; no leaderboard probing; no evaluator/physics changes; no SlamDunk code read.
Work dir: /Users/aebatirel/Documents/Code/v2d-research/work/15/ (stage A/B sheets in up/, stage C scripts and
outputs in c/). The pre-rewrite version of this note is at work/15/c/notes_before_rewrite.md.
2026-10-06 Stage B re-run: section 12 adds spot checks, corrections and automatic clip statistics (artifacts in
work/15/b2/). Section 12 supersedes section 8 on these points: eval 35 has 5 hand-overs and ends yawed ~60 deg (not
120-150); eval 36 has 2 hand-overs; eval 38 ends yawed ~65 deg (not ~90); eval 20 is probably not a trimmed twin.

## 1. Summary (most important first)

1. [V] Do NOT rotate ego_cam_a by 180 deg. The stored eval and public colour and mono videos are already upright,
   and camera_calibration.json matches the stored frames (stereo rectification test, section 9).
2. [V] The evaluator's collision model does not match the scans where contact matters. FlashCHORD replaces every
   collision mesh with CoACD hulls (threshold 0.05; note 01 C.8). With CoACD 1.0.14 at that threshold, the public GT
   contact states sit 5-15 mm inside the hulls: lid on pot 7.6-8.4 mm, cup on rack 6-8 mm, pot on rack 7-10 mm,
   sweeper between the rack dividers 10-15 mm. For the rack pairs a scan-vs-scan control gives only 0-1.3 mm, so the
   overlap comes from the hulls themselves. Eval 30's anchor (the sweeper between the dividers) and eval 1's lid
   therefore start inside the collision model at frame 0, and the evaluator resets with no VOC.
   [E] Expect the object to be ejected at step 1 and a slot-0 settle error in eval 30.
3. [E] Robot grasp synthesis (rigid grasp-and-carry, note 10 P9) likely FAILS on 8/20 eval episodes:
   14, 15, 16, 20, 25, 28, 35, 36. On 8 more (3, 5, 6, 10, 19, 30, 32, 33) the grasps themselves are feasible, but a
   tool-contact, insertion or asset segment likely fails in simulation. Only 1, 8, 37 and 38 look like plain
   grasp-and-carry. Section 3 gives the reason for each episode.
4. [V] Eval 20 starts with the slot-0 cup already held in mid-air, and eval 32 starts with the hand already on the cup.
   The evaluator starts from the exact reference fingers with VOC 0 and no hold (note 01 C.7/C.10). [E] So the frame-0
   reference grasp in 20 must hold the cup from step 0, against note 10's "contact-free frame 0" rule.
5. [V] The public twins contain long on-table moving segments (slides and pivots): boards 23/24 (piece_1: 68 of 87
   moving frames), sweeper 18 (64/154, 13.5 cm run), dustpans 18 and 39 (18.6 cm slide). Sim friction is 1.0 everywhere
   (note 01). [E physics] So "press on top and drag" cannot move an object in sim. A slide needs a lateral push on an
   edge or a full grasp, and the soft wrist needs ~12 cm of residual to overcome the 2.9 N table friction of a
   0.3 kg object.
6. [V] The rack's utensil tower survives CoACD but is narrowed: walls ~6 mm thicker inward, opening ~18-24 mm [E] vs
   ~30 mm, floor 0.5-1 cm higher. Eval 15/16 put a spoon handle (~16-20 mm) into it. The pot basin floor is raised 5-25 mm,
   and the cup walls bulge 10-25 mm inward at some rim azimuths, which affects stirring in 3/5/6/32/33. The board halving
   slot survives (16 mm in the hulls vs 9.1 mm plate), so the eval 25 cross is NOT blocked by the hulls.
7. [V] The spoon is in 10/20 eval episodes and is the only object, and so the anchor, in 35/36/37. It has no scan, URDF or
   GT, so its sim asset (collision and inertia) is entirely ours. Its roll sign is ~50/50 (notes 07/13).
8. [V] Anchor timing: the slot-0 static start is 0 frames in 20 and 32, <=1 s in 5, 6, 14, 19, 33 and 35, and the whole
   clip for the rack anchors (15, 16, 28). The frame-0 anchor pose must come from the tracked trajectory (a static end
   segment, back-propagated), not from an assumed resting start.
9. [V] Distractors and visibility: second people in 14, 15, 16 and 25 (and in the mono views of 20); identical-looking
   boards in 25 (identity from the marker layout); objects cut by the colour border in 20 and 28 (the mono pair sees more);
   edge-on or end-on views in 25, 38, 35 and 36; heavy blur on spoon strokes and lifted objects.

## 2. Stage C: per-episode risk table, mapped to pipeline components

Ratings: H = high risk of a score-relevant failure, M = medium, L = low, - = not applicable. Components:
SEG = segmentation and identity; TRK = 6-DoF tracking through grasps, occlusion, blur and truncation; STEREO = metric
depth needs; SMOOTH = world-frame smoother and slot-0 anchor (static windows, support and contact constraints);
GRASP = robot grasp synthesis vs non-prehensile or dexterous actions; SIM = collision assets and contact-critical states
under CoACD (stage C measurements, section 4); SPOON = spoon mesh, roll and markers; SYM = symmetric or ambiguous anchor
(notes 11/12). Evidence: per-episode descriptions (section 8) and section 4; ratings are [E] unless stated otherwise.

| ep | slot0 / slot1 | SEG | TRK | STEREO | SMOOTH (anchor) | GRASP | SIM | SPOON | SYM | grasp synthesis |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | pot / lid | M white-on-white, lid merges with pot | M handle in fist f28-300; pot waved with blur f132-182 | L | L static ~45-125 f | M handle power grasp (0.3 kg x ~0.2 m lever = ~0.6 N m); lid bar pinch; drags while held | H lid starts 7.6-7.9 mm inside pot hulls at f0; re-seat 8 mm | - | L pot unique; lid 2-fold broken by markers | FEASIBLE if the lid states are hull-aware |
| 3 | pot / spoon | M thin spoon at the pot rim | H spoon bowl inside pot, fast strokes | M thin spoon: marker triangulation | L pot ~static | M spoon pinch from flat (~16-20 mm handle on table); stirring = tool contact | H basin floor +5-25 mm in hulls; spoon-pot contact pushes a 0.3 kg pot | H slot 1 | L | PARTIAL (stir contact) |
| 5 | pot / spoon | M-H pot fills 1/3 of the image, defocus | H both objects move together, blur f88-104 | H pot close to camera | H static 16-20 f | H pot lifted with spoon inside while stirring (coupled contact, both hands busy) | H as 3 | H | L | PARTIAL, worst of the stirring set |
| 6 | pot / spoon | M | H spoon hidden in pot most of f48-176 | M | H static 16-20 f | M-H as 3 plus small pot lifts and tilts | H as 3 | H | L | PARTIAL |
| 8 | beige cup / pot | M beige cup vs table/skin [H] | M cup in fist, turned upside down | M cup high above table | M static 44-50 f | M cylinder wrap (88 mm) + inversion; pot handle lift/tilt | L | - | H beige near-3-fold spin, no GT prior | FEASIBLE (spin is the risk) |
| 10 | blue cup / beige cup | H nested cylinders, blue cup behind fist + beige | M-H | M | L-M blue cup near-static | M-H beige held only by its top ~2-3 cm band to finish the nest (twin 11: beige ends 30 mm above blue) | M nest 4.6-4.9 mm inside blue hulls; wall bulges | - | H blue cup spin from markers; beige near-3-fold | PARTIAL (insertion) |
| 14 | blue cup / rack | M white rack; 2nd person at edge | M-H hand-over mid-air, 180 deg flip, blur f80 | M | H static ~16 f (rack-relative yaw prior LOO 1.9 deg, note 11) | H L->R hand-over of a horizontal cup + flip + inverted placement | M-H cup on rack 6-8 mm inside hulls | - | M | LIKELY FAILS |
| 15 | rack / spoon | H 2nd person fills left third; spoon crosses his arm | M-H hand-over; spoon end hidden in tower | M | L rack static all clip | H spoon pinch from flat + R->L hand-over + handle-first insertion (grasp must be at bowl/upper handle) | H tower opening ~18-24 mm in hulls vs ~16-20 mm handle | H slot 1 | M rack anchor needs world link/geometry (note 11) | LIKELY FAILS |
| 16 | rack / spoon | H 2nd person larger, hands in lap | M-H two-hand regrasp | M | L rack static all clip | H as 15 (right hand inserts) | H as 15 | H | M | LIKELY FAILS |
| 19 | sweeper / dustpan | M tiny sweeper in fist | H anchor barely visible during strokes | M | H static ~10-15 f; no static end (sweeper still held) | M-H sweeping drags on table/dustpan (twin 18: 64/154 on-table moving frames); dustpan slid then tilted | L sweeper vs dustpan <=3.4 mm | - | M 2-fold, resolved world-free (note 11) | PARTIAL (drag strokes) |
| 20 | blue cup / pitcher | M pitcher cut by border; 2nd person in mono | H pitcher truncated f48-96 in cam a; cup moving in hand | H pitcher near camera: use mono pair | H static start 0 f; only static end ~40 f | H f0 cup in hand mid-air at reset (VOC 0); pitcher lift 32 cm / 92 deg | L | - | H blue cup; bearing prior LOO 6 deg | LIKELY FAILS (frame-0 grasp) |
| 25 | board 1 / board 2 | H identical boards: identity from marker layout; 2 people | H thin boards edge-on; fine two-hand adjustment | H edge-on 7.5-9 mm plates | M static ~30 f; end-snap prior (note 11) | H flat plate pick-up by slide/pivot to the table edge (twin 23: 68/87 on-table frames), stand on edge, slot together | L slot survives (16 mm vs 9.1 mm); cross 1.3-2.9 mm | - | M 2-fold + identity | LIKELY FAILS (non-prehensile pre-grasp) |
| 28 | rack / pot | H white pot on white rack | H 180 deg mid-air flip; top-border cut f96-120; hand-over | M-H pot near camera f24-40: use mono views | L rack static all clip | H both hands on a 24x33 mm stick handle during the hand-over; flip under ~0.6 N m handle torque (twin 26 rotation saturation, note 14) | M-H pot on rack 7 mm inside hulls | - | L | LIKELY FAILS |
| 30 | sweeper / rack | M sweeper among white fins | M-H sweeper in fist while scrubbing; hidden by fins at start/end | M | H anchor starts in divider comb; static 28-32 f | M ring grasp easy; scrubbing presses on a 0.3 kg rack held by the other hand | H anchor 10 mm inside rack hulls at f0 (twin 31), 13-15 mm at end | - | M 2-fold, resolved world-free | PARTIAL (asset/anchor) |
| 32 | blue cup / spoon | M | H spoon bowl inside cup; blur | M | H static start 0 f; static end ~f190-258 | M-H f0 hand already on cup (must not penetrate); cup held tilted mid-air ~170 f; spoon pinch; stir in cup | M-H cup wall bulges 10-25 mm in hulls | H | H blue cup, no GT prior | PARTIAL (stir contact) |
| 33 | blue cup / spoon | M | H many fast strokes | M | M-H static 12-16 f | M-H as 32 without f0 contact | M-H | H | H | PARTIAL (stir contact) |
| 35 | spoon / - | M colour fails on skin, mono on floor -> fuse | H end-on views; fists over markers | H axis depth when end-on | M static 16 f; static end 20-35 f | H >=4 hand-overs + in-hand reorientation (each switch is a chance of a discrete failure) | M own thin hulls (bowl/handle) | H anchor; roll ~50/50 | H roll | LIKELY FAILS |
| 36 | spoon / - | M | H twirls, blur, end-on | H | M static 20-24 f | H in-hand twirls + R->L hand-over | M | H anchor | H roll | LIKELY FAILS |
| 37 | spoon / - | L | M blur at lift | M lift height | M static 16-24 f; static end ~40 f | L-M pinch from flat, lift, place back | M own asset | H anchor | H roll | FEASIBLE (sanity case) |
| 38 | dustpan / - | L bright yellow-green | M plate edge-on f80 | M thin plate | M static 32-36 f | L-M ring-handle grasp; one hand; possible table slides | L | - | L handle breaks symmetry | FEASIBLE |

Component load (counts of H in the table, with M-H in brackets): TRK 11 (3, 5, 6, 19, 20, 25, 28, 32, 33, 35, 36)
[+10, 14, 15, 16, 30]; SPOON 10; GRASP 9 (5, 14, 15, 16, 20, 25, 28, 35, 36) [+6, 10, 19, 32, 33]; SYM 8 (8, 10, 20, 32,
33, 35, 36, 37); SIM 7 (1, 3, 5, 6, 15, 16, 30) [+14, 28, 32, 33]; SMOOTH 7 (5, 6, 14, 19, 20, 30, 32) [+33]; SEG 5
(10, 15, 16, 25, 28); STEREO 5 (5, 20, 25, 35, 36) [+28]. Eval 5 has GRASP H but is not in the grasp-synthesis
"likely fails" list: its grasps exist, and the risk is the spoon-pot contact while the pot is lifted.

## 3. Grasp-synthesis flags (rigid grasp-and-carry per segment, note 10 P9)

LIKELY FAILS (8): the key segment is not a rigid grasp-and-carry, or it needs a start state the sampler rules out.
- 20: frame-0 cup is already in mid-air in the left hand. Reset = exact reference fingers, VOC 0, no hold. In one 50 ms
  control step a free cup falls ~1.2 cm [E], so the frame-0 grasp must already squeeze. [H] Fix: a deliberately
  pre-loaded (slightly penetrating) frame-0 grasp, verified by a frame-0 drop test in the evaluator physics.
- 25: boards are 7.5-9 mm plates lying flat. The human slides board 1 to the table edge, pivots it on edge, then slots
  the two boards together with both hands. At mu = 1.0 everywhere, a top-press drag is impossible [E]. A lateral edge push
  or a pivot primitive is needed (non-prehensile), followed by an edge pinch.
- 28: L->R hand-over with both hands on one 24x33 mm stick handle, plus a 180 deg mid-air flip with ~0.6 N m of
  gravity torque at the grip [E]. Two human-sized Sharpa hands (208x90x50 mm) on a ~15 cm handle are likely to collide.
- 14: mid-air hand-over of a horizontal cup, then a 180 deg flip and an inverted placement on a rack whose hulls the GT
  end pose penetrates by 6-8 mm.
- 15, 16: spoon pinch from flat, then a hand-over or two-hand regrasp, then a handle-first insertion into a tower
  whose hull opening (~18-24 mm) barely clears the handle. The grasp must sit on the bowl/upper handle.
- 35: >=4 hand-to-hand passes and in-hand reorientations. Each switch is a discrete failure opportunity (note 14: one
  drop costs 0.18-0.45 AUC and kills MP-SR).
- 36: in-hand twirls (dexterous rotation inside one hand), then a hand-over.
PARTIAL (8): the grasps are feasible, but a contact segment likely breaks in simulation.
- 3, 5, 6 (stirring in the pot), 32, 33 (stirring in a hand-held cup): the spoon bowl works inside a cavity whose hull
  floor or walls are 5-25 mm off. Every reference error turns into contact forces on a 0.3 kg container. 5 is the worst,
  because the pot is lifted with the spoon inside. In 32 the hand is already on the cup at f0.
- 10: insertion is only possible with a rim-band grasp (top ~2-3 cm of the beige cup) or a release-and-drop. The nest
  state overlaps the hulls by ~5 mm.
- 19: sweeping strokes drag the held sweeper over the table and dustpan, and the dustpan is slid and yawed on the table.
  Hands are already moving at f0.
- 30: the grasp is easy, but the slot-0 sweeper starts 10 mm inside the rack hulls, and the scrub presses on a 0.3 kg
  rack.
FEASIBLE (4): 1 (pot handle + lid bar; the lid states must be hull-aware), 8 (cup wrap and pot handle; the beige spin
is the real risk), 37 (pick-lift-place), 38 (one-hand ring handle).

## 4. Stage C measurements (details in the log, section 7)
- [V] Collision assets: the public URDFs reuse the visual GLB as the collision mesh (separate *_collision.glb only for
  the sweeper and the boards), mass 0.3 kg as a placeholder. FlashCHORD's CoACD runs at threshold 0.05 with unlimited
  hulls (note 01). There is no spoon URDF or mesh.
- [V] CoACD 1.0.14 (seed 0, threshold 0.05, other params default; [E] FlashCHORD's wrapper assets/mesh.py was not
  fetched, so its other params may differ) gives 9-73 hulls per object. Top-down height maps (scan vs hulls): cups keep
  their cavity, but the walls bulge 10-25+ mm inward at some rim azimuths. The pot basin floor rises 5-25 mm. In the rack,
  57/37/10 % of plan cells rise >5/>10/>25 mm, and the tower narrows. The boards' slot is kept (16 vs 19 mm). The
  dustpan, lid and sweeper change by <=10 mm on >90 % of cells.
- [V] GT contact states inside the hulls (hull-of-A samples in the hulls of B): lid/pot 7.6-8.4 mm (eps 0, 2);
  beige/blue nest 4.6-4.9 mm (11); cup/rack 6.0-8.4 mm (12, 13); pot/rack 7.1-9.6 mm (26, 27); sweeper/rack 10-15 mm (31);
  boards 1.3-2.9 mm (23, 24); sweeper/dustpan <=3.4 mm (18); separated pairs 0.0 mm. In the rack-pair control, scan
  vs scan gives 1.0-1.3 mm max (p99 0.0-0.6), so the rack overlap comes from CoACD.
- [V] On-table moving frames in public GT (lowest scan vertex within 1 cm of the table, >2 cm/s): listed in summary
  item 5. Cups, the pitcher and most pot motions are airborne.
- [V] Sizes: cups rim ~88 mm, 170 mm tall; pot stick handle reaches 242 mm from the body centroid, end cross-section ~24x33
  mm; pitcher 141x272x415 mm; lid 190 mm; rack 117x175x510 mm; sweeper 48x114x142 mm; dustpan plate ~3-4 mm [E];
  boards 139x227 mm, 7.5/9.1 mm thick.

## 5. Design needs (consolidated across stages A, B and C; method only, no per-episode labels)
1. Rig: no 180-degree re-rotation. Use the calibration as given (left = ego_cam_c, right = ego_cam_b). Add mono-pair
   tracking as a fallback whenever the colour view truncates an object (20, 28), and reject non-ego hands in the colour
   and mono streams (14, 15, 16, 20, 25).
2. Anchor: estimate the slot-0 frame-0 pose from the whole track (best-observed or static END segment, propagated
   backward), with support and stable-face priors (note 11). Detect the static start automatically (hands open or
   first contact) and allow it to be zero (20, 32).
3. Hull-aware references (new): reproduce FlashCHORD's exact convex_decompose call offline (fetch assets/mesh.py at the
   pinned commit), project every reference pose to non-penetration against those hulls, and run a frame-0 settle/drop
   test in the evaluator physics before any RL spend. Ask the organisers whether we may supply collision meshes (note 10
   Q4). Without this, eval 30 (anchor), 1, 10, 14, 28 and the stirring clips start or end in interpenetration.
4. Per-segment action typing from object kinematics plus support contact: static / carry / on-table slide-or-pivot /
   hand-over / tool contact (stir, sweep, scrub) / insertion / in-hand reorientation. Each type then goes to grasp
   synthesis (carry), to a push/pivot primitive (slides; lateral edge pushes, since mu = 1 everywhere), or to the
   repaired human-hand fallback (in-hand, hand-over windows).
5. Task-constrained grasp locations: rim band for nesting (10), bowl/upper handle for handle-first insertion (15/16),
   one hand per handle end for the pot hand-over (28), and frame-0 pre-loaded grasps (20, 32 contact at f0).
6. Spoon: our own mesh, collision hulls and inertia, a marker-based pose (notes 13) and a roll sign rule. Also a
   collision-aware smoother against the container hulls in 3/5/6/32/33 and the tower in 15/16.
7. Symmetric anchors: blue cup (10, 14, 20, 32, 33) and beige cup (8) need the marker-layout spin (note 12); rack (15, 16)
   needs geometry or a world link (note 11); board identity (25) from the marker layout.
8. Budget: the 8 "likely fails" episodes are where extra seeds (note 14 best-of-N) and per-segment fallbacks pay most.

## 6. Development cases with public GT for each risk (falsification tests)
| risk | public dev case | test that could falsify the fix |
|---|---|---|
| frame-0 in-hand anchor (20) | 21/22 trimmed to start at the cup lift (~f33-40) | back-propagated anchor error vs GT; frame-0 drop test of the pre-loaded grasp in sim |
| hull interpenetration at reset (30, 1) | 31 f0 (sweeper in dividers), 0/2 f0 (lid on pot) | the hull-aware projected start must settle <2 mm / <1 deg in 1 s at VOC 0 |
| placement on inflated rack (14, 28) | 12/13 end, 27 end | end pose after settling vs GT; the policy must not knock the rack |
| flat-plate pick-up by slide/pivot (25) | 23/24 piece_1 (68/87 on-table frames) | push primitive reproduces a 7 cm slide and the pivot in sim within 1 cm / 5 deg |
| sweeping drags (19) | 18 | sweeper/dustpan tracking error during on-table runs |
| nesting insertion (10) | 11 | beige final height within 5 mm of GT in sim with a rim-band grasp |
| hand-over on a handle (28) | 27 is single-handed; 26 has the left hand on the tower | no public two-hand handle hand-over -> sim-only feasibility test |
| stirring/tool contact (3/5/6/32/33) | none with GT (no spoon) | proxy: sweeper-in-dustpan contact (18) |
| spoon in-hand/hand-overs (35/36) | none (dustpan hand-over in 39 as a proxy) | count of discrete drops over 3 seeds |

## 7. Stage C measurement log (chronological, as recorded during the run)
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

## 8. Per-episode descriptions (Stages A and B; upright sheets in work/15/up/)

### Stage A (eval 1, 3, 5, 6, 8, 10, 14, 15, 16)
- [V] Stage-A instruction says "rotate 180"; per Progress 1/2 the stored ego_cam_a is already upright, so
  descriptions below use the UPRIGHT sheets work/15/up/e<ep>_even12.png (12 evenly spaced frames, 400 px wide each)
  plus onset sheets. Eval object slots from kit data/track_3_evaluation_objects.json.

#### Eval 1 (335 f, 16.7 s; slots: 0 white_pot, 1 white_pot_lid; twin task Pot_with_lid = public 0/2)
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

#### Eval 3 (313 f, 15.6 s; slots: 0 white_pot, 1 wooden_spoon; no public twin - spoon has no scan/GT, cf. 10/13)
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

#### Eval 5 (288 f, 14.4 s; slots: 0 white_pot, 1 wooden_spoon; same scene layout as eval 3)
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

#### Eval 6 (243 f, 12.1 s; slots: 0 white_pot, 1 wooden_spoon; same layout as 3/5)
- [V] f0-8 hands open; LEFT hand on pot handle by f16, pot rotated/slid on table by ~f24-32 ([E] handle
  direction changes ~20-30 deg). RIGHT hand lifts spoon ~f32-40 (blur), stirs inside pot f48-176 while
  left hand holds/tilts pot; pot raised a little off the table toward the camera at ~f80 and ~f110
  ([E] tilt + lift of a few cm, larger in image, blurred); spoon returned ~f198-220, hands open f242.
- [V] Occlusion: spoon bowl hidden inside pot most of f48-176; right forearm over pot; pot handle in fist.
  Strong motion blur on spoon in most stirring frames (stirring is fast, ~1 stroke per 8-16 frames [E]).
- [E] slot-0 static start ~16-24 frames.
- Pattern [V] eps 3/5/6 are the same "pot + spoon stirring" task with varying pot motion: 3 = pot stays
  on table, 5 = pot lifted high, 6 = pot lifted slightly. Method must not assume either.

#### Eval 8 (219 f, 11.0 s; slots: 0 beige_cup, 1 white_pot; no public twin task "pour cup into pot")
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

#### Eval 10 (161 f, 8.0 s; slots: 0 blue_cup, 1 beige_cup; twin task Cup_Stack = public 11)
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

#### Eval 14 (158 f, 7.9 s; slots: 0 blue_cup, 1 plastic_dish_rack; twin task Cup_In_Dish_Rack = public 12/13)
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

#### Eval 15 (166 f, 8.3 s; slots: 0 plastic_dish_rack, 1 wooden_spoon; no public twin with spoon)
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

#### Eval 16 (173 f, 8.6 s; slots: 0 plastic_dish_rack, 1 wooden_spoon; same task/scene as eval 15)
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

### Stage A synthesis: eval 1,3,5,6,8,10,14,15,16 (design needs; no per-episode labels for inference)
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
(Stage B followed; see below.)

### Stage B (eval 19, 20, 25, 28, 30, 32, 33, 35, 36, 37, 38)
- Slots (kit json): 19 mini_sweeper,mini_dust_pan | 20 blue_cup,water_pitcher | 25 wooden_piece_1,wooden_piece_2 |
  28 plastic_dish_rack,white_pot | 30 mini_sweeper,plastic_dish_rack | 32/33 blue_cup,wooden_spoon |
  35/36/37 wooden_spoon (solo) | 38 mini_dust_pan (solo).
- Public twins: 19<->18 Dust_Brush; 20<->21/22 Water_Can_Blue_Cup; 25<->23/24 Planter_Stand; 28<->26/27
  Pan_In_Dishrack; 30<->31 Brush_Dishrack; 38<->39/40 Dustpan_Solo; 32/33 (cup+spoon) and 35/36/37 (spoon solo): NO twin.
  Public ego_cam_a already local: 0,11,12,13,18,21,22,23,26,31,39,41 (no download needed for twins).


#### Eval 19 (235 f, 11.7 s; slots: 0 mini_sweeper, 1 mini_dust_pan; twin Dust_Brush = public 18)
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

#### Eval 20 (202 f, 10.1 s; slots: 0 blue_cup, 1 water_pitcher; twin Water_Can_Blue_Cup = public 21/22)
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

#### Eval 25 (356 f, 17.8 s; slots: 0 wooden_piece_1, 1 wooden_piece_2; twin Planter_Stand = public 23/24)
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

#### Eval 28 (220 f, 11.0 s; slots: 0 plastic_dish_rack, 1 white_pot; twin Pan_In_Dishrack = public 26/27)
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

#### Eval 30 (263 f, 13.1 s; slots: 0 mini_sweeper, 1 plastic_dish_rack; twin Brush_Dishrack = public 31)
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

#### Eval 32 (259 f, 13.0 s; slots: 0 blue_cup, 1 wooden_spoon; NO public twin (cup+spoon "stir in cup"))
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

#### Eval 33 (348 f, 17.4 s; slots: 0 blue_cup, 1 wooden_spoon; same task as eval 32, no public twin)
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

#### Eval 35 (421 f, 21.0 s; slot: 0 wooden_spoon (solo); no public twin, spoon has no scan)
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

#### Eval 36 (407 f, 20.3 s; slot: 0 wooden_spoon (solo); no public twin)
- Sheets: up/e36_even12.png, up/e36_onset.png.
- [V] Spoon flat near the table's back edge (bowl left, handle right). f0-8 hands open; RIGHT hand grips the
  handle ~f24-32, lifts ~f40 (blur), turns it bowl-up vertical f48-64, then waves/twirls it: horizontal and
  pointing AWAY from the camera f72-120 (strongly foreshortened, bowl beyond the table edge against the floor,
  sometimes nearly end-on); left hand idle and open f0-~200. Hand-over R->L ~f210-225; LEFT hand holds it
  vertical bowl-up f221-258; both hands f295; RIGHT hand vertical f332; laid on the table ~f360-370 (yaw ~30 deg
  different from start, closer to the camera); hands open f406.
- [E] slot-0 static start ~20-24 frames; static end ~30-40 frames.
- Risks [H]: long single-object clip with fast twirls (blur) and end-on views; hand-over; same spoon-mesh issue.

#### Eval 37 (151 f, 7.5 s; slot: 0 wooden_spoon (solo); no public twin)
- Sheets: up/e37_even12.png, up/e37_onset.png.
- [V] Simplest Stage-B clip: spoon flat across the table (bowl left, handle right). f0-8 hands open; RIGHT hand
  touches ~f16, grips the handle ~f24-32, lifts ~f40 (blur), holds it roughly level and high above/behind the
  table's back edge f48-64 (spoon against the floor/truss background, [E] ~20-30 cm above the table), lowers and
  lays it back ~f72-88 close to its start pose, keeps the hand on it to ~f104 (small slide/adjust [E]), releases
  ~f108-112; static f112-150. Left hand idle/open the whole clip; no hand-over, no large rotation.
- [E] slot-0 static start ~16-24 frames; static end ~40 frames; end pose within a few cm/deg of the start [E].
- Risks [H]: low; good "sanity" case for the spoon pipeline (mesh, scale, lift height from stereo).

#### Eval 38 (263 f, 13.1 s; slot: 0 mini_dust_pan (solo); twin Dustpan_Solo = public 39/40)
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


### Stage B synthesis: eval 19,20,25,28,30,32,33,35,36,37,38 (design needs; no per-episode labels for inference)
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
work/15/board_ascii.py. Stage C: sections 2-7.

## 9. Rig, calibration and early provenance (progress logs 1-3)
Work dir: /Users/aebatirel/Documents/Code/v2d-research/work/15/ (dl.sh, sheet.py, sheets/*.png)
Videos: /Users/aebatirel/Documents/Code/v2d-research/data/track_3/evaluation/videos/chunk-000/observation.images.ego_cam_a/ (all 20, sizes match tree.json)

### Early findings
- [V] Stored ego_cam_a eval video is ALREADY upright (hands enter from image bottom, floor/horizon at top).
  Rotating it 180 deg makes it upside down. calibration.json marks ego devices rotation_deg=180 and the
  ego stereo pair entry says left=ego_cam_c, right=ego_cam_b ("a 180 degree rotation mirrors the baseline
  direction"), i.e. the file describes the rotated (stored) orientation. Whether intrinsics cx/cy are
  for the raw or rotated image is still unverified. Sheet: sheets/e1_norot.png vs e1_even (rotated, wrong).
- [V] Eval frame counts (ego_cam_a, 20 fps): 1:335 3:313 5:288 6:243 8:219 10:161 14:158 15:166 16:173 19:235
  20:202 25:356 28:220 30:263 32:259 33:348 35:421 36:407 37:151 38:263.

### Progress 1 (12-frame sheets for all 20 viewed; sheets/e<ep>_even.png, sheets/f0_a.png, f0_b.png)
- [V] Eval 20 frame 0: slot-0 blue_cup already held in the air by the left hand (tilted, off-table, sheets/e20_f0.png).
  Public twins 21/22 start with the cup resting on the table (GT z0 0.687 = resting; p21_start.png). Zero static prefix.
- [V] Eval 32 frame 0: left hand already wrapped around slot-0 blue_cup (on table); lifted by ~f23.
- [V] Second person visible in background in 15, 16 (seated, green shirt, hands/arms) and 25 (standing legs).
- Notes per episode being written below.

### Progress 2 (onset sheets sheets/e<ep>_onset.png viewed for all except 20; calibration test)
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

### Progress 3 (resumed 2026-10-05 after outage)
- [V] All 20 eval ego_cam_a clips present; eval ego_cam_b for 3,8,15,20,25,35,36,37 and ego_cam_c for 3,20,35,36.
- [V] Re-made UPRIGHT (no rotation) 12-frame sheets: work/15/up/e<ep>_even12.png (older sheets/e*_even.png are rotated 180 = upside down).
- [V] Mocap marker balls (black/grey spheres, ~1 cm) are visible on the pot lid and pot in eval 1 (sheets/e1_norot.png).
- [V] Public GT static prefixes (work/15/gt_start.out): slot-0 1 cm onset 10-114 frames when slot 0 moves; slot 0 never moves in 11 (blue_cup), 26/27/12?/13? (rack is slot 1 in 12/13; rack is slot 0 in 26/27/31).


## 10. Artifacts and commands
- Python: /Users/aebatirel/Documents/Code/v2d-research/venv/bin/python <script> run inside work/15/c/ (stage C) or
  work/15/ (stages A/B). CoACD is importable only through work/15/c/pylib (installed with
  `uv pip install --python <venv python> --target ./pylib --no-deps coacd`); the shared venv was not modified.
- Stage C scripts -> outputs (work/15/c/): dims.py -> dims.out; thin.py -> thin.out; support.py -> support.out;
  coacd_run.py -> hulls/<obj>.npz, coacd_run.out; coacd_fill.py -> coacd_fill.out, fill_<obj>.txt; rack_heights.py ->
  rack_heights.out, rack_tower_6mm.out, board1_3mm.out, board2_3mm.out; board_thick.py -> board_thick.out;
  pen.py -> pen.out; pen_ctrl.py -> pen_ctrl.out; nest.py -> nest.out.
- Stage A/B: work/15/sheet.py (contact sheets), up/e<ep>_even12.png, up/e<ep>_onset.png, twin sheets up/p*_even12.png,
  up/boards_f0_e25_p23.png, up/e20_cam{a,b,c}_lift.png, twin_motion.py/.out, board_ascii.py, gt_start.py/.out,
  rectcheck*.py. Older sheets/e*_even.png are rotated 180 deg (upside down) and should not be used.
- No downloads in stage C. Nothing was submitted, and no evaluator or physics file was changed.

## 11. Skeptical verification of claims C1-C4 (verifier, 2026-10-05; scripts in work/15-verify/)
- C1 [V reproduced]: raw decoded frames (no rotation) are upright for eval a (1, 20), public a (0) and eval mono b/c (20)
  (15-verify/raw_grid.jpg). ffprobe shows no rotation side data, so every decoder returns the same upright pixels.
  Own SIFT + calibration-epipolar test (15-verify/epi_bc.py, independent of stereoRectify): b<->c median epipolar error
  with the calibration as given (left=c) 1.32 / 2.57 / 1.22 px (eval 20 / eval 35 / public 12) vs 5.5-28 px for the
  swapped, inverted, principal-point-flipped and F-conjugated variants. Colour->mono (epi_a.py): ego_cam_a
  extrinsics_to_stereo_left fits ego_cam_b (raw device stereo-left), NOT ego_cam_c (the pair's "left"):
  a->b 3.2-6.0 px (eval 3, 20; frame-set dependent) vs a->c 17 px, inverse 35-38 px. Correction: the 3-4 px holds only
  on some frame sets, and the colour extrinsic target is cam_b despite the "stereo_left" name.
- C2 setup [V code, fetched at video_to_data@7c0d3b94 into 15-verify/fc_*.py|yaml|toml]: flash_chord/assets/mesh.py
  convex_decompose calls coacd.run_coacd(threshold=0.05, max_convex_hull=-1, preprocess_mode="auto", no other kwargs;
  objects.py passes decompose_params={} by default; decomposition is per Newton mesh shape on unscaled source vertices).
  BUT flash_chord/pyproject.toml pins coacd==1.0.11, not the 1.0.14 dig 15 used. Both versions have identical
  run_coacd defaults (checked by signature). Public GLBs are single-geometry with identity node transforms, scale 1.
  Next: re-decompose with coacd 1.0.11 (15-verify/pylib11) and re-measure penetration with an independent metric.
- C2 [V reproduced with the pinned coacd 1.0.11] (15-verify/decomp11.py -> hulls11/, penv.py): 1.0.11 gives other hull
  counts than 1.0.14 (rack 54 vs 50, sweeper 24 vs 22, pot 40 vs 31, lid 48 vs 41; 1.0.14 rerun without merge_vertices
  reproduces dig 15's counts exactly, so the call is deterministic) but the same penetration: hull-of-A surface depth in
  B hulls, 1.0.11: sweeper/rack ep31 f0 10.5 mm, f160 15.3; lid/pot ep0 f0 7.7, ep2 f0 8.1, ep0 end 8.4; pot/rack ep26 f4
  9.8, ep27 f216 7.2. Scan-of-A points give 0.5-2 mm less (pot/rack ep27: 5.2 max, p99 0.1). Upper bound by face-normal
  SAT per hull pair: 9.5-17.3 mm. So the 5-15 mm range stands; "the hulls cause it" still needs the control below.
- C2 control [V] (15-verify/ctrlv.py, hulls11): dig-15-style normal-sign scan-vs-scan max is 1.1-1.9 mm for ep31 f160,
  ep27 f216, ep26 f4, but 3.7 mm at ep31 f0 (dig 15's own pen_ctrl.out says 3.8; the claim's "1.0-1.3 mm" omits the
  frame-0 case). Independent unsigned-distance check: the deepest A-scan point is 0.1-3.2 mm from B's scanned surface
  yet 7.6-14.8 mm inside B's hulls (sweeper/rack f160: 0.2 mm vs 14.8 mm; lid/pot f0: 0.1-0.9 mm vs 7.6 mm). A ball of
  that radius around a point next to a 2-3 mm wall must contain free space, so the hulls fill free space by >= 6-14 mm:
  hull-caused for the lid/pot too (supports dig 15's [E]). Real scan overlap is at most ~1-4 mm.
- C3 mechanism [V code, 15-verify/fc_evaluation_rollout.py:392-401 + kit AUC.py _warp_to_reference_start]: the first
  recorded achieved pose (step 0, reference_frame 0) is read AFTER the first jax_env.step (one 50 ms control step;
  sim/rl.yaml fps 20, substeps 5), and the scorer warps ALL achieved frames/objects by the transform that maps achieved
  slot-0 step-0 pose onto GT slot-0 frame 0. So a slot-0 push-out that happens inside step 1 is absorbed into the
  alignment and becomes a world-frame error for every later frame and for slot 1, not a slot-0 "settle error"; only
  displacement after step 1 shows as a slot-0 error. Object-object pairs are not filtered by the collision policy
  (scene/collision.py:140-175); within-object hull pairs are filtered (objects.py:202-209).
- C2 remaining pairs [V, hulls11 = pinned coacd 1.0.11]: cup on rack ep12 f160/end 8.4/8.3 mm, ep13 f176/end 6.3/6.0 mm
  (reproduces 6-8.4); nest ep11 f96/end 4.1/4.3 mm (dig 15 with 1.0.14: 4.6-4.9; SAT upper bound 8.4-9.7); boards
  ep23 f292 3.0, ep24 f244 1.7 mm, but piece_1 SCAN points are 0.0 mm inside piece_2 hulls (only one hull pair overlaps:
  piece_1's own hull inflation). Controls: cup/rack normal-sign 1.0 mm max (reproduces); nest deep points are 0.8 mm
  median from the blue-cup scan with 4.2 mm hull depth (thin-wall case, hull-caused only in part, [E]).
- C3/C4 frames [V] (15-verify/f0_30_20.jpg): eval 30 f0 sweeper stands between the rack dividers (twin 31 f0 too, but in
  a different gap); eval 1 f0 lid on pot; eval 20 f0-f8 blue cup held tilted in the left hand off the table edge, twin 21
  f0 cup resting. Eval-30 "10 mm" is a twin-31 inference (31 f0 gap 10.3-10.5 mm, 31 end gap 13.1 mm), not measured.
- Reset [V code]: kit evaluation/flash_sac.yaml sets reset_mode: explicit, start_frame 0; harness explicit path ->
  prepare_explicit_reset (reset.py:384-399) sets finger_scale 1.0 (exact reference fingers), VOC scale 0, VOC force and
  torque 0, no settling hold (the hold exists only in "sampled_settled"). Control step 50 ms (sim/rl.yaml).
- C3 approximate physics [E, NOT the evaluator] (15-verify/mjsettle.py: MuJoCo 3.8.1 CPU in 15-verify/pylibmj, hulls11,
  dt 0.01, implicitfast, Newton, pyramidal, impratio 20, mu 1, margin 0, default solref 0.02/1; Newton's ke/kd->solref
  mapping unverified): twin 31 f0 sweeper+rack -> sweeper moves 5.4 mm / 5.9 deg in the first 50 ms step, 18.6 mm (dz
  +17.9) by 0.25 s, 40.5 mm / 32.6 deg by 1 s (rack 1.6-2.7 mm / ~1 deg = same as rack alone). Twin 0 f0 lid+pot -> lid
  12.7 mm (dz +12) in 50 ms, 34 mm / 17-19 deg by 0.25-1 s; pot (eval-1 slot 0) only its baseline 1.2 mm / 0.9 deg.
- C3 softness sensitivity [E]: solref timeconst is clamped to 2*dt = 0.02 s, so 0.005 = default. Softer contact
  (solref -1000 -100 = literal ke/kd, or 0.05 s): step-1 motion only 4.5 mm / 2.9-3.8 deg (sweeper) and 1.7-1.8 mm (lid);
  the push-out then continues over 0.25-1 s to sweeper +21-22 mm up / ~3 deg and lid +9-12 mm / 2-3 deg. So "ejected AT
  STEP 1" is not robust: depending on contact softness most of the push-out lands after step 1 (a slot-0 error while
  static, not absorbed by the alignment). In every setting the push-out (1-4 cm, 3-33 deg) exceeds note 14's
  5 deg + 3 mm and 10 deg + 5 mm scenarios, so the cited AUC costs are a lower bound, not an estimate, for eval 30.
- C3 hull-aware z-lift test [E, 15-verify/mjlift.py]: the sweeper must be lifted 54 mm along z to clear the rack hulls
  (the overlap is lateral, inside the filled divider gaps); dropped from there it wedges 34 mm lower, i.e. ~20 mm above GT,
  tilted 13-15 deg. The lid clears at +12 mm and settles 3 mm / 2.4 deg -> ~9 mm above GT. So a pure vertical projection
  does not give a faithful eval-30 anchor; the sim-consistent sweeper rest pose is ~2 cm off GT whatever we do (unless
  the organisers accept our own collision meshes).
- C1 extra [V] (15-verify/upright.py): table-wood pixel centroid at f0/f30 lies at 0.62-0.84 of image height in all 20 eval
  and all 12 local public ego_cam_a clips (table below the horizon) -> every stored colour clip is upright.
- C4 [V]: eval 20 f0-f8 cup held tilted off the table edge (f0_30_20.jpg); twins 21/22 GT cup resting at f0 (z 0.687, z range
  0.2-1.1 mm over f0-19, 1 cm onset f37/f44). Reset is explicit with exact fingers and VOC 0 (above). Free fall in one 50 ms
  step: 0.5 g t^2 = 12.3 mm analytic, 15 g dt^2 = 14.7 mm with 5 semi-implicit 10 ms substeps. Note 10 P10 does say "open
  contact-free frame 0" (and G3 assumes a static-prefix anchor), so eval 20 (and 32) violate both. Extra: the cup is slot 0, so
  any step-1 slip is absorbed by the scorer alignment and misaligns the pitcher for the whole clip. "Trimmed" stays [H]:
  eval 20 has 202 frames vs 186/189 for twins 21/22, so the take is not simply a shortened twin.
- Verdict summary: C1 holds (correct the colour-mono error to 3.2-6.0 px and note the extrinsic targets cam_b). C2 holds
  with the pinned coacd 1.0.11 (nest 4.1-4.3 mm, rack control 1.0-3.8 mm incl. ep31 f0). C3 partly: push-out reproduced in
  approximate MuJoCo but its timing depends on contact softness and its size (1-4 cm, 3-33 deg for the sweeper) exceeds the
  quoted note-14 scenarios; the eval-30 depth is a twin inference. C4 holds.

## 12. Stage B re-run (workflow stage 2 of 3, 2026-10-06)
- [V] Resume check: section 8 "Stage B" (per-episode notes for 19, 20, 25, 28, 30, 32, 33, 35, 36, 37, 38, twin
  comparisons and the Stage B synthesis table) is already complete from the 2026-10-05 run, and its sheets exist in
  work/15/up/. That work is reused as is. This re-run only adds spot checks of uncertain Stage B claims, twins that are
  now local but were not viewed before (public 22 ego_cam_a), and automatic clip statistics (eval vs twin). New
  artifacts go to work/15/b2/.
- [V] Start checks (b2/e19_f0_22.png, b2/e28_f0_22.png; frames 0-22 step 2): eval 19 f0 left hand blurred while
  reaching, right hand raised open; left hand on the dustpan ring by ~f6-8; right hand reaches the sweeper ~f14 and
  touches it at ~f16-18. So the slot-0 sweeper is static for ~16 frames (0.8 s), consistent with the earlier ~10-15 f.
  Eval 28 f0 left hand open but moving in, on the pot handle by ~f8; right hand raised open through f22. Both
  earlier claims hold.
- [V] NEW: a seated second person (jeans, white sneakers, office chair, a forearm at the top-left) is at the LEFT image
  edge in eval 19 (f0 and f120), 28 (f0, f150) and 30 (f0); in 38 f0 only the chair base shows (b2/leftedge.png, left
  520 px of 2028). His forearm and shoe are within ~25 % of the image width of the table. Together with sections 8/9 a
  non-ego person is in view in at least 14, 15, 16, 19, 20 (mono), 25, 28 and 30. [H] So non-ego rejection is a
  default requirement, not a special case: accept only arms that enter from the bottom border and stay connected
  to it. [V] The camera wearer has a white smartwatch and a black bead bracelet on the LEFT wrist in every clip
  sampled here (19, 28, 30, 38) [H: a generic left/right ego-hand cue, still to be checked on all clips].
- [V] Twin 22 ego_cam_a is now local and was viewed (b2/p22_even12.png, 189 f): f0 hands open, cup RESTING upright at the
  table's left edge; left hand grasps the cup ~f17; right hand grips the pitcher ~f34; pitcher high and cut by the
  top/right border f51-85 with its gripping hand out of frame at f68; cup held tilted in the left hand f51-~150;
  pitcher back on the table ~f137, cup set down ~f154, hands open f154-188 (static end ~35 f). A STANDING person walks
  at the top-left (f0-17) and stays there; the seated person is at the left edge.
  Compared with eval 20 (202 f): eval 20 grips the pitcher ~f16-24 (twin 22 ~f34) but sets the cup down at about the
  same frame (~f150-160 vs ~f154) and is 13 f longer. [E] So eval 20 is not a twin clip with its first ~1.5-2 s cut
  off. More likely the wearer already held the cup when recording started, and the middle of the clip runs slower.
  The earlier "trimmed start" stays [H] and should not be used as a design assumption. For the frame-0 in-hand anchor,
  21/22 trimmed to start after the cup grasp (~f17-35) are still the closest development cases with GT.
- [V] Automatic clip statistics, eval Stage B vs local twins (b2/clipstats.py -> b2/clipstats.out, b2/clip_<tag>.npz;
  colour at 507x380; head motion = median LK flow of 300 corner features between consecutive frames, in px/frame at
  507 px width; sharpness = variance of the Laplacian; "soft" = frames below 0.5x the clip median):

  | clip | frames | flow median | flow p90 | flow max | soft frames |
  |---|---|---|---|---|---|
  | e19 / p18 | 235 / 353 | 1.37 / 0.72 | 2.97 / 2.14 | 10.5 / 5.3 | 5 % / 1 % |
  | e20 / p21 / p22 | 202 / 186 / 189 | 1.23 / 1.60 / 1.25 | 2.46 / 3.87 / 3.02 | 5.8 / 11.5 / 11.5 | 1 / 4 / 5 % |
  | e25 / p23 | 356 / 325 | 0.98 / 0.89 | 2.33 / 2.28 | 7.4 / 5.1 | 1 / 2 % |
  | e28 / p26 | 220 / 158 | 1.08 / 0.95 | 2.57 / 1.85 | 6.4 / 2.5 | 1 / 0 % |
  | e30 / p31 | 263 / 290 | 0.67 / 0.76 | 1.69 / 1.91 | 3.3 / 3.3 | 0 / 0 % |
  | e38 / p39 | 263 / 319 | 0.90 / 1.13 | 1.94 / 2.55 | 3.3 / 4.3 | 0 / 1 % |
  | e32, e33, e35, e36, e37 (no twin) | 259, 348, 421, 407, 151 | 1.01, 0.93, 1.10, 1.05, 0.95 | 2.52, 3.18, 2.56, 2.36, 1.73 | 6.5, 11.6, 5.7, 4.8, 2.7 | 3, 2, 2, 0, 0 % |

  [E] With ~83 deg across 507 px (0.16 deg/px), the median head rotation is ~0.1-0.2 deg/frame (2-4.5 deg/s), p90 up to
  ~0.6 deg/frame, and peaks reach ~1.9 deg/frame (~38 deg/s). Peaks coincide with manipulation events: e19 f116-154 (dustpan
  dump toward the left edge), e33 f304-307 (cup set down), p21 f24-26 and p22 f19-23 (head turns to the cup grasp).
  [V] Global-softness frames are rare (0-5 %). So the blur seen in the sheets is mostly object motion, not whole-frame
  head-motion blur. [E] The eval clips are in the same head-motion range as their twins (e30/p31 nearly equal). Eval 19
  moves the head about 2x faster than twin 18 (median 1.37 vs 0.72), consistent with eval 19 being the same script done
  faster. So the public twins are representative development cases for camera tracking. A visual-odometry front end
  that handles p21/p22 (the fastest twins, peak 11.5 px/frame) covers every Stage B eval clip.
- [V] Eval 35 dense sheet (b2/e35_dense.png, f24-408 step 12) refines "several hand-to-hand passes". The holding hand
  alternates R (f16-~36) -> both (f36-60) -> L (f72-96; spoon nearly along the view axis, the right hand open) -> both
  (f108-132) -> R (f144-168, spoon vertical bowl-up, left hand open) -> both (f180-204) -> L (f216) -> both (f228-252,
  horizontal) -> R (f264-300, diagonal) -> both (f312-336) -> L (f348-384) -> set down by the left hand ~f384-396.
  [E] That is 5 complete hand-overs (R->L, L->R, R->L, L->R, R->L), each through a 1-1.5 s two-hand phase. Only ~35 % of
  the clip has a single holding hand. [E physics] For a rigid grasp-and-carry policy that means 5 grasp switches, each a
  chance of a drop. The two-hand phases (~45 % of frames) need both Sharpa hands on a ~30 cm spoon at once.
- [V] Eval 36 dense sheet (b2/e36_dense.png, f24-396 step 12): the right hand grips the handle end ~f24-36 and lifts the
  spoon bowl-up by f48. From f48 to ~f180 it swings the spoon AWAY from the camera and back about three times (end-on or
  strongly foreshortened at f72-84, f120 and f156; bowl near the table at f96, f132 and f168, where it may touch the
  table [E]). This reads as "lift, point away, lower" cycles rather than in-hand twirls. Then R->L hand-over f192-204
  (spoon vertical bowl-up), left hand holds it vertical f216-264, L->R hand-over f276-288, the right hand carries it to
  the right (f300-336) and lays it down bowl-left f348-372. Released ~f384, static to f406.
  [E] So eval 36 has 2 hand-overs (R->L, L->R), not 1. The table's "R, R->L, R" and section 3's "twirls, then a
  hand-over" undercount it. The main tracking risk is the three end-on phases (~0.5 s each). There, the image length of
  the spoon axis collapses and only stereo depth plus the marker triangle constrain the axis direction (note 13: ~1 deg
  tilt, 2.5-6 deg roll from b+c markers when they are visible).
- [V] Start vs end frames (b2/e35_startend.png f0/f420, b2/e36_startend.png f0/f406). Eval 35: f0 bowl upper-left,
  handle tip lower-right; f420 bowl left, tip upper-right. [E] The image-plane yaw change of the handle-to-bowl axis,
  after correcting for the table ellipse (~0.87 vertical squash), is ~60 deg (140 -> ~200 deg). The earlier "~120-150 deg"
  overstated it; correction: ~60 +- 15 deg. Eval 36: f0 bowl left, tip upper-right; f406 bowl upper-left, tip
  lower-right; [E] ~45 deg, consistent with the earlier ~30 deg. In both clips the spoon is set down within ~10 cm of its
  start [E]. Roll (bowl up vs down) cannot be read at this resolution in either clip.
- [H] Eval 35's END layout looks like eval 36's START layout, and eval 36's end looks like eval 35's start: same table,
  similar spoon placement. They may be consecutive takes. This is only a curiosity: inference must not link episodes, and
  it says nothing about mocap. It does mean the end-pose distribution of solo-spoon clips is "back near the start, yaw
  changed by tens of degrees", which a placement prior (note 11 style) could use.
- [V] Eval 19 end (b2/e19_end.png, f190-234 step 4): the dustpan is back flat on the table and static from ~f190, with the
  left hand open at the lower left. The sweeper (slot 0) stays in the right fist to the last frame f234, re-gripped and
  moved near the dustpan's right side. Confirms: slot 0 has NO static end, and its only free window is f0-~16. [E] In
  eval 19 the scorer's anchor therefore rests on ~0.8 s of a small object partly hidden by the fingers of the
  approaching hand from ~f12. That is the weakest anchor in Stage B apart from 20 and 32.
- [V] Eval 28 flip (b2/e28_flip.png, f88-143 step 5): the right hand holds the stick handle, with the arm stretched up
  and to the right. The pot's far rim touches or crosses the TOP border f88-~123 (interior facing the camera f88-103).
  The flip f108-133 is a ~180 deg roll ABOUT THE HANDLE AXIS by forearm rotation; by f128-143 the base faces the camera.
  The left hand rests low-left from f88. [E] So the flip is a wrist roll of ~180 deg in ~1.3 s (~140 deg/s) with the pot
  hanging off a ~24x33 mm handle. The seated person's forearm is at the left edge in every frame.
- [V] Eval 38 start vs end (b2/e38_startend.png f0/f262): f0 lip upper-left, ring handle lower-right; f262 lip vertical at
  left, ring to the right, plate flat. [E] With the ellipse correction the yaw change is ~65 +- 15 deg. The earlier
  "~90 deg" overstated it. The dustpan ends ~10-15 cm right of its start [E].
- [V] Contact precedes motion onset, and the grasp itself shifts the anchor (b2/gtdisp.py; public GT, slot-0 displacement
  and rotation from frame 0). Twin 22 cup: <=0.8 mm/0.7 deg to f12, then 2.5 mm/1.9 deg at f18 when the left hand closes
  (grasp seen at ~f17 in b2/p22_even12.png), held there to f39, lift at f42-45 (1 cm onset f44). Twin 21 cup: <=0.4 mm to
  f30, lift f33-39. Twin 31 sweeper (the twin of eval 30): 0.0 mm to f21, then 1.9 mm/4.4 deg at f30 and 4.6 mm/7.7-8.2
  deg by f42-45 while still on the table, lift at f48 (1 cm onset f47). Twin 18 sweeper: 0.4 mm/1.0 deg wiggle f21-24,
  1.3 mm/2.8 deg at f36, lift f39.
  [E] So the window up to the GT 1 cm onset is NOT a static window. The last 10-25 frames before the lift contain grasp
  perturbations of 2-5 mm and 2-8 deg. Averaging or smoothing the anchor over that window biases the frame-0 rotation by up
  to ~8 deg (31). The scorer applies the anchor's frame-0 pose to every object, so a rotation error theta moves an object at
  distance r by about theta*r: 2 deg at 0.25 m is ~0.9 cm, 8 deg is ~3.5 cm. Design need: estimate the frame-0 anchor
  only from frames before first hand contact (or explicitly model the contact shift). Test it on 31 and 22 by
  comparing "pre-contact only" with "up to the 1 cm onset" anchors against GT frame 0.
- [V] Automatic dustpan visibility (b2/pancolor.py -> b2/pancolor.out, b2/pan_<tag>.npz). An HSV yellow-green threshold
  at 507x380, keeping only the largest blob (the raw threshold also catches the hazard-tape stripes; see b2/pan_dbg.png),
  gives the visible area relative to the clip median. Eval 19: area drops to 0.14-0.5x during the dump tilt f144-156
  (minimum f152-153, which is also the head-turn peak of 10.5 px/frame). Twin 18 shows the same dip at f140-152
  (0.35-0.87x). Eval 38 never falls below 0.79x; at the "edge-on" f76-82 it is still 0.81-0.83x, so its edge-on risk
  is smaller than section 8 suggested. No border contact in eval 19, eval 38 or twin 18; twin 39 touches the right
  border for 21 frames (f224-244), which matches the truncation seen earlier.
  [E] For the dustpan, the hard frames in Stage B are the eval 19 dump (~12 frames, near edge-on, plus head-motion blur
  and the dustpan beyond the table edge). Twin 18 f140-152 is a matching development case with GT. [H] A colour-blob
  prior is a cheap, automatic segmentation seed for the dustpan, provided the tape stripes are rejected by blob size or
  shape. It needs no per-episode labels.

### Stage B re-run synthesis (adds to the Stage B synthesis in section 8; method only, no per-episode labels)
1. [V] A non-ego person is in view in at least 8/20 eval clips: 14, 15, 16, 19, 25, 28, 30 in the colour view and 20 in
   the mono views. Twins 22, 23 (two standing people plus the seated one, up/p23_even12.png) and 27 also contain one. Rejecting non-ego hands and arms is a default pipeline stage.
2. [V GT] Hand contact moves the anchor 2-5 mm and 2-8 deg before the 1 cm motion onset (twins 22, 31, 18). Estimate the
   frame-0 anchor from the pre-contact frames only (19: ~f0-14, the hand touches the sweeper at ~f16; 30: ~f0-28, grip ~f32; in twin 31 the first GT shift is at f24), or model the shift.
   [E] At 0.25 m lever arm, every 2 deg of anchor rotation error costs ~0.9 cm on the other object.
3. [V] Head motion in the eval clips (median 0.7-1.4, peak <=11.6 px/frame at 507 px) lies inside the range of the local
   public twins (peak 11.5 in 21/22). Whole-frame blur is rare (0-5 % soft frames). [E] Blur in the sheets is object
   motion, so deblurring or temporal priors belong in object tracking, not in the camera front end.
4. [V/E] Grasp-switch counts for the policy budget: 35 = 5 hand-overs (two-hand phases ~45 % of frames), 36 = 2, 28 = 1,
   19/20/30/32/33 = 0 (one object per hand), 25 = two-hand placement, 37/38 = single hand.
5. [V] Hardest single-object views: the eval 19 dustpan dump (f144-156; twin 18 f140-152 matches it, with GT); the
   eval 36 end-on spoon phases (f72-84, f120, f156; no GT twin; stereo plus markers); the eval 28 pot at the top border
   during a ~140 deg/s roll about the handle axis (f88-133).
6. [E] End-pose summaries corrected: eval 35 spoon yaw ~60 deg, eval 36 ~45 deg, eval 38 dustpan ~65 deg, all within
   ~10-15 cm of the start. Eval 19 sweeper: no static end.
7. Not done in this re-run: no new downloads (twins 24, 40 and ego_cam_a of 27 are still not local; 27 was viewed via
   cam_b before). The blue-cup visibility was not measured automatically: the blue floor tape defeats a simple colour
   threshold.

Stage B re-run status: COMPLETE (2026-10-06). New artifacts in work/15/b2/: e19_f0_22.png, e28_f0_22.png, leftedge.png,
p22_even12.png, e35_dense.png, e36_dense.png, e35_startend.png, e36_startend.png, e19_end.png, e28_flip.png,
e38_startend.png, pan_dbg.png; scripts clipstats.py (-> clipstats.out, clip_<tag>.npz), edgecrop.py, gtdisp.py,
pancolor.py (-> pancolor.out, pan_<tag>.npz). Sheets come from work/15/sheet.py with rot=0 (no rotation).

## 13. Stage C re-run (workflow stage 3 of 3, 2026-10-06) - progress log
- [V] Resume check: sections 1-7 (risk table, grasp flags, CoACD measurements) are from the 2026-10-05 Stage C run and
  predate the verifier (section 11) and the Stage B re-run (section 12). This re-run folds those corrections into the risk
  table, adds a few cheap checks (artifacts in work/15/c2/), and then rewrites the head of this note.
- [V] Non-ego person, remaining clips (work/15/c2/leftedge_A.png: left 520 px of 2028 at a mid frame of 1, 3, 5, 6, 8, 10,
  20, 32, 33, 35, 36, 37; c2/e8_topleft.png: eval 8 f60/110/160 top-left). The same seated person (office chair, jeans,
  white sneakers) is at the left edge in ALL twelve: legs and shoes in 1, 3, 5, 6, 8, 10, 32, 33, 35, 36, 37; only the chair
  base and a dark shape in eval 20's colour view. In eval 8 his BARE FOREARM with a dark wristwatch enters the top-left
  corner f60-160 (skin distractor ~1/3 of the image height). With section 12 (19, 28, 30; 38 chair only) and section 8
  (14, 15, 16, 25), a non-ego person is in the colour view of 19-20/20 eval clips (legs at least), and his arms or hands
  in at least 8, 14, 15, 16, 19, 25, 28 and 30. [E] So non-ego rejection is a default stage; the risk it guards against is
  a hand/skin detector latching onto his arms at the left border. [V] He also wears a wristwatch (dark band), so the ego
  left-hand cue must be the WHITE smartwatch plus the arm entering from the bottom border, not "a watch".
- [V] Pot handle free length (work/15/c2/handle.py -> handle.out; white_pot scan sliced every 10 mm along its 357.5 mm long
  axis, p1-p99 widths): body 0-~195 mm (diameter up to ~186 mm), handle ~200-357 mm, so the free handle is ~155-160 mm
  long. Its cross-section is ~18 x 31 mm over most of the length (29-35 mm at the root, 10 x 31 mm over the last ~25 mm).
  This refines the earlier "24 x 33 mm" (an outer-40 % envelope). [E] Two Sharpa hands (palm ~90 mm wide, note 04,
  secondary source) side by side need ~180 mm, more than the ~157 mm free handle. In eval 28's two-hand hand-over
  (f48-64) and eval 1/3/5/6/8's one-hand holds this means: one hand on the handle is fine (power grasp around 18 x 31 mm);
  two hands on it at once must overlap the root/pot wall or stack fingers. That supports the GRASP H rating for 28.
